"""CAG validation API — read-only capability report.

    GET /api/v1/validation/cag           (full machine-readable report)
    GET /api/v1/validation/cag/summary   (compact result table for the UI)

Every response carries the provenance disclaimer: this is a representative
validation against a synthetic reproduction of documented CAG irregularity
patterns — never a claim of detecting real CAG cases.

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
