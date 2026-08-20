<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { marked } from 'marked'
import {
  NButton,
  NCheckbox,
  NConfigProvider,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NInputNumber,
  NMessageProvider,
  NSelect,
  NSpace,
  NSpin,
  NStatistic,
  NSwitch,
  NTag,
  NPopconfirm,
  NPopover,
  NDropdown,
  createDiscreteApi,
  darkTheme,
  lightTheme
} from 'naive-ui'
import {
  AnalyticsOutline,
  AlertCircleOutline,
  ChatbubbleEllipsesOutline,
  CheckmarkCircleOutline,
  ClipboardOutline,
  CodeSlashOutline,
  CopyOutline,
  DocumentTextOutline,
  EyeOutline,
  FlashOutline,
  GlobeOutline,
  KeyOutline,
  LinkOutline,
  LogOutOutline,
  MoonOutline,
  OpenOutline,
  PlayOutline,
  RefreshOutline,
  SaveOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  SunnyOutline,
  TerminalOutline,
  TrashOutline
} from '@vicons/ionicons5'

const { message } = createDiscreteApi(['message'])

// ─── Theme management: dark by default, auto follows system, manual override ─
const THEME_KEY = 'gw_admin_theme'
const theme = ref('dark')
const isDark = computed(() => {
  if (theme.value === 'dark') return true
  if (theme.value === 'light') return false
  return window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)').matches : true
})

function applyTheme() {
  const dark = isDark.value
  document.documentElement.classList.toggle('dark', dark)
  try {
    localStorage.setItem(THEME_KEY, theme.value)
  } catch (_) {}
}

function setTheme(value) {
  theme.value = value
  applyTheme()
}

const themeOptions = [
  { label: '暗色（默认）', value: 'dark' },
  { label: '跟随系统', value: 'auto' },
  { label: '亮色', value: 'light' }
]

function loadTheme() {
  try {
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === 'dark' || stored === 'light' || stored === 'auto') theme.value = stored
  } catch (_) {}
  applyTheme()
}

const themeOverrides = {
  common: {
    primaryColor: '#18a058',
    primaryColorHover: '#36ad6a',
    primaryColorPressed: '#0c7a43',
    primaryColorSuppl: '#36ad6a',
    infoColor: '#2080f0',
    infoColorHover: '#4098fc',
    infoColorPressed: '#1060c9',
    borderRadius: '8px',
    fontFamily: 'Lato, "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
    fontFamilyMono: '"Fira Code", Consolas, monospace'
  },
  Button: {
    borderRadiusMedium: '8px',
    fontWeight: '700'
  }
}

const navItems = [
  { key: 'overview', label: '概览', icon: AnalyticsOutline },
  { key: 'chat', label: '对话', icon: ChatbubbleEllipsesOutline },
  { key: 'network', label: '网络', icon: GlobeOutline },
  { key: 'test', label: '服务测试', icon: FlashOutline },
  { key: 'settings', label: '配置', icon: SettingsOutline },
  { key: 'logs', label: '日志', icon: TerminalOutline }
]

const endpointOptions = [
  { label: 'OpenAI Chat Completions', value: 'chat' },
  { label: 'OpenAI Responses', value: 'responses' },
  { label: 'Google generateContent', value: 'google' },
  { label: 'Google streamGenerateContent', value: 'google-stream' }
]

const active = ref('overview')
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const networkLoading = ref(false)
const autoLogs = ref(true)
const stickToBottom = ref(true)
const logBox = ref(null)
const logTimer = ref(null)
const apiKeysText = ref('')
const apiKeyItems = ref([])
const apiKeyDraft = ref('')
const editingApiKeyIndex = ref(null)
const cookieItems = ref([])
const cookieDraft = ref('')
const editingCookieIndex = ref(null)
const showCookieRaw = ref({})

const auth = reactive({
  checked: false,
  authenticated: false,
  password: '',
  loggingIn: false
})

const status = reactive({
  ok: false,
  version: '',
  models: [],
  config: {},
  urls: {},
  logs: {},
  admin_static: {}
})

const config = reactive({
  cookie_file: '',
  cookie_files: [],
  cookie_content: '',
  cookie_contents: [],
  cookie_source: {},
  proxy: '',
  gemini_base_url: '',
  auth_user: null,
  xsrf_token: '',
  default_model: '',
  public_base_url: '',
  empty_response_fallback: '',
  api_keys: [],
  force_non_stream: false,
  temporary_chats: false,
  admin_password: '',
  gemini_bl: ''
})

const network = reactive({
  local_ip: '',
  public_ip: '',
  city: '',
  region: '',
  country: '',
  org: '',
  timezone: '',
  proxy_enabled: false,
  connectivity: {},
  raw_error: ''
})

const test = reactive({
  endpoint: 'chat',
  model: 'gemini-3.6-flash',
  stream: false,
  prompt: '你好，请用一句话说明当前服务是否可用。',
  result: ''
})

const chat = reactive({
  model: 'gemini-3.6-flash',
  stream: false,
  input: '',
  systemPrompt: '',
  messages: [],
  sending: false
})

const CHAT_STORAGE_KEY = 'gemini_web2api_chat'

function saveChatToStorage() {
  try {
    const data = { model: chat.model, stream: chat.stream, systemPrompt: chat.systemPrompt, messages: chat.messages }
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(data))
  } catch (_) {}
}

function loadChatFromStorage() {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (data.messages) chat.messages = data.messages
    if (data.model) chat.model = data.model
    if (data.stream !== undefined) chat.stream = data.stream
    if (data.systemPrompt) chat.systemPrompt = data.systemPrompt
  } catch (_) {}
}

