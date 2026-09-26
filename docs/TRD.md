# Drishti — Technical Requirements Document

## 1. Technical Objective

Build a modular web application that transforms MPLADS/e-SAKSHI-style data into explainable investigation intelligence.

Recommended stack from the solution brief:
- **Frontend:** React + TypeScript
- **UI:** Tailwind CSS + shadcn/ui
- **Charts:** Recharts
- **Maps:** Leaflet
- **Backend:** FastAPI + Python
- **ORM:** SQLAlchemy
- **Validation:** Pydantic
- **Database:** PostgreSQL
- **ML:** Pandas, NumPy, scikit-learn
- **NLP:** TF-IDF + cosine similarity; Sentence Transformers optional
- **Reports:** ReportLab

SQLite may be used temporarily if deployment speed becomes a constraint.

## 2. Functional Technical Requirements

### TR-01 Data ingestion
The API shall accept a normalized CSV/dataset and map source columns into a canonical project schema.

### TR-02 Provenance
Every imported dataset shall have:
- source label
- ingestion timestamp
- dataset version
- synthetic/official/demo classification
- row count
- validation summary

### TR-03 Validation
Validation shall run before anomaly detection.

Minimum rules:
- required identifiers present
- dates logically ordered
- expenditure <= sanctioned amount unless explicitly marked as an exception
- progress values within expected bounds
- numeric fields parseable
- duplicate work IDs detected

### TR-04 Derived metrics
The backend shall calculate:
- cost deviation
- expenditure ratio
- financial/physical gap
- elapsed days
- expected duration
- delay days
- peer percentile
- peer median
- duplicate candidate score
- ML anomaly score
- agency concentration where data exists

### TR-05 Rule engine
Rules must be independently executable and return structured evidence.

Example:
```json
{
  "rule_code": "FIN_PHYS_GAP",
  "triggered": true,
  "severity": "high",
  "evidence": {
    "financial_progress": 84,
    "physical_progress": 32,
    "gap": 52
  }
}
```

### TR-06 ML engine
Isolation Forest must run against a stable feature set. The ML result is one evidence signal and must not directly become a fraud verdict.

### TR-07 NLP duplicate detection
Normalize descriptions before comparison. Use TF-IDF/cosine similarity for the MVP. Optionally add sentence embeddings later.

### TR-08 Peer benchmarking
Peer groups should be configurable using combinations of:
- district
- category
- sector
- financial year
- approximate project size

### TR-09 Evidence fusion
The fusion layer shall preserve individual signals and calculate a transparent priority using configured weights/logic.

### TR-10 API
All frontend functionality shall use typed REST APIs rather than direct database access.

### TR-11 Auditability
Important state transitions and officer actions shall be recorded.

### TR-12 Reporting
Reports must be generated from persisted case/project evidence and include a generation timestamp and report identifier.

## 3. Non-Functional Requirements

### Performance
- Dashboard API should return common aggregate views quickly on demo-sized data.
- Filtering should be server-side for large datasets.
- ML/NLP processing should run asynchronously for large imports.

### Reliability
- Failed ingestion should not partially corrupt the dataset.
- Detection jobs should have explicit status: queued, running, completed, failed.
- Errors must be visible to administrators without exposing stack traces to normal users.

### Security
- Authentication should be required for non-demo deployments.
- Role-based authorization should separate administrator, investigator and supervisor capabilities.
- Sensitive data should not appear in application logs.
- Database credentials must be environment variables/secrets.

### Explainability
Every investigation priority must be decomposable into signals and evidence.

### Reproducibility
A detection run should be tied to:
- dataset version
- rule version
- model version
- execution timestamp

## 4. Suggested API Surface

### Data
`POST /api/v1/datasets/import`  
`GET /api/v1/datasets`  
`GET /api/v1/datasets/{id}/quality`

### Projects
`GET /api/v1/projects`  
`GET /api/v1/projects/{id}`  
`GET /api/v1/projects/{id}/signals`  
`GET /api/v1/projects/{id}/related`

### Analytics
`GET /api/v1/dashboard/summary`  
`GET /api/v1/risk/distribution`  
`GET /api/v1/benchmarks`  
`POST /api/v1/detection/runs`

### Cases
`POST /api/v1/cases`  
`GET /api/v1/cases`  
`GET /api/v1/cases/{id}`  
`PATCH /api/v1/cases/{id}`  
`POST /api/v1/cases/{id}/feedback`

### Reports
`POST /api/v1/cases/{id}/report`  
`GET /api/v1/reports/{id}`

## 5. Detection Pipeline

```text
RAW DATA
  ↓
SCHEMA MAPPING
  ↓
VALIDATION + NORMALIZATION
  ↓
DERIVED METRICS
  ↓
┌───────────────┬──────────────┬───────────────┐
│ RULE ENGINE   │ ML ENGINE    │ NLP ENGINE    │
└───────────────┴──────────────┴───────────────┘
  ↓
PEER BENCHMARKING
  ↓
EVIDENCE FUSION
  ↓
INVESTIGATION PRIORITY
  ↓
CASE / REPORT
```

## 6. Environment Configuration

Minimum:
```text
DATABASE_URL=
APP_ENV=
SECRET_KEY=
CORS_ORIGINS=
MODEL_VERSION=
RULESET_VERSION=
REPORT_STORAGE_PATH=
```

## 7. Testing Requirements

### Unit tests
- validation rules
- derived metric calculations
- peer calculations
- duplicate scoring
- evidence fusion
- case state transitions

### Integration tests
- dataset import
- detection run
- project details
- case creation
- report generation

### UI tests
- dashboard filtering
- queue filtering
- project investigation
- case creation
- report download

### Data tests
Maintain fixed synthetic fixtures for known anomaly scenarios.

### CAG-grounded validation tests (docs/CAG_VALIDATION.md)
- fixture provenance: every fixture work `CAGV-`-prefixed, dataset always
  `is_synthetic=True` with `synthetic_cag_pattern` source-label marker
- expected pattern characteristics survive ingestion
- detector execution against the unmodified pipeline (deterministic
  reference date; thresholds never modified)
- honest result generation: FLAGGED / PARTIAL / MISSED reported as
  measured; data-unavailable patterns reported NOT_VALIDATABLE, never faked
- language discipline: no claim of detecting real CAG cases, no accuracy
  metrics against unavailable real data
- API surface: `/api/v1/validation/cag` and `…/summary`

## 8. Deployment

Preferred architecture:
- React static frontend
- FastAPI backend
- PostgreSQL database
- object/file storage for generated reports if required

For a hackathon demo, the architecture may be simplified, but service boundaries should remain clear so deployment can be expanded later.
