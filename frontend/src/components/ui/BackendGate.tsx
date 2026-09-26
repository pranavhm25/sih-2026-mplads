import { useEffect, useRef } from 'react'
import { useBackendReady } from '../../hooks/useHealth'
import { BackendDownState, BackendStartingState } from '../ui/Bits'

/**
 * Shown instead of an error screen while the backend wakes from a cold
 * start (docs/DEMO_RUNBOOK.md). Polls /api/v1/health/ready on a fast
 * interval inside a bounded window; the moment it turns ready, `onReady`
 * reloads the page data. If the window is exhausted it shows operator
 * guidance — never a stack trace, never "application crashed".
 */
export function BackendGate({
  onReady,
  pollMs = 1500,
  maxAttempts = 60, // ~90s window before operator guidance
}: {
  onReady: () => void
  pollMs?: number
  maxAttempts?: number
}) {
  const { status, lastError } = useBackendReady({ pollMs, maxAttempts })
  const reloaded = useRef(false)

  useEffect(() => {
    if (status === 'ready' && !reloaded.current) {
      reloaded.current = true
      onReady()
    }
  }, [status, onReady])

  if (status === 'down') {
    return <BackendDownState onRetry={onReady} />
  }
  return <BackendStartingState detail={lastError} />
}
