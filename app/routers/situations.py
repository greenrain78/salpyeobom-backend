from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.dependencies import get_current_user
from app.models.patient import Situation, SituationAction
from app.schemas.common import SuccessResponse
from app.schemas.situation import ActionRequest, ActionResponse, ActiveSituationsData, SituationOut

router = APIRouter(
    prefix="/api/v1/situations",
    tags=["situations"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/active", response_model=SuccessResponse[ActiveSituationsData])
async def get_active_situations(
    limit: int = Query(default=20, ge=1),
) -> SuccessResponse[ActiveSituationsData]:
    situations = (
        await Situation.filter(action_status__not="조치 완료")
        .select_related("patient")
        .order_by("-occurred_at")
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


@router.post(
    "/{situation_id}/actions",
    response_model=ActionResponse,
    status_code=201,
)
async def create_action(
    body: ActionRequest,
    situation_id: int = Path(...),
) -> ActionResponse:
    situation = await Situation.get_or_none(situation_id=situation_id)
    if situation is None:
        raise HTTPException(status_code=404, detail="상황을 찾을 수 없습니다.")

    await SituationAction.create(
        situation=situation,
        action_type=body.action_type,
        action_note=body.action_note,
    )
    situation.action_status = body.status_update
    await situation.save()

    return ActionResponse()
