// Central API client. Components never call fetch directly (AGENTS_RULES §3).
import type {
  AlertDigestData,
  AuditEventRow,
  AuditVerifyReport,
  Case,
  DashboardData,
  DatasetListResponse,
  DatasetQualityReport,
  DatasetRecords,
  Envelope,
  FixtureInfo,
  ImportSummary,
  AuthOfficer,
  LoginResponse,
  Officer,
  ProjectDetail,
  QueueResponse,
  StakeholderSummary,
  TrendsData,
  ValidationSummary,
  CagValidationSummary,
} from '../types/types'

export const API_HOST = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
export const BASE = `${API_HOST}/api/v1`

export function resolveApiUrl(path: string): string {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${API_HOST}${normalized}`
}

const TOKEN_KEY = 'drishti.token'

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function storeToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

class ApiError extends Error {
  status: number
  code?: string
  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function toApiError(res: Response): Promise<ApiError> {
  let message = `Request failed (${res.status})`
  let code: string | undefined
  try {
    const body = await res.json()
    message = body?.error?.message ?? body?.detail?.error?.message ?? body?.detail ?? message
    code = body?.error?.code ?? body?.detail?.error?.code
  } catch {
    /* keep default */
  }
  return new ApiError(res.status, message, code)
}

async function request<T>(path: string, init?: RequestInit): Promise<Envelope<T>> {
  const res = await fetch(`${BASE}${path}`, {
    headers: authHeaders(),
    ...init,
  })
  if (!res.ok) throw await toApiError(res)
  return res.json() as Promise<Envelope<T>>
}

/** Like request(), for endpoints that return bare JSON without the {data, meta} envelope. */
async function bareRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: authHeaders(),
    ...init,
  })
  if (!res.ok) throw await toApiError(res)
  return res.json() as Promise<T>
}

export interface HealthData {
  status: string
  service: string
}

export const api = {
  // /api/v1/health intentionally returns bare JSON (liveness probe), not the envelope.
  health: () => bareRequest<HealthData>('/health'),
  dashboard: () => request<DashboardData>('/dashboard/summary'),
  queue: (params: Record<string, string | undefined>) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v) qs.set(k, v)
    })
    return request<QueueResponse>(`/projects?${qs.toString()}`)
  },
  project: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  officers: () => request<Officer[]>('/officers'),
  createCase: (payload: { project_id: string; assigned_officer_id?: string; note?: string }) =>
    request<Case>('/cases', { method: 'POST', body: JSON.stringify(payload) }),
  updateCase: (
    id: string,
    payload: { status?: string; resolution_type?: string; resolution_summary?: string; assigned_officer_id?: string },
  ) => request<Case>(`/cases/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  addNote: (id: string, payload: { author_id: string; body: string }) =>
    request<Case>(`/cases/${id}/notes`, { method: 'POST', body: JSON.stringify(payload) }),
  recordFeedback: (
    id: string,
    payload: { resolution_type: string; officer_id: string; summary?: string },
  ) => request<Case>(`/cases/${id}/feedback`, { method: 'POST', body: JSON.stringify(payload) }),
  listCases: () => request<Case[]>('/cases'),
  getCase: (id: string) => request<Case>(`/cases/${id}`),
  generateReport: async (caseId: string) => {
    const res = await request<{ report: { id: string; report_number: string; generated_at: string }; download_url: string }>(
      `/cases/${caseId}/report`,
      { method: 'POST' },
    )
    if (res.data && res.data.download_url) {
      res.data.download_url = resolveApiUrl(res.data.download_url)
    }
    return res
  },
  demoSeed: () =>
    request<{
      dataset: string
      name: string
      version: string
      row_count: number
      quality_status: string
      run_id: string
      run_status: string
      message: string
    }>('/datasets/demo-seed', { method: 'POST' }),
  datasets: () => request<DatasetListResponse>('/datasets'),
  datasetQuality: (id: string) => request<DatasetQualityReport>(`/datasets/${id}/quality`),
  datasetRecords: (id: string, limit = 50, offset = 0) =>
    request<DatasetRecords>(`/datasets/${id}/records?limit=${limit}&offset=${offset}`),
  fixtures: () => request<{ fixtures: FixtureInfo[] }>('/datasets/fixtures'),
  // Backlog: auth + audit chain
  login: (email: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  authMe: () => request<AuthOfficer>('/auth/me'),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
  auditVerify: () => request<AuditVerifyReport>('/audit/verify'),
  auditEvents: (limit = 50) => request<AuditEventRow[]>(`/audit/events?limit=${limit}`),
  stakeholderSummary: () => request<StakeholderSummary>('/stakeholder/summary'),
  validationSummary: () => request<ValidationSummary>('/validation/summary'),
  alertDigest: () => request<AlertDigestData>('/alerts/digest'),
  ackDigest: () =>
    request<{ role: string; last_seen_seq: number; acked_at: string }>(
      '/alerts/digest/ack',
      { method: 'POST' },
    ),
  trends: () => request<TrendsData>('/trends'),
  // CAG-grounded validation (docs/CAG_VALIDATION.md) — representative,
  // synthetic reproduction of documented patterns; never CAG case data.
  cagValidationSummary: () => request<CagValidationSummary>('/validation/cag/summary'),
  ingestFixture: (name: string) =>
    request<ImportSummary>(`/datasets/fixtures/${name}/ingest`, { method: 'POST' }),
  importFile: (file: File, datasetType?: string): Promise<Envelope<ImportSummary>> => {
    const form = new FormData()
    form.append('file', file)
    const qs = datasetType && datasetType !== 'AUTO_DETECT' ? `?dataset_type=${datasetType}` : ''
    const token = getStoredToken()
    const headers: Record<string, string> = {}
    if (token) headers.Authorization = `Bearer ${token}`
    return fetch(`${BASE}/datasets/import${qs}`, { method: 'POST', headers, body: form }).then(
      async (res) => {
        if (!res.ok) {
          let message = `Import failed (${res.status})`
          let code: string | undefined
          try {
            const body = await res.json()
            message = body?.error?.message ?? body?.detail?.error?.message ?? body?.detail ?? message
            code = body?.error?.code ?? body?.detail?.error?.code
          } catch {
            /* keep default */
          }
          throw new ApiError(res.status, message, code)
        }
        return res.json() as Promise<Envelope<ImportSummary>>
      },
    )
  },
}

export { ApiError }
