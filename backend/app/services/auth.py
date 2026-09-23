"""Authentication + RBAC (backlog #2, #4).

- login: PBKDF2 verify → HMAC session token → hash-chained AUDIT_LOGIN event
- logout: token invalidation client-side + AUDIT_LOGOUT event
- get_current_officer: bearer-token dependency for protected endpoints
- Demo accounts are seeded (config-gated) so the stack is usable immediately;
  production flips `demo_accounts_enabled=false` and provisions real users.
"""
from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core import security
from app.core.constants import StakeholderRole
from app.core.database import get_db
from app.models import AuditEvent, Officer

logger = logging.getLogger("drishti.auth")

DEMO_PASSWORD = "drishti-demo"


def seed_demo_accounts(db: Session) -> None:
    """Create the four stakeholder demo accounts + admin (idempotent)."""
    accounts = [
        ("ministry@drishti.demo", "Ministry Reviewer", StakeholderRole.MINISTRY, None, None),
        ("snl@drishti.demo", "State Nodal Officer", StakeholderRole.STATE_NODAL, None, "Karnataka"),
        ("district@drishti.demo", "District Authority", StakeholderRole.DISTRICT_AUTHORITY, None, None),
        ("mp@drishti.demo", "Hon'ble MP (Demo)", StakeholderRole.MP, "Bangalore North", "Karnataka"),
        ("admin@drishti.demo", "Platform Admin", StakeholderRole.ADMIN, None, None),
    ]
    for email, name, role, constituency, state in accounts:
        existing = db.query(Officer).filter(Officer.email == email).one_or_none()
        if existing:
            continue
        db.add(Officer(
            name=name,
            email=email,
            role=role.value,
            stakeholder_role=role.value,
            constituency=constituency,
            state=state,
            password_hash=security.hash_password(DEMO_PASSWORD),
            is_active=True,
        ))
    db.commit()


def authenticate(db: Session, email: str, password: str) -> tuple[Officer, str] | None:
    """Verify credentials; return (officer, token) or None."""
    officer = db.query(Officer).filter(Officer.email == email.lower().strip()).one_or_none()
    if officer is None or not officer.is_active:
        return None
    if not security.verify_password(password, officer.password_hash):
        return None
    token = security.issue_token(officer.id)
    return officer, token


def login(db: Session, email: str, password: str, request: Request | None = None) -> dict:
    result = authenticate(db, email, password)
    if result is None:
        security.append_audit_event(
            db,
            action="AUDIT_LOGIN_FAILED",
            entity_type="officer",
            payload={"email": email},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    officer, token = result
    security.append_audit_event(
        db,
        action="AUDIT_LOGIN",
        actor_id=officer.id,
        entity_type="officer",
        entity_id=officer.id,
        payload={"stakeholder_role": officer.stakeholder_role},
    )
    db.commit()
    return {"token": token, "officer": _officer_out(officer)}


def logout(db: Session, officer: Officer) -> dict:
    security.append_audit_event(
        db,
        action="AUDIT_LOGOUT",
        actor_id=officer.id,
        entity_type="officer",
        entity_id=officer.id,
    )
    db.commit()
    return {"ok": True}


def get_current_officer(
    request: Request, db: Session = Depends(get_db)
) -> Officer:
    """Bearer-token auth dependency."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = auth.removeprefix("Bearer ").strip()
    officer_id = security.verify_token(token)
    if officer_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    officer = db.get(Officer, officer_id)
    if officer is None or not officer.is_active:
        raise HTTPException(status_code=401, detail="Account disabled.")
    return officer


def optional_officer(
    request: Request, db: Session = Depends(get_db)
) -> Officer | None:
    """Like get_current_officer but returns None instead of 401.

    Endpoints that must work both pre- and post-auth use this; response
    payloads never change scope silently — callers check and scope explicitly.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    officer_id = security.verify_token(auth.removeprefix("Bearer ").strip())
    if officer_id is None:
        return None
    officer = db.get(Officer, officer_id)
    return officer if officer and officer.is_active else None


def require_stakeholder(*allowed: StakeholderRole):
    """Dependency factory: endpoint accessible only to listed stakeholder roles."""
    def dep(officer: Officer = Depends(get_current_officer)) -> Officer:
        if officer.stakeholder_role not in {r.value for r in allowed}:
            raise HTTPException(status_code=403, detail="Insufficient scope.")
        return officer
    return dep


def _officer_out(o: Officer) -> dict:
    return {
        "id": o.id,
        "name": o.name,
        "email": o.email,
        "role": o.role,
        "stakeholder_role": o.stakeholder_role,
        "constituency": o.constituency,
        "state": o.state,
        "district": o.district,
    }
