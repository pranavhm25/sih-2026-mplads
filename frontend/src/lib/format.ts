// Display formatting shared across screens.

export function formatINR(value: number): string {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`
  return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export function formatPct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return '—'
  return `${value > 0 ? '+' : ''}${value.toFixed(digits)}%`
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const SIGNAL_LABELS: Record<string, string> = {
  COST_ANOMALY: 'Cost',
  FIN_PHYS_GAP: 'F/P gap',
  DELAY: 'Delay',
  DUPLICATE: 'Duplicate candidate',
  ML_ANOMALY: 'ML unusual',
  DATA_QUALITY: 'Data quality',
  AGENCY_CONCENTRATION: 'Agency concentration',
}

export function signalLabel(t: string): string {
  return SIGNAL_LABELS[t] ?? t
}

export const PRIORITY_ORDER: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
}

// Priority color: used with a text/shape counterpart so status is never
// communicated by color alone (DESIGN.md §18).
export const PRIORITY_CLASS: Record<string, string> = {
  CRITICAL: 'text-vermilion font-semibold',
  HIGH: 'text-vermilion',
  MEDIUM: 'text-amber-signal',
  LOW: 'text-ink-faint',
}
