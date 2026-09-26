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
    COMPLIANCE = "COMPLIANCE"


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
    CLOSED = "CLOSED"


class ResolutionType(StrEnum):
    CONFIRMED_CONCERN = "CONFIRMED_CONCERN"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    # Human investigation found no substantiated irregularity. Distinct from
    # FALSE_POSITIVE: FALSE_POSITIVE means the automated flag itself was
    # wrong (dedup/quality artifact); NOT_SUBSTANTIATED means the flag was
    # plausible but human verification did not substantiate the concern.
    NOT_SUBSTANTIATED = "NOT_SUBSTANTIATED"


# Structured reason categories a NOT_SUBSTANTIATED closure must choose from
# (plus a free-text explanation). Lightweight by design: one pick + one
# sentence — not a burden on the investigator.
class ResolutionReason(StrEnum):
    DOCUMENTATION_PROVIDED = "DOCUMENTATION_PROVIDED"
    LEGITIMATE_DELAY = "LEGITIMATE_DELAY"
    DATA_QUALITY_ISSUE = "DATA_QUALITY_ISSUE"
    FALSE_DUPLICATE_CANDIDATE = "FALSE_DUPLICATE_CANDIDATE"
    APPROVED_VARIATION = "APPROVED_VARIATION"
    CONTEXTUAL_EXCEPTION = "CONTEXTUAL_EXCEPTION"
    OTHER = "OTHER"


class OfficerRole(StrEnum):
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"
    SUPERVISOR = "SUPERVISOR"


class StakeholderRole(StrEnum):
    """The four decision-maker roles named in PS 26102 (backlog #4).

    Each role gets a scoped, role-appropriate view of the SAME data:
    no role sees another's slice unless scope permits.
    """

    MP = "MP"
    DISTRICT_AUTHORITY = "DISTRICT_AUTHORITY"
    STATE_NODAL = "STATE_NODAL"
    MINISTRY = "MINISTRY"
    ADMIN = "ADMIN"  # platform operator, full scope


# ---------------------------------------------------------------------------
# Backlog #1 — Categorical compliance rule pack.
# MPLADS violations documented by CAG performance audits are categorical,
# not statistical. Rules match work descriptions against guideline reference
# data. Language is deliberately cautious: "compliance indicator", never
# "fraud" (PS guardrail + Prompt-3 §50).
# ---------------------------------------------------------------------------
COMPLIANCE_GUIDELINE_CITATION = (
    "MPLADS Guidelines (2023 revision); CAG Performance Audit of MPLADS — "
    "prohibited/expenditure categories"
)

# Keyword patterns → prohibited/unrestricted category (matched on normalized
# lowercase work description). Each entry cites the guideline basis.
PROHIBITED_CATEGORY_PATTERNS: list[dict] = [
    {"code": "RELIGIOUS_STRUCTURE", "label": "Religious structure",
     "patterns": ["temple", "mandir", "mosque", "masjid", "church", "gurudwara",
                  "gurdwara", "shrine", "prayer hall", "dargah"],
     "guideline": "Guidelines para 2.1: works for religious purposes are prohibited"},
    {"code": "MEMORIAL_STATUE", "label": "Memorial / statue",
     "patterns": ["memorial", "statue", "pratima", "bust", "samadhi", "smarak"],
     "guideline": "Guidelines para 2.1: memorials/statues prohibited"},
    {"code": "PRIVATE_PROPERTY", "label": "Private property benefit",
     "patterns": ["private school", "private trust", "private society",
                  "private hospital", "personal residence"],
     "guideline": "Guidelines para 2.2: works on private property prohibited"},
    {"code": "REPAIR_UNPERMITTED", "label": "Repair/maintenance beyond limits",
     "patterns": ["repair of road", "repair work", "annual repair",
                  "maintenance of building", "repainting"],
     "guideline": "Guidelines: repair/maintenance spend restricted to specified assets/limits"},
    {"code": "OFFICE_BUILDING", "label": "Office building",
     "patterns": ["office building", "office complex", "secretariat building",
                  "legislative assembly building"],
     "guideline": "Guidelines para 2.1: government office buildings prohibited"},
]

