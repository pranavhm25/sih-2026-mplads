"""Benchmark orchestrator (Steps 6–9): scenarios, evaluation, serialization.

The model under test is the REAL pipeline: generated rows go through the
official ingestion path and the unmodified detection run (quality →
metrics → peers → rules → compliance → agency concentration → NLP → IF →
fusion). Thresholds are exactly the production defaults; nothing is tuned.

Ground-truth discipline:
- only injected rows count as anomalies in the confusion matrix
- baseline rows flagged by the pipeline are FALSE POSITIVES and are
  reported (never silently discarded)
- per-anomaly-type metrics use each type's injected rows plus all clean
  rows as the negatives pool (standard multi-class-in-binary reporting)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    Dataset,
    DetectionRun,
    InvestigationCase,
    Project,
    ProjectSignal,
)
from app.services.detection.fusion import compute_priorities
from app.services.detection.runner import run_detection
from app.services.ingestion.orchestrator import import_official_file
from app.services.validation.synthetic.injection import (
    INJECTED_PREFIX,
    REFERENCE_DATE,
    SyntheticDatasetBuilder,
)
from app.services.validation.synthetic.metrics import (
    ConfusionMatrix,
    WorkEvaluation,
    compute_metrics,
    evaluate,
)

logger = logging.getLogger("drishti.synthetic_validation")

RESULTS_VERSION = "synthetic-validation-1"
DEFAULT_SEED = 26102
INJECTED_VERSION = "synthetic-validation-injected"

SCENARIOS = {
    "A_clean_baseline": {"n_baseline": 60, "injections": {}},
    "B_small_injection": {
        "n_baseline": 60,
        "injections": {"cost": 4, "delay": 4, "pattern": 3},
    },
    "C_moderate_injection": {
        "n_baseline": 60,
        "injections": {
            "cost": 6, "duplicate": 2, "delay": 6, "spending_pattern": 4,
        },
    },
    "D_mixed_types": {
        "n_baseline": 60,
        "injections": {
            "cost": 6, "duplicate": 3, "delay": 6, "spending_pattern": 6,
            "pattern": 5,
        },
    },
}


def _cleanup_dataset(db: Session, dataset_id: str) -> None:
    """Remove a benchmark dataset and all descendants (test-DB hygiene)."""
    pids = [pid for (pid,) in db.query(Project.id)
            .filter(Project.dataset_id == dataset_id).all()]
    if pids:
        db.query(InvestigationCase).filter(
            InvestigationCase.project_id.in_(pids)
        ).delete(synchronize_session=False)
        db.query(ProjectSignal).filter(
            ProjectSignal.project_id.in_(pids)
        ).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_(pids)).delete(
            synchronize_session=False
        )
    db.query(DetectionRun).filter(
        DetectionRun.dataset_id == dataset_id
    ).delete(synchronize_session=False)
    d = db.get(Dataset, dataset_id)
    if d is not None:
        db.delete(d)
    db.commit()


def run_scenario(
    scenario_name: str,
    scenario_cfg: dict,
    seed: int = DEFAULT_SEED,
    db: Session | None = None,
    cleanup: bool = True,
) -> dict:
    """Generate → inject → ingest → detect → evaluate one scenario."""
    own_db = db is None
    if own_db:
        db = SessionLocal()

    builder = SyntheticDatasetBuilder(seed=seed)
    builder.generate_baseline_dataset(n=scenario_cfg["n_baseline"])
    for inj_type, n in scenario_cfg["injections"].items():
        getattr(builder, f"inject_{inj_type}_anomalies")(n)

    raw = builder.build_csv()
    summary = import_official_file(
        db,
        raw,
        file_name=f"synthetic_validation_{scenario_name}.csv",
        name=f"Synthetic validation — {scenario_name} (controlled benchmark)",
        is_synthetic=True,
        run_pipeline=False,
    )
    dataset = db.get(Dataset, summary["dataset_id"])
    dataset.version = INJECTED_VERSION
    dataset.source_label = (
        "synthetic_validation_injection: controlled benchmark, "
        "not real MPLADS data"
    )
    db.commit()

    run = run_detection(db, dataset, today=REFERENCE_DATE)

    projects = db.query(Project).filter(Project.dataset_id == dataset.id).all()
    fusion = compute_priorities(db, projects)
    signals_by_pid: dict[str, list] = {}
    for p in projects:
        signals_by_pid[p.id] = [
            s for s in p.signals
            if s.triggered and s.signal_type != "DATA_QUALITY"
        ]

    gt = builder.ground_truth.entries
    work_evals: list[WorkEvaluation] = []
    for p in projects:
        g = gt.get(p.work_id)
        if g is None:
            continue  # row was rejected at ingestion; not part of the trial
        sigs = signals_by_pid.get(p.id, [])
        sig_types = [s.signal_type for s in sigs]
        expected = g["expected_detector"]
        work_evals.append(WorkEvaluation(
            work_id=p.work_id,
            injected=g["injected"],
            anomaly_type=g["anomaly_type"],
            expected_detector=expected,
            flagged=bool(sigs),
            signal_types=sig_types,
            priority=(fusion.get(p.id, {}) or {}).get("level"),
            priority_score=(fusion.get(p.id, {}) or {}).get("score"),
            hit_expected_detector=(
                (expected in sig_types) if expected else None
            ),
        ))

    total_injected = sum(1 for w in work_evals if w.injected)
    cm, metrics = evaluate(work_evals, total_injected)

    # ---- per anomaly type (negatives pool = all clean rows) ------------
    clean = [w for w in work_evals if not w.injected]
    clean_flagged = sum(1 for w in clean if w.flagged)
    clean_total = len(clean)
    per_type = {}
    for atype in sorted({w.anomaly_type for w in work_evals if w.injected}):
        t_rows = [w for w in work_evals
                  if w.injected and w.anomaly_type == atype]
        t_cm = ConfusionMatrix(
            tp=sum(1 for w in t_rows if w.flagged),
            fn=sum(1 for w in t_rows if not w.flagged),
            fp=clean_flagged,
            tn=clean_total - clean_flagged,
        )
        t_metrics = compute_metrics(t_cm, len(t_rows))
        det_hits = sum(1 for w in t_rows if w.hit_expected_detector)
        per_type[atype] = {
            "injected": len(t_rows),
            "detected": t_cm.tp,
            "missed": t_cm.fn,
            "expected_detector": t_rows[0].expected_detector,
            "expected_detector_hits": det_hits,
            "cm": t_cm.as_dict(),
            "metrics": t_metrics.as_dict(),
            "work_ids": [w.work_id for w in t_rows],
        }

    result = {
        "scenario": scenario_name,
        "seed": seed,
        "config": {
            "n_baseline": scenario_cfg["n_baseline"],
            "injections": scenario_cfg["injections"],
            "reference_date": REFERENCE_DATE.isoformat(),
        },
        "dataset": {
            "id": dataset.id,
            "rows_imported": dataset.row_count,
            "quality_status": dataset.quality_status,
            "detection_run_id": run.id,
            "detection_run_status": run.status,
            "ruleset_version": run.ruleset_version,
            "model_version": run.model_version,
        },
        "totals": {
            "records_evaluated": len(work_evals),
            "injected": total_injected,
            "normal": clean_total,
            **cm.as_dict(),
        },
        "metrics": metrics.as_dict(),
        "per_anomaly_type": per_type,
        "false_positives": [
            w.as_dict() for w in clean if w.flagged
        ],
        "false_negatives": [
            w.as_dict() for w in work_evals if w.injected and not w.flagged
        ],
        "ground_truth": builder.ground_truth.as_list(),
        "injection_log": builder.injection_log,
    }

    if cleanup:
        _cleanup_dataset(db, dataset.id)
    if own_db:
        db.close()
    return result


def build_report(scenarios: dict[str, dict], seed: int) -> dict:
    """Assemble the machine-readable report (Step 9)."""
    overall_cm = ConfusionMatrix()
    for s in scenarios.values():
        t = s["totals"]
        overall_cm.tp += t["tp"]
        overall_cm.fp += t["fp"]
        overall_cm.tn += t["tn"]
        overall_cm.fn += t["fn"]
    overall_total_injected = sum(
        s["totals"]["injected"] for s in scenarios.values()
    )
    overall_metrics = compute_metrics(overall_cm, overall_total_injected)

    detector_versions = sorted({
        (s["dataset"]["ruleset_version"], s["dataset"]["model_version"])
        for s in scenarios.values()
    })

    return {
        "report_version": RESULTS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": "Synthetic Model Validation — controlled injection benchmark",
        "language_discipline": (
            "Controlled synthetic benchmark on the existing detection "
            "pipeline. Results do NOT represent production-world fraud "
            "detection accuracy. All metrics are computed against "
            "synthetic ground truth for injected anomalies."
        ),
        "experiment_configuration": {
            "seed": seed,
            "reference_date": REFERENCE_DATE.isoformat(),
            "scenarios": {
                name: cfg for name, cfg in SCENARIOS.items()
            },
            "pipeline": (
                "unmodified: quality → metrics → peers → rules → "
                "compliance → agency concentration → NLP duplicates → "
                "Isolation Forest → fusion"
            ),
            "threshold_tuning": "none — production defaults used",
            "detector_versions": [
                f"ruleset={r}, model={m}" for r, m in detector_versions
            ],
        },
        "scenarios": {
            name: {
                "totals": s["totals"],
                "metrics": s["metrics"],
                "per_anomaly_type": s["per_anomaly_type"],
                "false_positive_count": len(s["false_positives"]),
                "false_negative_count": len(s["false_negatives"]),
                "dataset_rows_imported": s["dataset"]["rows_imported"],
                "detection_run_status": s["dataset"]["detection_run_status"],
            }
            for name, s in scenarios.items()
        },
        "overall": {
            "cm": overall_cm.as_dict(),
            "metrics": overall_metrics.as_dict(),
            "total_injected": overall_total_injected,
        },
        "detailed_results": {
            name: {
                "false_positives": s["false_positives"],
                "false_negatives": s["false_negatives"],
            }
            for name, s in scenarios.items()
        },
    }


def run_full_benchmark(seed: int = DEFAULT_SEED, db: Session | None = None) -> dict:
    """Run all scenarios and return the machine-readable report."""
    scenarios = {}
    for name, cfg in SCENARIOS.items():
        logger.info("synthetic validation scenario %s starting", name)
        scenarios[name] = run_scenario(name, cfg, seed=seed, db=db)
        logger.info("synthetic validation scenario %s done", name)
    return build_report(scenarios, seed)
