// Central API client. Components never call fetch directly (AGENTS_RULES §3).
import type {
  Case,
  DashboardData,
  DatasetListResponse,
  DatasetQualityReport,
  DatasetRecords,
  Envelope,
  FixtureInfo,
  ImportSummary,
  Officer,
  ProjectDetail,
  QueueResponse,
} from '../types/types'

const BASE = '/api/v1'

class ApiError extends Error {
  status: number
  code?: string
  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<Envelope<T>> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let message = `Request failed (${res.status})`
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
  return res.json() as Promise<Envelope<T>>
}

export interface HealthData {
  status: string
  service: string
}

export const api = {
  health: () => request<HealthData>('/health'),
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
  generateReport: (caseId: string) =>
    request<{ report: { id: string; report_number: string; generated_at: string }; download_url: string }>(
      `/cases/${caseId}/report`,
      { method: 'POST' },
    ),
  datasets: () => request<DatasetListResponse>('/datasets'),
  datasetQuality: (id: string) => request<DatasetQualityReport>(`/datasets/${id}/quality`),
  datasetRecords: (id: string, limit = 50, offset = 0) =>
    request<DatasetRecords>(`/datasets/${id}/records?limit=${limit}&offset=${offset}`),
  fixtures: () => request<{ fixtures: FixtureInfo[] }>('/datasets/fixtures'),
  ingestFixture: (name: string) =>
    request<ImportSummary>(`/datasets/fixtures/${name}/ingest`, { method: 'POST' }),
  importFile: (file: File, datasetType?: string): Promise<Envelope<ImportSummary>> => {
    const form = new FormData()
    form.append('file', file)
    const qs = datasetType && datasetType !== 'AUTO_DETECT' ? `?dataset_type=${datasetType}` : ''
    return fetch(`${BASE}/datasets/import${qs}`, { method: 'POST', body: form }).then(
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
