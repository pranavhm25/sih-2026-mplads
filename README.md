# Drishti — MPLADS Risk Intelligence & Investigation Platform

**SIH 2026 · Problem Statement 26102 · MoSPI · Data Informatics & Innovation Division (DIID) · Smart Automation**

Drishti is an **investigation-first** decision-support platform for MPLADS. It ingests work-level data, detects potential irregularities, explains the evidence behind every signal, prioritizes works for human investigation, and manages the resulting cases through to audit-ready reports.

> **Detect → Explain → Prioritize → Investigate → Document → Learn**

Drishti **never** declares a project fraudulent. It surfaces potential irregularities and investigation indicators; authorized officials verify, classify and decide.

---

## Product walkthrough (demo journey)

1. **Command Center** — where should attention go first? Summary strip, district attention, priority distribution, investigate-first queue.
2. **Investigation Queue** — dense work register with priority/signal/state filters and one-click case creation.
3. **Project Intelligence** — the signature screen: evidence ledger (Signal | Observed | Reference | Delta), Rule → Evidence → Action expansion, peer benchmark, duplicate candidates, timeline, verification checklist, case panel.
4. **Case file** — lifecycle (Open → Under review → Field verification → Resolved/Escalated), officer notes, feedback classification, audit trail, PDF report.
5. **Data & Provenance** — every dataset labelled official vs *synthetic demo*.

The flagship demo work **MPL-10281** converges **five independent signals**: cost anomaly (+~60% vs peer median), financial/physical gap (84% vs 32%), delay (~145d beyond expected), duplicate candidate (91% text similarity, ~43m away) and an Isolation Forest unusual-pattern score.

## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React 18, TypeScript (strict), Tailwind CSS, Recharts, Vite |
| Backend   | FastAPI, SQLAlchemy 2, Pydantic v2 |
| Database  | SQLite (demo default) / PostgreSQL (drop-in via `DATABASE_URL`) |
| ML        | scikit-learn Isolation Forest (unsupervised unusualness only) |
| NLP       | TF-IDF + cosine similarity duplicate candidates |
| Reports   | ReportLab PDF |
| Tests     | pytest (33 tests: rules, fusion, ingestion, quality, API, cases, reports) |

## Quick start

### Backend (port 8000)

```bash
cd backend
py -m pip install -r requirements.txt        # or pip3
cp .env.example .env                          # optional; defaults work
py -m uvicorn app.main:app --reload --port 8000
```

On first start the API seeds the deterministic synthetic demo dataset and runs the full detection pipeline automatically.

### Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend.

### Tests

```bash
cd backend && py -m pytest tests/ -q
cd frontend && npm run build    # typechecks + bundles
```

## Architecture

```text
DATA (CSV import / demo fixture)
  ↓  ingestion: schema mapping, normalization, provenance
DATA QUALITY (missing fields, date ordering, expenditure, duplicate IDs, invalid values)
  ↓
DERIVED METRICS (gap, delay, expenditure ratio, peer stats)
  ↓
┌──────────────┬─────────────┬──────────────┐
│ RULE ENGINE  │ ML ENGINE   │ NLP ENGINE   │
│ cost/gap/    │ Isolation   │ TF-IDF dup.  │
│ delay        │ Forest      │ candidates   │
└──────────────┴─────────────┴──────────────┘
  ↓  EVIDENCE FUSION (weights + severity + convergence bonus)
INVESTIGATION PRIORITY  →  QUEUE / COMMAND CENTER
  ↓  CASE (Open → Under review → Field verification → Resolved/Escalated)
  ↓  AUDIT REPORT (PDF)  →  OFFICER FEEDBACK
```

Backend layering: `api/` (thin routers) → `services/` (business logic: ingestion, quality, detection, cases, reports) → `models/` (SQLAlchemy) → `db`. Detection modules are independently testable.

### Data separation (non-negotiable)

`SOURCE FACT ≠ DERIVED METRIC ≠ MODEL OUTPUT ≠ OFFICER CONCLUSION` — enforced by separate tables (`projects`, `project_metrics`, `project_signal`, `investigation_case`) with versioned provenance on every derived row.

## API surface (`/api/v1`)

```
GET  /dashboard/summary                 GET  /projects        (?priority&signal_type&state&search&sort)
GET  /projects/{id}                     GET  /officers
GET  /datasets                          GET  /datasets/{id}/quality
POST /datasets/import (CSV)             POST /detection/runs
GET  /cases                             POST /cases
PATCH/ cases/{id}                       POST /cases/{id}/notes
POST /cases/{id}/evidence               POST /cases/{id}/feedback
POST /cases/{id}/report                 GET  /reports/{id}/download
```

All responses use the `{ data, meta }` envelope with dataset version + synthetic flag.

## Honest-uncertainty rules baked in

- Missing data renders as **“not reported” / “—”**, never estimated.
- Peer groups need ≥ 6 comparable works; otherwise the UI says **“Insufficient comparable projects”** — no fabricated benchmark.
- Signals use the language of *candidates/indicators*, and every signal carries its threshold, calculation and recommended verification.
- Synthetic demo data is labelled at every display point (`Synthetic demo data` chip).

## Environment

See `backend/.env.example` (`DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `MODEL_VERSION`, `RULESET_VERSION`, `REPORT_STORAGE_PATH`, `DEMO_AUTOSEED`). Secrets stay out of Git.
