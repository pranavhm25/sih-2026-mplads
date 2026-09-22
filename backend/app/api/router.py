"""API router aggregation (foundation §9 structure).

Routes live in app/api/routes/; app/api/v1 remains as the implemented
surface from the first build phase and is mounted alongside.
"""
from fastapi import APIRouter

from app.api.routes import health
from app.api.v1 import cases, datasets, projects

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(cases.router, tags=["cases"])
