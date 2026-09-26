"""Pydantic schemas — the typed API boundary (TR-10).

Frontend contracts are defined here; ORM models never leak directly
into responses. Every response carries meta with provenance.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ResolutionType


class Meta(BaseModel):
    """Standard response metadata (AGENTS_RULES.md §8)."""

    dataset_version: str | None = None
    generated_at: str | None = None
    is_synthetic: bool | None = None


class Envelope(BaseModel):
    """Predictable response wrapper: data + meta."""

    data: Any
    meta: Meta = Field(default_factory=Meta)


class OfficerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str
    district: str | None = None
    is_active: bool


class EvidenceOut(BaseModel):
    """One evidence row inside an evidence ledger."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    field_name: str
    field_value: str
    reference_label: str | None = None
    reference_value: str | None = None
    calculation: str | None = None


class SignalOut(BaseModel):
    """Detected signal with its evidence and recommended verification."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    signal_type: str
    severity: str
    triggered: bool
    title: str
    explanation: str
    observed_value: dict | None = None
    reference_value: dict | None = None
    difference_value: dict | None = None
    source_type: str
    source_version: str
    created_at: datetime
    evidence: list[EvidenceOut] = []
    recommended_action: str | None = None


class MetricsOut(BaseModel):
    """Derived metrics — clearly a separate layer from source facts."""

    cost_deviation_pct: float | None = None
    peer_median_cost: float | None = None
    peer_p75_cost: float | None = None
    peer_percentile: float | None = None
    financial_physical_gap: float | None = None
    expenditure_ratio: float | None = None
    elapsed_days: int | None = None
    expected_duration_days: int | None = None
    delay_days: int | None = None
    agency_share_pct: float | None = None
    ml_anomaly_score: float | None = None
    duplicate_score: float | None = None
    calculated_at: datetime | None = None
    calculation_version: str | None = None


class PeerOut(BaseModel):
    """Peer benchmark context for one project."""

    peer_group_name: str
    peer_count: int
    median_cost: float | None = None
    p75_cost: float | None = None
    percentile: float | None = None


class RelatedProjectOut(BaseModel):
    """Duplicate-candidate link with component similarities visible."""

    related_project_id: str
    work_id: str
    project_name: str
    district: str
    text_similarity: float | None = None
    location_distance_m: float | None = None
    cost_similarity: float | None = None
    category_match: bool | None = None
    time_overlap: bool | None = None
    vendor_match: bool | None = None
    contextual_confidence: str | None = None
    combined_score: float


class ProjectSummary(BaseModel):
    """Compact project record for queue/dashboard lists."""

    id: str
    work_id: str
    description: str
    district: str
    state: str
    category: str | None = None
    status: str
    sanctioned_cost: float
    latitude: float | None = None
    longitude: float | None = None
    priority: PriorityOut | None = None
    primary_signals: list[str] = []
    case_status: str | None = None


class PriorityOut(BaseModel):
    """Fused investigation priority with its decomposition."""

    level: str
    score: float
    signal_count: int
    reasons: list[str] = []


class ProjectDetail(ProjectSummary):
    """Full project intelligence payload (APP_FLOW.md §4)."""

    mp_name: str | None = None
    constituency: str | None = None
    location_text: str | None = None
    sector: str | None = None
    estimated_cost: float
    expenditure: float | None = None
    financial_progress: float
    physical_progress: float
    sanction_date: date | None = None
    start_date: date | None = None
    completion_date: date | None = None
    implementing_agency: str | None = None
    contractor_name: str | None = None
    expected_duration_days: int | None = None
    metrics: MetricsOut | None = None
    signals: list[SignalOut] = []
    peers: list[PeerOut] = []
    related: list[RelatedProjectOut] = []
    why_flagged: str | None = None
    dataset_version: str | None = None
    dataset_is_synthetic: bool | None = None


class ProjectListResponse(Envelope):
    data: list[ProjectSummary]


class QueueFilters(BaseModel):
    """Server-side queue filters (TRD: filtering must be server-side)."""

    priority: str | None = None
    state: str | None = None
    district: str | None = None
    category: str | None = None
    signal_type: str | None = None
    case_status: str | None = None
    search: str | None = None
    sort: str = "priority"
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source_type: str
    source_label: str
    version: str
    is_synthetic: bool
    ingested_at: datetime
    row_count: int
    quality_status: str
    quality_summary: dict | None = None


class QualityIssue(BaseModel):
    """One data-quality/compliance exception, with the affected field."""

    work_id: str
    project_id: str
    rule: str
    severity: str
    field: str | None = None
    detail: str


class QualityReport(BaseModel):
    dataset_id: str
    quality_status: str
    total_rows: int
    issues: list[QualityIssue] = []
    summary: dict = {}


class DashboardSummary(BaseModel):
    """Command Center payload (PRD R9)."""

    total_works: int
    total_value: float
    high_priority_count: int
    critical_count: int
    delayed_count: int
    duplicate_candidate_count: int
    quality_exception_count: int
    case_open_count: int
    risk_distribution: dict[str, int]
    signal_distribution: dict[str, int]
    districts: list[dict] = []
    queue_preview: list[ProjectSummary] = []
    dataset: DatasetOut | None = None
    map_points: list[ProjectSummary] = []


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


class CaseCreate(BaseModel):
    project_id: str
    assigned_officer_id: str | None = None
    note: str | None = None


class CaseUpdate(BaseModel):
    status: str | None = None
    assigned_officer_id: str | None = None
    resolution_type: ResolutionType | None = None
    resolution_summary: str | None = None


class CaseNoteCreate(BaseModel):
    author_id: str
    body: str = Field(min_length=1)


class CaseEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    actor_id: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    metadata_json: dict | None = Field(default=None, alias="metadata_json")
    created_at: datetime


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_number: str
    project_id: str
    priority: str
    status: str
    assigned_officer_id: str | None = None
    opened_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    resolution_type: str | None = None
    resolution_summary: str | None = None
    project: ProjectSummary | None = None
    assigned_officer: OfficerOut | None = None
    events: list[CaseEventOut] = []
    notes: list["CaseNoteOut"] = []
    evidence: list["CaseEvidenceOut"] = []


class CaseNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    author_id: str
    body: str
    created_at: datetime
    updated_at: datetime
    author: OfficerOut | None = None


class CaseEvidenceCreate(BaseModel):
    signal_id: str | None = None
    description: str = Field(min_length=1)
    evidence_type: str = "SIGNAL"


class CaseEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    signal_id: str | None = None
    description: str
    evidence_type: str
    file_reference: str | None = None
    created_at: datetime


class FeedbackCreate(BaseModel):
    """Officer feedback classification (APP_FLOW.md §9)."""

    resolution_type: ResolutionType
    officer_id: str
    summary: str | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    report_number: str
    format: str
    file_reference: str
    generated_by: str
    generated_at: datetime
    report_version: str


class DetectionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    model_version: str
    ruleset_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    summary: dict | None = None
    error_message: str | None = None


class DetectionRunRequest(BaseModel):
    dataset_id: str | None = None  # None = latest dataset


CaseOut.model_rebuild()
