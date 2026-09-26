# Drishti — Backend Schema

## 1. Database

Primary recommendation: PostgreSQL.

Naming convention:
- snake_case
- singular table names
- UUID primary keys for application entities
- source system identifiers preserved separately

## 2. Entity Relationship Overview

```text
dataset
  │
  └──< project
          │
          ├──< project_signal
          │       └── signal_evidence
          │
          ├──< project_peer
          │
          ├──< related_project
          │
          └──< investigation_case
                    │
                    ├──< case_event
                    ├──< case_note
                    ├──< case_evidence
                    └──< report
```

## 3. datasets

Stores ingestion/provenance metadata.

```text
id                  UUID PK
name                VARCHAR
source_type         VARCHAR   # OFFICIAL_PUBLIC_DASHBOARD | OFFICIAL_FILE_UPLOAD | OFFICIAL_DATASET_API | SYNTHETIC_FIXTURE
dataset_type        VARCHAR   # MP_ALLOCATION | SCHEME_AGGREGATE | WORK_LEVEL | OTHER_OFFICIAL_EXPORT | SYNTHETIC_FIXTURE
source_label        VARCHAR   # e.g. "MPLADS e-SAKSHI"
source_url          VARCHAR NULL
version             VARCHAR
is_synthetic        BOOLEAN
retrieved_at        TIMESTAMP NULL
file_name           VARCHAR NULL
file_hash           VARCHAR NULL   # sha256 — duplicate-upload guard
source_schema       JSONB NULL     # detected columns + canonical mapping record
ingested_at         TIMESTAMP
row_count           INTEGER
quality_status      VARCHAR   # GOOD | ACCEPTABLE | DEGRADED | FAILED (deterministic scale)
quality_summary     JSONB
created_at          TIMESTAMP
```

## 3a. mp_allocation_record

Normalized MP-level allocation rows (Prompt 3). Lok Sabha sources fill
`constituency`; Rajya Sabha sources fill `elected_nominated`. The other
house-specific column stays NULL — never invented.

```text
id                  UUID PK
dataset_id          UUID FK
serial_number       INTEGER NULL
state               VARCHAR NULL
mp_name             VARCHAR NULL
constituency        VARCHAR NULL   # Lok Sabha only
elected_nominated   VARCHAR NULL   # Rajya Sabha only
allocated_amount    NUMERIC(16,2) NULL
amount_unit         VARCHAR        # RUPEE | LAKH | CRORE — unit as in source
source_row_number   INTEGER
created_at          TIMESTAMP
```

## 3b. scheme_aggregate

Dashboard-level aggregate metrics per house (Prompt 3).

```text
id                                  UUID PK
dataset_id                          UUID FK
house                               VARCHAR NULL
allocated_limit                     NUMERIC(18,2) NULL
amount_consented_for_calamity       NUMERIC(18,2) NULL
works_recommended                   INTEGER NULL
works_sanctioned                    INTEGER NULL
works_completed                     INTEGER NULL
expenditure_completed_and_ongoing   NUMERIC(18,2) NULL
monetary_unit                       VARCHAR       # RUPEE | LAKH | CRORE
as_of_date                          DATE NULL
source_row_number                   INTEGER
created_at                          TIMESTAMP
```

## 3c. validation_issue

Row-level validation issues from ingestion (Prompt 3). ERROR rows are
excluded from import but preserved here — never silently discarded.

```text
id               UUID PK
dataset_id       UUID FK
row_number       INTEGER NULL
field            VARCHAR NULL
rule             VARCHAR       # e.g. missing_mp_name, negative_amount
duplicate_serial
duplicate_mp_record, aggregate_consistency_issue, ...
severity         VARCHAR       # ERROR | WARNING | INFO
message          TEXT
observed_value   TEXT NULL
created_at       TIMESTAMP
```

### Unit handling

Dashboard aggregates are displayed in Crore; allocation exports carry raw
rupee amounts. Values normalize together with their unit
(`value + unit`), and `to_rupees()` performs the only sanctioned explicit
conversion. Cross-unit comparison without conversion is prohibited.

## 4. projects

Canonical MPLADS work record.

