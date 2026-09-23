"""Official import orchestrator (Prompt-3 §10, §28, §43, §47).

One function per pipeline stage, chained by `import_official_file`:

    parse → detect schema → map columns → normalize → validate
          → persist valid rows (partial validity) → record issues
          → compute quality → provenance + summary

Rules enforced here:
- Partial validity: ERROR rows are skipped but preserved as ValidationIssue
  records; WARNING/INFO rows are imported alongside their issues (§27).
- Provenance: every dataset records source name/type, file name, SHA-256
  hash and detected source schema (§8, §43).
- Duplicate uploads are detected via file hash and rejected (§43).
- Structured logging events surround each stage (§47).
- Language discipline: data issues are data-quality findings, never fraud
  (§50).
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import DatasetSourceType, DatasetType
from app.core.errors import DrishtiError
from app.models import (
    Dataset,
    MPAllocationRecord,
    Project,
    SchemeAggregate,
    ValidationIssue,
)
from app.services.ingestion.parsers import ParsedFile, parse_file
from app.services.ingestion.registry import (
    SourceSchema,
    build_source_schema_record,
    detect_schema,
    unmatched_required_fields,
)
from app.services.ingestion.validation import (
    ValidationReport,
    normalize_aggregate_row,
    normalize_mp_allocation_row,
    normalize_work_level_row,
    validate_aggregate_rows,
    validate_mp_allocation_rows,
    validate_work_level_rows,
)

logger = logging.getLogger("drishti.ingestion")

SOURCE_NAME_OFFICIAL = "MPLADS e-SAKSHI"
SOURCE_NAME_SYNTHETIC = "Drishti Synthetic Fixture"


class ImportRejected(DrishtiError):
    """Structured import rejection (Prompt-3 §46)."""

    def __init__(self, message: str, code: str, details: dict | None = None):
        self.details = details or {}
        super().__init__(message=message, status_code=400, code=code)


def sha256_of(raw: bytes) -> str:
    """Deterministic file identity (§43)."""
    return hashlib.sha256(raw).hexdigest()


def find_duplicate(db: Session, file_hash: str) -> Dataset | None:
    return (
        db.query(Dataset)
        .filter(Dataset.file_hash == file_hash)
        .first()
    )


def persist_dataset(
    db: Session,
    *,
    name: str,
    dataset_type: DatasetType,
    source_type: DatasetSourceType,
    source_label: str,
    version: str,
    is_synthetic: bool,
    file_name: str | None,
    file_hash: str | None,
    source_url: str | None = None,
    source_schema: dict | None = None,
) -> Dataset:
    """Create the dataset row with full provenance (§8)."""
    dataset = Dataset(
        name=name,
        dataset_type=dataset_type.value,
        source_type=source_type.value,
        source_label=source_label,
        version=version,
        is_synthetic=is_synthetic,
        file_name=file_name,
        file_hash=file_hash,
        source_url=source_url,
        source_schema=source_schema,
        retrieved_at=datetime.now(timezone.utc) if not is_synthetic else None,
        row_count=0,
        quality_status="PENDING",
    )
    db.add(dataset)
    db.flush()
    return dataset


def persist_validation_issues(
    db: Session, dataset_id: str, report: ValidationReport
) -> int:
    """Preserve every validation issue — including ERROR rows (§27, §45)."""
    for issue in report.issues:
        db.add(ValidationIssue(
            dataset_id=dataset_id,
            row_number=issue.row_number,
            field=issue.field,
            rule=issue.rule,
            severity=issue.severity,
            message=issue.message,
            observed_value=issue.observed_value,
        ))
    db.flush()
    return len(report.issues)


def persist_mp_allocation_rows(
    db: Session, dataset: Dataset, rows: list[dict[str, Any]]
) -> int:
    for row in rows:
        db.add(MPAllocationRecord(dataset_id=dataset.id, **{
            k: v for k, v in row.items() if not k.startswith("_")
        }))
    db.flush()
    return len(rows)


def persist_aggregate_rows(
    db: Session, dataset: Dataset, rows: list[dict[str, Any]]
) -> int:
    for row in rows:
        db.add(SchemeAggregate(dataset_id=dataset.id, **{
            k: v for k, v in row.items() if not k.startswith("_")
        }))
    db.flush()
    return len(rows)


def _work_level_to_project(row: dict[str, Any], dataset_id: str) -> Project:
    """Canonical work record from a normalized official row.

    Fields the source did not provide remain NULL — never fabricated (§4).
    """
    return Project(
        dataset_id=dataset_id,
        work_id=row["work_id"],
        mp_name=row.get("mp_name"),
        constituency=row.get("constituency"),
        state=row["state"],
        district=row["district"],
        description=row["description"],
        estimated_cost=row.get("estimated_cost") if row.get("estimated_cost") is not None else row.get("sanctioned_amount"),
        sanctioned_cost=row["sanctioned_amount"],
        expenditure=row.get("expenditure"),
        financial_progress=row.get("financial_progress") if row.get("financial_progress") is not None else 0,
        physical_progress=row.get("physical_progress") if row.get("physical_progress") is not None else 0,
        sanction_date=row.get("sanction_date"),
        start_date=row.get("start_date"),
        completion_date=row.get("completion_date"),
        category=row.get("category"),
        sector=row.get("sector"),
        status=row.get("status") or "Unknown",
        implementing_agency=row.get("implementing_agency"),
        contractor_name=row.get("contractor_name"),
        expected_duration_days=row.get("expected_duration_days"),
        location_text=row.get("location_text"),
        latitude=row.get("latitude"),
        longitude=row.get("longitude"),
    )


def persist_work_level_rows(
    db: Session, dataset: Dataset, rows: list[dict[str, Any]]
) -> int:
    from app.models import PaymentRecord

    payments = 0
    for row in rows:
        project = _work_level_to_project(row, dataset.id)
        db.add(project)
        db.flush()  # assign project.id before wiring optional payments
        for pay in row.get("_payments", []):
            if pay.get("amount") is None:
                continue
            db.add(PaymentRecord(
                project_id=project.id,
                dataset_id=dataset.id,
                payment_ref=pay.get("payment_ref"),
                amount=pay["amount"],
                currency="INR",
                unit=pay.get("unit") or "RUPEE",
                paid_on=pay.get("paid_on"),
                payee=pay.get("payee"),
                stage=pay.get("stage"),
                source_row_number=row.get("source_row_number"),
            ))
            payments += 1
    db.flush()
    if payments:
        logger.info("payment_records_persisted count=%d dataset_id=%s", payments, dataset.id)
    return len(rows)


def build_import_summary(
    *,
    dataset: Dataset,
    dataset_type: DatasetType,
    source_type: DatasetSourceType,
    report: ValidationReport,
    total_source_rows: int,
    parse_notes: list[str],
    duplicate_of: Dataset | None = None,
) -> dict[str, Any]:
    """Structured import response (Prompt-3 §12) following the Envelope."""
    quality = dataset.quality_status or "PENDING"
    data: dict[str, Any] = {
        "dataset_id": dataset.id,
        "dataset_type": dataset.dataset_type,
        "source_type": dataset.source_type,
        "status": "IMPORTED",
        "row_count": dataset.row_count,
        "valid_rows": report.valid_rows,
        "warning_rows": report.warning_rows,
        "error_rows": report.error_rows,
        "quality_status": quality,
        "quality_reasons": report.reasons(),
        "is_synthetic": dataset.is_synthetic,
        "file_name": dataset.file_name,
        "file_hash": dataset.file_hash,
        "issue_counts_by_rule": report.counts_by_rule(),
        "missing_field_counts": report.missing_field_counts(),
        "invalid_field_counts": report.invalid_field_counts(),
        "duplicate_counts": report.duplicate_counts(),
        "parse_notes": parse_notes,
        "duplicate_dataset": duplicate_of.id if duplicate_of else None,
    }
    return data


def _key(header: str) -> str:
    """Header key matching the registry's normalization."""
    from app.services.ingestion.registry import _key as registry_key

    return registry_key(header)


