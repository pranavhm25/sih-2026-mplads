"""Categorical compliance rule pack (backlog #1).

CAG performance audits of MPLADS documented categorical violations — works at
prohibited categories (religious structures, memorials), payments to ineligible
entities, unpermitted repair/maintenance spend. Statistical anomaly detection
does not target these: a rule/reference-data path does.

Design constraints:
- Pure deterministic matching on normalized text — no LLM, no fuzz.
- Every signal carries its guideline citation as evidence.
- Language is cautious by construction: "compliance indicator — verify against
  the cited guideline", never "fraud" (Prompt-3 §50; PS human-in-the-loop rule).
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.constants import Severity, SignalType, SourceType
from app.models import Project, ProjectSignal
from app.services.detection.signal_factory import add_evidence, make_signal

_WORD = re.compile(r"[a-z ]+")


def _normalize(text: str) -> str:
    """Lowercase, collapse non-letters, single-space — no aggressive stemming."""
    return " ".join(_WORD.findall(text.lower())).strip()


def _match_patterns(text_norm: str, patterns: list[str]) -> str | None:
    """Return the first matched pattern (word-boundary match), else None."""
    for pat in patterns:
        if re.search(rf"\b{re.escape(pat)}\b", text_norm):
            return pat
    return None


def classify_work(description: str) -> dict | None:
    """Return the prohibited-category match for a description, or None."""
    norm = _normalize(description or "")
    if not norm:
        return None
    for entry in C.PROHIBITED_CATEGORY_PATTERNS:
        hit = _match_patterns(norm, entry["patterns"])
        if hit:
            return {"entry": entry, "matched_term": hit}
    return None


def classify_agency(agency: str | None) -> dict | None:
    """Return the payee-type indicator for an implementing agency, or None."""
    if not agency:
        return None
    norm = _normalize(agency)
    for entry in C.INELIGIBLE_PAYEE_PATTERNS:
        hit = _match_patterns(norm, entry["patterns"])
        if hit:
            return {"entry": entry, "matched_term": hit}
    return None


def run_compliance_rules(
    db: Session,
    projects: list[Project],
) -> dict[str, int]:
    """Evaluate categorical compliance for each work; persist signals+evidence.

    Returns per-kind trigger counts. Idempotent with the rule engine: existing
    COMPLIANCE signals for these projects are removed before re-running.
    """
    counters: dict[str, int] = {}
    if not projects:
        return counters

    existing = (
        db.query(ProjectSignal)
        .filter(
            ProjectSignal.project_id.in_([p.id for p in projects]),
            ProjectSignal.signal_type == SignalType.COMPLIANCE,
        )
        .all()
    )
    for s in existing:
        db.delete(s)
    db.flush()

    for p in projects:
        findings: list[dict] = []

        cat = classify_work(p.description or "")
        if cat:
            findings.append(("CATEGORY", cat))

        payee = classify_agency(p.implementing_agency)
        if payee:
            findings.append(("AGENCY", payee))

        for kind, hit in findings:
            entry = hit["entry"]
            matched = hit["matched_term"]
            severity = C.COMPLIANCE_SEVERITY.get(entry["code"], Severity.MEDIUM)
            observed = (
                {"description": p.description, "matched_term": matched}
                if kind == "CATEGORY"
                else {"implementing_agency": p.implementing_agency,
                      "matched_term": matched}
            )
            s = make_signal(
                project_id=p.id,
                signal_type=SignalType.COMPLIANCE,
                severity=severity,
                title=f"Compliance indicator: {entry['label']}",
                explanation=(
                    f"Work description matches the '{entry['label']}' reference "
                    f"category (term: '{matched}'). {entry['guideline']}. This is "
                    f"a compliance indicator for verification against the cited "
                    f"guideline — not a determination of wrongdoing."
                ),
                observed=observed,
                reference={
                    "category_code": entry["code"],
                    "guideline_citation": entry["guideline"],
                },
                difference={"kind": kind, "matched_term": matched},
                source_type=SourceType.RULE,
            )
            db.add(s)
            db.flush()
            db.add(add_evidence(
                s,
                field_name="description" if kind == "CATEGORY"
                else "implementing_agency",
                field_value=(p.description or "")[:300] if kind == "CATEGORY"
                else (p.implementing_agency or "")[:300],
                reference_label="guideline citation",
                reference_value=entry["guideline"],
                calculation=(
                    f"deterministic keyword match on '{matched}' → "
                    f"{entry['code']}"
                ),
                provenance={
                    "rule": "COMPLIANCE",
                    "category_code": entry["code"],
                    "citation": C.COMPLIANCE_GUIDELINE_CITATION,
                },
            ))
            counters[entry["code"]] = counters.get(entry["code"], 0) + 1

    db.flush()
    return counters
