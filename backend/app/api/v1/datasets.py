"""Datasets + detection API: /api/v1/datasets, /api/v1/detection."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Dataset, DetectionRun
from app.schemas.schemas import Envelope, Meta, QualityIssue, QualityReport
from app.services.bootstrap import latest_dataset
from app.services.detection.runner import run_detection
from app.services.ingestion.ingestion import ingest_rows

router = APIRouter()


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.ingested_at.desc()).all()
    from app.schemas.schemas import DatasetOut
    return Envelope(
        data=[DatasetOut.model_validate(d).model_dump() for d in datasets],
        meta=Meta(generated_at=_now()),
    )


@router.get("/datasets/{dataset_id}/quality")
def dataset_quality(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    issues = _collect_quality_issues(db, dataset)
    report = QualityReport(
        dataset_id=dataset.id,
        quality_status=dataset.quality_status or "PENDING",
        total_rows=dataset.row_count,
        issues=issues,
        summary=dataset.quality_summary or {},
    )
    return Envelope(data=report.model_dump(), meta=Meta(dataset_version=dataset.version,
                                                       is_synthetic=dataset.is_synthetic,
                                                       generated_at=_now()))


@router.post("/datasets/import")
async def import_csv(
    file: UploadFile = File(...),
    name: str = "CSV import",
    db: Session = Depends(get_db),
):
    """Import a CSV dataset (official or demo). Provenance is recorded."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB).")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(r) for r in reader]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded CSV.")
    except csv.Error:
        raise HTTPException(status_code=400, detail="Malformed CSV file.")
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no data rows.")

    is_synthetic = "synthetic" in (file.filename or "").lower() or "demo" in (file.filename or "").lower()
    dataset = ingest_rows(
        db,
        rows,
        name=name,
        source_label=file.filename or "csv upload",
        source_type="CSV",
        version=_next_version(db),
        is_synthetic=is_synthetic,
    )
    run = run_detection(db, dataset)
    return Envelope(
        data={"dataset": dataset.id, "row_count": dataset.row_count,
              "quality_status": dataset.quality_status, "run_id": run.id,
              "run_status": run.status},
        meta=Meta(dataset_version=dataset.version, is_synthetic=dataset.is_synthetic,
                  generated_at=_now()),
    )


@router.post("/detection/runs")
def start_detection_run(dataset_id: str | None = None, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id) if dataset_id else latest_dataset(db)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    run = run_detection(db, dataset)
    from app.schemas.schemas import DetectionRunOut
    return Envelope(data=DetectionRunOut.model_validate(run).model_dump(),
                    meta=Meta(dataset_version=dataset.version, generated_at=_now()))


@router.get("/detection/runs")
def list_detection_runs(db: Session = Depends(get_db)):
    runs = db.query(DetectionRun).order_by(DetectionRun.started_at.desc()).limit(20).all()
    from app.schemas.schemas import DetectionRunOut
    return Envelope(data=[DetectionRunOut.model_validate(r).model_dump() for r in runs],
                    meta=Meta(generated_at=_now()))


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _next_version(db: Session) -> str:
    n = db.query(Dataset).count()
    return f"import-{n + 1:03d}"


def _collect_quality_issues(db: Session, dataset: Dataset) -> list[QualityIssue]:
    """Derive the issue list from stored DATA_QUALITY signals."""
    from app.models import Project, ProjectSignal

    projects = {p.id: p for p in db.query(Project).filter(
        Project.dataset_id == dataset.id).all()}
    signals = (
        db.query(ProjectSignal).filter(
            ProjectSignal.project_id.in_(list(projects.keys())),
            ProjectSignal.signal_type == "DATA_QUALITY",
            ProjectSignal.triggered.is_(True),
        ).all()
        if projects else []
    )
    issues: list[QualityIssue] = []
    for s in signals:
        p = projects[s.project_id]
        field = (s.reference_value or {}).get("field") if s.reference_value else None
        issues.append(QualityIssue(
            work_id=p.work_id,
            project_id=p.id,
            rule=s.title,
            severity=s.severity,
            field=None,
            detail=s.explanation,
        ))
    return issues
