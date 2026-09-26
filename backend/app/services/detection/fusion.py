"""Evidence fusion engine (PRD R8, TR-09).

Combines independent signals into an explainable investigation priority.
The decomposition is always preserved: every priority carries the signal
count, per-signal weighted contributions and human-readable reasons — the
UI shows the reasons, not just the score (AGENTS_RULES.md Rule 3).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.constants import Priority, SignalType
from app.models import Project, ProjectSignal


def priority_label(score: float) -> str:
    """Map weighted evidence score to a priority band.

    Bands are documented thresholds, not black-box outputs:
      < 2.0 LOW · < 4.5 MEDIUM · < 7.0 HIGH · >= 7.0 CRITICAL
    """
    if score < 2.0:
        return Priority.LOW
    if score < 4.5:
        return Priority.MEDIUM
    if score < 7.0:
        return Priority.HIGH
    return Priority.CRITICAL


def fuse_project(signals: list[ProjectSignal]) -> dict:
    """Compute the fused priority for one project from its signals."""
    contributions: list[dict] = []
    total = 0.0
    for s in signals:
        if not s.triggered:
            continue
        weight = C.SIGNAL_WEIGHTS.get(s.signal_type, 1.0)
        mult = C.SEVERITY_MULTIPLIER.get(s.severity, 1.0)
        # Contextual gating for duplicate signals (TR-07, "similarity ≠
        # duplication"): a text-only or contradictory-context duplicate
        # candidate contributes a reduced share, so textual similarity alone
        # cannot drive an unjustified priority.
        weight_multiplier = 1.0
        diff = getattr(s, "difference_value", None)
        if (
            s.signal_type == SignalType.DUPLICATE
            and isinstance(diff, dict)
            and diff.get("contextual_confidence") in ("low", "unavailable")
        ):
            weight_multiplier = C.DUPLICATE_WEAK_CONFIDENCE_WEIGHT
        contribution = round(weight * mult * weight_multiplier, 2)
        total += contribution
        contributions.append({
            "signal_type": s.signal_type,
            "severity": s.severity,
            "title": s.title,
            "contribution": contribution,
        })

    # Multi-signal convergence bonus: independent engines agreeing is the
    # strongest indicator — reflect that in the priority, visibly.
    source_types = {
        s.source_type for s in signals
        if s.triggered and s.source_type in (C.SourceType.RULE, C.SourceType.ML, C.SourceType.NLP)
    }
    convergence_bonus = 0.0
    if len(source_types) >= 2:
        convergence_bonus = 1.5
    if len(source_types) >= 3:
        convergence_bonus = 3.0
    total += convergence_bonus

    return {
        "score": round(total, 2),
        "signal_count": len(contributions),
        "level": priority_label(total),
        "reasons": [c["title"] for c in contributions],
        "contributions": contributions,
        "convergence_bonus": convergence_bonus,
        "engines": sorted(source_types),
    }


def compute_priorities(db: Session, projects: list[Project]) -> dict[str, dict]:
    """Fuse evidence for each project. Returns {project_id: fusion-dict}."""
    ids = [p.id for p in projects]
    signals = (
        db.query(ProjectSignal).filter(ProjectSignal.project_id.in_(ids)).all()
        if ids else []
    )
    by_project: dict[str, list[ProjectSignal]] = {}
    for s in signals:
        by_project.setdefault(s.project_id, []).append(s)

    return {pid: fuse_project(sigs) for pid, sigs in by_project.items()}
