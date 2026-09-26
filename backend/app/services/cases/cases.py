"""Case management service (PRD R12).

Owns the case lifecycle: creation, assignment, status transitions with
mandatory audit events, notes, evidence attachment and officer feedback.
Transitions are validated against CASE_TRANSITIONS; every change is
recorded as a CaseEvent (TR-11).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.constants import (
    CASE_TRANSITIONS,
    CaseStatus,
    ResolutionReason,
    ResolutionType,
)
from app.core.errors import NotFoundError, StateTransitionError, ValidationError400
from app.models import (
    CaseEvent,
    InvestigationCase,
    Officer,
    Project,
    ProjectSignal,
    Report,
)

CASE_SEQUENCE_START = 1001


def next_case_number(db: Session) -> str:
    """Deterministic, human-readable case numbers: DRSHY-C-1001, 1002…"""
    last = (
        db.query(InvestigationCase)
        .order_by(InvestigationCase.case_number.desc())
        .first()
    )
    if last and last.case_number.startswith("DRSHY-C-"):
        try:
            n = int(last.case_number.split("-")[-1]) + 1
        except ValueError:
            n = CASE_SEQUENCE_START
    else:
        n = CASE_SEQUENCE_START
    return f"DRSHY-C-{n}"


def next_case_report_number(db: Session, case: InvestigationCase) -> str:
    """Per-case report numbering: DRSHY-R-1001-1, -2, …"""
    existing = db.query(Report).filter(Report.case_id == case.id).count()
    return f"DRSHY-R-{case.case_number.split('-')[-1]}-{existing + 1}"


def create_case(
    db: Session,
    *,
    project: Project,
    priority: str,
    assigned_officer_id: str | None,
    actor_id: str | None,
    note: str | None = None,
) -> InvestigationCase:
    """Create an OPEN case referencing a project, with audit event."""
    case = InvestigationCase(
        case_number=next_case_number(db),
        project_id=project.id,
        priority=priority,
        status=CaseStatus.OPEN,
        assigned_officer_id=assigned_officer_id,
    )
    db.add(case)
    db.flush()

    db.add(CaseEvent(
        case_id=case.id,
        event_type="CASE_CREATED",
        actor_id=actor_id,
        to_status=CaseStatus.OPEN,
        metadata_json={
            "priority": priority,
            "project_work_id": project.work_id,
            "note": note,
        },
    ))

    if note and actor_id:
        db.add(_make_note(db, case, author_id=actor_id, body=note))

    db.commit()
    return case


def _make_note(db: Session, case: InvestigationCase, *, author_id: str, body: str):
    officer = db.get(Officer, author_id)
    if officer is None:
        raise NotFoundError("Officer", author_id)
    from app.models import CaseNote
    return CaseNote(case_id=case.id, author_id=author_id, body=body)


def add_note(db: Session, case: InvestigationCase, *, author_id: str, body: str):
    note = _make_note(db, case, author_id=author_id, body=body)
    db.add(note)
    db.add(CaseEvent(
        case_id=case.id,
        event_type="NOTE_ADDED",
        actor_id=author_id,
        metadata_json={"note_id": note.id},
    ))
    db.commit()
    return note


def attach_evidence(
    db: Session,
    case: InvestigationCase,
    *,
    signal_id: str | None,
    description: str,
    evidence_type: str = "SIGNAL",
    file_reference: str | None = None,
) -> "object":
    from app.models import CaseEvidence

    if signal_id is not None:
        signal = db.get(ProjectSignal, signal_id)
        if signal is None:
            raise NotFoundError("Signal", signal_id)
        if signal.project_id != case.project_id:
            raise ValidationError400("Signal does not belong to this case's project.")
    ce = CaseEvidence(
        case_id=case.id,
        signal_id=signal_id,
        description=description,
        evidence_type=evidence_type,
        file_reference=file_reference,
    )
    db.add(ce)
    db.add(CaseEvent(
        case_id=case.id,
        event_type="EVIDENCE_ATTACHED",
        metadata_json={"signal_id": signal_id, "evidence_type": evidence_type},
    ))
    db.commit()
    return ce


# Statuses that conclude the investigation and require a recorded outcome.
_CONCLUDING_STATUSES = {CaseStatus.RESOLVED, CaseStatus.ESCALATED, CaseStatus.CLOSED}

# Reopening from a concluded state is a supervisor action — no new outcome
# classification required, and the previous resolution stays on the record.
_REOPENING_STATUSES = {CaseStatus.UNDER_REVIEW}


def update_case(
    db: Session,
    case: InvestigationCase,
    *,
    status: str | None = None,
    assigned_officer_id: str | None = ...,  # type: ignore[assignment]
    resolution_type: str | None = None,
    resolution_reason: str | None = None,
    resolution_summary: str | None = None,
    actor_id: str | None = None,
) -> InvestigationCase:
    """Apply a validated update; every transition writes an audit event."""
    if assigned_officer_id is not ...:
        if assigned_officer_id is not None:
            officer = db.get(Officer, assigned_officer_id)
            if officer is None:
                raise NotFoundError("Officer", assigned_officer_id)
        case.assigned_officer_id = assigned_officer_id
        db.add(CaseEvent(
            case_id=case.id,
            event_type="OFFICER_ASSIGNED",
            actor_id=actor_id,
            metadata_json={"officer_id": assigned_officer_id},
        ))

    if resolution_type is not None:
        if resolution_type not in ResolutionType.__members__:
            raise ValidationError400(f"Unknown resolution type: {resolution_type}")
    if resolution_reason is not None and resolution_reason not in ResolutionReason.__members__:
        raise ValidationError400(f"Unknown resolution reason: {resolution_reason}")

    if status is not None and status != case.status:
        allowed = CASE_TRANSITIONS.get(case.status, set())
        if status not in allowed:
            raise StateTransitionError(
                f"Transition {case.status} → {status} is not allowed. "
                f"Allowed: {', '.join(sorted(allowed)) or 'none'}."
            )
        concluding = status in _CONCLUDING_STATUSES
        if concluding and not resolution_type:
            raise ValidationError400(
                "A resolution classification is required when resolving, "
                "escalating or closing a case."
            )
        if status == CaseStatus.CLOSED:
            # The not-substantiated outcome must carry a structured reason so
            # the audit trail shows WHY the flagged concern was not upheld.
            if resolution_type != ResolutionType.NOT_SUBSTANTIATED.value:
                raise ValidationError400(
                    "Closing a case requires resolution_type NOT_SUBSTANTIATED. "
                    "Use RESOLVED (with CONFIRMED_CONCERN) for a substantiated outcome."
                )
            if not resolution_reason:
                raise ValidationError400(
                    "A structured resolution reason is required when closing a "
                    "case as not substantiated."
                )
            if not (resolution_summary or "").strip():
                raise ValidationError400(
                    "A short free-text explanation is required when closing a "
                    "case as not substantiated."
                )
        from_status = case.status
        case.status = status
        if concluding:
            case.closed_at = datetime.now(timezone.utc)
        elif status in _REOPENING_STATUSES and from_status in _CONCLUDING_STATUSES:
            case.closed_at = None  # reopened — keep resolution_* as history
        db.add(CaseEvent(
            case_id=case.id,
            event_type="STATUS_CHANGED",
            actor_id=actor_id,
            from_status=from_status,
            to_status=status,
            metadata_json={
                **({"resolution_type": resolution_type} if resolution_type else {}),
                **({"resolution_reason": resolution_reason} if resolution_reason else {}),
            },
        ))

    if resolution_type is not None:
        case.resolution_type = resolution_type
    if resolution_reason is not None:
        case.resolution_reason = resolution_reason
    if resolution_summary is not None:
        case.resolution_summary = resolution_summary

    db.commit()
    db.refresh(case)
    return case


def record_feedback(
    db: Session,
    case: InvestigationCase,
    *,
    resolution_type: str,
    officer_id: str,
    summary: str | None = None,
) -> InvestigationCase:
    """Capture the officer's classification (APP_FLOW.md §9)."""
    officer = db.get(Officer, officer_id)
    if officer is None:
        raise NotFoundError("Officer", officer_id)
    if resolution_type not in ResolutionType.__members__:
        raise ValidationError400(f"Unknown resolution type: {resolution_type}")

    case.resolution_type = resolution_type
    if summary:
        case.resolution_summary = summary
    db.add(CaseEvent(
        case_id=case.id,
        event_type="FEEDBACK_RECORDED",
        actor_id=officer_id,
        metadata_json={"resolution_type": resolution_type},
    ))
    db.commit()
    db.refresh(case)
    return case
