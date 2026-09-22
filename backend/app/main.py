"""Drishti API — FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import DrishtiError, drishti_error_handler, unhandled_error_handler

setup_logging()
logger = logging.getLogger("drishti")


def _safe_db_label() -> str:
    """Database kind only — never credentials — for startup logs."""
    return "sqlite" if settings.is_sqlite else settings.database_url.split("://")[0]


logger.info("Starting Drishti API (env=%s, db=%s)", settings.app_env, _safe_db_label())


# Idempotent schema creation for DEVELOPMENT convenience only.
# Production deployments must apply Alembic migrations instead
# (alembic upgrade head) — see backend/alembic/.
if settings.app_env != "production":
    from app.db import create_all
    create_all()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed the demo dataset when the database is empty.
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        if settings.demo_autoseed:
            from app.services.bootstrap import bootstrap
            bootstrap(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Drishti — MPLADS Risk Intelligence & Investigation Platform",
    version="0.1.0",
    description=(
        "Investigation-first decision support for MPLADS. Drishti detects "
        "potential irregularities, explains the evidence, and prioritizes "
        "works for human investigation. It never declares a project fraudulent."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(DrishtiError, drishti_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic/FastAPI validation failures in the standard error envelope."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": {".".join(str(loc) for loc in e.get("loc", [])): e.get("msg")
                            for e in exc.errors()},
            }
        },
    )


app.include_router(api_router)


@app.get("/api/health")
def health_legacy():
    """Legacy alias kept for existing clients."""
    return {"status": "ok", "app": "drishti", "env": settings.app_env}
