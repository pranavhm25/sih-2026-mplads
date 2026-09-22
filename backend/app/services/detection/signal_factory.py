"""Signal factory — uniform construction of ProjectSignal + evidence.

Every detector (rule, ML, NLP, quality) emits signals through this factory
so each carries: observed value, reference value, difference, explanation,
source version and the recommended verification action (Rule → Evidence →
Action, DESIGN.md §9).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.config import settings
from app.models import ProjectSignal, SignalEvidence


def make_signal(
    *,
    project_id: str,
    signal_type: str,
    severity: str,
    title: str,
    explanation: str,
    observed: Any = None,
    reference: Any = None,
    difference: Any = None,
    source_type: str,
    source_version: str | None = None,
) -> ProjectSignal:
    """Build an un-persisted ProjectSignal (caller adds to session)."""
    return ProjectSignal(
        project_id=project_id,
        signal_type=signal_type,
        severity=severity,
        triggered=True,
        title=title,
        explanation=explanation,
        observed_value=_as_json(observed),
        reference_value=_as_json(reference),
        difference_value=_as_json(difference),
        source_type=source_type,
        source_version=source_version or settings.ruleset_version,
    )


def add_evidence(
    signal: ProjectSignal,
    *,
    field_name: str,
    field_value: Any,
    reference_label: str | None = None,
    reference_value: Any = None,
    calculation: str | None = None,
    provenance: dict | None = None,
) -> SignalEvidence:
    """Attach one evidence row to a signal."""
    return SignalEvidence(
        signal_id=signal.id,
        field_name=field_name,
        field_value=_to_text(field_value),
        reference_label=reference_label,
        reference_value=_to_text(reference_value),
        calculation=calculation,
        provenance=provenance or {},
    )


def recommended_action(signal_type: str) -> str:
    """Recommended verification action for a signal type (APP_FLOW.md §7)."""
    return C.RECOMMENDED_VERIFICATION.get(
        signal_type, "Review the source record and confirm the reported values."
    )


def _as_json(value: Any) -> dict | None:
    """Wrap scalars into JSON-friendly dicts with a consistent shape."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return {"value": value}


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
