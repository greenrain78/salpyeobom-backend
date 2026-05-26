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
from app.models.patient import Patient, Situation, SituationAction

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
        "doc_no": "NO.2026-04-08-001",
        "manager_name": "김재섭 주무관",
        "management_level": "집중 관리군 (1등급)",
        "diseases": ["고혈압", "초기 치매", "관절염"],
        "next_visit_time": "2026.04.10 (금) 14:00",
        "next_visit_plan": "정기 혈압 체크 및 스마트 플러그 점검",
    },
    {
        "patient_id": "user_1002",
        "name": "최갑수",
        "age": 82,
        "address_full": "서울특별시 노원구 상계동 45-1 행복아파트 305호",
        "address_summary": "상계동 45-1",
        "doc_no": "NO.2026-04-08-002",
        "manager_name": "이수진 주무관",
        "management_level": "일반 관리군 (2등급)",
        "diseases": ["당뇨", "고지혈증"],
        "next_visit_time": "2026.04.12 (일) 10:00",
        "next_visit_plan": "혈당 측정 및 식이 상담",
    },
    {
        "patient_id": "user_1003",
        "name": "박영희",
        "age": 75,
        "address_full": "서울특별시 노원구 중계동 78-2 청솔빌라 102호",
        "address_summary": "중계동 78-2",
        "doc_no": "NO.2026-04-08-003",
        "manager_name": "박민준 주무관",
        "management_level": "자립 관리군 (3등급)",
        "diseases": ["골다공증"],
        "next_visit_time": "2026.04.15 (수) 11:00",
        "next_visit_plan": "낙상 예방 운동 안내",
    },
    {
        "patient_id": "user_1004",
        "name": "이정호",
        "age": 80,
        "address_full": "서울특별시 노원구 하계동 22-9 미래빌 401호",
        "address_summary": "하계동 22-9",
        "doc_no": "NO.2026-04-08-004",
        "manager_name": "김재섭 주무관",
        "management_level": "일반 관리군 (2등급)",
        "diseases": ["고혈압", "심부전"],
        "next_visit_time": "2026.04.11 (토) 13:00",
        "next_visit_plan": "심전도 측정 장비 점검",
    },
    {
        "patient_id": "user_1005",
        "name": "윤말순",
        "age": 88,
        "address_full": "서울특별시 노원구 월계동 34-5 한빛주택 1층",
        "address_summary": "월계동 34-5",
        "doc_no": "NO.2026-04-08-005",
        "manager_name": "이수진 주무관",
        "management_level": "집중 관리군 (1등급)",
        "diseases": ["중기 치매", "고혈압", "신부전"],
        "next_visit_time": "2026.04.09 (목) 09:00",
        "next_visit_plan": "인지 기능 검사 및 투약 확인",
    },
    {
        "patient_id": "user_1006",
        "name": "강병철",
        "age": 71,
        "address_full": "서울특별시 노원구 공릉동 55-3 늘푸른빌라 203호",
        "address_summary": "공릉동 55-3",
        "doc_no": "NO.2026-04-08-006",
        "manager_name": "박민준 주무관",
        "management_level": "자립 관리군 (3등급)",
        "diseases": ["관절염"],
        "next_visit_time": "2026.04.17 (금) 15:00",
        "next_visit_plan": "활동 보조 기기 점검",
    },
]

SITUATIONS = [
    {
        "patient_id": "user_1001",
        "category": "낙상 의심",
        "detail_reason": "거실 센서 가속도 변화 감지.",
        "occurred_at": datetime(2026, 4, 8, 11, 33, 45, tzinfo=UTC),
        "action_status": "현장 출동",
        "is_active": True,
    },
    {
        "patient_id": "user_1002",
        "category": "미응답",
        "detail_reason": "최근 3시간 활동량 데이터 미수신.",
        "occurred_at": datetime(2026, 4, 8, 10, 12, 5, tzinfo=UTC),
        "action_status": "조치 대기",
        "is_active": True,
    },
    {
        "patient_id": "user_1005",
        "category": "미응답",
        "detail_reason": "오전 투약 알림 미확인 2회 연속.",
        "occurred_at": datetime(2026, 4, 7, 9, 5, 0, tzinfo=UTC),
        "action_status": "조치 완료",
        "is_active": False,
    },
]

ACTIONS = [
    {
        "situation_index": 2,  # user_1005의 상황 (조치 완료)
        "action_type": "유선 연락",
        "action_note": "오전 투약 후 수면 중임을 유선으로 확인 완료. 특이사항 없음.",
        "status_update": "조치 완료",
    },
]


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------


async def seed(reset: bool = False) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

    if reset:
        await SituationAction.all().delete()
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
    situations_objs = []
    created_situations = 0
    for data in SITUATIONS:
        patient = await Patient.get(patient_id=data["patient_id"])
        situation, created = await Situation.get_or_create(
            patient=patient,
            occurred_at=data["occurred_at"],
            defaults={k: v for k, v in data.items() if k != "patient_id"},
        )
        situations_objs.append(situation)
        if created:
            created_situations += 1

    print(f"상황: {created_situations}건 생성 (총 {await Situation.all().count()}건)")

    # 조치 기록
    created_actions = 0
    for data in ACTIONS:
        situation = situations_objs[data["situation_index"]]
        _, created = await SituationAction.get_or_create(
            situation=situation,
            action_type=data["action_type"],
            defaults={
                "action_note": data["action_note"],
                "status_update": data["status_update"],
            },
        )
        if created:
            created_actions += 1

    print(f"조치 기록: {created_actions}건 생성")
    print("시드 완료")

    await Tortoise.close_connections()


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    asyncio.run(seed(reset=reset))
