import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.user import User

TORTOISE_TEST_CONFIG = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "models": {
            "models": ["app.models.user", "app.models.patient", "app.models.adl_raw"],
            "default_connection": "default",
        }
    },
}


@pytest.fixture
async def client():
    await Tortoise.init(config=TORTOISE_TEST_CONFIG)
    await Tortoise.generate_schemas()

    app = create_app()
    app.router.lifespan_context = None

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    await Tortoise.close_connections()


@pytest.fixture
async def auth_client(client: AsyncClient):
    """인증된 클라이언트 — 보호된 엔드포인트 테스트에 사용"""
    user = await User.create(
        username="testadmin",
        email="admin@test.com",
        hashed_password=hash_password("adminpass123"),
    )
    token = create_access_token(subject=str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    return client
