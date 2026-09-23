import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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

interface QualityIssue {
  work_id: string
  project_id: string
  rule: string
  severity: string
  field: string | null
  detail: string
}

interface QualityData {
  dataset_id: string
  quality_status: string
  total_rows: number
  issues: QualityIssue[]
}

export default function DataScreen() {
  const [datasets, setDatasets] = useState<DatasetRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Demo seed state
  const [confirmSeed, setConfirmSeed] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [seedSuccess, setSeedSuccess] = useState<string | null>(null)

  // Quality report state
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null)
  const [qualityData, setQualityData] = useState<QualityData | null>(null)
  const [loadingQuality, setLoadingQuality] = useState(false)

  const loadDatasets = () => {
    return api
      .datasets()
      .then((r) => {
        setDatasets(r.data)
        if (r.data.length > 0 && !selectedDatasetId) {
          setSelectedDatasetId(r.data[0].id)
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load datasets'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    void loadDatasets()
  }, [])

  useEffect(() => {
    if (!selectedDatasetId) return
    setLoadingQuality(true)
    api
      .datasetQuality(selectedDatasetId)
      .then((r) => setQualityData(r.data))
      .catch(() => setQualityData(null))
      .finally(() => setLoadingQuality(false))
  }, [selectedDatasetId])

  const handleSeed = async () => {
    setSeeding(true)
    setError(null)
    setSeedSuccess(null)
    setConfirmSeed(false)
    try {
      const res = await api.demoSeed()
      setSeedSuccess(
        `Demo dataset loaded (${res.data.row_count} works). Detection run ${res.data.run_status.toLowerCase()}.`
      )
      await loadDatasets()
      setSelectedDatasetId(res.data.dataset)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to seed demo dataset')
    } finally {
      setSeeding(false)
    }
  }

  if (loading) return <Loading label="Loading datasets…" />
  if (error && !datasets.length) return <ErrorState message={error} onRetry={() => void loadDatasets()} />

  return (
    <div className="mx-auto max-w-[1100px]">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[26px] font-semibold leading-tight">Data &amp; Provenance</h1>
          <p className="mt-0.5 text-meta text-ink-faint">
            Official data, derived analytics and controlled synthetic demo data are always distinguished.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {!confirmSeed ? (
            <button
              onClick={() => setConfirmSeed(true)}
              disabled={seeding}
              className="btn btn-primary"
            >
              {seeding ? 'Seeding demo data…' : 'Load demo dataset'}
            </button>
          ) : (
            <div className="flex items-center gap-2 border border-rule bg-paper p-2">
              <span className="text-[12px] text-ink-soft">Reset to clean demo data?</span>
              <button
                onClick={() => void handleSeed()}
                disabled={seeding}
                className="btn btn-primary text-[11.5px]"
              >
                Confirm
              </button>
              <button
                onClick={() => setConfirmSeed(false)}
                disabled={seeding}
                className="btn text-[11.5px]"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </header>

      {seedSuccess && (
        <div className="mb-4 border border-forest/40 bg-accent-soft p-3 text-[13px] text-forest flex items-center justify-between">
          <span>{seedSuccess}</span>
          <button onClick={() => setSeedSuccess(null)} className="font-mono text-xs text-forest hover:underline">
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="mb-4">
          <ErrorState message={error} onRetry={() => void loadDatasets()} />
        </div>
      )}

      {!datasets.length ? (
        <div className="border border-dashed border-rule bg-paper/60 p-8 text-center">
          <p className="font-plex text-[13px] font-medium text-ink-soft">No datasets ingested yet.</p>
          <p className="mt-1 text-[12.5px] text-ink-faint">
            Click &ldquo;Load demo dataset&rdquo; above or POST a CSV to /api/v1/datasets/import.
          </p>
        </div>
      ) : (
        <>
          <table className="ledger-table border-t border-ink/60">
            <thead>
              <tr>
                <th>Dataset</th>
                <th>Version</th>
                <th>Provenance</th>
                <th className="text-right">Works</th>
                <th>Quality</th>
                <th className="text-right">Ingested</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr
                  key={d.id}
                  className={`cursor-pointer ${selectedDatasetId === d.id ? 'bg-accent-soft/80' : ''}`}
                  onClick={() => setSelectedDatasetId(d.id)}
                >
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
                  <td className="text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedDatasetId(d.id)
                      }}
                      className="font-plex text-[11.5px] text-accent hover:underline"
                    >
                      {selectedDatasetId === d.id ? 'Viewing' : 'Inspect'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Quality Report Section (A5) */}
          <section className="mt-8 border border-rule bg-paper p-5">
            <div className="mb-3 flex items-baseline justify-between">
              <div>
                <h2 className="section-title">Data Quality Report</h2>
                <p className="mt-0.5 text-meta text-ink-faint">
                  Integrity rules evaluated across source records during dataset validation.
                </p>
              </div>
              {qualityData && (
                <span className="num text-meta text-ink-soft">
                  {qualityData.issues.length} issue{qualityData.issues.length === 1 ? '' : 's'} flagged
                </span>
              )}
            </div>

            {loadingQuality ? (
              <p className="py-4 text-[13px] text-ink-faint">Loading quality report…</p>
            ) : !qualityData ? (
              <p className="py-4 text-[13px] text-ink-faint">Select a dataset to view its quality report.</p>
            ) : !qualityData.issues.length ? (
              <div className="border border-forest/30 bg-accent-soft/40 p-4">
                <p className="font-plex text-[12.5px] font-semibold text-forest">
                  ✓ Valid: No quality exceptions detected
                </p>
                <p className="mt-0.5 text-[12px] text-ink-soft">
                  All {qualityData.total_rows} records satisfy date chronological ordering, progress bounds, and cost rules.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="ledger-table">
                  <thead>
                    <tr>
                      <th>Work ID</th>
                      <th>Rule</th>
                      <th>Severity</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {qualityData.issues.map((issue, idx) => (
                      <tr key={`${issue.work_id}-${idx}`}>
                        <td className="num font-semibold">
                          <Link
                            to={`/projects/${issue.project_id}`}
                            className="text-accent hover:underline"
                          >
                            {issue.work_id}
                          </Link>
                        </td>
                        <td className="font-medium text-[12.5px]">{issue.rule}</td>
                        <td>
                          <span
                            className={`font-plex text-[11px] font-semibold ${
                              issue.severity === 'CRITICAL' ? 'text-vermilion' : 'text-amber-signal'
                            }`}
                          >
                            {issue.severity}
                          </span>
                        </td>
                        <td className="text-[12.5px] text-ink-soft">{issue.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
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
