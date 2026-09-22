"""Health endpoint — liveness only, never touches the database."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """Lightweight liveness probe (no DB access by design)."""
    return {"status": "ok", "service": "drishti-api"}
