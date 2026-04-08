from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_db, init_db
from app.routers import auth, dashboard, patients, situations


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
    app.include_router(dashboard.router)
    app.include_router(situations.router)
    app.include_router(patients.router)
    return app


app = create_app()
