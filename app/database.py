from tortoise import Tortoise

from app.config import settings

MODELS = [
    "app.models.user",
    "app.models.patient",
    "app.models.adl",
    "app.models.adl_raw",
    "aerich.models",
]

TORTOISE_ORM = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": MODELS,
            "default_connection": "default",
        }
    },
}


async def init_db(db_url: str | None = None) -> None:
    await Tortoise.init(
        config={
            "connections": {"default": db_url or settings.DATABASE_URL},
            "apps": {"models": {"models": MODELS, "default_connection": "default"}},
        }
    )
    await Tortoise.generate_schemas()


async def close_db() -> None:
    await Tortoise.close_connections()
