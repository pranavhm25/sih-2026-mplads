"""Data-quality engine (PRD R2).

Deterministic checks over ingested projects. Each issue becomes a
DATA_QUALITY signal so quality exceptions remain visible in the queue,
Project Intelligence and the dashboard compliance count. This layer runs
before any anomaly detection (TR-03).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.constants import Severity, SignalType, SourceType
from app.models import Dataset, Project, ProjectSignal, SignalEvidence
from app.services.detection.signal_factory import make_signal


def run_quality_checks(db: Session, dataset: Dataset) -> dict:
    """Run quality rules over all projects of a dataset.

    Returns a summary dict and persists DATA_QUALITY signals + evidence.
    Existing quality signals for these projects are replaced.
    """
    projects = db.query(Project).filter(Project.dataset_id == dataset.id).all()
    issues: list[dict] = []
    counters = {
        "completion_before_sanction": 0,
        "expenditure_above_sanctioned": 0,
        "progress_above_100": 0,
        "missing_mandatory": 0,
        "duplicate_work_id": 0,
        "invalid_numeric": 0,
    }

    # Remove previous quality signals for this dataset's projects.
    project_ids = [p.id for p in projects]
    if project_ids:
        db.query(ProjectSignal).filter(
            ProjectSignal.project_id.in_(project_ids),
            ProjectSignal.signal_type == SignalType.DATA_QUALITY,
        ).delete(synchronize_session=False)

    seen_work_ids: set[str] = set()

    for p in projects:
        def add_issue(rule: str, severity: str, field: str | None, detail: str,
                      observed, reference=None, difference=None) -> None:
            counters[rule] = counters.get(rule, 0) + 1
            issues.append({
                "work_id": p.work_id, "project_id": p.id,
                "rule": rule, "severity": severity,
                "field": field, "detail": detail,
            })
            signal = make_signal(
                project_id=p.id,
                signal_type=SignalType.DATA_QUALITY,
                severity=severity,
                title=_TITLES[rule],
                explanation=detail,
                observed=observed,
                reference=reference,
                difference=difference,
                source_type=SourceType.DATA_QUALITY,
            )
            db.add(signal)
            db.flush()
            db.add(SignalEvidence(
                signal_id=signal.id,
                field_name=field or rule,
                field_value=str(observed) if observed is not None else "missing",
                reference_label="expected",
                reference_value=str(reference) if reference is not None else None,
                calculation=detail,
                provenance={"rule": rule, "engine": "quality", "version": "v1"},
            ))

        # 1. Completion before sanction
        if p.completion_date and p.sanction_date and p.completion_date < p.sanction_date:
            add_issue(
                "completion_before_sanction", Severity.HIGH, "completion_date",
                f"Completion date {p.completion_date} precedes sanction date "
                f"{p.sanction_date}.",
                observed=str(p.completion_date), reference=f">= {p.sanction_date}",
            )

        # 2. Expenditure above sanctioned cost
        if p.expenditure is not None and p.expenditure > p.sanctioned_cost:
            add_issue(
                "expenditure_above_sanctioned", Severity.HIGH, "expenditure",
                f"Expenditure ₹{p.expenditure:,.0f} exceeds sanctioned cost "
                f"₹{p.sanctioned_cost:,.0f}.",
                observed=float(p.expenditure), reference=float(p.sanctioned_cost),
                difference=float(p.expenditure - p.sanctioned_cost),
            )

        # 3. Progress above 100%
        for field, value in (("financial_progress", p.financial_progress),
                             ("physical_progress", p.physical_progress)):
            if value is not None and value > 100:
                add_issue(
                    "progress_above_100", Severity.MEDIUM, field,
                    f"{field.replace('_', ' ').capitalize()} is {value}% (above 100%).",
                    observed=float(value), reference="<= 100",
                )

        # 4. Missing mandatory / expected fields
        for field in ("mp_name", "category", "expenditure", "location_text",
                      "latitude", "expected_duration_days"):
            if getattr(p, field, None) in (None, ""):
                add_issue(
                    "missing_mandatory", Severity.LOW, field,
                    f"Field '{field}' is missing.",
                    observed=None,
                )

        # 5. Duplicate work IDs within the dataset
        if p.work_id in seen_work_ids:
            add_issue(
                "duplicate_work_id", Severity.HIGH, "work_id",
                f"Work ID {p.work_id} appears more than once in the dataset.",
                observed=p.work_id, reference="unique",
            )
        seen_work_ids.add(p.work_id)

        # 6. Invalid numerics (negative costs or progress)
        for field, value in (("estimated_cost", p.estimated_cost),
                             ("sanctioned_cost", p.sanctioned_cost),
                             ("financial_progress", p.financial_progress),
                             ("physical_progress", p.physical_progress)):
            if value is not None and value < 0:
                add_issue(
                    "invalid_numeric", Severity.MEDIUM, field,
                    f"{field.replace('_', ' ').capitalize()} is negative ({value}).",
                    observed=float(value), reference=">= 0",
                )

    summary = {
        "total_rows": len(projects),
        "rows_with_issues": len({i["project_id"] for i in issues}),
        "total_issues": len(issues),
        "counters": counters,
    }
    dataset.quality_status = (
        "VALID" if not issues else
        "VALID_WITH_WARNINGS" if len(issues) < max(3, len(projects) * 0.2) else "INVALID"
    )
    dataset.quality_summary = summary
    db.commit()
    return summary


_TITLES = {
    "completion_before_sanction": "Completion date precedes sanction date",
    "expenditure_above_sanctioned": "Expenditure exceeds sanctioned cost",
    "progress_above_100": "Progress reported above 100%",
    "missing_mandatory": "Mandatory field missing",
    "duplicate_work_id": "Duplicate work ID",
    "invalid_numeric": "Invalid numeric value",
}
