from httpx import AsyncClient

from app.models.patient import Patient

URL = "/api/v1/dashboard/summary"


async def test_summary_empty(auth_client: AsyncClient):
    res = await auth_client.get(URL)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data == {
        "emergency_count": 0,
        "warning_count": 0,
        "normal_count": 0,
        "total_monitoring_count": 0,
    }


async def test_summary_counts(auth_client: AsyncClient):
    await Patient.bulk_create(
        [
            Patient(
                patient_id="p1",
                name="A",
                age=70,
                address_full="서울",
                address_summary="상계동",
                cross_verification_level="초고위험",
            ),
            Patient(
                patient_id="p2",
                name="B",
                age=71,
                address_full="서울",
                address_summary="상계동",
                cross_verification_level="주의",
            ),
            Patient(
                patient_id="p3",
                name="C",
                age=72,
                address_full="서울",
                address_summary="상계동",
                cross_verification_level="정상",
            ),
            Patient(
                patient_id="p4",
                name="D",
                age=73,
                address_full="서울",
                address_summary="상계동",
                cross_verification_level="정상",
            ),
        ]
    )
    res = await auth_client.get(URL)
    data = res.json()["data"]
    assert data["emergency_count"] == 1
    assert data["warning_count"] == 1
    assert data["normal_count"] == 2
    assert data["total_monitoring_count"] == 4
