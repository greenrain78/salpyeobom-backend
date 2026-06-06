from datetime import date

from pydantic import BaseModel


class AdlRawRecipientItem(BaseModel):
    """사람-그룹 목록의 한 행 — care_recipient_id 단위로 집계된 인적 정보+카운트."""

    care_recipient_id: str
    age: int | None
    sex: str | None
    alone: str | None
    district: str | None
    total_records: int
    source_type_counts: dict[str, int]
    last_event_date: date | None
    first_event_date: date | None


class AdlRawRecipientsData(BaseModel):
    items: list[AdlRawRecipientItem]
    total: int
    page: int
    page_size: int


class AdlRawRecordSummary(BaseModel):
    """한 사람의 일자별 레코드 목록에 쓰이는 요약 행 — 시계열 배열 제외."""

    model_config = {"from_attributes": True}

    id: int
    source_type: str
    lifeog_date: date | None
    emergency_date: date | None
    death_date: date | None
    aix_d: float | None
    total_aix_sum: float | None
    night_aix_ratio: float | None
    outgoing_count_d: int | None


class AdlRawRecipientRecordsData(BaseModel):
    care_recipient_id: str
    items: list[AdlRawRecordSummary]
    total: int
    page: int
    page_size: int


class AdlRawListItem(BaseModel):
    """GET /api/v1/adl-raw 목록 한 행 — 배열 컬럼 제외."""

    model_config = {"from_attributes": True}

    id: int
    care_recipient_id: str
    source_type: str
    age: int | None
    sex: str | None
    alone: str | None
    district: str | None
    lifeog_date: date | None
    emergency_date: date | None
    death_date: date | None
    aix_d: float | None
    total_aix_sum: float | None
    night_aix_ratio: float | None
    outgoing_count_d: int | None


class AdlRawListData(BaseModel):
    items: list[AdlRawListItem]
    total: int
    page: int
    page_size: int
    source_type_counts: dict[str, int]
    unique_recipient_count: int


class AdlRawDetail(BaseModel):
    # Identity
    id: int
    source_type: str

    # Basic info
    care_recipient_id: str
    age: int | None
    sex: str | None
    alone: str | None
    vision: str | None
    hearing: str | None
    dosage: str | None
    district: str | None
    house_structure: str | None
    room_no: int | None
    bath_location: str | None

    # Event info
    lifeog_date: date | None
    emergency_date: date | None
    emergency_record: str | None
    occurrence_place: str | None
    on_site: str | None
    hospital_transfer: str | None
    hospital_treatment: str | None
    death_date: date | None
    death_record: str | None

    # AIX analytics
    aix_d: float | None
    aix_1_eq_0_repeat_count: int | None
    total_aix_sum: float | None
    total_aix_inc_ratio: float | None
    night_aix_ratio: float | None
    total_age_aix_ratio: float | None

    # Sleep analytics
    sleep_start_time_d: str | None
    sleep_end_time_d: str | None
    total_sleep_period: float | None
    total_sleep_aix_ratio: float | None

    # Bath analytics
    bath_count_d: int | None
    bath_time_d: float | None
    bath_nomove_time: float | None
    bath_count_in_sleep: int | None
    bath_time_per_count: float | None
    total_bath_average_count: float | None

    # Outgoing analytics
    outgoing_count_d: int | None
    outgoing_time_d: float | None
    outgoing_late_night_count_d: int | None
    outgoing_late_night_time_d: float | None
    last_outgoing_time: str | None
    total_outgoing_average_time: float | None
    total_outgoing_average_count: float | None

    # Hourly arrays (24 elements, direct passthrough from model)
    aix_h_list: list[int] | None
    temp_list: list[float] | None
    humi_list: list[float] | None
    illu_list: list[float] | None

    # Derived 24h aggregates (computed in router, not stored in DB)
    outgoing_24h: list[int] | None
    sleep_depth_24h: list[float] | None

    # Metadata
    created_at: str | None = None
