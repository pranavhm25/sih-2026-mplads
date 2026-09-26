import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { SyntheticValidationReport } from '../types/types'

export interface SyntheticValidationState {
  status: 'loading' | 'ready' | 'error'
  data: SyntheticValidationReport | null
  error: string | null
}

/**
 * Loads the Synthetic Model Validation benchmark (controlled injection
 * benchmark — not real-world fraud detection accuracy).
 */
export function useSyntheticValidation(): SyntheticValidationState & {
  reload: () => void
} {
  const [state, setState] = useState<SyntheticValidationState>({
    status: 'loading',
    data: null,
    error: null,
  })

  const load = useCallback(async () => {
    setState((s) => ({ ...s, status: 'loading', error: null }))
    try {
      const res = await api.syntheticValidation()
      setState({ status: 'ready', data: res.data, error: null })
    } catch (e) {
      setState({
        status: 'error',
        data: null,
        error: e instanceof Error ? e.message : 'Benchmark unavailable',
      })
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return { ...state, reload: load }
}
