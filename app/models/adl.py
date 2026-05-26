from typing import Any

from tortoise import fields
from tortoise.models import Model


class AdlDailyRecord(Model):
    """일별 ADL 집계 피처 — AI 학습/예측 입력값"""

    id = fields.IntField(primary_key=True)
    patient: Any = fields.ForeignKeyField(
        "models.Patient", related_name="adl_records", on_delete=fields.CASCADE
    )
    record_date = fields.DateField()

    # 수면
    sleep_start_time = fields.CharField(max_length=8, null=True)
    sleep_end_time = fields.CharField(max_length=8, null=True)
    total_sleep_period = fields.FloatField(null=True)
    total_sleep_aix_ratio = fields.FloatField(null=True)
    aix_score = fields.FloatField(null=True)

    # 외출
    outgoing_count = fields.IntField(null=True)
    outgoing_time = fields.FloatField(null=True)
    outgoing_late_night_count = fields.IntField(null=True)
    outgoing_late_night_time = fields.FloatField(null=True)

    # 욕실
    bath_count = fields.IntField(null=True)
    bath_time = fields.FloatField(null=True)
    bath_nomove_time = fields.FloatField(null=True)
    bath_count_in_sleep = fields.IntField(null=True)
    total_bath_average_count = fields.FloatField(null=True)

    # AI 분석 결과 (TimeseriesData 대체)
    mae_score = fields.FloatField(null=True)
    is_anomaly = fields.BooleanField(default=False)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "adl_daily_records"
        unique_together = (("patient", "record_date"),)


class AdlHourlyEnvironment(Model):
    """시간별 환경 센서 데이터 (24행/일)"""

    id = fields.IntField(primary_key=True)
    daily_record: Any = fields.ForeignKeyField(
        "models.AdlDailyRecord", related_name="hourly_env", on_delete=fields.CASCADE
    )
    hour = fields.IntField()
    temperature = fields.FloatField(null=True)
    humidity = fields.FloatField(null=True)
    illuminance = fields.FloatField(null=True)

    class Meta:
        table = "adl_hourly_environment"
        unique_together = (("daily_record", "hour"),)
