from tortoise import Tortoise

from app.config import settings

MODELS = [
    "app.models.user",
    "app.models.patient",
    "app.models.adl_raw",
    "app.models.report",
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


async def init_db(db_url: str | None = None, generate_schemas: bool = False) -> None:
    # generate_schemas 는 로컬 부트스트랩/테스트 전용. 운영 스키마는 aerich 마이그레이션이
    # 단일 진실 공급원이므로 기본값은 False (부팅마다 스키마 자동 생성 → 드리프트 방지).
    await Tortoise.init(
        config={
            "connections": {"default": db_url or settings.DATABASE_URL},
            "apps": {"models": {"models": MODELS, "default_connection": "default"}},
        }
    )
    if generate_schemas:
        await Tortoise.generate_schemas()


async def close_db() -> None:
    await Tortoise.close_connections()
