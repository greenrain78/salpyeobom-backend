"""보고서 생성 대상 수급자 산정기.

조건: AI 이상탐지(`adl_anomaly_results`)에서 두 모델 동시 이상(`anomaly_dual`)
비율이 임계(기본 0.70) 이상인 수급자만 보고서 대상으로 본다. FK 연결을 위해
`patients` 에 존재하는 대상자로 한정한다.

`adl_anomaly_results` 는 Tortoise 모델에 매핑돼 있지 않고 PK 도 없는 분석 산출물
테이블이라, 이 유틸 스크립트에서만 읽기 전용 집계 쿼리로 접근한다(앱 런타임 아님).
환자 존재 여부 확인은 ORM(`Patient`)으로 한다.

사용법:
  USE_REMOTE_DB=1 uv run python scripts/select_report_targets.py [--threshold 0.7] [--out out/report_targets.jsonl]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from tortoise import Tortoise

from app.database import TORTOISE_ORM
from app.models.patient import Patient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "report_targets.jsonl"

# 수급자별 dual 이상 비율 집계 (읽기 전용). 매핑/PK 없는 테이블이라 raw SELECT 사용.
_AGG_SQL = """
SELECT care_recipient_id,
       max(label) AS label,
       avg(CASE WHEN anomaly_dual THEN 1.0 ELSE 0.0 END) AS dual_frac,
       sum(CASE WHEN anomaly_dual THEN 1 ELSE 0 END) AS dual_cnt,
       count(*) AS total,
       avg(mae_a) AS mae_avg
FROM adl_anomaly_results
GROUP BY care_recipient_id
"""


async def select_targets(threshold: float) -> list[dict]:
    """dual 이상 비율 >= threshold 이고 Patient 가 존재하는 대상자 목록을 반환."""
    conn = Tortoise.get_connection("default")
    rows = await conn.execute_query_dict(_AGG_SQL)

    candidates = [r for r in rows if (r["dual_frac"] or 0) >= threshold]

    # FK 연결 가능한(=Patient 존재) 대상자만 남긴다.
    cand_ids = [r["care_recipient_id"] for r in candidates]
    existing = set(await Patient.filter(patient_id__in=cand_ids).values_list("patient_id", flat=True))

    targets = []
    for r in candidates:
        if r["care_recipient_id"] not in existing:
            continue
        targets.append(
            {
                "care_recipient_id": r["care_recipient_id"],
                "label": r["label"],
                "dual_frac": round(float(r["dual_frac"]), 4),
                "dual_cnt": int(r["dual_cnt"]),
                "total": int(r["total"]),
                "mae_avg": round(float(r["mae_avg"]), 4),
            }
        )
    # 강한 이상부터 (비율 → MAE 내림차순)
    targets.sort(key=lambda t: (t["dual_frac"], t["mae_avg"]), reverse=True)
    return targets


async def _main(threshold: float, out: Path) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    targets = await select_targets(threshold)
    await Tortoise.close_connections()

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for t in targets:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    groups = Counter(
        t["care_recipient_id"].split("-")[1] if "-" in t["care_recipient_id"] else "기타"
        for t in targets
    )
    print(f"보고서 대상 (dual 이상 비율 >= {threshold:.0%}): {len(targets)}명")
    for g, n in groups.most_common():
        print(f"  {g}: {n}명")
    print(f"대상 목록 저장 → {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="보고서 생성 대상 수급자 산정")
    p.add_argument("--threshold", type=float, default=0.70, help="dual 이상 비율 임계 (기본 0.70)")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="대상 목록 JSONL 출력 경로")
    args = p.parse_args()
    asyncio.run(_main(args.threshold, args.out))
