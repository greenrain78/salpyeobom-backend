import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.main import create_app

TORTOISE_TEST_CONFIG = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "models": {
            "models": ["app.models.user", "app.models.patient"],
            "default_connection": "default",
        }
    },
}


@pytest.fixture
async def client():
    await Tortoise.init(config=TORTOISE_TEST_CONFIG)
    await Tortoise.generate_schemas()

    app = create_app()
    app.router.lifespan_context = None  # lifespan 비활성화 (DB는 위에서 직접 초기화)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    await Tortoise.close_connections()
