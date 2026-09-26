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

All 12 backlog items implemented (planning doc removed from the repository;
items summarized below):

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
- **Pitch/governance docs**: docs/SUSTAINABILITY.md.
- **Demo hardening**: XLSX fixture variants; migration c4d5e6f7a8b9
  (verified up/down).

Auth keys are env-driven (SECRET_KEY, SESSION_TTL_HOURS,
DEMO_ACCOUNTS_ENABLED) — see .env.example.


## CAG-Grounded Validation Layer (2026-09-26)

Capability validation proving which irregularity PATTERNS documented in
real CAG audits of MPLADS fall within Drishti's detection capability.
Full report: docs/CAG_VALIDATION.md. Architecture:

- **Catalog** (`app/data/cag_catalog.py`): 3 verified CAG sources
  (Report 3A of 2001; Report No. 31 of 2010 — tabled 18 Mar 2011;
  Report No. 22 of 2025, Para 3.1) and 9 irregularity patterns with
  verbatim quotes, required data fields, mapped Drishti detector and
  honest limitations. Adding findings = adding catalog entries.
- **Fixture** (`app/data/fixtures/cag_patterns.csv`): 17 synthetic works,
  all `CAGV-`-prefixed, reproducing ONLY the structural signature of each
  validatable pattern; ingested through the unmodified official pipeline
  with `is_synthetic=True`, version `cag-validation-1`, source label
  marker `synthetic_cag_pattern`.
- **Service** (`app/services/validation/cag_validation.py`): ingest →
  unmodified detection run (deterministic reference date) → per-pattern
  evaluation → machine-readable report. Results are FLAGGED / PARTIAL /
  MISSED / NOT_VALIDATABLE; thresholds never modified to force hits.
- **API**: `GET /api/v1/validation/cag` (full) and `…/summary` (compact),
  both `meta.is_synthetic=true`; cached per-process, invalidated on new
  imports.
- **UI**: Evidence & Validation screen (`/validation`) with the standing
  banner "Representative validation — not original CAG case data."

Reference run: 6 FLAGGED (compliance prohibited-category, delay,
financial/physical gap, ML spend-vs-progress profile, duplicate pair,
ineligible payee), 0 PARTIAL, 0 MISSED, 3 NOT_VALIDATABLE (missing MP
recommendation trail, authority fund ledger, records governance — real
detection gaps, documented, not faked). All 8 flagged works enter the
investigation queue. NO accuracy claims against real CAG data: the
underlying work-level records are not publicly available. Tests:
backend/tests/test_cag_validation.py (25), module-end cleanup restores
the demo dataset as the latest import for other integration tests.


## Synthetic Model Validation (2026-09-26)

Quantitative, reproducible injection benchmark of the UNMODIFIED pipeline
(docs/SYNTHETIC_VALIDATION.md). Positioning language: "Controlled
synthetic benchmark — results do NOT represent production-world fraud
detection accuracy." Never present its numbers as real-world accuracy.

- Engine (`app/services/validation/synthetic/`): `metrics.py` (pure,
  zero-division-safe confusion matrix + precision/recall/F1/FPR/detection
  rate), `injection.py` (seeded `SyntheticDatasetBuilder`: 60-row baseline
  in documented normal bands + 5 injectors — cost inflation, duplicate
  pairs, abnormal duration, spending-pattern, suspicious attributes —
  each recording full ground truth), `benchmark.py` (scenarios A–D →
  real ingestion → unmodified detection → per-record evaluation → JSON).
- Scenarios: A clean baseline / B small / C moderate / D mixed
  (60 baseline works each; 11/20/29 injected).
- Ground truth per record: record_id, ground_truth normal|anomaly,
  anomaly_type, injection_id, original_record_id, expected_detector.
  Baseline flags are FALSE POSITIVES, listed in the artifact (never
  discarded).
- Metrics discipline: undefined = `null`, never a fabricated 0/1;
  `hit_expected_detector` tracked separately from the headline "flagged".
- Determinism: seed 26102 (configurable); same seed → byte-identical
  report (apart from generated_at). Reference date pinned 2026-09-01.
- Artifact: `docs/synthetic_validation_results.json` (regenerate via
  `py scripts/run_synthetic_validation.py` from backend/). Docs numbers
  ALWAYS come from the artifact — never hand-written.
