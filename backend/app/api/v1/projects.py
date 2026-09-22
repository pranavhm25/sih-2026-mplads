"""Projects + analytics API (TRD §4): /api/v1/projects, /api/v1/dashboard."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_dataset, get_project_or_404
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import InvestigationCase, Officer, Project, ProjectSignal
from app.schemas.schemas import (
    DashboardSummary,
    DatasetOut,
    Envelope,
    Meta,
    ProjectDetail,
    ProjectSummary,
    QueueFilters,
)
from app.services.detection.fusion import compute_priorities
from app.services.presenters import to_detail, to_summary

router = APIRouter()


def _priority_rank(level: str | None) -> int:
    return {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(level or "", 9)


def _cases_by_project(db: Session) -> dict[str, InvestigationCase]:
    cases = db.query(InvestigationCase).all()
    by_project: dict[str, InvestigationCase] = {}
    for c in cases:
        by_project.setdefault(c.project_id, c)
    return by_project


def _envelope(data, db: Session, dataset) -> Envelope:
    return Envelope(
        data=data,
        meta=Meta(
            dataset_version=dataset.version if dataset else None,
            generated_at=datetime.now(timezone.utc).isoformat(),
            is_synthetic=dataset.is_synthetic if dataset else None,
        ),
    )


@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
    priority: str | None = Query(default=None),
    state: str | None = Query(default=None),
    district: str | None = Query(default=None),
    category: str | None = Query(default=None),
    signal_type: str | None = Query(default=None),
    case_status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str = Query(default="priority"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Investigation queue: projects with fused priority + filters."""
    dataset = get_current_dataset(db)
    projects = db.query(Project).filter(Project.dataset_id == dataset.id).all()
    fusion = compute_priorities(db, projects)
    cases = _cases_by_project(db)

    items = [to_summary(p, fusion.get(p.id), cases.get(p.id)) for p in projects]

    if priority:
        items = [i for i in items if i.priority and i.priority.level == priority]
    if state:
        items = [i for i in items if i.state.lower() == state.lower()]
    if district:
        items = [i for i in items if i.district.lower() == district.lower()]
    if category:
        items = [i for i in items if i.category and i.category.lower() == category.lower()]
    if signal_type:
        items = [i for i in items if signal_type in i.primary_signals]
    if case_status:
        items = [i for i in items if i.case_status == case_status]
    if search:
        q = search.lower()
        items = [i for i in items if q in i.work_id.lower() or q in i.description.lower()]

    if sort == "priority":
        items.sort(key=lambda i: (_priority_rank(i.priority.level if i.priority else None),
                                  -(i.priority.score if i.priority else 0)))
    elif sort == "cost":
        items.sort(key=lambda i: -i.sanctioned_cost)
    elif sort == "district":
        items.sort(key=lambda i: i.district)

    page = items[offset: offset + limit]
    return _envelope({"items": page, "total": len(items), "offset": offset, "limit": limit}, db, dataset)


@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Project Intelligence payload: signals, evidence, peers, related."""
    dataset = get_current_dataset(db)
    project = get_project_or_404(db, project_id)
    fusion = compute_priorities(db, [project])
    case = (
        db.query(InvestigationCase)
        .filter(InvestigationCase.project_id == project.id)
        .order_by(InvestigationCase.opened_at.desc())
        .first()
    )
    detail = to_detail(
        project,
        fusion.get(project.id),
        case,
        dataset_version=dataset.version,
        dataset_is_synthetic=dataset.is_synthetic,
    )
    return _envelope(detail, db, dataset)


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    """Command Center aggregate (PRD R9)."""
    dataset = get_current_dataset(db)
    projects = db.query(Project).filter(Project.dataset_id == dataset.id).all()
    fusion = compute_priorities(db, projects)
    cases = _cases_by_project(db)

    items = [to_summary(p, fusion.get(p.id), cases.get(p.id)) for p in projects]

    risk: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    signal_dist: dict[str, int] = {}
    total_value = 0.0
    delayed = 0
    duplicate_candidates = 0
    quality_exceptions = 0

    signal_rows = (
        db.query(ProjectSignal).filter(
            ProjectSignal.project_id.in_([p.id for p in projects]),
            ProjectSignal.triggered.is_(True),
        ).all()
        if projects else []
    )
    for s in signal_rows:
        signal_dist[s.signal_type] = signal_dist.get(s.signal_type, 0) + 1
        if s.signal_type == "DELAY":
            delayed += 1
        elif s.signal_type == "DUPLICATE":
            duplicate_candidates += 1
        elif s.signal_type == "DATA_QUALITY":
            quality_exceptions += 1

    for i in items:
        total_value += i.sanctioned_cost
        if i.priority:
            risk[i.priority.level] = risk.get(i.priority.level, 0) + 1

    districts: dict[str, dict] = {}
    for i in items:
        d = districts.setdefault(i.district, {"district": i.district, "state": i.state,
                                              "works": 0, "value": 0.0, "high": 0})
        d["works"] += 1
        d["value"] += i.sanctioned_cost
        if i.priority and i.priority.level in ("HIGH", "CRITICAL"):
            d["high"] += 1

    queue_preview = sorted(
        items,
        key=lambda i: (_priority_rank(i.priority.level if i.priority else None),
                       -(i.priority.score if i.priority else 0)),
    )[:8]

    open_cases = sum(1 for c in cases.values() if c.status not in ("RESOLVED",))

    summary = DashboardSummary(
        total_works=len(items),
        total_value=round(total_value, 2),
        high_priority_count=risk.get("HIGH", 0) + risk.get("CRITICAL", 0),
        critical_count=risk.get("CRITICAL", 0),
        delayed_count=delayed,
        duplicate_candidate_count=duplicate_candidates,
        quality_exception_count=quality_exceptions,
        case_open_count=open_cases,
        risk_distribution=risk,
        signal_distribution=signal_dist,
        districts=sorted(districts.values(), key=lambda d: -d["high"]),
        queue_preview=queue_preview,
        dataset=DatasetOut.model_validate(dataset).model_dump(),
    )
    return _envelope(summary.model_dump(), db, dataset)


@router.get("/officers")
def list_officers(db: Session = Depends(get_db)):
    officers = db.query(Officer).filter(Officer.is_active.is_(True)).all()
    dataset = get_current_dataset(db)
    from app.schemas.schemas import OfficerOut
    return _envelope([OfficerOut.model_validate(o).model_dump() for o in officers], db, dataset)
