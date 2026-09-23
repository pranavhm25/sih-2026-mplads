"""SQLAlchemy ORM models — Drishti backend.

Implements docs/BACKEND_SCHEMA.md. Layer separation is enforced by design:
source facts (projects), derived metrics (project_metrics), model output
(project_signal), and officer conclusions (cases/notes) live in separate
tables with explicit provenance.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    LargeBinary,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid4())


class Dataset(Base):
    """Ingestion/provenance metadata (schema §3, extended by Prompt 3 for
    dataset typing, file identity and quality reporting)."""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50), default="CSV")
    source_label: Mapped[str] = mapped_column(String(255), default="synthetic demo")
    version: Mapped[str] = mapped_column(String(50), default="v1")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    quality_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # --- Prompt-3 provenance extensions -------------------------------------
    dataset_type: Mapped[str] = mapped_column(String(40), default="WORK_LEVEL")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="dataset")
    mp_allocations: Mapped[list["MPAllocationRecord"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    aggregates: Mapped[list["SchemeAggregate"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    validation_issues: Mapped[list["ValidationIssue"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class Project(Base):
    """Canonical MPLADS work record (schema §4). Source facts only."""

    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_work_dataset", "work_id", "dataset_id"),
        Index("ix_projects_state_district", "state", "district"),
        Index("ix_projects_category", "category"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_latlng", "latitude", "longitude"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    work_id: Mapped[str] = mapped_column(String(64))
    mp_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    constituency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(255))
    district: Mapped[str] = mapped_column(String(255))
    location_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    sanctioned_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    expenditure: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    financial_progress: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    physical_progress: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    sanction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    implementing_agency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contractor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="projects")
    payments: Mapped[list["PaymentRecord"]] = relationship(
        foreign_keys="PaymentRecord.project_id",
        back_populates="project",
        cascade="all, delete-orphan",
        overlaps="project",
    )
    assets: Mapped[list["AssetRecord"]] = relationship(
        foreign_keys="AssetRecord.project_id",
        back_populates="project",
        cascade="all, delete-orphan",
        overlaps="project",
    )
    metrics: Mapped["ProjectMetrics | None"] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    signals: Mapped[list["ProjectSignal"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    peer_links: Mapped[list["ProjectPeer"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    related_links: Mapped[list["RelatedProject"]] = relationship(
        foreign_keys="RelatedProject.project_id",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    cases: Mapped[list["InvestigationCase"]] = relationship(back_populates="project")


class ProjectMetrics(Base):
    """Derived analytics — never mixed with source facts (schema §5)."""

    __tablename__ = "project_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), unique=True
    )
    cost_deviation_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    peer_median_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    peer_p75_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    peer_percentile: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    financial_physical_gap: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    expenditure_ratio: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    elapsed_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agency_share_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    ml_anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    duplicate_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    calculation_version: Mapped[str] = mapped_column(String(50), default="v1")

    project: Mapped[Project] = relationship(back_populates="metrics")


class ProjectSignal(Base):
    """One detected signal per row (schema §6). Model output layer."""

    __tablename__ = "project_signal"
    __table_args__ = (
        Index("ix_signal_project_severity", "project_id", "severity"),
        Index("ix_signal_type", "signal_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    signal_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[str] = mapped_column(String(255))
    explanation: Mapped[str] = mapped_column(Text)
    observed_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reference_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    difference_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20))
    source_version: Mapped[str] = mapped_column(String(50), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="signals")
    evidence: Mapped[list["SignalEvidence"]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )


class SignalEvidence(Base):
    """Fine-grained evidence supporting a signal (schema §7)."""

    __tablename__ = "signal_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    signal_id: Mapped[str] = mapped_column(ForeignKey("project_signal.id"))
    field_name: Mapped[str] = mapped_column(String(100))
    field_value: Mapped[str] = mapped_column(Text)
    reference_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    signal: Mapped[ProjectSignal] = relationship(back_populates="evidence")


class PeerGroup(Base):
    """Named peer-group definition (schema §8)."""

    __tablename__ = "peer_group"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    financial_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    size_band: Mapped[str | None] = mapped_column(String(50), nullable=True)
    definition: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ProjectPeer(Base):
    """Benchmark relationship between a project and a peer group (schema §9)."""

    __tablename__ = "project_peer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    peer_group_id: Mapped[str] = mapped_column(ForeignKey("peer_group.id"))
    peer_count: Mapped[int] = mapped_column(Integer)
    median_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    p75_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    percentile: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="peer_links")
    peer_group: Mapped[PeerGroup] = relationship()


class RelatedProject(Base):
    """Potentially related / duplicate-candidate link (schema §10)."""

    __tablename__ = "related_project"
    __table_args__ = (Index("ix_related_score", "project_id", "combined_score"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    related_project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    text_similarity: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    location_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 1), nullable=True)
    cost_similarity: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    category_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_overlap: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    combined_score: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    relation_type: Mapped[str] = mapped_column(String(50), default="DUPLICATE_CANDIDATE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(
        foreign_keys=[project_id], back_populates="related_links"
    )
    related_project: Mapped[Project] = relationship(foreign_keys=[related_project_id])


class InvestigationCase(Base):
    """Officer-owned investigation case (schema §11). Conclusion layer."""

    __tablename__ = "investigation_case"
    __table_args__ = (
        Index("ix_case_status_priority", "status", "priority"),
        Index("ix_case_officer", "assigned_officer_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    case_number: Mapped[str] = mapped_column(String(50), unique=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    assigned_officer_id: Mapped[str | None] = mapped_column(
        ForeignKey("officer.id"), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship(back_populates="cases")
    assigned_officer: Mapped["Officer | None"] = relationship()
    events: Mapped[list["CaseEvent"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    notes: Mapped[list["CaseNote"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["CaseEvidence"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class CaseEvent(Base):
    """Immutable-style audit trail (schema §12)."""

    __tablename__ = "case_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_case.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("officer.id"), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    case: Mapped[InvestigationCase] = relationship(back_populates="events")


class CaseNote(Base):
    """Officer note on a case (schema §13)."""

    __tablename__ = "case_note"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_case.id"))
    author_id: Mapped[str] = mapped_column(ForeignKey("officer.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    case: Mapped[InvestigationCase] = relationship(back_populates="notes")
    author: Mapped["Officer"] = relationship()


class CaseEvidence(Base):
    """Evidence attached to a case (schema §14)."""

    __tablename__ = "case_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_case.id"))
    signal_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_signal.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(50), default="SIGNAL")
    file_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    case: Mapped[InvestigationCase] = relationship(back_populates="evidence")
    signal: Mapped[ProjectSignal | None] = relationship()


class Officer(Base):
    """Platform user (schema §15, extended by backlog #2/#4)."""

    __tablename__ = "officer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="INVESTIGATOR")
    # Stakeholder scope (backlog #4): MP / DISTRICT_AUTHORITY / STATE_NODAL /
    # MINISTRY / ADMIN. NULL for platform investigators.
    stakeholder_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    constituency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # PBKDF2-SHA256 (backlog #2); NULL for demo-only officers.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RuleDefinition(Base):
    """Configurable detection rule metadata (schema §16)."""

    __tablename__ = "rule_definition"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    rule_code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    definition: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(String(20))
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="v1")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DetectionRun(Base):
    """Detection execution record (schema §17)."""

    __tablename__ = "detection_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    model_version: Mapped[str] = mapped_column(String(50))
    ruleset_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="QUEUED")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Report(Base):
    """Generated audit report (schema §18)."""

    __tablename__ = "report"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_case.id"))
    report_number: Mapped[str] = mapped_column(String(50), unique=True)
    format: Mapped[str] = mapped_column(String(20), default="PDF")
    file_reference: Mapped[str] = mapped_column(String(500))
    generated_by: Mapped[str] = mapped_column(ForeignKey("officer.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    report_version: Mapped[str] = mapped_column(String(50), default="v1")

    case: Mapped[InvestigationCase] = relationship(back_populates="reports")
    generator: Mapped[Officer] = relationship()


class MPAllocationRecord(Base):
    """Normalized MP-level allocation row (Prompt-3 §15).

    Lok Sabha sources provide constituency; Rajya Sabha sources provide
    elected_nominated. Fields absent from a source stay NULL — never
    invented (Prompt-3 §4/§15).
    """

    __tablename__ = "mp_allocation_record"
    __table_args__ = (
        Index("ix_mpa_state", "state"),
        Index("ix_mpa_name", "mp_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    serial_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mp_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    constituency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    elected_nominated: Mapped[str | None] = mapped_column(String(50), nullable=True)
    allocated_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    # Unit actually present in the source: RUPEE or CRORE (Prompt-3 §18/§37).
    amount_unit: Mapped[str] = mapped_column(String(10), default="RUPEE")
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="mp_allocations")


class SchemeAggregate(Base):
    """Dashboard-level aggregate metrics (Prompt-3 §16).

    One row per house where the source provides values; only fields
    actually available are populated.
    """

    __tablename__ = "scheme_aggregate"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    house: Mapped[str | None] = mapped_column(String(20), nullable=True)
    allocated_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    amount_consented_for_calamity: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    works_recommended: Mapped[int | None] = mapped_column(Integer, nullable=True)
    works_sanctioned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    works_completed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expenditure_completed_and_ongoing: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    # Unit of the monetary aggregate fields (RUPEE / CRORE / LAKH).
    monetary_unit: Mapped[str] = mapped_column(String(10), default="RUPEE")
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="aggregates")


class AuditEvent(Base):
    """Tamper-evident audit event (backlog #2).

    Append-only chain: entry_hash = sha256(prev_hash || canonical(event)).
    Any retroactive modification breaks every subsequent link, and
    `verify_audit_chain` detects exactly where.
    """

    __tablename__ = "audit_event"
    __table_args__ = (
        Index("ix_audit_seq", "seq"),
        Index("ix_audit_action", "action"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    seq: Mapped[int] = mapped_column(Integer, unique=True, autoincrement=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertDigest(Base):
    """Stateful early-warning digest per stakeholder role (backlog #6).

    `last_seen_seq` marks how far the role has reviewed; regeneration
    reports only signal/case movement since that watermark.
    """

    __tablename__ = "alert_digest"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    role: Mapped[str] = mapped_column(String(40))
    last_seen_seq: Mapped[int] = mapped_column(Integer, default=0)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PaymentRecord(Base):
    """Vendor payment against a work (backlog #5). Optional layer: rows exist
    only when an official source provides payment data — never fabricated."""

    __tablename__ = "payment_record"
    __table_args__ = (
        Index("ix_payment_project", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    payment_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    unit: Mapped[str] = mapped_column(String(10), default="RUPEE")
    paid_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    payee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(
        foreign_keys=[project_id], back_populates="payments"
    )


class AssetRecord(Base):
    """Asset creation / verification status for a completed work (backlog #5).
    Optional layer, same NULL-first policy as payments."""

    __tablename__ = "asset_record"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    asset_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    geo_tagged_photo_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(
        foreign_keys=[project_id], back_populates="assets"
    )


class ValidationIssue(Base):
    """One normalized-validation issue for an ingested row (Prompt-3 §23).

    ERROR rows are not imported (but preserved here); WARNING/INFO rows are
    imported alongside their issue. This table is the audit trail for
    partial-validity imports.
    """

    __tablename__ = "validation_issue"
    __table_args__ = (
        Index("ix_vissue_dataset", "dataset_id"),
        Index("ix_vissue_severity", "severity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="validation_issues")
