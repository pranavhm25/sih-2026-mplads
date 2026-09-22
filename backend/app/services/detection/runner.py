"""Detection run orchestrator (TRD §5 pipeline).

Chains: quality → metrics → peer benchmarking → rules → NLP duplicates →
ML → fusion. Records a DetectionRun with explicit status and summary so
failures are visible and retryable, tied to dataset/ruleset/model versions.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RunStatus
from app.models import DetectionRun, Dataset, Project
from app.ml import isolation_forest
from app.nlp import duplicate_candidates
from app.rules import engine as rules
from app.services.detection import (
    benchmarking,
    fusion,
    metrics as metrics_svc,
)
from app.services.quality.quality import run_quality_checks

logger = logging.getLogger("drishti.detection")


def run_detection(db: Session, dataset: Dataset, today: date | None = None) -> DetectionRun:
    """Execute the full detection pipeline for a dataset.

    `today` pins the elapsed-time calculations so demo runs stay
    deterministic; defaults to the real current date for live imports.
    """
    today = today or date.today()
    run = DetectionRun(
        dataset_id=dataset.id,
        model_version=settings.model_version,
        ruleset_version=settings.ruleset_version,
        status=RunStatus.RUNNING,
    )
    db.add(run)
    db.commit()

    try:
        summary: dict = {}

        # 1. Data quality (also emits DATA_QUALITY signals)
        summary["quality"] = run_quality_checks(db, dataset)

        # 2. Derived metrics
        n_metrics = metrics_svc.compute_metrics(db, dataset.id, today=today)
        summary["metrics_computed"] = n_metrics

        # 3. Peer benchmarking (fills cost deviation in metrics)
        benchmarks = benchmarking.build_peer_groups(db, dataset.id)
        summary["peer_groups"] = len(benchmarks)

        # 4. Rule engine (cost anomaly, F/P gap, delay)
        projects = db.query(Project).filter(Project.dataset_id == dataset.id).all()
        summary["rules"] = rules.run_rule_engine(db, projects, today)

        # 5. NLP duplicate candidates
        summary["duplicates"] = duplicate_candidates.detect_duplicate_candidates(db, projects)

        # 6. Isolation Forest
        summary["ml"] = isolation_forest.run_ml_engine(db, projects, today)

        # 7. Evidence fusion → investigation priority per project
        priorities = fusion.compute_priorities(db, projects)
        summary["priorities"] = {
            pid: {"level": f["level"], "score": f["score"], "signal_count": f["signal_count"]}
            for pid, f in priorities.items()
        }
        levels: dict[str, int] = {}
        for f in priorities.values():
            levels[f["level"]] = levels.get(f["level"], 0) + 1
        summary["priority_distribution"] = levels

        run.status = RunStatus.COMPLETED
        run.summary = summary
        from datetime import datetime, timezone
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Detection run %s completed: %s", run.id, summary.get("priority_distribution"))

    except Exception as exc:  # noqa: BLE001 — record and surface the failure
        db.rollback()
        run.status = RunStatus.FAILED
        run.error_message = str(exc)[:2000]
        from datetime import datetime, timezone
        run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()
        logger.exception("Detection run failed")
        raise

    return run
