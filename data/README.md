# Drishti — data directory

Layers (never mix them):

- `raw/` — source files exactly as received (CSV exports, permitted MPLADS extracts).
- `processed/` — normalized/cleaned outputs ready for `/api/v1/datasets/import`.
- `fixtures/` — deterministic test/demo fixtures. Synthetic fixtures must keep
  `synthetic` in the filename so ingestion labels them `is_synthetic=true`.

Provenance rules (AGENTS_RULES.md Rule 6): synthetic/demo data is always
labelled as such in the UI and database; it must never be presented as an
official government record. Real data files stay out of Git.
