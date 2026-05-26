"""UAT (User Acceptance Tests) — end-to-end user journey scenarios.

These tests exercise the full request flow as a real user would, chaining
multiple endpoints and verifying that the system holds together for three
primary personas:

  Scenario 1 — 모니터링 담당자 신규 가입 → 로그인 → 대시보드 확인
  Scenario 2 — 환자 케어 흐름 (검색 → 상세 → 상황 목록)
  Scenario 3 — ADL 원시 데이터 분석 흐름 (필터 조회 → 상세 분석)
"""

from datetime import UTC, date, datetime

from httpx import AsyncClient

from app.models.adl_raw import AdlRawRecord
from app.models.patient import Patient, Situation

# ───────────────────────────────────────────────────────────────────────────
# Scenario 1: 담당자 신규 가입 → 로그인 → 대시보드 확인
# ───────────────────────────────────────────────────────────────────────────


async def test_uat_scenario_1_new_user_onboarding(client: AsyncClient) -> None:
    """주요 흐름: 신규 담당자가 가입하고 로그인해 대시보드 요약을 본다."""

    # Arrange — 대시보드에 노출될 환자를 미리 등록
    await Patient.create(
        patient_id="onboarding_demo",
        name="박노인",
        age=82,
        address_full="서울특별시 노원구 상계동 1-1",
        address_summary="상계동 1-1",
    )

    # Act 1 — 회원가입
    register_res = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newcaretaker",
            "email": "caretaker@example.com",
            "password": "uat-pass-1234",
        },
    )

    # Assert 1 — 가입 성공 (201) 응답이 hashed_password 노출 안 함
    assert register_res.status_code == 201, register_res.text
    body = register_res.json()
    assert body["username"] == "newcaretaker"
    assert "hashed_password" not in body

    # Act 2 — 로그인
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username": "newcaretaker", "password": "uat-pass-1234"},
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]

    # Act 3 — 인증된 호출로 /me, /dashboard/summary 확인
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    summary_res = await client.get("/api/v1/dashboard/summary", headers=headers)

    # Assert 2/3 — 본인 정보와 대시보드 카운트가 정상
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "newcaretaker"
    assert summary_res.status_code == 200
    assert summary_res.json()["data"]["total_monitoring_count"] == 1


# ───────────────────────────────────────────────────────────────────────────
# Scenario 2: 환자 케어 흐름
# ───────────────────────────────────────────────────────────────────────────


async def test_uat_scenario_2_patient_care_flow(auth_client: AsyncClient) -> None:
    """주요 흐름: 환자 목록 검색 → 상세 조회 → 활성 상황 확인."""

    # Arrange — 환자 2명과 진행 중 상황 1건, 종료 상황 1건
    p1 = await Patient.create(
        patient_id="care_001",
        name="김순자",
        age=78,
        address_full="서울특별시 노원구 상계동 1",
        address_summary="상계동 1",
        manager_name="김재섭",
        management_level="집중 관리군 (1등급)",
        diseases=["고혈압", "당뇨"],
    )
    await Patient.create(
        patient_id="care_002",
        name="최갑수",
        age=80,
        address_full="서울특별시 노원구 상계동 2",
        address_summary="상계동 2",
    )
    await Situation.create(
        patient=p1,
        category="미응답",
        detail_reason="3시간 미응답",
        occurred_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=UTC),
        action_status="조치 대기",
    )
    await Situation.create(
        patient=p1,
        category="낙상 의심",
        detail_reason="가속도 센서 임계 초과",
        occurred_at=datetime(2026, 4, 1, 9, 0, 0, tzinfo=UTC),
        action_status="조치 완료",
    )

    # Act 1 — 이름 검색
    search_res = await auth_client.get("/api/v1/patients", params={"search_name": "김"})
    assert search_res.status_code == 200
    found = search_res.json()["data"]
    assert found["total_count"] == 1
    assert found["patients"][0]["patient_id"] == "care_001"

    # Act 2 — 상세 조회
    detail_res = await auth_client.get("/api/v1/patients/care_001/details")
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["age"] == "만 78세"
    assert detail["administration"]["diseases"] == ["고혈압", "당뇨"]

    # Act 3 — 활성 상황만 노출되는지
    sit_res = await auth_client.get("/api/v1/situations/active")
    assert sit_res.status_code == 200
    situations = sit_res.json()["data"]["situations"]
    assert len(situations) == 1
    assert situations[0]["category"] == "미응답"
    assert situations[0]["action_status"] == "조치 대기"


