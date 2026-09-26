"""SIH demo scenario: a completed human investigation of an AI risk flag.

Creates one InvestigationCase on the flagship duplicate pair (MPL-10281 ↔
MPL-10412) and walks it through the full lifecycle:

    OPEN → UNDER_REVIEW → FIELD_VERIFICATION → CLOSED (NOT_SUBSTANTIATED)

The investigator verifies the two works with the district office and finds
they are separate sanctioned projects — the duplicate concern is not
substantiated. Every step is recorded in the case audit trail; the original
AI-generated signals remain untouched as historical detection evidence.

Demo story this implements (PRD R12 / SIH prompt): "Drishti identifies a
risk. A case enters investigation. The investigator reviews the evidence,
finds a legitimate explanation, and records the outcome 'Not substantiated'.
The audit trail preserves the decision, and the dashboard counts the case as
concluded — not as unresolved."

AI FLAG ≠ FRAUD: the scenario ends in a human outcome, never a verdict.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.constants import CaseStatus, ResolutionReason, ResolutionType
from app.models import InvestigationCase, Officer, Project
from app.services.cases.cases import create_case, update_case

logger = logging.getLogger("drishti.bootstrap")

# The flagship duplicate pair from docs/MEMORY.md / PRD narrative.
_DEMO_WORK_ID = "MPL-10281"

_NOTE_REVIEW = (
    "Opened from the duplicate-candidate signal. Reviewing both works' "
    "sanction records and implementing agencies before field verification."
)

_NOTE_FIELD = (
    "District office verification complete: MPL-10281 and MPL-10412 are "
    "separate sanctioned works — different work orders, different implementing "
    "agencies, and the shared description is standard departmental boilerplate. "
    "The textual similarity alone did not hold up under contextual check."
)


def seed_demo_case_scenario(db: Session) -> InvestigationCase | None:
    """Seed the completed-investigation demo case (idempotent).

    Returns the case (re-created after every demo reseed, since the wipe
    removes all synthetic-dataset cases), or None when the flagship work
    is not present (e.g. a database without the demo dataset).
    """
    project = (
        db.query(Project)
        .filter(Project.work_id == _DEMO_WORK_ID)
        .order_by(Project.ingested_at.desc() if hasattr(Project, "ingested_at") else Project.id)
        .first()
    )
    if project is None:
        logger.info("Demo case scenario skipped: %s not found.", _DEMO_WORK_ID)
        return None

    # A completed case for this project already exists — nothing to do.
    existing = (
        db.query(InvestigationCase)
        .filter(
            InvestigationCase.project_id == project.id,
            InvestigationCase.status.in_(
                [CaseStatus.CLOSED.value, CaseStatus.RESOLVED.value, CaseStatus.ESCALATED.value]
            ),
        )
        .first()
    )
    if existing is not None:
        return existing

    investigator = (
        db.query(Officer).filter(Officer.role == "INVESTIGATOR").order_by(Officer.name).first()
    ) or db.query(Officer).order_by(Officer.name).first()
    if investigator is None:
        logger.info("Demo case scenario skipped: no officers seeded yet.")
        return None

    case = create_case(
        db,
        project=project,
        priority="HIGH",
        assigned_officer_id=investigator.id,
        actor_id=investigator.id,
        note=_NOTE_REVIEW,
    )
    case = update_case(db, case, status=CaseStatus.UNDER_REVIEW.value, actor_id=investigator.id)
    case = update_case(db, case, status=CaseStatus.FIELD_VERIFICATION.value, actor_id=investigator.id)
    db.add(_make_note(db, case, author_id=investigator.id, body=_NOTE_FIELD))

    case = update_case(
        db,
        case,
        status=CaseStatus.CLOSED.value,
        resolution_type=ResolutionType.NOT_SUBSTANTIATED.value,
        resolution_reason=ResolutionReason.FALSE_DUPLICATE_CANDIDATE.value,
        resolution_summary=(
            "Verified with the district office: the two works are separate "
            "sanctioned projects. The duplicate concern was not substantiated; "
            "the flagged similarity is standard departmental boilerplate."
        ),
        actor_id=investigator.id,
    )
    logger.info(
        "Demo case %s seeded: full investigation lifecycle ending NOT_SUBSTANTIATED.",
        case.case_number,
    )
    return case


def _make_note(db: Session, case: InvestigationCase, *, author_id: str, body: str):
    from app.models import CaseNote

    return CaseNote(case_id=case.id, author_id=author_id, body=body)
