from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.models.enums import ActionStatus
from app.models.patient import Situation
from app.schemas.common import SuccessResponse
from app.schemas.situation import ActiveSituationsData, SituationOut

router = APIRouter(
    prefix="/api/v1/situations",
    tags=["situations"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/active", response_model=SuccessResponse[ActiveSituationsData])
async def get_active_situations(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1),
) -> SuccessResponse[ActiveSituationsData]:
    situations = (
        await Situation.filter(action_status__not=ActionStatus.COMPLETED)
        .select_related("patient")
        .order_by("-occurred_at")
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return SuccessResponse(
        data=ActiveSituationsData(
            situations=[
                SituationOut(
                    situation_id=s.situation_id,
                    patient_id=s.patient.patient_id,
                    name=s.patient.name,
                    address_summary=s.patient.address_summary,
                    category=s.category,
                    detail_reason=s.detail_reason,
                    occurred_at=s.occurred_at,
                    action_status=s.action_status,
                )
                for s in situations
            ]
        )
    )
