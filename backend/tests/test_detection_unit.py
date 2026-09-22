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
