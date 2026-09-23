"""Row-level validation for official imports (Prompt-3 §23–29).

Validators are dataset-type-specific: an MP allocation row is not a work
row, and work-level rules never run against MP allocation records (§26).
Every issue carries row_number, field, rule, severity, message and the
observed value. ERROR rows are excluded from persistence but always
preserved as ValidationIssue records — never silently discarded (§27).

Data inconsistencies are reported as data-quality issues, never as fraud
findings (§50).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.core.constants import DatasetType, IssueSeverity
from app.services.ingestion.normalizers import normalize_monetary, to_rupees

# MP allocation validations (§24) — severities fixed by the prompt.
MP_ALLOCATION_SEVERITY: dict[str, str] = {
    "missing_state": IssueSeverity.ERROR,
    "missing_mp_name": IssueSeverity.ERROR,
    "invalid_amount": IssueSeverity.ERROR,
    "negative_amount": IssueSeverity.ERROR,
    "duplicate_serial": IssueSeverity.WARNING,
    "duplicate_mp_record": IssueSeverity.WARNING,
    "implausible_amount": IssueSeverity.WARNING,
    "invalid_serial": IssueSeverity.INFO,
}

# Scheme aggregate validations (§25).
AGGREGATE_SEVERITY: dict[str, str] = {
    "aggregate_consistency_issue": IssueSeverity.WARNING,
    "invalid_count": IssueSeverity.ERROR,
    "invalid_amount": IssueSeverity.ERROR,
}

# Work-level validations (§26) — only when a work dataset is imported.
WORK_LEVEL_SEVERITY: dict[str, str] = {
    "missing_work_id": IssueSeverity.ERROR,
    "missing_state": IssueSeverity.ERROR,
    "missing_district": IssueSeverity.ERROR,
    "missing_description": IssueSeverity.ERROR,
    "missing_sanctioned_amount": IssueSeverity.ERROR,
    "invalid_numeric": IssueSeverity.ERROR,
    "negative_amount": IssueSeverity.ERROR,
    "progress_out_of_range": IssueSeverity.ERROR,
    "expenditure_above_sanctioned": IssueSeverity.WARNING,
    "invalid_date_order": IssueSeverity.WARNING,
    "invalid_coordinates": IssueSeverity.WARNING,
    "duplicate_work_id": IssueSeverity.ERROR,
}


@dataclass
class Issue:
    """One validation issue (§23) — exactly the fields the UI table needs."""

    row_number: int | None
    field: str | None
    rule: str
    severity: str
    message: str
    observed_value: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_number": self.row_number,
            "field": self.field,
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "observed_value": self.observed_value,
        }


class ValidationReport:
    """Accumulated issues for one import + quality-status computation (§28/§29)."""

    def __init__(self, total_rows: int) -> None:
        self.total_rows = total_rows
        self.issues: list[Issue] = []
        # Rows whose source-row index produced at least one ERROR.
        self._error_rows: set[int] = set()
        self._warn_rows: set[int] = set()

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)
        if issue.row_number is not None:
            if issue.severity == IssueSeverity.ERROR:
                self._error_rows.add(issue.row_number)
            elif issue.severity == IssueSeverity.WARNING:
                self._warn_rows.add(issue.row_number)

    @property
    def error_rows(self) -> int:
        return len(self._error_rows)

    @property
    def warning_rows(self) -> int:
        return len(self._warn_rows)

    @property
    def valid_rows(self) -> int:
        return self.total_rows - self.error_rows

    def row_has_error(self, row_number: int | None) -> bool:
        return row_number is not None and row_number in self._error_rows

    def counts_by_rule(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.rule] = counts.get(issue.rule, 0) + 1
        return counts

    def missing_field_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            if issue.rule.startswith("missing_"):
                key = issue.field or issue.rule
                counts[key] = counts.get(key, 0) + 1
        return counts

    def invalid_field_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            if issue.rule.startswith(("invalid_", "negative_", "progress_out_of_range")):
                key = issue.field or issue.rule
                counts[key] = counts.get(key, 0) + 1
        return counts

    def duplicate_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            if "duplicate" in issue.rule:
                counts[issue.rule] = counts.get(issue.rule, 0) + 1
        return counts

    def quality_status(self) -> str:
        """Deterministic, explainable quality state (§29) — no opaque score."""
        if self.total_rows == 0:
            return "FAILED"
        error_rate = self.error_rows / self.total_rows
        warn_rate = self.warning_rows / self.total_rows
        from app.core import constants as C
        if error_rate == 0 and warn_rate == 0:
            return "GOOD"
        if error_rate <= C.QUALITY_ERROR_RATE_ACCEPTABLE and warn_rate <= C.QUALITY_WARN_RATE_DEGRADED:
            return "ACCEPTABLE"
        if error_rate <= C.QUALITY_ERROR_RATE_DEGRADED:
            return "DEGRADED"
        return "FAILED"

    def reasons(self) -> list[str]:
        """Plain-language reasons behind the quality status (§29 example)."""
        reasons: list[str] = []
        by_rule = self.counts_by_rule()
        for rule, count in sorted(by_rule.items(), key=lambda kv: -kv[1]):
            label = rule.replace("_", " ")
            reasons.append(f"{count} record{'s' if count != 1 else ''} with {label}")
        return reasons


def validate_mp_allocation_rows(
    normalized_rows: list[dict[str, Any]],
) -> ValidationReport:
    """MP allocation validations (§24). No fraud language; data issues only."""
    report = ValidationReport(len(normalized_rows))
    seen_serials: dict[Any, int] = {}
    seen_mp: dict[tuple[str | None, str | None], int] = {}

    for row in normalized_rows:
        n = row["source_row_number"]

        state = row.get("state")
        if not state:
            report.add(Issue(
                n, "state", "missing_state",
                MP_ALLOCATION_SEVERITY["missing_state"],
                "Missing state.", _obs(state),
            ))

        mp_name = row.get("mp_name")
        if not mp_name:
            report.add(Issue(
                n, "mp_name", "missing_mp_name",
                MP_ALLOCATION_SEVERITY["missing_mp_name"],
                "Missing MP name.", _obs(mp_name),
            ))

        amount = row.get("allocated_amount")
        if amount is None:
            report.add(Issue(
                n, "allocated_amount", "invalid_amount",
                MP_ALLOCATION_SEVERITY["invalid_amount"],
                "Invalid or missing allocated amount.", _obs(row.get("_raw_amount")),
            ))
        elif amount < 0:
            report.add(Issue(
                n, "allocated_amount", "negative_amount",
                MP_ALLOCATION_SEVERITY["negative_amount"],
                "Negative allocation amount.", _obs(amount),
            ))
        elif amount < Decimal(100000):
            report.add(Issue(
                n, "allocated_amount", "implausible_amount",
                MP_ALLOCATION_SEVERITY["implausible_amount"],
                "Allocated amount is below ₹1 lakh; verify the unit (₹ vs Crore).",
                _obs(amount),
            ))

        serial = row.get("serial_number")
        if serial is None:
            report.add(Issue(
                n, "serial_number", "invalid_serial",
                MP_ALLOCATION_SEVERITY["invalid_serial"],
                "Serial number missing or not numeric.", _obs(row.get("_raw_serial")),
            ))
        else:
            first = seen_serials.get(serial)
            if first is not None:
                report.add(Issue(
                    n, "serial_number", "duplicate_serial",
                    MP_ALLOCATION_SEVERITY["duplicate_serial"],
                    f"Duplicate serial number {serial} (first seen in row {first}).",
                    _obs(serial),
                ))
            else:
                seen_serials[serial] = n

        key = (state, mp_name)
        if mp_name and key in seen_mp:
            first = seen_mp[key]
            report.add(Issue(
                n, "mp_name", "duplicate_mp_record",
                MP_ALLOCATION_SEVERITY["duplicate_mp_record"],
                f"Possible duplicate MP record (first seen in row {first}).",
                _obs(mp_name),
            ))
        elif mp_name:
            seen_mp[key] = n

    return report


def validate_aggregate_rows(
    normalized_rows: list[dict[str, Any]],
) -> ValidationReport:
    """Aggregate consistency checks (§25). Warnings, never fraud labels."""
    report = ValidationReport(len(normalized_rows))
    for row in normalized_rows:
        n = row["source_row_number"]
        recommended = row.get("works_recommended")
        sanctioned = row.get("works_sanctioned")
        completed = row.get("works_completed")

        for field_name, value in (
            ("works_recommended", recommended),
            ("works_sanctioned", sanctioned),
            ("works_completed", completed),
        ):
            if value is not None and value < 0:
                report.add(Issue(
                    n, field_name, "invalid_count",
                    AGGREGATE_SEVERITY["invalid_count"],
                    f"{field_name} is negative.", _obs(value),
                ))

        if (
            completed is not None and sanctioned is not None
            and completed > sanctioned
        ):
            report.add(Issue(
                n, "works_completed", "aggregate_consistency_issue",
                AGGREGATE_SEVERITY["aggregate_consistency_issue"],
                f"Works completed ({completed}) exceed works sanctioned "
                f"({sanctioned}) — aggregate consistency issue.",
                _obs(completed),
            ))

        for field_name in ("allocated_limit", "amount_consented_for_calamity",
                           "expenditure_completed_and_ongoing"):
            value = row.get(field_name)
            if value is not None and value < 0:
                report.add(Issue(
                    n, field_name, "invalid_amount",
                    AGGREGATE_SEVERITY["invalid_amount"],
                    f"{field_name} is negative.", _obs(value),
                ))
    return report


def validate_work_level_rows(
    normalized_rows: list[dict[str, Any]],
) -> ValidationReport:
    """Work-level validations (§26). Runs ONLY for WORK_LEVEL datasets."""
    report = ValidationReport(len(normalized_rows))
    seen_work_ids: dict[str, int] = {}

    for row in normalized_rows:
        n = row["source_row_number"]

        for field_name in ("work_id", "state", "district", "description"):
            if not row.get(field_name):
                report.add(Issue(
                    n, field_name, f"missing_{field_name}",
                    WORK_LEVEL_SEVERITY[f"missing_{field_name}"],
                    f"Missing {field_name.replace('_', ' ')}.", _obs(row.get(field_name)),
                ))

        work_id = row.get("work_id")
        if work_id:
            first = seen_work_ids.get(work_id)
            if first is not None:
                report.add(Issue(
                    n, "work_id", "duplicate_work_id",
                    WORK_LEVEL_SEVERITY["duplicate_work_id"],
                    f"Work ID {work_id} appears more than once (first seen in row {first}).",
                    _obs(work_id),
                ))
            else:
                seen_work_ids[work_id] = n

        for field_name in ("sanctioned_amount", "expenditure", "estimated_cost"):
            value = row.get(field_name)
            if value is not None and value < 0:
                report.add(Issue(
                    n, field_name, "negative_amount",
                    WORK_LEVEL_SEVERITY["negative_amount"],
                    f"{field_name.replace('_', ' ')} is negative.", _obs(value),
                ))

        sanctioned = row.get("sanctioned_amount")
        if sanctioned is None:
            report.add(Issue(
                n, "sanctioned_amount", "missing_sanctioned_amount",
                WORK_LEVEL_SEVERITY["missing_sanctioned_amount"],
                "Missing sanctioned amount.", _obs(row.get("_raw_sanctioned")),
            ))
        elif sanctioned <= 0:
            report.add(Issue(
                n, "sanctioned_amount", "invalid_numeric",
                WORK_LEVEL_SEVERITY["invalid_numeric"],
                "Sanctioned amount must be positive.", _obs(sanctioned),
            ))

        expenditure = row.get("expenditure")
        if expenditure is not None and sanctioned is not None and sanctioned > 0 \
                and expenditure > sanctioned:
            report.add(Issue(
                n, "expenditure", "expenditure_above_sanctioned",
                WORK_LEVEL_SEVERITY["expenditure_above_sanctioned"],
                "Expenditure exceeds sanctioned amount — data inconsistency.",
                _obs(expenditure),
            ))

        for field_name in ("physical_progress", "financial_progress"):
            value = row.get(field_name)
            if value is not None and not (Decimal(0) <= value <= Decimal(100)):
                report.add(Issue(
                    n, field_name, "progress_out_of_range",
                    WORK_LEVEL_SEVERITY["progress_out_of_range"],
                    f"{field_name.replace('_', ' ').capitalize()} is outside 0–100.",
                    _obs(value),
                ))

        sanction_date = row.get("sanction_date")
        completion_date = row.get("completion_date")
        if sanction_date and completion_date and completion_date < sanction_date:
            report.add(Issue(
                n, "completion_date", "invalid_date_order",
                WORK_LEVEL_SEVERITY["invalid_date_order"],
                f"Completion date {completion_date} precedes sanction date "
                f"{sanction_date}.", _obs(completion_date),
            ))

        lat, lon = row.get("latitude"), row.get("longitude")
        if lat is not None and not (-90 <= lat <= 90):
            report.add(Issue(
                n, "latitude", "invalid_coordinates",
                WORK_LEVEL_SEVERITY["invalid_coordinates"],
                f"Latitude {lat} is outside ±90.", _obs(lat),
            ))
        if lon is not None and not (-180 <= lon <= 180):
            report.add(Issue(
                n, "longitude", "invalid_coordinates",
                WORK_LEVEL_SEVERITY["invalid_coordinates"],
                f"Longitude {lon} is outside ±180.", _obs(lon),
            ))

    return report


def _obs(value: Any) -> str | None:
    """Stable text form of an observed value for the issue table."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def normalize_mp_allocation_row(
    row: dict[str, Any], column_map: dict[str, str], row_number: int
) -> dict[str, Any]:
    """Map + normalize one MP allocation row (§15, §18, §20, §21)."""
    from app.services.ingestion.normalizers import (
        normalize_decimal, normalize_int, normalize_text,
    )

    def source_value(canonical: str) -> Any:
        for header, target in column_map.items():
            if target == canonical:
                return row.get(header)
        return None

    out: dict[str, Any] = {"source_row_number": row_number}
    out["serial_number"] = normalize_int(source_value("serial_number"))
    out["_raw_serial"] = source_value("serial_number")
    out["state"] = normalize_text(source_value("state"))
    out["mp_name"] = normalize_text(source_value("mp_name"))
    out["constituency"] = normalize_text(source_value("constituency"))
    out["elected_nominated"] = normalize_text(source_value("elected_nominated"))
    amount, unit = normalize_monetary(source_value("allocated_amount"))
    out["allocated_amount"] = amount
    out["amount_unit"] = unit
    out["_raw_amount"] = source_value("allocated_amount")
    return out


