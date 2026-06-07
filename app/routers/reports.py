from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.email import send_report_email
from app.schemas.common import SuccessResponse
from app.schemas.report import ReportEmailRequest, ReportEmailResult

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/email", response_model=SuccessResponse[ReportEmailResult])
async def email_report(body: ReportEmailRequest) -> SuccessResponse[ReportEmailResult]:
    report_name = await send_report_email(
        recipient=body.recipient,
        report_name=body.report_name,
        subject=body.subject,
        message=body.message,
    )
    return SuccessResponse(data=ReportEmailResult(sent_to=body.recipient, report_name=report_name))
