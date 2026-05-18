from datetime import date, timedelta

from httpx import AsyncClient

from app.models.patient import Patient
from app.models.patient import TimeseriesData as TimeseriesModel


async def _make_patient(pid: str = "user_1001", **kwargs) -> Patient:
    return await Patient.create(
        patient_id=pid,
        name=kwargs.get("name", "김순자"),
        age=kwargs.get("age", 78),
        address_full=kwargs.get("address_full", "서울특별시 노원구 상계동 123-4"),
        address_summary=kwargs.get("address_summary", "상계동 123-4"),
        doc_no="NO.2026-04-08-001",
        manager_name="김재섭",
        management_level="집중 관리군 (1등급)",
        diseases=["고혈압", "초기 치매"],
        next_visit_time="2026.04.10 (금) 14:00",
        next_visit_plan="정기 혈압 체크",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/patients
# ---------------------------------------------------------------------------


async def test_list_patients_empty(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/patients")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_count"] == 0
    assert data["patients"] == []


async def test_list_patients_pagination(auth_client: AsyncClient):
    for i in range(5):
        await _make_patient(pid=f"p{i}", name=f"환자{i}")

    res = await auth_client.get("/api/v1/patients", params={"page": 1, "limit": 3})
    data = res.json()["data"]
    assert data["total_count"] == 5
    assert data["total_pages"] == 2
    assert len(data["patients"]) == 3

    res2 = await auth_client.get("/api/v1/patients", params={"page": 2, "limit": 3})
    assert len(res2.json()["data"]["patients"]) == 2


async def test_list_patients_search(auth_client: AsyncClient):
    await _make_patient(pid="p1", name="김순자")
    await _make_patient(pid="p2", name="최갑수")

    res = await auth_client.get("/api/v1/patients", params={"search_name": "김"})
    data = res.json()["data"]
    assert data["total_count"] == 1
    assert data["patients"][0]["name"] == "김순자"


async def test_list_patients_fields(auth_client: AsyncClient):
    await _make_patient()
    item = (await auth_client.get("/api/v1/patients")).json()["data"]["patients"][0]
    assert item["patient_id"] == "user_1001"
    assert item["manager_name"] == "김재섭"
    assert "hashed_password" not in item


# ---------------------------------------------------------------------------
# GET /api/v1/patients/{patient_id}/details
# ---------------------------------------------------------------------------


async def test_patient_details_success(auth_client: AsyncClient):
    await _make_patient()
    res = await auth_client.get("/api/v1/patients/user_1001/details")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["name"] == "김순자"
    assert data["age"] == "만 78세"
    assert data["administration"]["diseases"] == ["고혈압", "초기 치매"]


async def test_patient_details_not_found(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/patients/ghost/details")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/patients/{patient_id}/timeseries
# ---------------------------------------------------------------------------


async def test_timeseries_success(auth_client: AsyncClient):
    patient = await _make_patient()
    today = date.today()
    await TimeseriesModel.bulk_create(
        [
            TimeseriesModel(
                patient=patient, date=today - timedelta(days=2), mae_score=1.1, is_anomaly=False
            ),
            TimeseriesModel(
                patient=patient, date=today - timedelta(days=1), mae_score=1.4, is_anomaly=False
            ),
            TimeseriesModel(patient=patient, date=today, mae_score=3.42, is_anomaly=True),
        ]
    )

    res = await auth_client.get("/api/v1/patients/user_1001/timeseries")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["patient_id"] == "user_1001"
    assert len(data["timeseries"]) == 3
    assert data["timeseries"][-1]["is_anomaly"] is True


async def test_timeseries_days_filter(auth_client: AsyncClient):
    patient = await _make_patient()
    today = date.today()
    await TimeseriesModel.bulk_create(
        [
            TimeseriesModel(
                patient=patient, date=today - timedelta(days=30), mae_score=1.0, is_anomaly=False
            ),
            TimeseriesModel(patient=patient, date=today, mae_score=1.5, is_anomaly=False),
        ]
    )

    res = await auth_client.get("/api/v1/patients/user_1001/timeseries", params={"days": 7})
    assert len(res.json()["data"]["timeseries"]) == 1


async def test_timeseries_new_patient_returns_empty(auth_client: AsyncClient):
    await _make_patient()
    res = await auth_client.get("/api/v1/patients/user_1001/timeseries")
    assert res.status_code == 200
    assert res.json()["data"]["timeseries"] == []


async def test_timeseries_not_found(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/patients/ghost/timeseries")
    assert res.status_code == 404
