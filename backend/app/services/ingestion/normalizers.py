"""Deterministic normalization for ingested values (Prompt-3 §18–22, §37).

Every transformation here is pure, explicit and unit-tested. Normalizers
never invent data: unparseable input maps to None, and the caller records a
validation issue. Monetary values keep their unit — a Crore figure is never
silently treated as rupees (Prompt-3 §37).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

# Values that mean "no data" in exports. Case-insensitive match after trim.
NULL_TOKENS: frozenset[str] = frozenset({
    "", "n/a", "na", "n.a.", "n.a", "-", "--", "—", "–", "null", "nil",
    "none", "empty", "#n/a", "#value!", "?",
})

# Multipliers for explicit unit conversion (§37).
_UNIT_LAKH = Decimal(100000)
_UNIT_CRORE = Decimal(10000000)

DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
    "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%Y-%m-%dT%H:%M:%S",
)


def is_null(value: Any) -> bool:
    """True for null-like values (§22). Never true for legitimate values like 0."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in NULL_TOKENS
    return False


def normalize_text(value: Any) -> str | None:
    """Trim, collapse repeated whitespace, map null-like values to None (§21/§22)."""
    if is_null(value):
        return None
    text = " ".join(str(value).split())
    return text or None


def normalize_int(value: Any) -> int | None:
    """Deterministic integer-count normalization (§20).

    'No. 109747' → 109747; '1,234' → 1234; unparseable → None.
    """
    if is_null(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value == int(value) else None
    text = str(value).strip()
    for prefix in ("No.", "no.", "No", "no"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.replace(",", "").replace("₹", "").strip()
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def normalize_decimal(value: Any) -> Decimal | None:
    """Numeric value without unit inference; unparseable → None."""
    if is_null(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).strip().replace(",", "").replace("₹", "").strip()
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def normalize_percentage(value: Any) -> Decimal | None:
    """Percentages to 0–100 (§19). '84%', '84', '84.0' all → 84.

    Values outside 0–100 are still returned (validation flags them);
    this function never clamps, so impossible source values stay visible.
    """
    if is_null(value):
        return None
    text = str(value).strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    num = normalize_decimal(text)
    return num


def normalize_monetary(value: Any) -> tuple[Decimal | None, str]:
    """Normalize a monetary cell, preserving its unit (§18/§37).

    Returns (value_in_unit, unit) where unit ∈ {RUPEE, LAKH, CRORE}.

    Examples:
        "₹ 4,324.08 Crore" → (4324.08, CRORE)
        "73421449"         → (73421449, RUPEE)
        "24.2L"            → (24.2, LAKH)
        "₹1,000"           → (1000, RUPEE)

    The unit is explicit: callers convert deterministically via
    `to_rupees()` only when the schema requires a canonical rupee value.
    """
    if is_null(value):
        return None, "RUPEE"
    if isinstance(value, bool):
        return None, "RUPEE"
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value)), "RUPEE"

    import re

    text = str(value).strip()
    upper = text.upper()

    # Unit detection: whole unit tokens (word-bounded), longest first.
    unit = "RUPEE"
    unit_match = re.search(r"(CRORES?|LAKHS?|CR|L)\b", upper)
    if unit_match:
        token = unit_match.group(1)
        unit = "CRORE" if token.startswith(("CRORE", "CR")) else "LAKH"

    # Numeric stem: drop the unit token and currency decorations, keep the
    # first number (commas are thousand separators, not chunk delimiters).
    stem = re.sub(r"(CRORES?|LAKHS?|CR|L)\b", " ", upper)
    stem = stem.replace("₹", " ").replace("RS.", " ").replace("RS", " ").replace("INR", " ")
    stem = stem.replace(",", "")
    stem = re.sub(r"[^0-9.\-]", " ", stem).strip()
    num: Decimal | None = None
    for chunk in stem.split():
        try:
            num = Decimal(chunk)
            break
        except InvalidOperation:
            continue
    return num, unit


def to_rupees(value: Decimal | None, unit: str) -> Decimal | None:
    """Deterministic unit conversion (§37). Every conversion is unit-tested."""
    if value is None:
        return None
    if unit == "RUPEE":
        return value
    if unit == "LAKH":
        return value * _UNIT_LAKH
    if unit == "CRORE":
        return value * _UNIT_CRORE
    return None





def normalize_date(value: Any) -> date | None:
    """Date normalization across common export formats; unparseable → None."""
    if is_null(value):
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
