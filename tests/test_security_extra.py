"""Additional security unit tests — JWT expiry and signature failures."""

from datetime import UTC, datetime, timedelta

import pytest
from jose import JWTError, jwt

from app.config import settings
from app.core.security import create_access_token, decode_access_token


def test_decode_access_token_rejects_tampered_signature() -> None:
    # Arrange — generate a valid token, then mutate the last char of the signature
    token = create_access_token(subject="42")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    # Act / Assert
    with pytest.raises(JWTError):
        decode_access_token(tampered)


def test_decode_access_token_rejects_expired_token() -> None:
    # Arrange — manually craft a token with an expiry in the past
    expired_payload = {
        "sub": "99",
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    # Act / Assert
    with pytest.raises(JWTError):
        decode_access_token(expired_token)


def test_decode_access_token_rejects_wrong_secret() -> None:
    # Arrange — token signed with a different secret
    foreign_token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "completely-different-secret",
        algorithm=settings.ALGORITHM,
    )

    # Act / Assert
    with pytest.raises(JWTError):
        decode_access_token(foreign_token)
