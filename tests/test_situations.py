from datetime import UTC, datetime

from httpx import AsyncClient

from app.models.patient import Patient, Situation

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

    res = await auth_client.get(ACTIVE_URL)
    assert res.status_code == 200
    item = res.json()["data"]["situations"][0]
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
