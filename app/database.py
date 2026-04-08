from tortoise import Tortoise
from app.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": ["app.models.user", "aerich.models"],
            "default_connection": "default",
        }
    },
}


async def init_db(db_url: str | None = None) -> None:
    config = {
        "connections": {"default": db_url or settings.DATABASE_URL},
        "apps": {
            "models": {
                "models": ["app.models.user", "aerich.models"],
                "default_connection": "default",
            }
        },
    }
    await Tortoise.init(config=config)
    await Tortoise.generate_schemas()


async def close_db() -> None:
    await Tortoise.close_connections()
