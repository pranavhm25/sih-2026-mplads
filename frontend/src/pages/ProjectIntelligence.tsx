import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../services/api'
import type { Case, Officer, ProjectDetail, Signal } from '../types/types'
import { ErrorState, Loading, PriorityMark } from '../components/ui/Bits'
import { formatDate, formatINR, formatPct, signalLabel } from '../lib/format'

// One evidence-ledger row per signal: SIGNAL | OBSERVED | REFERENCE | DELTA.
function ledgerRows(s: Signal): { signal: string; observed: string; reference: string; delta: string } {
  switch (s.signal_type) {
    case 'FIN_PHYS_GAP': {
      const o = s.observed_value ?? {}
      const d = s.difference_value ?? {}
      return {
        signal: 'Financial / Physical',
        observed: `${o.financial_pct ?? '—'}% / ${o.physical_pct ?? '—'}%`,
        reference: 'financial ≈ physical',
        delta: `${d.gap_pp != null ? '+' : ''}${Number(d.gap_pp ?? 0).toFixed(0)} pp`,
      }
    }
    case 'COST_ANOMALY': {
      const o = s.observed_value ?? {}
      const r = s.reference_value ?? {}
      const d = s.difference_value ?? {}
      return {
        signal: 'Cost vs peers',
        observed: formatINR(Number(o.sanctioned_cost ?? 0)),
        reference: `${formatINR(Number(r.peer_median ?? 0))} median`,
        delta: formatPct(Number(d.deviation_pct ?? 0)),
      }
    }
    case 'DELAY': {
      const o = s.observed_value ?? {}
      const r = s.reference_value ?? {}
      const d = s.difference_value ?? {}
      return {
        signal: 'Duration',
        observed: `${o.elapsed_days ?? '—'} days`,
        reference: `${r.expected_days ?? '—'} days expected`,
        delta: `+${d.delay_days ?? 0}d`,
      }
    }
    case 'DUPLICATE': {
      const d = s.difference_value ?? {}
      const ev = s.evidence.find((e) => e.field_name === 'location distance')
      const r = s.reference_value ?? {}
      return {
        signal: 'Duplicate candidate',
        observed: `${Math.round(Number(d.combined_score ?? 0) * 100)}% similarity`,
        reference: `vs ${r.related_work_id ?? '—'}`,
        delta: ev ? `${Number(ev.field_value.replace(' m', '')).toFixed(0)}m away` : 'location n/a',
      }
    }
    case 'ML_ANOMALY': {
      const o = s.observed_value ?? {}
      return {
        signal: 'ML unusualness',
        observed: Number(o.anomaly_score ?? 0).toFixed(3),
        reference: 'typical > −0.05',
        delta: 'statistical',
      }
    }
    case 'DATA_QUALITY':
      return { signal: 'Data quality', observed: s.title, reference: '—', delta: '—' }
    default:
      return { signal: signalLabel(s.signal_type), observed: s.title, reference: '—', delta: '—' }
  }
}

