import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { api } from "@/lib/api-client"
import type { StatusData } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { Clipboard, FlaskConical, Play, Trash2 } from "lucide-react"

const ENDPOINT_OPTIONS = [
  { value: "chat", label: "OpenAI Chat Completions" },
  { value: "responses", label: "OpenAI Responses" },
  { value: "google", label: "Google generateContent" },
  { value: "google-stream", label: "Google streamGenerateContent" },
]

function pretty(data: unknown): string {
  if (typeof data === "string") {
    try {
      return JSON.stringify(JSON.parse(data), null, 2)
    } catch {
      return data
    }
  }
  return JSON.stringify(data, null, 2)
}

export default function TestPage() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<StatusData | null>(null)
  const [endpoint, setEndpoint] = useState("chat")
  const [model, setModel] = useState("gemini-3.6-flash")
  const [stream, setStream] = useState(false)
  const [prompt, setPrompt] = useState("你好，请用一句话说明当前服务是否可用。")
  const [result, setResult] = useState("")
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    api
      .status()
      .then((data) => {
        setStatus(data)
        const q = searchParams.get("model")
        if (q) setModel(q)
        else if (data.models.length) setModel(data.models[0].id)
      })
      .catch(() => toast.error("状态读取失败"))
  }, [searchParams])

  const modelOptions = useMemo(
    () => [
      { value: "__all__", label: "全部模型（使用默认模型）" },
      ...(status?.models ?? []).map((m) => ({ value: m.id, label: `${m.id} - ${m.description}` })),
    ],
    [status],
  )

  const selectedModel =
    model === "__all__"
      ? status?.config.default_model || status?.models[0]?.id || "gemini-3.6-flash"
      : model

  const requestForTest = (): [string, Record<string, unknown>] => {
    if (endpoint === "responses") {
      return ["/v1/responses", { model: selectedModel, input: prompt, stream: false }]
    }
    if (endpoint === "google" || endpoint === "google-stream") {
      const method = endpoint === "google-stream" ? "streamGenerateContent" : "generateContent"
      return [
        `/v1beta/models/${encodeURIComponent(selectedModel)}:${method}`,
        { contents: [{ role: "user", parts: [{ text: prompt }] }] },
      ]
    }
    return [
      "/v1/chat/completions",
      { model: selectedModel, messages: [{ role: "user", content: prompt }], stream },
    ]
  }

  const curlCommand = useMemo(() => {
    const base = status?.urls.current || "/v1"
    const p = prompt.replace(/"/g, '\\"')
    if (endpoint === "responses") {
      return `curl ${base}/responses -H "Content-Type: application/json" -d "{\\"model\\":\\"${selectedModel}\\",\\"input\\":\\"${p}\\"}"`
    }
    if (endpoint.startsWith("google")) {
      const method = endpoint === "google-stream" ? "streamGenerateContent" : "generateContent"
      return `curl ${window.location.origin}/v1beta/models/${selectedModel}:${method} -H "Content-Type: application/json" -d "{\\"contents\\":[{\\"role\\":\\"user\\",\\"parts\\":[{\\"text\\":\\"${p}\\"}]}]}"`
    }
    return `curl ${base}/chat/completions -H "Content-Type: application/json" -d "{\\"model\\":\\"${selectedModel}\\",\\"messages\\":[{\\"role\\":\\"user\\",\\"content\\":\\"${p}\\"}],\\"stream\\":${stream}}"`
  }, [endpoint, prompt, selectedModel, status, stream])

  const runTest = async () => {
    setTesting(true)
    setResult("请求中...")
    try {
      const [path, body] = requestForTest()
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const text = await res.text()
      if (!res.ok) throw new Error(pretty(text))
      setResult(pretty(text))
    } catch (err) {
      setResult(`请求失败\n${err instanceof Error ? err.message : String(err)}`)
      toast.error("测试失败")
    } finally {
      setTesting(false)
    }
  }

  const copyText = async (text: string, label = "已复制") => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(label)
    } catch {
      toast.warning("复制失败，请手动复制")
    }
  }

  const callGuide = useMemo(
    () =>
      [
        `Base URL: ${status?.urls.current || "/v1"}`,
        `Chat: POST ${status?.urls.current || "/v1"}/chat/completions`,
        `Responses: POST ${status?.urls.current || "/v1"}/responses`,
        `模型: ${selectedModel}`,
        "流式: 按请求 stream 参数控制",
      ].join("\n"),
    [status, selectedModel],
  )

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <FlaskConical className="size-4 text-primary" /> 请求
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1.5">
                <span className="text-xs text-muted-foreground">接口</span>
                <Select value={endpoint} onValueChange={(v) => setEndpoint(v ?? "chat")}>
                  <SelectTrigger size="sm" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ENDPOINT_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
              <label className="space-y-1.5">
                <span className="text-xs text-muted-foreground">模型</span>
                <Select value={model} onValueChange={(v) => setModel(v ?? "gemini-3.6-flash")}>
                  <SelectTrigger size="sm" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {modelOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
            </div>
            <label className="space-y-1.5">
              <span className="text-xs text-muted-foreground">Prompt</span>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="min-h-40"
              />
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => void runTest()} disabled={testing}>
                <Play className="size-4" /> {testing ? "测试中…" : "运行测试"}
              </Button>
              <Button variant="outline" onClick={() => copyText(curlCommand, "curl 已复制")}>
                <Clipboard className="size-4" /> 复制 curl
              </Button>
              <Button variant="ghost" onClick={() => setResult("")}>
                <Trash2 className="size-4" /> 清空
              </Button>
              {endpoint === "chat" && (
                <Button variant="outline" size="sm" onClick={() => setStream((s) => !s)}>
                  {stream ? "流式" : "非流式"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <FlaskConical className="size-4 text-primary" /> 响应
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="min-h-72 overflow-x-auto rounded-lg border border-border/50 bg-muted/25 p-3 text-[11px] text-muted-foreground">
              {result || "等待测试结果"}
            </pre>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <FlaskConical className="size-4 text-primary" /> 调用方法
            </CardTitle>
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => copyText(callGuide, "调用说明已复制")}>
              <Clipboard className="size-3.5" /> 复制说明
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-lg border border-border/50 bg-muted/25 p-3 text-[11px] text-muted-foreground">
            {callGuide}
          </pre>
        </CardContent>
      </Card>

      {!status && <Skeleton className="h-32 w-full" />}
    </div>
  )
}
