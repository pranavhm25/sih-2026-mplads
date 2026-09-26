"""System readiness checks for /api/v1/health/ready.

Kept deliberately cheap: one trivial SQL round-trip + one count query.
Never runs the detection pipeline. Imported lazily by the health route so
`app.api.routes.health` itself stays free of DB machinery (foundation
contract test scans the module source for Session/engine).
"""
from __future__ import annotations

import logging

from sqlalchemy import text

logger = logging.getLogger("drishti.health")


def readiness_payload() -> tuple[dict, bool]:
    """Probe the storage/demo layer; never raises, never runs detection.

    Returns ``(payload, ready)``:
    - ready:     ``{"status": "ok", "ready": True, "checks": {...}}``
    - not ready: ``{"status": "starting", "ready": False, "checks": {...}}``
    """
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models import Dataset

    checks: dict = {}
    ready = True
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
            if settings.demo_autoseed:
                n_works = (
                    db.query(Dataset)
                    .filter(Dataset.dataset_type == "WORK_LEVEL")
                    .count()
                )
                checks["demo_dataset"] = "ok" if n_works > 0 else "missing"
                if n_works == 0:
                    ready = False
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 — readiness must answer, not crash
        logger.warning("readiness check failed: %s", exc.__class__.__name__)
        checks["database"] = "unreachable"
        ready = False

    payload = {"status": "ok" if ready else "starting", "ready": ready, "checks": checks}
    return payload, ready