# ───────────────────────────────────────────────────────────────────────────
# Scenario 3: ADL 원시 데이터 분석 흐름
# ───────────────────────────────────────────────────────────────────────────


async def test_uat_scenario_3_adl_analysis_flow(auth_client: AsyncClient) -> None:
    """주요 흐름: ADL 원시 데이터 다건 필터 조회 → 특정 레코드 상세 → 24시간 외출 변환.

    NOTE: PostgreSQL ArrayField 컬럼은 SQLite 테스트 환경에서 INSERT 가 불가하므로,
    DB 단계에서는 스칼라 필드만 채우고 24h 변환 계약은 transform 함수를 직접 호출해 검증한다.
    """
    from app.services.adl_raw_transform import (
        aggregate_outgoing_to_24h,
        recount_outgoing_count_d,
    )

    # Arrange — 3건 (응급 2, 사망 1). 모두 스칼라 필드만 사용.
    target = await AdlRawRecord.create(
        source_type="응급",
        care_recipient_id="UAT-001",
        age=82,
        sex="F",
        alone="Y",
        district="노원구",
        lifeog_date=date(2026, 3, 10),
        aix_d=2.4,
        total_aix_sum=120.0,
        night_aix_ratio=0.45,
        total_sleep_period=6.5,
    )
    await AdlRawRecord.create(
        source_type="응급",
        care_recipient_id="UAT-002",
        age=70,
        sex="M",
        alone="N",
        district="강남구",
        lifeog_date=date(2026, 3, 11),
    )
    await AdlRawRecord.create(
        source_type="사망",
        care_recipient_id="UAT-003",
        age=90,
        sex="F",
        alone="Y",
        district="노원구",
        lifeog_date=date(2026, 3, 12),
    )

    # Act 1 — 필터: 노원구 + 응급 → UAT-001 한 명만
    list_res = await auth_client.get(
        "/api/v1/adl-raw/recipients",
        params={"district": "노원구", "source_type": "응급"},
    )
    assert list_res.status_code == 200
    listing = list_res.json()["data"]
    assert listing["total"] == 1
    assert listing["items"][0]["care_recipient_id"] == "UAT-001"
    assert listing["items"][0]["source_type_counts"] == {"응급": 1}
    assert listing["items"][0]["total_records"] == 1

    # Act 2 — 상세 조회
    detail_res = await auth_client.get(f"/api/v1/adl-raw/{target.id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["id"] == target.id
    assert detail["aix_d"] == 2.4
    assert detail["total_aix_sum"] == 120.0
    assert detail["night_aix_ratio"] == 0.45

    # Act 3 — 24h 외출 변환 계약 직접 검증 (라우터가 동일 함수를 사용)
    outgoing_minutes = [0] * 1440
    outgoing_minutes[0] = 5  # hour 0 +5
    outgoing_minutes[60] = 3  # hour 1 +3
    outgoing_minutes[120] = 254  # sentinel — 정제 후 0
    outgoing_minutes[121] = 255  # sentinel — 정제 후 0

    outgoing_24h = aggregate_outgoing_to_24h(outgoing_minutes)
    assert outgoing_24h is not None
    assert len(outgoing_24h) == 24
    assert outgoing_24h[0] == 5
    assert outgoing_24h[1] == 3
    assert sum(outgoing_24h[2:]) == 0

    assert recount_outgoing_count_d(outgoing_minutes) == 2
