from pydantic import BaseModel, EmailStr


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
