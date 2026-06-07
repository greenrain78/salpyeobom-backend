from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class ReportItem(BaseModel):
    id: int
    patient_id: str
    patient_name: str
    risk_level: str  # 위험 | 주의 | 사망 (대상자 교차검증등급에서 파생)
    title: str
    file_name: str
    generated_at: datetime
    emailed_at: datetime | None = None
    emailed_to: str | None = None


class ReportDayGroup(BaseModel):
    date: date
    count: int
    items: list[ReportItem]


class ReportListData(BaseModel):
    risk_count: int
    caution_count: int
    death_count: int
    total: int
    today_count: int
    groups: list[ReportDayGroup]


class ReportEmailRequest(BaseModel):
    recipient: EmailStr
    report_name: str | None = None  # None → 기본 보고서(위험예측보고서_661.docx)
    subject: str | None = None
    message: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "recipient": "manager@example.com",
            }
        }
    }


class ReportEmailResult(BaseModel):
    sent_to: EmailStr
    report_name: str
