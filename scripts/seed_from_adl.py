"""adl_raw_records 기반 Patient/Situation 파생 시드 스크립트.

사용법: uv run python scripts/seed_from_adl.py

매 실행마다 patients / situations 테이블을 비우고 adl_raw_records 로부터 재구성한다.
users 와 adl_raw_records 테이블 자체는 건드리지 않는다. 멱등.

매핑:
- care_recipient_id 그룹당 1 Patient (patient_id = name = care_recipient_id)
- source_type in ("응급","사망") 행 중 같은 (recipient_id, date) 쌍당 1 Situation
- Situation.detail_reason 은 emergency_record / death_record 원본 텍스트 그대로
- Situation.action_status 는 "조치 완료" 고정 (과거 사건이므로 /active 에 안 잡힘)
"""

import asyncio
import sys
from datetime import UTC, date, datetime, time

from tortoise import Tortoise

sys.path.insert(0, ".")
from app.database import TORTOISE_ORM
from app.models.adl_raw import AdlRawRecord
from app.models.enums import ActionStatus
from app.models.patient import Patient, Situation


def _build_address(district: str | None, house: str | None, room: int | None) -> tuple[str, str]:
    """address_full, address_summary 생성. 두 필드 모두 NOT NULL."""
    district = district or "미상"
    room_str = f"{room}호" if room is not None else ""
    house = house or ""
    full_parts = [district, house, room_str]
    full = " ".join(p for p in full_parts if p).strip() or district
    summary = f"{district} {room_str}".strip() if room_str else district
    return full, summary


async def seed_from_adl() -> None:
    await Tortoise.init(config=TORTOISE_ORM)

    # 1) patients / situations 초기화 (users, adl_raw_records 는 건드리지 않음)
    await Situation.all().delete()
    await Patient.all().delete()

    # 2) adl_raw_records 조회 후 care_recipient_id 별 그룹화
    records = await AdlRawRecord.all()
    by_recipient: dict[str, list[AdlRawRecord]] = {}
    for r in records:
        by_recipient.setdefault(r.care_recipient_id, []).append(r)

    # 3) Patient 생성 — 1 그룹당 1행
    created_patients = 0
    for recipient_id, rows in by_recipient.items():
        sample = rows[0]
        age = next((r.age for r in rows if r.age is not None), 0)
        address_full, address_summary = _build_address(
            sample.district, sample.house_structure, sample.room_no
        )
        await Patient.create(
            patient_id=recipient_id,
            name=recipient_id,
            age=age,
            address_full=address_full,
            address_summary=address_summary,
            diseases=[],
        )
        created_patients += 1

    # 4) Situation 생성 — source_type in ("응급","사망") 행 중 (recipient, category, date) 1쌍당 1건
    seen: set[tuple[str, str, date]] = set()
    created_situations = 0
    for r in records:
        if r.source_type == "응급" and r.emergency_date is not None:
            key = (r.care_recipient_id, "응급", r.emergency_date)
            if key in seen:
                continue
            seen.add(key)
            patient = await Patient.get(patient_id=r.care_recipient_id)
            await Situation.create(
                patient=patient,
                category="응급",
                detail_reason=r.emergency_record,
                occurred_at=datetime.combine(r.emergency_date, time(0, 0), tzinfo=UTC),
                action_status=ActionStatus.COMPLETED,
            )
            created_situations += 1
        elif r.source_type == "사망" and r.death_date is not None:
            key = (r.care_recipient_id, "사망", r.death_date)
            if key in seen:
                continue
            seen.add(key)
            patient = await Patient.get(patient_id=r.care_recipient_id)
            await Situation.create(
                patient=patient,
                category="사망",
                detail_reason=r.death_record,
                occurred_at=datetime.combine(r.death_date, time(0, 0), tzinfo=UTC),
                action_status=ActionStatus.COMPLETED,
            )
            created_situations += 1

    print(f"환자: {created_patients}명 생성")
    print(f"상황: {created_situations}건 생성")
    print("시드 완료")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed_from_adl())
