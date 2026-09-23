"""API router aggregation (v1).

Routers:
- health    — /api/v1/health
- projects  — /api/v1/projects, /api/v1/dashboard (work-level intelligence)
- datasets  — /api/v1/datasets (imports, quality, records, detection runs)
- cases     — /api/v1/cases, /api/v1/reports
"""
from fastapi import APIRouter

from app.api.routes import health
from app.api.v1 import cases, datasets, projects

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(datasets.router)
api_router.include_router(projects.router)
api_router.include_router(cases.router)
