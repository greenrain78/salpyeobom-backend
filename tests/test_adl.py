from datetime import UTC, date, datetime

import pytest
from tortoise.exceptions import IntegrityError

from app.models.adl import AdlDailyRecord, AdlHourlyEnvironment, AdlRawIngest
from app.models.patient import Patient


async def _make_patient(pid: str = "p_adl_001") -> Patient:
    return await Patient.create(
        patient_id=pid,
        name="이순자",
        age=81,
        address_full="서울특별시 강북구 미아동 10-1",
        address_summary="미아동 10-1",
        phone_number="01021379180",
    )


async def test_adl_raw_ingest_create(client):
    patient = await _make_patient()
    raw = await AdlRawIngest.create(
        patient=patient,
        device_id="01021379180",
        gateway_mac="6044197d21a4",
        device_ts=datetime(2021, 3, 17, 10, 14, 54, tzinfo=UTC),
        payload={"header": {"deviceId": "01021379180"}, "data": {"numOfSensors": 4}},
    )
    assert raw.id is not None
    assert raw.is_processed is False
    assert raw.device_id == "01021379180"


async def test_adl_raw_ingest_patient_nullable(client):
    raw = await AdlRawIngest.create(
        patient=None,
        device_id="unknown_device",
        gateway_mac="aabbccddeeff",
        device_ts=datetime(2021, 3, 17, 10, 0, 0, tzinfo=UTC),
        payload={},
    )
    assert raw.patient_id is None


async def test_adl_daily_record_create(client):
    patient = await _make_patient("p_adl_002")
    record = await AdlDailyRecord.create(
        patient=patient,
        record_date=date(2021, 3, 17),
        sleep_start_time="22:30:00",
        sleep_end_time="06:15:00",
        total_sleep_period=465.0,
        total_sleep_aix_ratio=82.5,
        aix_score=0.73,
        outgoing_count=1,
        outgoing_time=45.0,
        bath_count=1,
        bath_time=12.0,
        mae_score=1.8,
        is_anomaly=False,
    )
    assert record.id is not None
    assert record.aix_score == pytest.approx(0.73)


async def test_adl_daily_record_unique_per_day(client):
    patient = await _make_patient("p_adl_003")
    await AdlDailyRecord.create(patient=patient, record_date=date(2021, 3, 17))
    with pytest.raises(IntegrityError):
        await AdlDailyRecord.create(patient=patient, record_date=date(2021, 3, 17))


async def test_adl_hourly_environment_24_rows(client):
    patient = await _make_patient("p_adl_004")
    record = await AdlDailyRecord.create(patient=patient, record_date=date(2021, 3, 17))

    env_rows = [
        AdlHourlyEnvironment(
            daily_record=record,
            hour=h,
            temperature=22.5 + h * 0.1,
            humidity=55.0,
            illuminance=0 if h < 6 else 300,
        )
        for h in range(24)
    ]
    await AdlHourlyEnvironment.bulk_create(env_rows)

    count = await AdlHourlyEnvironment.filter(daily_record=record).count()
    assert count == 24


async def test_adl_hourly_environment_unique_per_hour(client):
    patient = await _make_patient("p_adl_005")
    record = await AdlDailyRecord.create(patient=patient, record_date=date(2021, 3, 17))
    await AdlHourlyEnvironment.create(daily_record=record, hour=12, temperature=25.0)
    with pytest.raises(IntegrityError):
        await AdlHourlyEnvironment.create(daily_record=record, hour=12, temperature=26.0)


async def test_adl_cascade_delete(client):
    patient = await _make_patient("p_adl_006")
    record = await AdlDailyRecord.create(patient=patient, record_date=date(2021, 3, 17))
    await AdlHourlyEnvironment.create(daily_record=record, hour=0, temperature=21.0)

    await record.delete()
    remaining = await AdlHourlyEnvironment.filter(daily_record_id=record.id).count()
    assert remaining == 0
