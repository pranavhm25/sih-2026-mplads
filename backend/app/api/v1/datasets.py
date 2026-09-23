"""Datasets API — official imports, provenance, quality, typed records.

Endpoints (Prompt-3 §11, §30, §31, §32):

    POST /api/v1/datasets/import                  (multipart file)
    GET  /api/v1/datasets                         (paginated list)
    GET  /api/v1/datasets/{id}/quality            (quality report)
    GET  /api/v1/datasets/{id}/records            (type-safe records)
    GET  /api/v1/datasets/fixtures                (synthetic fixtures)
    POST /api/v1/datasets/fixtures/{name}/ingest  (ingest a fixture)

Records stay type-safe: an MP allocation row is never reshaped into a
work/project row (§32). Detection endpoints live at /api/v1/detection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import (
    Dataset,
    MPAllocationRecord,
    Project,
    ProjectSignal,
    SchemeAggregate,
    ValidationIssue,
)
from app.schemas.schemas import Envelope, Meta
from app.services.bootstrap import latest_dataset
from app.services.detection.runner import run_detection
from app.services.ingestion.orchestrator import (
    ImportRejected,
    import_official_file,
)

router = APIRouter()

# Route order note: /datasets/fixtures is declared before /datasets/{dataset_id}
# routes by FastAPI registration order below.


def _meta(dataset: Dataset | None = None) -> Meta:
    return Meta(
        dataset_version=dataset.version if dataset else None,
        generated_at=datetime.now(timezone.utc).isoformat(),
        is_synthetic=dataset.is_synthetic if dataset else None,
    )


@router.get("/datasets")
def list_datasets(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Paginated dataset list with provenance fields (§30)."""
    total = db.query(Dataset).count()
    datasets = (
        db.query(Dataset)
        .order_by(Dataset.ingested_at.desc(), Dataset.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [_dataset_out(d) for d in datasets]
    return Envelope(
        data={"items": items, "total": total, "offset": offset, "limit": limit},
        meta=_meta(datasets[0] if datasets else None),
    )


@router.get("/datasets/fixtures")
def get_available_fixtures():
    """List bundled synthetic fixtures (§39). Always labelled synthetic."""
    from app.data.fixtures import FIXTURES

    fixtures = [
        {"name": name, "file_name": path.name, "dataset_type": dtype, "label": label}
        for name, (path, dtype, label) in sorted(FIXTURES.items())
    ]
    return Envelope(data={"fixtures": fixtures}, meta=_meta())


@router.post("/datasets/fixtures/{name}/ingest")
def ingest_named_fixture(name: str, db: Session = Depends(get_db)):
    """Ingest a bundled synthetic fixture (is_synthetic forced True, §40)."""
    from app.data.fixtures import FIXTURES

    if name not in FIXTURES:
        raise NotFoundError("Fixture", name)
    from app.data.fixtures import ingest_fixture

    summary = ingest_fixture(db, name)
    return Envelope(data=summary, meta=_meta(db.get(Dataset, summary["dataset_id"])))


@router.post("/datasets/import")
async def import_dataset(
    file: UploadFile = File(...),
    dataset_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Import an official CSV/XLSX dataset (§10–§12).

    Detection of the dataset type is deterministic from the source columns
    when `dataset_type` is not supplied. Duplicate uploads (same SHA-256)
    are rejected. Partial validity applies: ERROR rows are excluded but
    preserved in the validation-issue table.
    """
    raw = await file.read()
    if len(raw) > C.MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB).")
    file_name = file.filename or "upload.csv"
    try:
        summary = import_official_file(
            db,
            raw,
            file_name=file_name,
            dataset_type=dataset_type,
            is_synthetic=_looks_synthetic(file_name),
            pipeline_runner=run_detection,
        )
    except ImportRejected as exc:
        # Structured error envelope (§46) — no stack traces reach the client.
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message,
                               "details": exc.details}},
        )
    return Envelope(data=summary, meta=_meta(db.get(Dataset, summary["dataset_id"])))


@router.get("/datasets/{dataset_id}/quality")
def dataset_quality(
    dataset_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=1000),
):
    """Full quality report + validation summary (§31, §45)."""
    dataset = _dataset_or_404(db, dataset_id)
    issues_q = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.dataset_id == dataset.id)
        .order_by(
            ValidationIssue.severity.desc(), ValidationIssue.row_number.asc()
        )
        .limit(limit)
        .all()
    )
    total_issues = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.dataset_id == dataset.id)
        .count()
    )
    summary = dataset.quality_summary or {}

    # Work-level datasets additionally surface persisted DATA_QUALITY signals
    # from the detection layer (run after import).
    detection_issue_count = 0
    if dataset.dataset_type == C.DatasetType.WORK_LEVEL.value:
        detection_issue_count = (
            db.query(ProjectSignal)
            .join(Project, ProjectSignal.project_id == Project.id)
            .filter(
                Project.dataset_id == dataset.id,
                ProjectSignal.signal_type == C.SignalType.DATA_QUALITY,
                ProjectSignal.triggered.is_(True),
            )
            .count()
        )

    data = {
        "dataset_id": dataset.id,
        "dataset_type": dataset.dataset_type,
        "quality_status": dataset.quality_status,
        "total_rows": summary.get("total_rows", dataset.row_count),
        "valid_rows": summary.get("valid_rows", dataset.row_count),
        "warning_rows": summary.get("warning_rows", 0),
        "error_rows": summary.get("error_rows", 0),
        "reasons": summary.get("reasons", []),
        "missing_field_counts": summary.get("missing_field_counts", {}),
        "invalid_field_counts": summary.get("invalid_field_counts", {}),
        "duplicate_counts": summary.get("duplicate_counts", {}),
        "parse_notes": summary.get("parse_notes", []),
        "issue_count": total_issues,
        "detection_issue_count": detection_issue_count,
        "issues": [
            {
                "row_number": i.row_number,
                "field": i.field,
                "rule": i.rule,
                "severity": i.severity,
                "message": i.message,
                "observed_value": i.observed_value,
            }
            for i in issues_q
        ],
    }
    return Envelope(data=data, meta=_meta(dataset))


@router.get("/datasets/{dataset_id}/records")
def dataset_records(
    dataset_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Type-safe record browsing (§32, §34).

    The returned `fields` list describes the columns actually available for
    THIS dataset type — empty analytical columns are never shown.
    """
    dataset = _dataset_or_404(db, dataset_id)
    dtype = dataset.dataset_type

    if dtype == C.DatasetType.MP_ALLOCATION.value:
        q = db.query(MPAllocationRecord).filter(
            MPAllocationRecord.dataset_id == dataset.id
        )
        total = q.count()
        rows = q.order_by(MPAllocationRecord.source_row_number.asc()).offset(offset).limit(limit).all()
        fields = ["serial_number", "state", "mp_name", "constituency",
                  "elected_nominated", "allocated_amount", "amount_unit"]
        records = [
            {
                "source_row_number": r.source_row_number,
                "serial_number": r.serial_number,
                "state": r.state,
                "mp_name": r.mp_name,
                "constituency": r.constituency,
                "elected_nominated": r.elected_nominated,
                "allocated_amount": float(r.allocated_amount) if r.allocated_amount is not None else None,
                "amount_unit": r.amount_unit,
            }
            for r in rows
        ]
        # House-specific columns never provided by the source are omitted
        # rather than shown as all-empty (§34, §15).
        if rows and all(r["constituency"] is None for r in records):
            fields.remove("constituency")
        if rows and all(r["elected_nominated"] is None for r in records):
            fields.remove("elected_nominated")
    elif dtype == C.DatasetType.SCHEME_AGGREGATE.value:
        q = db.query(SchemeAggregate).filter(
            SchemeAggregate.dataset_id == dataset.id
        )
        total = q.count()
        rows = q.order_by(SchemeAggregate.source_row_number.asc()).offset(offset).limit(limit).all()
        fields = ["house", "allocated_limit", "amount_consented_for_calamity",
                  "works_recommended", "works_sanctioned", "works_completed",
                  "expenditure_completed_and_ongoing", "monetary_unit", "as_of_date"]
        records = [
            {
                "source_row_number": r.source_row_number,
                "house": r.house,
                "allocated_limit": float(r.allocated_limit) if r.allocated_limit is not None else None,
                "amount_consented_for_calamity": (
                    float(r.amount_consented_for_calamity)
                    if r.amount_consented_for_calamity is not None else None
                ),
                "works_recommended": r.works_recommended,
                "works_sanctioned": r.works_sanctioned,
                "works_completed": r.works_completed,
                "expenditure_completed_and_ongoing": (
                    float(r.expenditure_completed_and_ongoing)
                    if r.expenditure_completed_and_ongoing is not None else None
                ),
                "monetary_unit": r.monetary_unit,
                "as_of_date": r.as_of_date.isoformat() if r.as_of_date else None,
            }
            for r in rows
        ]
    elif dtype == C.DatasetType.WORK_LEVEL.value:
        q = db.query(Project).filter(Project.dataset_id == dataset.id)
        total = q.count()
        rows = q.order_by(Project.created_at.asc()).offset(offset).limit(limit).all()
        fields = ["work_id", "state", "district", "description",
                  "sanctioned_cost", "expenditure", "status"]
        records = [
            {
                "id": p.id,
                "work_id": p.work_id,
                "state": p.state,
                "district": p.district,
                "description": p.description,
                "sanctioned_cost": float(p.sanctioned_cost),
                "expenditure": float(p.expenditure) if p.expenditure is not None else None,
                "status": p.status,
            }
            for p in rows
        ]
    else:
        fields = []
        records = []
        total = 0

    return Envelope(
        data={
            "dataset_id": dataset.id,
            "dataset_type": dataset.dataset_type,
            "fields": fields,
            "records": records,
            "total": total,
            "offset": offset,
            "limit": limit,
        },
        meta=_meta(dataset),
    )


@router.post("/datasets/demo-seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """Reset / reseed deterministic demo dataset and run detection engines."""
    from app.services.bootstrap import reseed_demo_dataset
    dataset, run = reseed_demo_dataset(db)
    return Envelope(
        data={
            "dataset": dataset.id,
            "name": dataset.name,
            "version": dataset.version,
            "row_count": dataset.row_count,
            "quality_status": dataset.quality_status,
            "run_id": run.id,
            "run_status": run.status,
            "message": "Demo dataset reseeded and detection run completed.",
        },
        meta=_meta(dataset),
    )


# ---------------------------------------------------------------------------
# Detection run endpoints (unchanged contract from Prompt 1)
# ---------------------------------------------------------------------------



@router.post("/detection/runs")
def start_detection_run(
    dataset_id: str | None = None, db: Session = Depends(get_db)
):
    from app.schemas.schemas import DetectionRunOut

    dataset = db.get(Dataset, dataset_id) if dataset_id else _latest_project_dataset(db)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    run = run_detection(db, dataset)
    return Envelope(data=DetectionRunOut.model_validate(run).model_dump(), meta=_meta(dataset))


@router.get("/detection/runs")
def list_detection_runs(db: Session = Depends(get_db)):
    from app.models import DetectionRun
    from app.schemas.schemas import DetectionRunOut

    runs = db.query(DetectionRun).order_by(DetectionRun.started_at.desc()).limit(20).all()
    return Envelope(
        data=[DetectionRunOut.model_validate(r).model_dump() for r in runs],
        meta=_meta(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dataset_or_404(db: Session, dataset_id: str) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise NotFoundError("Dataset", dataset_id)
    return dataset


def _latest_project_dataset(db: Session) -> Dataset | None:
    """Latest dataset that actually contains works (detection needs projects)."""
    ds = latest_dataset(db)
    if ds is None:
        return None
    if ds.dataset_type == C.DatasetType.WORK_LEVEL.value:
        return ds
    return (
        db.query(Dataset)
        .filter(Dataset.dataset_type == C.DatasetType.WORK_LEVEL.value)
        .order_by(Dataset.ingested_at.desc(), Dataset.created_at.desc())
        .first()
    )


def _looks_synthetic(file_name: str) -> bool:
    lowered = file_name.lower()
    return "synthetic" in lowered or "fixture" in lowered or "demo" in lowered


def _dataset_out(d: Dataset) -> dict[str, Any]:
    return {
        "id": d.id,
        "name": d.name,
        "dataset_type": d.dataset_type,
        "source_type": d.source_type,
        "source_label": d.source_label,
        "source_url": d.source_url,
        "file_name": d.file_name,
        "file_hash": d.file_hash,
        "version": d.version,
        "is_synthetic": d.is_synthetic,
        "ingested_at": d.ingested_at.isoformat() if d.ingested_at else None,
        "row_count": d.row_count,
        "quality_status": d.quality_status,
        "quality_summary": d.quality_summary,
    }
