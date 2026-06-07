from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.enums import ActionStatus
from app.models.patient import Patient, Situation
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import DashboardSummary

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)

# 활성 상황 카테고리 → 통계 버킷 매핑. category 는 개방형 문자열이라
# (app/models/enums.py 참조) ENUM 대신 키워드 포함 여부로 분류한다.
EMERGENCY_KEYWORDS = ("낙상", "응급", "사망")
WARNING_KEYWORDS = ("미응답", "지연")


@router.get("/summary", response_model=SuccessResponse[DashboardSummary])
async def get_summary() -> SuccessResponse[DashboardSummary]:
    total = await Patient.all().count()

    active_categories: list[str] = await Situation.filter(
        action_status__not=ActionStatus.COMPLETED
    ).values_list("category", flat=True)  # type: ignore[assignment]

    emergency = sum(1 for c in active_categories if any(k in c for k in EMERGENCY_KEYWORDS))
    warning = sum(1 for c in active_categories if any(k in c for k in WARNING_KEYWORDS))
    normal = max(0, total - emergency - warning)

    return SuccessResponse(
        data=DashboardSummary(
            total_monitoring_count=total,
            emergency_count=emergency,
            warning_count=warning,
            normal_count=normal,
        )
    )
