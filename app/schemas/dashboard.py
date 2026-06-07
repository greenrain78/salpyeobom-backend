from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_monitoring_count: int
    # 활성 상황을 카테고리로 버킷팅한 건수 (대시보드 상단 통계 카드)
    emergency_count: int = 0  # 낙상·응급·사망
    warning_count: int = 0  # 미응답·지연
    normal_count: int = 0  # 전체 - (응급 + 경고)