export default function ProjectIntelligence() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  const [case_, setCase] = useState<Case | null>(null)
  const [officers, setOfficers] = useState<Officer[]>([])
  const [note, setNote] = useState('')
  const [caseBusy, setCaseBusy] = useState(false)
  const [caseMsg, setCaseMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.project(id)
      setProject(res.data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load project')
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

  const triggered = useMemo(() => (project?.signals ?? []).filter((s) => s.triggered), [project])

  async function ensureCase(): Promise<Case | null> {
    if (case_) return case_
    if (!project) return null
    const primary = officers.find((o) => o.role === 'INVESTIGATOR') ?? officers[0]
    const res = await api.createCase({
      project_id: project.id,
      assigned_officer_id: primary?.id,
      note: 'Case opened from Project Intelligence.',
    })
    setCase(res.data)
    return res.data
  }

  async function handleCreateCase() {
    if (!project) return
    setCaseBusy(true)
    setCaseMsg(null)
    try {
      const c = await ensureCase()
      setCaseMsg(`Case ${c?.case_number} is open.`)
    } catch (e) {
      setCaseMsg(e instanceof Error ? e.message : 'Could not create case')
    } finally {
      setCaseBusy(false)
    }
  }

  async function handleAdvance() {
    if (!case_) return
    setCaseBusy(true)
    setCaseMsg(null)
    const next: Record<string, string> = {
      OPEN: 'UNDER_REVIEW',
      UNDER_REVIEW: 'FIELD_VERIFICATION',
      FIELD_VERIFICATION: 'RESOLVED',
    }
    const target = next[case_.status]
    if (!target) {
      setCaseMsg('Case is closed. Reopen from the Cases screen if needed.')
      setCaseBusy(false)
      return
    }
    try {
      const payload: Record<string, unknown> = { status: target }
      if (target === 'RESOLVED') payload.resolution_type = 'NEEDS_VERIFICATION'
      const res = await api.updateCase(case_.id, payload)
      setCase(res.data)
      setCaseMsg(`Status → ${res.data.status}.`)
    } catch (e) {
      setCaseMsg(e instanceof Error ? e.message : 'Transition failed')
    } finally {
      setCaseBusy(false)
    }
  }

  async function handleAddNote() {
    if (!case_ || !note.trim()) return
    const author = officers[0]
    if (!author) return
    setCaseBusy(true)
    try {
      const res = await api.addNote(case_.id, { author_id: author.id, body: note.trim() })
      setCase(res.data)
      setNote('')
      setCaseMsg('Note recorded in the case file.')
    } catch (e) {
      setCaseMsg(e instanceof Error ? e.message : 'Could not add note')
    } finally {
      setCaseBusy(false)
    }
  }

  if (loading) return <Loading label="Loading project…" />
  if (error) return <ErrorState message={error} onRetry={() => void load()} />
  if (!project) return <ErrorState message="Project not found." onRetry={() => void load()} />

  const m = project.metrics

  return (
    <div className="mx-auto max-w-[1200px]">
      {/* Header */}
      <header className="border-b-2 border-ink pb-4">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <p className="num text-[13px] text-ink-faint">{project.work_id}</p>
            <h1 className="mt-0.5 max-w-2xl text-[24px] font-semibold leading-snug">{project.description}</h1>
            <p className="mt-1 text-[13px] text-ink-soft">
              {project.district}, {project.state} · {project.category ?? 'Uncategorised'} ·{' '}
              <span className="font-mono">{project.status}</span>
            </p>
            <p className="mt-1 text-meta text-ink-faint">
              dataset {project.dataset_version ?? '—'}
              {project.dataset_is_synthetic && (
                <span className="provenance-chip ml-2">Synthetic demo data</span>
              )}
            </p>
          </div>
          <div className="shrink-0 border border-rule bg-paper px-4 py-3 text-right">
            {project.priority ? (
              <>
                <p className="section-title">Investigation priority</p>
                <p className="mt-1.5">
                  <PriorityMark level={project.priority.level} score={project.priority.score} />
                </p>
                <p className="mt-1.5 font-plex text-[12px] font-semibold text-ink">
                  {project.priority.signal_count} signal{project.priority.signal_count === 1 ? '' : 's'} converge
                </p>
              </>
            ) : (
              <>
                <p className="section-title">Priority</p>
                <p className="mt-1 font-plex text-[12px] text-ink-faint">No triggered signals</p>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Why this project is here */}
      {project.why_flagged && (
        <section className="mt-4 border-l-2 border-accent bg-accent-soft/60 px-4 py-3">
          <h2 className="section-title">Why this project is here</h2>
          <p className="mt-1 max-w-4xl text-[13.5px] leading-relaxed text-ink">{project.why_flagged}</p>
        </section>
      )}

      <div className="mt-6 grid grid-cols-12 gap-8">
        {/* Main column */}
        <div className="col-span-8 min-w-0">
          {/* Evidence ledger */}
          <section>
            <h2 className="section-title mb-2">Evidence ledger</h2>
            <table className="ledger-table border-t border-ink/60">
              <thead>
                <tr>
                  <th>Signal</th>
                  <th>Observed</th>
                  <th>Reference</th>
                  <th className="text-right">Delta</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {triggered.map((s) => {
                  const row = ledgerRows(s)
                  const open = expanded === s.id
                  return (
                    <FragmentRow
                      key={s.id}
                      row={row}
                      severity={s.severity}
                      source={s.source_type}
                      open={open}
                      onToggle={() => setExpanded(open ? null : s.id)}
                      colSpan={5}
                    >
                      <div className="border-l-2 border-accent bg-accent-soft/40 px-4 py-3">
                        <p className="section-title">Rule</p>
                        <p className="font-plex text-[13px] font-semibold">{signalLabel(s.signal_type)} — {s.title}</p>
                        <p className="section-title mt-3">Evidence</p>
                        <p className="text-[13px] leading-relaxed text-ink-soft">{s.explanation}</p>
                        {s.evidence.length > 0 && (
                          <table className="ledger-table mt-2">
                            <thead>
                              <tr>
                                <th>Field</th>
                                <th>Observed</th>
                                <th>Reference</th>
                                <th>Calculation</th>
                              </tr>
                            </thead>
                            <tbody>
                              {s.evidence.map((e) => (
                                <tr key={e.id}>
                                  <td className="font-mono text-[11.5px]">{e.field_name}</td>
                                  <td className="num">{e.field_value}</td>
                                  <td className="num">
                                    {e.reference_label ? `${e.reference_label}: ` : ''}
                                    {e.reference_value ?? '—'}
                                  </td>
                                  <td className="text-[12px] text-ink-soft">{e.calculation ?? '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                        <p className="section-title mt-3">Action</p>
                        <p className="text-[13px] font-medium text-ink">{s.recommended_action}</p>
                        <p className="mt-2 text-meta text-ink-faint">
                          {s.source_type} · {s.source_version} · {formatDate(s.created_at)}
                        </p>
                      </div>
                    </FragmentRow>
                  )
                })}
                {!triggered.length && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-ink-faint">
                      No triggered signals for this work.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          {/* Peer context */}
          <section className="mt-8">
            <h2 className="section-title mb-2">Peer context</h2>
            {project.peers.length ? (
              <table className="ledger-table border-t border-ink/60">
                <thead>
                  <tr>
                    <th>Peer group</th>
                    <th className="text-right">Peers</th>
                    <th className="text-right">Median cost</th>
                    <th className="text-right">P75</th>
                    <th className="text-right">This work percentile</th>
                  </tr>
                </thead>
                <tbody>
                  {project.peers.map((p) => (
                    <tr key={p.peer_group_name}>
                      <td className="font-medium">{p.peer_group_name}</td>
                      <td className="num text-right">{p.peer_count}</td>
                      <td className="num text-right">{p.median_cost != null ? formatINR(p.median_cost) : '—'}</td>
                      <td className="num text-right">{p.p75_cost != null ? formatINR(p.p75_cost) : '—'}</td>
                      <td className="num text-right font-semibold">{p.percentile?.toFixed(0)}th</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="border border-dashed border-rule bg-paper/60 px-4 py-3 text-[13px] text-ink-faint">
                Insufficient comparable projects for a peer benchmark — no benchmark is fabricated.
              </p>
            )}
          </section>

          {/* Related works */}
          <section className="mt-8">
            <h2 className="section-title mb-2">Potentially related works</h2>
            {project.related.length ? (
              <table className="ledger-table border-t border-ink/60">
                <thead>
                  <tr>
                    <th>Work</th>
                    <th className="text-right">Text sim.</th>
                    <th className="text-right">Distance</th>
                    <th className="text-right">Cost sim.</th>
                    <th className="text-right">Combined</th>
                    <th className="w-20" />
                  </tr>
                </thead>
                <tbody>
                  {project.related.map((r) => (
                    <tr key={r.related_project_id}>
                      <td>
                        <p className="num text-[12px] text-accent">
                          <Link to={`/projects/${r.related_project_id}`}>{r.work_id}</Link>
                        </p>
                        <p className="truncate text-[12.5px]">{r.project_name}</p>
                      </td>
                      <td className="num text-right">{r.text_similarity != null ? `${Math.round(r.text_similarity * 100)}%` : '—'}</td>
                      <td className="num text-right">{r.location_distance_m != null ? `${r.location_distance_m.toFixed(0)} m` : 'n/a'}</td>
                      <td className="num text-right">{r.cost_similarity != null ? `${Math.round(r.cost_similarity * 100)}%` : '—'}</td>
                      <td className="num text-right font-semibold">{Math.round(r.combined_score * 100)}%</td>
                      <td className="text-right text-meta text-ink-faint">candidate</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-[13px] text-ink-faint">No related works detected.</p>
            )}
            <p className="mt-1 text-meta text-ink-faint">
              Related works are duplicate candidates for verification — not confirmed duplicates.
            </p>
          </section>

          {/* Timeline */}
          <section className="mt-8">
            <h2 className="section-title mb-2">Timeline</h2>
            <ol className="space-y-1.5 border-t border-ink/60 pt-3 text-[13px]">
              <TimelineItem label="Sanctioned" value={formatDate(project.sanction_date)} />
              <TimelineItem label="Started" value={formatDate(project.start_date)} />
              <TimelineItem
                label="Expected completion"
                value={
                  project.sanction_date && project.expected_duration_days
                    ? formatDate(
                        new Date(
                          new Date(project.sanction_date).getTime() +
                            project.expected_duration_days * 86400000,
                        ).toISOString(),
                      )
                    : '—'
                }
              />
              <TimelineItem label="Recorded completion" value={formatDate(project.completion_date)} />
              {m?.delay_days != null && m.delay_days > 0 && (
                <li className="text-vermilion">
                  <span className="font-semibold font-plex">+{m.delay_days} days</span> beyond expected duration
                </li>
              )}
            </ol>
          </section>
        </div>

        {/* Side column */}
        <div className="col-span-4 space-y-8">
          {/* Source facts */}
          <section>
            <h2 className="section-title mb-2">Source record</h2>
            <dl className="space-y-1.5 border-t border-ink/60 pt-3 text-[13px]">
              <Fact label="Estimated" value={formatINR(project.estimated_cost)} />
              <Fact label="Sanctioned" value={formatINR(project.sanctioned_cost)} />
              <Fact label="Expenditure" value={project.expenditure != null ? formatINR(project.expenditure) : 'Not reported'} />
              <Fact label="Financial progress" value={`${project.financial_progress}%`} />
              <Fact label="Physical progress" value={`${project.physical_progress}%`} />
              <Fact label="Implementing agency" value={project.implementing_agency ?? '—'} />
              <Fact label="Contractor / vendor" value={project.contractor_name ?? 'Not recorded'} />
              <Fact label="Location" value={project.location_text ?? '—'} />
            </dl>
          </section>

          {/* Recommended verification */}
          <section>
            <h2 className="section-title mb-2">Recommended verification</h2>
            <ul className="space-y-2 border-t border-ink/60 pt-3">
              {triggered
                .filter((s) => s.recommended_action)
                .map((s) => (
                  <li key={s.id} className="flex gap-2 text-[12.5px] leading-snug">
                    <span className="mt-0.5 font-mono text-[10px] text-ink-faint">☐</span>
                    <span>
                      <span className="font-plex font-semibold">{signalLabel(s.signal_type)}:</span>{' '}
                      {s.recommended_action}
                    </span>
                  </li>
                ))}
              {!triggered.length && (
                <li className="text-[13px] text-ink-faint">No verification items — no triggered signals.</li>
              )}
            </ul>
          </section>

          {/* Case panel */}
          <section className="border border-ink/60 bg-paper p-4">
            <h2 className="section-title mb-2">Investigation case</h2>
            {case_ ? (
              <div className="space-y-2.5">
                <p className="num text-[13px] font-semibold">{case_.case_number}</p>
                <p className="font-plex text-[12px] font-semibold text-forest">{case_.status.replaceAll('_', ' ')}</p>
                {caseMsg && <p className="text-[12px] text-ink-soft" role="status">{caseMsg}</p>}
                <div className="flex gap-2">
                  <button className="btn flex-1 justify-center" disabled={caseBusy} onClick={() => void handleAdvance()}>
                    Advance status
                  </button>
                </div>
                <label className="block text-[12px] text-ink-soft">
                  Officer note
                  <textarea
                    className="field mt-1 w-full"
                    rows={3}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Recorded observation, call reference, site visit note…"
                  />
                </label>
                <button className="btn w-full justify-center" disabled={caseBusy || !note.trim()} onClick={() => void handleAddNote()}>
                  Add note
                </button>
                {case_.notes.length > 0 && (
                  <div className="border-t border-rule pt-2">
                    {case_.notes.map((n) => (
                      <p key={n.id} className="border-b border-rule py-1.5 text-[12px] text-ink-soft">
                        <span className="font-semibold">{n.author?.name ?? 'Officer'}:</span> {n.body}
                      </p>
                    ))}
                  </div>
                )}
                <Link to={`/cases/${case_.id}`} className="block pt-1 font-plex text-[12px] font-medium text-accent hover:underline">
                  Open full case file →
                </Link>
              </div>
            ) : (
              <div className="space-y-2.5">
                <p className="text-[12.5px] text-ink-soft">
                  Create an investigation case to document verification, notes and the audit trail for this work.
                </p>
                {caseMsg && <p className="text-[12px] text-vermilion" role="status">{caseMsg}</p>}
                <button className="btn btn-primary w-full justify-center" disabled={caseBusy} onClick={() => void handleCreateCase()}>
                  {caseBusy ? 'Working…' : 'Create investigation case'}
                </button>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

function FragmentRow(props: {
  row: { signal: string; observed: string; reference: string; delta: string }
  severity: string
  source: string
  open: boolean
  onToggle: () => void
  colSpan: number
  children: React.ReactNode
}) {
  const { row, severity, source, open, onToggle, colSpan, children } = props
  const sevClass =
    { CRITICAL: 'text-vermilion font-semibold', HIGH: 'text-vermilion', MEDIUM: 'text-amber-signal', LOW: 'text-ink-faint' }[
      severity
    ] ?? ''
  return (
    <>
      <tr className="cursor-pointer" onClick={onToggle} aria-expanded={open}>
        <td className={`font-plex font-medium ${sevClass}`}>
          {row.signal}
          <span className="ml-1.5 font-mono text-[10px] text-ink-faint">{source}</span>
        </td>
        <td className="num">{row.observed}</td>
        <td className="num text-ink-soft">{row.reference}</td>
        <td className={`num text-right ${sevClass}`}>{row.delta}</td>
        <td className="text-right font-mono text-[11px] text-ink-faint">{open ? '▾' : '▸'}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={colSpan} className="p-0">
            {children}
          </td>
        </tr>
      )}
    </>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-ink-faint">{label}</dt>
      <dd className="num text-right font-medium">{value}</dd>
    </div>
  )
}

function TimelineItem({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-baseline gap-3">
      <span className="w-44 shrink-0 text-ink-faint">{label}</span>
      <span className="num font-medium">{value}</span>
    </li>
  )
}
