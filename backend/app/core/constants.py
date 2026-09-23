"""Domain constants shared across the backend.

Keeping these in one place avoids magic strings scattered through the
detection services and API schemas.
"""
from enum import StrEnum


class SignalType(StrEnum):
    """Categories of investigation signals."""

    DATA_QUALITY = "DATA_QUALITY"
    COST_ANOMALY = "COST_ANOMALY"
    FIN_PHYS_GAP = "FIN_PHYS_GAP"
    DELAY = "DELAY"
    DUPLICATE = "DUPLICATE"
    ML_ANOMALY = "ML_ANOMALY"
    AGENCY_CONCENTRATION = "AGENCY_CONCENTRATION"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceType(StrEnum):
    """Provenance of a signal (BACKEND_SCHEMA.md §6)."""

    RULE = "RULE"
    ML = "ML"
    NLP = "NLP"
    BENCHMARK = "BENCHMARK"
    DATA_QUALITY = "DATA_QUALITY"


class Priority(StrEnum):
    """Fused investigation priority (evidence-based, not a verdict)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    FIELD_VERIFICATION = "FIELD_VERIFICATION"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class ResolutionType(StrEnum):
    CONFIRMED_CONCERN = "CONFIRMED_CONCERN"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"


class OfficerRole(StrEnum):
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"
    SUPERVISOR = "SUPERVISOR"


class DatasetStatus(StrEnum):
    PENDING = "PENDING"
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"


class DatasetType(StrEnum):
    """What a dataset contains (Prompt-3 §7). MP allocation rows are NOT
    works; keeping types explicit keeps records type-safe end to end."""

    MP_ALLOCATION = "MP_ALLOCATION"
    SCHEME_AGGREGATE = "SCHEME_AGGREGATE"
    WORK_LEVEL = "WORK_LEVEL"
    OTHER_OFFICIAL_EXPORT = "OTHER_OFFICIAL_EXPORT"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class DatasetSourceType(StrEnum):
    """Where a dataset came from (Prompt-3 §6 source hierarchy).

    OFFICIAL_* datasets are real MPLADS data; SYNTHETIC_FIXTURE is a
    development-only fixture that must never be presented as official.
    """

    OFFICIAL_PUBLIC_DASHBOARD = "OFFICIAL_PUBLIC_DASHBOARD"
    OFFICIAL_FILE_UPLOAD = "OFFICIAL_FILE_UPLOAD"
    OFFICIAL_DATASET_API = "OFFICIAL_DATASET_API"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class IssueSeverity(StrEnum):
    """Severity of an ingestion validation issue (Prompt-3 §23)."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Case lifecycle: OPEN → UNDER_REVIEW → FIELD_VERIFICATION → RESOLVED | ESCALATED
CASE_TRANSITIONS: dict[str, set[str]] = {
    CaseStatus.OPEN: {CaseStatus.UNDER_REVIEW, CaseStatus.FIELD_VERIFICATION},
    CaseStatus.UNDER_REVIEW: {CaseStatus.FIELD_VERIFICATION, CaseStatus.RESOLVED, CaseStatus.ESCALATED},
    CaseStatus.FIELD_VERIFICATION: {CaseStatus.UNDER_REVIEW, CaseStatus.RESOLVED, CaseStatus.ESCALATED},
    CaseStatus.RESOLVED: {CaseStatus.UNDER_REVIEW},  # reopen path
    CaseStatus.ESCALATED: {CaseStatus.UNDER_REVIEW},  # return from escalation
}


# Recommended verification actions per signal type (Rule → Evidence → Action).
RECOMMENDED_VERIFICATION: dict[str, str] = {
    SignalType.FIN_PHYS_GAP: (
        "Verify physical execution on site and reconcile payment milestones "
        "against certified progress."
    ),
    SignalType.COST_ANOMALY: (
        "Compare the sanctioned estimate with the work order and peer works of "
        "the same district/category; verify item-wise rate justification."
    ),
    SignalType.DELAY: (
        "Verify current site status and review extension/time-bound completion "
        "documentation."
    ),
    SignalType.DUPLICATE: (
        "Verify the physical asset location and cross-check related work records "
        "to confirm whether both works exist independently."
    ),
    SignalType.ML_ANOMALY: (
        "Review the statistically unusual feature profile against source records "
        "and confirm whether the pattern has an operational explanation."
    ),
    SignalType.AGENCY_CONCENTRATION: (
        "Review the implementing agency's full work portfolio for shared "
        "patterns across flagged works."
    ),
    SignalType.DATA_QUALITY: (
        "Correct the source record and re-validate the dataset entry."
    ),
}


# Weight of each signal type in the fusion priority calculation.
# Independent signals reinforce each other; weights are configurable inputs,
# not verdicts. Severity multiplies the contribution.
SIGNAL_WEIGHTS: dict[str, float] = {
    SignalType.FIN_PHYS_GAP: 3.0,
    SignalType.COST_ANOMALY: 3.0,
    SignalType.DUPLICATE: 2.5,
    SignalType.DELAY: 2.0,
    SignalType.ML_ANOMALY: 1.5,
    SignalType.AGENCY_CONCENTRATION: 1.5,
    SignalType.DATA_QUALITY: 1.0,
}

SEVERITY_MULTIPLIER: dict[str, float] = {
    Severity.LOW: 0.5,
    Severity.MEDIUM: 1.0,
    Severity.HIGH: 1.5,
    Severity.CRITICAL: 2.0,
}

# Thresholds (documented, not magic numbers).
FIN_PHYS_GAP_TRIGGER_PP = 25  # percentage points
FIN_PHYS_GAP_HIGH_PP = 40
COST_DEVIATION_TRIGGER_PCT = 40  # % above peer median
COST_DEVIATION_HIGH_PCT = 60
DELAY_TRIGGER_DAYS = 90
DELAY_HIGH_DAYS = 180
DUPLICATE_SCORE_TRIGGER = 0.60
DUPLICATE_SCORE_HIGH = 0.75
ML_ANOMALY_TRIGGER = -0.05  # Isolation Forest decision_function; below = unusual
ML_ANOMALY_HIGH = -0.15

# ---------------------------------------------------------------------------
# Data-quality scale (Prompt-3 §28/§29): deterministic, documented states —
# never an opaque score. error_rate = error rows / total rows, warn_rate likewise.
# ---------------------------------------------------------------------------
QUALITY_ERROR_RATE_ACCEPTABLE = 0.02   # <= 2% errors → GOOD/ACCEPTABLE
QUALITY_ERROR_RATE_DEGRADED = 0.10     # <= 10% errors → ACCEPTABLE/DEGRADED
QUALITY_WARN_RATE_DEGRADED = 0.15      # heavy warnings degrade GOOD → ACCEPTABLE

# Uploaded files larger than this are rejected outright (bytes).
MAX_IMPORT_FILE_BYTES = 50 * 1024 * 1024

# MP allocation amounts are raw rupees in official exports; amounts below
# this are implausible for an MPLADS annual entitlement and flag a WARNING.
MP_ALLOCATION_MIN_PLAUSIBLE_INR = 100000  # ₹1 lakh
