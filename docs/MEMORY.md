# Drishti — Project Memory

## Project Identity

- Product: **Drishti**
- SIH Problem Statement: **26102**
- Organization: **MoSPI**
- Division: **Data Informatics & Innovation Division (DIID)**
- Category: **Software**
- Theme: **Smart Automation**

## Product Definition

Drishti is an **MPLADS Risk Intelligence & Investigation Platform**.

One-line description:

> Drishti continuously analyzes MPLADS works, identifies unusual patterns, explains why they are unusual, prioritizes them for investigation, and helps authorities investigate and document them.

## Core Principle

Drishti must not automatically declare a project fraudulent.

The system identifies:
- potential irregularities
- unusual patterns
- projects that warrant investigation

Authorized officials make final decisions.

## Core Workflow

```text
INGEST
 ↓
CLEAN & VALIDATE
 ↓
DETECT
 ↓
CORRELATE
 ↓
PRIORITIZE
 ↓
INVESTIGATE
 ↓
DOCUMENT
 ↓
FEEDBACK
```

## Detection Signals

### Cost anomaly
Compare project cost with comparable projects.

### Financial/physical mismatch
Compare financial progress with physical progress.

### Delay
Compare expected duration with elapsed duration.

### Duplicate candidate
Use:
- text similarity
- location proximity
- cost similarity
- category match
- time overlap

### Agency/contractor concentration
Use where the underlying data supports it.

### ML anomaly
Use Isolation Forest as an unusual-pattern detector.

## Evidence Fusion

The platform combines independent signals:

```text
Rules
+
ML
+
NLP
+
Peer Context
↓
Evidence Fusion
↓
Investigation Priority
```

Do not reduce the product to a single unexplained risk score.

## Signature Differentiators

1. Investigation-first design.
2. Rule → Evidence → Action.
3. Multi-signal convergence.
4. Human-in-the-loop workflow.
5. Audit-ready case management.
6. Contextual peer intelligence.

## Core Screens

1. Command Center
2. Investigation Queue
3. Project Intelligence
4. Investigation Case
5. Reports
6. Data / Rules administration

## Must-Have MVP

- real/permitted MPLADS dataset
- data cleaning and validation
- cost anomaly
- financial/physical mismatch
- delay detection
- duplicate candidate detection
- Isolation Forest
- peer benchmarking
- explainable investigation priority
- evidence breakdown
- multi-signal convergence
- Command Center
- Investigation Queue
- Project Intelligence
- geographic visualization
- case creation
- recommended verification
- audit report

## Should-Have

- contractor/agency concentration
- Risk Replay
- officer feedback
- compliance dashboard
- CAG-informed rule library
- better role-based views

## Future Scope

- satellite verification
- computer vision
- document intelligence
- graph analytics
- predictive risk trajectories
- LLM Investigation Copilot

## Recommended Stack

Frontend:
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts
- Leaflet

Backend:
- FastAPI
- Python
- SQLAlchemy
- Pydantic

Data:
- PostgreSQL

ML:
- Pandas
- NumPy
- scikit-learn
- Isolation Forest
- optional LOF

NLP:
- TF-IDF
- cosine similarity
- optional Sentence Transformers

Reports:
- ReportLab

## UI Memory

The interface must **not** look like a generic AI/SaaS template.

Avoid:
- gradients
- excessive rounded cards
- centered dashboard layouts
- Inter
- decorative blobs
- neon colors
- excessive shadows

Target:
- evidence ledger
- government/engineering workpaper feel
- restrained colors
- strong tables
- maps
- typographic hierarchy
- compact operational layouts
- IBM Plex Sans/Serif + Source Sans 3 + IBM Plex Mono

## Demo Story

```text
MPLADS DATA
 ↓
DETECTION ENGINE
 ↓
RULES + ML + NLP
 ↓
PEER CONTEXT
 ↓
EVIDENCE FUSION
 ↓
RISK PRIORITIZATION
 ↓
INVESTIGATION QUEUE
 ↓
INVESTIGATION CASE
 ↓
HUMAN VERIFICATION
 ↓
AUDIT REPORT
 ↓
OFFICER FEEDBACK
```

