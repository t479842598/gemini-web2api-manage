import { useEffect, useMemo, useState } from "react"
import { api } from "@/lib/api-client"
import type { ConfigPayload, CookieItem, StatusData } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { Eye, EyeOff, KeyRound, Pencil, Plus, RefreshCw, Save, ShieldCheck, Trash2 } from "lucide-react"

function maskSecret(value: string): string {
  if (!value) return "-"
  if (value.length <= 10) return `${value.slice(0, 3)}***${value.slice(-2)}`
  return `${value.slice(0, 7)}...${value.slice(-4)}`
}

export default function SettingsPage() {
  const [status, setStatus] = useState<StatusData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // API keys
  const [apiKeys, setApiKeys] = useState<string[]>([])
  const [keyDraft, setKeyDraft] = useState("")
  const [editingKeyIndex, setEditingKeyIndex] = useState<number | null>(null)

  // Cookies
  const [cookieItems, setCookieItems] = useState<CookieItem[]>([])
  const [cookieDraft, setCookieDraft] = useState("")
  const [editingCookieIndex, setEditingCookieIndex] = useState<number | null>(null)
  const [showCookieRaw, setShowCookieRaw] = useState<Record<number, boolean>>({})

  // Config fields
  const [proxy, setProxy] = useState("")
  const [geminiBaseUrl, setGeminiBaseUrl] = useState("")
  const [authUser, setAuthUser] = useState("")
  const [xsrfToken, setXsrfToken] = useState("")
  const [geminiBl, setGeminiBl] = useState("")
  const [defaultModel, setDefaultModel] = useState("__all__")
  const [publicBaseUrl, setPublicBaseUrl] = useState("")
  const [emptyFallback, setEmptyFallback] = useState("")
  const [forceNonStream, setForceNonStream] = useState(false)
  const [temporaryChats, setTemporaryChats] = useState(false)
  const [adminPassword, setAdminPassword] = useState("")

  const loadStatus = async () => {
    try {
      const data = await api.status()
      setStatus(data)
      const config = data.config
      setApiKeys([...(config.api_keys || [])])
      const contents = config.cookie_contents || []
      setCookieItems(
        (config.cookie_files || []).map((path, index) => ({
          path,
          content: contents[index] || "",
        })),
      )
      setProxy(config.proxy || "")
      setGeminiBaseUrl(config.gemini_base_url || "")
      setAuthUser(config.auth_user != null ? String(config.auth_user) : "")
      setXsrfToken(config.xsrf_token || "")
      setGeminiBl(config.gemini_bl || "")
      setDefaultModel(config.default_model || "__all__")
      setPublicBaseUrl(config.public_base_url || "")
      setEmptyFallback(config.empty_response_fallback || "")
      setForceNonStream(!!config.force_non_stream)
      setTemporaryChats(!!config.temporary_chats)
      setAdminPassword("")
    } catch (err) {
      toast.error(`状态读取失败：${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void loadStatus(), 0)
    return () => window.clearTimeout(timer)
  }, [])

  const modelOptions = useMemo(
    () => [
      { value: "__all__", label: "全部模型（使用默认模型）" },
      ...(status?.models ?? []).map((m) => ({ value: m.id, label: `${m.id} - ${m.description}` })),
    ],
    [status],
  )

  // ── API Key 操作 ──
  const addApiKey = () => {
    const value = keyDraft.trim()
    if (!value) return
    setApiKeys((prev) => {
      const next = [...prev]
      if (editingKeyIndex !== null) {
        next.splice(editingKeyIndex, 1, value)
      } else {
        next.push(value)
      }
      return next
    })
    setKeyDraft("")
    setEditingKeyIndex(null)
  }

  const deleteApiKey = (index: number) => {
    setApiKeys((prev) => prev.filter((_, i) => i !== index))
  }

  // ── Cookie 操作 ──
  const addCookie = () => {
    const value = cookieDraft.trim()
    if (!value) return
    const row: CookieItem = { path: null, content: value }
    setCookieItems((prev) => {
      const next = [...prev]
      if (editingCookieIndex !== null) {
        next.splice(editingCookieIndex, 1, row)
      } else {
        next.push(row)
      }
      return next
    })
    setCookieDraft("")
    setEditingCookieIndex(null)
    toast.info("Cookie 已暂存，点击「保存配置」后生效")
  }

  const editCookie = (index: number) => {
    setEditingCookieIndex(index)
    const item = cookieItems[index]
    setCookieDraft(item.content || item.path || "")
  }

  const deleteCookie = (index: number) => {
    setCookieItems((prev) => prev.filter((_, i) => i !== index))
    setShowCookieRaw((prev) => {
      const next = { ...prev }
      delete next[index]
      return next
    })
  }

  // ── 保存 / 重读 ──
  const saveConfig = async () => {
    setSaving(true)
    try {
      const payload = {
        cookie_content: "",
        api_keys: apiKeys,
        cookie_items: cookieItems.map((item) => ({
          path: item.path ?? null,
          content: item.content ?? null,
        })),
        proxy,
        gemini_base_url: geminiBaseUrl,
        auth_user: authUser === "" ? null : Number(authUser),
        xsrf_token: xsrfToken,
        default_model: defaultModel === "__all__" ? null : defaultModel,
        public_base_url: publicBaseUrl,
        empty_response_fallback: emptyFallback,
        gemini_bl: geminiBl,
        force_non_stream: forceNonStream,
        temporary_chats: temporaryChats,
        admin_password: adminPassword,
      }
      const data = await api.saveConfig(payload)
      setStatus((prev) => (prev ? { ...prev, config: data.config } : prev))
      // 回读最新 cookie 状态
      const config = data.config
      setApiKeys([...(config.api_keys || [])])
      const contents = config.cookie_contents || []
      setCookieItems(
        (config.cookie_files || []).map((path, index) => ({
          path,
          content: contents[index] || "",
        })),
      )
      setAdminPassword("")
      const cookieCount = (config.cookie_source?.files ?? []).filter((f) => f.exists).length
      toast.success(cookieCount ? `配置已保存（${cookieCount} 个 Cookie 已落盘）` : "配置已保存")
    } catch (err) {
      toast.error(`保存失败：${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading && !status) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const previewConfig = {
    ...(status?.config ?? ({} as ConfigPayload)),
    cookie_content: "",
    cookie_contents: cookieItems.map((item) =>
      item.content ? "（已设置，隐藏）" : item.path || "",
    ),
    api_keys: apiKeys,
    admin_password: adminPassword ? "待更新" : "",
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <ShieldCheck className="size-4 text-primary" /> 配置
            </CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => void loadStatus()}>
                <RefreshCw className="size-3.5" /> 重新读取
              </Button>
              <Button size="sm" onClick={() => void saveConfig()} disabled={saving}>
                <Save className="size-3.5" /> {saving ? "保存中…" : "保存配置"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* API 密钥 */}
          <section className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <KeyRound className="size-4 text-primary" /> API 密钥
            </h3>
            <div className="flex gap-2">
              <Input
                type="password"
                value={keyDraft}
                onChange={(e) => setKeyDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addApiKey()}
                placeholder="输入 API 密钥"
              />
              <Button onClick={addApiKey}>
                <Plus className="size-4" /> {editingKeyIndex !== null ? "保存" : "新增"}
              </Button>
            </div>
            <div className="overflow-hidden rounded-lg border border-border/50">
              <table className="w-full text-sm">
                <thead className="border-b border-border/60 bg-muted/30 text-left text-[11px] text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">序号</th>
                    <th className="px-3 py-2 font-medium">密钥</th>
                    <th className="px-3 py-2 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-3 py-4 text-center text-xs text-muted-foreground">
                        未启用密钥
                      </td>
                    </tr>
                  )}
                  {apiKeys.map((item, index) => (
                    <tr key={`${item}-${index}`} className="border-b border-border/40 last:border-0">
                      <td className="px-3 py-2">{index + 1}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {editingKeyIndex === index ? item : maskSecret(item)}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="size-7"
                            onClick={() => {
                              setEditingKeyIndex(index)
                              setKeyDraft(item)
                            }}
                            title="修改"
                          >
                            <Pencil className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="size-7 text-destructive"
                            onClick={() => deleteApiKey(index)}
                            title="删除"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Cookie */}
          <section className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="size-4 text-primary" /> Cookie
            </h3>
            <Textarea
              value={cookieDraft}
              onChange={(e) => setCookieDraft(e.target.value)}
              placeholder="粘贴完整 Cookie；可新增多条，默认第一条有效"
              className="min-h-16"
            />
            <div className="flex gap-2">
              <Button onClick={addCookie}>
                <Plus className="size-4" /> {editingCookieIndex !== null ? "保存修改" : "新增 Cookie"}
              </Button>
              {editingCookieIndex !== null && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setEditingCookieIndex(null)
                    setCookieDraft("")
                  }}
                >
                  取消
                </Button>
              )}
            </div>
            <div className="overflow-hidden rounded-lg border border-border/50">
              <table className="w-full text-sm">
                <thead className="border-b border-border/60 bg-muted/30 text-left text-[11px] text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">序号</th>
                    <th className="px-3 py-2 font-medium">状态</th>
                    <th className="px-3 py-2 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {cookieItems.length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-3 py-4 text-center text-xs text-muted-foreground">
                        未配置 Cookie
                      </td>
                    </tr>
                  )}
                  {cookieItems.map((item, index) => (
                    <tr key={`${item.path}-${index}`} className="border-b border-border/40 last:border-0">
                      <td className="px-3 py-2">{index + 1}</td>
                      <td className="max-w-72 truncate px-3 py-2 font-mono text-xs">
                        {item.content ? (
                          showCookieRaw[index] ? (
                            item.content
                          ) : (
                            maskSecret(item.content)
                          )
                        ) : (
                          <span className="text-muted-foreground">{item.path || "待保存"}</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-1">
                          {item.content && (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              className="size-7"
                              onClick={() =>
                                setShowCookieRaw((prev) => ({ ...prev, [index]: !prev[index] }))
                              }
                              title={showCookieRaw[index] ? "隐藏" : "显示"}
                            >
                              {showCookieRaw[index] ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="size-7"
                            onClick={() => editCookie(index)}
                            title={item.content ? "修改" : "替换"}
                          >
                            <Pencil className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="size-7 text-destructive"
                            onClick={() => deleteCookie(index)}
                            title="删除"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* 其他配置 */}
          <section className="grid gap-3 sm:grid-cols-2">
            <Field label="新管理员密码">
              <Input
                type="password"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="留空表示不修改"
              />
            </Field>
            <Field label="代理">
              <Input
                value={proxy}
                onChange={(e) => setProxy(e.target.value)}
                placeholder="例如 http://127.0.0.1:7890 或 socks5://user:pass@host:port"
              />
            </Field>
            <Field label="Gemini Base URL">
              <Input
                value={geminiBaseUrl}
                onChange={(e) => setGeminiBaseUrl(e.target.value)}
                placeholder="留空默认 https://gemini.google.com"
              />
            </Field>
            <Field label="Google 账号序号">
              <Input
                value={authUser}
                onChange={(e) => setAuthUser(e.target.value)}
                placeholder="默认账号留空；第二账号填 1"
                type="number"
              />
            </Field>
            <Field label="XSRF Token">
              <Input
                type="password"
                value={xsrfToken}
                onChange={(e) => setXsrfToken(e.target.value)}
                placeholder="可选：不填则自动获取"
              />
            </Field>
            <Field label="Gemini BL">
              <Input
                value={geminiBl}
                onChange={(e) => setGeminiBl(e.target.value)}
                placeholder="boq_assistant-bard-web-server_YYYYMMDD.00_p0"
              />
            </Field>
            <Field label="默认模型">
              <Select value={defaultModel} onValueChange={(v) => setDefaultModel(v ?? "__all__")}>
                <SelectTrigger size="sm" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {modelOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="公网 Base URL">
              <Input
                value={publicBaseUrl}
                onChange={(e) => setPublicBaseUrl(e.target.value)}
                placeholder="例如 https://your-domain.com/v1"
              />
            </Field>
            <Field label="空响应兜底文案" className="sm:col-span-2">
              <Textarea
                value={emptyFallback}
                onChange={(e) => setEmptyFallback(e.target.value)}
                className="min-h-16"
              />
            </Field>
            <div className="flex flex-wrap items-center gap-6 sm:col-span-2">
              <Toggle label="强制非流式" checked={forceNonStream} onChange={setForceNonStream} />
              <Toggle label="临时对话" checked={temporaryChats} onChange={setTemporaryChats} />
            </div>
          </section>
        </CardContent>
      </Card>

      {/* 当前配置预览 */}
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <ShieldCheck className="size-4 text-primary" /> 当前配置
            <Badge variant="outline" className="text-[10px]">预览</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-lg border border-border/50 bg-muted/25 p-3 text-[11px] text-muted-foreground">
            {JSON.stringify(previewConfig, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}

function Field({
  label,
  children,
  className = "",
}: {
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <label className={`space-y-1.5 ${className}`}>
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </label>
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
      className="flex items-center gap-2 text-sm"
    >
      <span
        className={`relative h-5 w-9 rounded-full transition-colors ${
          checked ? "bg-primary" : "bg-muted-foreground/25"
        }`}
      >
        <span
          className={`absolute top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </span>
      {label}
    </button>
  )
}
