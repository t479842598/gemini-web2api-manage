import { useCallback, useEffect, useRef, useState } from "react"
import { api } from "@/lib/api-client"
import type { LogsData } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { Copy, RefreshCw, ScrollText, Trash2 } from "lucide-react"

export default function LogsPage() {
  const [logs, setLogs] = useState<LogsData | null>(null)
  const [text, setText] = useState("")
  const [offset, setOffset] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoLogs, setAutoLogs] = useState(true)
  const [stickToBottom, setStickToBottom] = useState(true)
  const [filter, setFilter] = useState("")
  const boxRef = useRef<HTMLPreElement>(null)

  const readLogs = useCallback(async (reset = false) => {
    try {
      const query = reset || offset === null ? { tail: 60000 } : { offset }
      const data = await api.logs(query)
      setOffset(data.offset)
      setLogs(data)
      if (reset) {
        setText(data.content)
      } else {
        setText((prev) => (data.content ? prev + data.content : prev))
      }
    } catch (err) {
      if (reset) setText(`日志读取失败：${err instanceof Error ? err.message : String(err)}`)
      toast.warning(`日志读取失败：${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }, [offset])

  useEffect(() => {
    void readLogs(true)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!autoLogs) return
    const timer = setInterval(() => void readLogs(false), 1800)
    return () => clearInterval(timer)
  }, [autoLogs, readLogs])

  useEffect(() => {
    if (stickToBottom && boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight
    }
  }, [text, stickToBottom])

  const filtered = filter.trim()
    ? text.split("\n").filter((line) => line.toLowerCase().includes(filter.toLowerCase())).join("\n")
    : text

  const logMeta = logs
    ? `日志路径：${logs.path} · ${logs.exists ? `${logs.size} bytes` : "文件不存在"}`
    : "日志路径：未获取"

  const copyText = async (t: string, label = "已复制") => {
    try {
      await navigator.clipboard.writeText(t)
      toast.success(label)
    } catch {
      toast.warning("复制失败，请手动复制")
    }
  }

  if (loading && !logs) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <ScrollText className="size-4 text-primary" /> 运行日志
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="搜索日志…"
                className="w-44"
              />
              <Toggle label="自动滚动" checked={stickToBottom} onChange={setStickToBottom} />
              <Toggle label="自动更新" checked={autoLogs} onChange={setAutoLogs} />
              <Button variant="outline" size="icon-sm" className="size-8" onClick={() => void readLogs(true)} title="刷新">
                <RefreshCw className="size-3.5" />
              </Button>
              <Button variant="outline" size="icon-sm" className="size-8" onClick={() => copyText(text, "日志已复制")} title="复制">
                <Copy className="size-3.5" />
              </Button>
              <Button
                variant="outline"
                size="icon-sm"
                className="size-8 text-destructive"
                onClick={() => {
                  setText("")
                  setFilter("")
                  setOffset(null)
                }}
                title="清空"
              >
                <Trash2 className="size-3.5" />
              </Button>
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground">
            {logMeta}
            {filter.trim() ? ` · 过滤：${filter.trim()}` : ""}
          </p>
        </CardHeader>
        <CardContent>
          <pre
            ref={boxRef}
            className="h-[68vh] overflow-auto rounded-lg border border-border/50 bg-muted/25 p-3 text-[11px] leading-relaxed text-muted-foreground"
          >
            {filtered || "暂无日志，服务产生输出后会显示在这里。"}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 text-xs text-muted-foreground"
    >
      <span
        className={`relative h-4 w-8 rounded-full transition-colors ${
          checked ? "bg-primary" : "bg-muted-foreground/25"
        }`}
      >
        <span
          className={`absolute top-0.5 size-3 rounded-full bg-white shadow-sm transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </span>
      {label}
    </button>
  )
}
