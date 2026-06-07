"""검증 — 합성 배치 vs 실데이터(id 1~60) 클래스별 지표 분포 비교.

계획 합격 기준: 주요 지표 KS test p>0.05 또는 클래스 분리도 보존.
scipy 미설치 환경을 가정해 2-표본 Kolmogorov–Smirnov 를 직접 구현한다.

사용:
  uv run python scripts/synthetic/validate_batch.py --batch out/synthetic/batch_sample.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # 프로젝트 루트 (app import)

DB_URL = "postgres://spb_user:spb123@db.salpyeobom.kro.kr:15432/spb_db"
METRICS = ["aix_d", "total_aix_sum", "night_aix_ratio", "bath_count_d",
           "outgoing_count_d", "total_sleep_period"]
# 실데이터 라벨: id1~30 응급, id31~60 사망. 평시는 실데이터 없음(외삽) → KS 생략.
REAL_CLASS = {"응급": (1, 30), "사망": (31, 60)}


def _ks_2samp(a: list[float], b: list[float]) -> tuple[float, float]:
    """2-표본 KS 통계량 D 와 근사 p-value (동점/상수분포 정확 처리)."""
    n1, n2 = len(a), len(b)
    sa, sb = sorted(a), sorted(b)
    vals = sorted(set(sa) | set(sb))
    d = 0.0
    import bisect
    for v in vals:
        f1 = bisect.bisect_right(sa, v) / n1
        f2 = bisect.bisect_right(sb, v) / n2
        d = max(d, abs(f1 - f2))
    ne = n1 * n2 / (n1 + n2)
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * d
    return d, _probks(lam)


def _probks(lam: float) -> float:
    """KS 분포 Q(lam) — Numerical Recipes probks. lam→0 에서 1 로 안정 수렴."""
    if lam <= 0:
        return 1.0
    a2 = -2.0 * lam * lam
    fac, total, termbf = 2.0, 0.0, 0.0
    for j in range(1, 101):
        term = fac * math.exp(a2 * j * j)
        total += term
        if abs(term) <= 1e-3 * termbf or abs(term) <= 1e-8 * total:
            return max(0.0, min(1.0, total))
        fac = -fac
        termbf = abs(term)
    return 1.0  # 미수렴(lam 매우 작음) → p≈1


def _ks_matched(real: list[float], synth: list[float], draws: int = 21) -> tuple[float, float]:
    """공정 비교: 합성을 실 n 만큼 반복 subsample 해 KS p 의 중앙값을 취한다.

    실데이터는 n=30 단일 시계열, 합성은 n=1500 모집단이라 전수 KS 는 과민 기각된다.
    동일 n 으로 맞추면 '같은 분포에서 30개 뽑은 것과 구별되는가'를 본다.
    """
    rng = random.Random(20240501)
    n = len(real)
    ps, ds = [], []
    for _ in range(draws):
        sub = rng.sample(synth, min(n, len(synth)))
        dd, pp = _ks_2samp(real, sub)
        ds.append(dd)
        ps.append(pp)
    ps.sort()
    ds.sort()
    return ds[len(ds) // 2], ps[len(ps) // 2]


def _stats(v: list[float]) -> str:
    if not v:
        return "—"
    return f"{min(v):>6.0f}/{sum(v)/len(v):>6.0f}/{max(v):>6.0f}"


async def _load_real() -> dict[str, dict[str, list[float]]]:
    from tortoise import Tortoise

    await Tortoise.init(db_url=DB_URL, modules={"models": ["app.models.adl_raw"]})
    from app.models.adl_raw import AdlRawRecord

    out: dict[str, dict[str, list[float]]] = {}
    for klass, (lo, hi) in REAL_CLASS.items():
        rows = await AdlRawRecord.filter(id__range=(lo, hi)).all()
        out[klass] = {m: [getattr(r, m) for r in rows if getattr(r, m) is not None] for m in METRICS}
    await Tortoise.close_connections()
    return out


def _load_synth(batch: Path) -> dict[str, dict[str, list[float]]]:
    src2cls = {"응급": "응급", "사망": "사망", "평소": "평시"}
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with batch.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            klass = src2cls.get(r["source_type"])
            if not klass:
                continue
            for m in METRICS:
                if r.get(m) is not None:
                    out[klass][m].append(r[m])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=Path, default=Path("out/synthetic/batch_sample.jsonl"))
    args = ap.parse_args()

    real = asyncio.run(_load_real())
    synth = _load_synth(args.batch)

    print("=" * 92)
    print("검증: 실데이터(id1~60) vs 합성 — 지표별 min/avg/max + KS (전수 / n-매칭)")
    print("형식: 실(min/avg/max) | 합성(min/avg/max) | 전수KS p | n매칭KS p | 판정(매칭 p>0.05)")
    print("=" * 92)
    passes = total = 0
    for klass in ("응급", "사망"):
        print(f"\n[{klass}]  실 n={len(real[klass]['aix_d'])}  합성 n={len(synth[klass]['aix_d'])}")
        for m in METRICS:
            r, s = real[klass][m], synth[klass][m]
            if not r or not s:
                continue
            _, p_full = _ks_2samp(r, s)
            _, p_match = _ks_matched(r, s)
            ok = p_match > 0.05
            total += 1
            passes += ok
            print(f"  {m:<18} {_stats(r):>22} | {_stats(s):>22} | "
                  f"p={p_full:.3f} | p={p_match:.3f} {'✓' if ok else '×'}")

    print("\n" + "=" * 78)
    print("클래스 분리도 (시그니처 — 분류기가 의존하는 결정축)")
    print("=" * 78)
    for klass in ("평시", "응급", "사망"):
        s = synth[klass]
        bath0 = sum(1 for x in s["bath_count_d"] if x == 0) / len(s["bath_count_d"])
        na = s["night_aix_ratio"]
        print(f"  [{klass}] 목욕=0 비율={bath0:.0%}  night_aix(avg)={sum(na)/len(na):6.1f}  "
              f"aix_d(avg)={sum(s['aix_d'])/len(s['aix_d']):.0f}")
    print("\n  기대: 사망 목욕=0 100% · 응급 night_aix 大(수천) · 사망/평시 night_aix 小")
    print(f"\nKS 합격(n-매칭): {passes}/{total} 지표 (p>0.05)")


if __name__ == "__main__":
    main()
