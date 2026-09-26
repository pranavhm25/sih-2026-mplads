"""Cases + reports API: /api/v1/cases, /api/v1/reports.

Every case mutation is additionally appended to the tamper-evident audit
chain (backlog #2) — case events remain the domain trail; audit events are
the integrity layer above them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db
from app.models import InvestigationCase, Officer, Project, Report
from app.schemas.schemas import (
    CaseCreate,
    CaseEvidenceCreate,
    CaseEvidenceOut,
    CaseNoteCreate,
    CaseOut,
    CaseUpdate,
    Envelope,
    FeedbackCreate,
    Meta,
    ReportOut,
)
from app.services.cases import cases as case_service
from app.services.detection.fusion import compute_priorities
from app.services.presenters import to_summary
from app.services.reports.report_service import generate_case_report

router = APIRouter()


def _case_out(db: Session, case: InvestigationCase) -> dict:
    from app.schemas.schemas import (
        CaseEventOut,
        CaseNoteOut,
        OfficerOut,
        ProjectSummary,
    )

    project = case.project
    fusion = compute_priorities(db, [project])
    summary = to_summary(project, fusion.get(project.id), case)

    data = CaseOut(
        id=case.id,
        case_number=case.case_number,
        project_id=case.project_id,
        priority=case.priority,
        status=case.status,
        assigned_officer_id=case.assigned_officer_id,
        opened_at=case.opened_at,
        updated_at=case.updated_at,
        closed_at=case.closed_at,
        resolution_type=case.resolution_type,
        resolution_reason=case.resolution_reason,
        resolution_summary=case.resolution_summary,
        project=summary,
        assigned_officer=(OfficerOut.model_validate(case.assigned_officer).model_dump()
                          if case.assigned_officer else None),
        events=[CaseEventOut.model_validate(e).model_dump() for e in case.events],
        notes=[CaseNoteOut.model_validate(n).model_dump() for n in case.notes],
        evidence=[CaseEvidenceOut.model_validate(e).model_dump() for e in case.evidence],
    )
    return data.model_dump()


@router.get("/cases")
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(InvestigationCase).order_by(
        InvestigationCase.opened_at.desc()).all()
    return Envelope(data=[_case_out(db, c) for c in cases], meta=Meta(generated_at=_now()))


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return Envelope(data=_case_out(db, case), meta=Meta(generated_at=_now()))


@router.post("/cases", status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Reject a second active case for the same project. CLOSED (not
    # substantiated) frees the project for a future case if new signals appear.
    existing = (
        db.query(InvestigationCase)
        .filter(InvestigationCase.project_id == project.id)
        .order_by(InvestigationCase.opened_at.desc())
        .first()
    )
    if existing and existing.status not in ("RESOLVED", "CLOSED"):
        raise HTTPException(
            status_code=409,
            detail=f"An active case ({existing.case_number}) already exists for this project.",
        )

    fusion = compute_priorities(db, [project])
    f = fusion.get(project.id, {})
    priority = f.get("level", "MEDIUM")

    case = case_service.create_case(
        db,
        project=project,
        priority=priority,
        assigned_officer_id=payload.assigned_officer_id,
        actor_id=payload.assigned_officer_id,
        note=payload.note,
    )
    security.append_audit_event(
        db, action="CASE_OPENED", actor_id=payload.assigned_officer_id,
        entity_type="investigation_case", entity_id=case.id,
        payload={"case_number": case.case_number, "priority": case.priority,
                 "project_id": project.id},
    )
    db.commit()
    return Envelope(data=_case_out(db, case), meta=Meta(generated_at=_now()))


@router.patch("/cases/{case_id}")
def update_case(case_id: str, payload: CaseUpdate, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    try:
        case = case_service.update_case(
            db,
            case,
            status=payload.status,
            assigned_officer_id=payload.assigned_officer_id
            if payload.assigned_officer_id is not None else ...,
            resolution_type=payload.resolution_type.value if payload.resolution_type else None,
            resolution_reason=payload.resolution_reason.value if payload.resolution_reason else None,
            resolution_summary=payload.resolution_summary,
        )
    except Exception as exc:
        from app.core.errors import DrishtiError
        if isinstance(exc, DrishtiError):
            raise HTTPException(status_code=exc.status_code, detail=exc.message)
        raise
    security.append_audit_event(
        db, action="CASE_UPDATED", entity_type="investigation_case",
        entity_id=case.id,
        payload={"case_number": case.case_number, "status": case.status,
                 "resolution_type": case.resolution_type,
                 "resolution_reason": case.resolution_reason},
    )
    db.commit()
    return Envelope(data=_case_out(db, case), meta=Meta(generated_at=_now()))


@router.post("/cases/{case_id}/notes", status_code=201)
def add_case_note(case_id: str, payload: CaseNoteCreate, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    try:
        case_service.add_note(db, case, author_id=payload.author_id, body=payload.body)
    except Exception as exc:
        from app.core.errors import DrishtiError, NotFoundError
        if isinstance(exc, NotFoundError):
            raise HTTPException(status_code=404, detail=exc.message)
        raise
    security.append_audit_event(
        db, action="CASE_NOTE_ADDED", entity_type="investigation_case",
        entity_id=case.id, payload={"case_number": case.case_number},
    )
    db.commit()
    return Envelope(data=_case_out(db, case), meta=Meta(generated_at=_now()))


@router.post("/cases/{case_id}/evidence", status_code=201)
def attach_case_evidence(case_id: str, payload: CaseEvidenceCreate,
                         db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    try:
        case_service.attach_evidence(
            db, case, signal_id=payload.signal_id,
            description=payload.description, evidence_type=payload.evidence_type,
        )
    except Exception as exc:
        from app.core.errors import DrishtiError
        if isinstance(exc, DrishtiError):
            raise HTTPException(status_code=exc.status_code, detail=exc.message)
        raise
    return Envelope(data=_case_out(db, case), meta=Meta(generated_at=_now()))


@router.post("/cases/{case_id}/feedback")
def record_feedback(case_id: str, payload: FeedbackCreate, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    try:
        case = case_service.record_feedback(
            db, case,
            resolution_type=payload.resolution_type.value,
            officer_id=payload.officer_id,
            summary=payload.summary,
        )
    except Exception as exc:
        from app.core.errors import DrishtiError
        if isinstance(exc, DrishtiError):
            raise HTTPException(status_code=exc.status_code, detail=exc.message)
        raise
    security.append_audit_event(
        db, action="CASE_FEEDBACK_RECORDED", actor_id=payload.officer_id,
        entity_type="investigation_case", entity_id=case.id,
        payload={"case_number": case.case_number,
                 "resolution_type": case.resolution_type},
    )
    db.commit()
    return Envelope(data=_case_out(db, case), meta=Meta(generated_at=_now()))


@router.post("/cases/{case_id}/report", status_code=201)
def generate_report(case_id: str, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    officer = (
        db.query(Officer).filter(Officer.is_active.is_(True)).order_by(Officer.name).first()
    )
    if officer is None:
        raise HTTPException(status_code=409, detail="No active officer available to generate the report.")
    report = generate_case_report(db, case, officer)
    security.append_audit_event(
        db, action="REPORT_GENERATED", actor_id=officer.id,
        entity_type="report", entity_id=report.id,
        payload={"report_number": report.report_number, "case_number": case.case_number},
    )
    db.commit()
    return Envelope(
        data={"report": ReportOut.model_validate(report).model_dump(),
              "download_url": f"/api/v1/reports/{report.id}/download"},
        meta=Meta(generated_at=_now()),
    )


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    from pathlib import Path
    path = Path(report.file_reference)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Report file is no longer available on disk.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{report.report_number}.pdf",
    )


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