```text
id                  UUID PK
dataset_id          UUID FK
work_id             VARCHAR UNIQUE WITHIN DATASET
mp_name             VARCHAR NULL
constituency        VARCHAR NULL
state               VARCHAR
district             VARCHAR
location_text       TEXT NULL
latitude            DECIMAL NULL
longitude           DECIMAL NULL
category            VARCHAR NULL
sector              VARCHAR NULL
description         TEXT
estimated_cost      NUMERIC
sanctioned_cost     NUMERIC
expenditure         NUMERIC
financial_progress  NUMERIC
physical_progress   NUMERIC
sanction_date       DATE NULL
start_date          DATE NULL
completion_date     DATE NULL
status              VARCHAR
implementing_agency VARCHAR NULL
contractor_name     VARCHAR NULL
expected_duration_days INTEGER NULL
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

## 5. project_metrics

Derived values. Keep these separate from source facts.

```text
id                  UUID PK
project_id          UUID FK UNIQUE
cost_deviation_pct  NUMERIC NULL
peer_median_cost    NUMERIC NULL
peer_p75_cost       NUMERIC NULL
peer_percentile     NUMERIC NULL
financial_physical_gap NUMERIC NULL
expenditure_ratio   NUMERIC NULL
elapsed_days        INTEGER NULL
delay_days          INTEGER NULL
agency_share_pct    NUMERIC NULL
ml_anomaly_score    NUMERIC NULL
duplicate_score     NUMERIC NULL
calculated_at       TIMESTAMP
calculation_version VARCHAR
```

## 6. project_signal

One row per detected signal.

```text
id                  UUID PK
project_id          UUID FK
signal_type         VARCHAR
severity            VARCHAR
triggered           BOOLEAN
title               VARCHAR
explanation         TEXT
observed_value      JSONB
reference_value     JSONB NULL
difference_value    JSONB NULL
source_type         VARCHAR
source_version      VARCHAR
created_at          TIMESTAMP
```

Allowed `source_type` examples:
- RULE
- ML
- NLP
- BENCHMARK
- DATA_QUALITY

## 7. signal_evidence

Fine-grained evidence supporting a signal.

```text
id                  UUID PK
signal_id           UUID FK
field_name          VARCHAR
field_value         TEXT
reference_label     VARCHAR NULL
reference_value     TEXT NULL
calculation         TEXT NULL
provenance          JSONB NULL
created_at          TIMESTAMP
```

## 8. peer_group

```text
id                  UUID PK
name                VARCHAR
district             VARCHAR NULL
sector              VARCHAR NULL
category            VARCHAR NULL
financial_year      VARCHAR NULL
size_band           VARCHAR NULL
definition          JSONB
created_at          TIMESTAMP
```

## 9. project_peer

Stores benchmark relationships.

```text
id                  UUID PK
project_id          UUID FK
peer_group_id       UUID FK
peer_count          INTEGER
median_cost         NUMERIC NULL
p75_cost            NUMERIC NULL
percentile          NUMERIC NULL
calculated_at       TIMESTAMP
```

## 10. related_project

Potentially related/duplicate projects.

```text
id                  UUID PK
project_id          UUID FK
related_project_id  UUID FK
text_similarity     NUMERIC NULL
location_distance_m NUMERIC NULL
cost_similarity     NUMERIC NULL
category_match      BOOLEAN NULL
time_overlap        BOOLEAN NULL
vendor_match        BOOLEAN NULL   # contextual validation; NULL = agency data unavailable
contextual_confidence VARCHAR NULL # high | medium | low | unavailable
combined_score      NUMERIC
relation_type       VARCHAR
created_at          TIMESTAMP
```

Contextual columns (migration `d8e9f0a1b2c3`): TF-IDF text similarity is a
candidate GENERATOR; `vendor_match` + `contextual_confidence` record the
independent evidence that decides whether a pair is a strong candidate
("similarity ≠ duplication" — see TRD TR-07).

## 11. investigation_case

```text
id                  UUID PK
case_number         VARCHAR UNIQUE
project_id          UUID FK
priority            VARCHAR
status              VARCHAR
assigned_officer_id UUID NULL
opened_at            TIMESTAMP
updated_at           TIMESTAMP
closed_at            TIMESTAMP NULL
resolution_type      VARCHAR NULL
resolution_summary   TEXT NULL
```

Suggested status values:
- OPEN
- UNDER_REVIEW
- FIELD_VERIFICATION
- RESOLVED
- ESCALATED

Suggested resolution values:
- CONFIRMED_CONCERN
- FALSE_POSITIVE
- NEEDS_VERIFICATION

## 12. case_event

Immutable-style audit trail.

```text
id                  UUID PK
case_id             UUID FK
event_type          VARCHAR
actor_id            UUID NULL
from_status         VARCHAR NULL
to_status           VARCHAR NULL
metadata            JSONB
created_at          TIMESTAMP
```

## 13. case_note

```text
id                  UUID PK
case_id             UUID FK
author_id           UUID
body                TEXT
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

## 14. case_evidence

```text
id                  UUID PK
case_id             UUID FK
signal_id           UUID NULL
description         TEXT
evidence_type       VARCHAR
file_reference      VARCHAR NULL
created_at          TIMESTAMP
```

## 15. officer

