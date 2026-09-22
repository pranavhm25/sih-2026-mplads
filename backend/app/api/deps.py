"""Shared API dependencies."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import DrishtiError
from app.models import Dataset, Project
from app.services.bootstrap import latest_dataset


def get_session() -> Session:
    return next(get_db())


def get_current_dataset(db: Session) -> Dataset:
    """Latest ingested dataset, or raise a structured error if none."""
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
