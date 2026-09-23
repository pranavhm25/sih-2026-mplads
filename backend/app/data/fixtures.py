"""Synthetic fixtures (Prompt-3 §39/§40).

Byte-level fixture files under app/data/fixtures exercise the ingestion
architecture exactly like an official upload. They are ALWAYS ingested with
is_synthetic=True, source_type=SYNTHETIC_FIXTURE — never presented as
official MPLADS data (§40).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.ingestion.orchestrator import import_official_file

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

# Fixture name → (path, dataset_type hint, display name)
FIXTURES: dict[str, tuple[Path, str, str]] = {
    "mp_allocation_ls": (
        FIXTURE_DIR / "mp_allocation_ls.csv", "MP_ALLOCATION",
        "Synthetic MP allocation — Lok Sabha structure",
    ),
    "mp_allocation_rs": (
        FIXTURE_DIR / "mp_allocation_rs.csv", "MP_ALLOCATION",
        "Synthetic MP allocation — Rajya Sabha structure",
    ),
    "scheme_aggregate": (
        FIXTURE_DIR / "scheme_aggregate.csv", "SCHEME_AGGREGATE",
        "Synthetic scheme aggregate statistics",
    ),
    "work_level": (
        FIXTURE_DIR / "work_level.csv", "WORK_LEVEL",
        "Synthetic work-level records",
    ),
}


def fixture_names() -> list[str]:
    return sorted(FIXTURES)


def load_fixture_bytes(name: str) -> bytes:
    """Raw fixture bytes, or raise a structured error for unknown names."""
    entry = FIXTURES.get(name)
    if entry is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Fixture", name)
    return entry[0].read_bytes()


def ingest_fixture(
    db: Session,
    name: str,
    *,
    pipeline_runner=None,
) -> dict[str, Any]:
    """Ingest a named synthetic fixture through the official pipeline.

    The result is always a synthetic dataset (is_synthetic=True,
    source_type=SYNTHETIC_FIXTURE) regardless of file content.
    """
    path, dtype, display = FIXTURES[name]
    raw = path.read_bytes()
    return import_official_file(
        db,
        raw,
        file_name=path.name,
        dataset_type=dtype,
        name=f"{display} (synthetic fixture)",
        is_synthetic=True,
        run_pipeline=bool(pipeline_runner),
        pipeline_runner=pipeline_runner,
    )
