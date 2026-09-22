"""Drishti API — FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.errors import DrishtiError, drishti_error_handler, unhandled_error_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("drishti")

# Idempotent table creation at import time keeps scripts/tests simple;
# production deployments can migrate first and set this aside.
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed the demo dataset when the database is empty.
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

app.include_router(api_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "drishti", "env": settings.app_env}
