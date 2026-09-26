# Synthetic Model Validation — Controlled Injection Benchmark

**Drishti — MPLADS Risk Intelligence & Investigation Platform**
Report version: `synthetic-validation-1`
Benchmark artifact: `docs/synthetic_validation_results.json`
Runner: `backend/scripts/run_synthetic_validation.py`
Engine: `backend/app/services/validation/synthetic/`

> **Language discipline.** This is a **controlled synthetic benchmark** on
> the existing detection pipeline. Results do **not** represent
> production-world fraud detection accuracy. All metrics are computed
> against synthetic ground truth for anomalies we injected ourselves.

## 1. Objective

Quantitatively evaluate Drishti's existing detection pipeline using
controlled synthetic data with explicit ground truth, and report
precision / recall / F1 / false-positive rate / detection rate / confusion
matrix — without modifying the pipeline, its thresholds, or its behaviour.

## 2. Dataset generation

`SyntheticDatasetBuilder` (deterministic, seeded with `26102` — fixed)
produces a **baseline of 60 clean works** in one district:

| Field | Band (deliberately away from every trigger) |
|---|---|
| Sanctioned cost | 25 L median ×(0.88–1.12) |
| Financial vs physical | within ±12 pp |
| Elapsed vs expected | ≤ 200 d vs 300–420 d expected |
| Expenditure ratio | 0.15–0.55 of sanctioned |
| Agencies | 4 rotated (no concentration) |
| Descriptions | 12 kinds × 8 places × 3 phrasings (no accidental text twins) |
| Locations | spaced grid, adjacent sites ≈ 2.2 km apart (no proximity hits) |

Bands were calibrated so Scenario A (clean) exercises the pipeline without
firing the rule triggers. Two iterations were needed: the first design
concentrated all works under one agency (AGENCY_CONCENTRATION flagged
everything) and reused six description kinds (TF-IDF produced 328 false
duplicate-pair signals). The calibration history itself is documented as a
limitation in §11.

## 3. Injection methodology

Injectors add records **on top of** the baseline; each is registered in a
ground-truth side table. Five anomaly types — exactly the five that map to
existing Drishti detectors:

| Injector | Anomaly type | Construction | Expected detector |
|---|---|---|---|
| `inject_cost_anomalies` | cost_inflation | ~2× the 25L band median (≈ +100% deviation; trigger +40%) | COST_ANOMALY |
| `inject_duplicate_anomalies` | duplicate_similar_work | near-twin **pairs**: near-identical description, cost within 1%, ~15 m apart, overlapping windows | DUPLICATE |
| `inject_delay_anomalies` | abnormal_duration | sanctioned 500 d ago vs 300 d expected, minimal progress (delay ≈ +200 d; trigger 90 d) | DELAY |
| `inject_spending_pattern_anomalies` | unusual_spending_pattern | expenditure 95–99% of sanctioned while physical progress 10–20% (joint IF feature outlier) | ML_ANOMALY |
| `inject_pattern_anomalies` | suspicious_attribute_combination | guideline-prohibited descriptions (temple / statue / office building) + one trust-implemented row | COMPLIANCE |

Every injected record carries:

```json
{
  "record_id": "SYA-C0021",
  "ground_truth": "anomaly",
  "injected": true,
  "anomaly_type": "cost_inflation",
  "injection_id": "inj-001",
  "original_record_id": "SYB-0007",
  "expected_detector": "COST_ANOMALY"
}
```

Clean records: `{"ground_truth": "normal", "injected": false, …}`.

The full dataset (baseline + injected) is serialized to CSV and pushed
through the **real** ingestion path and the **unmodified** detection run
(quality → metrics → peers → rules → compliance → agency concentration →
NLP duplicates → Isolation Forest → fusion). Nothing is short-circuited;
thresholds are the production defaults.

## 4. Ground truth & evaluation protocol

Per record (binary: "injected anomaly" = positive):

| | Flagged by pipeline | Not flagged |
|---|---|---|
| **Injected** | TP | FN |
| **Baseline (normal)** | FP | TN |

A record counts as flagged when it carries ≥1 non-data-quality signal.
`hit_expected_detector` additionally records whether the *mapped* detector
fired — kept separate so the headline metrics measure "flagged for
investigation", not "matched the cheat sheet". False positives are listed
per scenario in the artifact (never silently discarded).

Per-type metrics reuse the standard formulation with the clean rows as the
shared negatives pool.

## 5. Metrics

```
Precision = TP / (TP + FP)          Recall = TP / (TP + FN)
F1 = 2·P·R / (P + R)                FPR = FP / (FP + TN)
Detection rate = TP / total injected
```

Zero-denominator rule: a metric is `null` when its denominator is 0
(undefined — never fabricated as 0 or 1). Scenario A reports `null`
precision/recall/F1 because it injects nothing; that is honest output, not
a bug.

