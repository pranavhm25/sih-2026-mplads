import { useCallback, useEffect, useState } from 'react'
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
        status: res.data.status === 'ok' ? 'up' : 'down',
        service: res.data.service ?? null,
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
