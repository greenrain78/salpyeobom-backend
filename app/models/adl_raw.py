from tortoise import fields
from tortoise.contrib.postgres.fields import ArrayField
from tortoise.models import Model


class AdlRawRecord(Model):
    """엑셀 샘플 원시 ADL 데이터 — 응급/사망 이벤트 당일 기록"""

    id = fields.IntField(primary_key=True)
    # 외부 CSV 적재에서 오는 개방형 값: "응급" | "사망" | "평소" | "사망전" 등. ENUM 미강제.
    source_type = fields.CharField(max_length=4, db_index=True)

    # 기본 정보
    care_recipient_id = fields.CharField(max_length=32, db_index=True)
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
    place_code_1_list: list[int] = ArrayField(element_type="int", null=True)
    aix_1_list: list[int] = ArrayField(element_type="int", null=True)
    aix_h_list: list[int] = ArrayField(element_type="int", null=True)
    aix_d = fields.FloatField(null=True)
    aix_1_eq_0_repeat_count = fields.IntField(null=True)
    total_aix_sum = fields.FloatField(null=True)
    total_aix_inc_ratio = fields.FloatField(null=True)
    night_aix_ratio = fields.FloatField(null=True)
    total_age_aix_ratio = fields.FloatField(null=True)

    # 수면
    sleep_depth_1_list: list[int] = ArrayField(element_type="int", null=True)
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
    outgoing_1_list: list[int] = ArrayField(element_type="int", null=True)
    outgoing_count_d = fields.IntField(null=True)
    outgoing_time_d = fields.FloatField(null=True)
    outgoing_late_night_count_d = fields.IntField(null=True)
    outgoing_late_night_time_d = fields.FloatField(null=True)
    last_outgoing_time = fields.CharField(max_length=16, null=True)
    total_outgoing_average_time = fields.FloatField(null=True)
    total_outgoing_average_count = fields.FloatField(null=True)

    # 시간별 환경 센서 (PostgreSQL 배열, 인덱스 = 시간 0~23)
    temp_list: list[float] = ArrayField(element_type="double precision", null=True)
    humi_list: list[float] = ArrayField(element_type="double precision", null=True)
    illu_list: list[float] = ArrayField(element_type="double precision", null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "adl_raw_records"
