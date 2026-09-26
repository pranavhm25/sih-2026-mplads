"""Synthetic model validation tests (Step 10).

Verifies:
  - deterministic generation (same seed → identical plan)
  - injection correctness (counts, distinct IDs, ground truth wiring)
  - ground-truth correctness (normal vs anomaly marking)
  - metric calculations against hand-computed values (toy dataset)
  - confusion-matrix classification
  - zero-division handling (None, never fabricated 0/1)
  - result serialization (JSON round-trip, no NaN/Infinity)
  - one end-to-end scenario through the real pipeline (small, deterministic)
  - DB hygiene (benchmark datasets removed afterwards)
"""
from __future__ import annotations

import json

import pytest

from app.services.validation.synthetic.injection import (
    BASELINE_PREFIX,
    INJECTED_PREFIX,
    REFERENCE_DATE,
    SyntheticDatasetBuilder,
)
from app.services.validation.synthetic.metrics import (
    ConfusionMatrix,
    WorkEvaluation,
    compute_metrics,
    evaluate,
    safe_div,
)


# ---------------------------------------------------------------------------
# Determinism (Step 3)
# ---------------------------------------------------------------------------
class TestDeterminism:
    def test_same_seed_identical_plans(self):
        b1 = SyntheticDatasetBuilder(seed=26102)
        b2 = SyntheticDatasetBuilder(seed=26102)
        b1.generate_baseline_dataset(n=40)
        b2.generate_baseline_dataset(n=40)
        b1.inject_cost_anomalies(3)
        b2.inject_cost_anomalies(3)
        b1.inject_duplicate_anomalies(2)
        b2.inject_duplicate_anomalies(2)
        assert b1.build_csv() == b2.build_csv()
        assert b1.ground_truth.as_list() == b2.ground_truth.as_list()

    def test_different_seed_different_plan(self):
        b1 = SyntheticDatasetBuilder(seed=1)
        b2 = SyntheticDatasetBuilder(seed=2)
        b1.generate_baseline_dataset(n=30)
        b2.generate_baseline_dataset(n=30)
        assert b1.build_csv() != b2.build_csv()

    def test_reference_date_fixed(self):
        assert REFERENCE_DATE.isoformat() == "2026-09-01"


# ---------------------------------------------------------------------------
# Injection correctness (Steps 2–3)
# ---------------------------------------------------------------------------
class TestInjections:
    def test_baseline_rows_marked_normal(self):
        b = SyntheticDatasetBuilder(seed=7)
        b.generate_baseline_dataset(n=20)
        entries = b.ground_truth.entries
        assert len(entries) == 20
        assert all(e["injected"] is False for e in entries.values())
        assert all(e["ground_truth"] == "normal" for e in entries.values())
        assert all(w.startswith(BASELINE_PREFIX) for w in entries)

    def test_cost_injection_ground_truth(self):
        b = SyntheticDatasetBuilder(seed=7)
        b.generate_baseline_dataset(n=20)
        rows = b.inject_cost_anomalies(3)
        assert len(rows) == 3
        for r in rows:
            g = b.ground_truth.entries[r["work_id"]]
            assert g["injected"] is True
            assert g["ground_truth"] == "anomaly"
            assert g["anomaly_type"] == "cost_inflation"
            assert g["expected_detector"] == "COST_ANOMALY"
            assert g["injection_id"].startswith("inj-")
            assert g["original_record_id"]  # baseline source recorded
            assert g["original_record_id"].startswith(BASELINE_PREFIX)
            assert r["work_id"].startswith(INJECTED_PREFIX)

    def test_duplicate_injection_creates_pairs(self):
        b = SyntheticDatasetBuilder(seed=7)
        b.generate_baseline_dataset(n=20)
        rows = b.inject_duplicate_anomalies(2)
        assert len(rows) == 4  # each injection = one near-twin pair
        for r in rows:
            g = b.ground_truth.entries[r["work_id"]]
            assert g["anomaly_type"] == "duplicate_similar_work"
            assert g["expected_detector"] == "DUPLICATE"

    def test_injected_ids_are_unique_and_namespaced(self):
        b = SyntheticDatasetBuilder(seed=7)
        b.generate_baseline_dataset(n=30)
        b.inject_cost_anomalies(4)
        b.inject_delay_anomalies(4)
        b.inject_pattern_anomalies(3)
        b.inject_spending_pattern_anomalies(4)
        b.inject_duplicate_anomalies(2)
        ids = [r["work_id"] for r in b.rows]
        assert len(ids) == len(set(ids))  # no collisions
        injected_ids = [i for i in ids if i.startswith(INJECTED_PREFIX)]
        assert len(injected_ids) == 4 + 4 + 3 + 4 + 4

    def test_all_injectors_record_expected_detectors(self):
        b = SyntheticDatasetBuilder(seed=7)
        b.generate_baseline_dataset(n=20)
        b.inject_cost_anomalies(2)
        b.inject_duplicate_anomalies(1)
        b.inject_delay_anomalies(2)
        b.inject_spending_pattern_anomalies(2)
        b.inject_pattern_anomalies(2)
        expected = {
            "cost_inflation": "COST_ANOMALY",
            "duplicate_similar_work": "DUPLICATE",
            "abnormal_duration": "DELAY",
            "unusual_spending_pattern": "ML_ANOMALY",
            "suspicious_attribute_combination": "COMPLIANCE",
        }
        seen = {
            g["anomaly_type"]: g["expected_detector"]
            for g in b.ground_truth.entries.values()
            if g["injected"]
        }
        assert seen == expected


