import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react"
import { api, ApiClientError } from "@/lib/api-client"

interface AuthContextValue {
  isAuthenticated: boolean
  isLoading: boolean
  login: (password: string) => Promise<string | null>
  logout: () => Promise<void>
  checkSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const checkSession = useCallback(async () => {
    try {
      const session = await api.session()
      setIsAuthenticated(session.authenticated)
    } catch {
      setIsAuthenticated(false)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    checkSession()
  }, [checkSession])

  const login = useCallback(async (password: string): Promise<string | null> => {
    try {
      await api.login(password)
      await checkSession()
      return null
    } catch (err: unknown) {
      if (err instanceof ApiClientError && err.status === 401) {
        return "管理员密码错误"
      }
      if (err instanceof Error) return err.message
      return "登录失败"
    }
  }, [checkSession])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // 忽略登出失败，仍视为未认证
    } finally {
      setIsAuthenticated(false)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, logout, checkSession }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
