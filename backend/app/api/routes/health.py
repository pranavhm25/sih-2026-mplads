"""Health routes.

- GET /api/v1/health        — liveness: instant, no DB, safe for load
                              balancers and Render's healthCheckPath.
- GET /api/v1/health/ready  — readiness: DB reachable + demo data present
                              (when DEMO_AUTOSEED is on). Never runs
                              detection; safe to poll during cold starts.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def health():
    """Lightweight liveness probe (no DB access by design)."""
    return {"status": "ok", "service": "drishti-api"}


@router.get("/health/ready")
def ready():
    """Readiness probe: process is up AND the storage/demo layer is usable.

    Returns HTTP 200 with ready=true once the app can serve the demo,
    503 with a reason otherwise. Kept cheap: never runs detection work.
    """
    from app.services.system_checks import readiness_payload

    payload, is_ready = readiness_payload()
    return JSONResponse(payload, status_code=200 if is_ready else 503)
