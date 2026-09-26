import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { signalLabel } from '../lib/format'
import type {
  AlertDigestData,
  AuditVerifyReport,
  StakeholderSummary,
  TrendsData,
  ValidationSummary,
} from '../types/types'

const ROLE_LABELS: Record<string, string> = {
  MP: "Hon'ble MP",
  DISTRICT_AUTHORITY: 'District Authority',
  STATE_NODAL: 'State Nodal Authority',
  MINISTRY: 'Ministry (MoSPI)',
  ADMIN: 'Platform Admin',
  UNAUTHENTICATED: 'Not signed in',
}

const DEMO_ACCOUNTS = [
  { email: 'ministry@drishti.demo', label: 'Ministry' },
  { email: 'snl@drishti.demo', label: 'State Nodal' },
  { email: 'district@drishti.demo', label: 'District' },
  { email: 'mp@drishti.demo', label: 'MP' },
]

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border border-ink/60 bg-paper">
      <h2 className="border-b border-rule bg-paper-deep px-4 py-2 font-plex text-[12px] font-semibold uppercase tracking-wide text-ink-soft">
        {title}
      </h2>
      <div className="px-4 py-3">{children}</div>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border border-rule px-3 py-2">
      <p className="text-meta text-ink-faint">{label}</p>
      <p className="num mt-0.5 text-[18px] font-semibold leading-none">{value}</p>
    </div>
  )
}

