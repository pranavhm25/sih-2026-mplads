# Drishti — MPLADS Risk Intelligence & Investigation Platform

**SIH 2026 · Problem Statement 26102 · MoSPI · Data Informatics & Innovation Division (DIID) · Smart Automation**

Drishti is an **investigation-first** decision-support platform for MPLADS. It ingests official data, detects potential irregularities, explains the evidence behind every signal, prioritizes works for human investigation, and manages the resulting cases through to audit-ready reports.

> **Detect → Explain → Prioritize → Investigate → Document → Learn**

Drishti **never** declares a project fraudulent. It surfaces potential irregularities and investigation indicators; authorized officials verify, classify and decide.

## 🔗 Live demo

| | |
|---|---|
| **Application** | [https://mplads-drishti-codeholics.vercel.app](https://mplads-drishti-codeholics.vercel.app) |
| **API health** | [https://drishti-backend-h2c8.onrender.com/api/v1/health](https://drishti-backend-h2c8.onrender.com/api/v1/health) |
| **API docs (Swagger)** | [https://drishti-backend-h2c8.onrender.com/docs](https://drishti-backend-h2c8.onrender.com/docs) |

Sign in with any demo stakeholder account — password for all: `drishti-demo`
(`ministry@drishti.demo`, `snl@drishti.demo`, `district@drishti.demo`, `mp@drishti.demo`, `admin@drishti.demo`).

> ℹ️ Hosted on free tiers: the backend sleeps after ~15 idle minutes, so the first request may take ~50 s to wake it. Demo data reseeds automatically on every boot.

---

## Product walkthrough (demo journey)

1. **Command Center** — where should attention go first? Summary strip, geographic distribution map (Leaflet point markers colored by priority with tooltips), district attention, priority distribution, investigate-first queue.
2. **Investigation Queue** — dense work register with priority/signal/state filters and one-click case creation.
3. **Project Intelligence** — the signature screen: evidence ledger (Signal | Observed | Reference | Delta), Rule → Evidence → Action expansion, peer benchmark, duplicate candidates, timeline, verification checklist, case panel.
4. **Case file** — lifecycle (Open → Under review → Field verification → Resolved/Escalated), officer notes, feedback classification, audit trail, PDF report.
5. **Data & Provenance** — one-click demo reseed, CSV import, data quality exception reporting; every dataset labelled official vs *synthetic demo*.

The flagship demo work **MPL-10281** converges **five independent signals**: cost anomaly (+~60% vs peer median), financial/physical gap (84% vs 32%), delay (~145d beyond expected), duplicate candidate (91% text similarity, ~43m away) and an Isolation Forest unusual-pattern score. An **agency concentration** cluster is showcased in Belagavi (>80% sanctioned value held by one agency).

## Official data ingestion

The **Data** screen imports official CSV/XLSX exports from the MPLADS
e-SAKSHI dashboard. Supported dataset types:

| Type | Source | Notes |
|------|--------|-------|
| `MP_ALLOCATION` | Lok Sabha / Rajya Sabha allocation exports | Type detected from source columns; house-specific fields stay NULL when absent |
| `SCHEME_AGGREGATE` | Dashboard aggregate statistics | Monetary values keep their display unit (Crore) |
| `WORK_LEVEL` | Future official work-level datasets | Extensible; detection pipeline runs automatically on import |
| `SYNTHETIC_FIXTURE` | Bundled evaluation fixtures | Always labelled DEMO DATA — never official |

Per-work analytical fields (per-work sanctioned cost, expenditure,
progress percentages, dates, coordinates, agency) are **not currently
exposed** by the observed public dashboard/exports. Drishti stores NULL
for absent fields, never fabricates them, and reports them as unavailable.

The import pipeline: parse → detect schema → map columns → normalize
(explicit currency/unit handling: raw rupees vs Crore) → validate per row
(row, field, rule, severity, message, observed value) → persist valid rows
(**partial validity**: ERROR rows excluded but preserved in the validation
issue table) → deterministic quality status (GOOD / ACCEPTABLE / DEGRADED /
FAILED) with plain-language reasons. Duplicate uploads (same SHA-256) are
rejected. One-click synthetic fixtures exercise the whole pipeline for
evaluation.

## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React 18, TypeScript (strict), Tailwind CSS, Leaflet, react-leaflet, Recharts, Vite |
| Backend   | FastAPI, SQLAlchemy 2, Pydantic v2 |
| Database  | SQLite (demo default) / PostgreSQL (drop-in via `DATABASE_URL`) |
| ML        | scikit-learn Isolation Forest (unsupervised unusualness only) |
| NLP       | TF-IDF + cosine similarity duplicate candidates |
| Reports   | ReportLab PDF |
| Tests     | pytest (136 backend tests: official ingestion, quality, rules, fusion, duplicates, ML, agency concentration, API, cases, reports) |

## Quick start

### Option 1: Run with Docker (Recommended — One Command)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or [Docker Engine + Docker Compose](https://docs.docker.com/engine/install/) (Linux). Ensure Docker is running.

#### On Linux / macOS (One Command)

```bash
./run.sh
```
*(Or directly: `docker compose up --build`)*

To stop the platform:
```bash
./stop.sh
# or: docker compose down
```

#### On Windows (One Command)

**Via Command Prompt or File Explorer:**
Double-click `run.bat` or run:
```cmd
run.bat
```

**Via PowerShell:**
```powershell
.\run.ps1
```
*(Or directly: `docker compose up --build`)*

To stop the platform: double-click `stop.bat` or run `docker compose down`.

---

#### Service Endpoints

Once started, the backend automatically initializes tables, seeds the synthetic demo dataset, and executes the full detection pipeline:

- **Frontend Application:** [http://localhost:5317](http://localhost:5317)
- **Backend Swagger Docs:** [http://localhost:8317/docs](http://localhost:8317/docs) (or proxied at [http://localhost:5317/docs](http://localhost:5317/docs))
- **Backend Health Check:** [http://localhost:8317/api/v1/health](http://localhost:8317/api/v1/health)


---

### Option 2: Local manual setup

#### Backend (port 8317)

```bash
cd backend
py -m pip install -r requirements.txt        # or pip3
cp .env.example .env                          # optional; defaults work
py -m alembic upgrade head                    # apply schema migrations
py -m uvicorn app.main:app --reload --port 8317
```

In non-production environments tables are also created automatically at startup; production must use Alembic migrations. On first start the API seeds the deterministic synthetic demo dataset and runs the full detection pipeline automatically.

Liveness probe: `GET /api/v1/health` → `{"status": "ok", "service": "drishti-api"}` (never touches the database).

### Frontend (port 5317)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5317. The dev server proxies `/api` to the backend.

---

### Option 3: Free Cloud Deployment (Vercel + Render)

Deploy the entire platform online 100% free of charge:
- **Backend on Render**: Auto-provisions using the included [render.yaml](render.yaml) blueprint.
- **Frontend on Vercel**: Connect your GitHub repository, configure `VITE_API_URL` to point to Render, and deploy.
- **Detailed Step-by-Step Instructions**: See the [Free Hosting Guide](docs/FREE_HOSTING_GUIDE.md) or the [30-Minute Beginner Quickstart](docs/HOSTING_QUICKSTART.md).

---

### Tests

```bash
cd backend && py -m pytest tests/ -q          # 136 backend tests
cd frontend && npm run test                   # vitest (health screen + smoke)
cd frontend && npm run typecheck && npm run build
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

- **Backend:** see `backend/.env.example` (`DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `MODEL_VERSION`, `RULESET_VERSION`, `REPORT_STORAGE_PATH`, `DEMO_AUTOSEED`, `SESSION_TTL_HOURS`, `DEMO_ACCOUNTS_ENABLED`). Secrets stay out of Git.
- **Frontend:** `VITE_API_URL` is baked in at build time from `frontend/.env.production` (empty locally — the Vite dev proxy handles `/api`).
