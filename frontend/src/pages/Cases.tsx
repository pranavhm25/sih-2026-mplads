import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../services/api'
import type { Case, Officer } from '../types/types'
import { EmptyState, ErrorState, Loading } from '../components/ui/Bits'
import { formatDateTime } from '../lib/format'

export function CasesList() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listCases()
      .then((r) => setCases(r.data))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load cases'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading label="Loading cases…" />
  if (error) return <ErrorState message={error} />

  return (
    <div className="mx-auto max-w-[1100px]">
      <header className="mb-4">
        <h1 className="text-[26px] font-semibold leading-tight">Investigation Cases</h1>
        <p className="mt-0.5 text-meta text-ink-faint">
          Officer-owned records. Every action is written to the case audit trail.
        </p>
      </header>
      {!cases.length ? (
        <EmptyState
          title="No cases have been opened yet."
          hint="Open a case from the Investigation Queue or a project page."
        />
      ) : (
        <table className="ledger-table border-t border-ink/60">
          <thead>
            <tr>
              <th>Case</th>
              <th>Work</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Officer</th>
              <th className="text-right">Updated</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/cases/${c.id}`} className="num font-semibold text-accent hover:underline">
                    {c.case_number}
                  </Link>
                </td>
                <td>
                  <p className="num text-[12px] text-ink-faint">{c.project?.work_id}</p>
                  <p className="max-w-[280px] truncate text-[12.5px]">{c.project?.description}</p>
                </td>
                <td>
                  <span className="font-plex text-[12px] font-semibold text-forest">
                    {c.status.replaceAll('_', ' ')}
                  </span>
                  {c.resolution_type && (
                    <span className="block text-meta text-ink-faint">
                      {c.resolution_type.replaceAll('_', ' ')}
                    </span>
                  )}
                </td>
                <td className="num">{c.priority}</td>
                <td className="text-[12.5px]">{c.assigned_officer?.name ?? 'Unassigned'}</td>
                <td className="num text-right text-[12px]">{formatDateTime(c.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

const TRANSITIONS: Record<string, string[]> = {
  OPEN: ['UNDER_REVIEW', 'FIELD_VERIFICATION'],
  UNDER_REVIEW: ['FIELD_VERIFICATION', 'RESOLVED', 'ESCALATED'],
  FIELD_VERIFICATION: ['UNDER_REVIEW', 'RESOLVED', 'ESCALATED'],
  RESOLVED: ['UNDER_REVIEW'],
  ESCALATED: ['UNDER_REVIEW'],
}

export function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const [case_, setCase] = useState<Case | null>(null)
  const [officers, setOfficers] = useState<Officer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [reportUrl, setReportUrl] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const res = await api.getCase(id)
      setCase(res.data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load case')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    api
      .officers()
      .then((r) => setOfficers(r.data))
      .catch(() => setOfficers([]))
  }, [])

  async function run(fn: () => Promise<void>) {
    setBusy(true)
    setMsg(null)
    try {
      await fn()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Loading label="Loading case…" />
  if (error) return <ErrorState message={error} onRetry={() => void load()} />
  if (!case_) return <ErrorState message="Case not found." onRetry={() => void load()} />

  const author = officers[0]

  return (
    <div className="mx-auto max-w-[1100px]">
      <header className="border-b-2 border-ink pb-4">
        <p className="num text-[13px] text-ink-faint">{case_.case_number}</p>
        <h1 className="mt-0.5 text-[24px] font-semibold leading-snug">
          {case_.project?.description ?? 'Investigation case'}
        </h1>
        <p className="mt-1 text-[13px] text-ink-soft">
          <span className="font-plex font-semibold text-forest">{case_.status.replaceAll('_', ' ')}</span>
          {' · '}priority {case_.priority}
          {case_.assigned_officer ? ` · ${case_.assigned_officer.name}` : ' · unassigned'}
        </p>
      </header>

      {msg && (
        <p className="mt-3 border border-rule bg-paper px-3 py-2 text-[12.5px] text-ink-soft" role="status">
          {msg}
        </p>
      )}

      <div className="mt-5 grid grid-cols-12 gap-8">
        <div className="col-span-7 min-w-0 space-y-8">
          {/* Actions */}
          <section>
            <h2 className="section-title mb-2">Case actions</h2>
            <div className="flex flex-wrap gap-2 border-t border-ink/60 pt-3">
              {(TRANSITIONS[case_.status] ?? []).map((t) => (
                <button
                  key={t}
                  className="btn"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      const payload: Record<string, unknown> = { status: t }
                      if (t === 'RESOLVED') payload.resolution_type = 'NEEDS_VERIFICATION'
                      const res = await api.updateCase(case_.id, payload)
                      setCase(res.data)
                      setMsg(`Status → ${res.data.status.replaceAll('_', ' ')}.`)
                    })
                  }
                >
                  → {t.replaceAll('_', ' ')}
                </button>
              ))}
              <button
                className="btn btn-primary"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    const res = await api.generateReport(case_.id)
                    setReportUrl(res.data.download_url)
                    setMsg(`Report ${res.data.report.report_number} generated.`)
                    await load()
                  })
                }
              >
                Generate audit report
              </button>
            </div>
            {reportUrl && (
              <a href={reportUrl} className="mt-2 inline-block font-plex text-[12.5px] font-medium text-accent hover:underline" download>
                Download generated report (PDF) ↓
              </a>
            )}
            <p className="mt-2 text-meta text-ink-faint">
              Resolution classifications: confirmed concern · false positive · needs verification.
            </p>
          </section>

          {/* Feedback */}
          <section>
            <h2 className="section-title mb-2">Officer feedback (classification)</h2>
            <div className="flex gap-2 border-t border-ink/60 pt-3">
              {['CONFIRMED_CONCERN', 'FALSE_POSITIVE', 'NEEDS_VERIFICATION'].map((rt) => (
                <button
                  key={rt}
                  className={`btn ${case_.resolution_type === rt ? 'btn-primary' : ''}`}
                  disabled={busy || !author}
                  onClick={() =>
                    void run(async () => {
                      if (!author) return
                      const res = await api.recordFeedback(case_.id, {
                        resolution_type: rt,
                        officer_id: author.id,
                      })
                      setCase(res.data)
                      setMsg(`Feedback recorded: ${rt.replaceAll('_', ' ')}.`)
                    })
                  }
                >
                  {rt.replaceAll('_', ' ')}
                </button>
              ))}
            </div>
            {case_.resolution_summary && (
              <p className="mt-2 text-[12.5px] text-ink-soft">Summary: {case_.resolution_summary}</p>
            )}
          </section>

          {/* Notes */}
          <section>
            <h2 className="section-title mb-2">Officer notes</h2>
            <div className="border-t border-ink/60 pt-3">
              {case_.notes.length ? (
                case_.notes.map((n) => (
                  <div key={n.id} className="border-b border-rule py-2">
                    <p className="text-meta text-ink-faint">
                      {n.author?.name ?? 'Officer'} · {formatDateTime(n.created_at)}
                    </p>
                    <p className="text-[13px]">{n.body}</p>
                  </div>
                ))
              ) : (
                <p className="text-[13px] text-ink-faint">No notes recorded yet.</p>
              )}
              <label className="mt-3 block text-[12px] text-ink-soft">
                Add note
                <textarea
                  className="field mt-1 w-full"
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Observation, verification result, call reference…"
                />
              </label>
              <button
                className="btn mt-2"
                disabled={busy || !note.trim() || !author}
                onClick={() =>
                  void run(async () => {
                    if (!author) return
                    const res = await api.addNote(case_.id, { author_id: author.id, body: note.trim() })
                    setCase(res.data)
                    setNote('')
                    setMsg('Note recorded.')
                  })
                }
              >
                Record note
              </button>
            </div>
          </section>
        </div>

        {/* Side: project link + audit trail */}
        <div className="col-span-5 space-y-8">
          {case_.project && (
            <section>
              <h2 className="section-title mb-2">Investigated work</h2>
              <div className="border-t border-ink/60 pt-3 text-[13px]">
                <p className="num text-ink-faint">{case_.project.work_id}</p>
                <p className="mt-0.5 font-medium">{case_.project.description}</p>
                <p className="text-ink-soft">
                  {case_.project.district} · {case_.project.category ?? '—'}
                </p>
                <Link
                  to={`/projects/${case_.project.id}`}
                  className="mt-1 inline-block font-plex text-[12px] font-medium text-accent hover:underline"
                >
                  Open Project Intelligence →
                </Link>
              </div>
            </section>
          )}

          <section>
            <h2 className="section-title mb-2">Audit trail</h2>
            <ol className="space-y-1.5 border-t border-ink/60 pt-3">
              {[...case_.events].reverse().map((e) => (
                <li key={e.id} className="text-[12.5px]">
                  <span className="num text-ink-faint">{formatDateTime(e.created_at)}</span>
                  {' — '}
                  <span className="font-plex font-semibold">{e.event_type.replaceAll('_', ' ')}</span>
                  {e.from_status || e.to_status ? (
                    <span className="text-ink-soft">
                      {' '}
                      ({e.from_status?.replaceAll('_', ' ') ?? '—'} → {e.to_status?.replaceAll('_', ' ') ?? '—'})
                    </span>
                  ) : null}
                </li>
              ))}
              {!case_.events.length && <li className="text-[13px] text-ink-faint">No events recorded.</li>}
            </ol>
          </section>
        </div>
      </div>
    </div>
  )
}
