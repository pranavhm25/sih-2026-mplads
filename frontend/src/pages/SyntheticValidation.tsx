import { useSyntheticValidation } from '../hooks/useSyntheticValidation'
import { formatDateTime } from '../lib/format'
import type { SyntheticScenarioSummary } from '../types/types'

/**
 * Synthetic Model Validation — controlled injection benchmark panel.
 *
 * Wording discipline: this is a "controlled synthetic benchmark". It must
 * never be presented as "fraud accuracy" or as real-world performance.
 */

const SCENARIO_LABELS: Record<string, string> = {
  A_clean_baseline: 'A — Clean baseline',
  B_small_injection: 'B — Small injection',
  C_moderate_injection: 'C — Moderate injection',
  D_mixed_types: 'D — Mixed types',
}

const ANOMALY_LABELS: Record<string, string> = {
  cost_inflation: 'Cost inflation',
  duplicate_similar_work: 'Duplicate/similar work',
  abnormal_duration: 'Abnormal duration',
  unusual_spending_pattern: 'Unusual spending pattern',
  suspicious_attribute_combination: 'Suspicious attribute combination',
}

function pct(v: number | null): string {
  return v === null ? 'n/a' : v.toFixed(4)
}

function MetricsRow({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-rule py-1.5 last:border-b-0">
      <span className="text-[12.5px] text-ink-soft">{label}</span>
      <span className="num text-[13px] font-semibold">{pct(value)}</span>
    </div>
  )
}

function ScenarioCard({ name, s }: { name: string; s: SyntheticScenarioSummary }) {
  return (
    <div className="border border-ink/60 bg-paper">
      <div className="border-b border-rule px-3 py-2">
        <p className="font-plex text-[12.5px] font-semibold">
          {SCENARIO_LABELS[name] ?? name}
        </p>
        <p className="num mt-0.5 text-meta text-ink-faint">
          {s.totals.records_evaluated} records · {s.totals.injected} injected ·
          run {s.detection_run_status}
        </p>
      </div>
      <div className="px-3 py-2">
        <MetricsRow label="Precision" value={s.metrics.precision} />
        <MetricsRow label="Recall" value={s.metrics.recall} />
        <MetricsRow label="F1" value={s.metrics.f1} />
        <MetricsRow label="False-positive rate" value={s.metrics.false_positive_rate} />
        <MetricsRow label="Detection rate" value={s.metrics.detection_rate} />
      </div>
      <div className="num border-t border-rule px-3 py-2 text-[11.5px] text-ink-faint">
        TP {s.totals.tp} · FP {s.totals.fp} · TN {s.totals.tn} · FN {s.totals.fn}
      </div>
    </div>
  )
}