# Payee-type risk: implementing agency names that look like entities outside
# the permitted lists (societies/trusts need prior nodal approval).
INELIGIBLE_PAYEE_PATTERNS: list[dict] = [
    {"code": "UNAPPROVED_TRUST", "label": "Trust/society implementing agency",
     "patterns": ["trust", "society", "foundation", "seva samiti"],
     "guideline": "Guidelines: trust/society agencies require State Nodal approval"},
]

# Split-payment heuristic: repeated payments on one work within a short window
# that each stay just below a review threshold (payment data only; backlog #5).
SPLIT_PAYMENT_WINDOW_DAYS = 14
SPLIT_PAYMENT_MIN_COUNT = 3

# Severity mapping for compliance signals.
COMPLIANCE_SEVERITY = {
    "RELIGIOUS_STRUCTURE": Severity.CRITICAL,
    "MEMORIAL_STATUE": Severity.CRITICAL,
    "PRIVATE_PROPERTY": Severity.HIGH,
    "OFFICE_BUILDING": Severity.HIGH,
    "REPAIR_UNPERMITTED": Severity.MEDIUM,
    "UNAPPROVED_TRUST": Severity.MEDIUM,
}

# Fusion weight for the compliance signal (sits beside SIGNAL_WEIGHTS).
COMPLIANCE_SIGNAL_WEIGHT = 3.5

# ---------------------------------------------------------------------------
# Backlog #6 — Alert digest thresholds (per-stakeholder early warning).
# ---------------------------------------------------------------------------
ALERT_DIGEST_CRITICAL_FLOOR = "CRITICAL"  # roles below Ministry get critical+
ALERT_DIGEST_HIGH_FLOOR = "HIGH"          # Ministry sees high+; both see critical

# Backlog #8 — benchmark scale (full 18th-LS recommended volume, rounded).
BENCHMARK_ROW_COUNT = 110_000
BENCHMARK_SEED = 26102


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


# Case lifecycle (PRD R12):
#
#   OPEN → UNDER_REVIEW → FIELD_VERIFICATION ─┬→ RESOLVED (concluded w/ record)
#                                             │    └→ ESCALATED
#                                             └→ CLOSED (not substantiated)
#
# Two human outcomes exist at the end of verification:
# - SUBSTANTIATED path: the concern held up → RESOLVED with a confirmed
#   classification, optionally ESCALATED to higher authority.
# - NOT SUBSTANTIATED path: the available evidence did not substantiate the
#   flagged concern → CLOSED. This is not a fraud/innocence verdict and does
#   not imply the AI flag was wrong — see ResolutionType.NOT_SUBSTANTIATED.
#
# Closed/escalated cases can be reopened by supervisors (UNDER_REVIEW).
CASE_TRANSITIONS: dict[str, set[str]] = {
    CaseStatus.OPEN: {CaseStatus.UNDER_REVIEW, CaseStatus.FIELD_VERIFICATION},
    CaseStatus.UNDER_REVIEW: {
        CaseStatus.FIELD_VERIFICATION, CaseStatus.RESOLVED, CaseStatus.ESCALATED,
    },
    CaseStatus.FIELD_VERIFICATION: {
        CaseStatus.UNDER_REVIEW, CaseStatus.RESOLVED, CaseStatus.ESCALATED,
        CaseStatus.CLOSED,
    },
    CaseStatus.RESOLVED: {CaseStatus.UNDER_REVIEW, CaseStatus.ESCALATED},
    CaseStatus.CLOSED: {CaseStatus.UNDER_REVIEW},  # supervisor reopen path
    CaseStatus.ESCALATED: {CaseStatus.UNDER_REVIEW},  # return from escalation
}


