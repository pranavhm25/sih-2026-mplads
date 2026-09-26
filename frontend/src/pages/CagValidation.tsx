import { useCagValidation } from '../hooks/useCagValidation'
import { formatDateTime } from '../lib/format'
import type { CagValidationResult } from '../types/types'

/**
 * Evidence & Validation — CAG-grounded pattern validation.
 *
 * Shows whether Drishti's existing detectors can identify the irregularity
 * PATTERNS documented in real CAG audits of MPLADS, using a controlled
 * synthetic reproduction. This is capability validation — it never claims
 * that Drishti detected a real CAG case.
 */

const RESULT_STYLE: Record<CagValidationResult, { label: string; cls: string }> = {
  FLAGGED: { label: 'Flagged', cls: 'border-forest/50 bg-forestsoft text-forest' },
  PARTIAL: { label: 'Partial', cls: 'border-amber-600/40 bg-amber-50 text-amber-800' },
  MISSED: { label: 'Missed', cls: 'border-vermilion/50 bg-verms-soft text-vermilion' },
  NOT_VALIDATABLE: {
    label: 'Not validatable',
    cls: 'border-rule bg-paper text-ink-faint',
  },
}

export default function CagValidation() {
  const { status, data, error, reload } = useCagValidation()

  return (
    <div className="mx-auto max-w-[980px]">
      <header className="mb-4">
        <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">
          Evidence &amp; Validation
        </h1>
        <p className="mt-0.5 text-meta text-ink-faint">
          CAG-grounded pattern validation — can Drishti&apos;s detectors identify the
          irregularity patterns documented in CAG audits of MPLADS?
        </p>
      </header>

      <div className="mb-4 border border-amber-700/40 bg-amber-50 px-4 py-3">
        <p className="font-plex text-[12.5px] font-semibold text-amber-900">
          Representative validation — not original CAG case data.
        </p>
        <p className="mt-1 text-[12px] leading-relaxed text-amber-900/90">
          {data?.provenance ??
            'Fixtures reproduce the structural characteristics of documented CAG irregularity patterns for detector validation. They are not the original CAG dataset.'}
        </p>
      </div>

      {status === 'loading' && (
        <div className="border border-rule bg-paper px-4 py-6 text-[13px] text-ink-faint">
          Running validation…
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
          <section className="mb-5 border border-ink/60 bg-paper">
            <div className="border-b border-rule px-4 py-3">
              <h2 className="font-plex text-[13px] font-semibold">Run summary</h2>
            </div>
            <dl className="grid grid-cols-2 gap-px bg-rule sm:grid-cols-4">
              {[
                { label: 'Patterns assessed', value: data.summary.patterns_total },
                { label: 'Flagged', value: data.summary.FLAGGED },
                {
                  label: 'Not validatable',
                  value: data.summary.NOT_VALIDATABLE,
                },
                { label: 'Signals emitted', value: data.summary.signals_emitted },
              ].map((s) => (
                <div key={s.label} className="bg-paper px-4 py-3">
                  <dt className="text-meta text-ink-faint">{s.label}</dt>
                  <dd className="num mt-0.5 text-[20px] font-semibold">{s.value}</dd>
                </div>
              ))}
            </dl>
            <div className="border-t border-rule px-4 py-3 text-meta text-ink-faint">
              Detection run {data.summary.detection_run_status} · ruleset{' '}
              <span className="num">{data.summary.detection_ruleset_version}</span> · model{' '}
              <span className="num">{data.summary.detection_model_version}</span> ·{' '}
              {data.summary.rows_imported} synthetic works · quality{' '}
              <span className="num">{data.summary.dataset_quality_status}</span>
              {data.generated_at && <> · generated {formatDateTime(data.generated_at)}</>}
            </div>
          </section>

          <section className="mb-5">
            <h2 className="mb-2 font-plex text-[13px] font-semibold">
              Pattern results
            </h2>
            <div className="overflow-x-auto border border-ink/60 bg-paper">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-ink/60 text-left">
                    <th className="px-3 py-2 font-medium">Pattern</th>
                    <th className="px-3 py-2 font-medium">Validation</th>
                    <th className="px-3 py-2 font-medium">Fixture works</th>
                    <th className="px-3 py-2 font-medium">Queue</th>
                  </tr>
                </thead>
                <tbody>
                  {data.patterns.map((p) => {
                    const style = RESULT_STYLE[p.result]
                    const queueItems = p.work_ids
                      .map((wid) => data.queue_entry[wid])
                      .filter(Boolean)
                    const enters = queueItems.some((q) => q.enters_queue)
                    return (
                      <tr key={p.pattern_id} className="border-b border-rule last:border-b-0">
                        <td className="px-3 py-2">
                          <p className="font-medium">
                            <span className="num text-ink-faint">{p.pattern_id}</span>{' '}
                            {p.title}
                          </p>
                          {p.reason && (
                            <p className="mt-0.5 text-meta text-ink-faint">{p.reason}</p>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`inline-block border px-1.5 py-0.5 text-[11px] font-semibold ${style.cls}`}
                          >
                            {style.label}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          {p.work_ids.length ? (
                            <span className="num text-meta">
                              {p.work_ids.join(', ')}
                            </span>
                          ) : (
                            <span className="text-meta text-ink-faint">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-meta">
                          {p.work_ids.length ? (
                            enters ? (
                              <span className="text-forest">Enters queue</span>
                            ) : (
                              <span className="text-ink-faint">Below threshold</span>
                            )
                          ) : (
                            <span className="text-ink-faint">n/a</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="border border-ink/60 bg-paper px-4 py-3">
            <h2 className="font-plex text-[13px] font-semibold">Reading this report</h2>
            <ul className="mt-2 space-y-1.5 text-[12.5px] leading-relaxed text-ink-soft">
              <li>
                <strong>Flagged</strong> — the mapped detector emitted its expected
                signal for the synthetic reproduction of the documented pattern.
              </li>
              <li>
                <strong>Not validatable</strong> — the pattern requires data Drishti
                does not have (recommendation trails, authority fund ledgers,
                records-keeping registers). Reported honestly; not treated as a
                failure of the detector.
              </li>
              <li>
                No accuracy metrics against real CAG data are claimed: the underlying
                work-level records are not publicly available. Thresholds were not
                modified to force positive results.
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
