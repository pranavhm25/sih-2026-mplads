"""Unit tests for detection rules and evidence fusion."""
from __future__ import annotations

from app.core import constants as C
from app.nlp.duplicate_candidates import (
    combined_score,
    cost_similarity,
    normalize_text,
)
from app.services.detection.fusion import fuse_project, priority_label


class TestPriorityLabel:
    def test_low(self):
        assert priority_label(0.5) == C.Priority.LOW

    def test_medium(self):
        assert priority_label(3.0) == C.Priority.MEDIUM

    def test_high(self):
        assert priority_label(5.0) == C.Priority.HIGH

    def test_critical(self):
        assert priority_label(8.0) == C.Priority.CRITICAL


class TestFusion:
    def test_empty_signals(self):
        f = fuse_project([])
        assert f["score"] == 0
        assert f["level"] == C.Priority.LOW
        assert f["signal_count"] == 0

    def test_single_rule_signal(self):
        class S:
            triggered = True
            signal_type = C.SignalType.DELAY
            severity = C.Severity.HIGH
            title = "Delay"
            source_type = C.SourceType.RULE

        f = fuse_project([S()])
        assert f["score"] == 2.0 * 1.5  # weight * severity multiplier
        assert f["signal_count"] == 1
        assert f["convergence_bonus"] == 0.0

    def test_convergence_bonus_for_multiple_engines(self):
        class S:
            triggered = True
            title = "t"
            severity = C.Severity.MEDIUM

        rule = S(); rule.signal_type = C.SignalType.DELAY; rule.source_type = C.SourceType.RULE
        nlp = S(); nlp.signal_type = C.SignalType.DUPLICATE; nlp.source_type = C.SourceType.NLP
        f = fuse_project([rule, nlp])
        assert f["convergence_bonus"] == 1.5

        ml = S(); ml.signal_type = C.SignalType.ML_ANOMALY; ml.source_type = C.SourceType.ML
        f3 = fuse_project([rule, nlp, ml])
        assert f3["convergence_bonus"] == 3.0

    def test_untriggered_signals_ignored(self):
        class S:
            triggered = False
            signal_type = C.SignalType.DELAY
            severity = C.Severity.CRITICAL
            title = "x"
            source_type = C.SourceType.RULE

        f = fuse_project([S()])
        assert f["score"] == 0


class TestDuplicateScoring:
    def test_normalize_text_stops_generic_words(self):
        assert "construction" not in normalize_text("Construction of community hall")
        assert "community" in normalize_text("Construction of community hall")

    def test_cost_similarity_identical(self):
        assert cost_similarity(100.0, 100.0) == 1.0

    def test_cost_similarity_half(self):
        assert cost_similarity(100.0, 50.0) == 0.5

    def test_combined_score_max_one(self):
        s = combined_score(1.0, 0.0, 1.0, True, True)
        assert s <= 1.0

    def test_combined_score_near_duplicate(self):
        s = combined_score(0.86, 43.0, 0.98, True, True)
        assert s >= C.DUPLICATE_SCORE_HIGH

    def test_combined_score_missing_location_reweights(self):
        s = combined_score(0.9, None, 0.95, True, True)
        assert 0.0 < s <= 1.0


