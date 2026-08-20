import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { marked } from "marked"
import { api } from "@/lib/api-client"
import type { StatusData, UploadFileInfo } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import {
  Bot,
  Copy,
  FileDown,
  FileText,
  ImagePlus,
  Paperclip,
  Play,
  Send,
  Trash2,
  Wrench,
  X,
} from "lucide-react"

const CHAT_STORAGE_KEY = "gemini_web2api_chat"

interface ChatMessage {
  role: "user" | "assistant"
  content: string
  images?: string[]
  fileNames?: string[]
}

interface StoredChat {
  model: string
  stream: boolean
  systemPrompt: string
  messages: ChatMessage[]
}

interface ToolCallResult {
  id: string
  name: string
  content: string
}

const AGENT_TOOLS = [
  {
    type: "function",
    function: {
      name: "get_weather",
      description: "查询城市天气",
      parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] },
    },
  },
  {
    type: "function",
    function: {
      name: "calc",
      description: "四则运算求值",
      parameters: { type: "object", properties: { expr: { type: "string" } }, required: ["expr"] },
    },
  },
  {
    type: "function",
    function: { name: "get_time", description: "获取当前时间", parameters: { type: "object", properties: {} } },
  },
  {
    type: "function",
    function: {
      name: "read_file",
      description: "读取服务器上的上传文件内容",
      parameters: { type: "object", properties: { name: { type: "string" } }, required: ["name"] },
    },
  },
]

function renderMarkdown(text: string): string {
  try {
    return marked.parse(text, { async: false }) as string
  } catch {
    return text
  }
}

function parseChatResponse(text: string): string {
  try {
    const data = JSON.parse(text)
    return data?.choices?.[0]?.message?.content || text
  } catch {
    return text
  }
}

