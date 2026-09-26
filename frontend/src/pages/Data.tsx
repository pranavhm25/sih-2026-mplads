import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../services/api'
import { ErrorState, Loading } from '../components/ui/Bits'
import { formatDateTime } from '../lib/format'
import type {
  Dataset,
  DatasetQualityReport,
  DatasetRecords,
  FixtureInfo,
  ImportSummary,
} from '../types/types'

// Deterministic quality states (Prompt-3 §29) — never an opaque score.
const QUALITY_CLASS: Record<string, string> = {
  GOOD: 'text-forest',
  ACCEPTABLE: 'text-forest',
  DEGRADED: 'text-amber-signal',
  FAILED: 'text-vermilion',
  PENDING: 'text-ink-faint',
}

const DATASET_TYPE_LABELS: Record<string, string> = {
  MP_ALLOCATION: 'MP Allocation',
  SCHEME_AGGREGATE: 'Scheme Aggregate',
  WORK_LEVEL: 'Work Level',
  OTHER_OFFICIAL_EXPORT: 'Other Official Export',
  SYNTHETIC_FIXTURE: 'Synthetic Fixture',
}

const FIELD_LABELS: Record<string, string> = {
  serial_number: 'Sr. No.',
  state: 'State',
  mp_name: 'MP Name',
  constituency: 'Constituency',
  elected_nominated: 'Elected/Nominated',
  allocated_amount: 'Allocated Amount',
  amount_unit: 'Unit',
  house: 'House',
  allocated_limit: 'Allocated Limit',
  amount_consented_for_calamity: 'Calamity Consent',
  works_recommended: 'Works Recommended',
  works_sanctioned: 'Works Sanctioned',
  works_completed: 'Works Completed',
  expenditure_completed_and_ongoing: 'Expenditure (Compl. + Ongoing)',
  monetary_unit: 'Unit',
  as_of_date: 'As of',
  work_id: 'Work ID',
  district: 'District',
  description: 'Description',
  sanctioned_cost: 'Sanctioned Cost',
  expenditure: 'Expenditure',
  status: 'Status',
}

function fieldLabel(f: string): string {
  return FIELD_LABELS[f] ?? f.replaceAll('_', ' ')
}

function formatRecordValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') return value.toLocaleString('en-IN')
  return String(value)
}

