from datetime import UTC, datetime

from httpx import AsyncClient

from app.models.patient import Patient, Situation

URL = "/api/v1/dashboard/summary"


async def test_summary_empty(auth_client: AsyncClient):
    res = await auth_client.get(URL)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data == {
        "total_monitoring_count": 0,
        "emergency_count": 0,
        "warning_count": 0,
        "normal_count": 0,
    }


async def test_summary_counts(auth_client: AsyncClient):
    await Patient.bulk_create(
        [
            Patient(
                patient_id="p1", name="A", age=70, address_full="서울", address_summary="상계동"
            ),
            Patient(
                patient_id="p2", name="B", age=71, address_full="서울", address_summary="상계동"
            ),
            Patient(
                patient_id="p3", name="C", age=72, address_full="서울", address_summary="상계동"
            ),
            Patient(
                patient_id="p4", name="D", age=73, address_full="서울", address_summary="상계동"
            ),
        ]
    )
    res = await auth_client.get(URL)
    data = res.json()["data"]
    assert data["total_monitoring_count"] == 4


async def test_summary_buckets(auth_client: AsyncClient):
    # Arrange — 4 대상자, 활성 상황 3건(응급/낙상/미응답) + 완료 1건(집계 제외)
    await Patient.bulk_create(
        [
            Patient(
                patient_id=f"p{i}",
                name=f"N{i}",
                age=70,
                address_full="서울",
                address_summary="상계동",
            )
            for i in range(1, 5)
        ]
    )
    p1 = await Patient.get(patient_id="p1")
    now = datetime(2026, 4, 8, 10, 0, 0, tzinfo=UTC)
    await Situation.create(patient=p1, category="응급", occurred_at=now, action_status="조치 대기")
    await Situation.create(
        patient=p1, category="낙상 의심", occurred_at=now, action_status="현장 출동"
    )
    await Situation.create(
        patient=p1, category="미응답", occurred_at=now, action_status="조치 대기"
    )
    await Situation.create(patient=p1, category="지연", occurred_at=now, action_status="조치 완료")

    # Act
    res = await auth_client.get(URL)
    data = res.json()["data"]

    # Assert — emergency=응급+낙상=2, warning=미응답=1(완료된 지연 제외), normal=4-2-1=1
    assert data["total_monitoring_count"] == 4
    assert data["emergency_count"] == 2
    assert data["warning_count"] == 1
    assert data["normal_count"] == 1