## 6. Overall results (seed 26102, all four scenarios)

**TP 60 · FP 8 · TN 232 · FN 0**

| Metric | Value |
|---|---|
| Precision | **0.8824** |
| Recall | **1.0000** |
| F1 | **0.9375** |
| False-positive rate | **0.0333** |
| Detection rate | **1.0000** |

## 7. Scenario results

| Scenario | Records | Injected | TP | FP | TN | FN | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A — clean baseline | 60 | 0 | 0 | 8 | 52 | 0 | null | null | null | 0.1333 |
| B — small injection | 71 | 11 | 11 | 0 | 60 | 0 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| C — moderate injection | 80 | 20 | 20 | 0 | 60 | 0 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| D — mixed types | 89 | 29 | 29 | 0 | 60 | 0 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

## 8. Per-anomaly results (Scenario D — all five types)

| Anomaly Type | Injected | Detected | Missed | Precision | Recall | F1 | Expected-detector hits |
|---|---:|---:|---:|---:|---:|---:|---:|
| cost_inflation | 6 | 6 | 0 | 1.0000 | 1.0000 | 1.0000 | 6/6 |
| duplicate_similar_work | 6 | 6 | 0 | 1.0000 | 1.0000 | 1.0000 | 6/6 |
| abnormal_duration | 6 | 6 | 0 | 1.0000 | 1.0000 | 1.0000 | 6/6 |
| unusual_spending_pattern | 6 | 6 | 0 | 1.0000 | 1.0000 | 1.0000 | 6/6 |
| suspicious_attribute_combination | 5 | 5 | 0 | 1.0000 | 1.0000 | 1.0000 | 5/5 |

In every scenario, each injected work was flagged **by its expected
detector** (e.g. `unusual_spending_pattern` rows via ML_ANOMALY), not merely
by an unrelated signal.

## 9. Confusion matrix (all scenarios pooled)

```text
                    Predicted
                 Flagged   Not flagged
Actual Injected    60          0
       Normal       8        232
```

## 10. False positives & false negatives

**False negatives: 0.** Every injected anomaly across all scenarios was
flagged.

**False positives: 8** — all in Scenario A's clean baseline, all
`ML_ANOMALY` at **LOW priority (score 1.5)**: `SYB-0010, SYB-0011,
SYB-0018, SYB-0025, SYB-0028, SYB-0040, SYB-0049, SYB-0056`.

Mechanism (honest finding, kept on purpose): the IF feature matrix has one
column (`duplicate_score`) that is NaN for every record in a
no-duplicates dataset; the engine's median-impute fallback fills such
columns with 0, and rows with NaN elsewhere get that column as their only
distinguishing feature, producing borderline scores just under the −0.05
trigger. No false positive reached MEDIUM priority or above, and none of
the rule/ compliance/ NLP engines produced false positives.

## 11. Limitations

1. **Synthetic ground truth only.** We injected the anomalies ourselves and
   evaluate against our own labels. **No real-world fraud-detection
   accuracy is claimed or measurable** — the underlying CAG/MPLADS
   work-level records are not publicly available.
2. **Deliberate detectability.** Injections are built to match documented
   detector definitions (e.g. +100% cost vs a +40% trigger). These are
   *capability* checks at clear separations, not estimates of performance
   on subtle real-world deviations.
3. **Single district, single categorical layout.** Peer benchmarking
   (district+category, ≥5 peers) is exercised only in that shape.
4. **Baseline calibration is part of the experiment.** The clean bands were
   tuned so Scenario A is quiet; the first attempt produced
   AGENCY_CONCENTRATION on all rows and 328 duplicate-pair false signals
   (see §2). The reported FPR is therefore conditional on a baseline that
   respects the platform's operating assumptions.
5. **Isolation Forest quirk.** The all-NaN duplicate-score imputation (§10)
   is a real engine characteristic surfaced by this benchmark; it is
   reported, not patched here.
6. **No threshold tuning was performed** — production defaults
   (`rules-v1` / `iforest-v1`) were used throughout, so no
   baseline-vs-tuned comparison exists to report.
7. **Perfect recall is expected, not celebrated**: all five anomaly types
   have deterministic triggers with wide margins. The informative numbers
   are the FPR and the FP anatomy.

## 12. Reproducing

```bash
cd backend
py scripts/run_synthetic_validation.py                  # seed 26102 (default)
py scripts/run_synthetic_validation.py --seed 12345     # any seed
py scripts/run_synthetic_validation.py --out other.json # custom artifact path
```

The benchmark is deterministic: two runs with the same seed produce
byte-identical reports apart from the `generated_at` timestamp (verified
during development). API equivalent: `GET /api/v1/validation/synthetic`.
Automated tests: `backend/tests/test_synthetic_validation.py` (19 tests).
