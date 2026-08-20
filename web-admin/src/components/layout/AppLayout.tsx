import { useState } from "react"
import { NavLink, Outlet, Navigate, useNavigate } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"
import { useDashboardTheme } from "@/components/theme/theme-context"
import { PageLoading } from "@/components/shared/PageLoading"
import { LogoMark } from "@/components/shared/LogoMark"
import {
  LayoutDashboard,
  MessagesSquare,
  Globe,
  FlaskConical,
  Settings,
  ScrollText,
  LogOut,
  Sun,
  Moon,
  Monitor,
  Menu,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { to: "/admin/dashboard", label: "概览", icon: LayoutDashboard },
  { to: "/admin/chat", label: "对话", icon: MessagesSquare },
  { to: "/admin/network", label: "网络检测", icon: Globe },
  { to: "/admin/test", label: "服务测试", icon: FlaskConical },
  { to: "/admin/settings", label: "配置", icon: Settings },
  { to: "/admin/logs", label: "运行日志", icon: ScrollText },
]

const themeIcons = {
  "porcelain-moss": Sun,
  "tungsten-dark": Moon,
  system: Monitor,
}

export default function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const { isAuthenticated, isLoading, logout } = useAuth()
  const navigate = useNavigate()
  const { mode, setMode, options } = useDashboardTheme()

  const handleLogout = async () => {
    await logout()
    navigate("/admin/login", { replace: true })
  }

  const cycleTheme = () => {
    const idx = options.findIndex((o) => o.mode === mode)
    const next = options[(idx + 1) % options.length]
    setMode(next.mode)
  }

  const ThemeIcon = themeIcons[mode] || Monitor

  if (isLoading) {
    return <PageLoading />
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />
  }

  const SidebarContent = (
    <>
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
        <LogoMark className="h-8 w-8" />
        <span className="text-sm font-semibold text-sidebar-foreground">
          GeminiWeb2API
        </span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-3">
        <div className="flex flex-col gap-0.5">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="mt-1.5 flex items-center gap-2">
          <button
            onClick={cycleTheme}
            className="flex h-8 w-8 items-center justify-center rounded-md text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
            title="切换主题"
          >
            <ThemeIcon className="h-4 w-4" />
          </button>
          <button
            onClick={handleLogout}
            className="flex flex-1 items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
          >
            <LogOut className="h-4 w-4" />
            退出登录
          </button>
        </div>
      </div>
    </>
  )

  return (
    <div className="admin-shell flex h-screen overflow-hidden bg-background">
      {/* Sidebar (desktop) */}
      <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-sidebar lg:flex">
        {SidebarContent}
      </aside>

      {/* Mobile header */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-border px-3 sm:px-4 lg:hidden">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setMobileNavOpen((open) => !open)}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent"
              aria-label={mobileNavOpen ? "关闭导航菜单" : "打开导航菜单"}
              aria-expanded={mobileNavOpen}
            >
              {mobileNavOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <LogoMark className="h-7 w-7 shrink-0" />
            <span className="truncate text-sm font-semibold">GeminiWeb2API</span>
          </div>
          <button
            onClick={cycleTheme}
            className="flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground hover:bg-accent"
            aria-label="切换主题"
          >
            <ThemeIcon className="h-4 w-4" />
          </button>
        </header>

        {mobileNavOpen && (
          <div className="border-b border-border bg-sidebar lg:hidden">
            <nav className="flex flex-col gap-0.5 px-3 py-2">
              {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50",
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </NavLink>
              ))}
              <button
                onClick={() => {
                  setMobileNavOpen(false)
                  void handleLogout()
                }}
                className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-sidebar-foreground/70"
              >
                <LogOut className="h-4 w-4" />
                退出登录
              </button>
            </nav>
          </div>
        )}

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