```text
id                  UUID PK
name                VARCHAR
email               VARCHAR UNIQUE
role                VARCHAR
district             VARCHAR NULL
is_active           BOOLEAN
created_at          TIMESTAMP
```

Roles:
- ADMIN
- INVESTIGATOR
- SUPERVISOR

## 16. rule_definition

```text
id                  UUID PK
rule_code           VARCHAR UNIQUE
name                VARCHAR
description         TEXT
definition          JSONB
severity             VARCHAR
source_reference     TEXT NULL
version              VARCHAR
enabled              BOOLEAN
created_at           TIMESTAMP
updated_at           TIMESTAMP
```

## 17. detection_run

```text
id                  UUID PK
dataset_id          UUID FK
model_version       VARCHAR
ruleset_version     VARCHAR
status               VARCHAR
started_at           TIMESTAMP
completed_at         TIMESTAMP NULL
summary              JSONB
error_message        TEXT NULL
```

## 18. report

```text
id                  UUID PK
case_id              UUID FK
report_number        VARCHAR UNIQUE
format               VARCHAR
file_reference       VARCHAR
generated_by         UUID
generated_at         TIMESTAMP
report_version       VARCHAR
```

## 18a. Backlog additions — security, stakeholder & optional data layers

### audit_event (tamper-evident chain)

```text
id            UUID PK
seq           INTEGER UNIQUE   -- chain position, 1..n
actor_id      UUID NULL
action        VARCHAR(80)      -- AUDIT_LOGIN, CASE_OPENED, REPORT_GENERATED, ...
entity_type   VARCHAR NULL
entity_id     UUID NULL
payload       JSON NULL
prev_hash     CHAR(64)         -- previous entry's hash (genesis = 64 zeros)
entry_hash    CHAR(64)         -- sha256(canonical event incl. prev_hash)
created_at    TIMESTAMP
```

Integrity rule: `entry_hash = sha256(seq ‖ prev_hash ‖ canonical_json(event))`.
Verification (`GET /api/v1/audit/verify`) re-walks the chain and reports the
first broken seq/reason. Auth: PBKDF2 `password_hash` + HMAC session tokens
on `officer`; `stakeholder_role`/`constituency`/`state` scope RBAC.

### alert_digest

```text
id               UUID PK
role             VARCHAR(40)   -- one watermark per stakeholder role
last_seen_seq    INTEGER       -- audit-seq watermark
last_generated_at TIMESTAMP NULL
created_at       TIMESTAMP
```

### payment_record (optional layer — only when a source provides payments)

```text
id             UUID PK
project_id     UUID FK → project
dataset_id     UUID FK → dataset
payment_ref    VARCHAR NULL
amount         NUMERIC(14,2)
currency       VARCHAR(10) DEFAULT 'INR'
unit           VARCHAR(10) DEFAULT 'RUPEE'
paid_on        DATE NULL
payee          VARCHAR NULL
stage          VARCHAR NULL
source_row_number INTEGER NULL
```

### asset_record (optional layer — asset verification status)

```text
id                   UUID PK
project_id           UUID FK → project
dataset_id           UUID FK → dataset
asset_description    TEXT NULL
geo_tagged_photo_ref VARCHAR NULL
verification_status  VARCHAR NULL
verified_at          TIMESTAMP NULL
source_row_number    INTEGER NULL
```

### officer extensions

```text
stakeholder_role  VARCHAR NULL  -- MP | DISTRICT_AUTHORITY | STATE_NODAL | MINISTRY | ADMIN
constituency      VARCHAR NULL
state             VARCHAR NULL
password_hash     VARCHAR NULL  -- pbkdf2_sha256$iterations$salt$hash
```

New signal type: `COMPLIANCE` (categorical guideline matching with citation
evidence; source_type=RULE, weight 3.5 in fusion). New API surface:
`/api/v1/auth/*`, `/api/v1/audit/*`, `/api/v1/stakeholder/summary`,
`/api/v1/validation/summary`, `/api/v1/alerts/digest`, `/api/v1/trends`.

Migration: `c4d5e6f7a8b9` (backlog security/stakeholder tables).

## 19. Recommended Indexes

- projects(work_id, dataset_id)
- projects(state, district)
- projects(category, sector)
- projects(status)
- projects(latitude, longitude)
- project_signal(project_id, severity)
- project_signal(signal_type)
- investigation_case(status, priority)
- investigation_case(assigned_officer_id)
- related_project(project_id, combined_score)

## 20. Integrity Rules

1. A signal must belong to an existing project.
2. Evidence must belong to an existing signal.
3. A case must reference an existing project.
4. Case transitions must be recorded as events.
5. Detection outputs must carry model/rule version.
6. Synthetic data must remain explicitly labelled.
7. No field should imply that an anomaly is proof of fraud.
