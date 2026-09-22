import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { ErrorState, Loading } from '../components/ui/Bits'
import { formatDateTime } from '../lib/format'

interface DatasetRow {
  id: string
  name: string
  version: string
  is_synthetic: boolean
  row_count: number
  quality_status: string
  ingested_at: string
  source_label: string
}

export default function DataScreen() {
  const [datasets, setDatasets] = useState<DatasetRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .datasets()
      .then((r) => setDatasets(r.data))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load datasets'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading label="Loading datasets…" />
  if (error) return <ErrorState message={error} />

  return (
    <div className="mx-auto max-w-[1100px]">
      <header className="mb-4">
        <h1 className="text-[26px] font-semibold leading-tight">Data &amp; Provenance</h1>
        <p className="mt-0.5 text-meta text-ink-faint">
          Official data, derived analytics and controlled synthetic demo data are always distinguished.
        </p>
      </header>

      {!datasets.length ? (
        <div className="border border-dashed border-rule bg-paper/60 p-8 text-center">
          <p className="font-plex text-[13px] font-medium text-ink-soft">No datasets ingested yet.</p>
          <p className="mt-1 text-[12.5px] text-ink-faint">
            POST a CSV to /api/v1/datasets/import or enable demo seeding.
          </p>
        </div>
      ) : (
        <table className="ledger-table border-t border-ink/60">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Version</th>
              <th>Provenance</th>
              <th className="text-right">Works</th>
              <th>Quality</th>
              <th className="text-right">Ingested</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.id}>
                <td>
                  <p className="font-medium">{d.name}</p>
                  <p className="text-meta text-ink-faint">{d.source_label}</p>
                </td>
                <td className="num">{d.version}</td>
                <td>
                  {d.is_synthetic ? (
                    <span className="provenance-chip">Synthetic demo data</span>
                  ) : (
                    <span className="font-mono text-[11px] text-forest">OFFICIAL IMPORT</span>
                  )}
                </td>
                <td className="num text-right">{d.row_count}</td>
                <td>
                  <span
                    className={`font-plex text-[11.5px] font-semibold ${
                      d.quality_status === 'VALID' ? 'text-forest' : 'text-amber-signal'
                    }`}
                  >
                    {d.quality_status.replaceAll('_', ' ')}
                  </span>
                </td>
                <td className="num text-right text-[12px]">{formatDateTime(d.ingested_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <section className="mt-10">
        <h2 className="section-title mb-2">Provenance policy</h2>
        <div className="border-t border-ink/60 pt-3 text-[13px] leading-relaxed text-ink-soft">
          <p>
            Records in this platform are separated into layers: <strong>source facts</strong> (as reported),
            <strong> derived metrics</strong> (computed), <strong>model output</strong> (signals), and
            <strong> officer conclusions</strong> (cases). Synthetic datasets are labelled at every point
            where their records are displayed, and are never mixed with official imports.
          </p>
          <p className="mt-2">
            Automated signals are investigation indicators only. They never constitute a finding, and
            missing data is reported as unavailable rather than estimated.
          </p>
        </div>
      </section>
    </div>
  )
}
