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
  status: 'OPEN' | 'UNDER_REVIEW' | 'FIELD_VERIFICATION' | 'RESOLVED' | 'ESCALATED'
  assigned_officer_id: string | null
  opened_at: string
  updated_at: string
  closed_at: string | null
  resolution_type: string | null
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