const logs = reactive({
  text: '',
  offset: null,
  size: 0,
  path: '',
  exists: false,
  candidates: []
})
const logFilter = ref('')

const urlLabels = {
  local: '本地地址',
  lan: '局域网',
  current: '当前地址',
  public: '公网地址',
  admin: '管理台'
}

const urlOrder = ['current', 'local', 'lan', 'public', 'admin']

const sortedUrls = computed(() => {
  const urls = status.urls || {}
  return urlOrder
    .filter((k) => urls[k])
    .map((k) => ({ key: k, label: urlLabels[k] || k, value: urls[k] }))
})

const envItems = computed(() => [
  { icon: ShieldCheckmarkOutline, label: 'Cookie', value: cookieState, type: config.cookie_file ? 'success' : 'default' },
  { icon: GlobeOutline, label: '代理', value: proxyState, type: config.proxy ? 'info' : 'default' },
  { icon: KeyOutline, label: 'API 密钥', value: apiKeyItems.length ? '已启用' : '未启用', type: apiKeyItems.length ? 'success' : 'warning' },
  { icon: FlashOutline, label: '流式模式', value: config.force_non_stream ? '强制非流式' : '正常流式', type: config.force_non_stream ? 'warning' : 'success' },
  { icon: TerminalOutline, label: 'CLI 兼容', value: '/v1beta 已启用', type: 'success' },
  { icon: SettingsOutline, label: '鉴权模式', value: apiKeyItems.length ? '密钥鉴权' : '无鉴权', type: apiKeyItems.length ? 'info' : 'warning' }
])

const pageMeta = computed(() => ({
  overview: ['概览', '查看服务状态、调用地址和运行环境'],
  chat: ['对话', '选择模型并直接和当前服务对话'],
  network: ['网络', '查看公网 IP、所在地区并测试连通性'],
  test: ['服务测试', '发起一次兼容 OpenAI 或 Gemini 的调用'],
  settings: ['配置', '调整 Cookie、代理、密钥、管理员密码和公开地址'],
  logs: ['日志', '实时查看服务与桌面管理器输出']
}[active.value]))

const modelOptions = computed(() => [
  { label: '全部模型（使用默认模型）', value: '__all__' },
  ...status.models.map((item) => ({
    label: `${item.id} - ${item.description || 'model'}`,
    value: item.id
  }))
])

const currentEndpoint = computed(() => endpointOptions.find((item) => item.value === test.endpoint))
const healthyType = computed(() => status.ok ? 'success' : 'error')
const cookieState = computed(() => config.cookie_file ? '已配置' : '匿名模式')
const proxyState = computed(() => config.proxy ? config.proxy : '系统环境')
const locationText = computed(() => [network.country, network.region, network.city].filter(Boolean).join(' / ') || '未获取')
const logMetaText = computed(() => {
  if (!logs.path) return '日志路径：未获取'
  const size = Number.isFinite(logs.size) ? logs.size : 0
  return `日志路径：${logs.path} · ${logs.exists ? `${size} bytes` : '文件不存在'}`
})

const filteredLogText = computed(() => {
  if (!logFilter.value.trim()) return logs.text
  const keyword = logFilter.value.trim().toLowerCase()
  const lines = logs.text.split('\n')
  const filtered = lines.filter((line) => line.toLowerCase().includes(keyword))
  return filtered.join('\n')
})

function selectedModel(value) {
  return value && value !== '__all__' ? value : (config.default_model || status.models[0]?.id || 'gemini-3.6-flash')
}

