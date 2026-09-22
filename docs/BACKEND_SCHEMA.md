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
source_type         VARCHAR
source_label        VARCHAR
version             VARCHAR
is_synthetic        BOOLEAN
ingested_at         TIMESTAMP
row_count           INTEGER
quality_status      VARCHAR
quality_summary     JSONB
created_at          TIMESTAMP
```

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
combined_score      NUMERIC
relation_type       VARCHAR
created_at          TIMESTAMP
```

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
