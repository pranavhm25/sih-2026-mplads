"""Pure metric math for the synthetic benchmark (Step 5).

Zero application imports by design: this module is independently testable
and its arithmetic is verified against a hand-computed toy dataset
(tests/test_synthetic_validation.py::TestMetrics).
"""
from __future__ import annotations

from dataclasses import dataclass, field


def safe_div(numerator: float, denominator: float) -> float | None:
    """Division that reports None instead of crashing on zero denominators."""
    if denominator == 0:
        return None
    return numerator / denominator


@dataclass
class ConfusionMatrix:
    """Confusion matrix for anomaly detection.

    Convention: the "positive" class is "injected anomaly". A detector that
    flags a record votes positive for that record (per-record, any matching
    signal counts once).
    """

    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    def as_dict(self) -> dict:
        return {"tp": self.tp, "fp": self.fp, "tn": self.tn, "fn": self.fn}


@dataclass
class Metrics:
    """Derived metrics; None where a denominator is zero (Step 5 rule)."""

    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    false_positive_rate: float | None = None
    detection_rate: float | None = None

    def as_dict(self) -> dict:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "false_positive_rate": self.false_positive_rate,
            "detection_rate": self.detection_rate,
        }


def compute_metrics(cm: ConfusionMatrix, total_injected: int) -> Metrics:
    """Derive all Step-5 metrics from a confusion matrix.

    Zero-division rule: when a denominator is 0 the metric is None — never
    a fabricated 0.0 or 1.0 (precision with no flagged records is
    *undefined*, not "perfect").
    """
    precision = safe_div(cm.tp, cm.tp + cm.fp)
    recall = safe_div(cm.tp, cm.tp + cm.fn)
    f1 = (
        safe_div(2 * precision * recall, precision + recall)
        if precision is not None and recall is not None
        else None
    )
    fpr = safe_div(cm.fp, cm.fp + cm.tn)
    detection_rate = safe_div(cm.tp, total_injected)
    return Metrics(
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=fpr,
        detection_rate=detection_rate,
    )


@dataclass
class WorkEvaluation:
    """Evaluator output for one work: ground truth vs detector vote."""

    work_id: str
    injected: bool
    anomaly_type: str | None
    expected_detector: str | None
    flagged: bool
    signal_types: list[str] = field(default_factory=list)
    priority: str | None = None
    priority_score: float | None = None
    hit_expected_detector: bool | None = None

    def as_dict(self) -> dict:
        return {
            "work_id": self.work_id,
            "injected": self.injected,
            "anomaly_type": self.anomaly_type,
            "expected_detector": self.expected_detector,
            "flagged": self.flagged,
            "signal_types": self.signal_types,
            "priority": self.priority,
            "priority_score": self.priority_score,
            "hit_expected_detector": self.hit_expected_detector,
        }


def evaluate(
    work_evals: list[WorkEvaluation], total_injected: int
) -> tuple[ConfusionMatrix, Metrics]:
    """Classify every evaluated work and derive metrics.

    Per-record classification:
        tp — injected AND flagged
        fn — injected AND NOT flagged
        fp — normal  AND flagged
        tn — normal  AND NOT flagged
    """
    cm = ConfusionMatrix()
    for w in work_evals:
        if w.injected and w.flagged:
            cm.tp += 1
        elif w.injected and not w.flagged:
            cm.fn += 1
        elif not w.injected and w.flagged:
            cm.fp += 1
        else:
            cm.tn += 1
    return cm, compute_metrics(cm, total_injected)
