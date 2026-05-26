"""
더미 데이터 생성 스크립트
사용법: uv run python scripts/seed.py [--reset]
  --reset: 기존 데이터 삭제 후 재생성
"""

import asyncio
import sys
from datetime import UTC, datetime

from tortoise import Tortoise

sys.path.insert(0, ".")
from app.database import TORTOISE_ORM
from app.models.patient import Patient, Situation

# ---------------------------------------------------------------------------
# 더미 데이터 정의
# ---------------------------------------------------------------------------

PATIENTS = [
    {
        "patient_id": "user_1001",
        "name": "김순자",
        "age": 78,
        "address_full": "서울특별시 노원구 상계동 123-4 사랑빌라 201호",
        "address_summary": "상계동 123-4",
        "manager_name": "김재섭 주무관",
        "management_level": "집중 관리군 (1등급)",
        "diseases": ["고혈압", "초기 치매", "관절염"],
    },
    {
        "patient_id": "user_1002",
        "name": "최갑수",
        "age": 82,
        "address_full": "서울특별시 노원구 상계동 45-1 행복아파트 305호",
        "address_summary": "상계동 45-1",
        "manager_name": "이수진 주무관",
        "management_level": "일반 관리군 (2등급)",
        "diseases": ["당뇨", "고지혈증"],
    },
    {
        "patient_id": "user_1003",
        "name": "박영희",
        "age": 75,
        "address_full": "서울특별시 노원구 중계동 78-2 청솔빌라 102호",
        "address_summary": "중계동 78-2",
        "manager_name": "박민준 주무관",
        "management_level": "자립 관리군 (3등급)",
        "diseases": ["골다공증"],
    },
    {
        "patient_id": "user_1004",
        "name": "이정호",
        "age": 80,
        "address_full": "서울특별시 노원구 하계동 22-9 미래빌 401호",
        "address_summary": "하계동 22-9",
        "manager_name": "김재섭 주무관",
        "management_level": "일반 관리군 (2등급)",
        "diseases": ["고혈압", "심부전"],
    },
    {
        "patient_id": "user_1005",
        "name": "윤말순",
        "age": 88,
        "address_full": "서울특별시 노원구 월계동 34-5 한빛주택 1층",
        "address_summary": "월계동 34-5",
        "manager_name": "이수진 주무관",
        "management_level": "집중 관리군 (1등급)",
        "diseases": ["중기 치매", "고혈압", "신부전"],
    },
    {
        "patient_id": "user_1006",
        "name": "강병철",
        "age": 71,
        "address_full": "서울특별시 노원구 공릉동 55-3 늘푸른빌라 203호",
        "address_summary": "공릉동 55-3",
        "manager_name": "박민준 주무관",
        "management_level": "자립 관리군 (3등급)",
        "diseases": ["관절염"],
    },
]

SITUATIONS = [
    {
        "patient_id": "user_1001",
        "category": "낙상 의심",
        "detail_reason": "거실 센서 가속도 변화 감지.",
        "occurred_at": datetime(2026, 4, 8, 11, 33, 45, tzinfo=UTC),
        "action_status": "현장 출동",
    },
    {
        "patient_id": "user_1002",
        "category": "미응답",
        "detail_reason": "최근 3시간 활동량 데이터 미수신.",
        "occurred_at": datetime(2026, 4, 8, 10, 12, 5, tzinfo=UTC),
        "action_status": "조치 대기",
    },
    {
        "patient_id": "user_1005",
        "category": "미응답",
        "detail_reason": "오전 투약 알림 미확인 2회 연속.",
        "occurred_at": datetime(2026, 4, 7, 9, 5, 0, tzinfo=UTC),
        "action_status": "조치 완료",
    },
]

# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------


async def seed(reset: bool = False) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

    if reset:
        await Situation.all().delete()
        await Patient.all().delete()
        print("기존 데이터 삭제 완료")

    # 환자
    created_patients = 0
    for data in PATIENTS:
        _, created = await Patient.get_or_create(patient_id=data["patient_id"], defaults=data)
        if created:
            created_patients += 1

    print(f"환자: {created_patients}명 생성 (총 {await Patient.all().count()}명)")

    # 상황
    created_situations = 0
    for data in SITUATIONS:
        patient = await Patient.get(patient_id=data["patient_id"])
        _, created = await Situation.get_or_create(
            patient=patient,
            occurred_at=data["occurred_at"],
            defaults={k: v for k, v in data.items() if k != "patient_id"},
        )
        if created:
            created_situations += 1

    print(f"상황: {created_situations}건 생성 (총 {await Situation.all().count()}건)")
    print("시드 완료")

    await Tortoise.close_connections()


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    asyncio.run(seed(reset=reset))
