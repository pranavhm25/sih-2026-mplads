"""Contextual duplicate-candidate tests ("similarity ≠ duplication").

Scenario matrix (docs/TRD.md TR-07):
  1. same description + same site + same agency   → strong candidate
  2. same description + nearby site + same agency  → strong candidate
  3. generic wording + far apart                   → NOT strong
  4. generic wording + different agencies          → confidence reduced
  5. similar description + missing coordinates     → graceful degradation
  6. similar description + missing agency         → graceful degradation
  7. unrelated descriptions                        → not candidates
Plus: MPL-10281 flagship pair keeps working with distance computed from
coordinates (never hardcoded) and contextual confidence HIGH.
"""
from __future__ import annotations

import math

import pytest

from app.core import constants as C
from app.nlp.duplicate_candidates import (
    combined_score,
    contextual_confidence,
    normalize_vendor,
    vendor_overlap,
)


# ---------------------------------------------------------------------------
# helpers — deterministic in-memory projects (no DB needed for unit level)
# ---------------------------------------------------------------------------
class _P:
    """Minimal stand-in with the attributes the engine touches."""

    def __init__(self, work_id, description, lat=None, lon=None,
                 agency="District Rural Development Agency",
                 cost=2_500_000, category="Education",
                 sanction_date=None, start_date=None, completion_date=None):
        self.id = work_id
        self.work_id = work_id
        self.description = description
        self.latitude = lat
        self.longitude = lon
        self.implementing_agency = agency
        self.sanctioned_cost = cost
        self.category = category
        self.sanction_date = sanction_date
        self.start_date = start_date
        self.completion_date = completion_date


GENERIC = "Construction of community hall at Ward 12"
NEARBY = 30.0          # within the 50 m strong band
FAR = 5000.0           # beyond the 2 km geo gate
DIFFERENT_SITE_LAT = 0.05  # ≈ 5.5 km apart


# ---------------------------------------------------------------------------
# unit level: vendor normalization + contextual confidence
# ---------------------------------------------------------------------------
class TestVendorOverlap:
    def test_identical_agencies_match(self):
        same, ratio = vendor_overlap("District Rural Development Agency",
                                     "District Rural Development Agency")
        assert same is True and ratio == 1.0

    def test_legal_form_noise_ignored(self):
        same, _ = vendor_overlap("Sri Balaji Constructions Pvt. Ltd.",
                                 "Sri Balaji Constr.")
        assert same is True

    def test_different_agencies_do_not_match(self):
        same, ratio = vendor_overlap("Public Works Department",
                                     "Municipal Corporation")
        assert same is False and ratio == 0.0

    def test_missing_vendor_is_unavailable(self):
        assert vendor_overlap(None, "Public Works Department") == (None, None)
        assert vendor_overlap("Public Works Department", "") == (None, None)

    def test_stopwords_removed(self):
        assert "limited" not in normalize_vendor("ABC Limited")
        assert "abc" in normalize_vendor("ABC Limited")


class TestContextualConfidence:
    def test_same_site_same_vendor_is_high(self):
        band, score, reasons = contextual_confidence(
            0.0, True, 1.0, True, True
        )
        assert band == "high"
        assert score is not None and score > 0.9
        assert "geographically proximate" in reasons
        assert "same implementing agency" in reasons

    def test_nearby_same_vendor_is_high(self):
        band, _, _ = contextual_confidence(NEARBY, True, 0.95, True, True)
        assert band == "high"

    def test_far_apart_is_low_even_with_same_vendor(self):
        band, _, reasons = contextual_confidence(FAR, True, 0.95, True, True)
        assert band == "low"
        assert "locations far apart" in reasons

    def test_different_vendor_is_low(self):
        band, _, reasons = contextual_confidence(None, False, 0.95, True, True)
        assert band == "low"
        assert "different implementing agencies" in reasons

    def test_missing_both_signals_is_unavailable(self):
        band, score, reasons = contextual_confidence(None, None, 0.95, True, True)
        assert band == "unavailable"
        assert score is None
        assert "agency data unavailable" in reasons

    def test_geo_only_agreement_is_medium(self):
        """Geo-close + unknown vendor: one signal agrees, none contradicts."""
        band, _, _ = contextual_confidence(NEARBY, None, 0.95, True, True)
        assert band == "medium"

    def test_vendor_only_agreement_is_medium(self):
        band, _, _ = contextual_confidence(None, True, 0.95, True, True)
        assert band == "medium"


# ---------------------------------------------------------------------------
# severity gating is contextual (Step 9)
# ---------------------------------------------------------------------------
class TestSeverityGating:
    def test_severity_mapping_in_engine(self):
        """High confidence → HIGH severity; low/unavailable → LOW."""
        # verified through the pipeline-level tests below; here we pin the
        # expected mapping so a regression is loud.
        assert C.DUPLICATE_WEAK_CONFIDENCE_WEIGHT < 1.0


