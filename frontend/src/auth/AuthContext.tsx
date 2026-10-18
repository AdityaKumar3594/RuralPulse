import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { configureAuth } from '../api/client'
import * as api from '../api/endpoints'
import type { TokenResponse, User } from '../api/types'

// sessionStorage, not localStorage: the token disappears when the tab closes, which matters on
// phones shared within a family. Logging out also clears it.
const TOKEN_KEY = 'Ruralpulse.token'
const USER_KEY = 'Ruralpulse.user'
const UNAUTHORIZED_EVENT = 'Ruralpulse:unauthorized'

// Registered at import time so even the first request of a restored session carries the token.
configureAuth(
  () => sessionStorage.getItem(TOKEN_KEY),
  () => window.dispatchEvent(new Event(UNAUTHORIZED_EVENT)),
)

interface AuthValue {
  user: User | null
  login: (phone: string, pin: string) => Promise<void>
  register: (data: { display_name: string; phone: string; pin: string; date_of_birth: string }) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

function readUser(): User | null {
  try {
    const raw = sessionStorage.getItem(USER_KEY)
    return raw && sessionStorage.getItem(TOKEN_KEY) ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation()
  const [user, setUser] = useState<User | null>(readUser)

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(USER_KEY)
    setUser(null)
  }, [])

  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, logout)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, logout)
  }, [logout])

  const accept = useCallback((res: TokenResponse) => {
    sessionStorage.setItem(TOKEN_KEY, res.access_token)
    sessionStorage.setItem(USER_KEY, JSON.stringify(res.user))
    setUser(res.user)
  }, [])

  const value = useMemo<AuthValue>(
    () => ({
      user,
      logout,
      login: async (phone, pin) => {
        const res = await api.login({ phone, pin })
        accept(res)
        void i18n.changeLanguage(res.user.preferred_language)
      },
      register: async (data) =>
        accept(await api.register({ ...data, preferred_language: i18n.language })),
    }),
    [user, logout, accept, i18n],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
