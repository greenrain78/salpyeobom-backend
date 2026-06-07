from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.core.dependencies import get_current_user
from app.core.email import resolve_report, send_report_email
from app.core.exceptions import ReportNotFound
from app.models.report import Report
from app.schemas.common import SuccessResponse
from app.schemas.report import (
    ReportEmailRequest,
    ReportEmailResult,
    ReportListData,
)
from app.services.reports import build_report_list

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=SuccessResponse[ReportListData])
async def list_reports(
    date_filter: str | None = Query(None, alias="date", description="특정일 (YYYY-MM-DD)"),
    from_: str | None = Query(None, alias="from", description="기간 시작일 (YYYY-MM-DD)"),
    to: str | None = Query(None, alias="to", description="기간 종료일 (YYYY-MM-DD)"),
) -> SuccessResponse[ReportListData]:
    """생성·발송된 보고서 전체 이력을 일자별 그룹으로 반환한다.

    기본은 전 기간(오늘 + 과거 전체). date/from/to 는 좁히기용 선택 필터.
    """
    reports = await Report.all().prefetch_related("patient")  # Meta.ordering 으로 최신순

    items: list[dict] = [
        {
            "id": r.id,
            "patient_id": r.patient.patient_id,
            "patient_name": r.patient.name,
            # 저장된 분류 우선, 없으면 등급 폴백 (build_report_list 에서 처리).
            "risk_level": r.risk_level,
            "patient_level": r.patient.cross_verification_level,
            "title": r.title,
            "file_name": r.file_name,
            "generated_at": r.generated_at,
            "emailed_at": r.emailed_at,
            "emailed_to": r.emailed_to,
        }
        for r in reports
    ]

    # 선택 필터 — 소규모 데이터라 파이썬에서 일자 비교(타임존 혼선 방지).
    only = date.fromisoformat(date_filter) if date_filter else None
    lo = date.fromisoformat(from_) if from_ else None
    hi = date.fromisoformat(to) if to else None
    if only or lo or hi:
        items = [it for it in items if _in_range(it["generated_at"].date(), only, lo, hi)]

    data = build_report_list(items, today=datetime.now(UTC).date())
    return SuccessResponse(data=ReportListData(**data))


def _in_range(day: date, only: date | None, lo: date | None, hi: date | None) -> bool:
    if only is not None:
        return day == only
    if lo is not None and day < lo:
        return False
    return not (hi is not None and day > hi)


@router.get("/{report_id}/file")
async def get_report_file(report_id: int) -> FileResponse:
    """보고서 PDF 를 인라인으로 서빙한다 (바이너리 → SuccessResponse 래핑 예외)."""
    report = await Report.get_or_none(id=report_id)
    if report is None:
        raise ReportNotFound()
    path = resolve_report(report.file_name)  # OUT_DIR 하위 + 경로 탈출 차단
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=report.file_name,
        content_disposition_type="inline",
    )


@router.post("/email", response_model=SuccessResponse[ReportEmailResult])
async def email_report(body: ReportEmailRequest) -> SuccessResponse[ReportEmailResult]:
    report_name = await send_report_email(
        recipient=body.recipient,
        report_name=body.report_name,
        subject=body.subject,
        message=body.message,
    )
    # 발송 이력 스탬프 (해당 Report 가 있으면) — PDF 파일명은 docx 와 stem 공유.
    stem = Path(report_name).stem
    report = await Report.filter(file_name=f"{stem}.pdf").first()
    if report is not None:
        report.emailed_at = datetime.now(UTC)
        report.emailed_to = body.recipient
        await report.save()

    return SuccessResponse(data=ReportEmailResult(sent_to=body.recipient, report_name=report_name))