export default function Stakeholders() {
  const { officer, login, logout } = useAuth()
  const [email, setEmail] = useState('ministry@drishti.demo')
  const [password, setPassword] = useState('drishti-demo')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [summary, setSummary] = useState<StakeholderSummary | null>(null)
  const [validation, setValidation] = useState<ValidationSummary | null>(null)
  const [digest, setDigest] = useState<AlertDigestData | null>(null)
  const [audit, setAudit] = useState<AuditVerifyReport | null>(null)
  const [trends, setTrends] = useState<TrendsData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadAll = useCallback(async () => {
    try {
      setError(null)
      const [s, v, t, a] = await Promise.all([
        api.stakeholderSummary(),
        api.validationSummary(),
        api.trends(),
        api.auditVerify(),
      ])
      setSummary(s.data)
      setValidation(v.data)
      setTrends(t.data)
      setAudit(a.data)
      if (getStoredToken()) {
        try {
          const d = await api.alertDigest()
          setDigest(d.data)
        } catch {
          setDigest(null) // 401 — not signed in
        }
      } else {
        setDigest(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll, officer])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setLoginError(null)
    try {
      await login(email, password)
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleAck() {
    await api.ackDigest()
    const d = await api.alertDigest()
    setDigest(d.data)
  }

  return (
    <div className="mx-auto max-w-[980px] space-y-5">
      <header>
        <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">Stakeholder views</h1>
        <p className="mt-0.5 text-meta text-ink-faint">
          Role-scoped decision support for the four stakeholders named in the problem
          statement — plus the platform's integrity instruments.
        </p>
      </header>

      {/* Sign-in */}
      <Section title="Sign in">
        {officer ? (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[14px] font-semibold">
                {officer.name}{' '}
                <span className="font-normal text-ink-faint">
                  — {ROLE_LABELS[officer.stakeholder_role ?? ''] ?? officer.stakeholder_role}
                </span>
              </p>
              <p className="text-meta text-ink-faint">
                {officer.constituency ? `Constituency: ${officer.constituency} · ` : ''}
                {officer.state ? `State: ${officer.state}` : ''}
                {!officer.constituency && !officer.state ? officer.email : ''}
              </p>
            </div>
            <button
              type="button"
              onClick={() => logout()}
              className="border border-ink/50 bg-paper px-3 py-1.5 font-plex text-[12px] hover:bg-accent-soft"
            >
              Sign out
            </button>
          </div>
        ) : (
          <form onSubmit={handleLogin} className="grid grid-cols-2 items-end gap-3 sm:flex sm:flex-wrap">
            <label className="col-span-2 text-[12px]">
              <span className="block text-ink-faint">Demo account</span>
              <select
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full border border-ink/40 bg-white px-2 py-1.5 font-plex text-[13px]"
              >
                {DEMO_ACCOUNTS.map((a) => (
                  <option key={a.email} value={a.email}>
                    {a.label} — {a.email}
                  </option>
                ))}
              </select>
            </label>
            <label className="col-span-1 text-[12px]">
              <span className="block text-ink-faint">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full border border-ink/40 bg-white px-2 py-1.5 font-plex text-[13px] sm:w-44"
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="border border-ink bg-ink px-4 py-1.5 font-plex text-[12px] font-semibold text-paper hover:bg-ink-soft disabled:opacity-50"
            >
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
            {loginError && <p className="text-[12px] text-vermilion">{loginError}</p>}
            <p className="w-full text-meta text-ink-faint">
              Demo accounts use the shared password <code>drishti-demo</code>. Production
              deployments disable them (<code>DEMO_ACCOUNTS_ENABLED=false</code>).
            </p>
          </form>
        )}
      </Section>

      {error && (
        <p className="border border-vermilion/40 bg-verms-soft px-4 py-2 text-[13px] text-vermilion">
          {error}
        </p>
      )}

      {/* Role-scoped summary */}
      {summary && (
        <Section title={`View — ${ROLE_LABELS[summary.scope.role] ?? summary.scope.role}`}>
          <p className="mb-3 text-[12px] text-ink-soft">
            <span className="font-semibold">{summary.scope.label}</span> — {summary.scope.note}
          </p>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <Stat label="Works in scope" value={summary.works.total} />
            <Stat label="Triggered signals" value={summary.signals.total} />
            <Stat label="Cases total" value={summary.cases.total} />
            <Stat label="Cases open" value={summary.cases.open} />
          </div>

          {summary.mp_headlines && (
            <div className="mt-3">
              <p className="mb-1 font-plex text-[12px] font-semibold uppercase tracking-wide text-ink-soft">
                Works needing attention in your constituency
              </p>
              {summary.mp_headlines.length === 0 ? (
                <p className="text-[13px] text-ink-faint">
                  No high-severity indicators for your works.
                </p>
              ) : (
                <ul className="divide-y divide-rule border border-rule">
                  {summary.mp_headlines.map((h, i) => (
                    <li key={i} className="px-3 py-2 text-[13px]">
                      <span className="num font-semibold">{h.work}</span> — {h.headline}
                      <span className="ml-2 text-meta text-ink-faint">({h.note})</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {summary.district_attention && summary.district_attention.length > 0 && (
            <div className="mt-3">
              <p className="mb-1 font-plex text-[12px] font-semibold uppercase tracking-wide text-ink-soft">
                Districts with most high-severity signals
              </p>
              <table className="w-full border border-rule text-[13px]">
                <thead>
                  <tr className="bg-paper-deep text-left text-meta text-ink-faint">
                    <th className="px-3 py-1.5 font-medium">District</th>
                    <th className="px-3 py-1.5 font-medium">High-severity signals</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.district_attention.map((d) => (
                    <tr key={d.district} className="border-t border-rule">
                      <td className="px-3 py-1.5">{d.district}</td>
                      <td className="num px-3 py-1.5 font-semibold">{d.high_signals}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      )}

      {/* Early-warning digest */}
      {officer && digest && (
        <Section title="Early-warning digest (since last review)">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-[13px]">
              {digest.counts.new_signals} new high/critical signal(s) ·{' '}
              {digest.counts.cases_moved} case movement(s) · floor ≥ {digest.floor_severity}
            </p>
            <button
              type="button"
              onClick={handleAck}
              className="border border-ink/50 bg-paper px-3 py-1.5 font-plex text-[12px] hover:bg-accent-soft"
            >
              Mark reviewed
            </button>
          </div>
          {digest.new_signals.length > 0 && (
            <ul className="mt-2 divide-y divide-rule border border-rule">
              {digest.new_signals.slice(0, 8).map((s, i) => (
                <li key={i} className="px-3 py-1.5 text-[13px]">
                  <span className="num font-semibold">{s.work}</span>{' '}
                  <span className="text-ink-faint">({s.district})</span> — {s.title}
                  <span className="ml-1 text-meta text-ink-faint">
                    [{signalLabel(s.signal_type)} · {s.severity}]
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}

      {/* Validation / precision story */}
      {validation && (
        <Section title="Detection performance & review capacity">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <Stat
              label="Reviewer precision"
              value={validation.feedback.precision === null ? '—' : `${(validation.feedback.precision * 100).toFixed(0)}%`}
            />
            <Stat label="Confirmed concerns" value={validation.feedback.confirmed_concern} />
            <Stat label="False positives" value={validation.feedback.false_positive} />
            <Stat
              label="Flag rate"
              value={
                validation.flag_rate.rate === null
                  ? '—'
                  : `${(validation.flag_rate.rate * 100).toFixed(1)}%`
              }
            />
          </div>
          <p className="mt-2 text-meta text-ink-faint">{validation.feedback.note}</p>
          <p className="mt-1 text-meta text-ink-faint">{validation.flag_rate.note}</p>
          <p className="mt-2 border-l-2 border-accent pl-3 text-[12px] text-ink-soft">
            <span className="font-semibold">Quantified target:</span> {validation.quantified_target}
          </p>
        </Section>
      )}

      {/* Trends */}
      {trends && (
        <Section title="Scheme trends (imported aggregates only)">
          {trends.series.length === 0 ? (
            <p className="text-[13px] text-ink-faint">
              No aggregate dataset imported yet. Import a SCHEME_AGGREGATE dataset on the
              Data screen to populate trends.
            </p>
          ) : (
            <table className="w-full border border-rule text-[13px]">
              <thead>
                <tr className="bg-paper-deep text-left text-meta text-ink-faint">
                  <th className="px-3 py-1.5 font-medium">House</th>
                  <th className="px-3 py-1.5 font-medium">Recommended</th>
                  <th className="px-3 py-1.5 font-medium">Sanctioned</th>
                  <th className="px-3 py-1.5 font-medium">Completed</th>
                  <th className="px-3 py-1.5 font-medium">Completion rate</th>
                  <th className="px-3 py-1.5 font-medium">Source</th>
                </tr>
              </thead>
              <tbody>
                {trends.series.map((row, i) => {
                  const rate =
                    row.works_sanctioned && row.works_completed
                      ? `${((row.works_completed / row.works_sanctioned) * 100).toFixed(1)}%`
                      : '—'
                  return (
                    <tr key={i} className="border-t border-rule">
                      <td className="px-3 py-1.5">{row.house ?? '—'}</td>
                      <td className="num px-3 py-1.5">{row.works_recommended?.toLocaleString('en-IN') ?? '—'}</td>
                      <td className="num px-3 py-1.5">{row.works_sanctioned?.toLocaleString('en-IN') ?? '—'}</td>
                      <td className="num px-3 py-1.5">{row.works_completed?.toLocaleString('en-IN') ?? '—'}</td>
                      <td className="num px-3 py-1.5">{rate}</td>
                      <td className="px-3 py-1.5">
                        {row.is_synthetic ? (
                          <span className="text-amber-signal">Synthetic fixture</span>
                        ) : (
                          'Official import'
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          <p className="mt-2 text-meta text-ink-faint">{trends.limitation}</p>
        </Section>
      )}

      {/* Audit chain */}
      {audit && (
        <Section title="Tamper-evident audit chain">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[14px]">
                {audit.valid ? (
                  <span className="font-semibold text-forest">● Chain valid</span>
                ) : (
                  <span className="font-semibold text-vermilion">
                    ✕ Chain broken at event #{audit.broken_at_seq} ({audit.reason})
                  </span>
                )}
              </p>
              <p className="mt-1 text-meta text-ink-faint">
                {audit.events_checked} event(s) verified · each event hash-links to its
                predecessor (SHA-256); any retroactive edit breaks the chain.
              </p>
              {audit.chain_tip && (
                <p className="mt-1 break-all text-meta text-ink-faint">
                  Chain tip: <code>{audit.chain_tip.slice(0, 32)}…</code>
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={loadAll}
              className="border border-ink/50 bg-paper px-3 py-1.5 font-plex text-[12px] hover:bg-accent-soft"
            >
              Re-verify
            </button>
          </div>
        </Section>
      )}
    </div>
  )
}

function getStoredToken(): string | null {
  return localStorage.getItem('drishti.token')
}
