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

1. Import dataset.
2. Store source metadata.
3. Normalize records.
4. Run quality validation.
5. Calculate derived features.
6. Execute rule, ML and NLP detectors.
7. Build peer groups.
8. Fuse signals.
9. Persist investigation priority.
10. Display in Command Center and queue.
11. Create case from a project.
12. Record officer actions.
13. Generate report.
14. Capture feedback.

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
