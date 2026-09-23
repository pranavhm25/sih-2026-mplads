"""Auth + audit-chain API (backlog #2).

    POST /api/v1/auth/login      → {token, officer}
    POST /api/v1/auth/logout
    GET  /api/v1/auth/me         → current officer profile
    GET  /api/v1/audit/verify    → hash-chain integrity report
    GET  /api/v1/audit/events    → recent events (authenticated)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_audit_chain
from app.models import AuditEvent
from app.schemas.schemas import Envelope, Meta
from app.services import auth as auth_svc
from app.services.auth import get_current_officer

router = APIRouter()


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    result = auth_svc.login(db, payload.email, payload.password)
    return Envelope(data=result, meta=Meta(generated_at=_now()))


@router.post("/auth/logout")
def logout(
    officer=Depends(get_current_officer), db: Session = Depends(get_db)
):
    return Envelope(data=auth_svc.logout(db, officer), meta=Meta(generated_at=_now()))


@router.get("/auth/me")
def me(officer=Depends(get_current_officer)):
    from app.services.auth import _officer_out

    return Envelope(data=_officer_out(officer), meta=Meta(generated_at=_now()))


@router.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db)):
    """Public-in-demo integrity endpoint: walks and verifies the whole chain.

    In production this would be admin-only; left open in demo mode so the
    tamper-evidence capability is demonstrable without setup.
    """
    report = verify_audit_chain(db)
    return Envelope(data=report, meta=Meta(generated_at=_now()))


@router.get("/audit/events")
def audit_events(
    db: Session = Depends(get_db),
    limit: int = 50,
    officer=Depends(get_current_officer),
):
    events = (
        db.query(AuditEvent)
        .order_by(AuditEvent.seq.desc())
        .limit(min(limit, 200))
        .all()
    )
    data = [
        {
            "seq": e.seq,
            "action": e.action,
            "actor_id": e.actor_id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "payload": e.payload,
            "prev_hash": e.prev_hash,
            "entry_hash": e.entry_hash,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
    return Envelope(data=data, meta=Meta(generated_at=_now()))


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
