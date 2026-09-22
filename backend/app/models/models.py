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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid4())


class Dataset(Base):
    """Ingestion/provenance metadata (schema §3)."""

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

    projects: Mapped[list["Project"]] = relationship(back_populates="dataset")


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
    """Platform user (schema §15)."""

    __tablename__ = "officer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="INVESTIGATOR")
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
