"""Derived metrics calculation (TR-04).

Computes transparent, reproducible derived values and stores them in
project_metrics — deliberately separate from source facts (projects).
Every value here can be re-derived from the source record.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Project, ProjectMetrics

METRICS_VERSION = "metrics-v1"


def compute_metrics_for_project(p: Project, today: date) -> ProjectMetrics:
    """Derive per-project metrics. None is used when a value is not
    computable — we never fabricate one."""
    m = ProjectMetrics(project_id=p.id, calculation_version=METRICS_VERSION)

    # Financial / physical progress gap (percentage points).
    if p.financial_progress is not None and p.physical_progress is not None:
        m.financial_physical_gap = p.financial_progress - p.physical_progress

    # Expenditure ratio (spend per unit of sanctioned cost).
    if p.expenditure is not None and p.sanctioned_cost:
        m.expenditure_ratio = p.expenditure / p.sanctioned_cost

    # Delay: elapsed vs expected duration for non-completed works.
    expected = p.expected_duration_days
    m.expected_duration_days = expected
    if p.sanction_date is not None:
        end_ref = p.completion_date or today
        elapsed = (end_ref - p.sanction_date).days
        m.elapsed_days = elapsed
        if expected is not None:
            m.delay_days = max(0, elapsed - expected)

    return m


def compute_metrics(db: Session, dataset_id: str, today: date | None = None) -> int:
    """Recompute derived metrics for every project of a dataset."""
    from datetime import date as _date

    today = today or _date.today()
    projects = db.query(Project).filter(Project.dataset_id == dataset_id).all()
    existing = {
        m.project_id: m
        for m in db.query(ProjectMetrics).filter(
            ProjectMetrics.project_id.in_([p.id for p in projects])
        )
    } if projects else {}

    count = 0
    for p in projects:
        m = existing.get(p.id) or ProjectMetrics(project_id=p.id)
        computed = compute_metrics_for_project(p, today)
        for attr in (
            "financial_physical_gap", "expenditure_ratio", "elapsed_days",
            "expected_duration_days", "delay_days", "cost_deviation_pct",
            "peer_median_cost", "peer_p75_cost", "peer_percentile",
        ):
            setattr(m, attr, getattr(computed, attr, None))
        m.calculation_version = METRICS_VERSION
        m.calculated_at = _date.today()
        if m not in db:
            db.add(m)
        count += 1
    db.commit()
    return count
