"""CAG + synthetic validation APIs — read-only capability reports.

    GET /api/v1/validation/cag           (full machine-readable report)
    GET /api/v1/validation/cag/summary   (compact result table for the UI)
    GET /api/v1/validation/synthetic     (controlled injection benchmark:
                                          precision/recall/F1/FPR/confusion
                                          on synthetic ground truth)

Every response carries the provenance disclaimer: these are representative
validations against synthetic reproductions of documented patterns and
injected anomalies — never claims of detecting real cases or real-world
fraud-detection accuracy.

The run is cached per-process (compute is a few seconds; the report is
deterministic apart from the generated_at timestamp), and the cache is keyed
by dataset count so a fresh import invalidates it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Dataset
from app.schemas.schemas import Envelope, Meta
from app.services.validation.cag_validation import run_cag_validation

logger = logging.getLogger("drishti.cag_validation_api")

router = APIRouter()

_cache: dict = {"dataset_count": None, "report": None}
_synthetic_cache: dict = {"report": None, "seed": None}


def _dataset_count(db: Session) -> int:
    return db.query(Dataset).count()


def get_cag_report(db: Session):
    """Cached machine-readable report; recomputed when datasets change."""
    count = _dataset_count(db)
    if _cache["report"] is None or _cache["dataset_count"] != count:
        report = run_cag_validation(db)
        report["generated_at"] = datetime.now(timezone.utc).isoformat()
        _cache["report"] = report
        _cache["dataset_count"] = count
    return _cache["report"]


@router.get("/validation/cag")
def get_validation_report(db: Session = Depends(get_db)):
    """Full CAG-grounded validation report (machine-readable)."""
    try:
        report = get_cag_report(db)
    except Exception as exc:  # noqa: BLE001 — surfaced through the error envelope
        logger.exception("CAG validation run failed")
        from app.core.errors import DrishtiError

        raise DrishtiError(
            message="CAG validation run failed — see server logs.",
            status_code=500,
            code="CAG_VALIDATION_FAILED",
        ) from exc
    return Envelope(
        data=report,
        meta=Meta(
            dataset_version=report["report_version"],
            generated_at=report["generated_at"],
            is_synthetic=True,
        ),
    )


@router.get("/validation/synthetic")
def get_synthetic_validation(seed: int = 26102):
    """Synthetic Model Validation — controlled injection benchmark.

    Deterministic: the same seed always reproduces the same dataset,
    injections and metrics (verified by tests). Runs the four scenarios
    through the unmodified pipeline in-process (a few seconds).
    """
    if (
        _synthetic_cache["report"] is None
        or _synthetic_cache["seed"] != seed
    ):
        try:
            from app.services.validation.synthetic.benchmark import (
                run_full_benchmark,
            )

            _synthetic_cache["report"] = run_full_benchmark(seed=seed)
            _synthetic_cache["seed"] = seed
        except Exception as exc:  # noqa: BLE001 — surfaced via error envelope
            logger.exception("synthetic validation benchmark failed")
            from app.core.errors import DrishtiError

            raise DrishtiError(
                message="Synthetic validation benchmark failed — see server logs.",
                status_code=500,
                code="SYNTHETIC_VALIDATION_FAILED",
            ) from exc
    report = _synthetic_cache["report"]
    return Envelope(
        data=report,
        meta=Meta(
            dataset_version=report["report_version"],
            generated_at=report["generated_at"],
            is_synthetic=True,
        ),
    )


@router.get("/validation/cag/summary")
def get_validation_summary(db: Session = Depends(get_db)):
    """Compact per-pattern result table for the Evidence & Validation view."""
    report = get_cag_report(db)
    data = {
        "report_version": report["report_version"],
        "generated_at": report["generated_at"],
        "disclaimer": report["disclaimer"],
        "provenance": report["data_limitations"]["provenance_statement"],
        "summary": report["summary"],
        "patterns": [
            {
                "pattern_id": r["pattern_id"],
                "title": r["title"],
                "result": r["result"],
                "flagged": r["flagged"],
                "validation_method": r["validation_method"],
                "work_ids": r["work_ids"],
                "reason": r["reason"],
            }
            for r in report["results"]
        ],
        "queue_entry": report["queue_entry_check"]["by_work_id"],
    }
    return Envelope(
        data=data,
        meta=Meta(
            dataset_version=report["report_version"],
            generated_at=report["generated_at"],
            is_synthetic=True,
        ),
    )
