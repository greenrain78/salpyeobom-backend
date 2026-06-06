from typing import Any

from tortoise import fields
from tortoise.models import Model

from app.models.enums import ActionStatus


class Patient(Model):
    patient_id = fields.CharField(max_length=64, primary_key=True)
    name = fields.CharField(max_length=64, db_index=True)
    age = fields.IntField()
    address_full = fields.CharField(max_length=255)
    address_summary = fields.CharField(max_length=128)
    phone_number = fields.CharField(max_length=20, null=True)
    # 행정 정보
    manager_name = fields.CharField(max_length=64, null=True)
    management_level = fields.CharField(max_length=64, null=True)
    diseases: list[Any] = fields.JSONField(default=list)  # type: ignore[assignment]

    class Meta:
        table = "patients"


class Situation(Model):
    situation_id = fields.IntField(primary_key=True)
    patient: Any = fields.ForeignKeyField(
        "models.Patient", related_name="situations", db_index=True
    )
    category = fields.CharField(max_length=32)
    detail_reason = fields.TextField(null=True)
    occurred_at = fields.DatetimeField(db_index=True)
    action_status = fields.CharEnumField(ActionStatus, max_length=16, default=ActionStatus.PENDING)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "situations"

    @property
    def is_active(self) -> bool:
        """활성 상태 = 조치가 완료되지 않음. action_status 단일 출처에서 파생."""
        return self.action_status != ActionStatus.COMPLETED
