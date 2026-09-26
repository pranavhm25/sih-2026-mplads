// API contracts mirroring backend/app/schemas/schemas.py

export interface Meta {
  dataset_version: string | null
  generated_at: string | null
  is_synthetic: boolean | null
}

export interface Envelope<T> {
  data: T
  meta: Meta
}

export interface Evidence {
  id: string
  field_name: string
  field_value: string
  reference_label: string | null
  reference_value: string | null
  calculation: string | null
}

export interface Signal {
  id: string
  signal_type: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  triggered: boolean
  title: string
  explanation: string
  observed_value: Record<string, unknown> | null
  reference_value: Record<string, unknown> | null
  difference_value: Record<string, unknown> | null
  source_type: 'RULE' | 'ML' | 'NLP' | 'BENCHMARK' | 'DATA_QUALITY'
  source_version: string
  created_at: string
  evidence: Evidence[]
  recommended_action: string | null
}

export interface Priority {
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  score: number
  signal_count: number
  reasons: string[]
}

export interface ProjectSummary {
  id: string
  work_id: string
  description: string
  district: string
  state: string
  category: string | null
  status: string
  sanctioned_cost: number
  latitude: number | null
  longitude: number | null
  priority: Priority | null
  primary_signals: string[]
  case_status: string | null
}

export interface Metrics {
  cost_deviation_pct: number | null
  peer_median_cost: number | null
  peer_p75_cost: number | null
  peer_percentile: number | null
  financial_physical_gap: number | null
  expenditure_ratio: number | null
  elapsed_days: number | null
  expected_duration_days: number | null
  delay_days: number | null
  agency_share_pct: number | null
  ml_anomaly_score: number | null
  duplicate_score: number | null
  calculated_at: string | null
  calculation_version: string | null
}

export interface Peer {
  peer_group_name: string
  peer_count: number
  median_cost: number | null
  p75_cost: number | null
  percentile: number | null
}

export interface RelatedProject {
  related_project_id: string
  work_id: string
  project_name: string
  district: string
  text_similarity: number | null
  location_distance_m: number | null
  cost_similarity: number | null
  category_match: boolean | null
  time_overlap: boolean | null
  /** Contextual validation ("similarity ≠ duplication"): null/undefined = data unavailable */
  vendor_match?: boolean | null
  contextual_confidence?: string | null
  combined_score: number
}

export interface ProjectDetail extends ProjectSummary {
  mp_name: string | null
  constituency: string | null
  location_text: string | null
  sector: string | null
  estimated_cost: number
  expenditure: number | null
  financial_progress: number
  physical_progress: number
  sanction_date: string | null
  start_date: string | null
  completion_date: string | null
  implementing_agency: string | null
  contractor_name: string | null
  expected_duration_days: number | null
  metrics: Metrics | null
  signals: Signal[]
  peers: Peer[]
  related: RelatedProject[]
  why_flagged: string | null
  dataset_version: string | null
  dataset_is_synthetic: boolean | null
}

export interface Officer {
  id: string
  name: string
  email: string
  role: string
  district: string | null
  is_active: boolean
}

export interface CaseEvent {
  id: string
  event_type: string
  actor_id: string | null
  from_status: string | null
  to_status: string | null
  metadata_json: Record<string, unknown> | null
  created_at: string
}

export interface CaseNote {
  id: string
  case_id: string
  author_id: string
  body: string
  created_at: string
  updated_at: string
  author: Officer | null
}

export interface CaseEvidence {
  id: string
  case_id: string
  signal_id: string | null
  description: string
  evidence_type: string
  file_reference: string | null
  created_at: string
}

export interface Case {
  id: string
  case_number: string
  project_id: string
  priority: string
  status: 'OPEN' | 'UNDER_REVIEW' | 'FIELD_VERIFICATION' | 'RESOLVED' | 'ESCALATED' | 'CLOSED'
  assigned_officer_id: string | null
  opened_at: string
  updated_at: string
  closed_at: string | null
  resolution_type: string | null
  resolution_reason: string | null
  resolution_summary: string | null
  project: ProjectSummary | null
  assigned_officer: Officer | null
  events: CaseEvent[]
  notes: CaseNote[]
  evidence: CaseEvidence[]
}

export interface Dataset {
  id: string
  name: string
  source_type: string
  source_label: string
  version: string
  is_synthetic: boolean
  ingested_at: string
  row_count: number
  quality_status: string
  quality_summary: Record<string, unknown> | null
  dataset_type?: string
  source_url?: string | null
  file_name?: string | null
  file_hash?: string | null
}

export interface DatasetListResponse {
  items: Dataset[]
  total: number
  offset: number
  limit: number
}

export interface ImportSummary {
  dataset_id: string
  dataset_type: string
  source_type: string
  status: string
  row_count: number
  valid_rows: number
  warning_rows: number
  error_rows: number
  quality_status: string
  quality_reasons: string[]
  is_synthetic: boolean
  file_name: string
  file_hash: string
  issue_counts_by_rule: Record<string, number>
  parse_notes: string[]
  duplicate_dataset: string | null
}

export interface ValidationIssueRow {
  row_number: number | null
  field: string | null
  rule: string
  severity: string
  message: string
  observed_value: string | null
}

export interface DatasetQualityReport {
  dataset_id: string
  dataset_type: string
  quality_status: string
  total_rows: number
  valid_rows: number
  warning_rows: number
  error_rows: number
  reasons: string[]
  missing_field_counts: Record<string, number>
  invalid_field_counts: Record<string, number>
  duplicate_counts: Record<string, number>
  parse_notes: string[]
  issue_count: number
  detection_issue_count: number
  issues: ValidationIssueRow[]
}