## Source-of-Truth Rule

This file records the stable product decisions for the project. If a later implementation decision conflicts with this memory, explicitly evaluate the trade-off before changing the core investigation-first concept.

## Official Source Reality (Prompt 3)

The MPLADS e-SAKSHI public dashboard currently exposes:

- Per-house dashboard aggregates: Allocated Limit, Amount Consented for
  Calamity, Works Recommended / Sanctioned / Completed, Expenditure on
  Completed and Ongoing Works.
- Allocation exports — Lok Sabha: Sr. No. | State | Hon'ble Members of
  Parliament | Constituency | Allocated Amount (₹). Rajya Sabha: same plus
  Elected/Nominated, without Constituency.
- Per-work analytical fields (sanctioned cost, expenditure, progress,
  dates, coordinates, agency) are NOT currently exposed. Drishti stores
  NULL for absent fields, never fabricates them, and keeps the WORK_LEVEL
  ingestion path extensible for future official datasets.

Dataset types: MP_ALLOCATION, SCHEME_AGGREGATE, WORK_LEVEL,
OTHER_OFFICIAL_EXPORT, SYNTHETIC_FIXTURE. An MP allocation row is never
reshaped into a work record. Monetary values keep their source unit
(RUPEE / LAKH / CRORE); comparison across units requires explicit
conversion. Quality states are deterministic (GOOD / ACCEPTABLE /
DEGRADED / FAILED) with plain-language reasons — never an opaque score.
Validation issues are preserved with row, field, rule, severity, message
and observed value; ERROR rows are excluded from import but never silently
discarded.


## Backlog Implementation (2026-09-23)

All 12 backlog items implemented (docs/ROADMAP_BACKLOG.md):

- **Compliance rule pack** (`app/rules/compliance.py`): deterministic keyword
  matching of work descriptions / implementing agencies against MPLADS
  guideline reference categories (religious structures, memorials, private
  property, unpermitted repair, office buildings, trust payees). Every
  signal carries its guideline citation as evidence; language is
  "compliance indicator", never fraud. SignalType.COMPLIANCE, fusion weight 3.5.
- **Security pack** (`app/core/security.py`, `app/services/auth.py`,
  `app/api/v1/auth.py`): PBKDF2 password hashing, HMAC-signed session tokens,
  login/logout/me endpoints, demo stakeholder accounts
  (ministry/snl/district/mp @drishti.demo, password drishti-demo).
- **Tamper-evident audit chain** (`audit_event` table): sha256 hash-linked
  events for logins and every case mutation + report generation;
  `GET /api/v1/audit/verify` pinpoints tampering (seq, reason).
  Case reports embed a SHA-256 evidence hash manifest.
- **Stakeholder views** (`/api/v1/stakeholder/summary` + frontend
  Stakeholders page): MP (own constituency, plain language), District (own
  works/cases), State Nodal (own state), Ministry (national + district
  attention). Unauthenticated calls get counts only, never another role's slice.
- **Validation story** (`/api/v1/validation/summary`): reviewer precision
  from case resolutions (null until feedback exists), flag-rate
  transparency, quantified target string.
- **Alert digest** (`/api/v1/alerts/digest` + ack): per-role watermark,
  high/critical floor for Ministry, critical-only for District/MP.
- **Trends** (`/api/v1/trends`): from imported SCHEME_AGGREGATE datasets
  only; carries the pre-2023-24 limitation note.
- **Payments/assets** (optional layers): `payment_record`, `asset_record`
  tables + registry fields; rows exist only when a source provides them.
- **Benchmark**: `backend/scripts/benchmark_scale.py` → 110k rows at
  ~1,070 rows/s (docs/benchmark_result.json).
- **Pitch/governance docs**: docs/PITCH_DELTAS.md, docs/SUSTAINABILITY.md.
- **Demo hardening**: XLSX fixture variants; migration c4d5e6f7a8b9
  (verified up/down).

Auth keys are env-driven (SECRET_KEY, SESSION_TTL_HOURS,
DEMO_ACCOUNTS_ENABLED) — see .env.example.