- Reference result (seed 26102): overall TP 60 / FP 8 / TN 232 / FN 0,
  precision 0.8824, recall 1.0000, F1 0.9375, FPR 0.0333; scenarios B/C/D
  perfect (P=R=F1=1.0, FPR=0). The 8 FPs are LOW-priority ML_ANOMALY
  signals in scenario A, caused by the IF all-NaN duplicate-score column
  imputation — honest engine quirk, reported not patched. No threshold
  tuning was performed.
- API: `GET /api/v1/validation/synthetic` (cached per seed). UI:
  Synthetic validation panel (`/validation/synthetic`) with the standing
  benchmark disclaimer. Tests: backend/tests/test_synthetic_validation.py
  (19).


## Contextual Duplicate Validation (2026-09-26)

Duplicate detection is now a TWO-STAGE pipeline (TRD TR-07):
"similarity ≠ duplication".

1. GENERATOR (unchanged): TF-IDF/cosine + weighted component score
   (text/geo/cost/category/time) — linguistic similarity only.
2. CONTEXTUAL VALIDATION (`app/nlp/duplicate_candidates.py`):
   - geospatial gate: haversine distance; strong band ≤ 50 m
     (DUPLICATE_GEO_STRONG_M); > 2 km contradicts the text match
     (DUPLICATE_GEO_MAX_M); missing coordinates = UNAVAILABLE, never
     zero distance.
   - vendor overlap: normalized token-set overlap of implementing
     agencies (≥ 0.5 = match; legal-form stopwords stripped); missing
     agency = UNAVAILABLE.
   - contextual confidence bands: HIGH = geo-close + same agency;
     MEDIUM = exactly one independent signal agrees; LOW = a signal
     contradicts (boilerplate similarity); UNAVAILABLE = no context.
   - severity is confidence-gated: HIGH only for high confidence;
     low/unavailable → LOW severity. Fusion penalizes weak-confidence
     DUPLICATE signals to 0.6× weight (DUPLICATE_WEAK_CONFIDENCE_WEIGHT)
     so text alone cannot drive priority.
   - every signal carries 5 evidence rows incl. geospatial proximity,
     vendor overlap and the contextual-confidence decomposition.

Schema: related_project gained vendor_match (bool, NULL = unavailable) +
contextual_confidence (high/medium/low/unavailable) — migration
d8e9f0a1b2c3. API RelatedProjectOut exposes both. Project Intelligence
"Potentially related works" table shows Distance / Vendor / Context
columns. Flagship MPL-10281 ↔ MPL-10412 verified: distance computed from
coordinates (7 m, in the ≤50 m band), confidence HIGH, severity HIGH.
Tests: backend/tests/test_duplicate_context.py (22) — boilerplate-FP
matrix (7 scenarios) + flagship pair.


## Demo Resilience Layer (2026-09-26)

Cold-start / availability hardening for the live SIH demo
(docs/DEMO_RUNBOOK.md). Render free tier sleeps the backend; the first
minutes of a demo must not look like a crash.

- **Readiness probe** `GET /api/v1/health/ready`
  (`app/services/system_checks.py`, kept out of the health route module so
  the foundation source-scan contract holds): one `SELECT 1` + demo-dataset
  count when `DEMO_AUTOSEED` — never detection. 200 `{status:'ok',
  ready:true, checks}` / 503 `{status:'starting', ready:false, checks}` via
  JSONResponse (a returned `(body, 503)` tuple would serialize as JSON 200).
- **Measured timings (local, SQLite, this machine):** cold boot to liveness
  ≈ 10.7 s, to READY ≈ 12.7 s (imports dominate; seed+detection ≈ +2 s on
  empty DB); warm restart identical (~12.8 s — bootstrap correctly no-ops
  when data exists, proven via unbuffered logs); warm /dashboard/summary
  0.37 s, cold 0.47 s; health/ready ≈ 0.22 s. Render wake is an estimated
  +30–60 s (not measurable locally).
- **Frontend retry layer** (`api.ts`): GET-only bounded exponential backoff
  [1,2,4,8,8]s (~23 s window) on network errors + 502/503/504 only;
  mutations never auto-retry (duplicate-case risk); `describeLoadFailure`
  gives waking-friendly copy; `setRetryDelaysForTesting` for vitest.
- **Waking UX**: `useBackendReady` (bounded poller, 1.5 s × 60 ≈ 90 s
  window) + `BackendGate` → "Drishti backend is starting. Retrying
  connection…" (amber, role=status) in Command Center / Investigation
  Queue / Project Intelligence; exhausted window shows operator guidance
  (never "crashed", never stack traces).
