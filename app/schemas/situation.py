from datetime import datetime

from pydantic import BaseModel, field_serializer


class SituationOut(BaseModel):
    situation_id: int
    patient_id: str
    name: str
    address_summary: str
    category: str
    detail_reason: str | None
    occurred_at: datetime
    action_status: str

    @field_serializer("occurred_at")
    def serialize_time(self, v: datetime) -> str:
        return v.strftime("%H:%M:%S")


class ActiveSituationsData(BaseModel):
    situations: list[SituationOut]


class ActionRequest(BaseModel):
    action_type: str
    action_note: str | None = None
    status_update: str  # ActionStatus 값 ("조치 대기"/"현장 출동"/"조치 완료")


class ActionResult(BaseModel):
    situation_id: int
    action_status: str
