import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { CagValidationSummary } from '../types/types'

export interface CagValidationState {
  status: 'loading' | 'ready' | 'error'
  data: CagValidationSummary | null
  error: string | null
}

/** Loads the CAG-grounded validation summary (representative, not CAG data). */
export function useCagValidation(): CagValidationState & { reload: () => void } {
  const [state, setState] = useState<CagValidationState>({
    status: 'loading',
    data: null,
    error: null,
  })

  const load = useCallback(async () => {
    setState((s) => ({ ...s, status: 'loading', error: null }))
    try {
      const res = await api.cagValidationSummary()
      setState({ status: 'ready', data: res.data, error: null })
    } catch (e) {
      setState({
        status: 'error',
        data: null,
        error: e instanceof Error ? e.message : 'Validation report unavailable',
      })
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return { ...state, reload: load }
}
