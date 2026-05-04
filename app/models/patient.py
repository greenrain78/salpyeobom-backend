from typing import Any

from tortoise import fields
from tortoise.models import Model


class Patient(Model):
    patient_id = fields.CharField(max_length=64, primary_key=True)
    name = fields.CharField(max_length=64)
    age = fields.IntField()
    address_full = fields.CharField(max_length=255)
    address_summary = fields.CharField(max_length=128)
    profile_image_url = fields.CharField(max_length=512, null=True)
    doc_no = fields.CharField(max_length=64, null=True)
    # AI 분석
    track_A_state = fields.CharField(max_length=16, default="정상")
    track_B_anomaly = fields.CharField(max_length=16, default="정상")
    cross_verification_level = fields.CharField(max_length=16, default="정상")
    alert_title = fields.CharField(max_length=255, null=True)
    alert_desc = fields.TextField(null=True)
    threshold_value = fields.FloatField(default=2.5)
    # 행정 정보
    manager_name = fields.CharField(max_length=64, null=True)
    management_level = fields.CharField(max_length=64, null=True)
    diseases: list[Any] = fields.JSONField(default=list)  # type: ignore[assignment]
    next_visit_time = fields.CharField(max_length=64, null=True)
    next_visit_plan = fields.TextField(null=True)

    class Meta:
        table = "patients"


class Situation(Model):
    situation_id = fields.IntField(primary_key=True)
    patient: Any = fields.ForeignKeyField("models.Patient", related_name="situations")
    category = fields.CharField(max_length=32)
    detail_reason = fields.TextField(null=True)
    occurred_at = fields.DatetimeField()
    action_status = fields.CharField(max_length=16, default="조치 대기")
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "situations"


class SituationAction(Model):
    id = fields.IntField(primary_key=True)
    situation: Any = fields.ForeignKeyField("models.Situation", related_name="actions")
    action_type = fields.CharField(max_length=16)
    action_note = fields.TextField(null=True)
    status_update = fields.CharField(max_length=16)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "situation_actions"


class TimeseriesData(Model):
    id = fields.IntField(primary_key=True)
    patient: Any = fields.ForeignKeyField("models.Patient", related_name="timeseries")
    date = fields.DateField()
    mae_score = fields.FloatField()
    is_anomaly = fields.BooleanField(default=False)

    class Meta:
        table = "timeseries_data"
