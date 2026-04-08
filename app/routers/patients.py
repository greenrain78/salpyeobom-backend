import math
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Path, Query

from app.models.patient import Patient
from app.models.patient import TimeseriesData as TimeseriesModel
from app.schemas.common import SuccessResponse
from app.schemas.patient_monitoring import (
    Administration,
    AiAnalysis,
    PatientDetail,
    PatientListData,
    PatientListItem,
    TimeseriesData,
    TimeseriesPoint,
)

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("", response_model=SuccessResponse[PatientListData])
async def list_patients(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1),
    search_name: str | None = Query(default=None),
) -> SuccessResponse[PatientListData]:
    qs = Patient.all()
    if search_name:
        qs = qs.filter(name__icontains=search_name)
    total = await qs.count()
    patients = await qs.offset((page - 1) * limit).limit(limit)
    return SuccessResponse(
        data=PatientListData(
            total_count=total,
            current_page=page,
            total_pages=math.ceil(total / limit) if total else 1,
            patients=[PatientListItem.model_validate(p) for p in patients],
        )
    )


@router.get("/{patient_id}/details", response_model=SuccessResponse[PatientDetail])
async def get_patient_details(
    patient_id: str = Path(...),
) -> SuccessResponse[PatientDetail]:
    patient = await Patient.get_or_none(patient_id=patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="대상자를 찾을 수 없습니다.")

    return SuccessResponse(
        data=PatientDetail(
            doc_no=patient.doc_no,
            profile_image_url=patient.profile_image_url,
            name=patient.name,
            age=f"만 {patient.age}세",
            address_full=patient.address_full,
            ai_analysis=AiAnalysis(
                track_A_state=patient.track_A_state,
                track_B_anomaly=patient.track_B_anomaly,
                cross_verification_level=patient.cross_verification_level,
                alert_title=patient.alert_title,
                alert_desc=patient.alert_desc,
            ),
            administration=Administration(
                manager_name=patient.manager_name,
                management_level=patient.management_level,
                diseases=patient.diseases,
                next_visit_time=patient.next_visit_time,
                next_visit_plan=patient.next_visit_plan,
            ),
        )
    )


@router.get("/{patient_id}/timeseries", response_model=SuccessResponse[TimeseriesData])
async def get_timeseries(
    patient_id: str = Path(...),
    days: int = Query(default=14, ge=1),
) -> SuccessResponse[TimeseriesData]:
    patient = await Patient.get_or_none(patient_id=patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="대상자를 찾을 수 없습니다.")

    records = await TimeseriesModel.filter(
        patient=patient,
        date__gte=date.today() - timedelta(days=days),
    ).order_by("date")

    return SuccessResponse(
        data=TimeseriesData(
            patient_id=patient_id,
            threshold_value=patient.threshold_value,
            timeseries=[
                TimeseriesPoint(
                    date=r.date,
                    mae_score=r.mae_score,
                    is_anomaly=r.is_anomaly,
                )
                for r in records
            ],
        )
    )
