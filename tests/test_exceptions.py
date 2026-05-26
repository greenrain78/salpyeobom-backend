"""Unit tests for custom HTTPException subclasses in app/core/exceptions.py."""

from app.core.exceptions import (
    EmailAlreadyExists,
    InvalidCredentials,
    UsernameAlreadyExists,
)


def test_username_already_exists_status_and_detail() -> None:
    # Arrange / Act
    exc = UsernameAlreadyExists()

    # Assert
    assert exc.status_code == 409
    assert exc.detail == "Username already registered"


def test_email_already_exists_status_and_detail() -> None:
    # Arrange / Act
    exc = EmailAlreadyExists()

    # Assert
    assert exc.status_code == 409
    assert exc.detail == "Email already registered"


def test_invalid_credentials_status_detail_and_header() -> None:
    # Arrange / Act
    exc = InvalidCredentials()

    # Assert
    assert exc.status_code == 401
    assert exc.detail == "Incorrect username or password"
    assert exc.headers == {"WWW-Authenticate": "Bearer"}
