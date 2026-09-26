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
        <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">Investigation Cases</h1>
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
        <div className="-mx-4 overflow-x-auto sm:mx-0">
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
                    {statusLabel(c.status)}
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
        </div>
      )}
    </div>
  )
}

// Mirrors backend CASE_TRANSITIONS (app/core/constants.py).
const TRANSITIONS: Record<string, string[]> = {
  OPEN: ['UNDER_REVIEW', 'FIELD_VERIFICATION'],
  UNDER_REVIEW: ['FIELD_VERIFICATION', 'RESOLVED', 'ESCALATED'],
  FIELD_VERIFICATION: ['UNDER_REVIEW', 'RESOLVED', 'ESCALATED', 'CLOSED'],
  RESOLVED: ['UNDER_REVIEW', 'ESCALATED'],
  CLOSED: ['UNDER_REVIEW'],
  ESCALATED: ['UNDER_REVIEW'],
}

// Structured reasons for a NOT_SUBSTANTIATED closure (backend
// ResolutionReason). One pick + one sentence — deliberately lightweight.
const NOT_SUBSTANTIATED_REASONS: { value: string; label: string }[] = [
  { value: 'DOCUMENTATION_PROVIDED', label: 'Documentation provided' },
  { value: 'LEGITIMATE_DELAY', label: 'Legitimate implementation delay' },
  { value: 'DATA_QUALITY_ISSUE', label: 'Data quality issue in source records' },
  { value: 'FALSE_DUPLICATE_CANDIDATE', label: 'Separate works (duplicate flag not upheld)' },
  { value: 'APPROVED_VARIATION', label: 'Approved variation / sanctioned change' },
  { value: 'CONTEXTUAL_EXCEPTION', label: 'Contextual exception verified' },
  { value: 'OTHER', label: 'Other (explained in notes)' },
]

const REASON_LABEL: Record<string, string> = Object.fromEntries(
  NOT_SUBSTANTIATED_REASONS.map((r) => [r.value, r.label]),
)

const STATUS_LABEL: Record<string, string> = {
  OPEN: 'Open',
  UNDER_REVIEW: 'Under review',
  FIELD_VERIFICATION: 'Field verification',
  RESOLVED: 'Resolved',
  ESCALATED: 'Escalated',
  CLOSED: 'Closed — not substantiated',
}

const statusLabel = (s: string) => STATUS_LABEL[s] ?? s.replaceAll('_', ' ')

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
  const [showOutcomeForm, setShowOutcomeForm] = useState(false)
  const [outcomeReason, setOutcomeReason] = useState('')
  const [outcomeText, setOutcomeText] = useState('')

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
        <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[13px] text-ink-soft">
            <span className="font-plex font-semibold text-forest">{statusLabel(case_.status)}</span>
            {' · '}priority {case_.priority}
            {case_.assigned_officer ? ` · ${case_.assigned_officer.name}` : ' · unassigned'}
          </p>
          <Link to={`/projects/${case_.project_id}`} className="font-plex text-[12px] font-medium text-accent hover:underline">
            View Project Intelligence →
          </Link>
        </div>
      </header>

      {msg && (
        <p className="mt-3 border border-rule bg-paper px-3 py-2 text-[12.5px] text-ink-soft" role="status">
          {msg}
        </p>
      )}

      <p className="mt-3 border border-rule bg-accent-soft px-3 py-2 text-[12.5px] text-ink-soft">
        AI-generated risk flags require human verification and do not constitute
        findings of fraud. Final case outcomes are recorded by authorized officers.
      </p>

      <div className="mt-5 grid grid-cols-12 gap-6 lg:gap-8">
        <div className="col-span-12 min-w-0 space-y-8 lg:col-span-7">
          {/* Actions */}
          <section>
            <h2 className="section-title mb-2">Case actions</h2>
            <div className="flex flex-wrap gap-2 border-t border-ink/60 pt-3">
              {(TRANSITIONS[case_.status] ?? []).map((t) =>
                t === 'CLOSED' ? (
                  <button
                    key={t}
                    className="btn"
                    disabled={busy}
                    onClick={() => setShowOutcomeForm((v) => !v)}
                  >
                    → Not substantiated (close case)
                  </button>
                ) : (
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
                    → {t === 'ESCALATED' ? 'Substantiated — escalate' : t.replaceAll('_', ' ')}
                  </button>
                ),
              )}
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
            {showOutcomeForm && (
              <form
                className="mt-3 space-y-3 border border-rule bg-paper p-3"
                onSubmit={(e) => {
                  e.preventDefault()
                  void run(async () => {
                    if (!case_) return
                    const res = await api.updateCase(case_.id, {
                      status: 'CLOSED',
                      resolution_type: 'NOT_SUBSTANTIATED',
                      resolution_reason: outcomeReason,
                      resolution_summary: outcomeText.trim(),
                    })
                    setCase(res.data)
                    setShowOutcomeForm(false)
                    setOutcomeReason('')
                    setOutcomeText('')
                    setMsg(
                      'Case closed — not substantiated. The decision and reason are recorded in the audit trail.',
                    )
                  })
                }}
              >
                <p className="text-[12.5px] font-medium text-ink">
                  Close as not substantiated
                </p>
                <p className="text-meta text-ink-faint">
                  The available evidence did not substantiate the flagged concern.
                  This records a human investigation outcome — not a finding of fraud
                  or innocence. The original AI-generated flag stays on the record.
                </p>
                <label className="block text-[12px] text-ink-soft">
                  Reason category
                  <select
                    className="field mt-1 w-full"
                    value={outcomeReason}
                    onChange={(e) => setOutcomeReason(e.target.value)}
                    required
                  >
                    <option value="" disabled>
                      Select a reason…
                    </option>
                    {NOT_SUBSTANTIATED_REASONS.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-[12px] text-ink-soft">
                  Short explanation (recorded in the audit trail)
                  <textarea
                    className="field mt-1 w-full"
                    rows={3}
                    value={outcomeText}
                    onChange={(e) => setOutcomeText(e.target.value)}
                    placeholder="e.g. Documents verified with the district office; the two works are separate sanctioned projects."
                    required
                  />
                </label>
                <div className="flex gap-2">
                  <button className="btn btn-primary" type="submit" disabled={busy || !outcomeReason || !outcomeText.trim()}>
                    Record outcome
                  </button>
                  <button className="btn" type="button" disabled={busy} onClick={() => setShowOutcomeForm(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            )}
            {reportUrl && (
              <a href={reportUrl} className="mt-2 inline-block font-plex text-[12.5px] font-medium text-accent hover:underline" download>
                Download generated report (PDF) ↓
              </a>
            )}
            <p className="mt-2 text-meta text-ink-faint">
              Outcome classifications: confirmed concern · false positive · not substantiated · needs verification.
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
            {case_.resolution_reason && (
              <p className="mt-1 text-[12.5px] text-ink-soft">
                Reason: {REASON_LABEL[case_.resolution_reason] ?? case_.resolution_reason}
              </p>
            )}
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
        <div className="col-span-12 space-y-8 lg:col-span-5">
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