export default function SyntheticValidation() {
  const { status, data, error, reload } = useSyntheticValidation()
  const scenarioEntries = data ? Object.entries(data.scenarios) : []
  const anomalyTypes = data
    ? Object.keys(
        data.scenarios['D_mixed_types']?.per_anomaly_type ?? {}
      ).sort()
    : []

  return (
    <div className="mx-auto max-w-[980px]">
      <header className="mb-4">
        <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">
          Synthetic Model Validation
        </h1>
        <p className="mt-0.5 text-meta text-ink-faint">
          Controlled synthetic benchmark — deterministic anomaly injection
          against the unmodified detection pipeline.
        </p>
      </header>

      <div className="mb-4 border border-amber-700/40 bg-amber-50 px-4 py-3">
        <p className="font-plex text-[12.5px] font-semibold text-amber-900">
          Controlled synthetic benchmark.
        </p>
        <p className="mt-1 text-[12px] leading-relaxed text-amber-900/90">
          Results do not represent production-world fraud detection accuracy.
          All metrics are computed against synthetic ground truth for
          anomalies injected by the benchmark itself.
        </p>
      </div>

      {status === 'loading' && (
        <div className="border border-rule bg-paper px-4 py-6 text-[13px] text-ink-faint">
          Running benchmark…
        </div>
      )}

      {status === 'error' && (
        <div className="border border-vermilion/50 bg-verms-soft px-4 py-6">
          <p className="text-[13px] font-medium text-vermilion">{error}</p>
          <button className="btn mt-3" onClick={reload}>
            Retry
          </button>
        </div>
      )}

      {status === 'ready' && data && (
        <>
          <section className="mb-5 grid gap-4 lg:grid-cols-[1fr_280px]">
            <div className="border border-ink/60 bg-paper">
              <div className="border-b border-rule px-4 py-3">
                <h2 className="font-plex text-[13px] font-semibold">
                  Overall (all scenarios pooled)
                </h2>
              </div>
              <dl className="grid grid-cols-2 gap-px bg-rule sm:grid-cols-4">
                {[
                  { label: 'Injected anomalies', value: data.overall.total_injected },
                  { label: 'Precision', value: pct(data.overall.metrics.precision) },
                  { label: 'Recall', value: pct(data.overall.metrics.recall) },
                  { label: 'F1', value: pct(data.overall.metrics.f1) },
                ].map((s) => (
                  <div key={s.label} className="bg-paper px-4 py-3">
                    <dt className="text-meta text-ink-faint">{s.label}</dt>
                    <dd className="num mt-0.5 text-[20px] font-semibold">{s.value}</dd>
                  </div>
                ))}
              </dl>
              <div className="border-t border-rule px-4 py-3 text-meta text-ink-faint">
                False-positive rate{' '}
                <span className="num">{pct(data.overall.metrics.false_positive_rate)}</span>{' '}
                · detection rate{' '}
                <span className="num">{pct(data.overall.metrics.detection_rate)}</span> ·
                FP <span className="num">{data.overall.cm.fp}</span> of{' '}
                <span className="num">
                  {data.overall.cm.fp + data.overall.cm.tn}
                </span>{' '}
                normal records
              </div>
            </div>

            <div className="border border-ink/60 bg-paper">
              <div className="border-b border-rule px-4 py-3">
                <h2 className="font-plex text-[13px] font-semibold">
                  Confusion matrix
                </h2>
              </div>
              <table className="num w-full text-[12.5px]">
                <thead>
                  <tr className="border-b border-rule text-left text-ink-faint">
                    <th className="px-3 py-1.5 font-medium"></th>
                    <th className="px-3 py-1.5 font-medium">Flagged</th>
                    <th className="px-3 py-1.5 font-medium">Missed</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-rule">
                    <td className="px-3 py-1.5">Injected</td>
                    <td className="px-3 py-1.5 font-semibold text-forest">
                      {data.overall.cm.tp}
                    </td>
                    <td className="px-3 py-1.5">{data.overall.cm.fn}</td>
                  </tr>
                  <tr>
                    <td className="px-3 py-1.5">Normal</td>
                    <td className="px-3 py-1.5 text-vermilion">{data.overall.cm.fp}</td>
                    <td className="px-3 py-1.5">{data.overall.cm.tn}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="mb-5">
            <h2 className="mb-2 font-plex text-[13px] font-semibold">Scenarios</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {scenarioEntries.map(([name, s]) => (
                <ScenarioCard key={name} name={name} s={s} />
              ))}
            </div>
          </section>

          <section className="mb-5">
            <h2 className="mb-2 font-plex text-[13px] font-semibold">
              Per anomaly type (scenario D)
            </h2>
            <div className="overflow-x-auto border border-ink/60 bg-paper">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-ink/60 text-left">
                    <th className="px-3 py-2 font-medium">Anomaly type</th>
                    <th className="px-3 py-2 text-right font-medium">Injected</th>
                    <th className="px-3 py-2 text-right font-medium">Detected</th>
                    <th className="px-3 py-2 text-right font-medium">Missed</th>
                    <th className="px-3 py-2 text-right font-medium">Precision</th>
                    <th className="px-3 py-2 text-right font-medium">Recall</th>
                    <th className="px-3 py-2 text-right font-medium">F1</th>
                    <th className="px-3 py-2 text-right font-medium">Detector</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalyTypes.map((at) => {
                    const v = data.scenarios['D_mixed_types'].per_anomaly_type[at]
                    return (
                      <tr key={at} className="border-b border-rule last:border-b-0">
                        <td className="px-3 py-2">{ANOMALY_LABELS[at] ?? at}</td>
                        <td className="num px-3 py-2 text-right">{v.injected}</td>
                        <td className="num px-3 py-2 text-right">{v.detected}</td>
                        <td className="num px-3 py-2 text-right">{v.missed}</td>
                        <td className="num px-3 py-2 text-right">{pct(v.metrics.precision)}</td>
                        <td className="num px-3 py-2 text-right">{pct(v.metrics.recall)}</td>
                        <td className="num px-3 py-2 text-right">{pct(v.metrics.f1)}</td>
                        <td className="num px-3 py-2 text-right text-ink-faint">
                          {v.expected_detector_hits}/{v.injected}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="border border-ink/60 bg-paper px-4 py-3">
            <h2 className="font-plex text-[13px] font-semibold">Run configuration</h2>
            <dl className="mt-2 space-y-1.5 text-[12.5px] text-ink-soft">
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-ink-faint">Seed (deterministic)</dt>
                <dd className="num">{data.experiment_configuration.seed}</dd>
              </div>
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-ink-faint">Threshold tuning</dt>
                <dd>{data.experiment_configuration.threshold_tuning}</dd>
              </div>
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-ink-faint">Detector versions</dt>
                <dd className="num text-right">
                  {data.experiment_configuration.detector_versions.join(', ')}
                </dd>
              </div>
              {data.generated_at && (
                <div className="flex items-baseline justify-between gap-4">
                  <dt className="text-ink-faint">Generated</dt>
                  <dd className="num">{formatDateTime(data.generated_at)}</dd>
                </div>
              )}
            </dl>
            <p className="mt-3 border-t border-rule pt-2 text-[12px] leading-relaxed text-ink-faint">
              The benchmark is deterministic: the same seed reproduces the same
              dataset, injections and metrics. Reproduce with{' '}
              <span className="num">py scripts/run_synthetic_validation.py</span>{' '}
              inside <span className="num">backend/</span>. Full methodology and
              limitations: <span className="num">docs/SYNTHETIC_VALIDATION.md</span>.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
