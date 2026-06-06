"""401 (unauthorized) coverage for all protected endpoints.

Previously only adl_raw and auth/me had explicit 401 tests. This file backfills
401 cases for dashboard, patients, and situations to prevent auth-bypass regressions.
"""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from jose import jwt

from app.config import settings


async def test_dashboard_summary_requires_auth(client: AsyncClient) -> None:
    # Arrange (no token)
    # Act
    res = await client.get("/api/v1/dashboard/summary")
    # Assert — HTTPBearer returns 403 when header missing, 401 with invalid token
    assert res.status_code in (401, 403)


async def test_dashboard_summary_rejects_invalid_token(client: AsyncClient) -> None:
    # Arrange
    headers = {"Authorization": "Bearer not-a-real-token"}
    # Act
    res = await client.get("/api/v1/dashboard/summary", headers=headers)
    # Assert
    assert res.status_code == 401


async def test_patients_list_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/patients")
    assert res.status_code in (401, 403)


async def test_patient_details_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/patients/anything/details")
    assert res.status_code in (401, 403)


async def test_situations_active_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/situations/active")
    assert res.status_code in (401, 403)


async def test_situations_active_rejects_invalid_token(client: AsyncClient) -> None:
    # Arrange
    headers = {"Authorization": "Bearer garbage.token.value"}
    # Act
    res = await client.get("/api/v1/situations/active", headers=headers)
    # Assert
    assert res.status_code == 401


async def test_rejects_validly_signed_token_with_non_numeric_sub(client: AsyncClient) -> None:
    """A token with a valid signature but a non-numeric `sub` must yield 401, not 500.

    `int(sub)` raises ValueError; get_current_user must translate that to 401.
    """
    # Arrange — correctly signed token whose subject is not an integer id
    token = jwt.encode(
        {"sub": "not-a-number", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {token}"}
    # Act
    res = await client.get("/api/v1/dashboard/summary", headers=headers)
    # Assert
    assert res.status_code == 401
