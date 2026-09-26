import { useHealth } from '../hooks/useHealth'
import { formatDateTime } from '../lib/format'

/**
 * Development screen (foundation task §10): verifies the
 * frontend → backend → database chain is reachable.
 * This is intentionally NOT the Command Center.
 */
export default function SystemStatus() {
  const { status, service, error, checkedAt, recheck } = useHealth()

  const badge =
    status === 'up'
      ? { cls: 'border-forest/50 bg-forestsoft text-forest', label: '● Backend connected' }
      : status === 'checking'
        ? { cls: 'border-rule bg-paper text-ink-faint', label: '○ Checking…' }
        : { cls: 'border-vermilion/50 bg-verms-soft text-vermilion', label: '✕ Backend unreachable' }

  return (
    <div className="mx-auto max-w-[720px]">
      <header className="mb-4">
        <h1 className="text-[22px] font-semibold leading-tight sm:text-[26px]">System status</h1>
        <p className="mt-0.5 text-meta text-ink-faint">
          Development check: frontend → backend API connectivity.
        </p>
      </header>

      <div className="border border-ink/60 bg-paper">
        <div className={`border-b border-rule px-4 py-3 ${badge.cls.split(' ')[1]}`}>
          <p className={`font-plex text-[13px] font-semibold ${badge.cls.split(' ')[2]}`}>{badge.label}</p>
        </div>
        <dl className="space-y-2 px-4 py-3 text-[13px]">
          <div className="flex items-baseline justify-between gap-4">
            <dt className="text-ink-faint">Service</dt>
            <dd className="num font-medium">{service ?? '—'}</dd>
          </div>
          <div className="flex items-baseline justify-between gap-4">
            <dt className="text-ink-faint">Endpoint</dt>
            <dd className="num font-medium">GET /api/v1/health</dd>
          </div>
          <div className="flex items-baseline justify-between gap-4">
            <dt className="text-ink-faint">Checked at</dt>
            <dd className="num font-medium">{checkedAt ? formatDateTime(checkedAt) : '—'}</dd>
          </div>
          {error && (
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-vermilion">Error</dt>
              <dd className="max-w-[380px] text-right text-[12px] text-vermilion">{error}</dd>
            </div>
          )}
        </dl>
        <div className="border-t border-rule px-4 py-3">
          <button className="btn" onClick={recheck} disabled={status === 'checking'}>
            Re-check connection
          </button>
        </div>
      </div>

      <p className="mt-3 text-meta text-ink-faint">
        If the backend is down, start it with:{' '}
        <span className="num">py -m uvicorn app.main:app --port 8000</span> inside{' '}
        <span className="num">backend/</span>.
      </p>
    </div>
  )
}
