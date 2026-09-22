"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import cases, datasets, projects

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(cases.router, tags=["cases"])
