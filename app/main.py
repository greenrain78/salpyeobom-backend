from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_db, init_db
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Salpyeobom API",
        version="0.1.0",
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )
    app.include_router(auth.router)
    return app


app = create_app()
