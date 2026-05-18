from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.patient import Patient
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import DashboardSummary

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/summary", response_model=SuccessResponse[DashboardSummary])
async def get_summary() -> SuccessResponse[DashboardSummary]:
    total = await Patient.all().count()
    return SuccessResponse(data=DashboardSummary(total_monitoring_count=total))