# ---------------------------------------------------------------------------
# Metric math (Steps 4–5) — toy dataset with hand-computed values
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_safe_div_zero_denominator(self):
        assert safe_div(1, 0) is None
        assert safe_div(0, 0) is None
        assert safe_div(3, 6) == 0.5

    def test_toy_confusion_matrix(self):
        """Hand-computed: 10 records, 4 injected; detector flags 3 injected
        (1 missed) + 1 clean (1 FP) → TP=3 FP=1 TN=5 FN=1."""
        works = [
            WorkEvaluation("A1", True, "t", "X", True),
            WorkEvaluation("A2", True, "t", "X", True),
            WorkEvaluation("A3", True, "t", "X", False),
            WorkEvaluation("A4", True, "t", "X", True),
            WorkEvaluation("N1", False, None, None, True),
            WorkEvaluation("N2", False, None, None, False),
            WorkEvaluation("N3", False, None, None, False),
            WorkEvaluation("N4", False, None, None, False),
            WorkEvaluation("N5", False, None, None, False),
            WorkEvaluation("N6", False, None, None, False),
        ]
        cm, m = evaluate(works, total_injected=4)
        assert (cm.tp, cm.fp, cm.tn, cm.fn) == (3, 1, 5, 1)
        # precision = 3/4 = 0.75; recall = 3/4 = 0.75
        assert m.precision == pytest.approx(0.75)
        assert m.recall == pytest.approx(0.75)
        # F1 = 2*0.75*0.75 / 1.5 = 0.75
        assert m.f1 == pytest.approx(0.75)
        # FPR = 1/6
        assert m.false_positive_rate == pytest.approx(1 / 6)
        # detection rate = 3/4
        assert m.detection_rate == pytest.approx(0.75)

    def test_zero_division_cases(self):
        # Nothing flagged at all → precision None, F1 None, FPR 0.0
        cm = ConfusionMatrix(tp=0, fp=0, tn=10, fn=4)
        m = compute_metrics(cm, total_injected=4)
        assert m.precision is None
        assert m.f1 is None
        assert m.recall == 0.0
        assert m.false_positive_rate == 0.0
        assert m.detection_rate == 0.0

        # No clean rows → FPR undefined (None), not 0
        cm2 = ConfusionMatrix(tp=3, fp=0, tn=0, fn=1)
        m2 = compute_metrics(cm2, total_injected=4)
        assert m2.false_positive_rate is None
        assert m2.precision == 1.0
        assert m2.recall == pytest.approx(0.75)

        # Perfect detection, no clean rows: F1 defined
        cm3 = ConfusionMatrix(tp=4, fp=0, tn=0, fn=0)
        m3 = compute_metrics(cm3, total_injected=4)
        assert m3.precision == 1.0
        assert m3.recall == 1.0
        assert m3.f1 == 1.0
        assert m3.detection_rate == 1.0

    def test_confusion_matrix_classification_paths(self):
        works = [
            WorkEvaluation("I1", True, "t", None, True),    # tp
            WorkEvaluation("I2", True, "t", None, False),   # fn
            WorkEvaluation("C1", False, None, None, True),  # fp
            WorkEvaluation("C2", False, None, None, False),  # tn
        ]
        cm, _ = evaluate(works, total_injected=2)
        assert (cm.tp, cm.fn, cm.fp, cm.tn) == (1, 1, 1, 1)

    def test_metrics_serializable(self):
        cm = ConfusionMatrix(tp=2, fp=1, tn=5, fn=1)
        m = compute_metrics(cm, total_injected=3)
        blob = json.dumps({"cm": cm.as_dict(), "metrics": m.as_dict()})
        parsed = json.loads(blob)
        assert parsed["cm"]["tp"] == 2
        assert parsed["metrics"]["precision"] is not None


