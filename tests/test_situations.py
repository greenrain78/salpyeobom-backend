from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.models.enums import ActionStatus
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


async def test_situation_is_active_derived_from_action_status(auth_client: AsyncClient):
    # Arrange — is_active is a derived property: active unless COMPLETED.
    patient = await _make_patient()
    pending = await _make_situation(patient, action_status=ActionStatus.PENDING)
    dispatched = await _make_situation(patient, action_status=ActionStatus.DISPATCHED)
    completed = await _make_situation(patient, action_status=ActionStatus.COMPLETED)

    # Assert
    assert pending.is_active is True
    assert dispatched.is_active is True
    assert completed.is_active is False


async def test_situation_rejects_invalid_action_status(auth_client: AsyncClient):
    # Arrange / Act / Assert — CharEnumField enforces the closed value set at write time.
    patient = await _make_patient()
    with pytest.raises(ValueError):
        await _make_situation(patient, action_status="존재하지 않는 상태")


async def test_active_situations_pagination_offset(auth_client: AsyncClient):
    # Arrange — 5 active situations with distinct, descending occurred_at order
    patient = await _make_patient()
    for i in range(5):
        await _make_situation(patient, occurred_at=datetime(2026, 4, 8, 10, i, 0, tzinfo=UTC))

    # Act — page 1 (limit 2) and page 2 (limit 2) must not overlap
    page1 = await auth_client.get(ACTIVE_URL, params={"page": 1, "limit": 2})
    page2 = await auth_client.get(ACTIVE_URL, params={"page": 2, "limit": 2})

    # Assert
    assert page1.status_code == 200 and page2.status_code == 200
    ids1 = [s["situation_id"] for s in page1.json()["data"]["situations"]]
    ids2 = [s["situation_id"] for s in page2.json()["data"]["situations"]]
    assert len(ids1) == 2 and len(ids2) == 2
    assert set(ids1).isdisjoint(ids2)


# ---------------------------------------------------------------------------
# POST /api/v1/situations/{id}/actions
# ---------------------------------------------------------------------------


def _actions_url(situation_id: int) -> str:
    return f"/api/v1/situations/{situation_id}/actions"


async def test_create_action_updates_status(auth_client: AsyncClient):
    # Arrange — 활성(조치 대기) 상황 1건
    patient = await _make_patient()
    situation = await _make_situation(patient, action_status="조치 대기")

    # Act — 유선 연락 후 "조치 완료"로 전환
    res = await auth_client.post(
        _actions_url(situation.situation_id),
        json={"action_type": "유선 연락", "action_note": None, "status_update": "조치 완료"},
    )

    # Assert — 201 + 상태 갱신, 이후 활성 목록에서 빠진다
    assert res.status_code == 201
    assert res.json()["data"]["action_status"] == "조치 완료"
    await situation.refresh_from_db()
    assert situation.action_status == ActionStatus.COMPLETED
    active = await auth_client.get(ACTIVE_URL)
    assert active.json()["data"]["situations"] == []


async def test_create_action_situation_not_found(auth_client: AsyncClient):
    res = await auth_client.post(
        _actions_url(999999),
        json={"action_type": "유선 연락", "status_update": "조치 완료"},
    )
    assert res.status_code == 404


async def test_create_action_invalid_status(auth_client: AsyncClient):
    patient = await _make_patient()
    situation = await _make_situation(patient)
    res = await auth_client.post(
        _actions_url(situation.situation_id),
        json={"action_type": "유선 연락", "status_update": "존재하지 않는 상태"},
    )
    assert res.status_code == 422


async def test_create_action_requires_auth(client: AsyncClient):
    res = await client.post(
        _actions_url(1),
        json={"action_type": "유선 연락", "status_update": "조치 완료"},
    )
    assert res.status_code == 401
