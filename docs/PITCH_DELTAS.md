# Pitch Deck Deltas (Backlog #11)

Ready-to-paste content that closes the evaluation's valid criticisms.

---

## Slide A — "Gap vs e-SAKSHI" (the differentiation slide)

**Title:** e-SAKSHI shows what happened. Drishti flags what deserves a second look.

| Capability | e-SAKSHI (official portal) | Drishti |
|---|---|---|
| Real-time scheme status, MP tables, official exports | ✔ | consumes them |
| Geo-tagged stage photos, citizen asset verification | ✔ | — (not our job) |
| Cross-work cost anomaly detection | ✘ | ✔ peer-median rule |
| Duplicate-work detection | ✘ | ✔ TF-IDF + location + cost |
| ML unusualness scoring | ✘ | ✔ Isolation Forest |
| Categorical compliance indicators (guideline-cited) | ✘ | ✔ |
| Evidence fusion → ranked investigation queue | ✘ | ✔ |
| Case workflow → audit-ready PDF with hash manifest | ✘ | ✔ |
| Role-scoped stakeholder views (MP/District/State/Ministry) | ops logins | ✔ decision-support views |
| Tamper-evident audit chain | ✘ | ✔ SHA-256 hash-linked events |

**Bottom line:** Drishti is a decision-support layer *on top of* the official
recording system — the same architecture the government already trusts
(PM-JAY claims portal + separate fraud AI; CAG auditing ministry data
independently). The recorder cannot be the only auditor.

---

## Slide B — Security & evidentiary integrity (was the 1/10 gap)

- **Auth + RBAC:** PBKDF2-hashed credentials, HMAC-signed sessions,
  stakeholder-scoped endpoints (MP sees own constituency; District own works;
  Ministry national).
- **Tamper-evident audit trail:** every login, case action, and report
  generation appends a SHA-256 hash-linked event; `GET /api/v1/audit/verify`
  re-walks the chain and pinpoints any tampering (live demo: edit one row in
  the DB → verification fails at that exact seq).
- **Evidence chain of custody:** every case report embeds a hash manifest
  (SHA-256 per signal/evidence/note + manifest root) — recipients can detect
  post-generation alteration.
- **Deployment posture:** containerized for government infrastructure
  (NIC/MoSPI on-prem); no public cloud free tier; secrets env-driven,
  never committed.

---

## Slide C — Quantified targets (was "slogans, not claims")

- **Review capacity, stated honestly:** the platform currently flags ~X% of
  works with ≥1 triggered signal (live number: `GET /api/v1/validation/summary`).
  Target: converge to **top ~5% of works** for review within **7 days of
  sanction** — at 18th-LS volume (~82k sanctioned/yr) that is ~4,100 works/yr
  ≈ 16/day nationally, i.e. one reviewer-hour scale per state.
- **Precision loop:** officer resolutions produce a live reviewer-precision
  metric; target ≥70% precision before any enforcement use.
- **Throughput (measured):** 110,000-row synthetic import processed at
  ~1,070 rows/s end-to-end (parse → map → normalize → validate → persist) —
  full annual national volume in ~2 minutes. (`docs/benchmark_result.json`)
- **Scale model:** ~543 Lok Sabha + 233 Rajya Sabha MPs; per-year works volume
  ~110k; Postgres schema indexed on district/category/status/geo lookups.

---

## Slide D — Honest data-access story (was "unverified")

- **Today (verified on the live portal):** dashboard aggregates + MP
  allocation exports (Excel/CSV/PDF) are publicly downloadable — Drishti's
  importer ingests exactly these, with schema auto-detection, unit-safe
  normalization (₹ vs Crore), SHA-256 dedupe, and a validation-issue ledger.
- **Tomorrow (institutional ask):** work-level bulk export / API via MoSPI
  data-sharing arrangement. The `work_level_v1` registry is extensible —
  a new official export is a registry entry, not a rewrite.
- **Known limitation (stated, not hidden):** the portal carries works
  recommended on/after 1 Apr 2023 only; pre-2023-24 trend analysis is not
  possible from this official source.
- **Never fabricated:** fields the source does not provide stay NULL; demo
  data is permanently labeled synthetic and separated from official imports.

---

## Slide E — Grounded problem framing (anchor in CAG typology)

CAG performance audits of MPLADS documented *categorical* violations:
prohibited work categories (religious structures, memorials), payments to
ineligible entities, unpermitted repair/maintenance spend, and suspected
fraud/misappropriation cases across sample states. Drishti's compliance pack
matches work descriptions and implementing agencies against guideline
reference categories — each signal carries its guideline citation and is
phrased as a verification indicator, never a verdict. This is the detection
path no existing tool covers for MPLADS.

---

## Weaknesses to pre-empt in Q&A

1. "Why not just add this to e-SAKSHI?" → Independence: the auditing layer
   must not be the recording system (same reason CAG ≠ ministries).
2. "What if your flags are wrong?" → Every signal is an indicator with
   visible thresholds and citations; officers classify outcomes; precision is
   measured, and false positives are a tracked metric, not a failure mode.
3. "Where does the data come from?" → Public official exports today; bulk
   work-level data via MoSPI arrangement; synthetic fixtures are permanently
   labeled and never mixed with official data.
4. "Who maintains the model?" → Governance cadence in `docs/SUSTAINABILITY.md`.
