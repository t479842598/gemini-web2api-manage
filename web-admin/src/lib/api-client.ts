import type {
  ConfigPayload,
  CookieItem,
  LogsData,
  NetworkData,
  SessionInfo,
  StatsData,
  StatsRange,
  StatusData,
} from "@/types"

const API_BASE = "/admin/api"

class ApiClientError extends Error {
  status: number
  data: unknown

  constructor(status: number, data: unknown) {
    let message = `Request failed (${status})`
    if (data && typeof data === "object" && "error" in data) {
      const err = (data as { error?: { message?: string } }).error
      if (err?.message) message = err.message
    }
    super(message)
    this.status = status
    this.data = data
  }
}

export { ApiClientError }

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> | undefined),
  }
  if (options?.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json"
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  })
  const text = await res.text()
  let json: unknown = {}
  try {
    json = text ? JSON.parse(text) : {}
  } catch {
    json = { error: { message: text.slice(0, 200) } }
  }
  if (!res.ok) {
    throw new ApiClientError(res.status, json)
  }
  return json as T
}

export const api = {
  // ── Auth ──
  session: () => request<SessionInfo>("/auth"),
  login: (password: string) =>
    request<{ ok: boolean }>("/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  logout: () => request<{ ok: boolean }>("/logout", { method: "POST" }),

  // ── Status / Config ──
  status: () => request<StatusData>("/status"),
  saveConfig: (payload: Record<string, unknown>) =>
    request<{ ok: boolean; config: ConfigPayload }>("/config", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // ── Network ──
  network: () => request<NetworkData>("/network"),

  // ── Stats ──
  stats: (range: StatsRange = "7d") =>
    request<StatsData>(`/stats?range=${range}`),

  // ── Logs ──
  logs: (params?: { tail?: number; offset?: number }) => {
    const sp = new URLSearchParams()
    if (params?.tail) sp.set("tail", String(params.tail))
    if (params?.offset !== undefined) sp.set("offset", String(params.offset))
    const qs = sp.toString()
    return request<LogsData>(`/logs${qs ? `?${qs}` : ""}`)
  },
}

/** 构造 config 保存 payload（cookie 用全量快照协议） */
export function buildConfigPayload(
  fields: {
    apiKeys?: string[]
    cookieItems?: CookieItem[]
    proxy?: string
    geminiBaseUrl?: string
    authUser?: number | null
    xsrfToken?: string
    defaultModel?: string
    publicBaseUrl?: string
    emptyResponseFallback?: string
    geminiBl?: string
    temporaryChats?: boolean
    forceNonStream?: boolean
    adminPassword?: string
  },
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    cookie_content: "",
  }
  if (fields.apiKeys !== undefined) payload.api_keys = fields.apiKeys
  if (fields.cookieItems !== undefined) payload.cookie_items = fields.cookieItems
  if (fields.proxy !== undefined) payload.proxy = fields.proxy
  if (fields.geminiBaseUrl !== undefined) payload.gemini_base_url = fields.geminiBaseUrl
  if (fields.authUser !== undefined) payload.auth_user = fields.authUser
  if (fields.xsrfToken !== undefined) payload.xsrf_token = fields.xsrfToken
  if (fields.defaultModel !== undefined) payload.default_model = fields.defaultModel
  if (fields.publicBaseUrl !== undefined) payload.public_base_url = fields.publicBaseUrl
  if (fields.emptyResponseFallback !== undefined)
    payload.empty_response_fallback = fields.emptyResponseFallback
  if (fields.geminiBl !== undefined) payload.gemini_bl = fields.geminiBl
  if (fields.temporaryChats !== undefined) payload.temporary_chats = fields.temporaryChats
  if (fields.forceNonStream !== undefined) payload.force_non_stream = fields.forceNonStream
  if (fields.adminPassword !== undefined) payload.admin_password = fields.adminPassword
  // 未提交的字段保持后端现状：仅回传 cookie 快照时，其余键不发送。
  return payload
}
