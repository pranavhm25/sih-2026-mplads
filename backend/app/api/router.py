"""API router aggregation (v1).

Routers:
- health    — /api/v1/health
- projects  — /api/v1/projects, /api/v1/dashboard (work-level intelligence)
- datasets  — /api/v1/datasets (imports, quality, records, detection runs)
- cases     — /api/v1/cases, /api/v1/reports
- auth      — /api/v1/auth, /api/v1/audit (backlog #2)
- stakeholder — role-scoped views (backlog #4), validation story (#3),
                alert digest (#6), trends (#7)
- cag_validation — CAG-grounded pattern capability report
                  (docs/CAG_VALIDATION.md) + synthetic injection
                  benchmark (docs/SYNTHETIC_VALIDATION.md)
"""
from fastapi import APIRouter

from app.api.routes import health
from app.api.v1 import auth, cag_validation, cases, datasets, projects, stakeholder

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(datasets.router)
api_router.include_router(projects.router)
api_router.include_router(cases.router)
api_router.include_router(stakeholder.router)
api_router.include_router(cag_validation.router)
