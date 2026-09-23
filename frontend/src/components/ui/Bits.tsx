// Small shared primitives. A component exists only when it improves
// information hierarchy (AGENTS_RULES §5).
import { PRIORITY_CLASS, signalLabel } from '../../lib/format'

export function PriorityMark({ level, score }: { level: string; score?: number }) {
  const bars = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }[level] ?? 0
  const color =
    { CRITICAL: 'text-vermilion', HIGH: 'text-vermilion', MEDIUM: 'text-amber-signal', LOW: 'text-ink-faint' }[
      level
    ] ?? 'text-ink-faint'
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`sigbar ${color}`} style={{ width: bars * 7 }} aria-hidden />
      <span className={`font-plex text-[11px] font-semibold tracking-wide ${PRIORITY_CLASS[level] ?? ''}`}>
        {level}
        {score !== undefined && <span className="num ml-1 font-normal text-ink-faint">{score.toFixed(1)}</span>}
      </span>
    </span>
  )
}

export function SignalChips({ types }: { types: string[] }) {
  if (!types.length) return <span className="text-ink-faint">—</span>
  return (
    <span className="flex flex-wrap gap-1">
      {types.map((t) => (
        <span
          key={t}
          className="border border-rule bg-paper px-1.5 py-px font-mono text-[10.5px] text-ink-soft"
        >
          {signalLabel(t)}
        </span>
      ))}
    </span>
  )
}

export function MetaLine({ dataset }: { dataset?: { version: string | null; is_synthetic: boolean | null } | null }) {
  if (!dataset) return null
  return (
    <p className="mt-1 flex items-center gap-2 text-meta text-ink-faint">
      <span className="font-mono">dataset {dataset.version ?? '—'}</span>
      {dataset.is_synthetic && <span className="provenance-chip">Synthetic demo data</span>}
      {!dataset.is_synthetic && <span className="font-mono">official import</span>}
    </p>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="space-y-2 p-6" role="status" aria-live="polite">
      <div className="h-3 w-56 animate-pulse bg-rule/70" />
      <div className="h-3 w-96 animate-pulse bg-rule/50" />
      <div className="h-3 w-80 animate-pulse bg-rule/40" />
      <span className="sr-only">{label}</span>
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="border border-dashed border-rule bg-paper/60 p-8 text-center">
      <p className="font-plex text-[13px] font-medium text-ink-soft">{title}</p>
      {hint && <p className="mt-1 text-[12.5px] text-ink-faint">{hint}</p>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="border border-vermilion/40 bg-verms-soft p-4">
      <p className="font-plex text-[13px] font-semibold text-vermilion">Something went wrong</p>
      <p className="mt-1 text-[12.5px] text-ink-soft">{message}</p>
      {onRetry && (
        <button className="btn mt-3" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

