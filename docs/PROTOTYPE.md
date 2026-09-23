# Drishti — Prototype Feature Draft

**Scope rule:** the prototype demonstrates the full story —

> Detect → Explain → Prioritize → Investigate → Document

— on a controlled, clearly-labelled demo dataset. It is judged as a working
demo of the investigation workflow, not a production system.

Status legend: ✅ exists · 🟡 partial / needs polish · ❌ missing · 🔶 stretch

---

## A. Data Foundation

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| A1 | Controlled synthetic MPLADS-style dataset (~200–500 works) with embedded demo scenarios | 🟡 | Demo fixture exists; must embed the showcase case (84%/32%, ₹38.7L vs ₹24.2L peer median, 510/365 days, duplicate at 91% + 43m) plus a cost-outlier cluster, stalled works, duplicate pairs, one agency-concentration case |
| A2 | One-click demo seed (ingest + detection run) | ✅ | `POST /api/v1/datasets/demo-seed` + "Load demo dataset" action with confirm on Data screen |
| A3 | CSV import path (real MPLADS extract if permitted) | ✅ | `/api/v1/datasets/import` with column aliasing |
| A4 | Provenance labels (official vs derived vs synthetic) in UI + DB | 🟡 | Backend flags exist; verify every screen shows them |
| A5 | Data quality flags surfaced on a screen | ✅ | Quality report table on Data screen with work ID links, rules, severities, and descriptions |

## B. Detection & Intelligence

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| B1 | Cost anomaly vs peer group (median / P75, deviation %) | ✅ | Rule engine + benchmarking |
| B2 | Financial vs physical progress mismatch | ✅ | Rule engine |
| B3 | Delay detection | ✅ | Rule engine |
| B4 | Duplicate candidates (text + location + cost + category + time overlap) | ✅ | NLP TF-IDF service |
| B5 | Isolation Forest anomaly signal | ✅ | ML engine |
| B6 | Agency/contractor concentration | ✅ | Implemented in `agency_concentration.py`; computes district sanctioned share, emits signals + evidence |
| B7 | Peer benchmarking (district/category/sector/year cohorts) | ✅ | |
| B8 | Evidence fusion → priority with multi-signal convergence bonus | ✅ | Fusion engine with documented bands |
| B9 | Rule → Evidence → Action triple on every signal | ✅ | Evidence + recommended verification action on every signal |
| B10 | Recommended verification checklist per project | ✅ | Dynamic checklist mapped to triggered signals on Project Intelligence |

## C. Product Screens

| # | Screen / Feature | Status | Notes |
|---|------------------|--------|-------|
| C1 | Command Center: KPI strip, risk distribution, district attention table, top cases | ✅ | |
| C2 | Geographic visualization | ✅ | `CommandCenterMap` with Leaflet CircleMarkers colored by priority, quick filter bar, popup with work info, signals, and intelligence link |
| C3 | Investigation Queue: priority sort, signal/geo/status filters | ✅ | |
| C4 | Project Intelligence: signals, evidence drill-down, peer comparison, related projects, timeline, actions | ✅ | Main demo screen — polish hardest here |
| C5 | Case management: create, assign, status transitions, notes, feedback | ✅ | |
| C6 | Audit report PDF (one click from case) | ✅ | ReportLab |
| C7 | Empty / loading / error states everywhere | ✅ | Audited across all pages; consistent state handlers and provenance badges |

## D. Demo Readiness

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| D1 | One continuous demo path: dataset → anomaly → evidence → peers → priority → case → checklist → PDF | ✅ | End-to-end verified & tested via `test_flagship_demo_workflow_end_to_end` |
| D2 | Risk Replay (priority over time) | 🔶 | Should-have; only if stable |
| D3 | Compliance dashboard | 🔶 | Should-have |
| D4 | Officer feedback analytics | 🔶 | Feedback capture exists; analytics is stretch |

---

## Explicitly OUT of prototype scope

Satellite verification · computer vision · document AI/OCR · graph analytics ·
predictive risk · LLM copilot · authentication/roles · production deployment
hardening · real-time ingestion.

## Implementation status note (updated after code audit)

Deeper audit revised several statuses from the first draft:
- A1/A2: demo dataset (deterministic, flagship case + quality violations) and
  startup autoseed **already exist** — gap is only a user-facing reset/reseed.
- B9/B10: Rule → Evidence → Action strings already flow through
  `signal_factory` (`RECOMMENDED_VERIFICATION`) — status effectively ✅.
- B6, A2, and C2 gaps have been implemented.

## Build plan — 4 sections

### Section 1 — Detection completeness: agency concentration detector (B6)
Status: **COMPLETE** ✅
- Signal type, weight (1.5), and recommended action already in `constants.py`.
- Implement detector computing agency share of district sanctioned value;
  emit signals + evidence via `signal_factory` (conventions match NLP/ML engines).
- Wire into `detection/runner.py` pipeline; record counts in run summary.
- Add demo scenario: one district where a single agency holds an unusual share.
- Unit + integration tests (detector math, threshold bands, demo trigger).

### Section 2 — Demo seed UX (A2)
Status: **COMPLETE** ✅
- `POST /api/v1/datasets/demo-seed`: wipe demo data → reseed → rerun detection.
- "Load demo dataset" action on the Data page (with confirm + provenance label).

### Section 3 — Geographic visualization (C2)
Status: **COMPLETE** ✅
- Add `react-leaflet` + `leaflet` to frontend.
- Map component on Command Center: priority-colored circle markers
  (CRITICAL/HIGH red · MEDIUM amber · LOW gray), tooltip with work ID + signals.
- Point markers with interactive filtering (All / High+Crit / Medium / Low).

### Section 4 — Polish + demo rehearsal (C7, D1)
Status: **COMPLETE** ✅
- Provenance label audit on every screen; empty/loading/error states.
- Run backend + frontend test suites; fix regressions (50 pytest tests + vitest + tsc + vite build passing).
- Verify flagship demo path end-to-end: dataset → anomaly → evidence →
  peers → priority → case → checklist → PDF report (`test_flagship_demo_workflow_end_to_end`).
- Update README + docs.

🔶 Stretch items (Risk Replay, compliance dashboard, feedback analytics) only
if the core path is stable after Section 4.