const curlCommand = computed(() => {
  const model = selectedModel(test.model)
  const prompt = test.prompt.replace(/"/g, '\\"')
  if (test.endpoint === 'responses') {
    return `curl ${status.urls.current || '/v1'}/responses -H "Content-Type: application/json" -d "{\\"model\\":\\"${model}\\",\\"input\\":\\"${prompt}\\"}"`
  }
  if (test.endpoint.startsWith('google')) {
    const method = test.endpoint === 'google-stream' ? 'streamGenerateContent' : 'generateContent'
    return `curl ${window.location.origin}/v1beta/models/${model}:${method} -H "Content-Type: application/json" -d "{\\"contents\\":[{\\"role\\":\\"user\\",\\"parts\\":[{\\"text\\":\\"${prompt}\\"}]}]}"`
  }
  return `curl ${status.urls.current || '/v1'}/chat/completions -H "Content-Type: application/json" -d "{\\"model\\":\\"${model}\\",\\"messages\\":[{\\"role\\":\\"user\\",\\"content\\":\\"${prompt}\\"}],\\"stream\\":${test.stream}}"`
})

function renderMarkdown(text) {
  if (!text) return ''
  try {
    return marked.parse(text, { async: false })
  } catch {
    return text
  }
}

function pretty(data) {
  if (typeof data === 'string') {
    try { return JSON.stringify(JSON.parse(data), null, 2) } catch (_) { return data }
  }
  return JSON.stringify(data, null, 2)
}

async function api(path, options = {}) {
  const controller = new AbortController()
  if (options.timeout) {
    setTimeout(() => controller.abort(), options.timeout)
    options.signal = controller.signal
    delete options.timeout
  }
  const res = await fetch(path, options)
  const text = await res.text()
  let data = text
  try { data = text ? JSON.parse(text) : {} } catch (_) {}
  if (!res.ok) {
    if (res.status === 401 && path !== '/admin/api/login') auth.authenticated = false
    const reason = data?.error?.message || data?.error || res.statusText
    throw new Error(reason)
  }
  return data
}

function applyStatus(data) {
  status.ok = !!(data.ok && data.version)
  Object.assign(status, data)
  Object.assign(config, data.config || {})
  config.admin_password = ''
  apiKeyItems.value = [...(data.config?.api_keys || [])]
  apiKeysText.value = apiKeyItems.value.join('\n')
  const cookieContents = data.config?.cookie_contents || []
  cookieItems.value = (data.config?.cookie_files || []).map((path, index) => ({
    path,
    content: cookieContents[index] || '',
    label: `Cookie ${index + 1}`
  }))
  if (!test.model && status.models.length) test.model = status.models[0].id
}

function syncApiKeysText() {
  apiKeysText.value = apiKeyItems.value.join('\n')
}

function maskSecret(value) {
  if (!value) return '-'
  if (value.length <= 10) return `${value.slice(0, 3)}***${value.slice(-2)}`
  return `${value.slice(0, 7)}...${value.slice(-4)}`
}

function addApiKey() {
  const value = apiKeyDraft.value.trim()
  if (!value) return
  if (editingApiKeyIndex.value !== null) {
    apiKeyItems.value.splice(editingApiKeyIndex.value, 1, value)
    editingApiKeyIndex.value = null
  } else {
    apiKeyItems.value.push(value)
  }
  apiKeyDraft.value = ''
  syncApiKeysText()
}

function editApiKey(index) {
  editingApiKeyIndex.value = index
  apiKeyDraft.value = apiKeyItems.value[index]
}

function deleteApiKey(index) {
  apiKeyItems.value.splice(index, 1)
  if (editingApiKeyIndex.value === index) {
    editingApiKeyIndex.value = null
    apiKeyDraft.value = ''
  }
  syncApiKeysText()
}

function copyApiKey(index) {
  copyText(apiKeyItems.value[index], 'API 密钥已复制')
}

function addCookie() {
  const value = cookieDraft.value.trim()
  if (!value) return
  const row = { path: '', content: value, label: `Cookie ${editingCookieIndex.value === null ? cookieItems.value.length + 1 : editingCookieIndex.value + 1}` }
  if (editingCookieIndex.value !== null) {
    cookieItems.value.splice(editingCookieIndex.value, 1, row)
    editingCookieIndex.value = null
  } else {
    cookieItems.value.push(row)
  }
  cookieDraft.value = ''
  message.info('Cookie 已暂存，点击「保存配置」后生效')
}

function editCookie(index) {
  editingCookieIndex.value = index
  const item = cookieItems.value[index]
  cookieDraft.value = item.content || item.path || ''
}

function deleteCookie(index) {
  cookieItems.value.splice(index, 1)
  if (editingCookieIndex.value === index) {
    editingCookieIndex.value = null
    cookieDraft.value = ''
  }
}

function toggleShowCookie(index) {
  showCookieRaw.value[index] = !showCookieRaw.value[index]
}

async function checkAuth() {
  try {
    const data = await api('/admin/api/auth')
    auth.authenticated = !!data.authenticated
    if (auth.authenticated) await bootDashboard()
  } catch (_) {
    auth.authenticated = false
  } finally {
    auth.checked = true
  }
}

async function login() {
  if (!auth.password) {
    message.warning('请输入管理员密码')
    return
  }
  auth.loggingIn = true
  try {
    await api('/admin/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: auth.password })
    })
    auth.authenticated = true
    auth.password = ''
    await bootDashboard()
    message.success('登录成功')
  } catch (err) {
    message.error(`登录失败：${err.message}`)
  } finally {
    auth.loggingIn = false
  }
}

async function logout() {
  await api('/admin/api/logout', { method: 'POST' }).catch(() => {})
  auth.authenticated = false
  if (logTimer.value) clearInterval(logTimer.value)
  logTimer.value = null
}

async function bootDashboard() {
  await loadStatus()
  await readLogs(true)
  toggleLogTimer()
}