- **Scripts**: `scripts/prewarm-demo.py` (stdlib-only) — pre-warm mode
  polls liveness→readiness to exit 0 (handles 404 readiness on older
  builds); check mode verifies frontend, liveness, readiness, critical API
  (`/dashboard/summary`) and demo login read-only. Exit codes 0/1.
- **Bug found by the demo-check**: /dashboard/summary 500ed on >999-project
  datasets (`too many SQL variables`). `signals_for_project_ids` in
  fusion.py chunks IN() queries at 900 ids; used by dashboard + fusion.
- Tests: backend/tests/test_health_readiness.py + test_demo_resilience.py
  (8) — 503 paths, outage degradation, session cleanup, >999-id chunking,
  read-only probe. Frontend: useHealth.test.tsx extended to 13 (retry
  window/exhaustion/4xx-no-retry/POST-no-retry, readiness recovery,
  CommandCenter waking→recover cycle). Full suite: 209 passed + 1 skipped;
  tsc + vite build green.
- Demo login credentials are public seeded accounts (ministry@drishti.demo
  / drishti-demo) — documented, not secrets.
## Not-Substantiated Case Outcome (2026-09-26)

PRD R12 extension implementing "AI FLAG ≠ FRAUD": an AI-generated risk flag
can be explicitly cleared by human investigation. Drishti prioritizes
investigations; it does not determine guilt.

- **State machine** (`CASE_TRANSITIONS` in app/core/constants.py, enforced
  centrally; violations → 409): OPEN → UNDER_REVIEW → FIELD_VERIFICATION →
  RESOLVED | ESCALATED | CLOSED. RESOLVED = concluded with recorded
  classification (+ RESOLVED → ESCALATED); ESCALATED = substantiated concern
  with a higher authority; CLOSED = not substantiated. CLOSED/ESCALATED →
  UNDER_REVIEW is the supervisor reopen path (closed_at cleared, resolution
  history kept).
- **CLOSED requires** resolution_type = NOT_SUBSTANTIATED (a NEW type,
  distinct from FALSE_POSITIVE which means the flag itself was wrong) + a
  structured `resolution_reason` category (DOCUMENTATION_PROVIDED,
  LEGITIMATE_DELAY, DATA_QUALITY_ISSUE, FALSE_DUPLICATE_CANDIDATE,
  APPROVED_VARIATION, CONTEXTUAL_EXCEPTION, OTHER) + a free-text
  `resolution_summary`. Validated centrally in the case service; useful 400s.
- **Schema**: investigation_case.resolution_reason (String 40, nullable) —
  migration e1a2b3c4d5e6 (down: d8e9f0a1b2c3). Statuses are data, not DDL.
- **Audit trail**: every STATUS_CHANGED CaseEvent carries from/to status,
  actor and outcome metadata (resolution_type + resolution_reason); the
  hash-linked audit chain records CASE_UPDATED. AI signals are never
  modified by any case action (regression-tested).
- **Dashboard**: open-case counts (dashboard + stakeholder summary) exclude
  RESOLVED, ESCALATED and CLOSED — a cleared case is concluded work, never
  unresolved work.
- **Reports**: cleared-case PDFs gain an explicit "Investigation outcome:
  NOT SUBSTANTIATED" section with the reason category and the standing note
  that this is not a fraud/innocence verdict; detected signals remain in the
  report (never removed because the case was cleared).
- **UI**: Case actions offer "→ Not substantiated (close case)" opening a
  neutral outcome form (reason select + short explanation, submit gated);
  status labels say "Closed — not substantiated"; an accent banner states
  "AI-generated risk flags require human verification and do not constitute
  findings of fraud." No red/green guilt-innocence language.
- **Demo scenario** (bootstrap-gated by DEMO_AUTOSEED,
  app/services/cases/demo_scenario.py): a completed investigation of the
  flagship duplicate pair MPL-10281 — OPEN → UNDER_REVIEW →
  FIELD_VERIFICATION → CLOSED (NOT_SUBSTANTIATED, FALSE_DUPLICATE_CANDIDATE)
  with investigator notes and full audit trail; idempotent, recreated after
  demo reseeds, closed cases free the project for future cases.
- Tests: backend/tests/test_case_outcomes.py (20) + Cases.test.tsx (3).
