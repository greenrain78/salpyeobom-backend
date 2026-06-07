from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

import app.routers.reports as reports_router
from app.models.patient import Patient
from app.models.report import Report

EMAIL_URL = "/api/v1/reports/email"
LIST_URL = "/api/v1/reports"


async def _make_patient(patient_id: str, name: str, level: str) -> Patient:
    return await Patient.create(
        patient_id=patient_id,
        name=name,
        age=80,
        address_full="서울시 강남구 테스트로 1",
        address_summary="강남구",
        cross_verification_level=level,
    )


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


# ── 보고서 목록 ──────────────────────────────────────────────────────────────


async def test_list_reports_success(auth_client: AsyncClient):
    """목록 조회 — 위험/주의/사망 집계와 일자별 그룹, 등급 파생을 검증한다."""
    p_a = await _make_patient("661", "김영숙", "A")
    p_b = await _make_patient("662", "김순자", "B")
    await Report.create(
        patient=p_a,
        title="661 보고서",
        file_name="r_a.pdf",
        generated_at=datetime(2026, 6, 7, tzinfo=UTC),
    )
    await Report.create(
        patient=p_b,
        title="662 보고서",
        file_name="r_b.pdf",
        generated_at=datetime(2026, 6, 6, tzinfo=UTC),
    )

    res = await auth_client.get(LIST_URL)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 2
    assert data["risk_count"] == 1
    assert data["caution_count"] == 1
    assert data["death_count"] == 0
    assert len(data["groups"]) == 2

    first_item = data["groups"][0]["items"][0]
    assert first_item["patient_name"] == "김영숙"
    assert first_item["risk_level"] == "위험"


async def test_list_reports_uses_stored_risk_level(auth_client: AsyncClient):
    """저장된 Report.risk_level 이 등급(cross_verification_level)보다 우선한다."""
    p = await _make_patient("661", "김영숙", "A")  # 등급 A → 폴백이면 위험
    await Report.create(
        patient=p,
        title="t",
        file_name="s.pdf",
        risk_level="사망",  # 저장된 분류
        generated_at=datetime(2026, 6, 7, tzinfo=UTC),
    )
    res = await auth_client.get(LIST_URL)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["death_count"] == 1
    assert data["risk_count"] == 0
    assert data["groups"][0]["items"][0]["risk_level"] == "사망"


async def test_list_reports_date_filter(auth_client: AsyncClient):
    """date 필터는 해당 일자 보고서만 반환한다."""
    p = await _make_patient("661", "김영숙", "A")
    await Report.create(
        patient=p,
        title="t1",
        file_name="d1.pdf",
        generated_at=datetime(2026, 6, 7, tzinfo=UTC),
    )
    await Report.create(
        patient=p,
        title="t2",
        file_name="d2.pdf",
        generated_at=datetime(2026, 6, 5, tzinfo=UTC),
    )

    res = await auth_client.get(f"{LIST_URL}?date=2026-06-07")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 1
    assert data["groups"][0]["items"][0]["file_name"] == "d1.pdf"


async def test_list_reports_requires_auth(client: AsyncClient):
    """토큰 없이 목록 호출 시 401/403."""
    res = await client.get(LIST_URL)
    assert res.status_code in (401, 403)


async def test_report_file_requires_auth(client: AsyncClient):
    """토큰 없이 파일 호출 시 401/403."""
    res = await client.get(f"{LIST_URL}/1/file")
    assert res.status_code in (401, 403)


async def test_report_file_not_found(auth_client: AsyncClient):
    """존재하지 않는 보고서 파일 요청은 404."""
    res = await auth_client.get(f"{LIST_URL}/99999/file")
    assert res.status_code == 404