# Recommended verification actions per signal type (Rule → Evidence → Action).
RECOMMENDED_VERIFICATION: dict[str, str] = {
    SignalType.COMPLIANCE: (
        "Verify the work against the cited MPLADS guideline provision and "
        "confirm the category/agency with the District Authority before any "
        "conclusion."
    ),
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
    SignalType.COMPLIANCE: COMPLIANCE_SIGNAL_WEIGHT,
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

# ---------------------------------------------------------------------------
# Duplicate-candidate contextual validation ("similarity ≠ duplication").
#
# TF-IDF/cosine is a candidate GENERATOR: it measures linguistic similarity,
# which government boilerplate produces constantly. A record only becomes a
# STRONG duplicate candidate when independent contextual evidence agrees:
# geospatial proximity and/or shared implementing agency. Each threshold is
# documented with the reason it exists. See docs/TRD.md TR-07 and
# docs/RULES.md §6.
# ---------------------------------------------------------------------------

# Geospatial gate: MPLADS works are local-area capital works; two genuinely
# distinct sanctioned works serving the same purpose are rarely sited within
# a few metres. Pairs closer than this are candidate matches; the value sits
# well below the 50 m full-proximity band in combined_score so the gate is
# not arbitrary relative to the scorer.
DUPLICATE_GEO_STRONG_M = 50.0
# Beyond this distance a pair cannot be a strong candidate even with
# identical text — the works are in different places. (Taper above this
# affects only scoring, not classification.)
DUPLICATE_GEO_MAX_M = 2000.0

# Combined-score floor for the contextual band: pairs scoring in
# [trigger, high) carry a MEDIUM baseline; contextual agreement decides
# whether a strong band is reached. Kept = DUPLICATE_SCORE_HIGH so the
# legacy high band and the contextual band agree.
DUPLICATE_CONTEXTUAL_STRONG = 0.75

# Weights for the contextual confidence assessment (documented, transparent,
# no ML): geo evidence is the strongest independent signal, vendor agreement
# is corroborating, cost/category/time already live in combined_score.
DUPLICATE_CONF_WEIGHT_GEO = 0.55
DUPLICATE_CONF_WEIGHT_VENDOR = 0.30
DUPLICATE_CONF_WEIGHT_CONTEXT = 0.15  # cost/category/time agreement

# Vendor-name normalization for overlap checks: strip legal-form noise and
# punctuation so "Sri Balaji Constructions" and "Sri Balaji Constr." match
# without fuzzy guessing (deterministic token set overlap).
DUPLICATE_VENDOR_STOPWORDS = (
    "sri", "smt", "private", "limited", "ltd", "pvt", "and", "the", "co",
    "company", "enterprises", "contractors", "constructions", "builders",
    "works", "agency", "division", "department", "engineering",
)
DUPLICATE_VENDOR_MIN_TOKEN_OVERLAP = 0.5  # shared core tokens / smaller set

# Fusion penalty when a duplicate signal is contextually weak: textual
# similarity alone must not drive an unjustified priority. Applied as a
# multiplier on the standard DUPLICATE weight (see SPLIT_PAYMENT style docs
# in fusion.py; penalty logic documented in TRD TR-07).
DUPLICATE_WEAK_CONFIDENCE_WEIGHT = 0.6
ML_ANOMALY_TRIGGER = -0.05  # Isolation Forest decision_function; below = unusual
ML_ANOMALY_HIGH = -0.15
AGENCY_SHARE_TRIGGER_PCT = 40.0  # % of district sanctioned value held by a single agency
AGENCY_SHARE_HIGH_PCT = 60.0
AGENCY_MIN_DISTRICT_WORKS = 4  # Minimum works in district to evaluate concentration
AGENCY_MIN_WORKS = 2  # Minimum works held by agency in district to trigger

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

