from pydantic import BaseModel


class DashboardSummary(BaseModel):
    emergency_count: int
    warning_count: int
    normal_count: int
    total_monitoring_count: int