class TestAgencyConcentrationUnit:
    @staticmethod
    def _create_mem_db():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.database import Base
        from app.models import Dataset

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        dataset = Dataset(
            name="Unit Test DS",
            source_label="unit-test",
            source_type="MEMORY",
            version="v1",
            is_synthetic=True,
            quality_status="VALID",
        )
        session.add(dataset)
        session.commit()
        return session, dataset

    def test_critical_concentration(self):
        from app.models import Project, ProjectMetrics
        from app.services.detection.agency_concentration import detect_agency_concentration

        db, ds = self._create_mem_db()
        projects = []
        # 3 works for Agency A at 10L = 30L; 2 works for Agency B at 5L = 10L. Total = 40L.
        # Agency A share = 75% >= 60% -> CRITICAL
        for i in range(3):
            p = Project(
                dataset_id=ds.id,
                work_id=f"W-A-{i}",
                state="Karnataka",
                district="Belagavi",
                description=f"Project A {i}",
                status="In Progress",
                sanctioned_cost=1000000,
                estimated_cost=1000000,
                financial_progress=50,
                physical_progress=50,
                implementing_agency="Public Works Department",
            )
            p.metrics = ProjectMetrics(project_id=p.id)
            db.add(p)
            projects.append(p)

        for i in range(2):
            p = Project(
                dataset_id=ds.id,
                work_id=f"W-B-{i}",
                state="Karnataka",
                district="Belagavi",
                description=f"Project B {i}",
                status="In Progress",
                sanctioned_cost=500000,
                estimated_cost=500000,
                financial_progress=50,
                physical_progress=50,
                implementing_agency="Other Agency",
            )
            p.metrics = ProjectMetrics(project_id=p.id)
            db.add(p)
            projects.append(p)
        db.commit()

        counts = detect_agency_concentration(db, projects)
        assert counts[C.SignalType.AGENCY_CONCENTRATION] == 3

        for p in projects[:3]:
            sig = next(s for s in p.signals if s.signal_type == C.SignalType.AGENCY_CONCENTRATION)
            assert sig.triggered is True
            assert sig.severity == C.Severity.CRITICAL
            assert float(p.metrics.agency_share_pct) == 75.0
            assert len(sig.evidence) >= 1

        for p in projects[3:]:
            sigs = [s for s in p.signals if s.signal_type == C.SignalType.AGENCY_CONCENTRATION]
            assert len(sigs) == 0
            assert float(p.metrics.agency_share_pct) == 25.0

    def test_high_severity_concentration(self):
        from app.models import Project, ProjectMetrics
        from app.services.detection.agency_concentration import detect_agency_concentration

        db, ds = self._create_mem_db()
        projects = []
        # Total 100L. Agency A has 2 works at 25L = 50L (50% -> HIGH between 40% and 60%)
        # Agency B has 2 works at 25L = 50L (50% -> HIGH)
        for i in range(2):
            p = Project(
                dataset_id=ds.id,
                work_id=f"W-A-{i}",
                state="Karnataka",
                district="Mysuru",
                description=f"Project A {i}",
                status="In Progress",
                sanctioned_cost=2500000,
                estimated_cost=2500000,
                financial_progress=50,
                physical_progress=50,
                implementing_agency="Agency Alpha",
            )
            p.metrics = ProjectMetrics(project_id=p.id)
            db.add(p)
            projects.append(p)
        for i in range(2):
            p = Project(
                dataset_id=ds.id,
                work_id=f"W-B-{i}",
                state="Karnataka",
                district="Mysuru",
                description=f"Project B {i}",
                status="In Progress",
                sanctioned_cost=2500000,
                estimated_cost=2500000,
                financial_progress=50,
                physical_progress=50,
                implementing_agency="Agency Beta",
            )
            p.metrics = ProjectMetrics(project_id=p.id)
            db.add(p)
            projects.append(p)
        db.commit()

        counts = detect_agency_concentration(db, projects)
        assert counts[C.SignalType.AGENCY_CONCENTRATION] == 4
        for p in projects:
            sig = next(s for s in p.signals if s.signal_type == C.SignalType.AGENCY_CONCENTRATION)
            assert sig.severity == C.Severity.HIGH

    def test_small_sample_does_not_trigger(self):
        from app.models import Project, ProjectMetrics
        from app.services.detection.agency_concentration import detect_agency_concentration

        db, ds = self._create_mem_db()
        projects = []
        # Only 2 works in district: should NOT trigger concentration even if 1 agency has 100%
        for i in range(2):
            p = Project(
                dataset_id=ds.id,
                work_id=f"W-S-{i}",
                state="Maharashtra",
                district="SmallDist",
                description=f"Small {i}",
                status="In Progress",
                sanctioned_cost=1000000,
                estimated_cost=1000000,
                financial_progress=50,
                physical_progress=50,
                implementing_agency="Sole Agency",
            )
            p.metrics = ProjectMetrics(project_id=p.id)
            db.add(p)
            projects.append(p)
        db.commit()

        counts = detect_agency_concentration(db, projects)
        assert C.SignalType.AGENCY_CONCENTRATION not in counts
        for p in projects:
            sigs = [s for s in p.signals if s.signal_type == C.SignalType.AGENCY_CONCENTRATION]
            assert len(sigs) == 0
            # Metrics still populated transparently
            assert float(p.metrics.agency_share_pct) == 100.0
