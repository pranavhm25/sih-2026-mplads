"""Stakeholder views + decision-support endpoints (backlog #3, #4, #6, #7).

    GET /api/v1/stakeholder/summary   — role-scoped dashboard payload (#4)
    GET /api/v1/validation/summary    — reviewer-agreement precision story (#3)
    GET /api/v1/alerts/digest         — early-warning digest since last review (#6)
    POST /api/v1/alerts/digest/ack    — mark digest reviewed (advances watermark)
    GET /api/v1/trends                — FY-over-FY aggregates from official imports (#7)

Scoping is explicit, never silent: the response carries `scope` describing the
role, its slice, and any limitations. Language stays decision-support cautious.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.constants import CaseStatus, Priority, ResolutionType, StakeholderRole
from app.core.database import get_db
from app.models import (
    AlertDigest,
    Dataset,
    InvestigationCase,
    Officer,
    Project,
    ProjectSignal,
    SchemeAggregate,
)
from app.schemas.schemas import Envelope, Meta
from app.services.auth import get_current_officer, optional_officer

router = APIRouter()

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta(officer: Officer | None = None, **extra) -> Meta:
    return Meta(
        generated_at=_now(),
        is_synthetic=None,
        **extra,
    )


# ---------------------------------------------------------------------------
# Backlog #4 — stakeholder-scoped summary
# ---------------------------------------------------------------------------

@router.get("/stakeholder/summary")
def stakeholder_summary(
    db: Session = Depends(get_db),
    officer: Officer | None = Depends(optional_officer),
):
    """Role-scoped decision-support payload for the four PS-named stakeholders.

    Without auth the endpoint reports `scope: UNAUTHENTICATED` with counts only
    (demo convenience) — never another role's slice. Authenticated calls scope
    by the officer's stakeholder_role: MP → own constituency, DISTRICT → own
    district, STATE_NODAL → own state, MINISTRY/ADMIN → national.
    """
    role = officer.stakeholder_role if officer else None

    # ---- base queries (national scope by default) --------------------------
    project_q = db.query(Project)
    case_q = db.query(InvestigationCase)
    scope_label = "NATIONAL"
    scope_note = "All works, all districts, all states."

    if role == StakeholderRole.MP.value:
        constituency = officer.constituency
        if constituency:
            project_q = project_q.filter(Project.constituency == constituency)
            scope_label = f"CONSTITUENCY:{constituency}"
            scope_note = (
                f"Works in {constituency}. Plain-language summaries; signals are "
                "investigation indicators handled by the district authority."
            )
        else:
            scope_note = "No constituency linked to this MP account."
    elif role == StakeholderRole.DISTRICT_AUTHORITY.value:
        district = officer.district
        if district:
            project_q = project_q.filter(Project.district == district)
            case_q = case_q.join(Project).filter(Project.district == district)
            scope_label = f"DISTRICT:{district}"
            scope_note = f"Works and cases in {district}."
        else:
            scope_note = "No district linked to this account."
    elif role == StakeholderRole.STATE_NODAL.value:
        state = officer.state
        if state:
            project_q = project_q.filter(Project.state == state)
            case_q = case_q.join(Project).filter(Project.state == state)
            scope_label = f"STATE:{state}"
            scope_note = f"Works and cases across {state}."
        else:
            scope_note = "No state linked to this account."

    total_works = project_q.count()
    by_status: dict[str, int] = dict(
        (row[0], row[1])
        for row in project_q.with_entities(Project.status, func.count()).group_by(Project.status).all()
    )
    triggered_q = (
        db.query(ProjectSignal)
        .join(Project, ProjectSignal.project_id == Project.id)
        .filter(ProjectSignal.triggered.is_(True))
    )
    # Apply the same scope filter to signals via subquery of scoped projects.
    scoped_ids = None
    if role in (StakeholderRole.MP.value, StakeholderRole.DISTRICT_AUTHORITY.value,
                StakeholderRole.STATE_NODAL.value):
        scoped_ids = [pid for (pid,) in project_q.with_entities(Project.id).all()]
        if scoped_ids:
            triggered_q = triggered_q.filter(ProjectSignal.project_id.in_(scoped_ids))
        else:
            triggered_q = triggered_q.filter(ProjectSignal.project_id.in_(["__none__"]))

    signals_by_type: dict[str, int] = dict(
        (row[0], row[1])
        for row in triggered_q.with_entities(
            ProjectSignal.signal_type, func.count()
        ).group_by(ProjectSignal.signal_type).all()
    )
    signals_by_severity: dict[str, int] = dict(
        (row[0], row[1])
        for row in triggered_q.with_entities(
            ProjectSignal.severity, func.count()
        ).group_by(ProjectSignal.severity).all()
    )

    # Cases (district/state/ministry see case queues; MP gets a plain summary)
    cases_total = case_q.count()
    cases_open = case_q.filter(
        InvestigationCase.status.notin_(
            [CaseStatus.RESOLVED.value, CaseStatus.ESCALATED.value, CaseStatus.CLOSED.value]
        )
    ).count()
    cases_by_status: dict[str, int] = dict(
        (row[0], row[1])
        for row in case_q.with_entities(InvestigationCase.status, func.count())
        .group_by(InvestigationCase.status).all()
    )

    # MP plain-language slice: own works' signal headlines only
    mp_headlines: list[dict] | None = None
    if role == StakeholderRole.MP.value:
        headlines_q = (
            db.query(ProjectSignal, Project)
            .join(Project, ProjectSignal.project_id == Project.id)
        )
        if scoped_ids:
            headlines_q = headlines_q.filter(ProjectSignal.project_id.in_(scoped_ids))
        headlines_q = headlines_q.filter(
            ProjectSignal.triggered.is_(True),
            ProjectSignal.severity.in_([C.Severity.HIGH.value, C.Severity.CRITICAL.value]),
        )
        mp_headlines = [
            {
                "work": p.work_id,
                "headline": s.title,
                "severity": s.severity,
                "note": "Indicator only — under verification by the district authority.",
            }
            for s, p in headlines_q.limit(10).all()
        ]

    # Ministry extra: worst districts (reuse existing dashboard logic shape)
    district_attention: list[dict] | None = None
    if role in (StakeholderRole.MINISTRY.value, StakeholderRole.ADMIN.value,
                StakeholderRole.STATE_NODAL.value, None):
        rows = (
            db.query(
                Project.district,
                func.count(Project.id),
            )
            .group_by(Project.district)
            .all()
        )
        districts = []
        for district, _cnt in rows:
            q = (
                db.query(ProjectSignal)
                .join(Project, ProjectSignal.project_id == Project.id)
                .filter(
                    Project.district == district,
                    ProjectSignal.triggered.is_(True),
                    ProjectSignal.severity.in_(
                        [C.Severity.HIGH.value, C.Severity.CRITICAL.value]
                    ),
                )
            )
            if scoped_ids:
                q = q.filter(ProjectSignal.project_id.in_(scoped_ids))
            hs = q.count()
            if hs:
                districts.append({"district": district, "high_signals": hs})
        district_attention = sorted(
            districts, key=lambda d: d["high_signals"], reverse=True
        )[:8]

    return Envelope(
        data={
            "scope": {
                "role": role or "UNAUTHENTICATED",
                "label": scope_label,
                "note": scope_note,
            },
            "works": {"total": total_works, "by_status": by_status},
            "signals": {
                "total": sum(signals_by_type.values()),
                "by_type": signals_by_type,
                "by_severity": signals_by_severity,
            },
            "cases": {
                "total": cases_total,
                "open": cases_open,
                "by_status": cases_by_status,
            },
            "mp_headlines": mp_headlines,
            "district_attention": district_attention,
        },
        meta=_meta(officer),
    )


# ---------------------------------------------------------------------------
# Backlog #3 — validation / precision story
# ---------------------------------------------------------------------------

@router.get("/validation/summary")
def validation_summary(db: Session = Depends(get_db)):
    """Reviewer-agreement metrics from the case feedback loop.

    ResolutionType.CONFIRMED_CONCERN / FALSE_POSITIVE / NEEDS_VERIFICATION are
    the ground-truth proxy: precision = confirmed / (confirmed + false_positive).
    Honest denominator handling: with no resolutions yet, precision is null —
    never a fabricated number.
    """
    rows = (
        db.query(InvestigationCase.resolution_type, func.count())
        .filter(InvestigationCase.resolution_type.isnot(None))
        .group_by(InvestigationCase.resolution_type)
        .all()
    )
    counts = {r[0]: r[1] for r in rows}
    confirmed = counts.get(ResolutionType.CONFIRMED_CONCERN.value, 0)
    false_pos = counts.get(ResolutionType.FALSE_POSITIVE.value, 0)
    needs_verification = counts.get(ResolutionType.NEEDS_VERIFICATION.value, 0)

    denom = confirmed + false_pos
    precision = round(confirmed / denom, 4) if denom else None

    # Flag-rate transparency: % of works with ≥1 triggered signal.
    total_works = db.query(Project).count()
    flagged_works = (
        db.query(ProjectSignal.project_id)
        .filter(ProjectSignal.triggered.is_(True))
        .distinct()
        .count()
    )
    flag_rate = round(flagged_works / total_works, 4) if total_works else None

    # Per-signal-type trigger counts + their share of flagged works.
    by_type_rows = (
        db.query(ProjectSignal.signal_type, func.count())
        .filter(ProjectSignal.triggered.is_(True))
        .group_by(ProjectSignal.signal_type)
        .all()
    )
    by_type = {r[0]: r[1] for r in by_type_rows}

    return Envelope(
        data={
            "feedback": {
                "confirmed_concern": confirmed,
                "false_positive": false_pos,
                "needs_verification": needs_verification,
                "precision": precision,
                "note": (
                    "Precision from officer resolutions; null until officers "
                    "close cases with a resolution type."
                ),
            },
            "flag_rate": {
                "flagged_works": flagged_works,
                "total_works": total_works,
                "rate": flag_rate,
                "note": (
                    "Share of works carrying ≥1 triggered signal — the review "
                    "capacity the platform asks of officers."
                ),
            },
            "signals_by_type": by_type,
            "quantified_target": (
                "Flag top ~5% of works for review within 7 days of sanction "
                "(~4,100 works/yr at 18th-LS sanctioned volume)."
            ),
        },
        meta=_meta(),
    )


# ---------------------------------------------------------------------------
# Backlog #6 — alert digest (stateful, per-role watermark)
# ---------------------------------------------------------------------------

_FLOOR_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@router.get("/alerts/digest")
def alert_digest(
    db: Session = Depends(get_db),
    officer: Officer = Depends(get_current_officer),
):
    """New high/critical signals + case movement since this role last reviewed."""
    role = officer.stakeholder_role or StakeholderRole.ADMIN.value
    digest = db.query(AlertDigest).filter(AlertDigest.role == role).one_or_none()
    watermark = digest.last_seen_seq if digest else 0

    floor = (
        C.ALERT_DIGEST_HIGH_FLOOR
        if role in (StakeholderRole.MINISTRY.value, StakeholderRole.ADMIN.value)
        else C.ALERT_DIGEST_CRITICAL_FLOOR
    )
    floor_rank = _FLOOR_RANK[floor]

    cutoff = _digest_watermark_time(db, watermark, role)
    new_signals = (
        db.query(ProjectSignal, Project)
        .join(Project, ProjectSignal.project_id == Project.id)
        .filter(
            ProjectSignal.triggered.is_(True),
            ProjectSignal.created_at > cutoff,
        )
        .order_by(ProjectSignal.created_at.desc())
        .limit(25)
        .all()
    )
    signal_items = [
        {
            "work": p.work_id,
            "district": p.district,
            "signal_type": s.signal_type,
            "severity": s.severity,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
        }
        for s, p in new_signals
        if _FLOOR_RANK.get(s.severity, 0) >= floor_rank
    ]

    cases_moved = (
        db.query(InvestigationCase)
        .filter(InvestigationCase.updated_at > cutoff)
        .order_by(InvestigationCase.updated_at.desc())
        .limit(15)
        .all()
    )
    case_items = [
        {
            "case_number": c.case_number,
            "status": c.status,
            "priority": c.priority,
            "updated_at": c.updated_at.isoformat(),
        }
        for c in cases_moved
        if _FLOOR_RANK.get(c.priority, 0) >= floor_rank
    ]

    return Envelope(
        data={
            "role": role,
            "watermark_seq": watermark,
            "floor_severity": floor,
            "new_signals": signal_items,
            "cases_moved": case_items,
            "counts": {"new_signals": len(signal_items), "cases_moved": len(case_items)},
            "generated_at": _now(),
        },
        meta=_meta(officer),
    )


@router.post("/alerts/digest/ack")
def ack_digest(
    db: Session = Depends(get_db),
    officer: Officer = Depends(get_current_officer),
):
    """Advance this role's digest watermark.

    The watermark is an explicit wall-clock cutoff captured at acknowledge
    time (plus the current audit-seq for provenance). Signal/case timestamps
    are written in the same naive-UTC rendering the DB uses, so the cutoff
    comparison is stable — everything acknowledged now disappears from the
    next digest.
    """
    from app.core import security

    role = officer.stakeholder_role or StakeholderRole.ADMIN.value
    digest = db.query(AlertDigest).filter(AlertDigest.role == role).one_or_none()
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC (matches storage)
    if digest is None:
        digest = AlertDigest(role=role, last_seen_seq=security.next_seq(db))
        db.add(digest)
    else:
        digest.last_seen_seq = security.next_seq(db)
    digest.last_generated_at = now
    # Store the cutoff in payload-carrying column style: reuse created_at as
    # row creation marker and keep the real cutoff in last_generated_at.
    digest_ack_cutoff[role] = now
    db.commit()
    return Envelope(
        data={"role": role, "last_seen_seq": digest.last_seen_seq,
              "acked_at": now.isoformat()},
        meta=_meta(officer),
    )


# In-memory per-role cutoffs for the current process. The durable part is
# last_generated_at on AlertDigest; this dict guards the edge where the
# cutoff must be exact even if the audit-seq event clock drifted.
digest_ack_cutoff: dict[str, datetime] = {}


def _digest_watermark_time(db: Session, seq: int, role: str | None = None) -> datetime:
    """Role watermark → wall-clock cutoff.

    Prefer the explicit acknowledge cutoff (process-local, exact); fall back
    to the audit event at the watermark seq; finally the epoch.
    """
    if role and role in digest_ack_cutoff:
        return digest_ack_cutoff[role]
    from app.models import AuditEvent

    if seq:
        ev = db.query(AuditEvent).filter(AuditEvent.seq == seq).one_or_none()
        if ev:
            created = ev.created_at
            if created.tzinfo is not None:
                created = created.astimezone(timezone.utc).replace(tzinfo=None)
            return created
    return datetime(1970, 1, 1)


# ---------------------------------------------------------------------------
# Backlog #7 — trends from imported SCHEME_AGGREGATE datasets
# ---------------------------------------------------------------------------

@router.get("/trends")
def trends(db: Session = Depends(get_db)):
    """FY-over-FY trend rows from official aggregate imports.

    Only imported data is shown — no calculated-from-unrelated-datasets numbers
    (backlog #7 mirrors Prompt-3 §36 discipline). Empty import history returns
    an empty series with an explicit limitation note.
    """
    aggregates = (
        db.query(SchemeAggregate, Dataset)
        .join(Dataset, SchemeAggregate.dataset_id == Dataset.id)
        .order_by(Dataset.ingested_at.asc(), SchemeAggregate.house.asc())
        .all()
    )
    series: list[dict] = []
    for agg, ds in aggregates:
        series.append({
            "dataset_id": ds.id,
            "dataset_name": ds.name,
            "ingested_at": ds.ingested_at.isoformat() if ds.ingested_at else None,
            "is_synthetic": ds.is_synthetic,
            "house": agg.house,
            "allocated_limit": float(agg.allocated_limit) if agg.allocated_limit else None,
            "works_recommended": agg.works_recommended,
            "works_sanctioned": agg.works_sanctioned,
            "works_completed": agg.works_completed,
            "expenditure": (
                float(agg.expenditure_completed_and_ongoing)
                if agg.expenditure_completed_and_ongoing else None
            ),
            "monetary_unit": agg.monetary_unit,
            "as_of_date": agg.as_of_date.isoformat() if agg.as_of_date else None,
        })

    completion_rates: list[dict] | None = None
    rows_with_counts = [
        s for s in series
        if s["works_sanctioned"] and s["works_completed"] and s["works_sanctioned"] > 0
    ]
    if rows_with_counts:
        completion_rates = [
            {
                "label": f"{s['house'] or 'All'} · {s['dataset_name']}",
                "rate": round(s["works_completed"] / s["works_sanctioned"], 4),
                "is_synthetic": s["is_synthetic"],
            }
            for s in rows_with_counts
        ]

    return Envelope(
        data={
            "series": series,
            "completion_rates": completion_rates,
            "limitation": (
                "e-SAKSHI portal carries works recommended on/after 1 Apr 2023 "
                "only; pre-2023-24 trend analysis is not possible from this "
                "official source."
            ),
        },
        meta=_meta(),
    )