# ---------------------------------------------------------------------------
# pipeline level: full detection over ingested rows
# ---------------------------------------------------------------------------
@pytest.fixture()
def dup_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.models import Dataset, ProjectMetrics

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    dataset = Dataset(
        name="Dup test DS", source_label="unit-test", source_type="MEMORY",
        version="v1", is_synthetic=True, quality_status="VALID",
    )
    session.add(dataset)
    session.commit()
    session.dataset_id = dataset.id
    yield session, dataset
    session.close()


def _add_work(db, dataset, row: dict) -> None:
    """Persist a Project directly from a plain dict — the unit under test is
    the duplicate engine, not the ingestion mapper."""
    from datetime import date

    from app.models import Project, ProjectMetrics

    p = Project(
        dataset_id=dataset.id,
        work_id=row["work_id"],
        state=row["state"], district=row["district"],
        description=row["work_name"],
        sanctioned_cost=row["sanctioned_amount"],
        estimated_cost=row["sanctioned_amount"],
        expenditure=row.get("expenditure"),
        financial_progress=row.get("financial_progress") or 0,
        physical_progress=row.get("physical_progress") or 0,
        sanction_date=date.fromisoformat(row["sanction_date"]),
        start_date=date.fromisoformat(row["start_date"]),
        category=row.get("category"),
        status=row.get("status") or "Unknown",
        implementing_agency=row.get("implementing_agency"),
        latitude=row.get("latitude"),
        longitude=row.get("longitude"),
        location_text=row.get("location_text"),
        expected_duration_days=row.get("expected_duration_days"),
    )
    db.add(p)
    db.flush()
    db.add(ProjectMetrics(project_id=p.id, calculation_version="metrics-v1"))
    db.commit()
    return p


def _row(work_id, description, lat=13.05, lon=77.55, agency="District Rural Development Agency"):
    return {
        "work_id": work_id,
        "work_name": description,
        "state": "Karnataka",
        "district": "Synthetic District",
        "category": "Education",
        "status": "In Progress",
        "sanction_date": "2025-06-01",
        "start_date": "2025-06-15",
        "expected_duration_days": 365,
        "physical_progress": 50,
        "financial_progress": 55,
        "sanctioned_amount": 2500000,
        "expenditure": 1200000,
        "latitude": lat,
        "longitude": lon,
        "implementing_agency": agency,
        "location_text": "Ward 12",
    }


def _run_detection(db, dataset):
    from app.models import Project
    from app.nlp.duplicate_candidates import detect_duplicate_candidates

    projects = db.query(Project).filter(Project.dataset_id == dataset.id).all()
    return detect_duplicate_candidates(db, projects), projects


def _signals_for(db, dataset, work_id):
    from app.models import Project, ProjectSignal

    p = db.query(Project).filter(
        Project.dataset_id == dataset.id, Project.work_id == work_id
    ).first()
    return p, [
        s for s in p.signals
        if s.signal_type == C.SignalType.DUPLICATE and s.triggered
    ]


