# Drishti — System Architecture

## 1. Architecture Philosophy

Drishti is organized around an **evidence pipeline**, not a dashboard pipeline.

```text
DATA
 ↓
QUALITY
 ↓
SIGNALS
 ↓
CONTEXT
 ↓
EVIDENCE FUSION
 ↓
PRIORITIZATION
 ↓
INVESTIGATION
 ↓
DOCUMENTATION
 ↓
FEEDBACK
```

## 2. High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                       DATA SOURCES                           │
│            MPLADS / e-SAKSHI / CSV / Demo Data              │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    INGESTION SERVICE                         │
│     Schema Mapping • Normalization • Provenance              │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    DATA QUALITY LAYER                        │
│ Validation • Deduplication • Missing Data • Consistency     │
└───────────────┬───────────────────┬──────────────────────────┘
                │                   │
                ▼                   ▼
      ┌────────────────┐   ┌──────────────────┐
      │ RULE ENGINE    │   │ ANALYTICS/ML     │
      │ Compliance     │   │ Isolation Forest │
      │ Delay          │   │ Feature scoring  │
      │ Progress gap   │   └────────┬─────────┘
      │ Cost checks    │            │
      └───────┬────────┘            │
              │                     │
              └──────────┬──────────┘
                         ▼
                ┌─────────────────┐
                │ NLP ENGINE      │
                │ Similarity /    │
                │ Duplicate pairs │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ PEER CONTEXT    │
                │ District        │
                │ Category        │
                │ Sector / Year   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ EVIDENCE FUSION │
                │ Explainable     │
                │ multi-signal    │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ PRIORITIZATION  │
                └────────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Command Center   Queue       Alerts
                         │
                         ▼
                ┌─────────────────┐
                │ INVESTIGATION   │
                │ WORKSPACE       │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ CASE MANAGEMENT │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ REPORT ENGINE   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ OFFICER FEEDBACK│
                └─────────────────┘
```

## 3. Frontend Architecture

```text
src/
├── app/
├── pages/
│   ├── CommandCenter/
│   ├── InvestigationQueue/
│   ├── ProjectIntelligence/
│   ├── Cases/
│   └── Reports/
├── components/
│   ├── data/
│   ├── evidence/
│   ├── maps/
│   └── charts/
├── features/
│   ├── projects/
│   ├── signals/
│   ├── cases/
│   └── reports/
├── services/
├── hooks/
├── types/
└── styles/
```

## 4. Backend Architecture

```text
app/
├── main.py
├── api/
├── models/
├── schemas/
├── services/
│   ├── ingestion/
│   ├── quality/
│   ├── detection/
│   ├── benchmarking/
│   ├── fusion/
│   ├── cases/
│   └── reports/
├── ml/
├── nlp/
├── rules/
├── db/
└── core/
```

The service layer should contain business logic. API routes should remain thin.

## 5. Detection Modules

### Rule engine
Deterministic checks:
- financial/physical mismatch
- delay
- cost threshold/context
- data-quality exceptions
- compliance checks

### ML engine
Isolation Forest over engineered numeric features.

### NLP engine
Description normalization and similarity comparison.

### Benchmark engine
Calculates peer distributions and contextual statistics.

### Fusion engine
Combines evidence while retaining each source signal.

## 6. Evidence Model

Every signal should contain:

```text
signal_id
project_id
signal_type
severity
triggered
observed_value
reference_value
difference
explanation
source_rule_or_model
created_at
```

This is the foundation of explainability.

## 7. Data Flow

1. Import dataset (CSV/XLSX upload; type detected deterministically from
   source columns or forced via `dataset_type`).
2. Store source metadata and provenance (source name/type, file name,
   SHA-256 hash, detected column mapping, retrieval timestamp).
3. Normalize records per dataset type (MP allocation / scheme aggregate /
   work-level) with explicit unit handling for monetary values.
4. Run per-row validation; record every issue (row, field, rule, severity,
   message, observed value). ERROR rows are excluded from persistence but
   preserved in `validation_issue`; WARNING/INFO rows import alongside
   their issues (partial validity).
5. Compute the deterministic quality status (GOOD / ACCEPTABLE / DEGRADED /
   FAILED) with plain-language reasons.
6. For work-level datasets: calculate derived features, execute rule, ML
   and NLP detectors, build peer groups, fuse signals, persist
   investigation priority.
7. Display datasets, quality reports and type-safe records in the Data
   screen; MP allocation rows are never reshaped into works.
8. Display intelligence surfaces (Command Center, queue, project
   intelligence) for work-level data.
9. Create case from a project.
10. Record officer actions.
11. Generate report.
12. Capture feedback.

## 7a. Ingestion Pipeline (Prompt 3)

```text
backend/app/services/ingestion/
├── parsers.py        # CSV/XLSX → headers + rows; explicit user-safe errors
├── registry.py       # source field registry: per-schema column mappings,
│                     # deterministic detection (no ML/LLM), provenance record
├── normalizers.py    # currency+unit, counts, percentages, text, nulls, dates
├── validation.py     # per-type validators, ValidationReport, quality scale
└── orchestrator.py   # parse → detect → map → normalize → validate →
                      # persist (partial validity) → quality → provenance
```

Adding a new official export = adding a `SourceSchema` entry to the
registry, not rewriting the engine. Duplicate uploads are rejected via
SHA-256 file hash. Synthetic fixtures under `backend/app/data/fixtures/`
flow through the same pipeline and are always labelled `is_synthetic=True`.

## 8. Architecture Decisions

### PostgreSQL
Chosen for relational project/case/evidence relationships and future scale.

### FastAPI
Provides typed, lightweight APIs and fits Python analytics/ML components.

### React + TypeScript
Supports a structured operational interface and typed frontend contracts.

### Separate evidence records
Avoid storing only a single risk number. Evidence needs to remain inspectable.

## 9. Future Extension Points

The architecture should allow adding:
- satellite verification
- computer vision
- document intelligence
- graph analytics
- predictive models
- LLM investigation copilot

without rewriting the case-management layer.
