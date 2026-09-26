"""CAG-grounded validation layer (docs/CAG_VALIDATION.md).

Runs the EXISTING detection pipeline against a controlled synthetic dataset
that reproduces the structural signatures of irregularity patterns documented
in real CAG audits of MPLADS — and reports honestly whether each pattern was
flagged.

Layer discipline (enforced by tests):
  1. SOURCE     — verified CAG findings (app/data/cag_catalog.py)
  2. MAPPING    — Drishti detector mapped to each pattern
  3. VALIDATION — synthetic reproduction; NEVER presented as a CAG case

Thresholds are never modified to force positive results; detectors and
thresholds are exactly those used in production runs.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.constants import DatasetType
from app.data.cag_catalog import CAG_PATTERNS, CAG_SOURCES
from app.models import (
    Dataset,
    Project,
    ProjectSignal,
    ValidationIssue,
)
from app.services.detection.runner import run_detection
from app.services.ingestion.orchestrator import import_official_file

logger = logging.getLogger("drishti.cag_validation")

FIXTURE_NAME = "cag_patterns"
FIXTURE_DISPLAY = (
    "CAG-grounded pattern validation fixture (synthetic — not CAG data)"
)

# Provenance constants stamped on the dataset row and into the report.
SOURCE_TYPE_VALUE = "synthetic_cag_pattern"
PROVENANCE_STATEMENT = (
    "This fixture reproduces the structural characteristics of documented "
    "CAG irregularity patterns for detector validation. It is not the "
    "original CAG dataset, contains no real MPLADS records, and demonstrates "
    "detection capability only — it does not claim that Drishti detected any "
    "real CAG case."
)

# Work IDs carrying each pattern's structural signature in the fixture.
PATTERN_WORK_IDS = {p["pattern_id"]: p["fixture_work_ids"] for p in CAG_PATTERNS}


def build_fixture_bytes() -> bytes:
    """Raw fixture CSV bytes — single on-disk source of truth."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "cag_patterns.csv"
    return path.read_bytes()


def _find_existing_validation_dataset(db: Session, file_hash: str) -> Dataset | None:
    """Reuse the validation dataset when the identical fixture is re-run.

    The import pipeline's duplicate-upload guard would otherwise reject the
    second validation run in one session. Reuse is safe: detection is
    idempotent (it clears and recomputes its own outputs).
    """
    from app.services.ingestion.orchestrator import sha256_of

    if file_hash is None:
        return None
    ds = (
        db.query(Dataset)
        .filter(Dataset.file_hash == file_hash, Dataset.is_synthetic.is_(True))
        .first()
    )
    if ds is not None and ds.version == "cag-validation-1":
        return ds
    return None


def _signal_types_for(project: Project) -> set[str]:
    return {s.signal_type for s in project.signals if s.triggered}


def _evaluate_pattern(
    db: Session,
    projects_by_work_id: dict[str, Project],
    priority_by_pid: dict[str, dict],
    pattern: dict,
) -> dict:
    """Compare the pattern's expected trigger with what the detectors emitted."""
    work_ids = pattern["fixture_work_ids"]
    if pattern["validation_method"] == "NOT_VALIDATABLE" or not work_ids:
        return {
            "pattern_id": pattern["pattern_id"],
            "title": pattern["title"],
            "validation_method": pattern["validation_method"],
            "result": "NOT_VALIDATABLE",
            "flagged": None,
            "expected_trigger": None,
            "observed_signals": [],
            "work_ids": [],
            "reason": pattern["limitations"],
        }

    observed: list[dict] = []
    flagged = False
    expected_signal = pattern.get("drishti_signal_type")

    for wid in work_ids:
        p = projects_by_work_id.get(wid)
        if p is None:
            observed.append({"work_id": wid, "error": "work missing after import"})
            continue
        sigs = [
            s for s in p.signals
            if s.triggered and s.signal_type != C.SignalType.DATA_QUALITY
        ]
        fusion = priority_by_pid.get(p.id, {})
        hit = bool(expected_signal) and expected_signal in {s.signal_type for s in sigs}
        flagged = flagged or hit
        observed.append({
            "work_id": wid,
            "signals": [
                {
                    "signal_type": s.signal_type,
                    "severity": s.severity,
                    "title": s.title,
                    "explanation": s.explanation,
                }
                for s in sigs
            ],
            "evidence_rows": sum(len(s.evidence) for s in sigs),
            "fused_priority": fusion.get("level"),
            "fused_score": fusion.get("score"),
            "signal_count": fusion.get("signal_count"),
            "expected_signal_hit": hit,
        })

    # A validation counts as PARTIAL when the pattern's primary signal did
    # not fire but other independent signals still converged on the work.
    if flagged:
        result = "FLAGGED"
    else:
        converged = any(
            o.get("signals") for o in observed if isinstance(o, dict)
        )
        result = "PARTIAL" if converged else "MISSED"
    return {
        "pattern_id": pattern["pattern_id"],
        "title": pattern["title"],
        "validation_method": pattern["validation_method"],
        "result": result,
        "flagged": flagged,
        "expected_trigger": pattern.get("expected_trigger"),
        "observed_signals": observed,
        "work_ids": work_ids,
        "reason": None if flagged else pattern["limitations"],
    }


