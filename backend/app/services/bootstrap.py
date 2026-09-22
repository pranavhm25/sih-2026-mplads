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
from app.models import Dataset, Officer, Project
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


def seed_demo_if_empty(db: Session) -> Dataset | None:
    """Ingest demo data + run detection when no dataset exists yet."""
    if db.query(Dataset).count() > 0:
        return None
    if not settings.demo_autoseed:
        return None

    logger.info("Seeding deterministic demo dataset…")
    rows = build_demo_rows()
    dataset = ingest_rows(
        db,
        rows,
        name="SIH 2026 demo dataset (synthetic)",
        source_label="Controlled synthetic demo — not official MPLADS records",
        version="demo-01",
        is_synthetic=True,
    )
    run_detection(db, dataset, today=REFERENCE_DATE)
    logger.info("Demo dataset %s ingested (%d works) and detection completed.",
                dataset.id, dataset.row_count)
    return dataset


def bootstrap(db: Session) -> None:
    ensure_officers(db)
    seed_demo_if_empty(db)
