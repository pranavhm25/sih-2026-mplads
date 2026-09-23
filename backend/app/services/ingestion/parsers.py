"""File parsing for dataset imports (Prompt-3 §10).

Extracts headers + raw rows from CSV and XLSX uploads. Parsing is separate
from mapping/normalization so each step stays independently testable, and
malformed files fail with explicit, user-safe errors.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field

from app.core.errors import DrishtiError

logger = logging.getLogger("drishti.ingestion")

SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls")


class FileParseError(DrishtiError):
    """Raised when an uploaded file cannot be parsed (Prompt-3 §46)."""

    def __init__(self, message: str, code: str = "INVALID_FILE"):
        super().__init__(message=message, status_code=400, code=code)


@dataclass
class ParsedFile:
    headers: list[str]
    rows: list[dict[str, object]]      # header-as-shown → cell value
    file_kind: str                     # CSV | XLSX
    issues: list[str] = field(default_factory=list)  # non-fatal parse notes

    @property
    def row_count(self) -> int:
        return len(self.rows)


def parse_file(raw: bytes, filename: str) -> ParsedFile:
    """Parse an uploaded CSV/XLSX into headers + rows.

    Raises FileParseError for empty, malformed or unsupported files so the
    API returns a structured error rather than a stack trace.
    """
    name = (filename or "").lower()
    if not name:
        raise FileParseError("The uploaded file has no filename.")
    if not name.endswith(SUPPORTED_EXTENSIONS):
        raise FileParseError(
            "Unsupported file type. Accepted formats: CSV, XLSX.",
            code="UNSUPPORTED_FILE",
        )

    if not raw or not raw.strip():
        raise FileParseError("The uploaded file is empty.", code="EMPTY_FILE")

    if name.endswith(".csv"):
        return _parse_csv(raw)
    return _parse_xlsx(raw)


def _parse_csv(raw: bytes) -> ParsedFile:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FileParseError(
            "The CSV file is not valid UTF-8 text.", code="INVALID_FILE"
        ) from exc

    reader = csv.reader(io.StringIO(text))
    try:
        first = next(reader, None)
    except csv.Error as exc:
        raise FileParseError("The CSV file is malformed.", code="INVALID_FILE") from exc
    if not first or all(not c.strip() for c in first):
        raise FileParseError("The CSV file has no header row.", code="INVALID_FILE")

    headers = [h.strip() for h in first]
    rows: list[dict[str, object]] = []
    issues: list[str] = []
    for lineno, record in enumerate(reader, start=2):  # data starts at line 2
        if all(not str(c).strip() for c in record):
            continue  # skip fully blank lines
        if len(record) < len(headers):
            issues.append(f"Row {lineno} has fewer cells than the header; padded empty.")
            record = list(record) + [""] * (len(headers) - len(record))
        elif len(record) > len(headers):
            issues.append(f"Row {lineno} has more cells than the header; extras ignored.")
            record = record[: len(headers)]
        rows.append(dict(zip(headers, (c for c in record))))
    if not rows:
        raise FileParseError("The CSV file contains no data rows.", code="EMPTY_FILE")
    return ParsedFile(headers=headers, rows=rows, file_kind="CSV", issues=issues)


def _parse_xlsx(raw: bytes) -> ParsedFile:
    try:
        import openpyxl  # local import: keeps CSV-only installs light
    except ImportError as exc:  # pragma: no cover
        raise FileParseError(
            "XLSX support is unavailable on the server.", code="INVALID_FILE"
        ) from exc
    try:
        workbook = openpyxl.load_workbook(
            io.BytesIO(raw), read_only=True, data_only=True
        )
    except Exception as exc:  # openpyxl raises assorted internal errors
        raise FileParseError(
            "The workbook could not be read. Is it a valid XLSX file?",
            code="INVALID_FILE",
        ) from exc

    sheet = workbook.active
    if sheet is None:
        workbook.close()
        raise FileParseError("The workbook has no sheets.", code="INVALID_FILE")

    sheet_rows = sheet.iter_rows(values_only=True)
    first = next(sheet_rows, None)
    if first is None or all(c is None or str(c).strip() == "" for c in first):
        workbook.close()
        raise FileParseError("The worksheet has no header row.", code="INVALID_FILE")

    headers: list[str] = []
    for idx, cell in enumerate(first):
        label = "" if cell is None else str(cell).strip()
        headers.append(label if label else f"column_{idx + 1}")
    width = len(headers)

    rows: list[dict[str, object]] = []
    for record in sheet_rows:
        if all(c is None or str(c).strip() == "" for c in record):
            continue
        cells = list(record)[:width]
        cells += [None] * (width - len(cells))
        rows.append(dict(zip(headers, cells)))
    workbook.close()
    if not rows:
        raise FileParseError("The worksheet contains no data rows.", code="EMPTY_FILE")
    return ParsedFile(headers=headers, rows=rows, file_kind="XLSX")
