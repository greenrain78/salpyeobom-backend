from datetime import datetime
from typing import Literal

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
    action_type: Literal["유선 연락", "현장 출동", "기타"]
    action_note: str | None = None
    status_update: Literal["조치 대기", "현장 출동", "조치 완료"]

    model_config = {
        "json_schema_extra": {
            "example": {
                "action_type": "유선 연락",
                "action_note": "오전 투약 후 수면 중임을 유선으로 확인 완료.",
                "status_update": "조치 완료",
            }
        }
    }


class ActionResponse(BaseModel):
    status: str = "success"
    message: str = "업무 일지가 성공적으로 등록되었으며, 상황 상태가 업데이트되었습니다."