# ---------------------------------------------------------------------------
# End-to-end scenario through the real pipeline
# ---------------------------------------------------------------------------
class TestBenchmarkScenario:
    @pytest.fixture(scope="class")
    def scenario_d(self, seeded_db):
        from app.core.database import SessionLocal
        from app.services.validation.synthetic.benchmark import (
            SCENARIOS,
            run_scenario,
        )

        db = SessionLocal()
        try:
            return run_scenario("D_mixed_types", SCENARIOS["D_mixed_types"], db=db)
        finally:
            db.close()

    def test_pipeline_completes_and_rows_imported(self, scenario_d):
        assert scenario_d["dataset"]["detection_run_status"] == "COMPLETED"
        assert scenario_d["dataset"]["rows_imported"] == 89  # 60 + 29 injected
        assert scenario_d["totals"]["records_evaluated"] == 89

    def test_injection_counts_match_config(self, scenario_d):
        t = scenario_d["totals"]
        assert t["injected"] == 29
        assert t["normal"] == 60
        assert t["tp"] + t["fn"] == 29
        assert t["tn"] + t["fp"] == 60

    def test_ground_truth_covers_all_rows(self, scenario_d):
        gt_ids = [g["record_id"] for g in scenario_d["ground_truth"]]
        assert len(gt_ids) == scenario_d["totals"]["records_evaluated"]
        assert all(
            g["ground_truth"] in ("normal", "anomaly")
            for g in scenario_d["ground_truth"]
        )

    def test_duplicate_rows_counted_as_injected(self, scenario_d):
        dt = scenario_d["per_anomaly_type"]["duplicate_similar_work"]
        assert dt["injected"] == 6  # 3 pairs × 2 rows

    def test_report_serializes_cleanly(self, seeded_db):
        from app.core.database import SessionLocal
        from app.services.validation.synthetic.benchmark import (
            run_full_benchmark,
        )

        db = SessionLocal()
        try:
            report = run_full_benchmark(db=db)
        finally:
            db.close()
        blob = json.dumps(report)
        assert "NaN" not in blob and "Infinity" not in blob
        parsed = json.loads(blob)
        assert parsed["report_version"] == "synthetic-validation-1"
        assert parsed["experiment_configuration"]["seed"] == 26102
        assert parsed["experiment_configuration"]["threshold_tuning"] == (
            "none — production defaults used"
        )
        assert "do NOT represent" in parsed["language_discipline"]
        # overall consistency: totals must add up
        o = parsed["overall"]["cm"]
        assert o["tp"] + o["fp"] + o["tn"] + o["fn"] == (
            sum(s["totals"]["records_evaluated"] for s in
                [parsed["scenarios"][k] for k in parsed["scenarios"]])
        )

    def test_benchmark_datasets_removed_after_run(self, seeded_db):
        """DB hygiene: injected benchmark datasets must not linger and
        become the latest import for other tests/screens."""
        from app.core.database import SessionLocal
        from app.models import Dataset

        db = SessionLocal()
        try:
            leftovers = (
                db.query(Dataset)
                .filter(Dataset.version == "synthetic-validation-injected")
                .all()
            )
            assert leftovers == []
        finally:
            db.close()
