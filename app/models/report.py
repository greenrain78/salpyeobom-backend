from typing import Any

from tortoise import fields
from tortoise.models import Model


class Report(Model):
    """생성·발송된 위험예측 보고서 이력.

    한 행 = out/reports/ 에 생성된 보고서(PDF) 1건. 위험/주의/사망 등급은 여기
    저장하지 않고 조회 시 FK 대상자의 cross_verification_level 에서 파생한다
    (app/services/reports.py:risk_of).
    """

    id = fields.IntField(primary_key=True)
    patient: Any = fields.ForeignKeyField("models.Patient", related_name="reports", db_index=True)
    title = fields.CharField(max_length=128)
    file_name = fields.CharField(max_length=255)  # out/reports/ 내 PDF 파일명
    generated_at = fields.DatetimeField(db_index=True)  # 보고서 일자/시각
    emailed_at = fields.DatetimeField(null=True)
    emailed_to = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "reports"
        ordering = ["-generated_at"]
