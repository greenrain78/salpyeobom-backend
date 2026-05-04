from httpx import AsyncClient

from app.core.security import decode_access_token

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

VALID_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepass123",
}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


async def test_register_success(client: AsyncClient):
    res = await client.post(REGISTER_URL, json=VALID_USER)
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == VALID_USER["username"]
    assert data["email"] == VALID_USER["email"]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data


async def test_register_duplicate_username(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    res = await client.post(
        REGISTER_URL,
        json={**VALID_USER, "email": "other@example.com"},
    )
    assert res.status_code == 409
    assert "Username" in res.json()["message"]


async def test_register_duplicate_email(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    res = await client.post(
        REGISTER_URL,
        json={**VALID_USER, "username": "otheruser"},
    )
    assert res.status_code == 409
    assert "Email" in res.json()["message"]


async def test_register_password_too_short(client: AsyncClient):
    res = await client.post(
        REGISTER_URL,
        json={**VALID_USER, "password": "short"},
    )
    assert res.status_code == 422


async def test_register_invalid_email(client: AsyncClient):
    res = await client.post(
        REGISTER_URL,
        json={**VALID_USER, "email": "not-an-email"},
    )
    assert res.status_code == 422


async def test_register_missing_fields(client: AsyncClient):
    res = await client.post(REGISTER_URL, json={"username": "only"})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_success(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    res = await client.post(
        LOGIN_URL,
        json={"username": VALID_USER["username"], "password": VALID_USER["password"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_jwt_contains_user_id(client: AsyncClient):
    reg = await client.post(REGISTER_URL, json=VALID_USER)
    user_id = reg.json()["id"]

    res = await client.post(
        LOGIN_URL,
        json={"username": VALID_USER["username"], "password": VALID_USER["password"]},
    )
    token = res.json()["access_token"]
    assert decode_access_token(token) == str(user_id)


async def test_login_wrong_password(client: AsyncClient):
    await client.post(REGISTER_URL, json=VALID_USER)
    res = await client.post(
        LOGIN_URL,
        json={"username": VALID_USER["username"], "password": "wrongpassword"},
    )
    assert res.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient):
    res = await client.post(
        LOGIN_URL,
        json={"username": "ghost", "password": "doesntmatter"},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Me (protected)
# ---------------------------------------------------------------------------


async def _get_token(client: AsyncClient) -> str:
    await client.post(REGISTER_URL, json=VALID_USER)
    res = await client.post(
        LOGIN_URL,
        json={"username": VALID_USER["username"], "password": VALID_USER["password"]},
    )
    return res.json()["access_token"]


async def test_me_success(client: AsyncClient):
    token = await _get_token(client)
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == VALID_USER["username"]
    assert data["email"] == VALID_USER["email"]
    assert "hashed_password" not in data


async def test_me_no_token(client: AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code in (401, 403)


async def test_me_invalid_token(client: AsyncClient):
    res = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert res.status_code == 401