def _detect_dataset_type(
    parsed: ParsedFile, requested: str | None
) -> tuple[DatasetType, SourceSchema | None, dict[str, str]]:
    """Type from request when valid; otherwise deterministic detection (§11)."""
    if requested:
        try:
            forced = DatasetType(requested)
        except ValueError as exc:
            raise ImportRejected(
                f"Unknown dataset_type '{requested}'.",
                "INVALID_DATASET_TYPE",
                {"allowed": [t.value for t in DatasetType]},
            ) from exc
        # Pick the best-matching registered schema *within the forced type*
        # (deterministic: highest match score, then registry order).
        from app.services.ingestion.registry import SCHEMAS, map_headers
        best: SourceSchema | None = None
        best_map: dict[str, str] = {}
        best_score = -1
        for schema in SCHEMAS:
            if schema.dataset_type != forced:
                continue
            score = schema.match_score({_key(h) for h in parsed.headers})
            cmap = map_headers(schema, parsed.headers)
            if score > best_score or (score == best_score and len(cmap) > len(best_map)):
                best, best_map, best_score = schema, cmap, score
        return forced, best, best_map

    schema, col_map = detect_schema(parsed.headers)
    if schema is None:
        raise ImportRejected(
            "The uploaded dataset does not match any known MPLADS export schema.",
            "INVALID_DATASET",
            {"observed_columns": parsed.headers[:40]},
        )
    return schema.dataset_type, schema, col_map


