from typing import Any

from pydantic import BaseModel, field_validator


class Administration(BaseModel):
    manager_name: str | None
    management_level: str | None
    diseases: list[str]
    next_visit_time: str | None = None
    next_visit_plan: str | None = None

    @field_validator("diseases", mode="before")
    @classmethod
    def _normalize_diseases(cls, v: Any) -> Any:
        """저장된 diseases 가 list[str] 또는 list[{"name": ...}] 두 형태로 섞여 있어
        (레거시 적재분) 문자열 리스트로 정규화한다. 저장 데이터는 건드리지 않는다."""
        if isinstance(v, list):
            return [d.get("name", "") if isinstance(d, dict) else d for d in v]
        return v


class AIAnalysis(BaseModel):
    """교차 검증(위험등급) + AI 분석 문구. adl_raw 파생 아티팩트에서 채워진다.

    프론트 상세 패널은 `ai_analysis.cross_verification_level` 로 경보 테마를 정한다.
    """

    cross_verification_level: str | None = None  # "A" | "B" | "C"
    alert_title: str | None = None
    alert_desc: str | None = None


class PatientDetail(BaseModel):
    name: str
    age: str
    address_full: str
    cross_verification_level: str | None = None
    doc_no: str | None = None
    profile_image_url: str | None = None
    ai_analysis: AIAnalysis
    administration: Administration


class PatientListItem(BaseModel):
    patient_id: str
    name: str
    address_summary: str
    manager_name: str | None
    cross_verification_level: str | None = None

    model_config = {"from_attributes": True}


class PatientListData(BaseModel):
    total_count: int
    current_page: int
    total_pages: int
    patients: list[PatientListItem]
