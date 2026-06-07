"""대량 생성 파이프라인 — N명/클래스 × 60일 = adl_raw_records 행 배치 생성.

scenario_gen.generate(서사·일과표) → expander.expand_person(1440배열+스칼라) →
싱크(JSONL 파일 또는 PostgreSQL adl_raw_records).

사용:
  # 클래스별 25명 → 로컬 JSONL (기본, 안전)
  uv run python scripts/synthetic/run_batch.py --per-class 25

  # 클래스별 1000명 → JSONL (전체 산출물 180k행)
  uv run python scripts/synthetic/run_batch.py --per-class 1000 --out out/synthetic/batch.jsonl

  # DB 적재 (원격 공유 DB 에 INSERT — 신중히, 명시적 플래그 필요)
  uv run python scripts/synthetic/run_batch.py --per-class 1000 --sink db

care_recipient_id: SYN-{응급|사망|평소}-{일련번호}. 실데이터(id 1~60)와 source_type
표기는 같지만 care_recipient_id 접두사 'SYN-' 로 합성임을 식별한다.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # 프로젝트 루트 (app import)
from expander import expand_person  # noqa: E402
from scenario_gen import generate  # noqa: E402

CLASSES = ["평시", "응급", "사망"]
SRC = {"평시": "평소", "응급": "응급", "사망": "사망"}


def _iter_rows(per_class: int, seed_base: int, start_date: dt.date):
    """(클래스, 사람index) 순회하며 60행씩 yield."""
    for klass in CLASSES:
        for i in range(per_class):
            seed = seed_base + i
            g = generate(klass, seed)
            rid = f"SYN-{SRC[klass]}-{i:05d}"
            yield klass, rid, expand_person(g, rid, start_date, seed)


def _json_default(o):
    if isinstance(o, dt.date):
        return o.isoformat()
    raise TypeError(type(o))


def run_jsonl(per_class: int, out: Path, seed_base: int, start_date: dt.date) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    t0 = time.time()
    with out.open("w", encoding="utf-8") as f:
        for _klass, _rid, rows in _iter_rows(per_class, seed_base, start_date):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")
                n += 1
    print(f"[jsonl] {n}행 → {out}  ({time.time() - t0:.1f}s, {out.stat().st_size/1e6:.1f}MB)")
    return n


_DATE_COLS = ("lifeog_date", "emergency_date", "death_date")


def _env_database_url() -> str:
    """원격 DB URL — .env 의 DATABASE_URL 을 직접 읽는다(읽기 전용)."""
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(".env 에 DATABASE_URL 이 없습니다")


def _rows_from_jsonl(path: Path, skip: int = 0):
    """JSONL 한 줄 = 행 dict. 날짜 문자열을 date 로 복원해 yield. 앞 skip 줄은 건너뜀."""
    with path.open(encoding="utf-8") as f:
        for _ in range(skip):
            next(f, None)
        for line in f:
            r = json.loads(line)
            for c in _DATE_COLS:
                if r.get(c):
                    r[c] = dt.date.fromisoformat(r[c])
            yield r


def _gen_flat(per_class: int, seed_base: int, start_date: dt.date):
    for _klass, _rid, rows in _iter_rows(per_class, seed_base, start_date):
        yield from rows


async def run_db(rows_iter, db_url: str) -> int:
    from tortoise import Tortoise

    from app.models.adl_raw import AdlRawRecord

    await Tortoise.init(db_url=db_url, modules={"models": ["app.models.adl_raw"]})
    n = 0
    t0 = time.time()
    buf: list[AdlRawRecord] = []
    for r in rows_iter:
        buf.append(AdlRawRecord(**r))
        if len(buf) >= 1000:
            await AdlRawRecord.bulk_create(buf)
            n += len(buf)
            buf = []
            print(f"  …{n}행 적재", flush=True)
    if buf:
        await AdlRawRecord.bulk_create(buf)
        n += len(buf)
    await Tortoise.close_connections()
    print(f"[db] {n}행 INSERT → {db_url.split('@')[-1]}  ({time.time() - t0:.1f}s)")
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=25)
    ap.add_argument("--sink", choices=["jsonl", "db"], default="jsonl")
    ap.add_argument("--out", type=Path, default=Path("out/synthetic/batch.jsonl"))
    ap.add_argument("--from-jsonl", type=Path, default=None,
                    help="sink=db 일 때 생성 대신 기존 JSONL 을 적재 (파일=DB 일치 보장)")
    ap.add_argument("--skip-lines", type=int, default=0,
                    help="--from-jsonl 적재 시 앞 N 줄 건너뜀 (이미 적재된 행 재적재 방지)")
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--start-date", default="2024-05-01")
    ap.add_argument("--db-url", default=None,
                    help="적재 대상 DB URL. 미지정 시 .env 의 DATABASE_URL(원격) 사용")
    args = ap.parse_args()
    start = dt.date.fromisoformat(args.start_date)

    if args.sink == "jsonl":
        total = args.per_class * len(CLASSES)
        print(f"생성: 클래스별 {args.per_class}명 ({total}명 × 60일 = {total*60}행) → jsonl")
        run_jsonl(args.per_class, args.out, args.seed_base, start)
        return

    # 원격 적재 대상: .env 의 DATABASE_URL(원격). settings 는 .env.local 의 로컬 URL 이
    # 우선되므로 사용하지 않고 .env 를 직접 읽는다(읽기 전용 — 수정 아님).
    db_url = args.db_url or _env_database_url()
    if args.from_jsonl:
        print(f"적재: {args.from_jsonl} (앞 {args.skip_lines}줄 skip) → DB {db_url.split('@')[-1]}")
        rows = _rows_from_jsonl(args.from_jsonl, skip=args.skip_lines)
    else:
        total = args.per_class * len(CLASSES)
        print(f"생성+적재: 클래스별 {args.per_class}명 ({total*60}행) → DB {db_url.split('@')[-1]}")
        rows = _gen_flat(args.per_class, args.seed_base, start)
    asyncio.run(run_db(rows, db_url))


if __name__ == "__main__":
    main()
