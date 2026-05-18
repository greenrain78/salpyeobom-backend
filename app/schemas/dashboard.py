from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_monitoring_count: int
