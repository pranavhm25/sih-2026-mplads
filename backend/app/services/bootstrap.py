"""Bootstrap service.

Seeds demo officers, ingests the deterministic demo dataset and runs the
detection pipeline on startup when the database is empty (DEMO_AUTOSEED).
The demo dataset is always flagged is_synthetic=True for provenance.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.data.demo_data import REFERENCE_DATE, build_demo_rows
from app.models import Dataset, DetectionRun, InvestigationCase, Officer, Project, RelatedProject
from app.services.detection.runner import run_detection
from app.services.ingestion.ingestion import ingest_rows

logger = logging.getLogger("drishti.bootstrap")

DEMO_OFFICERS = [
    {"name": "Officer A. Sharma", "email": "sharma@drishti.demo", "role": "INVESTIGATOR"},
    {"name": "Supervisor V. Rao", "email": "rao@drishti.demo", "role": "SUPERVISOR"},
    {"name": "Admin K. Iyer", "email": "admin@drishti.demo", "role": "ADMIN"},
]


def ensure_officers(db: Session) -> list[Officer]:
    officers = db.query(Officer).all()
    if officers:
        return officers
    for o in DEMO_OFFICERS:
        db.add(Officer(**o))
    db.commit()
    return db.query(Officer).all()


def latest_dataset(db: Session) -> Dataset | None:
    return (
        db.query(Dataset)
        .order_by(Dataset.ingested_at.desc(), Dataset.created_at.desc())
        .first()
    )


def wipe_demo_datasets(db: Session) -> int:
    """Wipe any existing synthetic demo datasets and their associated records."""
    demo_datasets = db.query(Dataset).filter(Dataset.is_synthetic.is_(True)).all()
    if not demo_datasets:
        return 0

    count = len(demo_datasets)
    ds_ids = [d.id for d in demo_datasets]

    # Find projects in demo datasets
    projects = db.query(Project).filter(Project.dataset_id.in_(ds_ids)).all()
    project_ids = [p.id for p in projects]

    if project_ids:
        # Cases attached to these projects
        cases = db.query(InvestigationCase).filter(InvestigationCase.project_id.in_(project_ids)).all()
        for c in cases:
            db.delete(c)
        db.flush()

        # Related projects bidirectional links
        db.query(RelatedProject).filter(
            (RelatedProject.project_id.in_(project_ids))
            | (RelatedProject.related_project_id.in_(project_ids))
        ).delete(synchronize_session=False)
        db.flush()

        # Delete projects (cascades to metrics, signals, evidence, peer links)
        for p in projects:
            db.delete(p)
        db.flush()

    # Delete detection runs associated with demo datasets
    db.query(DetectionRun).filter(DetectionRun.dataset_id.in_(ds_ids)).delete(synchronize_session=False)
    db.flush()

    # Delete demo datasets
    for d in demo_datasets:
        db.delete(d)
    db.commit()

    logger.info("Wiped %d synthetic demo dataset(s).", count)
    return count


def reseed_demo_dataset(db: Session) -> tuple[Dataset, DetectionRun]:
    """Wipe any existing synthetic demo datasets and reseed fresh demo data."""
    ensure_officers(db)
    wipe_demo_datasets(db)

    logger.info("Reseeding deterministic demo dataset…")
    rows = build_demo_rows()
    dataset = ingest_rows(
        db,
        rows,
        name="SIH 2026 demo dataset (synthetic)",
        source_label="Controlled synthetic demo — not official MPLADS records",
        version="demo-01",
        is_synthetic=True,
    )
    run = run_detection(db, dataset, today=REFERENCE_DATE)
    logger.info(
        "Demo dataset %s reseeded (%d works) and detection run %s completed.",
        dataset.id,
        dataset.row_count,
        run.id,
    )
    return dataset, run


def seed_demo_if_empty(db: Session) -> Dataset | None:
    """Ingest demo data + run detection when no dataset exists yet."""
    if db.query(Dataset).count() > 0:
        return None
    if not settings.demo_autoseed:
        return None

    dataset, _ = reseed_demo_dataset(db)
    return dataset


def bootstrap(db: Session) -> None:
    ensure_officers(db)
    seed_demo_if_empty(db)
