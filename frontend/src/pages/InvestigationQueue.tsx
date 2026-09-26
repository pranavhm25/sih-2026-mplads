import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, describeLoadFailure, isBackendUnavailableFailure } from '../services/api'
import type { Officer, ProjectSummary, QueueResponse } from '../types/types'
import { EmptyState, ErrorState, Loading, MetaLine, PriorityMark, SignalChips } from '../components/ui/Bits'
import { BackendGate } from '../components/ui/BackendGate'
import { PRIORITY_ORDER } from '../lib/format'

const SIGNAL_OPTIONS = [
  { value: 'COST_ANOMALY', label: 'Cost anomaly' },
  { value: 'FIN_PHYS_GAP', label: 'F/P gap' },
  { value: 'DELAY', label: 'Delay' },
  { value: 'DUPLICATE', label: 'Duplicate candidate' },
  { value: 'ML_ANOMALY', label: 'ML unusual' },
  { value: 'AGENCY_CONCENTRATION', label: 'Agency concentration' },
  { value: 'DATA_QUALITY', label: 'Data quality' },
]

const PRIORITY_OPTIONS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export default function InvestigationQueue() {
  const [resp, setResp] = useState<QueueResponse | null>(null)
  const [meta, setMeta] = useState<{ version: string | null; is_synthetic: boolean | null } | null>(null)
  const [officers, setOfficers] = useState<Officer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [creating, setCreating] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)

  const [filters, setFilters] = useState({
    priority: '',
    signal_type: '',
    state: '',
    search: '',
    sort: 'priority',
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setUnavailable(false)
    try {
      const res = await api.queue({
        priority: filters.priority || undefined,
        signal_type: filters.signal_type || undefined,
        state: filters.state || undefined,
        search: filters.search || undefined,
        sort: filters.sort,
        limit: '200',
      })
      setResp(res.data)
      setMeta({ version: res.meta.dataset_version, is_synthetic: res.meta.is_synthetic })
    } catch (e) {
      setError(describeLoadFailure(e, 'Failed to load queue'))
      setUnavailable(isBackendUnavailableFailure(e))
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    api
      .officers()
      .then((r) => setOfficers(r.data))
      .catch(() => setOfficers([]))
  }, [])

  const states = useMemo(() => {
    const set = new Set((resp?.items ?? []).map((i) => i.state))
    return Array.from(set).sort()
  }, [resp])

  async function createCase(p: ProjectSummary) {
    setCreating(p.id)
    setFlash(null)
    try {
      const primary = officers.find((o) => o.role === 'INVESTIGATOR') ?? officers[0]
      const res = await api.createCase({
        project_id: p.id,
        assigned_officer_id: primary?.id,
        note: 'Case opened from the investigation queue.',
      })
      setFlash(`Case ${res.data.case_number} opened for ${p.work_id}.`)
      void load()
    } catch (e) {
      setFlash(e instanceof Error ? e.message : 'Could not create case')
    } finally {
      setCreating(null)
    }
  }

  const sortedItems = useMemo(() => {
    const items = [...(resp?.items ?? [])]
    if (filters.sort === 'priority') {
      items.sort(
        (a, b) =>
          (PRIORITY_ORDER[a.priority?.level ?? 'LOW'] ?? 9) -
            (PRIORITY_ORDER[b.priority?.level ?? 'LOW'] ?? 9) ||
          (b.priority?.score ?? 0) - (a.priority?.score ?? 0),
      )
    } else if (filters.sort === 'cost') {
      items.sort((a, b) => b.sanctioned_cost - a.sanctioned_cost)
    } else if (filters.sort === 'district') {
      items.sort((a, b) => a.district.localeCompare(b.district))
    }
    return items
  }, [resp, filters.sort])

  return (
    <div className="mx-auto max-w-[1400px]">
      <header className="mb-4">
        <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">Investigation Queue</h1>
        <MetaLine dataset={meta} />
        <p className="mt-0.5 text-meta text-ink-faint">
          Works ordered by converging evidence. Priority is a triage aid, not a finding.
        </p>
      </header>

      {/* Filter bar */}
      <div className="mb-3 grid grid-cols-2 items-center gap-3 border border-rule bg-paper px-3 py-2.5 sm:flex sm:flex-wrap">
        <label className="flex min-w-0 items-center gap-1.5 text-[12px] text-ink-soft">
          Priority
          <select
            className="field max-sm:w-0 max-sm:flex-1 py-1"
            value={filters.priority}
            onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value }))}
          >
            <option value="">All</option>
            {PRIORITY_OPTIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-0 items-center gap-1.5 text-[12px] text-ink-soft">
          Signal
          <select
            className="field max-sm:w-0 max-sm:flex-1 py-1"
            value={filters.signal_type}
            onChange={(e) => setFilters((f) => ({ ...f, signal_type: e.target.value }))}
          >
            <option value="">All</option>
            {SIGNAL_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-0 items-center gap-1.5 text-[12px] text-ink-soft">
          State
          <select
            className="field max-sm:w-0 max-sm:flex-1 py-1"
            value={filters.state}
            onChange={(e) => setFilters((f) => ({ ...f, state: e.target.value }))}
          >
            <option value="">All</option>
            {states.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-0 items-center gap-1.5 text-[12px] text-ink-soft">
          Sort
          <select
            className="field max-sm:w-0 max-sm:flex-1 py-1"
            value={filters.sort}
            onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value }))}
          >
            <option value="priority">Priority</option>
            <option value="cost">Sanctioned cost</option>
            <option value="district">District</option>
          </select>
        </label>
        <label className="col-span-2 flex items-center gap-1.5 text-[12px] text-ink-soft sm:col-span-1 sm:ml-auto">
          Search
          <input
            className="field min-w-0 flex-1 py-1 sm:w-52 sm:flex-none"
            placeholder="Work ID or description…"
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          />
        </label>
      </div>

      {flash && (
        <p className="mb-3 border border-forest/40 bg-forestsoft px-3 py-2 text-[12.5px] text-forest" role="status">
          {flash}
        </p>
      )}

      {loading ? (
        <Loading label="Loading queue…" />
      ) : error && unavailable ? (
        <BackendGate onReady={() => void load()} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : !sortedItems.length ? (
        <EmptyState
          title="No works match the selected filters."
          hint="Clear a filter or re-run detection to refresh signals."
        />
      ) : (
        <div className="-mx-4 overflow-x-auto border-t border-ink/60 sm:mx-0">
          <table className="ledger-table min-w-[900px]">
            <thead className="sticky top-0 bg-paper">
              <tr>
                <th className="w-32">Priority</th>
                <th className="w-28">Work ID</th>
                <th>Project</th>
                <th className="w-36">District</th>
                <th className="w-44">Primary signals</th>
                <th className="w-28">Case</th>
                <th className="w-36 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((p) => (
                <tr key={p.id}>
                  <td>{p.priority ? <PriorityMark level={p.priority.level} score={p.priority.score} /> : '—'}</td>
                  <td>
                    <Link to={`/projects/${p.id}`} className="num text-accent hover:underline">
                      {p.work_id}
                    </Link>
                  </td>
                  <td>
                    <Link to={`/projects/${p.id}`} className="block">
                      <p className="truncate font-medium">{p.description}</p>
                      <p className="text-meta text-ink-faint">
                        {p.category ?? 'Uncategorised'} · {p.status}
                      </p>
                    </Link>
                  </td>
                  <td className="text-[12.5px]">
                    {p.district}
                    <span className="block text-meta text-ink-faint">{p.state}</span>
                  </td>
                  <td>
                    <SignalChips types={p.primary_signals} />
                  </td>
                  <td>
                    <span
                      className={`font-plex text-[11px] font-semibold ${
                        p.case_status ? 'text-forest' : 'text-ink-faint'
                      }`}
                    >
                      {p.case_status ?? 'None'}
                    </span>
                  </td>
                  <td className="text-right">
                    {p.case_status ? (
                      <Link to={`/projects/${p.id}`} className="btn py-1">
                        View
                      </Link>
                    ) : (
                      <button
                        className="btn btn-primary py-1"
                        disabled={creating === p.id}
                        onClick={() => void createCase(p)}
                      >
                        {creating === p.id ? 'Opening…' : 'Open case'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 px-4 text-meta text-ink-faint sm:px-0">
            {resp?.total ?? 0} works in current view · server-side filters
          </p>
        </div>
      )}
    </div>
  )
}
