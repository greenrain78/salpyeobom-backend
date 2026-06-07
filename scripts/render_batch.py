"""고퀄리티 일괄 렌더러 — LLM 작성 내러티브를 차트/PDF 템플릿에 주입해 생성·등록.

입력:
  - out/batch_inputs.jsonl : 대상(patient_id, cid, date) — prepare_batch 산출
  - out/narratives.jsonl   : 워크플로 서브에이전트가 작성한 내러티브 (patient_id + override 필드)
내러티브는 **patient_id 단독 키**로 매칭한다(날짜는 분산되므로). 샤딩(--shards/--shard)으로
N개 프로세스 병렬 렌더가 가능하고(프로세스 분리라 matplotlib 안전, soffice 프로파일 격리),
이미 등록된 보고서는 건너뛰어 **재개 가능**하다.

사용법:
  USE_REMOTE_DB=1 uv run --with "python-docx,matplotlib" \
      python scripts/render_batch.py [--shards N --shard I]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from tortoise import Tortoise

import scripts.report_generate as rg
from app.core.email import docx_to_pdf
from app.database import TORTOISE_ORM
from app.models.report import Report
from scripts.report_generate import (
    analyze_target,
    build,
    chart_activity,
    chart_selfcare,
    register_report,
    setup_chart_style,
)

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "out" / "batch_inputs.jsonl"
NARRATIVES = ROOT / "out" / "narratives.jsonl"

# build() 가 NARRATIVE 템플릿을 덮어쓰는 데 쓰는 키만 추린다 (그 외는 무시).
_OVERRIDE_KEYS = (
    "event",
    "window",
    "summary",
    "risk_factor",
    "trend_lead",
    "validation_note",
    "recommendations",
)


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


async def _main(shard: int, shards: int) -> None:
    inputs = _load_jsonl(INPUTS)
    narr_by_pid = {n["patient_id"]: n for n in _load_jsonl(NARRATIVES)}

    profile_dir = ROOT / "out" / f".lo_profile_{shard}"  # soffice 프로파일 격리(샤드별)
    profile_dir.mkdir(parents=True, exist_ok=True)
    # 차트 PNG 경로를 샤드별로 분리 (병렬 프로세스 간 동일 파일 덮어쓰기 레이스 방지).
    rg.ASSET_DIR = ROOT / "out" / "reports" / f"assets_shard{shard}"
    rg.ASSET_DIR.mkdir(parents=True, exist_ok=True)

    await Tortoise.init(config=TORTOISE_ORM)
    setup_chart_style()
    ok = skip_done = skip_nonarr = failed = 0
    try:
        for idx, rec in enumerate(inputs):
            if idx % shards != shard:  # 이 샤드 담당분만
                continue
            pid, cid, rec_date = rec["patient_id"], rec["cid"], rec["date"]
            narr = narr_by_pid.get(pid)
            if narr is None:
                skip_nonarr += 1
                continue
            file_name = f"위험예측보고서_{pid}_{rec_date.replace('-', '')}.pdf"
            if await Report.filter(file_name=file_name).exists():  # 재개: 이미 등록됨
                skip_done += 1
                continue
            try:
                an, profile = await analyze_target(pid, cid, None, None)
                profile["narrative"] = {k: narr[k] for k in _OVERRIDE_KEYS if k in narr}
                c1 = chart_activity(an)
                c2 = chart_selfcare(an)
                out = build(
                    an, c1, c2, patient_id=pid,
                    report_date=date.fromisoformat(rec_date), profile=profile,
                )
                try:
                    fname = docx_to_pdf(out, profile_dir=profile_dir).name
                except Exception as err:  # noqa: BLE001
                    print(f"경고: PDF 변환 실패({err}) — docx 등록: {pid}")
                    fname = out.name
                await register_report(
                    pid, f"{pid} 위험예측 보고서", fname,
                    date.fromisoformat(rec_date), profile["variant"],
                )
                ok += 1
                if ok % 25 == 0:
                    print(f"[shard {shard}/{shards}] 진행 {ok}건…")
            except Exception as err:  # noqa: BLE001 — 1건 실패가 샤드 전체를 죽이지 않도록
                print(f"실패 {pid}: {err}")
                failed += 1
    finally:
        await Tortoise.close_connections()
    print(
        f"[shard {shard}/{shards}] 완료 — 성공 {ok}, 이미됨 {skip_done}, "
        f"내러티브없음 {skip_nonarr}, 실패 {failed}"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="고퀄리티 일괄 렌더러 (내러티브 주입)")
    p.add_argument("--shards", type=int, default=1, help="전체 샤드 수(병렬 프로세스 수)")
    p.add_argument("--shard", type=int, default=0, help="이 프로세스의 샤드 인덱스 (0..shards-1)")
    args = p.parse_args()
    asyncio.run(_main(args.shard, args.shards))
