import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, getStoredToken, storeToken } from '../services/api'
import type { AuthOfficer } from '../types/types'

interface AuthState {
  officer: AuthOfficer | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState>({
  officer: null,
  login: async () => undefined,
  logout: async () => undefined,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [officer, setOfficer] = useState<AuthOfficer | null>(null)

  // Restore session from a stored token on first mount.
  useEffect(() => {
    const token = getStoredToken()
    if (!token) return
    api
      .authMe()
      .then((env) => setOfficer(env.data))
      .catch(() => storeToken(null))
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      officer,
      login: async (email, password) => {
        const env = await api.login(email, password)
        storeToken(env.data.token)
        setOfficer(env.data.officer)
      },
      logout: async () => {
        try {
          await api.logout()
        } finally {
          storeToken(null)
          setOfficer(null)
        }
      },
    }),
    [officer],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
