"""Unit tests for pydantic schema validators and serializers."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.patient_monitoring import Administration, AIAnalysis, PatientDetail
from app.schemas.situation import SituationOut


def test_register_request_accepts_8_char_password() -> None:
    # Arrange
    payload = {"username": "u", "email": "u@example.com", "password": "12345678"}

    # Act
    body = RegisterRequest(**payload)

    # Assert
    assert body.password == "12345678"


def test_register_request_rejects_7_char_password() -> None:
    # Arrange
    payload = {"username": "u", "email": "u@example.com", "password": "short7c"}

    # Act / Assert
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(**payload)
    assert "Password must be at least 8 characters" in str(exc_info.value)


def test_register_request_rejects_invalid_email() -> None:
    # Arrange
    payload = {"username": "u", "email": "not-an-email", "password": "validpass123"}

    # Act / Assert
    with pytest.raises(ValidationError):
        RegisterRequest(**payload)


def test_situation_out_serializes_time_as_hhmmss() -> None:
    # Arrange
    payload = {
        "situation_id": 1,
        "patient_id": "p1",
        "name": "김순자",
        "address_summary": "상계동",
        "category": "낙상 의심",
        "detail_reason": None,
        "occurred_at": datetime(2026, 4, 8, 11, 33, 45, tzinfo=UTC),
        "action_status": "조치 대기",
    }
    out = SituationOut(**payload)

    # Act
    dumped = out.model_dump()

    # Assert — serializer converts datetime to "HH:MM:SS"
    assert dumped["occurred_at"] == "11:33:45"


def test_situation_out_serializes_midnight_correctly() -> None:
    # Arrange
    payload = {
        "situation_id": 2,
        "patient_id": "p2",
        "name": "최갑수",
        "address_summary": "역삼동",
        "category": "미응답",
        "detail_reason": "테스트",
        "occurred_at": datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        "action_status": "조치 완료",
    }
    out = SituationOut(**payload)

    # Act
    dumped = out.model_dump()

    # Assert
    assert dumped["occurred_at"] == "00:00:00"


# ---------------------------------------------------------------------------
# 파생 메타 스키마 (AIAnalysis / PatientDetail / Administration)
# ---------------------------------------------------------------------------


def test_administration_normalizes_dict_diseases() -> None:
    # 레거시 적재분의 list[{"name": ...}] 형태도 문자열 리스트로 정규화된다.
    adm = Administration(
        manager_name=None,
        management_level=None,
        diseases=[{"name": "고혈압"}, {"name": "당뇨"}],
    )
    assert adm.diseases == ["고혈압", "당뇨"]


def test_administration_accepts_str_diseases() -> None:
    adm = Administration(manager_name=None, management_level=None, diseases=["고혈압"])
    assert adm.diseases == ["고혈압"]


def test_patient_detail_full_serialization() -> None:
    detail = PatientDetail(
        name="김영숙",
        age="만 78세",
        address_full="서울시 강남구 테헤란로 1",
        cross_verification_level="A",
        doc_no="2026-0661",
        profile_image_url=None,
        ai_analysis=AIAnalysis(
            cross_verification_level="A",
            alert_title="낙상 고위험",
            alert_desc="야간 활동 급증",
        ),
        administration=Administration(
            manager_name="이지은",
            management_level="집중 관리군 (1등급)",
            diseases=["골다공증"],
            next_visit_time="2026-06-09 14:00",
            next_visit_plan="낙상 위험 재평가",
        ),
    )
    dumped = detail.model_dump()
    assert dumped["ai_analysis"] == {
        "cross_verification_level": "A",
        "alert_title": "낙상 고위험",
        "alert_desc": "야간 활동 급증",
    }
    assert dumped["administration"]["next_visit_time"] == "2026-06-09 14:00"
    assert dumped["doc_no"] == "2026-0661"


def test_patient_detail_nullable_derived_fields() -> None:
    # 파생 메타 미적재 — 모든 nullable 필드가 기본값(None)으로 직렬화된다.
    detail = PatientDetail(
        name="홍길동",
        age="만 70세",
        address_full="주소",
        ai_analysis=AIAnalysis(),
        administration=Administration(manager_name=None, management_level=None, diseases=[]),
    )
    dumped = detail.model_dump()
    assert dumped["cross_verification_level"] is None
    assert dumped["profile_image_url"] is None
    assert dumped["ai_analysis"] == {
        "cross_verification_level": None,
        "alert_title": None,
        "alert_desc": None,
    }
    assert dumped["administration"]["next_visit_time"] is None
