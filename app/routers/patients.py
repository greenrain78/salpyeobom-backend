import asyncio
import math

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.dependencies import get_current_user
from app.models.patient import Patient
from app.schemas.common import SuccessResponse
from app.schemas.patient_monitoring import (
    Administration,
    AIAnalysis,
    PatientDetail,
    PatientListData,
    PatientListItem,
)

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["patients"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=SuccessResponse[PatientListData])
async def list_patients(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1),
    search_name: str | None = Query(default=None),
) -> SuccessResponse[PatientListData]:
    qs = Patient.all()
    if search_name:
        qs = qs.filter(name__icontains=search_name)
    # 목록에 필요한 5개 컬럼만 조회(전체 행 대신) + count 와 동시 실행으로
    # 원격 DB 왕복을 2회→1회(병렬)로 줄인다.
    total, patients = await asyncio.gather(
        qs.count(),
        qs.only(
            "patient_id",
            "name",
            "address_summary",
            "manager_name",
            "cross_verification_level",
        )
        .offset((page - 1) * limit)
        .limit(limit),
    )
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
            name=patient.name,
            age=f"만 {patient.age}세",
            address_full=patient.address_full,
            cross_verification_level=patient.cross_verification_level,
            doc_no=patient.doc_no,
            profile_image_url=patient.profile_image_url,
            ai_analysis=AIAnalysis(
                cross_verification_level=patient.cross_verification_level,
                alert_title=patient.ai_alert_title,
                alert_desc=patient.ai_alert_desc,
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
