from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_differs_from_plain():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False


def test_hash_password_unique_salts():
    h1 = hash_password("samepassword")
    h2 = hash_password("samepassword")
    assert h1 != h2


def test_jwt_roundtrip():
    token = create_access_token(subject="42")
    assert decode_access_token(token) == "42"


def test_jwt_different_subjects():
    t1 = create_access_token(subject="1")
    t2 = create_access_token(subject="2")
    assert decode_access_token(t1) == "1"
    assert decode_access_token(t2) == "2"