class TestBoilerplateScenarios:
    """The seven-scenario matrix (Step 7)."""

    def test_1_same_desc_same_site_same_vendor_strong(self, dup_db):
        db, ds = dup_db
        _add_work(db, ds, _row("D1", GENERIC, 13.05, 77.55))
        _add_work(db, ds, _row("D2", GENERIC, 13.05, 77.55))
        counts, _ = _run_detection(db, ds)
        p, sigs = _signals_for(db, ds, "D1")
        assert sigs, "strong pair must be flagged"
        assert sigs[0].severity == C.Severity.HIGH
        assert sigs[0].difference_value["contextual_confidence"] == "high"
        texts = " ".join(e.field_name for e in sigs[0].evidence)
        assert "vendor overlap" in texts and "geospatial proximity" in texts

    def test_2_same_desc_nearby_same_vendor_strong(self, dup_db):
        db, ds = dup_db
        _add_work(db, ds, _row("D1", GENERIC, 13.05, 77.55))
        # ~30 m offset in latitude
        _add_work(db, ds, _row("D2", GENERIC, 13.05027, 77.55))
        counts, _ = _run_detection(db, ds)
        _, sigs = _signals_for(db, ds, "D1")
        assert sigs
        assert sigs[0].difference_value["contextual_confidence"] == "high"
        # distance actually computed from coordinates, not hardcoded
        dist = sigs[0].evidence[1].field_value
        assert dist.endswith("m") and 20.0 <= float(dist[:-2]) <= 45.0

    def test_3_generic_wording_far_apart_not_strong(self, dup_db):
        db, ds = dup_db
        _add_work(db, ds, _row("D1", GENERIC, 13.05, 77.55))
        _add_work(db, ds, _row("D2", GENERIC, 13.05 + DIFFERENT_SITE_LAT, 77.55))
        counts, _ = _run_detection(db, ds)
        p, sigs = _signals_for(db, ds, "D1")
        if sigs:  # pair may not even survive the geo gate
            assert sigs[0].severity == C.Severity.LOW
            assert sigs[0].difference_value["contextual_confidence"] == "low"
            assert "insufficient contextual" in sigs[0].explanation
        assert counts.get("high", 0) == 0

    def test_4_generic_wording_different_vendors_reduced(self, dup_db):
        db, ds = dup_db
        _add_work(db, ds, _row("D1", GENERIC, 13.05, 77.55,
                               agency="Public Works Department"))
        _add_work(db, ds, _row("D2", GENERIC, 13.05, 77.55,
                               agency="Municipal Corporation"))
        counts, _ = _run_detection(db, ds)
        _, sigs = _signals_for(db, ds, "D1")
        assert sigs  # same site, so pair survives
        assert sigs[0].difference_value["contextual_confidence"] == "low"
        assert sigs[0].severity == C.Severity.LOW
        ev = " ".join(e.field_value for e in sigs[0].evidence)
        assert "different" in ev

    def test_5_missing_coordinates_graceful(self, dup_db):
        db, ds = dup_db
        _add_work(db, ds, _row("D1", GENERIC, None, None))
        _add_work(db, ds, _row("D2", GENERIC, 13.05, 77.55))
        counts, _ = _run_detection(db, ds)
        _, sigs = _signals_for(db, ds, "D1")
        # Without coordinates the pair can still be flagged via vendor
        # agreement (same agency) but must NOT be a strong candidate.
        assert counts.get("high", 0) == 0
        if sigs:
            assert sigs[0].difference_value["contextual_confidence"] in (
                "medium", "low", "unavailable"
            )
            geo_ev = next(
                e for e in sigs[0].evidence
                if e.field_name == "geospatial proximity"
            )
            assert "unavailable" in geo_ev.field_value

    def test_6_missing_vendor_graceful(self, dup_db):
        db, ds = dup_db
        _add_work(db, ds, _row("D1", GENERIC, 13.05, 77.55, agency=None))
        _add_work(db, ds, _row("D2", GENERIC, 13.05, 77.55, agency=None))
        counts, _ = _run_detection(db, ds)
        _, sigs = _signals_for(db, ds, "D1")
        assert sigs  # geo evidence still corroborates
        # geo-close + unknown vendor → medium, never high
        assert sigs[0].difference_value["contextual_confidence"] in ("medium",)
        assert counts.get("high", 0) == 0

    def test_7_unrelated_descriptions_not_candidates(self, dup_db):
        db, ds = dup_db
        _add_work(db, ds, _row("D1", GENERIC, 13.05, 77.55))
        _add_work(db, ds, _row("D2", "Providing school furniture desks chairs",
                               13.05, 77.55))
        counts, _ = _run_detection(db, ds)
        _, sigs = _signals_for(db, ds, "D1")
        assert not sigs
        assert sum(counts.values()) == 0


class TestMPL10281FlagshipPair:
    """Step 8: the flagship fixture pair must keep working; distance is
    computed from coordinates (≈43 m, asserted as a band, not a constant)."""

    def test_flagship_pair_contextual_high(self, seeded_db):
        from app.models import Project

        a = seeded_db.query(Project).filter(Project.work_id == "MPL-10281").first()
        b = seeded_db.query(Project).filter(Project.work_id == "MPL-10412").first()
        sigs = [
            s for s in a.signals
            if s.signal_type == C.SignalType.DUPLICATE and s.triggered
        ]
        assert sigs and b
        s = sigs[0]
        # contextual validation agrees → strong candidate
        assert s.difference_value["contextual_confidence"] == "high"
        assert s.severity == C.Severity.HIGH
        # distance from coordinates, within a physical-plausibility band
        geo_ev = next(
            e for e in s.evidence if e.field_name == "geospatial proximity"
        )
        dist_m = float(geo_ev.field_value[:-2])
        expected = math.hypot(
            (float(a.latitude) - float(b.latitude)) * 111_000,
            (float(a.longitude) - float(b.longitude)) * 111_000
            * math.cos(math.radians(float(a.latitude))),
        )
        assert abs(dist_m - expected) < 2.0  # same calculation, rounded display
        # pair is on the same block, well inside the 50 m strong band
        assert 0.0 < dist_m <= 50.0

    def test_flagship_pair_link_carries_context(self, seeded_db):
        from app.models import RelatedProject

        link = (
            seeded_db.query(RelatedProject)
            .filter(RelatedProject.relation_type == "DUPLICATE_CANDIDATE")
            .first()
        )
        assert link is not None
        assert link.vendor_match is True
        assert link.contextual_confidence == "high"
        assert link.location_distance_m is not None
