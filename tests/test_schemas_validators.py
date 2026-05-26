"""Unit tests for pydantic schema validators and serializers."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
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
