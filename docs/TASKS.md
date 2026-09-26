# Drishti — Implementation Tasks

## Sprint Objective

Deliver a stable SIH MVP in three days with the complete path:

**Data → Detection → Evidence → Priority → Investigation → Case → Report**

## Day 1 — Data + Intelligence

### P0 — Repository setup
- [ ] Create frontend/backend structure.
- [ ] Configure environment variables.
- [ ] Configure PostgreSQL/SQLite fallback.
- [ ] Add linting and formatting.
- [ ] Add base README.

### P0 — Dataset pipeline
- [ ] Obtain/use permitted MPLADS dataset.
- [ ] Create canonical column mapping.
- [ ] Build ingestion endpoint.
- [ ] Store dataset metadata.
- [ ] Mark official vs synthetic/demo data.
- [ ] Implement validation report.
- [ ] Normalize dates, currency and percentages.

### P0 — Data quality
- [ ] Missing mandatory fields.
- [ ] Invalid date ordering.
- [ ] Expenditure > sanctioned amount.
- [ ] Progress > 100%.
- [ ] Duplicate work IDs.
- [ ] Invalid numeric values.

### P0 — Derived metrics
- [ ] Cost deviation.
- [ ] Expenditure ratio.
- [ ] Financial/physical gap.
- [ ] Elapsed days.
- [ ] Expected duration.
- [ ] Delay days.
- [ ] Peer percentile.

### P0 — Detection
- [ ] Cost anomaly.
- [ ] Financial/physical mismatch.
- [ ] Delay detection.
- [ ] Duplicate candidate detection.
- [ ] Isolation Forest.
- [ ] Peer benchmarking.
- [ ] Evidence records.
- [ ] Evidence fusion.
- [ ] Investigation priority.

### P1 — Extended analytics
- [ ] Agency/contractor concentration.
- [ ] Risk Replay.
- [ ] Configurable rule definitions.

## Day 2 — Product

### P0 — Command Center
- [ ] Summary strip.
- [ ] Risk distribution.
- [ ] Geography view.
- [ ] Top investigation queue.
- [ ] Global filters.

### P0 — Investigation Queue
- [ ] Table.
- [ ] Priority sorting.
- [ ] Signal filters.
- [ ] Geography filters.
- [ ] Status filters.
- [ ] Open-project action.

### P0 — Project Intelligence
- [ ] Project header.
- [ ] Signal summary.
- [ ] Evidence details.
- [ ] Peer comparison.
- [ ] Related projects.
- [ ] Timeline.
- [ ] Recommended verification.

### P0 — Case Management
- [ ] Create case.
- [ ] Assignment.
- [ ] Status transitions.
- [ ] Officer notes.
- [ ] Evidence references.
- [ ] Feedback classification.

### P0 — Report
- [ ] Report preview.
- [ ] PDF generation.
- [ ] Report metadata.
- [ ] Download/export.

## Day 3 — Differentiation + Polish

### P0
- [ ] Rule → Evidence → Action presentation.
- [ ] Multi-signal convergence explanation.
- [ ] Clear provenance labels.
- [ ] Human-in-the-loop language.
- [ ] Empty/loading/error states.
- [ ] Demo scenario verification.
- [ ] Deployment.
- [ ] README.
- [ ] Screenshots.
- [ ] PPT architecture diagram.

### P1
- [ ] Risk Replay.
- [x] CAG-informed rule references.
- [x] CAG-grounded pattern validation layer (docs/CAG_VALIDATION.md):
      verified CAG findings → pattern catalog → synthetic reproduction →
      unmodified detector run → honest per-pattern results; 25 automated
      tests; Evidence & Validation screen.
- [x] Synthetic model validation framework (docs/SYNTHETIC_VALIDATION.md):
      deterministic injection engine with ground truth, scenario matrix,
      precision/recall/F1/FPR/confusion metrics, machine-readable artifact,
      CLI runner + API + Synthetic Model Validation panel; 19 automated tests.
- [x] Contextual duplicate-candidate validation ("similarity ≠ duplication"):
      TF-IDF kept as candidate generator; geospatial + vendor-overlap gates,
      contextual confidence bands, evidence rows, confidence-gated severity
      and fusion weight; migration d8e9f0a1b2c3; 22 automated tests
      (tests/test_duplicate_context.py) incl. boilerplate-FP matrix and
      MPL-10281 flagship verification.
- [ ] Officer feedback analytics.
- [ ] Compliance dashboard.

## Testing Checklist

### Backend
- [ ] Unit tests for every detection rule.
- [x] CAG validation tests (fixture provenance, detector execution, honest
      result generation, language discipline, API surface).
- [x] Synthetic validation tests (determinism, injection correctness,
      ground truth, metric math incl. toy dataset, zero-division, JSON
      serialization, end-to-end scenario, DB cleanup).
- [ ] Unit tests for fusion.
- [ ] API integration tests.
- [ ] Dataset fixture tests.
- [ ] Case state transition tests.
- [ ] Report generation test.

### Frontend
- [ ] Dashboard loads.
- [ ] Filters work.
- [ ] Queue opens project.
- [ ] Project evidence expands.
- [ ] Case creation works.
- [ ] Report generation works.
- [ ] Mobile/tablet degradation is acceptable.

## Definition of Done

A task is done only when:
1. It works with the canonical demo dataset.
2. Its output is explainable.
3. Errors have a visible state.
4. It does not silently fabricate missing data.
5. It is connected to the main user flow.
6. It has at least a basic test or reproducible manual test.
