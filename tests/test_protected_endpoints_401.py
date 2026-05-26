"""401 (unauthorized) coverage for all protected endpoints.

Previously only adl_raw and auth/me had explicit 401 tests. This file backfills
401 cases for dashboard, patients, and situations to prevent auth-bypass regressions.
"""

from httpx import AsyncClient


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
