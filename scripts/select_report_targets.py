"""보고서 생성 대상 수급자 산정기 (AI 이상탐지 기반 분류).

`adl_anomaly_results` 의 그룹(label)과 dual 이상 비율로 위험/주의/사망을 분류한다
(`app/services/reports.py:classify`):
  - 사망 그룹 → 사망 (전수)
  - 응급 그룹 → dual ≥0.75 위험, ≥0.70 주의, 그 외 제외
  - 평소 등 → 제외
FK 연결을 위해 `patients` 에 존재하는 대상자로 한정한다.

`adl_anomaly_results` 는 매핑/PK 없는 분석 산출물 테이블이라 이 유틸에서만 읽기 전용
집계 쿼리로 접근한다(앱 런타임 아님). 환자 존재 확인은 ORM(`Patient`).

사용법:
  USE_REMOTE_DB=1 uv run python scripts/select_report_targets.py [--out out/report_targets.jsonl]
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
from app.services.reports import classify

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "report_targets.jsonl"

# 수급자별 dual 이상 비율·라벨 집계 (읽기 전용). 매핑/PK 없는 테이블이라 raw SELECT 사용.
_AGG_SQL = """
SELECT care_recipient_id,
       max(label) AS label,
       avg(CASE WHEN anomaly_dual THEN 1.0 ELSE 0.0 END) AS dual_frac,
       avg(mae_a) AS mae_avg
FROM adl_anomaly_results
GROUP BY care_recipient_id
"""


async def select_targets() -> list[dict]:
    """classify 로 위험/주의/사망 분류되고 Patient 가 존재하는 대상자 목록을 반환."""
    conn = Tortoise.get_connection("default")
    rows = await conn.execute_query_dict(_AGG_SQL)

    classified = []
    for r in rows:
        risk = classify(r["label"], r["dual_frac"])
        if risk is None:
            continue
        classified.append({**r, "risk_level": risk})

    # FK 연결 가능한(=Patient 존재) 대상자만 남긴다.
    ids = [r["care_recipient_id"] for r in classified]
    existing = set(await Patient.filter(patient_id__in=ids).values_list("patient_id", flat=True))

    targets = [
        {
            "care_recipient_id": r["care_recipient_id"],
            "risk_level": r["risk_level"],
            "label": r["label"],
            "dual_frac": round(float(r["dual_frac"]), 4),
            "mae_avg": round(float(r["mae_avg"]), 4),
        }
        for r in classified
        if r["care_recipient_id"] in existing
    ]
    # 강한 이상부터 (비율 → MAE 내림차순)
    targets.sort(key=lambda t: (t["dual_frac"], t["mae_avg"]), reverse=True)
    return targets


async def _main(out: Path) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    targets = await select_targets()
    await Tortoise.close_connections()

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for t in targets:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    counts = Counter(t["risk_level"] for t in targets)
    print(f"보고서 대상: {len(targets)}명")
    for risk in ("위험", "주의", "사망"):
        print(f"  {risk}: {counts.get(risk, 0)}명")
    print(f"대상 목록 저장 → {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="보고서 생성 대상 수급자 산정 (이상탐지 기반 분류)")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="대상 목록 JSONL 출력 경로")
    args = p.parse_args()
    asyncio.run(_main(args.out))
