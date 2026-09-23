"""Security primitives (backlog #2).

- Passwords: PBKDF2-HMAC-SHA256, 200k iterations, per-user salt.
  Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
- Session tokens: HMAC-SHA256-signed `officer_id.expiry.hmac` strings —
  stateless but revocable by secret rotation; demo seed provides accounts.
- Audit chain: entry_hash = sha256(seq || prev_hash || canonical_json(event)).
  Genesis prev_hash is 64 zeros. `verify_audit_chain` locates the first
  broken link, so tampering is detectable and attributable.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time

from app.core.config import settings

PBKDF2_ITERATIONS = 200_000
SESSION_TTL_SECONDS = 8 * 60 * 60  # one working day


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), int(iterations)
    ).hex()
    return hmac.compare_digest(candidate, digest)


# ---------------------------------------------------------------------------
# Session tokens (stateless, HMAC-signed)
# ---------------------------------------------------------------------------

def _signing_key() -> bytes:
    return settings.secret_key.encode()


def issue_token(officer_id: str, ttl: int = SESSION_TTL_SECONDS) -> str:
    expiry = str(int(time.time()) + ttl)
    mac = hmac.new(_signing_key(), f"{officer_id}.{expiry}".encode(), hashlib.sha256).hexdigest()
    return f"{officer_id}.{expiry}.{mac}"


def verify_token(token: str) -> str | None:
    """Return officer_id for a valid, unexpired token; else None."""
    try:
        officer_id, expiry, mac = token.split(".")
    except ValueError:
        return None
    expected = hmac.new(
        _signing_key(), f"{officer_id}.{expiry}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(mac, expected):
        return None
    if int(expiry) < time.time():
        return None
    return officer_id


# ---------------------------------------------------------------------------
# Tamper-evident audit chain
# ---------------------------------------------------------------------------

GENESIS_PREV_HASH = "0" * 64


def canonical_event_bytes(
    seq: int,
    prev_hash: str,
    action: str,
    actor_id: str | None,
    entity_type: str | None,
    entity_id: str | None,
    payload: dict | None,
    created_at_iso: str,
) -> bytes:
    """Canonical byte encoding of one audit event for hashing.

    Uses sorted-key JSON with explicit separators so encoding is stable
    across processes and platforms. `created_at_iso` must be the stored
    literal (SQLite renders naive UTC); verification reads the same
    attribute back, so hash and verify always agree.
    """
    canonical = json.dumps(
        {
            "seq": seq,
            "prev_hash": prev_hash,
            "action": action,
            "actor_id": actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "payload": payload,
            "created_at": created_at_iso,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return canonical.encode("utf-8")


def _stored_created_at(event) -> str:
    """The timestamp literal exactly as persistence renders it.

    The ORM hands back a tz-aware datetime, but the stored literal is naive
    UTC (SQLite DATETIME storage). Hashing must use the same literal both at
    write and verify time, so normalize tz-aware → naive UTC ISO format.
    """
    from datetime import datetime, timezone

    created = event.created_at
    if isinstance(created, str):
        return created
    if isinstance(created, datetime):
        if created.tzinfo is not None:
            created = created.astimezone(timezone.utc).replace(tzinfo=None)
        return created.isoformat(sep=" ")
    return str(created)


def compute_entry_hash(event_bytes: bytes) -> str:
    return hashlib.sha256(event_bytes).hexdigest()


def next_seq(db) -> int:
    """Highest existing seq + 1 (1 for an empty chain)."""
    from sqlalchemy import func

    from app.models import AuditEvent

    current = db.query(func.max(AuditEvent.seq)).scalar()
    return (current or 0) + 1


def append_audit_event(
    db,
    *,
    action: str,
    actor_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    payload: dict | None = None,
) -> "AuditEvent":
    """Append one hash-linked event. Commits are left to the caller."""
    from app.models import AuditEvent
    from app.models.models import utcnow

    seq = next_seq(db)
    prev = (
        db.query(AuditEvent)
        .filter(AuditEvent.seq == seq - 1)
        .one_or_none()
    )
    prev_hash = prev.entry_hash if prev else GENESIS_PREV_HASH
    created_at = utcnow().replace(tzinfo=None)  # naive UTC — matches storage
    created_at_literal = created_at.isoformat(sep=" ")
    entry_hash = compute_entry_hash(
        canonical_event_bytes(
            seq, prev_hash, action, actor_id, entity_type, entity_id,
            payload, created_at_literal,
        )
    )
    event = AuditEvent(
        seq=seq,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        created_at=created_at,
    )
    db.add(event)
    db.flush()
    return event


def verify_audit_chain(db) -> dict:
    """Walk the full chain; report the first broken link, if any.

    Checks (in order):
    1. seq continuity (no gaps/duplicates)
    2. prev_hash linkage
    3. entry_hash recomputation
    """
    from app.models import AuditEvent

    events = db.query(AuditEvent).order_by(AuditEvent.seq).all()
    expected_seq = 1
    prev_hash = GENESIS_PREV_HASH
    for e in events:
        if e.seq != expected_seq:
            return {
                "valid": False,
                "broken_at_seq": expected_seq,
                "reason": "sequence_gap",
                "events_checked": expected_seq - 1,
            }
        if e.prev_hash != prev_hash:
            return {
                "valid": False,
                "broken_at_seq": e.seq,
                "reason": "prev_hash_mismatch",
                "events_checked": expected_seq - 1,
            }
        recomputed = compute_entry_hash(
            canonical_event_bytes(
                e.seq, e.prev_hash, e.action, e.actor_id, e.entity_type,
                e.entity_id, e.payload, _stored_created_at(e),
            )
        )
        if recomputed != e.entry_hash:
            return {
                "valid": False,
                "broken_at_seq": e.seq,
                "reason": "entry_hash_mismatch",
                "events_checked": expected_seq - 1,
            }
        prev_hash = e.entry_hash
        expected_seq += 1
    return {
        "valid": True,
        "broken_at_seq": None,
        "reason": None,
        "events_checked": len(events),
        "chain_tip": prev_hash,
    }
