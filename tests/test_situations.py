from datetime import UTC, datetime

from httpx import AsyncClient

from app.models.patient import Patient, Situation, SituationAction

ACTIVE_URL = "/api/v1/situations/active"


async def _make_patient(pid: str = "p1") -> Patient:
    return await Patient.create(
        patient_id=pid,
        name="김순자",
        age=78,
        address_full="서울시 노원구 상계동 123-4",
        address_summary="상계동 123-4",
    )


async def _make_situation(patient: Patient, **kwargs) -> Situation:
    return await Situation.create(
        patient=patient,
        category=kwargs.get("category", "미응답"),
        detail_reason=kwargs.get("detail_reason", "테스트 사유"),
        occurred_at=kwargs.get("occurred_at", datetime(2026, 4, 8, 10, 12, 5, tzinfo=UTC)),
        action_status=kwargs.get("action_status", "조치 대기"),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/situations/active
# ---------------------------------------------------------------------------


async def test_active_situations_empty(auth_client: AsyncClient):
    res = await auth_client.get(ACTIVE_URL)
    assert res.status_code == 200
    assert res.json()["data"]["situations"] == []


async def test_active_situations_returns_active_only(auth_client: AsyncClient):
    patient = await _make_patient()
    await _make_situation(patient, action_status="조치 대기")
    await _make_situation(patient, action_status="조치 완료")

    res = await auth_client.get(ACTIVE_URL)
    assert len(res.json()["data"]["situations"]) == 1


async def test_active_situations_fields(auth_client: AsyncClient):
    patient = await _make_patient()
    await _make_situation(
        patient, category="낙상 의심", occurred_at=datetime(2026, 4, 8, 11, 33, 45, tzinfo=UTC)
    )

    item = (
        res.json()["data"]["situations"][0] if (res := await auth_client.get(ACTIVE_URL)) else None
    )
    assert item["patient_id"] == "p1"
    assert item["name"] == "김순자"
    assert item["category"] == "낙상 의심"
    assert item["occurred_at"] == "11:33:45"
    assert item["action_status"] == "조치 대기"
    assert "hashed_password" not in item


async def test_active_situations_limit(auth_client: AsyncClient):
    patient = await _make_patient()
    for _ in range(5):
        await _make_situation(patient)

    res = await auth_client.get(ACTIVE_URL, params={"limit": 3})
    assert len(res.json()["data"]["situations"]) == 3


# ---------------------------------------------------------------------------
# POST /api/v1/situations/{situation_id}/actions
# ---------------------------------------------------------------------------


async def test_create_action_success(auth_client: AsyncClient):
    patient = await _make_patient()
    situation = await _make_situation(patient)

    res = await auth_client.post(
        f"/api/v1/situations/{situation.situation_id}/actions",
        json={"action_type": "유선 연락", "action_note": "확인 완료", "status_update": "조치 완료"},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "success"


async def test_create_action_updates_status(auth_client: AsyncClient):
    patient = await _make_patient()
    situation = await _make_situation(patient)

    await auth_client.post(
        f"/api/v1/situations/{situation.situation_id}/actions",
        json={"action_type": "현장 출동", "status_update": "현장 출동"},
    )
    await situation.refresh_from_db()
    assert situation.action_status == "현장 출동"


async def test_create_action_saves_record(auth_client: AsyncClient):
    patient = await _make_patient()
    situation = await _make_situation(patient)

    await auth_client.post(
        f"/api/v1/situations/{situation.situation_id}/actions",
        json={"action_type": "기타", "action_note": "메모", "status_update": "조치 완료"},
    )
    action = await SituationAction.filter(situation=situation).first()
    assert action is not None
    assert action.action_type == "기타"
    assert action.action_note == "메모"


async def test_create_action_not_found(auth_client: AsyncClient):
    res = await auth_client.post(
        "/api/v1/situations/99999/actions",
        json={"action_type": "기타", "status_update": "조치 완료"},
    )
    assert res.status_code == 404


async def test_create_action_invalid_type(auth_client: AsyncClient):
    patient = await _make_patient()
    situation = await _make_situation(patient)

    res = await auth_client.post(
        f"/api/v1/situations/{situation.situation_id}/actions",
        json={"action_type": "알수없음", "status_update": "조치 완료"},
    )
    assert res.status_code == 422
