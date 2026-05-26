from pydantic import BaseModel


class Administration(BaseModel):
    manager_name: str | None
    management_level: str | None
    diseases: list[str]


class PatientDetail(BaseModel):
    name: str
    age: str
    address_full: str
    administration: Administration


class PatientListItem(BaseModel):
    patient_id: str
    name: str
    address_summary: str
    manager_name: str | None

    model_config = {"from_attributes": True}


class PatientListData(BaseModel):
    total_count: int
    current_page: int
    total_pages: int
    patients: list[PatientListItem]