async function executeTool(name: string, args: Record<string, unknown>): Promise<string> {
  switch (name) {
    case "get_weather":
      return JSON.stringify({ city: args.city ?? "未知", weather: "晴", temp: 25 })
    case "calc": {
      try {
        const expr = String(args.expr ?? "0")
        const result = new Function(`"use strict"; return (${expr})`)()
        return JSON.stringify({ expr, result })
      } catch {
        return JSON.stringify({ error: "表达式无效" })
      }
    }
    case "get_time":
      return JSON.stringify({ time: new Date().toLocaleString("zh-CN") })
    case "read_file": {
      const name = String(args.name ?? "")
      try {
        const data = await api.readFile(name)
        if (!data.readable) return JSON.stringify({ error: "文件不可读（过大或二进制）", size: data.size })
        return data.content.slice(0, 3000)
      } catch {
        return JSON.stringify({ error: "文件不存在" })
      }
    }
    default:
      return JSON.stringify({ ok: false, error: "unknown tool: " + name })
  }
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error("文件读取失败"))
    reader.readAsDataURL(file)
  })
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "")
    reader.onerror = () => reject(new Error("文件读取失败"))
    reader.readAsDataURL(file)
  })
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
  const [agentMode, setAgentMode] = useState(false)
  const [agentTurns, setAgentTurns] = useState(0)
  const [images, setImages] = useState<string[]>([])
  const [serverFiles, setServerFiles] = useState<UploadFileInfo[]>([])
  const listRef = useRef<HTMLDivElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadServerFiles = useCallback(async () => {
    try {
      const data = await api.files()
      setServerFiles(data.files ?? [])
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    api
      .status()
      .then((data) => {
        setStatus(data)
        if (data.models.length) setModel(data.models[0].id)
      })
      .catch(() => toast.error("状态读取失败"))
      .finally(() => setStatusLoading(false))
    void loadServerFiles()
  }, [loadServerFiles])

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

  useEffect(() => {
    try {
      localStorage.setItem(
        CHAT_STORAGE_KEY,
        JSON.stringify({ model, stream, systemPrompt, messages } satisfies StoredChat),
      )
    } catch {
      /* ignore */
    }
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

  const selectedModel =
    model === "__all__"
      ? status?.config.default_model || status?.models[0]?.id || "gemini-3.6-flash"
      : model

  // ── 图片 ──
  const pickImages = async (files: FileList | null) => {
    if (!files) return
    const next: string[] = []
    for (const f of Array.from(files).slice(0, 4)) {
      try {
        const url = await fileToDataUrl(f)
        next.push(url)
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "图片读取失败")
      }
    }
    if (next.length) setImages((prev) => [...prev, ...next])
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return
    const imageFiles: File[] = []
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        const f = item.getAsFile()
        if (f) imageFiles.push(f)
      }
    }
    if (imageFiles.length) {
      e.preventDefault()
      void pickImages(imageFiles as unknown as FileList)
    }
  }

  // ── 文件上传 ──
  const uploadFiles = async (files: FileList | null) => {
    if (!files) return
    for (const f of Array.from(files).slice(0, 5)) {
      try {
        const b64 = await fileToBase64(f)
        await api.uploadFile(f.name, b64)
        toast.success(`已上传 ${f.name}`)
      } catch (e) {
        toast.error(`上传失败 ${f.name}: ${e instanceof Error ? e.message : String(e)}`)
      }
    }
    void loadServerFiles()
  }

  const deleteServerFile = async (name: string) => {
    try {
      await api.deleteFile(name)
      toast.success(`已删除 ${name}`)
      void loadServerFiles()
    } catch (e) {
      toast.error(`删除失败：${e instanceof Error ? e.message : String(e)}`)
    }
  }

  // ── Agent 工具循环 ──
  const runAgentLoop = async (
    apiMessages: Array<Record<string, unknown>>,
    setStatus: (s: string) => void,
  ): Promise<string> => {
    for (let i = 0; i < 6; i++) {
      setStatus(`Agent 第 ${i + 1} 轮…`)
      setAgentTurns(i + 1)
      const res = await fetch("/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: selectedModel, messages: apiMessages, tools: AGENT_TOOLS }),
      })
      const text = await res.text()
      if (!res.ok) throw new Error(text.slice(0, 300))
      const data = JSON.parse(text)
      const msg = data.choices?.[0]?.message
      apiMessages.push(msg)
      const tcs: Array<{ id: string; function: { name: string; arguments: string } }> = msg?.tool_calls ?? []
      if (!tcs.length) {
        return msg?.content ?? "（空响应）"
      }
      const results: ToolCallResult[] = []
      for (const tc of tcs) {
        let args: Record<string, unknown>
        try {
          args = JSON.parse(tc.function.arguments || "{}") as Record<string, unknown>
        } catch {
          args = {}
        }
        const content = await executeTool(tc.function.name, args)
        results.push({ id: tc.id, name: tc.function.name, content })
        apiMessages.push({ role: "tool", tool_call_id: tc.id, name: tc.function.name, content })
      }
      // 在 UI 上展示工具调用痕迹
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `🔧 工具调用：${results.map((r) => r.name).join(", ")}`,
        },
      ])
    }
    return "（Agent 达到最大轮次）"
  }

  // ── 发送 ──
  const sendChat = async () => {
    const content = input.trim()
    if (!content && !images.length) {
      toast.warning("请输入内容或添加图片")
      return
    }
    if (sending) return

    const userMsg: ChatMessage = { role: "user", content }
    if (images.length) userMsg.images = [...images]
    setMessages((prev) => [...prev, userMsg])
    setImages([])
    setInput("")
    setSending(true)

    try {
      const apiMessages: Array<Record<string, unknown>> = []
      if (systemPrompt.trim()) apiMessages.push({ role: "system", content: systemPrompt.trim() })
      if (images.length) {
        apiMessages.push({
          role: "user",
          content: [
            { type: "text", text: content || "请描述这张图片" },
            ...images.map((url) => ({ type: "image_url", image_url: { url } })),
          ],
        })
      } else {
        apiMessages.push({ role: "user", content })
      }

      let answer: string
      if (agentMode) {
        answer = await runAgentLoop(apiMessages, () => {})
      } else {
        const res = await fetch("/v1/chat/completions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: selectedModel, messages: apiMessages, stream }),
        })
        const text = await res.text()
        if (!res.ok) throw new Error(text.slice(0, 300))
        answer = parseChatResponse(text) || status?.config.empty_response_fallback || "（空响应）"
      }
      setMessages((prev) => [...prev, { role: "assistant", content: answer }])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `**调用失败：** ${err instanceof Error ? err.message : String(err)}` },
      ])
    } finally {
      setSending(false)
      setAgentTurns(0)
    }
  }

  // ── 服务器文件加入上下文 ──
  const addServerFile = async (name: string) => {
    try {
      const data = await api.readFile(name)
      if (!data.readable) {
        toast.warning(`${name} 不可读（${data.size} 字节，过大或二进制）`)
        return
      }
      const text = data.content.slice(0, 8000)
      setMessages((prev) => [
        ...prev,
        { role: "user", content: `[服务器文件 ${name} 内容]\n${text}\n请基于以上内容回答。`, fileNames: [name] },
      ])
      toast.success(`已将 ${name} 内容加入对话`)
    } catch (e) {
      toast.error(`读取失败：${e instanceof Error ? e.message : String(e)}`)
    }
  }

  const clearChat = () => {
    setMessages([])
    setSystemPrompt("")
    setImages([])
  }

  const copyText = async (t: string, label = "已复制") => {
    try {
      await navigator.clipboard.writeText(t)
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
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{stream ? "流式" : "非流式"}</Badge>
                <Badge
                  variant={agentMode ? "default" : "outline"}
                  className={agentMode ? "cursor-pointer" : "cursor-pointer"}
                  onClick={() => setAgentMode((a) => !a)}
                >
                  <Wrench className="mr-1 size-3" /> Agent
                  {agentMode ? "开" : "关"}
                </Badge>
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={clearChat}>
                  <Trash2 className="size-3.5" /> 清空
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div
              ref={listRef}
              className="h-[46vh] space-y-3 overflow-y-auto rounded-lg border border-border/50 bg-muted/10 p-3"
            >
              {messages.length === 0 && !sending && (
                <p className="py-14 text-center text-xs text-muted-foreground">
                  支持多轮对话、图片粘贴/上传、文件上传与 Agent 工具调用
                </p>
              )}
              {messages.map((item, index) => (
                <MessageItem key={index} item={item} />
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-xl border border-border/60 bg-card px-4 py-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="flex gap-1">
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/50" />
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                      </span>
                      {agentMode && agentTurns > 0 ? `Agent 第 ${agentTurns} 轮…` : "思考中…"}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 待发送图片 */}
            {images.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {images.map((url, i) => (
                  <div key={i} className="relative">
                    <img src={url} alt="" className="h-16 w-16 rounded-lg border border-border/60 object-cover" />
                    <button
                      onClick={() => setImages((prev) => prev.filter((_, j) => j !== i))}
                      className="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-destructive text-white"
                    >
                      <X className="size-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-2">
              <Textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="System Prompt（可选）：影响模型行为"
                className="min-h-14"
              />
              <div className="flex flex-wrap gap-2">
                <Select value={model} onValueChange={(v) => setModel(v ?? "gemini-3.6-flash")}>
                  <SelectTrigger size="sm" className="max-w-64">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {modelOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" size="sm" onClick={() => setStream((s) => !s)}>
                  {stream ? "流式" : "非流式"}
                </Button>
                <Button variant="outline" size="sm" onClick={() => imageInputRef.current?.click()} title="添加图片（支持粘贴）">
                  <ImagePlus className="size-4" /> 图片
                </Button>
                <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} title="上传文件到服务器">
                  <Paperclip className="size-4" /> 文件
                </Button>
                <input
                  ref={imageInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    void pickImages(e.target.files)
                    e.target.value = ""
                  }}
                />
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    void uploadFiles(e.target.files)
                    e.target.value = ""
                  }}
                />
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onPaste={handlePaste}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void sendChat()
                  }}
                  placeholder="输入内容（Ctrl+Enter 发送，支持粘贴图片）"
                  className="min-w-48 flex-1"
                />
                <Button onClick={() => void sendChat()} disabled={sending}>
                  <Send className="size-4" /> 发送
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <FileText className="size-4 text-primary" /> 服务器文件
                </CardTitle>
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => void loadServerFiles()}>
                  刷新
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {serverFiles.length === 0 ? (
                <p className="py-6 text-center text-xs text-muted-foreground">暂无上传文件</p>
              ) : (
                <div className="max-h-64 space-y-1.5 overflow-y-auto">
                  {serverFiles.map((f) => (
                    <div
                      key={f.name}
                      className="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/10 px-2.5 py-2"
                    >
                      <FileText className="size-4 shrink-0 text-muted-foreground" />
                      <button
                        className="min-w-0 flex-1 truncate text-left text-xs hover:text-primary"
                        title={`${f.name}（${f.size} 字节）加入对话`}
                        onClick={() => void addServerFile(f.name)}
                      >
                        {f.name}
                      </button>
                      <button
                        onClick={() => void deleteServerFile(f.name)}
                        className="shrink-0 text-muted-foreground hover:text-destructive"
                        title="删除"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
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
                <p className="mb-2 font-medium text-foreground">说明</p>
                <p>• 图片：点击「图片」或直接粘贴到输入框</p>
                <p>• 文件：上传后点文件名加入对话</p>
                <p className="mt-1">• Agent：开启后自动执行工具循环（天气/计算/时间/读文件）</p>
              </div>
              {statusLoading && <Skeleton className="h-24 w-full" />}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function MessageItem({ item }: { item: ChatMessage }) {
  return (
    <div className={`flex ${item.role === "user" ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
          item.role === "user"
            ? "bg-primary text-primary-foreground"
            : "border border-border/60 bg-card"
        }`}
      >
        {item.role === "user" ? (
          <div className="space-y-2">
            {item.content && <p className="whitespace-pre-wrap">{item.content}</p>}
            {item.images && item.images.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {item.images.map((url, i) => (
                  <img key={i} src={url} alt="" className="h-20 w-20 rounded-lg border object-cover" />
                ))}
              </div>
            )}
            {item.fileNames && item.fileNames.length > 0 && (
              <p className="text-[10px] opacity-70">📎 {item.fileNames.join(", ")}</p>
            )}
          </div>
        ) : item.content.startsWith("🔧") ? (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Bot className="size-3.5" /> {item.content}
          </div>
        ) : (
          <div
            className="prose prose-sm max-w-none dark:prose-invert [&_pre]:overflow-x-auto"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(item.content) }}
          />
        )}
      </div>
    </div>
  )
}
