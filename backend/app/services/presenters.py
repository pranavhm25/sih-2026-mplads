"""Presenters — convert ORM records into the typed API payloads.

Keeps route handlers thin and guarantees that signals always carry their
evidence, recommended action and provenance when exposed.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import constants as C
from app.models import (
    InvestigationCase,
    Project,
    ProjectPeer,
    ProjectSignal,
    RelatedProject,
)
from app.schemas.schemas import (
    EvidenceOut,
    MetricsOut,
    PeerOut,
    PriorityOut,
    ProjectDetail,
    ProjectSummary,
    RelatedProjectOut,
    SignalOut,
)


def priority_for(project: Project, fusion: dict | None) -> PriorityOut | None:
    if not fusion:
        return None
    return PriorityOut(
        level=fusion["level"],
        score=fusion["score"],
        signal_count=fusion["signal_count"],
        reasons=fusion["reasons"],
    )


def to_summary(project: Project, fusion: dict | None,
               case: InvestigationCase | None = None) -> ProjectSummary:
    triggered = [s for s in project.signals if s.triggered]
    primary = sorted(
        triggered,
        key=lambda s: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(s.severity, 9)),
    )
    return ProjectSummary(
        id=project.id,
        work_id=project.work_id,
        description=project.description,
        district=project.district,
        state=project.state,
        category=project.category,
        status=project.status,
        sanctioned_cost=float(project.sanctioned_cost),
        latitude=float(project.latitude) if project.latitude is not None else None,
        longitude=float(project.longitude) if project.longitude is not None else None,
        priority=priority_for(project, fusion),
        primary_signals=[s.signal_type for s in primary[:3]],
        case_status=case.status if case else None,
    )


def to_signal_out(s: ProjectSignal) -> SignalOut:
    return SignalOut(
        id=s.id,
        signal_type=s.signal_type,
        severity=s.severity,
        triggered=s.triggered,
        title=s.title,
        explanation=s.explanation,
        observed_value=s.observed_value,
        reference_value=s.reference_value,
        difference_value=s.difference_value,
        source_type=s.source_type,
        source_version=s.source_version,
        created_at=s.created_at,
        evidence=[EvidenceOut.model_validate(e) for e in s.evidence],
        recommended_action=C.RECOMMENDED_VERIFICATION.get(s.signal_type),
    )


def to_detail(project: Project, fusion: dict | None,
              case: InvestigationCase | None = None,
              dataset_version: str | None = None,
              dataset_is_synthetic: bool | None = None) -> ProjectDetail:
    summary = to_summary(project, fusion, case)
    m = project.metrics

    metrics_out = None
    if m is not None:
        metrics_out = MetricsOut(
            cost_deviation_pct=float(m.cost_deviation_pct) if m.cost_deviation_pct is not None else None,
            peer_median_cost=float(m.peer_median_cost) if m.peer_median_cost is not None else None,
            peer_p75_cost=float(m.peer_p75_cost) if m.peer_p75_cost is not None else None,
            peer_percentile=float(m.peer_percentile) if m.peer_percentile is not None else None,
            financial_physical_gap=float(m.financial_physical_gap) if m.financial_physical_gap is not None else None,
            expenditure_ratio=float(m.expenditure_ratio) if m.expenditure_ratio is not None else None,
            elapsed_days=m.elapsed_days,
            expected_duration_days=m.expected_duration_days,
            delay_days=m.delay_days,
            agency_share_pct=float(m.agency_share_pct) if m.agency_share_pct is not None else None,
            ml_anomaly_score=float(m.ml_anomaly_score) if m.ml_anomaly_score is not None else None,
            duplicate_score=float(m.duplicate_score) if m.duplicate_score is not None else None,
            calculated_at=m.calculated_at,
            calculation_version=m.calculation_version,
        )

    peers_out = [
        PeerOut(
            peer_group_name=pp.peer_group.name,
            peer_count=pp.peer_count,
            median_cost=float(pp.median_cost) if pp.median_cost is not None else None,
            p75_cost=float(pp.p75_cost) if pp.p75_cost is not None else None,
            percentile=float(pp.percentile) if pp.percentile is not None else None,
        )
        for pp in (project.peer_links or [])
    ]

    related_out: list[RelatedProjectOut] = []
    for link in (project.related_links or []):
        other = link.related_project
        related_out.append(RelatedProjectOut(
            related_project_id=other.id,
            work_id=other.work_id,
            project_name=other.description,
            district=other.district,
            text_similarity=float(link.text_similarity) if link.text_similarity is not None else None,
            location_distance_m=float(link.location_distance_m) if link.location_distance_m is not None else None,
            cost_similarity=float(link.cost_similarity) if link.cost_similarity is not None else None,
            category_match=link.category_match,
            time_overlap=link.time_overlap,
            vendor_match=link.vendor_match,
            contextual_confidence=link.contextual_confidence,
            combined_score=float(link.combined_score),
        ))
    # Also include links where this project is the *related* side.
    session = Session.object_session(project)
    if session:
        reverse = (
            session.query(RelatedProject)
            .filter(RelatedProject.related_project_id == project.id)
            .all()
        )
        for link in reverse:
            other = link.project
            if any(r.related_project_id == other.id for r in related_out):
                continue
            related_out.append(RelatedProjectOut(
                related_project_id=other.id,
                work_id=other.work_id,
                project_name=other.description,
                district=other.district,
                text_similarity=float(link.text_similarity) if link.text_similarity is not None else None,
                location_distance_m=float(link.location_distance_m) if link.location_distance_m is not None else None,
                cost_similarity=float(link.cost_similarity) if link.cost_similarity is not None else None,
                category_match=link.category_match,
                time_overlap=link.time_overlap,
                vendor_match=link.vendor_match,
                contextual_confidence=link.contextual_confidence,
                combined_score=float(link.combined_score),
            ))

    triggered = [s for s in project.signals if s.triggered]
    why = None
    if triggered:
        engines = sorted({s.source_type for s in triggered})
        top = sorted(triggered, key=lambda s: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(s.severity, 9)))[:3]
        why = (
            f"{len(triggered)} independent signal(s) from {', '.join(engines)} converge on this work: "
            + "; ".join(s.title for s in top)
            + ". Review the evidence below and verify on the ground before any conclusion."
        )

    return ProjectDetail(
        **summary.model_dump(),
        mp_name=project.mp_name,
        constituency=project.constituency,
        location_text=project.location_text,
        sector=project.sector,
        estimated_cost=float(project.estimated_cost),
        expenditure=float(project.expenditure) if project.expenditure is not None else None,
        financial_progress=float(project.financial_progress) if project.financial_progress is not None else None,
        physical_progress=float(project.physical_progress) if project.physical_progress is not None else None,
        sanction_date=project.sanction_date,
        start_date=project.start_date,
        completion_date=project.completion_date,
        implementing_agency=project.implementing_agency,
        contractor_name=project.contractor_name,
        expected_duration_days=project.expected_duration_days,
        metrics=metrics_out,
        signals=[to_signal_out(s) for s in sorted(
            project.signals,
            key=lambda s: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(s.severity, 9), s.signal_type),
        )],
        peers=peers_out,
        related=related_out,
        why_flagged=why,
        dataset_version=dataset_version,
        dataset_is_synthetic=dataset_is_synthetic,
    )
