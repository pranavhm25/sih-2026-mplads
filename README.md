# Drishti — MPLADS Risk Intelligence & Investigation Platform

**Smart India Hackathon 2026 · Problem Statement SIH26102 · Theme: Smart Automation · Team Codeholics**

Drishti is an **investigation-first decision-support platform** for the Member of Parliament Local Area Development Scheme (MPLADS). It ingests available MPLADS data, detects potential irregularities, explains the evidence behind every signal, prioritizes works for human investigation, and manages the resulting cases through to audit-ready reports.

> **AI FLAG ≠ FRAUD**
>
> Drishti identifies potential irregularities and prioritizes investigations. It never declares fraud. Authorized officials review the evidence and determine the final outcome — including explicitly clearing a flag when the investigation does not substantiate the concern.

**Live**

| | |
|---|---|
| Application | https://drishti-mplads-codeholics.vercel.app |
| API health | https://drishti-backend-h2c8.onrender.com/api/v1/health |
| API docs (Swagger) | https://drishti-backend-h2c8.onrender.com/docs |
| Source | https://github.com/pranavhm25/sih-2026-mplads |

Demo sign-in: `ministry@drishti.demo` / `drishti-demo` (see [Demo accounts](#demo-accounts)). Hosted on free tiers — the backend sleeps when idle; see [Demo reliability](#demo-reliability).

---

## 1. Overview

MPLADS administrators and auditors must monitor thousands of works with limited staff. Today that review is largely manual: unusual cost patterns, stalled works and suspiciously similar projects surface only when someone happens to notice them, and there is no shared, auditable trail from a suspicion to a concluded investigation.

Drishti addresses this with a pipeline: **DATA → DETECT → EXPLAIN → PRIORITIZE → INVESTIGATE → DOCUMENT**. It ingests official and controlled synthetic data, derives comparable metrics, runs an explainable detection layer (deterministic rules, categorical compliance checks, NLP duplicate candidates and an unsupervised Isolation Forest), fuses the independent evidence into an investigation priority, and carries each case through a governed human lifecycle with a tamper-evident audit trail and PDF reporting.

Three principles are enforced in code, not just prose:

- **Every number is traceable.** Signals carry observed value, reference, calculation and threshold. Missing data renders as "not reported" — never estimated.
- **Similarity ≠ duplication; unusualness ≠ wrongdoing.** Text-only duplicate candidates and statistical outliers are down-weighted, labeled as indicators, and always routed to humans.
- **Cleared ≠ deleted.** An investigation that does not substantiate a flag records *why*, while the original AI evidence remains preserved.

## 2. The Problem

SIH26102 asks for smart automation supporting MPLADS oversight — detecting potential irregularities and strengthening the evidence trail of scheme implementation. The operational reality the problem statement describes:

- Work-level records are voluminous and reviewed manually; systematic cross-project comparison is impractical at scale.
- Unusual patterns — cost deviation from comparable works, financial progress far ahead of physical progress, abnormal delays — are exactly the things humans miss when reviewing row by row.
- Similar or duplicated works are hard to spot across constituencies and years.
- Even where a concern exists, prioritization is informal: which of 5,000 works should an investigator open first, and why?
- Reviews lack a durable, auditable record: what was flagged, what evidence was considered, who decided, and on what basis.

## 3. The Solution

```text
DATA (official import / controlled fixture)
  ↓  ingestion: schema mapping, normalization, provenance
VALIDATION  (per-row issue reporting, deterministic quality grade)
  ↓
DETECTION  (rules · compliance catalog · NLP duplicates · Isolation Forest)
  ↓
CORRELATION  (duplicate candidates + agency concentration clusters)
  ↓
RISK PRIORITIZATION  (explainable evidence fusion)
  ↓
HUMAN INVESTIGATION  (governed case lifecycle, AI flag ≠ fraud)
  ↓
EVIDENCE & DECISION  (notes, outcome, structured reason)
  ↓
AUDIT REPORT  (PDF, tamper-evident event chain)
```

Drishti is an intelligence and investigation layer over available MPLADS data — not a transaction system, not a replacement for eSAKSHI, and not a fraud classifier.

## 4. Why Drishti

| Capability | Drishti |
|---|---|
| Data ingestion | Official CSV/XLSX imports with schema detection, column mapping, unit handling and SHA-256 dedup; one-click synthetic fixtures |
| Data quality | Per-row validation issues (row, field, rule, severity) and deterministic GOOD/ACCEPTABLE/DEGRADED/FAILED grades with plain-language reasons |
| Anomaly detection | Deterministic rules (cost, financial/physical gap, delay) with visible thresholds; unsupervised Isolation Forest unusualness |
| Similar-work detection | Two-stage duplicate-candidate pipeline: TF-IDF generation + contextual validation (geo, vendor, category/time) |
| Cross-project analysis | Peer benchmarking by district+category; agency concentration by district |
| Evidence explanation | Every signal persists observed value, reference, calculation, threshold and recommended verification |
| Risk prioritization | Weighted evidence fusion with severity multipliers, convergence bonus and full score decomposition |
| Investigation cases | Governed lifecycle with role-scoped views, officer assignment and notes |
| Human verification | Mandatory outcome + structured reason on closure; reopening path; "AI FLAG ≠ FRAUD" enforced in UI and API |
| Audit trail | Hash-linked, tamper-evident case event chain (actor, timestamp, transitions, outcome metadata) |
| Reports | Per-case PDF including original AI evidence, investigation actions, outcome and audit summary |
| Validation | CAG-grounded pattern validation, controlled synthetic injection benchmark (reproducible artifact), scale benchmark |

## 5. Key Features

### Command Center
Portfolio summary, geographic distribution map (Leaflet markers colored by priority), district attention view, priority distribution and the investigate-first queue. If the backend is waking, the center shows a bounded "backend is starting" state instead of an error.

### Data & Provenance
Import official CSV/XLSX exports, inspect per-dataset quality, browse row-level validation issues, reseed the demo dataset, and view the provenance label (OFFICIAL / DERIVED / SYNTHETIC) attached to every dataset and derived row.

### Detection Engine
Rule engine with peer-context thresholds; categorical compliance pack mapped from documented CAG irregularity patterns; agency concentration. All thresholds are documented constants (`backend/app/core/constants.py`), not magic numbers.

### Duplicate Detection
Two-stage contextual pipeline (§8). Candidates are output for human verification — never a duplication verdict. Confidence bands drive severity and fusion weight.

### Investigation Queue
Dense work register filtered by priority, signal type and state, with one-click case creation.

### Project Intelligence
The evidence ledger per work: signal → observed → reference → delta, expandable to rule logic and raw evidence; peer benchmark (or an explicit "insufficient comparable projects" notice); duplicate candidates with contextual columns; timeline; verification checklist; case panel.

### Case Management
State machine with centrally enforced transitions; officer assignment; investigator notes; closure requiring resolution type, structured reason category and free-text explanation; supervisor reopen path.

### Evidence & Audit Trail
Every status change persists an event (case, previous status, new status, actor, timestamp, outcome metadata) into a hash-linked chain. AI-generated signals are immutable once written — no case action can alter them.

### Reports
ReportLab PDF per case: original detected signals and evidence (always preserved, including for cleared cases), investigation notes, human outcome with reason, and the audit trail.

### Validation
CAG-grounded pattern validation (§9) and the synthetic injection benchmark (§10), both exposed in the UI and reproducible from the CLI.

### Demo Resilience
Liveness and readiness endpoints, GET-only bounded retry layer, waking-backend UI gate, pre-warm and demo-check scripts, and a runbook (§19, §D below in repository docs: `docs/DEMO_RUNBOOK.md`).

## 6. End-to-End Workflow

```mermaid
flowchart TD
    A[Ingest: official import / synthetic fixture] --> B[Clean & validate: row issues + quality grade]
    B --> C[Derive metrics: gap, delay, expenditure ratio, peer stats]
    C --> D[Detect: rules · compliance · duplicates · Isolation Forest]
    D --> E[Correlate: contextual duplicate validation, agency concentration]
    E --> F[Prioritize: explainable evidence fusion]
    F --> G[Investigate: open case, assign officer, review evidence]
    G --> H{Human outcome}
    H -->|substantiated| I[Resolved - classification recorded]
    I -->|higher authority| J[Escalated]
    H -->|evidence does not substantiate| K[Closed - Not Substantiated + structured reason]
    J --> L[Audit report PDF + tamper-evident trail]
    I --> L
    K --> L
    L --> M[Officer feedback feeds validation summary]
```

Officer feedback (confirmed concern / false positive / needs verification) is recorded on cases and aggregated into the validation summary endpoint — a closed learning loop, used for calibration review, not for auto-retraining.

## 7. Detection Methodology

### Rule Engine

Deterministic, peer-context rules (`backend/app/rules/engine.py`). Peer groups are benchmark groups by district + category; groups with fewer than six members are skipped and the UI reports "insufficient comparable projects" rather than fabricating a benchmark. Thresholds (documented constants, configurable):

| Rule | Trigger | High severity | Signal |
|---|---|---|---|
| Cost anomaly | ≥ 40% above peer median sanctioned cost | ≥ 60% | `COST_ANOMALY` |
| Financial/physical gap | ≥ 25 percentage points | ≥ 40 pp | `FIN_PHYS_GAP` |
| Delay | ≥ 90 days beyond expected duration | ≥ 180 days | `DELAY` |
| Compliance indicators | description matches cataloged guideline pattern | per catalog | `COMPLIANCE` |

Each rule writes structured evidence: observed value, reference value, the exact calculation, the threshold, provenance, and a recommended verification step. Rules record that an observed value differs from a reference — never wrongdoing.

### Isolation Forest

Unsupervised anomaly detection over five documented features (cost ratio to peer median, financial–physical gap, delay days, expenditure ratio, duplicate score). Output is presented strictly as *statistical unusualness* — never a fraud probability. Runs are deterministic (`random_state=26102`, fixed reference date); rows with missing features are excluded from scoring rather than imputed with invented values.

### Evidence Fusion

Signals from independent engines are combined into an investigation priority:

- Per-signal weight (gap 3.0, cost 3.0, compliance 3.5, duplicate 2.5, delay 2.0, ML 1.5, agency concentration 1.5, data quality 1.0) × severity multiplier (LOW 0.5 → CRITICAL 2.0).
- Contextual gating: a duplicate candidate with low/unavailable contextual confidence contributes only 60% of its weight — textual similarity alone cannot drive priority.
- Convergence bonus: +1.5 when two or more independent source engines (rule/ML/NLP) agree on the same work.
- Priority bands: < 2.0 LOW · < 4.5 MEDIUM · < 7.0 HIGH · ≥ 7.0 CRITICAL.

The decomposition is always preserved: the UI shows each signal's weighted contribution and the reasons, not just the score.

### Risk Prioritization

The fused score orders the investigation queue. It is an *evidence-weighted attention score*: transparent, threshold-banded, and reviewed by humans — not a classifier output and not a probability.

## 8. Contextual Duplicate Detection

**Textual similarity alone does not establish duplication.** Generic government work descriptions ("Construction of community hall at Ward N") are naturally similar across thousands of works, so a text-only duplicate rule would drown investigators in false positives.

Drishti's pipeline is deliberately two-stage:

```text
Stage 1 — candidate generation (linguistic only)
  TF-IDF over normalized descriptions (domain stopwords removed)
  → cosine similarity
  → weighted component score: text 0.40 · location 0.25 · cost 0.20
                              · category 0.10 · time 0.05
  → pairs scoring ≥ 0.60 become candidates
        ↓
Stage 2 — contextual validation (independent evidence)
  Geospatial proximity (haversine):  ≤ 50 m strong · ≤ 2,000 m window
  Vendor / implementing-agency token overlap
  Cost, category and time agreement
  → contextual confidence: HIGH / MEDIUM / LOW / UNAVAILABLE
  (weighted geo 0.55 · vendor 0.30 · context 0.15)
        ↓
Duplicate CANDIDATE for human verification
  — confidence drives severity; weak or contradictory context
    down-weights the signal in fusion (× 0.6)
```

The flagship fixture pair demonstrates the full chain: MPL-10281 and MPL-10412 score **0.87 TF-IDF cosine similarity** (with the production stopword list) and sit **≈ 7 m apart** (computed by haversine from the stored fixture coordinates) with near-identical sanctioned costs, category and implementing agency — contextual confidence HIGH. Both values are computed from the current fixture at detection time, not hardcoded.

## 9. CAG-Grounded Validation

Drishti's categorical compliance checks are anchored to real audit knowledge. **CAG audit reports are used as authoritative references for documented irregularity patterns. Where underlying case-level data is unavailable, representative synthetic fixtures reproduce relevant structural characteristics for detector validation.** No CAG-audited case is ingested as data, and no claim is made that Drishti "detected a real CAG case."

The catalog (`backend/app/data/cag_catalog.py`) is data, not code, and maintains a strict layer discipline:

```text
CAG documented irregularity  (verified source: report number, para, quote)
  ↓
Pattern abstraction          (what structural signature would a detector see?)
  ↓
Drishti detector mapping     (which detector targets the pattern, with what threshold)
  ↓
Representative validation fixture  (synthetic, is_synthetic=True, never presented as real)
  ↓
Detection result             (deterministic run, reported honestly)
```

Currently cataloged: **9 irregularity patterns** mapped to detectors, traceable to **3 verified CAG sources**:

| Source | Report | Note |
|---|---|---|
| CAG-2001-3A | Report 3A of 2001 — Performance Appraisal of MPLADS (period 1993–2000) | Findings quoted via a contemporaneous press summary; report listed on cag.gov.in |
| CAG-2010-31 | Report No. 31 of 2010 — Performance Audit (Civil) of MPLADS (2004-05 to 2008-09) | Executive summary paras 3.2–3.4, 4.2, 6.1–6.3, 7.1 |
| CAG-2025-22 | Report No. 22 of 2025 — Compliance Audit (Civil & Commercial), Union Government | Para 3.1 (p. 49): unfruitful expenditure of ₹62.61 lakh on an MPLADS indoor sports hall |

Patterns that would require data Drishti does not have are explicitly marked **NOT_VALIDATABLE** in the catalog rather than silently dropped. Details: [docs/CAG_VALIDATION.md](docs/CAG_VALIDATION.md).

## 10. Synthetic Validation

A controlled anomaly-injection framework (`backend/app/services/validation/synthetic/`) measures the unmodified detection pipeline against known ground truth: a clean 60-work baseline dataset per scenario, known anomalies injected with recorded ground truth, full-pipeline detection, then confusion-matrix metrics.

**Scenario design (seed 26102, production thresholds, no tuning):**

| Scenario | Baseline | Injections | Purpose |
|---|---|---|---|
| A — clean baseline | 60 | 0 | false-positive behavior |
| B — small injection | 60 | 11 (cost 4, delay 4, pattern 3) | sensitivity |
| C — moderate injection | 60 | 20 (cost, delay, duplicate, spending pattern) | mixed-type detection |
| D — mixed types | 60 | 29 (all five injection types) | stress |

**Results (aggregate across scenarios, from the committed artifact):**

| TP | FP | TN | FN | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|---|---|
| 60 | 8 | 232 | 0 | 0.882 | 1.000 | 0.938 | 0.033 |

Scenarios B, C and D detect every injected anomaly with zero false positives. All 8 false positives occur in the clean-baseline scenario: LOW-severity `ML_ANOMALY` signals arising from the Isolation Forest's median-imputation on all-NaN duplicate-score features. This is documented in the artifact as a known, bounded behavior rather than patched away.

> **These metrics are from controlled synthetic validation and do not represent production-world fraud detection accuracy.**

Reproduce the artifact:

```bash
cd backend
python scripts/run_synthetic_validation.py            # writes docs/synthetic_validation_results.json
```

The committed artifact was verified byte-identical (except timestamp) to a fresh run on the current codebase. Full methodology: [docs/SYNTHETIC_VALIDATION.md](docs/SYNTHETIC_VALIDATION.md).

A separate scale benchmark (`backend/scripts/benchmark_scale.py`, results in `docs/benchmark_result.json`) ingested **110,000 synthetic rows through the full ingestion pipeline in ~103 s (~1,066 rows/s)**, quality grade ACCEPTABLE — demonstrating the pipeline handles realistic dataset sizes.

## 11. Data Reality & Provenance

Every dataset and derived row carries one of three provenance labels:

| Label | Meaning | In this repository |
|---|---|---|
| **OFFICIAL** | Data originating from available official MPLADS/e-SAKSHI sources | Import path for Lok Sabha / Rajya Sabha allocation exports and dashboard aggregates |
| **DERIVED** | Metrics calculated from source data (gap, delay, expenditure ratio, peer statistics) | `project_metrics` rows with versioned derivation provenance |
| **SYNTHETIC** | Controlled fixtures for demonstration and validation | Bundled fixtures, always ingested with `is_synthetic=True` and labeled "Synthetic demo data" in the UI |

**The current public e-SAKSHI dashboard exposes allocation-level exports and scheme aggregates; per-work analytical fields (work-level sanctioned cost, expenditure, progress, dates, coordinates, agency) are not available from the observed public exports.** Drishti's work-level ingestion path is implemented and tested, absent fields are stored as NULL and displayed as "not reported" — they are never fabricated or estimated.

The demonstration dataset is a deterministic synthetic fixture (`random.Random(26102)`, fixed reference date 2026-09-01) constructed to exercise every detector. It is labeled synthetic at every display point and is never presented as real MPLADS data.

Provenance layering is enforced by separate tables:

```text
SOURCE FACT  ≠  DERIVED METRIC  ≠  MODEL OUTPUT  ≠  OFFICER CONCLUSION
(projects)      (project_metrics)  (project_signal)   (investigation_case)
```

## 12. Human-in-the-Loop Governance

An AI flag opens a governed investigation — it never ends one:

```text
AI flag detected
  ↓
OPEN → UNDER_REVIEW → FIELD_VERIFICATION
        ↓                      ↓
   Substantiated          Not Substantiated
        ↓                      ↓
   RESOLVED ─→ ESCALATED      CLOSED
        └────────┬─────────────┘
        (supervisor reopen → UNDER_REVIEW)
```

- Transitions are enforced centrally (`CASE_TRANSITIONS`); invalid transitions are rejected by the API with the allowed moves listed.
- **RESOLVED** = the investigation concluded with a recorded classification. **ESCALATED** = the substantiated concern was referred to a higher authority. Both are conclusive states.
- **CLOSED = Not Substantiated**: *the investigation did not substantiate the suspected irregularity.* It is not a fraud verdict, not an innocence verdict, and not a statement that the AI flag was wrong. Closure requires resolution type `NOT_SUBSTANTIATED`, a structured reason category (documentation provided · legitimate implementation delay · data-quality issue · false duplicate candidate · approved variation · contextual exception · other) and a short free-text explanation.
- Every transition writes a case event (previous status, new status, actor, timestamp, outcome metadata) to the hash-linked audit chain.
- **AI-generated signals are immutable.** No case action — including closure — modifies the original detection record; the evidence remains preserved as historical input.
- The UI displays a standing notice: *"AI-generated risk flags require human verification and do not constitute findings of fraud."*

## 13. Flagship Demonstration

The synthetic demo fixture centers on work **MPL-10281**, constructed to exhibit five independent signals that converge in fusion:

| Independent signal | Constructed characteristic |
|---|---|
| Cost anomaly | sanctioned cost well above the peer median for its district/category group |
| Financial/physical gap | 84% financial vs 32% physical progress |
| Delay | far beyond the 365-day expected duration |
| Duplicate candidate | MPL-10412 — 0.87 text similarity, ≈ 7 m away, same category/agency |
| Isolation Forest | statistically unusual multi-feature profile |

A deliberate agency-concentration cluster (Belagavi district, one agency holding the majority of sanctioned value) exercises the `AGENCY_CONCENTRATION` detector, whose trigger is 40% (high at 60%).

The pair then demonstrates the full human loop: a case opened from the flags is investigated and **closed as Not Substantiated (false duplicate candidate)** — the seeded demo case `DRSHY-C-1001` shows the complete audit trail from AI flag to human conclusion, with the original AI evidence intact in the case report.

> This entire scenario is a **synthetic demonstration fixture**. It is not a real MPLADS work, constituency or financial record.

## 14. Architecture

```text
┌────────────────────────────────────────────────────────────┐
│ Frontend  React 18 + TypeScript (strict) + Tailwind CSS    │
│           Leaflet map · Recharts · Vite build              │
└──────────────────────────┬─────────────────────────────────┘
                           │  REST (/api), VITE_API_URL
┌──────────────────────────▼─────────────────────────────────┐
│ FastAPI  — thin routers, {data, meta} envelope             │
│   health · auth · datasets · projects/dashboard · cases    │
│   reports · stakeholders · validation                      │
├────────────────────────────────────────────────────────────┤
│ Services                                                   │
│   ingestion (parsers/normalizers/quality gate)             │
│   detection:  RULES ── ML (Isolation Forest) ── NLP (TF-IDF)│
│               evidence fusion → priorities                 │
│   cases (state machine + hash-linked audit chain)          │
│   reports (PDF)   validation (CAG + synthetic benchmark)   │
├────────────────────────────────────────────────────────────┤
│ SQLAlchemy 2 models ── Alembic migrations                  │
└──────────────────────────┬─────────────────────────────────┘
                           │
              SQLite (demo default) / PostgreSQL
```

Backend layering: `api/` (thin routers) → `services/` (business logic) → `models/` (SQLAlchemy) → `db/`. Detection modules are independently testable; the health-route module is kept free of database imports by contract test.

## 15. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript (strict), Tailwind CSS, Leaflet + react-leaflet, Recharts, Vite |
| Backend | Python, FastAPI, Pydantic v2, Uvicorn |
| Database | SQLAlchemy 2, Alembic migrations; SQLite (demo default), PostgreSQL via `psycopg2-binary` (`DATABASE_URL`) |
| ML | scikit-learn Isolation Forest (unsupervised unusualness only) |
| NLP | TF-IDF + cosine similarity (scikit-learn), haversine geospatial filtering |
| Reports | ReportLab (PDF) |
| Testing | pytest (backend), Vitest + Testing Library (frontend), `tsc --noEmit` |
| Deployment | Docker Compose (local), Render (backend blueprint), Vercel (frontend) |

## 16. Repository Structure

```text
├── backend/
│   ├── app/
│   │   ├── api/            routers: health, auth, datasets, projects, cases, stakeholder, validation
│   │   ├── core/           config, constants (thresholds, state machine), security
│   │   ├── data/           synthetic demo data, CAG pattern catalog, bundled fixtures
│   │   ├── ml/             Isolation Forest engine
│   │   ├── models/         SQLAlchemy models
│   │   ├── nlp/            duplicate-candidate pipeline
│   │   ├── rules/          compliance rule engine
│   │   ├── schemas/        Pydantic request/response models
│   │   └── services/       ingestion, quality, detection, fusion, cases, reports, validation
│   ├── alembic/            migrations
│   ├── scripts/            synthetic validation runner, scale benchmark
│   └── tests/              pytest suite
├── frontend/               React SPA (pages, hooks, services, types)
├── docs/                   PRD, TRD, ARCHITECTURE, BACKEND_SCHEMA, APP_FLOW, DESIGN,
│                           DEMO_RUNBOOK, CAG_VALIDATION, SYNTHETIC_VALIDATION, …
├── scripts/                prewarm-demo.py (pre-warm + demo readiness check)
├── data/                   local data-drop convention (raw/ processed/ — git-ignored)
├── .github/workflows/      optional Render keep-alive (disabled by default)
├── render.yaml             Render backend blueprint
├── docker-compose.yml      local stack (frontend :5317 → nginx, backend :8317)
└── README.md
```

## 17. Quick Start

### Docker (recommended)

```bash
./run.sh                # Linux / macOS
run.bat                 # Windows (cmd)   or:  .\run.ps1  (PowerShell)
docker compose up --build   # directly
./stop.sh               # stop (or docker compose down)
```

Then: app at http://localhost:5317 · Swagger at http://localhost:8317/docs · health at http://localhost:8317/api/v1/health. On first start the backend initializes tables, seeds the deterministic synthetic demo dataset, runs the full detection pipeline and creates the demo scenario case.

### Backend (manual)

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env                # optional; defaults work
python -m alembic upgrade head      # apply migrations
python -m uvicorn app.main:app --reload --port 8317
```

### Frontend (manual)

```bash
cd frontend
npm install
npm run dev          # http://localhost:5317, /api proxied to :8317
```

### Database

SQLite is the demo default (`sqlite:///./drishti.db`). PostgreSQL is a drop-in via `DATABASE_URL` (e.g. `postgresql+psycopg://user:pass@host/drishti`) — the SQLAlchemy layer and migrations are database-agnostic.

## 18. Demo Accounts

The public demo deployment uses intentionally public demo accounts (also seeded in the repository for local runs). **They are demo credentials only** — production deployments disable them via `DEMO_ACCOUNTS_ENABLED=false` and provision real users.

| Account | Role | Password |
|---|---|---|
| `ministry@drishti.demo` | Ministry reviewer | `drishti-demo` |
| `snl@drishti.demo` | State nodal officer (Karnataka) | `drishti-demo` |
| `district@drishti.demo` | District authority | `drishti-demo` |
| `mp@drishti.demo` | Hon'ble MP (demo) | `drishti-demo` |
| `admin@drishti.demo` | Platform admin | `drishti-demo` |

No real credentials, API keys or secrets exist in this repository.

## 19. Demo Reliability

The demo runs on free tiers, and honesty about that is part of the design:

- **Render free tier sleeps the backend** after idle periods; the first request can take an estimated 30–60 s to wake it. (No uptime guarantee is offered or implied.)
- `GET /api/v1/health` — instant liveness, no database touch. `GET /api/v1/health/ready` — readiness: database reachable + demo dataset present; never runs detection.
- **Frontend retry layer**: idempotent GET requests retry with bounded exponential backoff (1/2/4/8/8 s, ~23 s window) on network errors and 502/503/504 only; mutations never auto-retry.
- **Waking-backend gate**: data pages show *"Drishti backend is starting. Retrying connection…"* and auto-recover when readiness returns — the wake never looks like a crash.
- **Pre-warm and check tooling** (stdlib-only):

```bash
python scripts/prewarm-demo.py            # wake the backend and wait for READY
python scripts/prewarm-demo.py check      # verify full demo stack (read-only)
```

- `DEMO_AUTOSEED=true` reseeds demo data on boot; the demo case is created idempotently.
- Measured on the development machine (local, SQLite): cold boot to liveness ≈ 10.7 s, to READY ≈ 12.7 s; warm `/dashboard/summary` ≈ 0.37 s. Full procedures: [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md).
- An optional GitHub Action (`keep-alive`) can ping the backend every 10 minutes to prevent sleeps; it is disabled by default and costs most of the free instance-hour allowance.

## 20. API

Base path `/api/v1`; all responses use a `{ data, meta }` envelope with dataset version and synthetic flag. Interactive docs at **`/docs`** (Swagger UI). 37 endpoints across:

| Group | Highlights |
|---|---|
| Health | `GET /health` (liveness) · `GET /health/ready` (readiness) |
| Dashboard | `GET /dashboard/summary` |
| Projects | `GET /projects` (filters: priority, signal type, state, search, sort) · `GET /projects/{id}` |
| Datasets | `GET /datasets` · `GET /datasets/{id}/quality` · `POST /datasets/import` · `POST /detection/runs` |
| Cases | `GET /cases` · `POST /cases` · `PATCH /cases/{id}` (validated transitions) · `POST /cases/{id}/notes` |
| Evidence & reports | `POST /cases/{id}/evidence` · `POST /cases/{id}/feedback` · `POST /cases/{id}/report` · `GET /reports/{id}/download` |
| Validation | CAG capability report + summary · synthetic benchmark endpoints |
| Stakeholders | role-scoped views (MP / district / state nodal / ministry), alert digest, trends |
| Auth | demo login, session management, audit chain verification |

## 21. Testing & Validation

All counts below are from runs on the current codebase (2026-09-27), not copied from older documentation.

| Suite | Command | Result |
|---|---|---|
| Backend | `cd backend && python -m pytest -q` | **230 passed** (≈ 33 s) |
| Frontend unit | `cd frontend && npx vitest run` | **16 passed** |
| Frontend types | `cd frontend && npx tsc -b --noEmit` | clean |
| Frontend build | `cd frontend && npx vite build` | succeeds |
| Synthetic benchmark | `python scripts/run_synthetic_validation.py` | artifact reproduced byte-identical |

Coverage highlights: CAG validation (25 tests — provenance, honest results, language discipline), duplicate contextual detection (22 — including a boilerplate false-positive matrix and the flagship pair), case lifecycle & NOT_SUBSTANTIATED outcome (20 — transitions, required reasons, audit trail, signal immutability, reports), demo resilience (8 — readiness 200/503, chunked queries, read-only probes), official ingestion, fusion, Isolation Forest unit tests, API integration and report generation.

## 22. Security

### Current prototype
- Secrets only via environment variables; `.env` is git-ignored, `.env.example` contains placeholders. `SECRET_KEY` must be set in any real deployment.
- Demo accounts are publicly documented and disabled by configuration for non-demo use (`DEMO_ACCOUNTS_ENABLED=false`).
- Hash-linked, append-only audit chain for case events; AI signals immutable by design.
- Read-only health/readiness probes and a read-only demo-check script; no destructive operator endpoints.
- CORS is environment-configured (locked to known origins locally; the public demo currently allows all origins to support the hosted frontend — acceptable for a public synthetic-data demo, not for real data).

### Production considerations (not implemented — roadmap)
Role-based access control with government identity (SSO), encryption at rest, government-hosted infrastructure and data residency, secrets management, formal security assessment, and integration with departmental audit controls.

## 23. Limitations

Stated plainly:

- **Public work-level data availability**: per-work financial, progress, geographic and agency fields are not available from the observed public MPLADS/e-SAKSHI exports; the full detection pipeline is exercised on controlled synthetic data until authorized feeds exist.
- **No labeled production fraud dataset**: model quality is measured by synthetic injection, not against real-world outcomes; the reported metrics are not production accuracy.
- **Synthetic validation only**: CAG patterns are validated via representative fixtures reproducing structural characteristics — not on the original case data.
- **Prototype infrastructure**: free-tier hosting, single-node SQLite/PostgreSQL, no HA, no formal security accreditation.
- **Not a production government system**: no eSAKSHI/PFMS integration, no digital-signature or records-management compliance, no departmental workflow integration.
- **Contextual data availability**: vendor identity, sanctioned-variations and groundwork documentation — often decisive in real investigations — are not consistently available to the system.
- Isolation Forest behavior on sparse features (documented LOW-severity false positives in the clean baseline) requires tuning review before real deployment.

## 24. Future Scope

- Authorized e-SAKSHI integration for real work-level data (and PFMS where appropriate), unlocking detection on live data.
- Investigator feedback-driven calibration: threshold review and model evaluation against human outcomes, with the existing feedback aggregation as the foundation.
- Validation on larger, verified datasets; regime-specific peer groups.
- Enhanced geospatial analysis (post-GIS buffer/overlap checks beyond point proximity).
- Longitudinal monitoring: constituency/year trend baselines and repeat-pattern surfacing.
- Production government infrastructure: RBAC/SSO, encryption at rest, data residency, secrets management, security hardening and accreditation.

## 25. Research & References

### Government / domain sources
- MPLADS official portal — https://mplads.gov.in
- MPLADS e-SAKSHI dashboard, MoSPI — https://mplads.mospi.gov.in/digigov/dashboard.html
- CAG of India audit reports — https://cag.gov.in/en/audit-report

### CAG references (as cataloged in `backend/app/data/cag_catalog.py`)
- CAG of India. *Audit Report (Civil) — Performance Appraisal of the Member of Parliament Local Area Development Scheme*, Report No. 3A of 2001 (period 1993–2000). https://cag.gov.in/en/audit-report
- CAG of India. *Report No. 31 of 2010 — Performance Audit of Civil on Member of Parliament Local Area Development Scheme* (period 2004-05 to 2008-09; tabled 18 March 2011). https://cag.gov.in/en/audit-report/details/2341
- CAG of India. *Report No. 22 of 2025 — Compliance Audit (Civil & Commercial), Union Government* — para 3.1 (p. 49), unfruitful expenditure of ₹62.61 lakh on an MPLADS indoor sports hall. https://cag.gov.in/uploads/download_audit_report/2025/Report-No.-22-of-2025_CAO-(Civil)_English-(03-10-2025)-06943aa88578c10.37125079.pdf

### Machine learning
- scikit-learn — `IsolationForest`: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- Liu, F. T., Ting, K. M., Zhou, Z.-H. **"Isolation Forest."** *2008 IEEE International Conference on Data Mining (ICDM 2008)*, pp. 413–422. https://doi.org/10.1109/ICDM.2008.17

### NLP
- scikit-learn — TF-IDF term weighting: https://scikit-learn.org/stable/modules/feature_extraction.html#tfidf-term-weighting
- scikit-learn — `cosine_similarity`: https://scikit-learn.org/stable/modules/metrics.html#cosine-similarity

### Frameworks & tools
- FastAPI — https://fastapi.tiangolo.com · SQLAlchemy — https://www.sqlalchemy.org · Pydantic — https://docs.pydantic.dev · Alembic — https://alembic.sqlalchemy.org
- React — https://react.dev · Vite — https://vite.dev · TanStack-era stack details in `frontend/package.json`
- scikit-learn — https://scikit-learn.org/stable/ · ReportLab — https://www.reportlab.com/opensource/
- Docker — https://docs.docker.com · Render — https://render.com/docs · Vercel — https://vercel.com/docs

## 26. Team

**Team Codeholics** · Smart India Hackathon 2026 · Problem Statement SIH26102

<p align="center">
  <strong>Drishti prioritizes investigations; it does not determine guilt.</strong>
</p>
