from typing import Any

from tortoise import fields
from tortoise.models import Model


class AdlRawRecord(Model):
    """엑셀 샘플 원시 ADL 데이터 — 응급/사망 이벤트 당일 기록"""

    id = fields.IntField(primary_key=True)
    source_type = fields.CharField(max_length=4)  # '응급' | '사망'

    # 기본 정보
    care_recipient_id = fields.CharField(max_length=32)
    age = fields.IntField(null=True)
    sex = fields.CharField(max_length=1, null=True)
    alone = fields.CharField(max_length=1, null=True)
    vision = fields.CharField(max_length=16, null=True)
    hearing = fields.CharField(max_length=16, null=True)
    dosage = fields.CharField(max_length=16, null=True)
    district = fields.CharField(max_length=64, null=True)
    house_structure = fields.CharField(max_length=16, null=True)
    room_no = fields.IntField(null=True)
    bath_location = fields.CharField(max_length=16, null=True)

    # 이벤트 정보
    lifeog_date = fields.DateField(null=True)
    emergency_date = fields.DateField(null=True)
    emergency_record = fields.TextField(null=True)
    occurrence_place = fields.CharField(max_length=32, null=True)
    on_site = fields.CharField(max_length=16, null=True)
    hospital_transfer = fields.CharField(max_length=16, null=True)
    hospital_treatment = fields.CharField(max_length=16, null=True)
    death_date = fields.DateField(null=True)
    death_record = fields.TextField(null=True)

    # 분석 데이터
    place_code_1_list: Any = fields.JSONField(null=True)
    aix_1_list: Any = fields.JSONField(null=True)
    aix_h_list: Any = fields.JSONField(null=True)
    aix_d = fields.FloatField(null=True)
    aix_1_eq_0_repeat_count = fields.IntField(null=True)
    total_aix_sum = fields.FloatField(null=True)
    total_aix_inc_ratio = fields.FloatField(null=True)
    night_aix_ratio = fields.FloatField(null=True)
    total_age_aix_ratio = fields.FloatField(null=True)

    # 수면
    sleep_depth_1_list: Any = fields.JSONField(null=True)
    sleep_start_time_d = fields.CharField(max_length=8, null=True)
    sleep_end_time_d = fields.CharField(max_length=8, null=True)
    total_sleep_period = fields.FloatField(null=True)
    total_sleep_aix_ratio = fields.FloatField(null=True)

    # 목욕
    bath_count_d = fields.IntField(null=True)
    bath_time_d = fields.FloatField(null=True)
    bath_nomove_time = fields.FloatField(null=True)
    bath_count_in_sleep = fields.IntField(null=True)
    bath_time_per_count = fields.FloatField(null=True)
    total_bath_average_count = fields.FloatField(null=True)

    # 외출
    outgoing_1_list: Any = fields.JSONField(null=True)
    outgoing_count_d = fields.IntField(null=True)
    outgoing_time_d = fields.FloatField(null=True)
    outgoing_late_night_count_d = fields.IntField(null=True)
    outgoing_late_night_time_d = fields.FloatField(null=True)
    last_outgoing_time = fields.CharField(max_length=16, null=True)
    total_outgoing_average_time = fields.FloatField(null=True)
    total_outgoing_average_count = fields.FloatField(null=True)

    # 시간별 환경 센서 (JSON 배열, 인덱스 = 시간 0~23)
    temp_list: Any = fields.JSONField(null=True)
    humi_list: Any = fields.JSONField(null=True)
    illu_list: Any = fields.JSONField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "adl_raw_records"
