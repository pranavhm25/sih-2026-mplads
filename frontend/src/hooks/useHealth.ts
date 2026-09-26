import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

export interface HealthState {
  status: 'checking' | 'up' | 'down'
  service: string | null
  error: string | null
  checkedAt: string | null
}

const INITIAL: HealthState = { status: 'checking', service: null, error: null, checkedAt: null }

/** Polls the backend health endpoint; states are checking / up / down. */
export function useHealth(): HealthState & { recheck: () => void } {
  const [state, setState] = useState<HealthState>(INITIAL)

  const check = useCallback(async () => {
    setState((s) => ({ ...s, status: 'checking', error: null }))
    try {
      const res = await api.health()
      setState({
        status: res.status === 'ok' ? 'up' : 'down',
        service: res.service ?? null,
        error: null,
        checkedAt: new Date().toISOString(),
      })
    } catch (e) {
      setState({
        status: 'down',
        service: null,
        error: e instanceof Error ? e.message : 'Backend unreachable',
        checkedAt: new Date().toISOString(),
      })
    }
  }, [])

  useEffect(() => {
    void check()
  }, [check])

  return { ...state, recheck: () => void check() }
}

// ---------------------------------------------------------------------------
// Cold-start readiness (docs/DEMO_RUNBOOK.md).
//
// On Render's free tier the backend sleeps between demos; the first minute
// of a session can be a cold start. useBackendReady polls /health/ready on
// a FAST interval while the service wakes (process up, dataset loading) and
// gives up after a bounded window — never infinite polling.
// ---------------------------------------------------------------------------

export type BackendReadyStatus = 'checking' | 'starting' | 'ready' | 'down'

export interface BackendReadyState {
  status: BackendReadyStatus
  /** Per-check payload from /health/ready, e.g. {database: 'ok', demo_dataset: 'ok'} */
  checks: Record<string, string>
  /** Poll attempts made since the last (re)start of the loop. */
  attempt: number
  lastError: string | null
  recheck: () => void
}

interface BackendReadyOptions {
  /** Poll interval while not ready (ms). Default 1500. */
  pollMs?: number
  /** Max polls before declaring the backend down. Default 60 (~90 s at 1.5 s). */
  maxAttempts?: number
}

/**
 * Bounded readiness poller for the waking-backend UX.
 *
 * - `checking`  → first probe in flight
 * - `starting`  → reachable but not ready yet (DB/demo dataset warming up)
 *                 OR unreachable but within the retry window (sleeping host)
 * - `ready`     → backend can serve the demo
 * - `down`      → retry window exhausted; show operator guidance
 */
export function useBackendReady(options: BackendReadyOptions = {}): BackendReadyState {
  const { pollMs = 1500, maxAttempts = 60 } = options
  const [status, setStatus] = useState<BackendReadyStatus>('checking')
  const [checks, setChecks] = useState<Record<string, string>>({})
  const [attempt, setAttempt] = useState(0)
  const [lastError, setLastError] = useState<string | null>(null)
  const [tick, setTick] = useState(0) // retry-loop trigger
  const cancelled = useRef(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const recheck = useCallback(() => {
    setAttempt(0)
    setStatus('checking')
    setLastError(null)
    setTick((t) => t + 1)
  }, [])

  useEffect(() => {
    cancelled.current = false

    const probe = async (n: number) => {
      if (cancelled.current) return
      try {
        const body = await api.healthReady()
        if (cancelled.current) return
        setChecks(body.checks ?? {})
        setLastError(null)
        if (body.ready) {
          setStatus('ready')
          return
        }
        setStatus('starting')
        schedule(n + 1)
      } catch (e) {
        if (cancelled.current) return
        setChecks({})
        setLastError(e instanceof Error ? e.message : 'Backend unreachable')
        setStatus('starting') // still inside the retry window
        schedule(n + 1)
      }
    }

    const schedule = (nextAttempt: number) => {
      if (cancelled.current) return
      if (nextAttempt >= maxAttempts) {
        setStatus('down')
        return
      }
      setAttempt(nextAttempt)
      timer.current = setTimeout(() => void probe(nextAttempt), pollMs)
    }

    void probe(0)

    return () => {
      cancelled.current = true
      if (timer.current) clearTimeout(timer.current)
    }
  }, [pollMs, maxAttempts, tick])

  return { status, checks, attempt, lastError, recheck }
}