export default function DataScreen() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Dataset | null>(null)
  const [quality, setQuality] = useState<DatasetQualityReport | null>(null)
  const [records, setRecords] = useState<DatasetRecords | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // Demo seed state
  const [confirmSeed, setConfirmSeed] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [seedSuccess, setSeedSuccess] = useState<string | null>(null)

  const loadDatasets = useCallback(() => {
    api
      .datasets()
      .then((r) => setDatasets(r.data.items))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load datasets'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadDatasets()
    window.addEventListener('drishti:datasets-changed', loadDatasets)
    return () => window.removeEventListener('drishti:datasets-changed', loadDatasets)
  }, [loadDatasets])

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
      loadDatasets()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to seed demo dataset')
    } finally {
      setSeeding(false)
    }
  }

  const openDataset = (d: Dataset) => {
    setSelected(d)
    setQuality(null)
    setRecords(null)
    setDetailLoading(true)
    Promise.all([api.datasetQuality(d.id), api.datasetRecords(d.id, 100)])
      .then(([q, r]) => {
        setQuality(q.data)
        setRecords(r.data)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load dataset'))
      .finally(() => setDetailLoading(false))
  }

  if (loading && !error) return <Loading label="Loading datasets…" />
  if (error && !datasets.length) return <ErrorState message={error} />

  return (
    <div className="mx-auto max-w-[1150px]">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">Data Ingestion &amp; Provenance</h1>
          <p className="mt-0.5 text-meta text-ink-faint">
            Official MPLADS e-SAKSHI imports, normalization, validation and quality assessment.
            Data issues are quality findings — never conclusions.
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

      <DataIngestionPanel onImported={loadDatasets} />
      <SyntheticFixturePanel />

      <section className="mt-10">
        <h2 className="section-title mb-2">Datasets ({datasets.length})</h2>
        {!datasets.length ? (
          <div className="border border-dashed border-rule bg-paper/60 p-8 text-center">
            <p className="font-plex text-[13px] font-medium text-ink-soft">No datasets ingested yet.</p>
            <p className="mt-1 text-[12.5px] text-ink-faint">
              Import an official CSV/XLSX above, or ingest a synthetic fixture for evaluation.
            </p>
          </div>
        ) : (
          <div className="-mx-4 overflow-x-auto sm:mx-0">
          <table className="ledger-table border-t border-ink/60">
            <thead>
              <tr>
                <th>Dataset</th>
                <th>Type</th>
                <th>Provenance</th>
                <th className="text-right">Rows</th>
                <th>Quality</th>
                <th className="text-right">Ingested</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr
                  key={d.id}
                  className={`cursor-pointer ${selected?.id === d.id ? 'bg-accent-soft' : ''}`}
                  onClick={() => openDataset(d)}
                >
                  <td>
                    <p className="font-medium">{d.name}</p>
                    <p className="text-meta text-ink-faint">
                      {d.file_name ?? d.source_label}
                      {d.file_hash && (
                        <span className="ml-1 font-mono text-[10px]">
                          sha256:{d.file_hash.slice(0, 10)}
                        </span>
                      )}
                    </p>
                  </td>
                  <td className="font-plex text-[11.5px]">
                    {DATASET_TYPE_LABELS[d.dataset_type ?? ''] ?? d.dataset_type ?? '—'}
                  </td>
                  <td>{provenanceChip(d)}</td>
                  <td className="num text-right">{d.row_count}</td>
                  <td>
                    <span className={`font-plex text-[11.5px] font-semibold ${QUALITY_CLASS[d.quality_status] ?? ''}`}>
                      {d.quality_status.replaceAll('_', ' ')}
                    </span>
                  </td>
                  <td className="num text-right text-[12px]">{formatDateTime(d.ingested_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>

      {detailLoading && <Loading label="Loading dataset detail…" />}

      {selected && quality && !detailLoading && (
        <DatasetDetail dataset={selected} quality={quality} records={records} />
      )}

      <section className="mt-10">
        <h2 className="section-title mb-2">Provenance policy</h2>
        <div className="border-t border-ink/60 pt-3 text-[13px] leading-relaxed text-ink-soft">
          <p>
            Every dataset records its <strong>source</strong> (MPLADS e-SAKSHI or synthetic fixture),
            <strong> type</strong> (MP allocation, scheme aggregate, work-level), <strong>file identity</strong>
            (SHA-256) and <strong>quality status</strong>. Official and synthetic data are never mixed:
            synthetic records are labelled at every point where they appear and are never presented as
            government records.
          </p>
          <p className="mt-2">
            Monetary values keep the unit present in the source (₹ raw amounts vs Crore display values)
            and are never compared across units without explicit conversion. Validation issues are
            preserved with row, field, rule, severity and observed value — invalid rows are excluded
            from import but never silently discarded.
          </p>
        </div>
      </section>
    </div>
  )
}

function provenanceChip(d: Dataset) {
  if (d.is_synthetic) return <span className="provenance-chip">Synthetic demo data</span>
  return (
    <span className="font-mono text-[11px] text-forest">
      {d.source_type === 'OFFICIAL_FILE_UPLOAD' ? 'OFFICIAL FILE UPLOAD' : d.source_type}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Import panel (Prompt-3 §33)
// ---------------------------------------------------------------------------

function DataIngestionPanel({ onImported }: { onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [datasetType, setDatasetType] = useState('AUTO_DETECT')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ImportSummary | null>(null)
  const [failure, setFailure] = useState<string | null>(null)

  const submit = async () => {
    if (!file) return
    setBusy(true)
    setFailure(null)
    setResult(null)
    try {
      const r = await api.importFile(file, datasetType)
      setResult(r.data)
      onImported()
    } catch (e) {
      setFailure(e instanceof ApiError ? e.message : 'Import failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="border border-rule bg-paper/70 p-4">
      <h2 className="section-title mb-3">Data Ingestion</h2>
      <div className="grid grid-cols-[110px_1fr] gap-x-4 gap-y-2 text-[13px] max-sm:grid-cols-1">
        <span className="pt-1 text-ink-faint max-sm:pt-0">Source</span>
        <span className="font-medium">MPLADS e-SAKSHI (official file upload)</span>

        <span className="pt-1 text-ink-faint">Dataset type</span>
        <span>
          <select
            className="field w-full max-w-[16rem] sm:w-64"
            value={datasetType}
            onChange={(e) => setDatasetType(e.target.value)}
          >
            <option value="AUTO_DETECT">Auto Detect (from source columns)</option>
            <option value="MP_ALLOCATION">MP Allocation</option>
            <option value="SCHEME_AGGREGATE">Scheme Aggregate</option>
            <option value="WORK_LEVEL">Work Level</option>
            <option value="OTHER_OFFICIAL_EXPORT">Other Official Export</option>
          </select>
        </span>

        <span className="pt-1 text-ink-faint">File</span>
        <span className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="max-w-full text-[12.5px]"
          />
          <button className="btn btn-primary" disabled={!file || busy} onClick={submit}>
            {busy ? 'Importing…' : 'Import Dataset'}
          </button>
        </span>
      </div>

      {failure && (
        <p className="mt-3 border-l-2 border-vermilion bg-verms-soft px-3 py-1.5 text-[12.5px] text-vermilion">
          {failure}
        </p>
      )}
      {result && <ImportResultCard summary={result} />}
    </section>
  )
}

function ImportResultCard({ summary }: { summary: ImportSummary }) {
  const ok = summary.error_rows === 0
  return (
    <div className="mt-4 border border-rule bg-white/60">
      <div className="border-b border-rule px-4 py-2 font-plex text-[13px] font-semibold">
        Dataset Imported
        <span className={`ml-3 font-mono text-[11px] ${QUALITY_CLASS[summary.quality_status] ?? ''}`}>
          QUALITY: {summary.quality_status}
        </span>
      </div>
      <div className="grid grid-cols-2 divide-y divide-rule px-4 py-3 text-[13px] sm:grid-cols-3 sm:divide-y-0 lg:grid-cols-6 lg:divide-x">
        <div className="py-1 sm:py-0">
          <p className="text-meta text-ink-faint">Type</p>
          <p className="font-medium">{DATASET_TYPE_LABELS[summary.dataset_type] ?? summary.dataset_type}</p>
        </div>
        <div className="py-1 sm:py-0">
          <p className="text-meta text-ink-faint">Rows</p>
          <p className="num">{summary.row_count}</p>
        </div>
        <div className="py-1 sm:py-0">
          <p className="text-meta text-ink-faint">Valid</p>
          <p className="num text-forest">{summary.valid_rows}</p>
        </div>
        <div className="py-1 sm:py-0">
          <p className="text-meta text-ink-faint">Warnings</p>
          <p className={`num ${summary.warning_rows ? 'text-amber-signal' : ''}`}>{summary.warning_rows}</p>
        </div>
        <div className="py-1 sm:py-0">
          <p className="text-meta text-ink-faint">Errors</p>
          <p className={`num ${summary.error_rows ? 'text-vermilion' : ''}`}>{summary.error_rows}</p>
        </div>
        <div className="py-1 sm:py-0">
          <p className="text-meta text-ink-faint">Status</p>
          <p className={`font-plex text-[11.5px] font-semibold ${summary.is_synthetic ? 'text-vermilion' : 'text-forest'}`}>
            {summary.is_synthetic ? 'DEMO DATA' : 'OFFICIAL'}
          </p>
        </div>
      </div>
      {summary.quality_reasons.length > 0 && (
        <div className="border-t border-rule px-4 py-2">
          <p className="text-meta text-ink-faint">Quality reasons</p>
          <ul className="mt-0.5 list-disc pl-5 text-[12.5px] text-ink-soft">
            {summary.quality_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="border-t border-rule px-4 py-1.5 text-[11px] text-ink-faint">
        {ok
          ? 'All rows imported.'
          : 'Rows with ERROR issues were excluded from import but preserved in the validation table below their dataset.'}
        {' '}File sha256: <span className="font-mono">{summary.file_hash.slice(0, 16)}…</span>
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Synthetic fixtures (§39)
// ---------------------------------------------------------------------------

function SyntheticFixturePanel() {
  const [fixtures, setFixtures] = useState<FixtureInfo[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const [failure, setFailure] = useState<string | null>(null)

  useEffect(() => {
    api
      .fixtures()
      .then((r) => setFixtures(r.data.fixtures))
      .catch(() => setFixtures([]))
  }, [])

  const ingest = async (name: string) => {
    setBusy(name)
    setFailure(null)
    setDone(null)
    try {
      const r = await api.ingestFixture(name)
      setDone(`${r.data.row_count} rows imported · quality ${r.data.quality_status}`)
      window.dispatchEvent(new CustomEvent('drishti:datasets-changed'))
    } catch (e) {
      setFailure(e instanceof ApiError ? e.message : 'Fixture ingestion failed.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className="mt-4 border border-dashed border-rule bg-paper/50 p-4">
      <h2 className="section-title mb-1">Synthetic fixtures — evaluation only</h2>
      <p className="mb-3 text-[12px] text-ink-faint">
        Deterministic fixtures exercising the ingestion architecture. Always labelled
        DEMO DATA — never official MPLADS records.
      </p>
      <div className="flex flex-wrap gap-2">
        {fixtures.map((f) => (
          <button
            key={f.name}
            className="btn"
            disabled={busy !== null}
            onClick={() => ingest(f.name)}
            title={`${f.label} (${f.dataset_type})`}
          >
            {busy === f.name ? 'Importing…' : `Ingest: ${f.label}`}
          </button>
        ))}
      </div>
      {done && <p className="mt-2 text-[12.5px] text-forest">✓ {done}</p>}
      {failure && <p className="mt-2 text-[12.5px] text-vermilion">{failure}</p>}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Dataset detail: quality + validation issues + typed records (§31, §34, §45)
// ---------------------------------------------------------------------------

function DatasetDetail({
  dataset,
  quality,
  records,
}: {
  dataset: Dataset
  quality: DatasetQualityReport
  records: DatasetRecords | null
}) {
  return (
    <section className="mt-8">
      <div className="flex flex-wrap items-baseline justify-between border-b border-ink/60 pb-2">
        <h2 className="font-plex text-[15px] font-semibold">{dataset.name}</h2>
        <div className="flex items-center gap-4 text-[12px] text-ink-soft">
          {provenanceChip(dataset)}
          <span className="font-mono text-[11px]">{dataset.version}</span>
          <span className={`font-plex font-semibold ${QUALITY_CLASS[quality.quality_status] ?? ''}`}>
            {quality.quality_status}
          </span>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-px bg-rule text-[13px] sm:grid-cols-3 lg:grid-cols-5">
        {(
          [
            ['Total rows', quality.total_rows],
            ['Valid', quality.valid_rows],
            ['Warnings', quality.warning_rows],
            ['Errors', quality.error_rows],
            ['Issues on file', quality.issue_count],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="bg-paper px-3 py-2">
            <p className="text-meta text-ink-faint">{label}</p>
            <p className="num text-[15px] font-semibold">{value}</p>
          </div>
        ))}
      </div>

      {quality.reasons.length > 0 && (
        <div className="mt-3 border-l-2 border-amber-signal bg-amber-soft px-3 py-2">
          <p className="text-meta text-ink-faint">Why this status</p>
          <ul className="mt-0.5 list-disc pl-5 text-[12.5px] text-ink-soft">
            {quality.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {quality.issues.length > 0 && (
        <div className="mt-5">
          <h3 className="section-title mb-2">Validation issues</h3>
          <div className="-mx-4 overflow-x-auto sm:mx-0">
          <table className="ledger-table border-t border-ink/60">
            <thead>
              <tr>
                <th className="text-right">Row</th>
                <th>Field</th>
                <th>Severity</th>
                <th>Issue</th>
                <th>Observed</th>
              </tr>
            </thead>
            <tbody>
              {quality.issues.map((i, idx) => (
                <tr key={idx}>
                  <td className="num text-right">{i.row_number ?? '—'}</td>
                  <td className="font-mono text-[11.5px]">{i.field ?? '—'}</td>
                  <td>
                    <span
                      className={`font-plex text-[11px] font-semibold ${
                        i.severity === 'ERROR'
                          ? 'text-vermilion'
                          : i.severity === 'WARNING'
                            ? 'text-amber-signal'
                            : 'text-ink-faint'
                      }`}
                    >
                      {i.severity}
                    </span>
                  </td>
                  <td>{i.message}</td>
                  <td className="num text-[11.5px]">{i.observed_value ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {records && records.records.length > 0 && (
        <div className="mt-6">
          <h3 className="section-title mb-2">
            Records — {DATASET_TYPE_LABELS[records.dataset_type] ?? records.dataset_type}
            <span className="ml-2 font-normal normal-case tracking-normal text-ink-faint">
              (showing {records.records.length} of {records.total}; only fields available in this
              source are displayed)
            </span>
          </h3>
          <div className="-mx-4 overflow-x-auto sm:mx-0">
          <table className="ledger-table border-t border-ink/60">
            <thead>
              <tr>
                {records.fields.map((f) => (
                  <th key={f}>{fieldLabel(f)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.records.map((r, idx) => (
                <tr key={idx}>
                  {records.fields.map((f) => (
                    <td key={f} className={typeof r[f] === 'number' ? 'num' : ''}>
                      {formatRecordValue(r[f])}
                      {f === 'allocated_amount' || f === 'allocated_limit'
                        ? ` ${String(r.amount_unit ?? r.monetary_unit ?? '')}`
                        : ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </section>
  )
}