def normalize_aggregate_row(
    row: dict[str, Any], column_map: dict[str, str], row_number: int
) -> dict[str, Any]:
    """Map + normalize one scheme-aggregate row (§16, §37)."""
    from app.services.ingestion.normalizers import normalize_date, normalize_text

    def source_value(canonical: str) -> Any:
        for header, target in column_map.items():
            if target == canonical:
                return row.get(header)
        return None

    out: dict[str, Any] = {"source_row_number": row_number}
    out["house"] = normalize_text(source_value("house"))
    monetary_fields = (
        "allocated_limit", "amount_consented_for_calamity",
        "expenditure_completed_and_ongoing",
    )
    unit = "RUPEE"
    for canonical in monetary_fields:
        value, value_unit = normalize_monetary(source_value(canonical))
        out[canonical] = value
        if value is not None and value_unit != "RUPEE":
            unit = value_unit
    out["monetary_unit"] = unit
    for canonical in ("works_recommended", "works_sanctioned", "works_completed"):
        from app.services.ingestion.normalizers import normalize_int
        out[canonical] = normalize_int(source_value(canonical))
    out["as_of_date"] = normalize_date(source_value("as_of_date"))
    return out


def normalize_work_level_row(
    row: dict[str, Any], column_map: dict[str, str], row_number: int
) -> dict[str, Any]:
    """Map + normalize one work-level row (§17). Only provided fields fill in."""
    from decimal import InvalidOperation

    from app.services.ingestion.normalizers import (
        normalize_date, normalize_decimal, normalize_int, normalize_percentage,
        normalize_text,
    )

    def source_value(canonical: str) -> Any:
        for header, target in column_map.items():
            if target == canonical:
                return row.get(header)
        return None

    out: dict[str, Any] = {"source_row_number": row_number}
    out["work_id"] = normalize_text(source_value("work_id"))
    out["mp_name"] = normalize_text(source_value("mp_name"))
    out["constituency"] = normalize_text(source_value("constituency"))
    out["state"] = normalize_text(source_value("state"))
    out["district"] = normalize_text(source_value("district"))
    out["description"] = normalize_text(source_value("description"))
    out["implementing_agency"] = normalize_text(source_value("implementing_agency"))

    out["estimated_cost"], est_unit = normalize_monetary(source_value("estimated_cost"))
    out["sanctioned_amount"], san_unit = normalize_monetary(source_value("sanctioned_amount"))
    out["expenditure"], exp_unit = normalize_monetary(source_value("expenditure"))
    out["monetary_unit"] = san_unit if san_unit != "RUPEE" else (
        exp_unit if exp_unit != "RUPEE" else est_unit
    )

    out["physical_progress"] = normalize_percentage(source_value("physical_progress"))
    out["financial_progress"] = normalize_percentage(source_value("financial_progress"))
    out["sanction_date"] = normalize_date(source_value("sanction_date"))
    out["completion_date"] = normalize_date(source_value("completion_date"))
    out["start_date"] = normalize_date(source_value("start_date"))
    out["category"] = normalize_text(source_value("category"))
    out["sector"] = normalize_text(source_value("sector"))
    out["status"] = normalize_text(source_value("status"))
    out["contractor_name"] = normalize_text(source_value("contractor_name"))
    out["expected_duration_days"] = normalize_int(source_value("expected_duration_days"))
    out["location_text"] = normalize_text(source_value("location_text"))

    lat_raw = source_value("latitude")
    lon_raw = source_value("longitude")
    try:
        out["latitude"] = None if lat_raw in (None, "") else Decimal(str(lat_raw).strip())
    except InvalidOperation:
        out["latitude"] = None
    try:
        out["longitude"] = None if lon_raw in (None, "") else Decimal(str(lon_raw).strip())
    except InvalidOperation:
        out["longitude"] = None
    return out
