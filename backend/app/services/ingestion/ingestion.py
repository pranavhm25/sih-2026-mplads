"""Ingestion service: canonical schema mapping, normalization, provenance.

Handles raw row dicts (from CSV import or demo fixture), validates and
normalizes them, and persists Dataset + Project records in one transaction.
Failed ingestion does not partially corrupt the database (TRD Reliability).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import DatasetStatus
from app.models import Dataset, Project

logger = logging.getLogger("drishti.ingestion")

# Source column aliases → canonical field names (TR-01).
COLUMN_ALIASES: dict[str, str] = {
    "work_id": "work_id",
    "workid": "work_id",
    "work id": "work_id",
    "id": "work_id",
    "mp_name": "mp_name",
    "mp": "mp_name",
    "mp name": "mp_name",
    "constituency": "constituency",
    "state": "state",
    "district": "district",
    "location": "location_text",
    "location_text": "location_text",
    "latitude": "latitude",
    "latitude_dd": "latitude",
    "lat": "latitude",
    "longitude": "longitude",
    "longitude_dd": "longitude",
    "lon": "longitude",
    "category": "category",
    "sector": "sector",
    "description": "description",
    "work_description": "description",
    "estimated_cost": "estimated_cost",
    "sanctioned_cost": "sanctioned_cost",
    "expenditure": "expenditure",
    "exp_amount": "expenditure",
    "financial_progress": "financial_progress",
    "physical_progress": "physical_progress",
    "sanction_date": "sanction_date",
    "start_date": "start_date",
    "completion_date": "completion_date",
    "status": "status",
    "implementing_agency": "implementing_agency",
    "agency": "implementing_agency",
    "contractor_name": "contractor_name",
    "contractor": "contractor_name",
    "expected_duration_days": "expected_duration_days",
    "expected_duration": "expected_duration_days",
}

MANDATORY_FIELDS = [
    "work_id", "state", "district", "description",
    "estimated_cost", "sanctioned_cost", "financial_progress", "physical_progress",
]

DATE_FIELDS = ["sanction_date", "start_date", "completion_date"]
NUMERIC_FIELDS = [
    "estimated_cost", "sanctioned_cost", "expenditure",
    "financial_progress", "physical_progress",
    "latitude", "longitude", "expected_duration_days",
]

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y")


def normalize_header(h: str) -> str:
    return h.strip().lower().replace("-", "_").replace(" ", "_")


def map_columns(row: dict[str, Any]) -> dict[str, Any]:
    """Map a raw CSV row (any header style) to canonical field names."""
    mapped: dict[str, Any] = {}
    for k, v in row.items():
        canonical = COLUMN_ALIASES.get(normalize_header(k))
        if canonical:
            mapped[canonical] = v
    return mapped


def parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_numeric(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).strip()
    text = text.replace("₹", "").replace(",", "").replace(" ", "")
    # Handle lakh/crore suffixes as present in MPLADS exports.
    upper = text.upper()
    try:
        if upper.endswith("CR"):
            return Decimal(text[:-2]) * 10000000
        if upper.endswith("L"):
            return Decimal(text[:-1]) * 100000
        return Decimal(text)
    except InvalidOperation:
        return None


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize types: dates, numerics, strings."""
    out: dict[str, Any] = {}
    for field, value in row.items():
        if field in DATE_FIELDS:
            out[field] = parse_date(value)
        elif field == "expected_duration_days":
            n = parse_numeric(value)
            out[field] = int(n) if n is not None else None
        elif field in NUMERIC_FIELDS:
            out[field] = parse_numeric(value)
        else:
            out[field] = str(value).strip() if value not in (None, "") else None
    return out


def _missing_mandatory(clean: dict[str, Any]) -> list[str]:
    missing = []
    for f in MANDATORY_FIELDS:
        v = clean.get(f)
        if v in (None, ""):
            missing.append(f)
    return missing


def ingest_rows(
    db: Session,
    rows: list[dict[str, Any]],
    *,
    name: str,
    source_label: str,
    source_type: str = "CSV",
    version: str = "v1",
    is_synthetic: bool = False,
) -> Dataset:
    """Validate + persist rows as a Dataset with Projects (atomic)."""
    dataset = Dataset(
        name=name,
        source_type=source_type,
        source_label=source_label,
        version=version,
        is_synthetic=is_synthetic,
        row_count=0,
        quality_status=DatasetStatus.PENDING,
    )
    db.add(dataset)
    db.flush()

    valid_projects: list[Project] = []
    invalid_rows = 0
    missing_field_counts: dict[str, int] = {}

    for raw in rows:
        mapped = map_columns(raw)
        clean = normalize_row(mapped)
        missing = _missing_mandatory(clean)
        if missing:
            invalid_rows += 1
            for f in missing:
                missing_field_counts[f] = missing_field_counts.get(f, 0) + 1
            continue

        project = Project(
            dataset_id=dataset.id,
            work_id=str(clean["work_id"]),
            mp_name=clean.get("mp_name"),
            constituency=clean.get("constituency"),
            state=str(clean["state"]),
            district=str(clean["district"]),
            location_text=clean.get("location_text"),
            latitude=clean.get("latitude"),
            longitude=clean.get("longitude"),
            category=clean.get("category"),
            sector=clean.get("sector"),
            description=str(clean["description"]),
            estimated_cost=clean["estimated_cost"],
            sanctioned_cost=clean["sanctioned_cost"],
            expenditure=clean.get("expenditure"),
            financial_progress=clean["financial_progress"],
            physical_progress=clean["physical_progress"],
            sanction_date=clean.get("sanction_date"),
            start_date=clean.get("start_date"),
            completion_date=clean.get("completion_date"),
            status=clean.get("status") or "Unknown",
            implementing_agency=clean.get("implementing_agency"),
            contractor_name=clean.get("contractor_name"),
            expected_duration_days=clean.get("expected_duration_days"),
        )
        valid_projects.append(project)

    db.add_all(valid_projects)
    dataset.row_count = len(valid_projects)
    dataset.quality_status = (
        DatasetStatus.VALID if invalid_rows == 0 else DatasetStatus.VALID_WITH_WARNINGS
    )
    dataset.quality_summary = {
        "rows_received": len(rows),
        "rows_ingested": len(valid_projects),
        "rows_rejected": invalid_rows,
        "missing_mandatory_counts": missing_field_counts,
        "is_synthetic": is_synthetic,
    }
    db.commit()
    return dataset
