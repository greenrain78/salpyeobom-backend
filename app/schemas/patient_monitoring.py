from datetime import date

from pydantic import BaseModel


class AiAnalysis(BaseModel):
    track_A_state: str
    track_B_anomaly: str
    cross_verification_level: str
    alert_title: str | None
    alert_desc: str | None


class Administration(BaseModel):
    manager_name: str | None
    management_level: str | None
    diseases: list[str]
    next_visit_time: str | None
    next_visit_plan: str | None


class PatientDetail(BaseModel):
    doc_no: str | None
    profile_image_url: str | None
    name: str
    age: str
    address_full: str
    ai_analysis: AiAnalysis
    administration: Administration


class PatientListItem(BaseModel):
    patient_id: str
    name: str
    address_summary: str
    manager_name: str | None
    cross_verification_level: str

    model_config = {"from_attributes": True}


class PatientListData(BaseModel):
    total_count: int
    current_page: int
    total_pages: int
    patients: list[PatientListItem]


class TimeseriesPoint(BaseModel):
    date: date
    mae_score: float
    is_anomaly: bool

    model_config = {"from_attributes": True}


class TimeseriesData(BaseModel):
    patient_id: str
    threshold_value: float
    timeseries: list[TimeseriesPoint]
