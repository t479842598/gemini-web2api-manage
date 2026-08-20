export interface ModelInfo {
  id: string
  description: string
}

export interface CookieFileInfo {
  path: string
  exists: boolean
  size: number
}

export interface CookieSource {
  env: boolean
  path: string
  exists: boolean
  size: number
  files: CookieFileInfo[]
}

export interface ConfigPayload {
  cookie_file: string
  cookie_files: string[]
  cookie_content: string
  cookie_contents: string[]
  cookie_source: CookieSource
  proxy: string
  gemini_base_url: string
  auth_user: number | null
  xsrf_token: string
  default_model: string
  public_base_url: string
  empty_response_fallback: string
  api_keys: string[]
  gemini_bl: string
  temporary_chats: boolean
  force_non_stream: boolean
  admin_password_set: boolean
}

export interface Urls {
  local?: string
  lan?: string
  current?: string
  public?: string
  admin?: string
}

export interface Connectivity {
  ok: boolean
  status: number | null
  latency_ms: number
  error?: string
}

export interface StatusData {
  ok: boolean
  version: string
  models: ModelInfo[]
  config: ConfigPayload
  urls: Urls
  logs: {
    path: string
    exists: boolean
    size: number
    modified: number | null
    candidates: string[]
  }
  admin_static: {
    path: string
    index: string
    ready: boolean
  }
}

export interface NetworkData {
  local_ip: string
  public_ip: string
  city: string
  region: string
  country: string
  org: string
  timezone: string
  proxy_enabled: boolean
  connectivity: {
    gemini: Connectivity
    google: Connectivity
  }
  raw_error: string
}

export interface LogsData {
  content: string
  offset: number
  size: number
  path: string
  exists: boolean
  candidates: string[]
  error?: string
}

export interface UsageAgg {
  count: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  success: number
}

export interface TrendBucket {
  bucket: string
  count: number
  success: number
}

export interface StatsData {
  ok: boolean
  range: string
  total: number
  success: number
  error: number
  success_rate: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  avg_duration_ms: number
  by_model: Record<string, UsageAgg>
  by_api_key: Record<string, UsageAgg>
  by_endpoint: Record<string, UsageAgg>
  trend: TrendBucket[]
}

export type StatsRange = "1d" | "3d" | "7d" | "30d" | "all"

export interface SessionInfo {
  authenticated: boolean
}

export interface CookieItem {
  path: string | null
  content: string | null
}

export interface UploadFileInfo {
  name: string
  size: number
  modified: number
}

export interface FilesData {
  ok: boolean
  dir: string
  files: UploadFileInfo[]
}

export interface FileContentData {
  ok: boolean
  name: string
  size: number
  readable: boolean
  truncated: boolean
  content: string
}