export interface DatasetRecords {
  dataset_id: string
  dataset_type: string
  fields: string[]
  records: Record<string, unknown>[]
  total: number
  offset: number
  limit: number
}

export interface FixtureInfo {
  name: string
  file_name: string
  dataset_type: string
  label: string
}

export interface DashboardData {
  total_works: number
  total_value: number
  high_priority_count: number
  critical_count: number
  delayed_count: number
  duplicate_candidate_count: number
  quality_exception_count: number
  case_open_count: number
  risk_distribution: Record<string, number>
  signal_distribution: Record<string, number>
  districts: { district: string; state: string; works: number; value: number; high: number }[]
  queue_preview: ProjectSummary[]
  dataset: Dataset | null
  map_points?: ProjectSummary[]
}

export interface QueueResponse {
  items: ProjectSummary[]
  total: number
  offset: number
  limit: number
}

// --- Backlog: security pack + stakeholder views ---------------------------

export interface AuthOfficer {
  id: string
  name: string
  email: string
  role: string
  stakeholder_role: string | null
  constituency: string | null
  state: string | null
  district: string | null
}

export interface LoginResponse {
  token: string
  officer: AuthOfficer
}

export interface AuditVerifyReport {
  valid: boolean
  broken_at_seq: number | null
  reason: string | null
  events_checked: number
  chain_tip?: string
}

export interface AuditEventRow {
  seq: number
  action: string
  actor_id: string | null
  entity_type: string | null
  entity_id: string | null
  payload: Record<string, unknown> | null
  prev_hash: string
  entry_hash: string
  created_at: string
}

export interface StakeholderSummary {
  scope: { role: string; label: string; note: string }
  works: { total: number; by_status: Record<string, number> }
  signals: {
    total: number
    by_type: Record<string, number>
    by_severity: Record<string, number>
  }
  cases: { total: number; open: number; by_status: Record<string, number> }
  mp_headlines: { work: string; headline: string; severity: string; note: string }[] | null
  district_attention: { district: string; high_signals: number }[] | null
}

export interface ValidationSummary {
  feedback: {
    confirmed_concern: number
    false_positive: number
    needs_verification: number
    precision: number | null
    note: string
  }
  flag_rate: {
    flagged_works: number    total_works: number
    rate: number | null
    note: string
  }
  signals_by_type: Record<string, number>
  quantified_target: string
}

export interface AlertDigestData {
  role: string
  watermark_seq: number
  floor_severity: string
  new_signals: {
    work: string
    district: string
    signal_type: string
    severity: string
    title: string
    created_at: string
  }[]
  cases_moved: {
    case_number: string
    status: string
    priority: string
    updated_at: string
  }[]
  counts: { new_signals: number; cases_moved: number }
  generated_at: string
}

export interface TrendsData {
  series: {
    dataset_id: string
    dataset_name: string
    ingested_at: string | null
    is_synthetic: boolean
    house: string | null
    allocated_limit: number | null
    works_recommended: number | null
    works_sanctioned: number | null
    works_completed: number | null
    expenditure: number | null
    monetary_unit: string
    as_of_date: string | null
  }[]
  completion_rates: { label: string; rate: number; is_synthetic: boolean }[] | null
  limitation: string
}

// ---------------- CAG-grounded validation (docs/CAG_VALIDATION.md) ----------------

export type CagValidationResult = 'FLAGGED' | 'PARTIAL' | 'MISSED' | 'NOT_VALIDATABLE'

export interface CagValidationPatternRow {
  pattern_id: string
  title: string
  result: CagValidationResult
  flagged: boolean | null
  validation_method: string
  work_ids: string[]
  reason: string | null
}

export interface CagValidationSummary {
  report_version: string
  generated_at: string | null
  disclaimer: string
  provenance: string
  summary: {
    patterns_total: number
    FLAGGED: number
    PARTIAL: number
    MISSED: number
    NOT_VALIDATABLE: number
    dataset_id: string
    dataset_quality_status: string
    detection_run_id: string
    detection_run_status: string
    detection_ruleset_version: string
    detection_model_version: string
    signals_emitted: number
    rows_imported: number
    validation_issues_recorded: number
  }
  patterns: CagValidationPatternRow[]
  queue_entry: Record<
    string,
    { priority: string | null; score: number | null; enters_queue: boolean }
  >
}

// ---------------- Synthetic Model Validation (docs/SYNTHETIC_VALIDATION.md) ----------------

export interface SyntheticScenarioSummary {
  totals: {
    records_evaluated: number
    injected: number
    normal: number
    tp: number
    fp: number
    tn: number
    fn: number
  }
  metrics: {
    precision: number | null
    recall: number | null
    f1: number | null
    false_positive_rate: number | null
    detection_rate: number | null
  }
  per_anomaly_type: Record<
    string,
    {
      injected: number
      detected: number
      missed: number
      expected_detector: string
      expected_detector_hits: number
      metrics: {
        precision: number | null
        recall: number | null
        f1: number | null
      }
    }
  >
  false_positive_count: number
  false_negative_count: number
  dataset_rows_imported: number
  detection_run_status: string
}

export interface SyntheticValidationReport {
  report_version: string
  generated_at: string | null
  language_discipline: string
  experiment_configuration: {
    seed: number
    reference_date: string
    threshold_tuning: string
    detector_versions: string[]
  }
  scenarios: Record<string, SyntheticScenarioSummary>
  overall: {
    cm: { tp: number; fp: number; tn: number; fn: number }
    metrics: {
      precision: number | null
      recall: number | null
      f1: number | null
      false_positive_rate: number | null
      detection_rate: number | null
    }
    total_injected: number
  }
}
