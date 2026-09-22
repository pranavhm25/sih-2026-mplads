"""Rule engine — deterministic, explainable detection rules (TR-05).

Each rule independently produces structured evidence. Rules never declare
wrongdoing; they record that an observed value differs from a reference
with a defined, visible threshold.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.config import settings
from app.core.constants import Severity, SignalType, SourceType
from app.models import Project, ProjectMetrics, ProjectSignal
from app.services.detection.signal_factory import add_evidence, make_signal


def _fmt_l(v: float) -> str:
    """Format rupees as lakh for human-readable evidence."""
    return f"₹{v / 100000:.1f}L"


def run_rule_engine(
    db: Session,
    projects: list[Project],
    today: date,
) -> dict[str, int]:
    """Run all rules; persist signals + evidence. Returns per-type counts."""
    counters: dict[str, int] = {}
    existing_signals = (
        db.query(ProjectSignal)
        .filter(
            ProjectSignal.project_id.in_([p.id for p in projects]),
            ProjectSignal.signal_type != C.SignalType.DATA_QUALITY,
        )
        .all()
        if projects else []
    )
    for s in existing_signals:
        db.delete(s)
    db.flush()

    for p in projects:
        m: ProjectMetrics | None = p.metrics

        # ---- Rule 1: cost anomaly (peer-context based) -------------------
        if m and m.cost_deviation_pct is not None and m.peer_median_cost is not None:
            dev = float(m.cost_deviation_pct)
            if dev >= C.COST_DEVIATION_TRIGGER_PCT:
                severity = (
                    Severity.CRITICAL if dev >= C.COST_DEVIATION_HIGH_PCT else Severity.HIGH
                )
                s = make_signal(
                    project_id=p.id,
                    signal_type=SignalType.COST_ANOMALY,
                    severity=severity,
                    title=f"Cost {_fmt_l(float(p.sanctioned_cost))} is {dev:+.0f}% vs peer median",
                    explanation=(
                        f"Sanctioned cost {_fmt_l(float(p.sanctioned_cost))} is {dev:+.0f}% "
                        f"above the peer median {_fmt_l(float(m.peer_median_cost))} "
                        f"(district/category peers, n={_peer_count(m)}). "
                        f"Peer P75: {_fmt_l(float(m.peer_p75_cost))}."
                    ),
                    observed={"sanctioned_cost": float(p.sanctioned_cost)},
                    reference={"peer_median": float(m.peer_median_cost),
                               "peer_p75": float(m.peer_p75_cost)},
                    difference={"deviation_pct": dev},
                    source_type=SourceType.RULE,
                )
                db.add(s)
                db.flush()
                db.add(add_evidence(
                    s,
                    field_name="sanctioned_cost",
                    field_value=_fmt_l(float(p.sanctioned_cost)),
                    reference_label="peer median (district+category)",
                    reference_value=_fmt_l(float(m.peer_median_cost)),
                    calculation=f"({float(p.sanctioned_cost):.0f} − {float(m.peer_median_cost):.0f}) "
                                f"/ {float(m.peer_median_cost):.0f} × 100 = {dev:+.1f}%",
                    provenance={"rule": "COST_ANOMALY", "threshold_pct": C.COST_DEVIATION_TRIGGER_PCT},
                ))
                counters[SignalType.COST_ANOMALY] = counters.get(SignalType.COST_ANOMALY, 0) + 1

        # ---- Rule 2: financial/physical progress mismatch -----------------
        if p.financial_progress is not None and p.physical_progress is not None:
            gap = float(p.financial_progress) - float(p.physical_progress)
            if gap >= C.FIN_PHYS_GAP_TRIGGER_PP:
                severity = (
                    Severity.CRITICAL if gap >= C.FIN_PHYS_GAP_HIGH_PP else Severity.HIGH
                )
                s = make_signal(
                    project_id=p.id,
                    signal_type=SignalType.FIN_PHYS_GAP,
                    severity=severity,
                    title=f"Financial vs physical gap {gap:+.0f} pp",
                    explanation=(
                        f"Financial progress is {float(p.financial_progress):.0f}% but physical "
                        f"progress is {float(p.physical_progress):.0f}%. Difference: "
                        f"{gap:.0f} percentage points. This is an investigation indicator, "
                        f"not proof of wrongdoing."
                    ),
                    observed={"financial_pct": float(p.financial_progress),
                              "physical_pct": float(p.physical_progress)},
                    reference={"expected": "financial ≈ physical progress"},
                    difference={"gap_pp": gap},
                    source_type=SourceType.RULE,
                )
                db.add(s)
                db.flush()
                db.add(add_evidence(
                    s,
                    field_name="progress (financial / physical)",
                    field_value=f"{float(p.financial_progress):.0f}% / {float(p.physical_progress):.0f}%",
                    reference_label="expected",
                    reference_value="financial ≈ physical",
                    calculation=f"{float(p.financial_progress):.0f} − {float(p.physical_progress):.0f} "
                                f"= {gap:+.0f} pp (trigger ≥ {C.FIN_PHYS_GAP_TRIGGER_PP} pp)",
                    provenance={"rule": "FIN_PHYS_GAP", "threshold_pp": C.FIN_PHYS_GAP_TRIGGER_PP},
                ))
                counters[SignalType.FIN_PHYS_GAP] = counters.get(SignalType.FIN_PHYS_GAP, 0) + 1

        # ---- Rule 3: delay ------------------------------------------------
        if m and m.delay_days is not None and m.delay_days >= C.DELAY_TRIGGER_DAYS:
            severity = (
                Severity.CRITICAL if m.delay_days >= C.DELAY_HIGH_DAYS else Severity.HIGH
            )
            expected = int(m.expected_duration_days or 0)
            elapsed = int(m.elapsed_days or 0)
            s = make_signal(
                project_id=p.id,
                signal_type=SignalType.DELAY,
                severity=severity,
                title=f"Delay of {m.delay_days} days",
                explanation=(
                    f"Elapsed duration is {elapsed} days against an expected {expected} days "
                    f"since sanction. Delay: {m.delay_days} days. Compare with site status "
                    f"before drawing conclusions."
                ),
                observed={"elapsed_days": elapsed},
                reference={"expected_days": expected},
                difference={"delay_days": int(m.delay_days)},
                source_type=SourceType.RULE,
            )
            db.add(s)
            db.flush()
            db.add(add_evidence(
                s,
                field_name="duration (elapsed / expected)",
                field_value=f"{elapsed}d / {expected}d",
                reference_label="expected duration",
                reference_value=f"{expected}d",
                calculation=f"{elapsed} − {expected} = +{m.delay_days}d "
                            f"(trigger ≥ {C.DELAY_TRIGGER_DAYS}d)",
                provenance={"rule": "DELAY", "threshold_days": C.DELAY_TRIGGER_DAYS},
            ))
            counters[SignalType.DELAY] = counters.get(SignalType.DELAY, 0) + 1

    db.flush()
    return counters


def _peer_count(m: ProjectMetrics) -> str:
    return "see peer context" if m.peer_percentile is not None else "n/a"
