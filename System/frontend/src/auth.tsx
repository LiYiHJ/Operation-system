import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { authApi } from './services/api'

type User = { id: number; username: string; displayName: string; role: string; permissions: string[]; status: string; createdAt?: string }

type AuthContextType = {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }
    authApi.me().then((res) => {
      if (res?.authenticated) setUser(res.user)
      else localStorage.removeItem('token')
    }).finally(() => setLoading(false))
  }, [])

  const value = useMemo(() => ({
    user,
    loading,
    login: async (username: string, password: string) => {
      const res = await authApi.login(username, password)
      localStorage.setItem('token', res.token)
      setUser(res.user)
    },
    logout: async () => {
      await authApi.logout()
      localStorage.removeItem('token')
      setUser(null)
    },
  }), [user, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
