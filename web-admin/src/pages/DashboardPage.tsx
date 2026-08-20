import { useEffect, useMemo, useState, type ReactNode } from "react"
import { useNavigate } from "react-router-dom"
import { api } from "@/lib/api-client"
import type { StatsData, StatsRange, StatusData, Urls, UsageAgg } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Copy,
  ExternalLink,
  FlaskConical,
  Globe,
  KeyRound,
  MessagesSquare,
  RefreshCw,
  Server,
  ScrollText,
  ShieldCheck,
  Terminal,
  XCircle,
} from "lucide-react"

const STATS_RANGE_OPTIONS: ReadonlyArray<{ value: StatsRange; label: string }> = [
  { value: "1d", label: "当天" },
  { value: "3d", label: "近 3 天" },
  { value: "7d", label: "近 7 天" },
  { value: "30d", label: "近 30 天" },
  { value: "all", label: "全部" },
]

function StatCard({
  icon,
  title,
  value,
  detail,
  loading,
}: {
  icon: ReactNode
  title: string
  value: ReactNode
  detail?: ReactNode
  loading: boolean
}) {
  return (
    <Card className="border-border/60 shadow-sm">
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-medium text-muted-foreground">{title}</p>
            {loading ? (
              <Skeleton className="mt-2 h-7 w-24" />
            ) : (
              <div className="mt-1 truncate text-2xl font-bold tracking-tight">{value}</div>
            )}
          </div>
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
        </div>
        {loading ? (
          <Skeleton className="mt-3 h-4 w-32" />
        ) : detail ? (
          <div className="mt-2 text-xs text-muted-foreground">{detail}</div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function formatTokens(value: number): string {
  return new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 }).format(value)
}

function UsageBars({
  entries,
  loading,
  emptyLabel,
}: {
  entries: ReadonlyArray<[string, UsageAgg]>
  loading: boolean
  emptyLabel: string
}) {
  const maxTokens = Math.max(...entries.map(([, data]) => data.total_tokens), 1)
  if (loading) return <Skeleton className="h-64 w-full" />
  if (entries.length === 0)
    return <p className="py-20 text-center text-xs text-muted-foreground">{emptyLabel}</p>
  return (
    <div className="space-y-3">
      {entries.slice(0, 8).map(([label, data], index) => {
        const width = Math.max(6, Math.round((data.total_tokens / maxTokens) * 100))
        return (
          <div
            key={label}
            className="group rounded-xl border border-border/50 bg-muted/10 p-3 transition-colors hover:bg-muted/30"
            title={`${label}：${data.total_tokens.toLocaleString()} total tokens`}
            tabIndex={0}
          >
            <div className="mb-2 flex items-center justify-between gap-3 text-xs">
              <div className="flex min-w-0 items-center gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[10px] font-semibold text-primary">
                  {index + 1}
                </span>
                <span className="min-w-0 truncate font-mono" title={label}>
                  {label}
                </span>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-muted-foreground">
                <span className="font-semibold text-foreground">{formatTokens(data.total_tokens)}</span>
                <span>{data.count} 次</span>
              </div>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary via-info to-warning transition-all duration-700 ease-out"
                style={{ width: `${width}%` }}
              />
            </div>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
              <span>输入 {data.prompt_tokens.toLocaleString()}</span>
              <span>输出 {data.completion_tokens.toLocaleString()}</span>
              <span>总计 {data.total_tokens.toLocaleString()}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

const URL_LABELS: Record<string, string> = {
  current: "当前地址",
  local: "本地地址",
  lan: "局域网",
  public: "公网地址",
  admin: "管理台",
}
const URL_ORDER = ["current", "local", "lan", "public", "admin"]

export default function DashboardPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<StatusData | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [range, setRange] = useState<StatsRange>("7d")
  const [stats, setStats] = useState<StatsData | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const loadStatus = async () => {
    try {
      const data = await api.status()
      setStatus(data)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "状态读取失败")
    } finally {
      setStatusLoading(false)
    }
  }

  useEffect(() => {
    void loadStatus()
    const timer = setInterval(() => void loadStatus(), 30000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    setStatsLoading(true)
    api
      .stats(range)
      .then(setStats)
      .catch(() => toast.error("统计读取失败"))
      .finally(() => setStatsLoading(false))
  }, [range])

  const config = status?.config
  const urls = status?.urls ?? {}
  const sortedUrls = URL_ORDER.filter((k) => k in urls && urls[k as keyof Urls]).map((k) => ({
    key: k,
    label: URL_LABELS[k] || k,
    value: urls[k as keyof Urls] as string,
  }))

  const cookieState = config?.cookie_file ? "已配置" : "匿名模式"
  const proxyState = config?.proxy ? config.proxy : "系统环境"
  const modelCount = status?.models.length ?? 0

  const envItems = useMemo(
    () => [
      { icon: ShieldCheck, label: "Cookie", value: cookieState, tone: config?.cookie_file ? "text-success" : "" },
      { icon: Globe, label: "代理", value: proxyState, tone: config?.proxy ? "text-info" : "" },
      { icon: KeyRound, label: "API 密钥", value: (config?.api_keys?.length ?? 0) ? "已启用" : "未启用", tone: config?.api_keys?.length ? "text-success" : "text-warning" },
      { icon: Terminal, label: "流式模式", value: config?.force_non_stream ? "强制非流式" : "正常流式", tone: config?.force_non_stream ? "text-warning" : "text-success" },
      { icon: Server, label: "鉴权模式", value: (config?.api_keys?.length ?? 0) ? "密钥鉴权" : "无鉴权", tone: config?.api_keys?.length ? "text-info" : "text-warning" },
    ],
    [config?.cookie_file, config?.proxy, config?.api_keys, config?.force_non_stream],
  )

  const copyText = async (text: string, label = "已复制") => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(label)
    } catch {
      toast.warning("复制失败，请手动复制")
    }
  }

  const statsTotal = stats?.total ?? 0
  const success = stats?.success ?? 0
  const error = stats?.error ?? 0
  const successPercent = statsTotal > 0 ? Math.round((success / statsTotal) * 100) : 0
  const errorPercent = statsTotal > 0 ? Math.round((error / statsTotal) * 100) : 0
  const quietPercent = Math.max(100 - successPercent - errorPercent, 0)
  const rangeLabel = STATS_RANGE_OPTIONS.find((o) => o.value === range)?.label ?? "全部"

  const modelEntries = useMemo(
    () => Object.entries(stats?.by_model ?? {}).sort((a, b) => b[1].total_tokens - a[1].total_tokens),
    [stats],
  )
  const keyEntries = useMemo(
    () => Object.entries(stats?.by_api_key ?? {}).sort((a, b) => b[1].total_tokens - a[1].total_tokens),
    [stats],
  )

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      {/* Hero 健康卡 */}
      <Card
        className={`relative overflow-hidden border shadow-sm ${status?.ok ? "border-success/30" : "border-destructive/30"}`}
      >
        <CardContent className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div
                className={`flex size-14 items-center justify-center rounded-2xl ${
                  status?.ok ? "bg-success-muted/40 text-success" : "bg-destructive/15 text-destructive"
                }`}
              >
                {status?.ok ? <CheckCircle2 className="size-7" /> : <XCircle className="size-7" />}
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {statusLoading ? "加载中…" : status?.ok ? "服务正常运行" : "服务异常"}
                </div>
                <div className="text-xs text-muted-foreground">
                  v{status?.version || "-"} · {config?.default_model || "-"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-6 text-center">
              <div>
                <div className="text-xl font-bold">{modelCount}</div>
                <div className="text-[11px] text-muted-foreground">模型</div>
              </div>
              <div className="hidden sm:block">
                <div className="max-w-36 truncate text-xl font-bold" title={status?.config?.cookie_source?.path}>
                  {cookieState}
                </div>
                <div className="text-[11px] text-muted-foreground">Cookie</div>
              </div>
              <Button variant="outline" size="sm" onClick={() => void loadStatus()}>
                <RefreshCw className="size-3.5" /> 刷新
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard icon={<Activity className="size-4" />} title="总请求" value={statsTotal} loading={statsLoading} detail={`范围：${rangeLabel}`} />
        <StatCard icon={<CheckCircle2 className="size-4" />} title="成功" value={success} loading={statsLoading} detail={`成功率 ${Math.round((stats?.success_rate ?? 0) * 100)}%`} />
        <StatCard icon={<XCircle className="size-4" />} title="失败" value={error} loading={statsLoading} detail={statsTotal ? `${Math.round((error / statsTotal) * 100)}%` : "-"} />
        <StatCard icon={<BarChart3 className="size-4" />} title="总 Token" value={formatTokens(stats?.total_tokens ?? 0)} loading={statsLoading} detail={`输入 ${formatTokens(stats?.prompt_tokens ?? 0)} / 输出 ${formatTokens(stats?.completion_tokens ?? 0)}`} />
        <StatCard icon={<Server className="size-4" />} title="平均耗时" value={stats ? `${stats.avg_duration_ms}ms` : "-"} loading={statsLoading} detail={stats?.total ? `${stats.total} 条记录` : "暂无记录"} />
      </div>

      {/* 快捷操作 */}
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => navigate("/admin/chat")}>
          <MessagesSquare className="size-4" /> 对话
        </Button>
        <Button variant="secondary" onClick={() => navigate("/admin/test")}>
          <FlaskConical className="size-4" /> 服务测试
        </Button>
        <Button variant="secondary" onClick={() => copyText(urls.current ?? "", "Base URL 已复制")}>
          <Copy className="size-4" /> 复制 Base URL
        </Button>
        <Button variant="secondary" onClick={() => navigate("/admin/logs")}>
          <ScrollText className="size-4" /> 查看日志
        </Button>
        <Button variant="secondary" onClick={() => navigate("/admin/network")}>
          <Globe className="size-4" /> 网络检测
        </Button>
      </div>

      {/* 请求统计 + 模型用量 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Activity className="size-4 text-primary" /> 请求统计
                <Badge variant="outline" className="text-[10px] font-normal">{rangeLabel}</Badge>
              </CardTitle>
              <Select value={range} onValueChange={(v) => setRange((v ?? "7d") as StatsRange)}>
                <SelectTrigger size="sm" className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent align="end">
                  {STATS_RANGE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {statsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                  <Metric label="总请求" value={statsTotal} />
                  <Metric label="成功" value={success} tone="text-success" />
                  <Metric label="失败" value={error} tone="text-destructive" />
                  <Metric label="总 Token" value={formatTokens(stats?.total_tokens ?? 0)} tone="text-warning" />
                  <Metric label="平均耗时" value={stats ? `${stats.avg_duration_ms}ms` : "-"} />
                </div>
                <div>
                  <div className="mb-2 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span>成功率 {successPercent}%</span>
                    <span>失败率 {errorPercent}%</span>
                  </div>
                  <div className="flex h-2 overflow-hidden rounded-full bg-muted">
                    <div className="bg-success" style={{ width: `${successPercent}%` }} />
                    <div className="bg-destructive" style={{ width: `${errorPercent}%` }} />
                    <div className="bg-muted-foreground/15" style={{ width: `${quietPercent}%` }} />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <BarChart3 className="size-4 text-primary" /> 模型用量
              </CardTitle>
              <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => navigate("/admin/logs")}>
                查看日志 <ArrowRight className="ml-1 size-3" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">按总 Token 排序，查看请求次数与输入/输出构成</p>
          </CardHeader>
          <CardContent>
            <UsageBars entries={modelEntries} loading={statsLoading} emptyLabel="暂无模型用量数据" />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* 调用地址 */}
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Globe className="size-4 text-primary" /> 调用地址
              </CardTitle>
              <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => copyText(JSON.stringify(urls, null, 2))}>
                <Copy className="mr-1 size-3" /> 复制全部
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {sortedUrls.map((item) => (
              <div key={item.key} className="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/10 px-3 py-2">
                <span className="w-16 shrink-0 text-xs text-muted-foreground">{item.label}</span>
                <span className="min-w-0 flex-1 truncate font-mono text-xs">{item.value}</span>
                <Button variant="ghost" size="icon-sm" className="size-7" onClick={() => window.open(item.value, "_blank", "noopener,noreferrer")} title="打开">
                  <ExternalLink className="size-3.5" />
                </Button>
                <Button variant="ghost" size="icon-sm" className="size-7" onClick={() => copyText(item.value)} title="复制">
                  <Copy className="size-3.5" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 运行环境 */}
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Server className="size-4 text-primary" /> 运行环境
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2">
            {envItems.map((item) => (
              <div key={item.label} className="rounded-lg border border-border/50 bg-muted/10 px-3 py-2.5">
                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <item.icon className="size-3.5" /> {item.label}
                </div>
                <div className={`mt-1 truncate text-sm font-semibold ${item.tone || ""}`}>{item.value}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* API Key 用量 */}
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-1">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <KeyRound className="size-4 text-primary" /> API Key 用量
          </CardTitle>
          <p className="text-xs text-muted-foreground">密钥仅显示脱敏前缀</p>
        </CardHeader>
        <CardContent>
          <UsageBars entries={keyEntries} loading={statsLoading} emptyLabel="暂无 API Key 用量数据" />
        </CardContent>
      </Card>

      {/* 可用模型 */}
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-1">
          <div className="flex items-center gap-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Terminal className="size-4 text-primary" /> 可用模型
            </CardTitle>
            <Badge variant="outline" className="text-[10px]">{modelCount} 个</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {statusLoading ? (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {status?.models.map((m) => (
                <button
                  key={m.id}
                  onClick={() => navigate(`/admin/test?model=${encodeURIComponent(m.id)}`)}
                  className="group rounded-xl border border-border/50 bg-muted/10 p-3 text-left transition-colors hover:bg-muted/30"
                >
                  <div className="font-mono text-xs font-medium group-hover:text-primary">{m.id}</div>
                  <div className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">{m.description}</div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {!statusLoading && !status?.ok && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertTriangle className="size-4" /> 服务状态读取异常，请检查服务是否正常运行
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, tone = "" }: { label: string; value: ReactNode; tone?: string }) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/25 px-3 py-2.5">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  )
}
