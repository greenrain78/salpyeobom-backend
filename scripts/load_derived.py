"""data/derived/patients.jsonl → DB 적재기 (시더 아님, 순수 로더).

사용법: uv run python scripts/load_derived.py [경로]

파생 로직이 전혀 없다. adl_raw_records 에서 파생된 Patient/Situation 데이터는
서브에이전트가 오프라인 1회 생성해 `data/derived/patients.jsonl` 로 고정·커밋했고,
이 스크립트는 그 JSONL 을 읽어 ORM 으로 적재만 한다.

멱등·비파괴:
- Patient 는 `update_or_create(patient_id=…)` 로 upsert (다른 환자·users·adl_raw_records 불변).
- Situations 는 해당 환자분의 기존 행을 지우고 JSONL 의 상황으로 새로고침.

JSONL 1줄 = 대상자 1명:
    {"patient_id": "...", "name": "...", "age": 83, "address_full": "...",
     "address_summary": "...", "phone_number": null,
     "manager_name": "...", "management_level": "...", "diseases": ["..."],
     "cross_verification_level": "A"|"B"|"C"|null,
     "ai_alert_title": "...", "ai_alert_desc": "...",
     "doc_no": "...", "next_visit_time": "...", "next_visit_plan": "...",
     "profile_image_url": null,
     "situations": [
        {"category": "낙상 의심", "detail_reason": "...",
         "occurred_at": "2026-06-06T22:30:00+00:00", "action_status": "조치 대기"}
     ]}
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from tortoise import Tortoise

sys.path.insert(0, ".")
from app.database import TORTOISE_ORM
from app.models.enums import ActionStatus
from app.models.patient import Patient, Situation

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "data" / "derived" / "patients.jsonl"

# Patient 모델로 그대로 매핑되는 컬럼들 (situations 는 별도 처리).
_PATIENT_FIELDS = (
    "name",
    "age",
    "address_full",
    "address_summary",
    "phone_number",
    "manager_name",
    "management_level",
    "diseases",
    "cross_verification_level",
    "ai_alert_title",
    "ai_alert_desc",
    "doc_no",
    "next_visit_time",
    "next_visit_plan",
    "profile_image_url",
)


def parse_records(path: Path) -> list[dict]:
    """JSONL 을 한 줄씩 파싱. 빈 줄은 건너뛴다."""
    records: list[dict] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


async def load_record(record: dict) -> int:
    """대상자 1명을 적재. 생성/갱신된 상황 건수를 반환.

    레코드에 `situations` 키가 **있을 때만** 해당 환자분의 상황을 새로고침한다
    (지우고 재구성). 키가 없으면 기존 상황은 그대로 보존한다 — 이미 양호한 상황
    데이터가 있는 DB에 7개 파생 컬럼만 덧입힐 때 쓰는 경로(환자 필드만 upsert).
    """
    patient_id = record["patient_id"]
    defaults = {f: record[f] for f in _PATIENT_FIELDS if f in record}
    patient, _ = await Patient.update_or_create(patient_id=patient_id, defaults=defaults)

    if "situations" not in record:
        return 0  # 상황 미지정 → 기존 상황 보존(필드만 보강)

    # 상황 새로고침 — 이 환자분의 기존 상황만 비우고 JSONL 의 상황으로 재구성.
    await Situation.filter(patient=patient).delete()
    situations = record["situations"] or []
    for s in situations:
        await Situation.create(
            patient=patient,
            category=s["category"],
            detail_reason=s.get("detail_reason"),
            occurred_at=datetime.fromisoformat(s["occurred_at"]),
            action_status=ActionStatus(s["action_status"]),
        )
    return len(situations)


async def load_derived(path: Path = DEFAULT_JSONL) -> tuple[int, int]:
    """JSONL 전체를 적재. (환자 수, 상황 수) 반환."""
    records = parse_records(path)
    situation_count = 0
    for record in records:
        situation_count += await load_record(record)
    return len(records), situation_count


async def _main(path: Path) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    patients, situations = await load_derived(path)
    print(f"적재 완료 — 환자 {patients}명, 상황 {situations}건 ({path})")
    await Tortoise.close_connections()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSONL
    asyncio.run(_main(target))
