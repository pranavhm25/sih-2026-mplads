"""Agency / contractor concentration detector (PRD R5, TRD §5).

Identifies situations where a single implementing agency holds an unusually
high share of the total sanctioned funds within a district.
This is an investigation indicator for portfolio risk, workload capacity,
and fair allocation — not an accusation of wrongdoing (AGENTS_RULES.md Rule 1).
"""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.constants import Severity, SignalType, SourceType
from app.models import Project, ProjectMetrics, ProjectSignal
from app.services.detection.signal_factory import add_evidence, make_signal

logger = logging.getLogger("drishti.detection.agency")


def _fmt_l(v: float) -> str:
    """Format rupees as lakh for human-readable evidence."""
    return f"₹{v / 100000:.1f}L"


def detect_agency_concentration(
    db: Session,
    projects: list[Project],
) -> dict[str, int]:
    """Calculate agency portfolio share per district; emit signals + evidence.

    Also updates `agency_share_pct` in ProjectMetrics for every evaluated project.
    Returns per-type count dictionary, e.g. {"AGENCY_CONCENTRATION": count}.
    """
    if not projects:
        return {}

    ids = [p.id for p in projects]
    # Clear previous agency concentration signals for idempotency
    db.query(ProjectSignal).filter(
        ProjectSignal.project_id.in_(ids),
        ProjectSignal.signal_type == SignalType.AGENCY_CONCENTRATION,
    ).delete(synchronize_session=False)
    db.flush()

    counters: dict[str, int] = {}

    # Group projects by district
    by_district: dict[str, list[Project]] = {}
    for p in projects:
        if p.district:
            by_district.setdefault(p.district, []).append(p)

    for district, dist_projects in by_district.items():
        # Only consider works with valid positive sanctioned cost
        valid_dist_works = [
            p for p in dist_projects
            if p.sanctioned_cost is not None and float(p.sanctioned_cost) > 0
        ]
        district_works_count = len(valid_dist_works)
        district_total = sum(float(p.sanctioned_cost) for p in valid_dist_works)

        if district_total <= 0:
            continue

        # Group by implementing agency within district
        agency_groups: dict[str, list[Project]] = {}
        for p in valid_dist_works:
            agency = (p.implementing_agency or "").strip()
            if agency:
                agency_groups.setdefault(agency, []).append(p)

        for agency, ag_works in agency_groups.items():
            ag_total = sum(float(p.sanctioned_cost) for p in ag_works)
            ag_works_count = len(ag_works)
            share_pct = (ag_total / district_total) * 100.0

            # Always record the computed agency_share_pct in project metrics for transparency
            for p in ag_works:
                if p.metrics is not None:
                    p.metrics.agency_share_pct = round(share_pct, 2)

            # Check if concentration exceeds detection threshold
            if (
                district_works_count >= C.AGENCY_MIN_DISTRICT_WORKS
                and ag_works_count >= C.AGENCY_MIN_WORKS
                and share_pct >= C.AGENCY_SHARE_TRIGGER_PCT
            ):
                severity = (
                    Severity.CRITICAL
                    if share_pct >= C.AGENCY_SHARE_HIGH_PCT
                    else Severity.HIGH
                )

                for p in ag_works:
                    s = make_signal(
                        project_id=p.id,
                        signal_type=SignalType.AGENCY_CONCENTRATION,
                        severity=severity,
                        title=f"Agency holds {share_pct:.0f}% of district sanctioned value",
                        explanation=(
                            f"Implementing agency '{agency}' accounts for {share_pct:.1f}% "
                            f"({_fmt_l(ag_total)} across {ag_works_count} works) of total sanctioned "
                            f"value in {district} ({_fmt_l(district_total)} across {district_works_count} works). "
                            f"Unusual concentration warrants reviewing agency allocation and portfolio risk."
                        ),
                        observed={
                            "agency": agency,
                            "agency_sanctioned_cost": ag_total,
                            "agency_works_count": ag_works_count,
                            "share_pct": round(share_pct, 1),
                        },
                        reference={
                            "district": district,
                            "district_total_cost": district_total,
                            "district_works_count": district_works_count,
                            "threshold_pct": C.AGENCY_SHARE_TRIGGER_PCT,
                        },
                        difference={"excess_share_pct": round(share_pct - C.AGENCY_SHARE_TRIGGER_PCT, 1)},
                        source_type=SourceType.RULE,
                    )
                    db.add(s)
                    db.flush()
                    db.add(add_evidence(
                        s,
                        field_name="agency district share",
                        field_value=f"{share_pct:.1f}% ({_fmt_l(ag_total)})",
                        reference_label="district total",
                        reference_value=f"{_fmt_l(district_total)} ({district_works_count} works)",
                        calculation=(
                            f"{ag_total:.0f} / {district_total:.0f} × 100 = {share_pct:.1f}% "
                            f"(trigger ≥ {C.AGENCY_SHARE_TRIGGER_PCT:.0f}%)"
                        ),
                        provenance={
                            "rule": "AGENCY_CONCENTRATION",
                            "threshold_pct": C.AGENCY_SHARE_TRIGGER_PCT,
                            "district": district,
                            "agency": agency,
                            "works_count": ag_works_count,
                        },
                    ))
                    counters[SignalType.AGENCY_CONCENTRATION] = counters.get(SignalType.AGENCY_CONCENTRATION, 0) + 1

    db.flush()
    return counters
