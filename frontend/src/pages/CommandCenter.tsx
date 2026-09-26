import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, describeLoadFailure } from '../services/api'
import type { DashboardData } from '../types/types'
import { ErrorState, Loading, MetaLine, PriorityMark, SignalChips } from '../components/ui/Bits'
import { BackendGate } from '../components/ui/BackendGate'
import { formatINR, signalLabel } from '../lib/format'
import CommandCenterMap from '../components/CommandCenterMap'
import { isBackendUnavailableFailure } from '../services/api'

export default function CommandCenter() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [meta, setMeta] = useState<{ version: string | null; is_synthetic: boolean | null } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setUnavailable(false)
    try {
      const res = await api.dashboard()
      setData(res.data)
      setMeta({ version: res.meta.dataset_version, is_synthetic: res.meta.is_synthetic })
    } catch (e) {
      setError(describeLoadFailure(e, 'Failed to load dashboard'))
      setUnavailable(isBackendUnavailableFailure(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <Loading label="Loading command center…" />
  if (error && unavailable) return <BackendGate onReady={() => void load()} />
  if (error) return <ErrorState message={error} onRetry={() => void load()} />
  if (!data) return <ErrorState message="No data available." onRetry={() => void load()} />

  const signalRows = Object.entries(data.signal_distribution).sort((a, b) => b[1] - a[1])

  return (
    <div className="mx-auto max-w-[1400px]">
      <header className="mb-4">
        <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">Command Center</h1>
        <MetaLine dataset={meta} />
      </header>

      <div className="mb-6">
        <SummaryStripFrom data={data} />
      </div>

      <div className="mb-8">
        <CommandCenterMap points={data.map_points ?? []} />
      </div>

      <div className="grid grid-cols-12 gap-6 lg:gap-8">
        {/* Left: geography */}
        <section className="col-span-12 xl:col-span-4">
          <h2 className="section-title mb-2">District attention</h2>
          <div className="rule-line pt-2">
            <table className="ledger-table">
              <thead>
                <tr>
                  <th>District</th>
                  <th className="text-right">Works</th>
                  <th className="text-right">Value</th>
                  <th className="text-right">High+Crit</th>
                </tr>
              </thead>
              <tbody>
                {data.districts.map((d) => (
                  <tr key={d.district}>
                    <td>
                      <p className="font-medium">{d.district}</p>
                      <p className="text-meta text-ink-faint">{d.state}</p>
                    </td>
                    <td className="num text-right">{d.works}</td>
                    <td className="num text-right">{formatINR(d.value)}</td>
                    <td className={`num text-right ${d.high > 0 ? 'text-vermilion font-semibold' : ''}`}>
                      {d.high}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="section-title mb-2 mt-8">Signal distribution</h2>
          <div className="rule-line pt-2">
            <dl className="space-y-1.5">
              {signalRows.map(([sig, count]) => (
                <div key={sig} className="flex items-center justify-between text-[13px]">
                  <dt className="text-ink-soft">{signalLabel(sig)}</dt>
                  <dd className="num font-semibold">{count}</dd>
                </div>
              ))}
              {!signalRows.length && <p className="text-[13px] text-ink-faint">No signals recorded.</p>}
            </dl>
          </div>
        </section>

        {/* Center: risk distribution */}
        <section className="col-span-12 xl:col-span-4">
          <h2 className="section-title mb-2">Investigation priority distribution</h2>
          <div className="rule-line pt-3">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={Object.entries(data.risk_distribution).map(([k, v]) => ({ level: k, works: v }))}
                layout="vertical"
                margin={{ left: 8, right: 24, top: 0, bottom: 0 }}
              >
                <CartesianGrid horizontal={false} stroke="#d8d3c8" strokeDasharray="2 3" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: '#7d8694' }} />
                <YAxis
                  type="category"
                  dataKey="level"
                  width={70}
                  tick={{ fontSize: 11, fill: '#1e222a', fontFamily: 'IBM Plex Mono' }}
                />
                <Tooltip cursor={{ fill: '#eef1f8' }} />
                <Bar dataKey="works" fill="#2d4a8a" barSize={16} />
              </BarChart>
            </ResponsiveContainer>
            <p className="mt-2 text-meta text-ink-faint">
              Priority reflects the weight of independent evidence per work. It is not a finding.
            </p>
          </div>

          <h2 className="section-title mb-2 mt-8">Data-quality exceptions</h2>
          <div className="rule-line flex items-baseline gap-3 pt-3">
            <span className="num text-[30px] font-semibold leading-none text-amber-signal">
              {data.quality_exception_count}
            </span>
            <p className="text-[12.5px] text-ink-soft">
              fields require correction or verification in source records
            </p>
          </div>
        </section>

        {/* Right: queue preview */}
        <section className="col-span-12 xl:col-span-4">
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="section-title">Investigate first</h2>
            <Link to="/queue" className="font-plex text-[12px] font-medium text-accent hover:underline">
              Full queue →
            </Link>
          </div>
          <div className="rule-line pt-1">
            {data.queue_preview.map((p) => (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="block border-b border-rule py-2.5 hover:bg-accent-soft/50"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="num text-[12px] text-ink-faint">{p.work_id}</span>
                  {p.priority && <PriorityMark level={p.priority.level} score={p.priority.score} />}
                </div>
                <p className="mt-0.5 truncate text-[13px] font-medium">{p.description}</p>
                <div className="mt-1">
                  <SignalChips types={p.primary_signals} />
                </div>
              </Link>
            ))}
            {!data.queue_preview.length && (
              <p className="py-6 text-center text-[13px] text-ink-faint">
                No works currently match. Adjust detection or filters.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function SummaryStripFrom({ data }: { data: DashboardData }) {
  return (      <div className="grid grid-cols-2 items-baseline gap-y-4 border-y border-ink/60 py-4 sm:grid-cols-3 lg:flex lg:flex-wrap lg:gap-x-10">
      {[
        { label: 'Works', value: String(data.total_works) },
        { label: 'Value', value: formatINR(data.total_value) },
        { label: 'High priority', value: String(data.high_priority_count), tone: 'critical' as const },
        { label: 'Critical', value: String(data.critical_count), tone: 'critical' as const },
        { label: 'Delayed', value: String(data.delayed_count) },
        { label: 'Duplicate candidates', value: String(data.duplicate_candidate_count) },
        { label: 'Open cases', value: String(data.case_open_count) },
      ].map((it) => (
        <div key={it.label} className="flex items-baseline gap-2">
          <span className="section-title block">{it.label}</span>
          <span
            className={`num text-[24px] font-semibold leading-none ${
              it.tone === 'critical' ? 'text-vermilion' : 'text-ink'
            }`}
          >
            {it.value}
          </span>
        </div>
      ))}
    </div>
  )
}
