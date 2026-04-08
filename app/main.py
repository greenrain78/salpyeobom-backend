from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
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

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 에러 핸들러 ───────────────────────────────────────────
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "message": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            f"{' → '.join(str(l) for l in e['loc'] if l != 'body')}: {e['msg']}"
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": errors},
        )

    # ── 라우터 ────────────────────────────────────────────────
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(situations.router)
    app.include_router(patients.router)

    return app


app = create_app()
