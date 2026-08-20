import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"
import { useDashboardTheme } from "@/components/theme/theme-context"
import { LogoMark } from "@/components/shared/LogoMark"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import { ShieldCheck, Sun, Moon, Monitor } from "lucide-react"

export default function LoginPage() {
  const [password, setPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const { mode, setMode, options } = useDashboardTheme()

  const cycleTheme = () => {
    const idx = options.findIndex((o) => o.mode === mode)
    setMode(options[(idx + 1) % options.length].mode)
  }
  const ThemeIcon = mode === "tungsten-dark" ? Moon : mode === "porcelain-moss" ? Sun : Monitor

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!password.trim() || submitting) return
    setSubmitting(true)
    const error = await login(password)
    setSubmitting(false)
    if (error) {
      toast.error(error)
      return
    }
    toast.success("登录成功")
    navigate("/admin/dashboard", { replace: true })
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-background p-4">
      <button
        onClick={cycleTheme}
        className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-md text-muted-foreground hover:bg-accent"
        title="切换主题"
      >
        <ThemeIcon className="h-5 w-5" />
      </button>

      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <div className="flex size-16 items-center justify-center rounded-2xl bg-primary/10">
            <LogoMark className="h-12 w-12" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">GeminiWeb2API</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              登录管理台查看状态、配置与日志
            </p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-border bg-card p-6 shadow-sm"
        >
          <label className="mb-2 flex items-center gap-1.5 text-sm font-medium">
            <ShieldCheck className="size-4 text-primary" />
            管理员密码
          </label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="请输入管理员密码"
            autoFocus
            autoComplete="current-password"
          />
          <Button type="submit" size="lg" className="mt-4 w-full" disabled={submitting}>
            {submitting ? "登录中…" : "登录"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          首次登录默认密码为 sk-admin，可在配置页修改
        </p>
      </div>
    </div>
  )
}
