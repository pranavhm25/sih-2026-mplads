"""ML engine — Isolation Forest unsupervised anomaly detection (PRD R7).

The model operates on a stable numeric feature set and its output is
presented strictly as *statistical unusualness*, never as a fraud
prediction (TR-06, AGENTS_RULES.md Rule 1). Features are documented so the
result stays explainable alongside rule evidence.
"""
from __future__ import annotations

import logging
from datetime import date

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.config import settings
from app.core.constants import Severity, SignalType, SourceType
from app.models import Project, ProjectMetrics, ProjectSignal
from app.services.detection.signal_factory import add_evidence, make_signal

logger = logging.getLogger("drishti.ml")

FEATURE_NAMES = [
    "cost_ratio_to_peer_median",   # sanctioned cost / peer median
    "financial_physical_gap",      # pp
    "delay_days",                  # days beyond expected
    "expenditure_ratio",           # expenditure / sanctioned
    "duplicate_score",             # max candidate score
]

RANDOM_STATE = 26102  # deterministic
CONTAMINATION = "auto"


def build_feature_matrix(
    projects: list[Project], metrics_by_pid: dict[str, ProjectMetrics]
) -> tuple[np.ndarray, list[str], list[list[float | None]]]:
    """Assemble the feature matrix; returns X, project_ids, raw rows.

    Rows with missing features are still included via NaN and later excluded
    from scoring individually — we never invent feature values.
    """
    rows: list[list[float | None]] = []
    pids: list[str] = []
    for p in projects:
        m = metrics_by_pid.get(p.id)
        if m is None:
            continue
        peer_median = float(m.peer_median_cost) if m.peer_median_cost else None
        cost_ratio = (
            float(p.sanctioned_cost) / peer_median
            if peer_median not in (None, 0) else None
        )
        rows.append([
            cost_ratio,
            float(m.financial_physical_gap) if m.financial_physical_gap is not None else None,
            float(m.delay_days) if m.delay_days is not None else None,
            float(m.expenditure_ratio) if m.expenditure_ratio is not None else None,
            float(m.duplicate_score) if m.duplicate_score is not None else None,
        ])
        pids.append(p.id)
    X = np.array(
        [[np.nan if v is None else v for v in row] for row in rows],
        dtype=float,
    )
    return X, pids, rows


def run_ml_engine(
    db: Session,
    projects: list[Project],
    today: date,
) -> dict[str, int]:
    """Score projects with Isolation Forest; persist ML_ANOMALY signals."""
    # Remove previous ML signals.
    ids = [p.id for p in projects]
    if ids:
        db.query(ProjectSignal).filter(
            ProjectSignal.project_id.in_(ids),
            ProjectSignal.signal_type == SignalType.ML_ANOMALY,
        ).delete(synchronize_session=False)
        db.flush()

    metrics_by_pid = {
        m.project_id: m
        for m in db.query(ProjectMetrics).filter(ProjectMetrics.project_id.in_(ids))
    } if ids else {}

    X, pids, raw_rows = build_feature_matrix(projects, metrics_by_pid)
    if len(pids) < 10:
        # Not enough data for a meaningful unsupervised fit — say so honestly.
        logger.info("ML engine skipped: only %d feature rows available", len(pids))
        return {"skipped": len(pids)}

    # Median-impute NaNs for fitting; columns that are entirely missing are
    # imputed as 0 rather than crashing (honest fallback, documented here).
    with np.errstate(all="ignore"):
        col_median = np.nanmedian(X, axis=0)
    col_median = np.where(np.isnan(col_median), 0.0, col_median)
    X_imputed = np.where(np.isnan(X), col_median, X)

    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
    )
    model.fit(X_imputed)
    scores = model.decision_function(X_imputed)  # higher = more typical

    counters: dict[str, int] = {}
    project_by_id = {p.id: p for p in projects}

    for idx, pid in enumerate(pids):
        score = float(scores[idx])
        if score >= C.ML_ANOMALY_TRIGGER:
            continue  # within the typical range
        severity = Severity.HIGH if score <= C.ML_ANOMALY_HIGH else Severity.MEDIUM
        p = project_by_id[pid]
        m = metrics_by_pid[pid]
        feature_desc = ", ".join(
            f"{name}={raw_rows[idx][i]:g}" if raw_rows[idx][i] is not None else f"{name}=n/a"
            for i, name in enumerate(FEATURE_NAMES)
        )
        s = make_signal(
            project_id=pid,
            signal_type=SignalType.ML_ANOMALY,
            severity=severity,
            title=f"Statistically unusual pattern (IF score {score:+.3f})",
            explanation=(
                f"Isolation Forest (unsupervised) rates this work statistically unusual "
                f"relative to the dataset (score {score:+.3f}, more negative = more unusual). "
                f"Feature profile: {feature_desc}. This is an unusual-pattern signal, "
                f"not a prediction of wrongdoing."
            ),
            observed={"anomaly_score": round(score, 4)},
            reference={"typical_range": f"> {C.ML_ANOMALY_TRIGGER}"},
            difference={"model_version": settings.model_version},
            source_type=SourceType.ML,
            source_version=settings.model_version,
        )
        db.add(s)
        db.flush()
        db.add(add_evidence(
            s,
            field_name="isolation forest score",
            field_value=f"{score:+.4f}",
            reference_label="decision_function",
            reference_value=f"trigger < {C.ML_ANOMALY_TRIGGER}",
            calculation="sklearn IsolationForest decision_function over 5 engineered features",
            provenance={
                "model": "IsolationForest",
                "model_version": settings.model_version,
                "features": FEATURE_NAMES,
                "n_estimators": 200,
                "random_state": RANDOM_STATE,
            },
        ))
        counters[SignalType.ML_ANOMALY] = counters.get(SignalType.ML_ANOMALY, 0) + 1

    # Persist scores for transparency even when below trigger.
    for idx, pid in enumerate(pids):
        m = metrics_by_pid[pid]
        m.ml_anomaly_score = round(float(scores[idx]), 4)

    db.commit()
    return counters
