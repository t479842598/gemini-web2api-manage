import { useEffect, useMemo, useRef, useState } from "react"
import { marked } from "marked"
import { api } from "@/lib/api-client"
import type { StatusData } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { Copy, FileDown, Play, Send, Trash2 } from "lucide-react"

const CHAT_STORAGE_KEY = "gemini_web2api_chat"

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

interface StoredChat {
  model: string
  stream: boolean
  systemPrompt: string
  messages: ChatMessage[]
}

function renderMarkdown(text: string): string {
  try {
    return marked.parse(text, { async: false }) as string
  } catch {
    return text
  }
}

function parseChatResponse(text: string, streamed: boolean): string {
  if (!streamed) {
    try {
      const data = JSON.parse(text)
      return (
        data?.choices?.[0]?.message?.content ||
        data?.choices?.[0]?.delta?.content ||
        text
      )
    } catch {
      return text
    }
  }
  let answer = ""
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed.startsWith("data:")) continue
    const payload = trimmed.slice(5).trim()
    if (!payload || payload === "[DONE]") continue
    try {
      const data = JSON.parse(payload)
      answer += data?.choices?.[0]?.delta?.content || data?.choices?.[0]?.message?.content || ""
    } catch {
      /* ignore */
    }
  }
  return answer
}

export default function ChatPage() {
  const [status, setStatus] = useState<StatusData | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [model, setModel] = useState("gemini-3.6-flash")
  const [stream, setStream] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState("")
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api
      .status()
      .then((data) => {
        setStatus(data)
        if (data.models.length) setModel(data.models[0].id)
      })
      .catch(() => toast.error("状态读取失败"))
      .finally(() => setStatusLoading(false))
  }, [])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(CHAT_STORAGE_KEY)
      if (!raw) return
      const data = JSON.parse(raw) as StoredChat
      if (data.messages) setMessages(data.messages)
      if (data.model) setModel(data.model)
      if (data.stream !== undefined) setStream(data.stream)
      if (data.systemPrompt !== undefined) setSystemPrompt(data.systemPrompt)
    } catch {
      /* ignore */
    }
  }, [])

  const persist = (next: StoredChat) => {
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(next))
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    persist({ model, stream, systemPrompt, messages })
  }, [model, stream, systemPrompt, messages])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, sending])

  const modelOptions = useMemo(
    () => [
      { value: "__all__", label: "全部模型（使用默认模型）" },
      ...(status?.models ?? []).map((m) => ({ value: m.id, label: `${m.id} - ${m.description}` })),
    ],
    [status],
  )

  const selectedModel = model === "__all__"
    ? status?.config.default_model || status?.models[0]?.id || "gemini-3.6-flash"
    : model

  const sendChat = async () => {
    const content = input.trim()
    if (!content) {
      toast.warning("请输入对话内容")
      return
    }
    if (sending) return
    const apiMessages: Array<{ role: string; content: string }> = []
    if (systemPrompt.trim()) apiMessages.push({ role: "system", content: systemPrompt.trim() })
    apiMessages.push(...messages, { role: "user", content })
    setMessages((prev) => [...prev, { role: "user", content }])
    setInput("")
    setSending(true)
    try {
      const res = await fetch("/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: selectedModel, messages: apiMessages, stream }),
      })
      const text = await res.text()
      if (!res.ok) throw new Error(text.slice(0, 300))
      const answer = parseChatResponse(text, stream)
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: answer || status?.config.empty_response_fallback || "（空响应）" },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `**调用失败：** ${err instanceof Error ? err.message : String(err)}` },
      ])
    } finally {
      setSending(false)
    }
  }

  const clearChat = () => {
    setMessages([])
    setSystemPrompt("")
  }

  const copyText = async (text: string, label = "已复制") => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(label)
    } catch {
      toast.warning("复制失败，请手动复制")
    }
  }

  const exportMarkdown = () => {
    const lines = messages.map((m) => {
      const role = m.role === "user" ? "**你**" : "**助手**"
      return `### ${role}\n\n${m.content}`
    })
    if (systemPrompt) lines.unshift(`### System\n\n${systemPrompt}`)
    return lines.join("\n\n---\n\n")
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 shadow-sm lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Send className="size-4 text-primary" /> 对话
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{stream ? "流式" : "非流式"}</Badge>
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={clearChat}>
                  <Trash2 className="size-3.5" /> 清空
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div
              ref={listRef}
              className="h-[52vh] space-y-3 overflow-y-auto rounded-lg border border-border/50 bg-muted/10 p-3"
            >
              {messages.length === 0 && !sending && (
                <p className="py-16 text-center text-xs text-muted-foreground">
                  选择模型后输入内容，即可用当前服务发起对话
                </p>
              )}
              {messages.map((item, index) => (
                <div key={index} className={`flex ${item.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                      item.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "border border-border/60 bg-card"
                    }`}
                  >
                    {item.role === "user" ? (
                      <p className="whitespace-pre-wrap">{item.content}</p>
                    ) : (
                      <div
                        className="prose prose-sm max-w-none dark:prose-invert [&_pre]:overflow-x-auto"
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(item.content) }}
                      />
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-xl border border-border/60 bg-card px-4 py-3">
                    <div className="flex gap-1">
                      <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/50" />
                      <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                      <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="System Prompt（可选）：影响模型行为"
                className="min-h-14"
              />
              <div className="flex gap-2">
                <Select value={model} onValueChange={(v) => setModel(v ?? "gemini-3.6-flash")}>
                  <SelectTrigger size="sm" className="max-w-72">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {modelOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setStream((s) => !s)}
                  className="shrink-0"
                  title="切换流式输出"
                >
                  {stream ? "流式" : "非流式"}
                </Button>
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void sendChat()
                  }}
                  placeholder="输入对话内容（Ctrl+Enter 发送）"
                  className="flex-1"
                />
                <Button onClick={() => void sendChat()} disabled={sending} className="shrink-0">
                  <Send className="size-4" /> 发送
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Play className="size-4 text-primary" /> 操作
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button variant="outline" className="w-full justify-start" onClick={() => copyText(JSON.stringify(messages, null, 2))}>
              <Copy className="size-4" /> 复制 JSON
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => copyText(exportMarkdown(), "Markdown 已复制")}>
              <FileDown className="size-4" /> 导出 Markdown
            </Button>
            <div className="rounded-lg border border-border/60 bg-muted/25 p-3 text-xs text-muted-foreground">
              <p className="mb-2 font-medium text-foreground">调用说明</p>
              <p className="break-all">Base URL: {status?.urls.current || "/v1"}</p>
              <p className="mt-1 break-all">Chat: POST {status?.urls.current || "/v1"}/chat/completions</p>
              <p className="mt-1">流式: 按请求 stream 参数控制</p>
            </div>
            {statusLoading && <Skeleton className="h-24 w-full" />}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
