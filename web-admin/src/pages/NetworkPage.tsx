import { useEffect, useState } from "react"
import { api } from "@/lib/api-client"
import type { NetworkData } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { Globe, RefreshCw, Server } from "lucide-react"

export default function NetworkPage() {
  const [network, setNetwork] = useState<NetworkData | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async (showToast = false) => {
    setLoading(true)
    try {
      const data = await api.network()
      setNetwork(data)
      if (showToast) toast.success("网络信息已刷新")
    } catch (err) {
      toast.error(`网络检测失败：${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const locationText = [network?.country, network?.region, network?.city]
    .filter(Boolean)
    .join(" / ") || "未获取"

  const items: Array<{ label: string; value: string }> = [
    { label: "本机局域网 IP", value: network?.local_ip || "-" },
    { label: "公网 IP", value: network?.public_ip || "-" },
    { label: "所在地区", value: locationText },
    { label: "运营商 / ASN", value: network?.org || "-" },
    { label: "时区", value: network?.timezone || "-" },
    { label: "代理", value: network?.proxy_enabled ? "已启用" : "未启用" },
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Globe className="size-4 text-primary" /> 网络信息
            </CardTitle>
            <Button variant="outline" size="sm" onClick={() => void load(true)} disabled={loading}>
              <RefreshCw className="size-3.5" /> 重新检测
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading && !network ? (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <div key={item.label} className="rounded-xl border border-border/50 bg-muted/10 p-3">
                  <div className="text-[11px] text-muted-foreground">{item.label}</div>
                  <div className="mt-1 truncate text-sm font-semibold" title={item.value}>
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <ConnectivityCard
          title="Gemini 连通性"
          data={network?.connectivity?.gemini}
          loading={loading}
        />
        <ConnectivityCard
          title="Google 连通性"
          data={network?.connectivity?.google}
          loading={loading}
        />
      </div>
    </div>
  )
}

function ConnectivityCard({
  title,
  data,
  loading,
}: {
  title: string
  data: { ok: boolean; status: number | null; latency_ms: number; error?: string } | undefined
  loading: boolean
}) {
  return (
    <Card className="border-border/60 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Server className="size-4 text-primary" /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading && !data ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <div className="space-y-2">
            <Badge
              variant={data?.ok ? "outline" : "destructive"}
              className={data?.ok ? "border-success/40 text-success" : undefined}
            >
              {data?.ok ? "连通" : "不可达"}
              {data?.latency_ms != null ? ` · ${data.latency_ms}ms` : ""}
            </Badge>
            <pre className="overflow-x-auto rounded-lg border border-border/50 bg-muted/25 p-3 text-[11px] text-muted-foreground">
              {JSON.stringify(data ?? {}, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
