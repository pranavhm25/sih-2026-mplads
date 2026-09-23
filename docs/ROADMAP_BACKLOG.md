# Drishti — Prioritized Backlog (IMPLEMENTED 2026-09-23)

Derived from: PS 26102 requirement audit, Claude's 45/100 evaluation, live e-SAKSHI
dashboard inspection (mplads.mospi.gov.in/digigov/dashboard.html), and the competitive
landscape (CAG AI-audits, PM-JAY/MJPJAY fraud AI, e-SAKSHI revamp).

**Status: all 12 items implemented.** See git history for the implementation commit
stage. Verification: 134 backend tests + 5 frontend tests + tsc + build green;
benchmark result in `docs/benchmark_result.json`; pitch content in
`docs/PITCH_DELTAS.md`; governance in `docs/SUSTAINABILITY.md`.

---

## P0 — WIN THE ROOM (implement on command)

### 1. Categorical compliance rule pack (Rule Engine v2)
The documented CAG-MPLADS violations are *categorical*, not statistical. Add a
first-class reference-data path beside the statistical one:
- Prohibited-category matcher (religious structures, memorials/statues, private
  property, repair/maintenance beyond permitted limits, office buildings)
  → reference table seeded from MPLADS guidelines + CAG audit typology
- Ineligible-payee indicator (trusts/societies/individuals outside permitted lists)
- Non-tendered / split-payment pattern flags (payment sequence heuristics)
- Each rule ships with guideline citation (clause number) shown in the evidence panel
- Language: "compliance indicator — verify against MPLADS guidelines", never "fraud"

### 2. Security & evidentiary integrity pack (the 1/10 killer)
- Auth + RBAC: four stakeholder roles from the PS (MP / District Authority /
  State Nodal Authority / Ministry) with scoped dashboards
- Tamper-evident audit log: hash-chained event log (chain = H(prev || event));
  a "verify chain" action demonstrates integrity live in the demo
- Case evidence export with hash manifest (report carries sha256 of all included
  records → chain-of-custody story)
- Security architecture slide: govt-grade hosting posture, no public cloud free tier

### 3. Validation & metrics story (no ground truth problem)
- Precision review loop: officer feedback (already in case workflow) → false-positive
  rate per rule, shown as a live metric ("reviewer agreement: N%")
- Calibrated alerts: every rule states expected flag rate; UI shows "flags X% of
  works — review capacity estimate"
- One quantified target in the pitch: e.g. "flag top 5% of works for review within
  7 days of sanction; ~82k sanctioned works/yr ⇒ ~4,100 works/yr ≈ 16/day"

### 4. Stakeholder role views (PS names four; currently one operator view)
- Ministry: national map + district attention list (exists)
- State Nodal: state-scoped rollup
- District: own works, own cases queue
- MP: own constituency works, own recommendations, plain-language summary
Same data, scoped queries + role-appropriate language.

---

## P1 — CLOSE TECHNICAL GAPS

### 5. Payments & asset-creation data model
PS lists "payments, asset creation" explicitly. Add optional normalized tables
(`payment`, `asset_record`) to the work-level schema, populated only if a source
provides them; wire into detection (payment clustering, payment-vs-stage gaps).
NULL-first: never fabricated.

### 6. Alert engine + early-warning digest
- Threshold digest: "new CRITICAL signals since last review", per-role
- Notification channels: in-app + CSV/email export (no external service dependency)
- Digest persisted per role so "since last review" is stateful

### 7. Trend analysis module
- FY-over-FY works recommended/sanctioned/completed, utilization %, completion rate
- Source: existing SCHEME_AGGREGATE ingestion path (already built in Prompt 3)
- Seasonality note: e-SAKSHI has no pre-2023-24 data — state this limitation honestly

### 8. Scale & throughput model (Scalability 5/10 → evidence)
- Bench test: ingest 110k synthetic work rows, measure pipeline wall-time
- Present: "processes full 18th-LS annual volume in X min on Y hardware"
- Postgres tuning notes (indexes already exist; add EXPLAIN proof)

### 9. Data-access reality check (feasibility 10/15)
- Documented: dashboard exposes Excel/CSV/PDF exports (allocation + aggregate tabs)
- Confirmed absence: no public work-level bulk export observed
- Actions: (a) verify any official bulk/API channel via MoSPI correspondence,
  (b) demo the pipeline on the legitimately downloadable exports,
  (c) show graceful degradation — Drishti runs on what exists today
- Do NOT scrape behind CAPTCHA/login; upload path covers official files

---

## P2 — PRESENTATION & OPS