def _check_unmapped_required(
    schema: SourceSchema | None, parsed: ParsedFile
) -> None:
    if schema is None:
        return
    missing = unmatched_required_fields(schema, parsed.headers)
    if missing:
        raise ImportRejected(
            "The uploaded dataset does not contain the required fields.",
            "INVALID_DATASET",
            {"missing_required_fields": missing, "observed_columns": parsed.headers[:40]},
        )


def import_official_file(
    db: Session,
    raw: bytes,
    *,
    file_name: str,
    dataset_type: str | None = None,
    source_url: str | None = None,
    name: str | None = None,
    version: str | None = None,
    is_synthetic: bool = False,
    run_pipeline: bool = True,
    pipeline_runner=None,
) -> dict[str, Any]:
    """Full official-import pipeline (Prompt-3 §10). Returns §12 response data.

    `pipeline_runner` lets the API layer attach detection without creating a
    circular import; callers pass `run_detection`-style callables.
    """
    started = time.perf_counter()
    logger.info("dataset_import_started dataset=%s", file_name)

    # 0. Duplicate-upload guard (§43).
    file_hash = sha256_of(raw)
    duplicate_of = find_duplicate(db, file_hash)
    if duplicate_of is not None:
        raise ImportRejected(
            "This file has already been imported.",
            "DUPLICATE_DATASET",
            {"existing_dataset_id": duplicate_of.id, "file_hash": file_hash},
        )

    # 1. Parse.
    try:
        parsed = parse_file(raw, file_name)
    except DrishtiError:
        logger.info("dataset_import_failed file=%s stage=parse", file_name)
        raise

    # 2. Identify dataset type + schema; map columns.
    dtype, schema, column_map = _detect_dataset_type(parsed, dataset_type)
    _check_unmapped_required(schema, parsed)
    logger.info(
        "source_schema_detected dataset=%s type=%s schema=%s",
        file_name, dtype.value, schema.schema_id if schema else "none",
    )

    # 3. Normalize rows.
    if dtype == DatasetType.MP_ALLOCATION:
        normalized = [
            normalize_mp_allocation_row(row, column_map, i)
            for i, row in enumerate(parsed.rows, start=1)
        ]
    elif dtype == DatasetType.SCHEME_AGGREGATE:
        normalized = [
            normalize_aggregate_row(row, column_map, i)
            for i, row in enumerate(parsed.rows, start=1)
        ]
    else:
        normalized = [
            normalize_work_level_row(row, column_map, i)
            for i, row in enumerate(parsed.rows, start=1)
        ]
    logger.info("normalization_completed dataset=%s rows=%d", file_name, len(normalized))

    # 4. Validate.
    if dtype == DatasetType.MP_ALLOCATION:
        report = validate_mp_allocation_rows(normalized)
    elif dtype == DatasetType.SCHEME_AGGREGATE:
        report = validate_aggregate_rows(normalized)
    else:
        report = validate_work_level_rows(normalized)
    logger.info(
        "validation_completed dataset=%s rows=%d errors=%d warnings=%d",
        file_name, len(normalized), report.error_rows, report.warning_rows,
    )

    # 5. Provenance + dataset row.
    if is_synthetic:
        source_type = DatasetSourceType.SYNTHETIC_FIXTURE
        source_label = SOURCE_NAME_SYNTHETIC
    else:
        source_type = DatasetSourceType.OFFICIAL_FILE_UPLOAD
        source_label = SOURCE_NAME_OFFICIAL
    dataset = persist_dataset(
        db,
        name=name or f"{dtype.value} import — {file_name}",
        dataset_type=dtype,
        source_type=source_type,
        source_label=source_label,
        version=version or _next_version(db),
        is_synthetic=is_synthetic,
        file_name=file_name,
        file_hash=file_hash,
        source_url=source_url,
        source_schema=build_source_schema_record(schema, parsed.headers, column_map),
    )

    # 6. Partial-validity persistence (§27).
    valid_rows = [r for r in normalized if not report.row_has_error(r["source_row_number"])]
    if dtype == DatasetType.MP_ALLOCATION:
        persisted = persist_mp_allocation_rows(db, dataset, valid_rows)
    elif dtype == DatasetType.SCHEME_AGGREGATE:
        persisted = persist_aggregate_rows(db, dataset, valid_rows)
    else:
        persisted = persist_work_level_rows(db, dataset, valid_rows)
    persist_validation_issues(db, dataset.id, report)

    # 7. Quality status (§28/§29) — deterministic states.
    dataset.row_count = persisted
    dataset.quality_status = report.quality_status()
    dataset.quality_summary = {
        "total_rows": len(normalized),
        "valid_rows": report.valid_rows,
        "warning_rows": report.warning_rows,
        "error_rows": report.error_rows,
        "missing_field_counts": report.missing_field_counts(),
        "invalid_field_counts": report.invalid_field_counts(),
        "duplicate_counts": report.duplicate_counts(),
        "reasons": report.reasons(),
        "parse_notes": parsed.issues,
    }
    db.commit()
    logger.info("dataset_persisted dataset=%s rows=%d", dataset.id, persisted)

    # 8. Optional downstream pipeline (detection) — official work-level data only.
    if run_pipeline and dtype == DatasetType.WORK_LEVEL and pipeline_runner is not None:
        try:
            pipeline_runner(db, dataset)
        except Exception:  # noqa: BLE001 — import stays valid; detection failure visible
            logger.exception("detection_after_import_failed dataset=%s", dataset.id)

    summary = build_import_summary(
        dataset=dataset,
        dataset_type=dtype,
        source_type=source_type,
        report=report,
        total_source_rows=len(normalized),
        parse_notes=parsed.issues,
        duplicate_of=duplicate_of,
    )
    logger.info(
        "dataset_import_completed dataset=%s type=%s rows=%d quality=%s duration=%.2fs",
        dataset.id, dtype.value, persisted, summary["quality_status"],
        time.perf_counter() - started,
    )
    return summary


def _next_version(db: Session) -> str:
    from app.models import Dataset as D

    n = db.query(D).count()
    return f"import-{n + 1:03d}"
