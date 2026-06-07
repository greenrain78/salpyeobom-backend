"""고퀄리티 일괄 생성용 배치 입력 준비기.

out/report_targets.jsonl(select_report_targets 산출)에서 클래스 균형으로 대상을 골라
최근 N일에 분산 배치하고, 각 대상자의 분석 요약(지표)을 덤프해 out/batch_inputs.jsonl 로
저장한다. 이 파일을 워크플로 서브에이전트가 읽어 맞춤 내러티브를 작성한다.

사용법:
  USE_REMOTE_DB=1 uv run --with "python-docx,matplotlib" \
      python scripts/prepare_batch.py [--all | --per-class 20] [--window-days 30] [--end 2026-06-07]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from tortoise import Tortoise

from app.database import TORTOISE_ORM
from scripts.dating import distribute_dates
from scripts.report_generate import analysis_summary, analyze_target

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ROOT / "out" / "report_targets.jsonl"
OUT = ROOT / "out" / "batch_inputs.jsonl"


def _load_targets() -> dict[str, list[dict]]:
    by_risk: dict[str, list[dict]] = {"위험": [], "주의": [], "사망": []}
    for line in TARGETS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec["risk_level"] in by_risk:
            by_risk[rec["risk_level"]].append(rec)
    return by_risk


async def _main(per_class: int, window_days: int, end: date, take_all: bool) -> None:
    by_risk = _load_targets()

    # 대상 선정: --all 이면 전수, 아니면 클래스별 상위 per_class.
    picks_recs: list[dict] = []
    for recs in by_risk.values():
        picks_recs.extend(recs if take_all else recs[:per_class])

    # 생성일(generated_at)을 최근 window_days 에 비균등·결정적 분산 (연출).
    ids = [r["care_recipient_id"] for r in picks_recs]
    date_map = distribute_dates(ids, end, window_days)
    picks = [{**r, "date": date_map[r["care_recipient_id"]]} for r in picks_recs]

    await Tortoise.init(config=TORTOISE_ORM)
    rows = []
    for rec in picks:
        cid = rec["care_recipient_id"]
        try:
            an, profile = await analyze_target(cid, cid, None, None)
        except Exception as err:  # noqa: BLE001
            print(f"건너뜀 {cid}: {err}")
            continue
        rows.append(
            {
                "patient_id": cid,
                "cid": cid,
                "date": rec["date"],
                "summary": analysis_summary(cid, cid, an, profile),
            }
        )
    await Tortoise.close_connections()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"배치 입력 {len(rows)}건 저장 → {OUT}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="고퀄리티 일괄 생성 배치 입력 준비")
    p.add_argument("--all", action="store_true", help="전체 대상 1,363명 (클래스 제한 없음)")
    p.add_argument("--per-class", type=int, default=20, help="클래스별 대상 수 (--all 미지정 시)")
    p.add_argument("--window-days", type=int, default=30, help="생성일 분산 창(최근 일수)")
    p.add_argument("--end", default="2026-06-07", help="분산 종료일 (YYYY-MM-DD)")
    args = p.parse_args()
    asyncio.run(
        _main(args.per_class, args.window_days, date.fromisoformat(args.end), args.all)
    )
