# Drishti — data directory

Layers (never mix them):

- `raw/` — source files exactly as received from official sources
  (e-SAKSHI exports, permitted MPLADS extracts). Real data files stay out of Git.
- `processed/` — normalized/cleaned outputs ready for `/api/v1/datasets/import`.
- `fixtures/` — deterministic test/demo fixtures. Backend-bundled synthetic
  fixtures live in `backend/app/data/fixtures/` and are ingested with
  `is_synthetic=true` regardless of filename.

## Official source reality

The MPLADS e-SAKSHI public dashboard currently exposes (observed):

- Dashboard aggregates per house: Allocated Limit, Amount Consented for
  Calamity, Works Recommended / Sanctioned / Completed, Expenditure on
  Completed and Ongoing Works.
- Allocation exports:
  - Lok Sabha: Sr. No. | State | Hon'ble Members of Parliament | Constituency | Allocated Amount (₹)
  - Rajya Sabha: Sr. No. | State | Hon'ble Members of Parliament | Elected/Nominated | Allocated Amount (₹)

Work-level fields (per-work sanctioned cost, expenditure, progress, dates,
coordinates, agency) are **not currently available** in the observed public
exports. Drishti keeps the work-level ingestion path extensible
(`WORK_LEVEL` dataset type) but never fabricates those fields for official
datasets — absence is stored as NULL and reported as unavailable.

## Unit handling

Dashboard aggregates are displayed in **Crore**; allocation exports carry
**raw rupee** amounts. Drishti normalizes monetary values together with
their unit (`RUPEE | LAKH | CRORE`) and never compares across units without
explicit conversion (`to_rupees`).