def run_cag_validation(db: Session, today: date | None = None) -> dict:
    """Full validation run: ingest fixture → detect → evaluate → report.

    Returns the machine-readable report (docs/CAG_VALIDATION.md §7 shape).
    Raises ImportError if the fixture fails ingestion.
    """
    today = today or date.today()
    raw = build_fixture_bytes()

    # Import through the OFFICIAL pipeline (schema detection, validation,
    # provenance) — always forced synthetic. Re-runs reuse the dataset
    # already ingested from identical bytes (idempotent validation).
    from app.services.ingestion.orchestrator import sha256_of

    file_hash = sha256_of(raw)
    existing = _find_existing_validation_dataset(db, file_hash)
    if existing is not None:
        dataset = existing
    else:
        summary = import_official_file(
            db,
            raw,
            file_name="cag_patterns.csv",
            name=FIXTURE_DISPLAY,
            is_synthetic=True,
            run_pipeline=False,
        )
        dataset = db.get(Dataset, summary["dataset_id"])
        if dataset is None:
            raise RuntimeError("CAG fixture import did not persist a dataset")

    # Stamp the provenance layer onto the dataset record.
    dataset.source_label = (
        f"{SOURCE_TYPE_VALUE}: {FIXTURE_DISPLAY}"
    )
    dataset.version = "cag-validation-1"
    db.commit()

    # Run the unmodified detection pipeline (deterministic reference date
    # so runs are reproducible).
    run = run_detection(db, dataset, today=today)

    projects = db.query(Project).filter(Project.dataset_id == dataset.id).all()
    projects_by_work_id = {p.work_id: p for p in projects}

    from app.services.detection.fusion import compute_priorities
    priority_by_pid = compute_priorities(db, projects)

    pattern_results = [
        _evaluate_pattern(db, projects_by_work_id, priority_by_pid, p)
        for p in CAG_PATTERNS
    ]

    counts = {"FLAGGED": 0, "PARTIAL": 0, "MISSED": 0, "NOT_VALIDATABLE": 0}
    for r in pattern_results:
        counts[r["result"]] += 1

    # Signals are re-read after fusion so counts reflect persisted state.
    n_signals = (
        db.query(ProjectSignal)
        .join(Project, ProjectSignal.project_id == Project.id)
        .filter(Project.dataset_id == dataset.id)
        .count()
    )

    return {
        "report_version": "cag-validation-1",
        "generated_at": None,  # filled by the API layer with a timestamp
        "purpose": (
            "Demonstrate which irregularity PATTERNS documented in CAG audits "
            "of MPLADS fall within Drishti's detection capability, using a "
            "controlled synthetic reproduction — not to claim detection of "
            "real CAG cases."
        ),
        "data_limitations": {
            "provenance_statement": PROVENANCE_STATEMENT,
            "source_type": SOURCE_TYPE_VALUE,
            "is_synthetic": True,
            "fixture_file": "app/data/fixtures/cag_patterns.csv",
            "underlying_records_available": False,
            "note": (
                "No accuracy metrics against real CAG data are claimed: the "
                "underlying work-level records are not publicly available."
            ),
        },
        "cag_sources": CAG_SOURCES,
        "patterns": [
            {
                "pattern_id": p["pattern_id"],
                "title": p["title"],
                "source_id": p["source_id"],
                "finding_reference": p["finding_reference"],
                "irregularity_type": p["irregularity_type"],
                "documented_pattern": p["documented_pattern"],
                "cag_quote": p["cag_quote"],
                "required_data_fields": p["required_data_fields"],
                "drishti_detector": p["drishti_detector"],
                "drishti_signal_type": p["drishti_signal_type"],
                "validation_method": p["validation_method"],
                "expected_trigger": p["expected_trigger"],
                "limitations": p["limitations"],
            }
            for p in CAG_PATTERNS
        ],
        "results": pattern_results,
        "summary": {
            "patterns_total": len(CAG_PATTERNS),
            **counts,
            "dataset_id": dataset.id,
            "dataset_quality_status": dataset.quality_status,
            "detection_run_id": run.id,
            "detection_run_status": run.status,
            "detection_ruleset_version": run.ruleset_version,
            "detection_model_version": run.model_version,
            "signals_emitted": n_signals,
            "rows_imported": dataset.row_count,
            "validation_issues_recorded": (
                db.query(ValidationIssue)
                .filter(ValidationIssue.dataset_id == dataset.id)
                .count()
            ),
        },
        "queue_entry_check": {
            "description": (
                "Whether flagged works would enter the investigation queue "
                "(priority MEDIUM or above in the fused ranking)."
            ),
            "by_work_id": {
                wid: {
                    "priority": priority_by_pid.get(p.id, {}).get("level"),
                    "score": priority_by_pid.get(p.id, {}).get("score"),
                    "enters_queue": priority_by_pid.get(p.id, {}).get("level")
                    in ("MEDIUM", "HIGH", "CRITICAL"),
                }
                for wid, p in projects_by_work_id.items()
            },
        },
        "disclaimer": (
            "Representative validation — not original CAG case data. "
            "Drishti capability demonstration only; signals are investigation "
            "indicators, not findings."
        ),
    }


def validate_fixture_provenance(db: Session, dataset_id: str) -> dict:
    """Provenance checks used by tests: labels, source_type, no real data."""
    ds = db.get(Dataset, dataset_id)
    return {
        "exists": ds is not None,
        "is_synthetic": bool(ds.is_synthetic) if ds else False,
        "source_type": ds.source_type if ds else None,
        "source_type_matches_declaration": (
            ds.source_type == C.DatasetSourceType.SYNTHETIC_FIXTURE if ds else False
        ),
        "source_label_carries_cag_marker": (
            bool(ds.source_label and SOURCE_TYPE_VALUE in ds.source_label)
            if ds else False
        ),
        "work_ids_all_cagv_prefixed": all(
            wid.startswith("CAGV-")
            for (wid,) in db.query(Project.work_id)
            .filter(Project.dataset_id == dataset_id)
            .all()
        ),
    }