async function loadStatus(showToast = false) {
  loading.value = true
  try {
    const data = await api('/admin/api/status')
    applyStatus(data)
    if (showToast) message.success('状态已刷新')
  } catch (err) {
    status.ok = false
    message.error(`状态读取失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

async function loadNetwork(showToast = false) {
  networkLoading.value = true
  try {
    Object.assign(network, await api('/admin/api/network'))
    if (showToast) message.success('网络信息已刷新')
  } catch (err) {
    message.error(`网络检测失败：${err.message}`)
  } finally {
    networkLoading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    syncApiKeysText()
    // cookie_items 全量快照协议：有 content 的项写入磁盘（复用已有路径或新建），
    // 仅 path 的项保留原文件，不在列表中的项视为删除。
    const payload = {
      ...config,
      api_keys: [...apiKeyItems.value],
      cookie_items: cookieItems.value.map((item) => ({ path: item.path || null, content: item.content || null })),
      cookie_content: ''
    }
    const data = await api('/admin/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    Object.assign(config, data.config || {})
    config.admin_password = ''
    apiKeyItems.value = [...(data.config?.api_keys || [])]
    apiKeysText.value = apiKeyItems.value.join('\n')
    const cookieContents = data.config?.cookie_contents || []
    cookieItems.value = (data.config?.cookie_files || []).map((path, index) => ({
      path,
      content: cookieContents[index] || '',
      label: `Cookie ${index + 1}`
    }))
    await loadStatus()
    const cookieFiles = (data.config?.cookie_source?.files || []).filter((f) => f.exists)
    message.success(cookieFiles.length ? `配置已保存（${cookieFiles.length} 个 Cookie 已落盘）` : '配置已保存')
  } catch (err) {
    message.error(`保存失败：${err.message}`)
  } finally {
    saving.value = false
  }
}

function requestForTest() {
  const model = selectedModel(test.model)
  if (test.endpoint === 'responses') {
    return ['/v1/responses', { model, input: test.prompt, stream: false }]
  }
  if (test.endpoint === 'google' || test.endpoint === 'google-stream') {
    const method = test.endpoint === 'google-stream' ? 'streamGenerateContent' : 'generateContent'
    return [`/v1beta/models/${encodeURIComponent(model)}:${method}`, {
      contents: [{ role: 'user', parts: [{ text: test.prompt }] }]
    }]
  }
  return ['/v1/chat/completions', {
    model,
    messages: [{ role: 'user', content: test.prompt }],
    stream: test.stream
  }]
}

const callGuide = computed(() => {
  const base = status.urls.current || '/v1'
  const model = selectedModel(test.model)
  const key = apiKeysText.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean)[0] || 'sk-your-key'
  return [
    `Base URL: ${base}`,
    `API Key: ${apiKeysText.value ? key : '未启用密钥时可任意填写'}`,
    `Chat: POST ${base}/chat/completions`,
    `Responses: POST ${base}/responses`,
    `模型: ${model}`,
    '流式: 按请求 stream 参数控制'
  ].join('\n')
})

function parseChatResponse(text, streamed = false) {
  if (!streamed) {
    try {
      const data = JSON.parse(text)
      return data?.choices?.[0]?.message?.content || data?.choices?.[0]?.delta?.content || text
    } catch {
      return text
    }
  }
  let answer = ''
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed.startsWith('data:')) continue
    const payload = trimmed.slice(5).trim()
    if (!payload || payload === '[DONE]') continue
    try {
      const data = JSON.parse(payload)
      answer += data?.choices?.[0]?.delta?.content || data?.choices?.[0]?.message?.content || ''
    } catch (_) {}
  }
  return answer
}

async function runTest() {
  testing.value = true
  test.result = '请求中...'
  try {
    const [path, body] = requestForTest()
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const text = await res.text()
    if (!res.ok) throw new Error(pretty(text))
    test.result = pretty(text)
  } catch (err) {
    test.result = `请求失败\n${err.message}`
    message.error('测试失败')
  } finally {
    testing.value = false
  }
}

async function sendChat() {
  const content = chat.input.trim()
  if (!content) {
    message.warning('请输入对话内容')
    return
  }
  if (chat.sending) return
  const model = selectedModel(chat.model)
  const apiMessages = []
  if (chat.systemPrompt.trim()) apiMessages.push({ role: 'system', content: chat.systemPrompt.trim() })
  apiMessages.push(...chat.messages, { role: 'user', content })
  chat.messages = [...chat.messages, { role: 'user', content }]
  chat.input = ''
  chat.sending = true
  try {
    const streamed = chat.stream
    const res = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, messages: apiMessages, stream: streamed })
    })
    const text = await res.text()
    if (!res.ok) throw new Error(pretty(text))
    const answer = parseChatResponse(text, streamed)
    chat.messages.push({ role: 'assistant', content: answer || config.empty_response_fallback || '（空响应）' })
  } catch (err) {
    chat.messages.push({ role: 'assistant', content: `**调用失败：** ${err.message}` })
  } finally {
    chat.sending = false
  }
}

async function readLogs(reset = false) {
  if (!auth.authenticated) return
  try {
    const query = reset || logs.offset === null ? '?tail=60000' : `?offset=${logs.offset}`
    const data = await api(`/admin/api/logs${query}`)
    logs.offset = data.offset
    logs.size = data.size
    logs.path = data.path || ''
    logs.exists = !!data.exists
    logs.candidates = data.candidates || []
    if (reset) {
      logs.text = data.content
    } else {
      logs.text = logs.text + data.content
    }
    if (!data.exists && reset) {
      logs.text = data.error ? `日志暂不可用：${data.error}` : '暂无日志文件，服务产生输出后会显示在这里。'
    } else if (!data.content && !reset) {
      logs.text = logs.text || '暂无日志内容'
    }
    if (stickToBottom.value) await scrollLogs()
  } catch (err) {
    if (reset) logs.text = `日志读取失败：${err.message}`
    message.warning(`日志读取失败：${err.message}`)
  }
}

async function scrollLogs() {
  await nextTick()
  if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
}

function toggleLogTimer() {
  if (logTimer.value) clearInterval(logTimer.value)
  if (autoLogs.value && auth.authenticated) {
    logTimer.value = setInterval(() => readLogs(false), 1800)
  } else {
    logTimer.value = null
  }
}

async function copyText(text, label = '已复制') {
  try {
    await navigator.clipboard.writeText(text || '')
    message.success(label)
  } catch {
    message.warning('复制失败，请手动复制')
  }
}

function exportChatMarkdown() {
  const lines = chat.messages.map((m) => {
    const role = m.role === 'user' ? '**你**' : '**助手**'
    return `### ${role}\n\n${m.content}`
  })
  if (chat.systemPrompt) lines.unshift(`### System\n\n${chat.systemPrompt}`)
  return lines.join('\n\n---\n\n')
}

watch(() => chat.messages.length, () => saveChatToStorage())
watch(() => chat.model, () => saveChatToStorage())
watch(() => chat.systemPrompt, () => saveChatToStorage())

function openUrl(url) {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

watch(autoLogs, toggleLogTimer)
watch(active, (value) => {
  if (value === 'network' && !network.public_ip && !networkLoading.value) loadNetwork()
  if (value === 'logs') readLogs(true)
})

onMounted(() => {
  loadTheme()
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (theme.value === 'auto') applyTheme()
    })
  }
  checkAuth()
  loadChatFromStorage()
})

onBeforeUnmount(() => {
  if (logTimer.value) clearInterval(logTimer.value)
})
</script>

