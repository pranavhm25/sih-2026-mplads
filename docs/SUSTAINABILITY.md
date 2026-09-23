# Drishti — Sustainability Plan (Backlog #10)

Addresses the evaluation gap: "no maintenance/ownership/retraining plan."

## 1. Model governance

| Concern | Mechanism in place | Cadence |
|---|---|---|
| Model drift | Officer feedback (Confirmed concern / False positive / Needs verification) feeds the precision metric at `GET /api/v1/validation/summary` | Reviewed monthly |
| Threshold tuning | All detection thresholds are documented constants (`app/core/constants.py`), not magic numbers; changes go through a threshold-review note in the repo | Quarterly board |
| Model retrain | Isolation Forest retrains on each detection run (unsupervised, seeded, deterministic); no scheduled batch retrain needed | Per run |
| Rule updates | Categorical compliance pack is data-driven (registry entries with guideline citations); guideline revisions = registry updates, no code change | On guideline revision |
| Data-quality gate | Dataset quality scale (GOOD/ACCEPTABLE/DEGRADED/FAILED) documented and deterministic | Per import |

## 2. Ownership (team roles)

- **Detection owner** — rules + ML engines, threshold proposals, precision review
- **Data owner** — ingestion registry, source schemas, validation rules, provenance
- **Platform owner** — auth/RBAC, audit chain, deployment, backups
- **Product owner** — stakeholder views, case workflow, reporting; MoSPI liaison

(For SIH: map these to actual team members before the finale.)

## 3. Hosting & cost model

- The stack ships as containers (`docker compose`): FastAPI + nginx frontend +
  PostgreSQL. Target deployment is **government infrastructure** (NIC cloud /
  MoSPI on-prem), not public free-tier hosting.
- Reference sizing for national scale (110k works/yr, ~15 GB DB incl. signals):
  1 app VM (4 vCPU/8 GB) + managed PostgreSQL (2 vCPU/8 GB) — comfortably inside
  a standard NIC VM allocation. Measured ingestion throughput: ~1,070 rows/s
  (see `docs/benchmark_result.json`), i.e. the full 18th-LS annual volume in
  ~2 minutes of pure ingestion.
- No external paid APIs are required: embedding/similarity is local TF-IDF;
  the ML model is scikit-learn; PDF generation is ReportLab.

## 4. Data partnerships (the real dependency)

- Official exports from e-SAKSHI (allocation tables, aggregate tabs) are
  publicly downloadable today and fully supported by the importer.
- Work-level bulk data requires a MoSPI data-sharing arrangement — the
  ingestion layer is schema-extensible (`work_level_v1` registry) and ready,
  but access is an institutional ask, not an engineering task.
