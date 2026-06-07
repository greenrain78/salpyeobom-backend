from typing import Any

from tortoise import fields
from tortoise.models import Model


class Report(Model):
    """생성·발송된 위험예측 보고서 이력.

    한 행 = out/reports/ 에 생성된 보고서(PDF) 1건. 분류(위험/주의/사망)는 생성 시점에
    AI 이상탐지 기반(app/services/reports.py:classify)으로 산정해 risk_level 에 저장한다.
    (저장값이 없으면 목록에서 cross_verification_level 폴백.)
    """

    id = fields.IntField(primary_key=True)
    patient: Any = fields.ForeignKeyField("models.Patient", related_name="reports", db_index=True)
    title = fields.CharField(max_length=128)
    file_name = fields.CharField(max_length=255)  # out/reports/ 내 PDF 파일명
    # 생성 시점 분류(위험|주의|사망). 이상탐지 기반(app/services/reports.py:classify)으로
    # 고정 저장. null 이면 목록에서 cross_verification_level 폴백.
    risk_level = fields.CharField(max_length=8, null=True)
    generated_at = fields.DatetimeField(db_index=True)  # 보고서 일자/시각
    emailed_at = fields.DatetimeField(null=True)
    emailed_to = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "reports"
        ordering = ["-generated_at"]