<template>
  <NConfigProvider :theme="isDark ? darkTheme : lightTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div v-if="!auth.checked" class="login-screen">
        <NSpin size="large" />
      </div>

      <div v-else-if="!auth.authenticated" class="login-screen">
        <section class="login-card">
          <div class="login-mark"><NIcon :component="ShieldCheckmarkOutline" /></div>
          <h1>GeminiWeb2API</h1>
          <p>登录管理台后可查看状态、修改配置、测试接口和读取日志。</p>
          <NForm label-placement="top" @submit.prevent="login">
            <NFormItem label="管理员密码">
              <NInput v-model:value="auth.password" type="password" show-password-on="click" placeholder="默认 sk-admin" @keyup.enter="login" />
            </NFormItem>
          </NForm>
          <NButton type="primary" block size="large" :loading="auth.loggingIn" @click="login">登录</NButton>
          <div class="login-note">首次登录默认密码为 sk-admin，登录后可在配置页修改。</div>
        </section>
      </div>

      <div v-else class="app-shell">
        <aside class="sidebar">
          <div class="brand">
            <div class="brand-mark">GW</div>
            <div>
              <div class="brand-title">GeminiWeb2API</div>
              <div class="brand-sub">Admin Console</div>
            </div>
          </div>
          <nav class="nav-list">
            <button v-for="item in navItems" :key="item.key" class="nav-button" :class="{ active: active === item.key }" @click="active = item.key">
              <NIcon size="18" :component="item.icon" />
              <span>{{ item.label }}</span>
              <span v-if="item.key === 'overview' && !status.ok" class="nav-badge nav-badge-error"></span>
            </button>
          </nav>
        </aside>

        <main class="main">
          <header class="topbar">
            <div>
              <h1 class="page-title">{{ pageMeta[0] }}</h1>
              <div class="page-desc">{{ pageMeta[1] }}</div>
            </div>
            <div class="top-actions">
              <NDropdown trigger="click" :options="themeOptions" @select="setTheme">
                <NButton tertiary size="small">
                  <template #icon><NIcon :component="isDark ? MoonOutline : SunnyOutline" /></template>{{ isDark ? '暗色' : '亮色' }}
                </NButton>
              </NDropdown>
              <NTag :type="healthyType" round>{{ status.ok ? '服务正常' : '服务异常' }}</NTag>
              <NButton secondary size="small" @click="copyText(status.urls?.current || '', 'Base URL 已复制')">
                <template #icon><NIcon :component="LinkOutline" /></template>复制 URL
              </NButton>
              <NButton secondary size="small" :loading="loading" @click="loadStatus(true)">
                <template #icon><NIcon :component="RefreshOutline" /></template>
              </NButton>
              <NButton tertiary size="small" @click="active = 'chat'">
                <template #icon><NIcon :component="ChatbubbleEllipsesOutline" /></template>对话
              </NButton>
              <NButton tertiary size="small" @click="logout">
                <template #icon><NIcon :component="LogOutOutline" /></template>退出
              </NButton>
            </div>
          </header>

          <NSpin :show="loading && !status.version">
            <!-- ═══ 概览 ═══ -->
            <section v-show="active === 'overview'" class="content-grid">
              <!-- 健康状态主卡 -->
              <div class="panel span-12 hero-card" :class="status.ok ? 'hero-ok' : 'hero-error'">
                <div class="hero-left">
                  <div class="hero-icon-wrap" :class="status.ok ? 'hero-icon-ok' : 'hero-icon-error'">
                    <NIcon :component="status.ok ? CheckmarkCircleOutline : AlertCircleOutline" :size="36" />
                  </div>
                  <div>
                    <div class="hero-status">{{ status.ok ? '服务正常运行' : '服务异常' }}</div>
                    <div class="hero-sub">v{{ status.version || '-' }} · {{ config.default_model || '-' }}</div>
                  </div>
                </div>
                <div class="hero-right">
                  <div class="hero-stat">
                    <div class="hero-stat-value">{{ status.models.length }}</div>
                    <div class="hero-stat-label">模型</div>
                  </div>
                  <div class="hero-stat">
                    <div class="hero-stat-value">{{ network.public_ip || '-' }}</div>
                    <div class="hero-stat-label">公网 IP</div>
                  </div>
                  <div class="hero-stat">
                    <div class="hero-stat-value">{{ cookieState === '已配置' ? '✓' : '—' }}</div>
                    <div class="hero-stat-label">Cookie</div>
                  </div>
                </div>
              </div>

              <!-- 快捷操作 -->
              <div class="panel span-12 quick-actions">
                <NButton type="primary" @click="active = 'chat'"><template #icon><NIcon :component="ChatbubbleEllipsesOutline" /></template>对话</NButton>
                <NButton secondary @click="active = 'test'"><template #icon><NIcon :component="FlashOutline" /></template>服务测试</NButton>
                <NButton secondary @click="copyText(status.urls?.current || '', 'Base URL 已复制')"><template #icon><NIcon :component="CopyOutline" /></template>复制 Base URL</NButton>
                <NButton secondary @click="active = 'logs'"><template #icon><NIcon :component="TerminalOutline" /></template>查看日志</NButton>
                <NButton secondary @click="active = 'network'"><template #icon><NIcon :component="GlobeOutline" /></template>网络检测</NButton>
              </div>

              <!-- 调用地址 -->
              <div class="panel span-8">
                <div class="panel-head">
                  <h2 class="panel-title">调用地址</h2>
                  <NButton text type="primary" @click="copyText(JSON.stringify(status.urls, null, 2))">
                    <template #icon><NIcon :component="CopyOutline" /></template>复制全部
                  </NButton>
                </div>
                <div class="url-list">
                  <div v-for="item in sortedUrls" :key="item.key" class="url-row">
                    <div class="url-label">{{ item.label }}</div>
                    <div class="url-value">{{ item.value }}</div>
                    <NButton size="small" secondary @click="openUrl(item.value)">
                      <template #icon><NIcon :component="OpenOutline" /></template>
                    </NButton>
                    <NButton size="small" secondary @click="copyText(item.value)">
                      <template #icon><NIcon :component="CopyOutline" /></template>
                    </NButton>
                  </div>
                </div>
              </div>

              <!-- 运行环境卡片 -->
              <div class="panel span-4">
                <h2 class="panel-title">运行环境</h2>
                <div class="env-grid">
                  <div v-for="item in envItems" :key="item.label" class="env-card">
                    <NIcon :component="item.icon" :size="18" class="env-icon" />
                    <div class="env-info">
                      <div class="env-label">{{ item.label }}</div>
                      <div class="env-value" :class="`env-${item.type}`">{{ item.value }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 模型列表 -->
              <div class="panel span-12">
                <div class="panel-head">
                  <h2 class="panel-title">可用模型</h2>
                  <NTag type="info" round>{{ status.models.length }} 个</NTag>
                </div>
                <div class="model-grid">
                  <div v-for="m in status.models" :key="m.id" class="model-card" @click="test.model = m.id; active = 'test'">
                    <div class="model-name">{{ m.id }}</div>
                    <div class="model-desc">{{ m.description }}</div>
                  </div>
                </div>
              </div>
            </section>

            <!-- ═══ 对话 ═══ -->
            <section v-show="active === 'chat'" class="content-grid chat-section">
              <div class="panel span-8 chat-panel">
                <div class="panel-head">
                  <h2 class="panel-title">对话</h2>
                  <NSpace align="center" wrap>
                    <NTag type="info" round>{{ chat.stream ? '流式' : '非流式' }}</NTag>
                    <NButton secondary size="small" @click="chat.messages = []; chat.systemPrompt = ''; saveChatToStorage()">
                      <template #icon><NIcon :component="TrashOutline" /></template>清空
                    </NButton>
                  </NSpace>
                </div>
                <div class="chat-list">
                  <div v-if="!chat.messages.length" class="chat-empty">选择模型后输入内容，即可用当前服务发起对话。</div>
                  <div v-for="(item, index) in chat.messages" :key="index" class="chat-message" :class="item.role">
                    <div class="chat-role">{{ item.role === 'user' ? '你' : '助手' }}</div>
                    <div class="chat-bubble" v-html="item.role === 'user' ? item.content : renderMarkdown(item.content)"></div>
                    <div v-if="item.role === 'assistant'" class="chat-actions">
                      <NButton text size="tiny" @click="copyText(item.content, '消息已复制')">
                        <template #icon><NIcon :component="CopyOutline" /></template>
                      </NButton>
                    </div>
                  </div>
                  <div v-if="chat.sending" class="chat-message assistant">
                    <div class="chat-role">助手</div>
                    <div class="chat-bubble thinking-dots"><span></span><span></span><span></span></div>
                  </div>
                </div>
                <NForm label-placement="top">
                  <div class="form-grid">
                    <NFormItem label="System Prompt" class="full">
                      <NInput v-model:value="chat.systemPrompt" type="textarea" placeholder="可选：系统提示词，会影响模型行为" :autosize="{ minRows: 2, maxRows: 4 }" />
                    </NFormItem>
                    <NFormItem label="模型">
                      <NSelect v-model:value="chat.model" :options="modelOptions" filterable tag />
                    </NFormItem>
                    <NFormItem label="流式输出">
                      <NSwitch v-model:value="chat.stream" />
                    </NFormItem>
                    <NFormItem label="内容" class="full">
                      <NInput v-model:value="chat.input" type="textarea" placeholder="输入对话内容（Ctrl+Enter 发送）" :autosize="{ minRows: 4, maxRows: 10 }" @keydown.ctrl.enter.prevent="sendChat" />
                    </NFormItem>
                  </div>
                </NForm>
                <div class="button-row">
                  <NButton type="primary" :loading="chat.sending" @click="sendChat">
                    <template #icon><NIcon :component="PlayOutline" /></template>发送
                  </NButton>
                  <NButton secondary @click="copyText(JSON.stringify(chat.messages, null, 2), '对话已复制')">
                    <template #icon><NIcon :component="CopyOutline" /></template>复制 JSON
                  </NButton>
                  <NButton secondary @click="copyText(exportChatMarkdown(), 'Markdown 已复制')">
                    <template #icon><NIcon :component="DocumentTextOutline" /></template>导出 MD
                  </NButton>
                </div>
              </div>
              <div class="panel span-4">
                <h2 class="panel-title">调用说明</h2>
                <pre class="code-box compact-code">{{ callGuide }}</pre>
              </div>
            </section>

            <!-- ═══ 网络 ═══ -->
            <section v-show="active === 'network'" class="content-grid">
              <div class="panel span-12">
                <div class="panel-head">
                  <h2 class="panel-title">网络信息</h2>
                  <NButton type="primary" :loading="networkLoading" @click="loadNetwork(true)">
                    <template #icon><NIcon :component="RefreshOutline" /></template>重新检测
                  </NButton>
                </div>
                <div class="network-grid">
                  <div class="network-item"><span>本机局域网 IP</span><strong>{{ network.local_ip || '-' }}</strong></div>
                  <div class="network-item"><span>公网 IP</span><strong>{{ network.public_ip || '-' }}</strong></div>
                  <div class="network-item"><span>所在地区</span><strong>{{ locationText }}</strong></div>
                  <div class="network-item"><span>运营商 / ASN</span><strong>{{ network.org || '-' }}</strong></div>
                  <div class="network-item"><span>时区</span><strong>{{ network.timezone || '-' }}</strong></div>
                  <div class="network-item"><span>代理</span><strong>{{ network.proxy_enabled ? '已启用' : '未启用' }}</strong></div>
                </div>
              </div>
              <div class="panel span-6">
                <div class="panel-head">
                  <h2 class="panel-title">Gemini 连通性</h2>
                  <NTag v-if="network.connectivity?.gemini" :type="network.connectivity.gemini.ok ? 'success' : 'error'" round>
                    {{ network.connectivity.gemini.ok ? '连通' : '不可达' }}
                    <template v-if="network.connectivity.gemini.latency_ms"> · {{ network.connectivity.gemini.latency_ms }}ms</template>
                  </NTag>
                </div>
                <pre class="code-box compact-code">{{ pretty(network.connectivity?.gemini || {}) }}</pre>
              </div>
              <div class="panel span-6">
                <div class="panel-head">
                  <h2 class="panel-title">Google 连通性</h2>
                  <NTag v-if="network.connectivity?.google" :type="network.connectivity.google.ok ? 'success' : 'error'" round>
                    {{ network.connectivity.google.ok ? '连通' : '不可达' }}
                    <template v-if="network.connectivity.google.latency_ms"> · {{ network.connectivity.google.latency_ms }}ms</template>
                  </NTag>
                </div>
                <pre class="code-box compact-code">{{ pretty(network.connectivity?.google || {}) }}</pre>
              </div>
            </section>

            <!-- ═══ 服务测试 ═══ -->
            <section v-show="active === 'test'" class="content-grid">
              <div class="panel span-6">
                <h2 class="panel-title">请求</h2>
                <NForm label-placement="top">
                  <div class="form-grid">
                    <NFormItem label="接口"><NSelect v-model:value="test.endpoint" :options="endpointOptions" /></NFormItem>
                    <NFormItem label="模型"><NSelect v-model:value="test.model" :options="modelOptions" filterable tag /></NFormItem>
                    <NFormItem label="流式输出"><NSwitch v-model:value="test.stream" :disabled="test.endpoint !== 'chat'" /></NFormItem>
                    <NFormItem label="调用方法"><NInput :value="currentEndpoint?.label || ''" readonly /></NFormItem>
                    <NFormItem label="Prompt" class="full"><NInput v-model:value="test.prompt" type="textarea" :autosize="{ minRows: 8, maxRows: 16 }" /></NFormItem>
                  </div>
                </NForm>
                <div class="button-row">
                  <NButton type="primary" :loading="testing" @click="runTest"><template #icon><NIcon :component="PlayOutline" /></template>运行测试</NButton>
                  <NButton secondary @click="copyText(curlCommand, 'curl 已复制')"><template #icon><NIcon :component="ClipboardOutline" /></template>复制 curl</NButton>
                  <NButton secondary @click="test.result = ''"><template #icon><NIcon :component="TrashOutline" /></template>清空</NButton>
                </div>
              </div>
              <div class="panel span-6">
                <h2 class="panel-title">响应</h2>
                <pre class="code-box result-box">{{ test.result || '等待测试结果' }}</pre>
              </div>
              <div class="panel span-12">
                <div class="panel-head">
                  <h2 class="panel-title">调用方法</h2>
                  <NButton text type="primary" @click="copyText(callGuide, '调用说明已复制')"><template #icon><NIcon :component="CopyOutline" /></template>复制说明</NButton>
                </div>
                <pre class="code-box compact-code">{{ callGuide }}</pre>
              </div>
            </section>

            <!-- ═══ 配置 ═══ -->
            <section v-show="active === 'settings'" class="content-grid">
              <div class="panel span-12 settings-panel">
                <h2 class="panel-title">配置</h2>
                <NForm label-placement="top">
                  <div class="form-grid settings-grid">
                    <NFormItem label="API 密钥" class="full">
                      <div class="secret-manager">
                        <div class="inline-editor">
                          <NInput v-model:value="apiKeyDraft" type="password" show-password-on="click" placeholder="输入 API 密钥" @keyup.enter="addApiKey" />
                          <NButton type="primary" @click="addApiKey">{{ editingApiKeyIndex === null ? '新增' : '保存' }}</NButton>
                        </div>
                        <table class="secret-table">
                          <thead><tr><th>序号</th><th>密钥</th><th>操作</th></tr></thead>
                          <tbody>
                            <tr v-if="!apiKeyItems.length"><td colspan="3" class="empty-cell">未启用密钥</td></tr>
                            <tr v-for="(item, index) in apiKeyItems" :key="`${item}-${index}`">
                              <td>{{ index + 1 }}</td>
                              <td class="secret-value">{{ editingApiKeyIndex === index ? item : maskSecret(item) }}</td>
                              <td>
                                <NSpace size="small" @click.stop>
                                  <NButton size="small" secondary @click="editApiKey(index)">修改</NButton>
                                  <NPopconfirm @positive-click="deleteApiKey(index)">
                                    <template #trigger><NButton size="small" tertiary type="error">删除</NButton></template>
                                    确认删除该密钥？
                                  </NPopconfirm>
                                </NSpace>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </NFormItem>
                    <NFormItem label="Cookie" class="full">
                      <div class="secret-manager">
                        <NInput v-model:value="cookieDraft" type="textarea" placeholder="粘贴完整 Cookie；可新增多条，默认第一条有效" :autosize="{ minRows: 2, maxRows: 5 }" />
                        <div class="button-row tight">
                          <NButton type="primary" @click="addCookie">{{ editingCookieIndex === null ? '新增 Cookie' : '保存修改' }}</NButton>
                          <NButton secondary @click="cookieDraft = ''; editingCookieIndex = null">取消</NButton>
                        </div>
                        <table class="secret-table">
                          <thead><tr><th>序号</th><th>状态</th><th>操作</th></tr></thead>
                          <tbody>
                            <tr v-if="!cookieItems.length"><td colspan="3" class="empty-cell">未配置 Cookie</td></tr>
                            <tr v-for="(item, index) in cookieItems" :key="`${item.path}-${index}`">
                              <td>{{ index + 1 }}</td>
                              <td class="secret-value">
                                <span v-if="item.content">
                                  <template v-if="showCookieRaw[index]">{{ item.content }}</template>
                                  <template v-else>{{ maskSecret(item.content) }}</template>
                                </span>
                                <span v-else>{{ item.path || '待保存' }}</span>
                              </td>
                              <td>
                                <NSpace size="small">
                                  <NButton v-if="item.content" size="small" secondary @click="toggleShowCookie(index)">{{ showCookieRaw[index] ? '隐藏' : '显示' }}</NButton>
                                  <NButton size="small" secondary @click="editCookie(index)">{{ item.content ? '修改' : '替换' }}</NButton>
                                  <NPopconfirm @positive-click="deleteCookie(index)">
                                    <template #trigger><NButton size="small" tertiary type="error">删除</NButton></template>
                                    确认删除该 Cookie？
                                  </NPopconfirm>
                                </NSpace>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </NFormItem>
                    <NFormItem label="新管理员密码"><NInput v-model:value="config.admin_password" type="password" show-password-on="click" placeholder="留空表示不修改; 默认 sk-admin" /></NFormItem>
                    <NFormItem label="代理"><NInput v-model:value="config.proxy" placeholder="例如 http://127.0.0.1:7890 或 socks5://user:pass@host:port" /></NFormItem>
                    <NFormItem label="Gemini Base URL"><NInput v-model:value="config.gemini_base_url" placeholder="留空默认 https://gemini.google.com" /></NFormItem>
                    <NFormItem label="Google 账号序号"><NInputNumber v-model:value="config.auth_user" clearable placeholder="默认账号留空；第二账号填 1" /></NFormItem>
                    <NFormItem label="XSRF Token"><NInput v-model:value="config.xsrf_token" type="password" show-password-on="click" placeholder="可选：Gemini 请求参数 at" /></NFormItem>
                    <NFormItem label="Gemini BL"><NInput v-model:value="config.gemini_bl" placeholder="boq_assistant-bard-web-server_YYYYMMDD.00_p0" /></NFormItem>
                    <NFormItem label="强制非流式"><NSwitch v-model:value="config.force_non_stream" /></NFormItem>
                    <NFormItem label="临时对话"><NSwitch v-model:value="config.temporary_chats" /></NFormItem>
                    <NFormItem label="默认模型"><NSelect v-model:value="config.default_model" :options="modelOptions" filterable tag /></NFormItem>
                    <NFormItem label="公网 Base URL"><NInput v-model:value="config.public_base_url" placeholder="例如 https://your-project.vercel.app/v1" /></NFormItem>
                    <NFormItem label="空响应兜底文案"><NInput v-model:value="config.empty_response_fallback" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" /></NFormItem>
                  </div>
                </NForm>
                <div class="button-row">
                  <NButton type="primary" :loading="saving" @click="saveConfig"><template #icon><NIcon :component="SaveOutline" /></template>保存配置</NButton>
                  <NButton secondary @click="loadStatus(true)"><template #icon><NIcon :component="RefreshOutline" /></template>重新读取</NButton>
                </div>
              </div>
              <div class="panel span-12">
                <h2 class="panel-title">当前配置文件内容</h2>
                <pre class="code-box compact-code">{{ pretty({ ...config, cookie_content: '', cookie_contents: cookieItems.map((item) => item.content ? '（已设置，隐藏）' : item.path).filter(Boolean), admin_password: config.admin_password ? '待更新' : '', api_keys: apiKeyItems }) }}</pre>
              </div>
            </section>

            <!-- ═══ 日志 ═══ -->
            <section v-show="active === 'logs'" class="content-grid">
              <div class="panel span-12">
                <div class="panel-head">
                  <h2 class="panel-title">运行日志</h2>
                  <NSpace align="center" wrap>
                    <NInput v-model:value="logFilter" placeholder="搜索日志…" clearable size="small" style="width: 180px" />
                    <NCheckbox v-model:checked="stickToBottom">自动滚动</NCheckbox>
                    <NSwitch v-model:value="autoLogs" />
                    <NButton secondary size="small" @click="readLogs(true)">
                      <template #icon><NIcon :component="RefreshOutline" /></template>
                    </NButton>
                    <NButton secondary size="small" @click="copyText(logs.text, '日志已复制')">
                      <template #icon><NIcon :component="DocumentTextOutline" /></template>
                    </NButton>
                    <NButton secondary size="small" @click="logs.text = ''; logFilter = ''">
                      <template #icon><NIcon :component="TrashOutline" /></template>
                    </NButton>
                  </NSpace>
                </div>
                <div class="log-meta">{{ logMetaText }}{{ logFilter ? ` · 过滤：${logFilter}` : '' }}</div>
                <pre v-if="logs.text" ref="logBox" class="code-box log-box">{{ filteredLogText }}</pre>
                <NEmpty v-else description="暂无日志，服务产生输出后会显示在这里。" />
              </div>
            </section>
          </NSpin>
        </main>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>
