"""Shared API dependencies."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.database import get_db
from app.core.errors import DrishtiError
from app.models import Dataset, Project
from app.services.bootstrap import latest_dataset


def get_session() -> Session:
    return next(get_db())


def get_current_dataset(db: Session) -> Dataset:
    """The dataset the intelligence layer should operate on.

    Prompt 3 introduced typed datasets (MP allocations, aggregates). The
    detection/queue/dashboard screens only make sense for WORK_LEVEL data,
    so prefer the latest work-level dataset; fall back to the latest
    dataset only when no work-level data exists at all (screens then show
    their empty states rather than a misleading queue).
    """
    work_level = (
        db.query(Dataset)
        .filter(Dataset.dataset_type == C.DatasetType.WORK_LEVEL.value)
        .order_by(Dataset.ingested_at.desc(), Dataset.created_at.desc())
        .first()
    )
    if work_level is not None:
        return work_level
    ds = latest_dataset(db)
    if ds is None:
        raise DrishtiError(
            "No dataset has been ingested yet. Import a dataset or enable demo seeding.",
            status_code=409,
            code="no_dataset",
        )
    return ds


def get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        from app.core.errors import NotFoundError
        raise NotFoundError("Project", project_id)
    return project