### 10. Sustainability plan (2/5)
- Model governance: quarterly retrain cadence, threshold review board, drift monitor
- Ownership: named maintainer roles in the team; handover doc
- Cost sheet: self-hosted govt infra estimate (containers already ship via compose)

### 11. Pitch/README deltas
- Add explicit "Gap vs e-SAKSHI" slide (see comparison section below)
- Fill blank reference links before Sept 27
- Anchor pitch in CAG fraud typology (prohibited categories, ineligible payees,
  13 suspected fraud cases across 7 states in one CAG MPLADS audit period)
- Differentiation table (see below)

### 12. Demo hardening
- XLSX fixtures alongside CSV for LS/RS/aggregate (validator robustness proof)
- Concurrent-import lock test on file-hash dedupe guard
- Pre-seeded demo DB snapshot for offline presentation

---

## COMPETITIVE DIFFERENTIATION (verified landscape)

| Existing | What it does | What it does NOT do (our gap) |
|---|---|---|
| e-SAKSHI portal (MoSPI, 2023→) | Real-time ops dashboard, geo-tagged stage photos, drill-down financials, overdue-work flagging, citizen asset verification, stakeholder logins | No anomaly/fraud/inefficiency analytics; no risk ranking; no cross-work pattern detection; no case-management or evidence packaging; no trend alerts |
| CAG AI-based audits | Forensic AI on state schemes; IFMIS/WAMIS/GePNIC integration | Post-facto audit of *other* schemes; not an MPLADS operational monitoring layer; not real-time |
| PM-JAY / MJPJAY fraud AI | Document forgery, inflated bills, duplicate-patient claims | Domain-specific to health insurance claims; no MPLADS work/asset model |
| Nirikshak AI (private) | Generic govtech dashboard suite | No public MPLADS anomaly-detection capability documented |

**One-line USP for the deck:** "e-SAKSHI shows what happened; Drishti flags what
deserves a second look — and packages the evidence for the officer who must decide."

**Needs-verification flags (say this on stage, it reads as maturity):**
- No public evidence of an AI anomaly-detection layer built specifically for MPLADS
- Bulk work-level data access beyond dashboard exports unconfirmed

---

## e-SAKSHI vs DRISHTI — CAPABILITY DIFFERENCE (live-inspected 2026-09)

Live official numbers (18th Lok Sabha, as on dashboard): Allocated ₹8,342.66 Cr ·
Calamity consent ₹4.06 Cr · Recommended 1,09,863 works / ₹5,904.99 Cr · Sanctioned
82,184 / ₹4,337.90 Cr · Completed 35,885 / ₹1,761.56 Cr · Expenditure ₹2,873.71 Cr ·
543 MP rows, Excel/CSV/PDF exports.

| Capability | e-SAKSHI | Drishti |
|---|---|---|
| Real-time scheme status per house | ✔ | ✘ (not our job) |
| MP allocation tables + official exports | ✔ | consumes them |
| Drill-down to a work's financials | ✔ (login views) | consumes if exported |
| Geo-tagged stage photos | ✔ | ✘ |
| Overdue-work flagging (single-work age) | ✔ | ✔ deeper: expected-duration vs elapsed by category |
| Citizen asset verification | ✔ | ✘ |
| **Cross-work anomaly detection (cost outliers)** | ✘ | ✔ peer-median rule |
| **Duplicate-work detection** | ✘ | ✔ TF-IDF + location + cost |
| **ML unusualness scoring** | ✘ | ✔ Isolation Forest |
| **Evidence fusion + risk prioritization** | ✘ | ✔ weighted convergence |
| **Case workflow w/ officer decisions** | ✘ | ✔ open→review→field→resolve |
| **Audit-ready PDF evidence report** | ✘ | ✔ |
| **Provenance & synthetic-data separation** | n/a | ✔ |
| **Categorical compliance rules** | ✘ | ⚠ backlog item 1 |
| **Role-scoped stakeholder views** | ✔ (ops logins) | ⚠ backlog item 4 (analyst view only today) |
| **Alerts/digests** | ✘ | ⚠ backlog item 6 |

Read: Drishti is a decision-support layer *on top of* e-SAKSHI data, not a
competitor to it. The demo sentence writes itself: same official export the
Ministry publishes, one upload, thirty seconds, ranked investigation queue.

Data-lineage note (honest limitation): e-SAKSHI work-level detail predating
2023-24 is not on the portal; trend analysis (item 7) must say so.

---

## CONVENIENCE ENDPOINT

Say "implement backlog item N" (or a list) and I build exactly that, keeping the
tested pipeline green (100 backend tests, tsc, vitest, build).
