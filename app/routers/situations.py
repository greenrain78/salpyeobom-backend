from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.dependencies import get_current_user
from app.models.enums import ActionStatus
from app.models.patient import Situation
from app.schemas.common import SuccessResponse
from app.schemas.situation import (
    ActionRequest,
    ActionResult,
    ActiveSituationsData,
    SituationOut,
)

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


@router.post(
    "/{situation_id}/actions",
    response_model=SuccessResponse[ActionResult],
    status_code=201,
)
async def create_action(
    body: ActionRequest,
    situation_id: int = Path(...),
) -> SuccessResponse[ActionResult]:
    situation = await Situation.get_or_none(situation_id=situation_id)
    if situation is None:
        raise HTTPException(status_code=404, detail="상황을 찾을 수 없습니다.")

    try:
        new_status = ActionStatus(body.status_update)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="유효하지 않은 조치 상태입니다.") from exc

    # NOTE: action_type / action_note 는 받아들이되 별도 ActionLog 테이블이 없어 저장하지 않는다.
    #       현재 범위(무중단 최소 변경)에서는 상황의 진행 상태(action_status) 갱신만 반영한다.
    situation.action_status = new_status
    await situation.save(update_fields=["action_status"])

    return SuccessResponse(
        data=ActionResult(
            situation_id=situation.situation_id,
            action_status=situation.action_status,
        )
    )
