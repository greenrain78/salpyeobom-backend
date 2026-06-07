import pytest
from httpx import AsyncClient

import app.routers.reports as reports_router

EMAIL_URL = "/api/v1/reports/email"


async def test_email_report_success(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """발송 서비스를 패치해 변환/SMTP 없이 200 응답을 검증한다."""

    async def fake_send(recipient, report_name=None, subject=None, message=None):
        return report_name or "위험예측보고서_661.docx"

    monkeypatch.setattr(reports_router, "send_report_email", fake_send)

    res = await auth_client.post(EMAIL_URL, json={"recipient": "manager@example.com"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["sent_to"] == "manager@example.com"
    assert data["report_name"] == "위험예측보고서_661.docx"


async def test_email_report_requires_auth(client: AsyncClient):
    """토큰 없이 호출하면 401/403."""
    res = await client.post(EMAIL_URL, json={"recipient": "manager@example.com"})
    assert res.status_code in (401, 403)


async def test_email_report_invalid_email(auth_client: AsyncClient):
    """잘못된 수신자 주소는 422."""
    res = await auth_client.post(EMAIL_URL, json={"recipient": "not-an-email"})
    assert res.status_code == 422


async def test_email_report_not_found(auth_client: AsyncClient):
    """존재하지 않는 보고서를 요청하면 404 (실제 경로 해석 로직 검증)."""
    res = await auth_client.post(
        EMAIL_URL,
        json={"recipient": "manager@example.com", "report_name": "no-such-report.docx"},
    )
    assert res.status_code == 404
