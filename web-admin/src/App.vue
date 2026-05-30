<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  NButton,
  NCheckbox,
  NConfigProvider,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NMessageProvider,
  NSelect,
  NSpace,
  NSpin,
  NStatistic,
  NSwitch,
  NTag,
  createDiscreteApi
} from 'naive-ui'
import {
  AnalyticsOutline,
  ClipboardOutline,
  CopyOutline,
  DocumentTextOutline,
  FlashOutline,
  GlobeOutline,
  LogOutOutline,
  ChatbubbleEllipsesOutline,
  PlayOutline,
  RefreshOutline,
  SaveOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  TerminalOutline,
  TrashOutline
} from '@vicons/ionicons5'

const { message } = createDiscreteApi(['message'])

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
  default_model: '',
  public_base_url: '',
  empty_response_fallback: '',
  api_keys: [],
  force_non_stream: false,
  admin_password: ''
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
  model: 'gemini-3.5-flash',
  stream: false,
  prompt: '你好，请用一句话说明当前服务是否可用。',
  result: ''
})

const chat = reactive({
  model: 'gemini-3.5-flash',
  stream: false,
  input: '',
  messages: []
})

const logs = reactive({
  text: '',
  offset: null,
  size: 0
})

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

function selectedModel(value) {
  return value && value !== '__all__' ? value : (config.default_model || status.models[0]?.id || 'gemini-3.5-flash')
}

const curlCommand = computed(() => {
  const model = selectedModel(test.model)
  const prompt = test.prompt.replace(/"/g, '\\"')
  if (test.endpoint === 'responses') {
    return `curl ${status.urls.current || '/v1'}/responses -H "Content-Type: application/json" -d "{\"model\":\"${model}\",\"input\":\"${prompt}\"}"`
  }
  if (test.endpoint.startsWith('google')) {
    const method = test.endpoint === 'google-stream' ? 'streamGenerateContent' : 'generateContent'
    return `curl ${window.location.origin}/v1beta/models/${model}:${method} -H "Content-Type: application/json" -d "{\"contents\":[{\"role\":\"user\",\"parts\":[{\"text\":\"${prompt}\"}]}]}"`
  }
  return `curl ${status.urls.current || '/v1'}/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"${model}\",\"messages\":[{\"role\":\"user\",\"content\":\"${prompt}\"}],\"stream\":${test.stream}}"`
})

function pretty(data) {
  if (typeof data === 'string') {
    try { return JSON.stringify(JSON.parse(data), null, 2) } catch (_) { return data }
  }
  return JSON.stringify(data, null, 2)
}

async function api(path, options = {}) {
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
  Object.assign(status, data)
  Object.assign(config, data.config || {})
  config.admin_password = ''
  apiKeyItems.value = [...(data.config?.api_keys || [])]
  apiKeysText.value = apiKeyItems.value.join('\n')
  cookieItems.value = (data.config?.cookie_files || []).map((path, index) => ({ path, content: '', label: `Cookie ${index + 1}` }))
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
}

function editCookie(index) {
  editingCookieIndex.value = index
  cookieDraft.value = cookieItems.value[index].content || ''
}

function deleteCookie(index) {
  cookieItems.value.splice(index, 1)
  if (editingCookieIndex.value === index) {
    editingCookieIndex.value = null
    cookieDraft.value = ''
  }
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
    applyStatus(await api('/admin/api/status'))
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
    const cookieContents = cookieItems.value.map((item) => item.content).filter(Boolean)
    const cookieFiles = cookieItems.value.filter((item) => !item.content && item.path).map((item) => item.path)
    const payload = {
      ...config,
      api_keys: [...apiKeyItems.value],
      cookie_files: cookieContents.length ? undefined : cookieFiles,
      cookie_contents: cookieContents.length ? cookieContents : undefined,
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
    cookieItems.value = (data.config?.cookie_files || []).map((path, index) => ({ path, content: '', label: `Cookie ${index + 1}` }))
    await loadStatus()
    message.success('配置已保存')
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
    stream: test.stream && !config.force_non_stream
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
    `流式: ${config.force_non_stream ? '全局已关闭，外部 stream=true 也会按非流式处理' : '按请求 stream 参数控制'}`
  ].join('\n')
})

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
  const model = selectedModel(chat.model)
  const messages = [...chat.messages, { role: 'user', content }]
  chat.messages = messages
  chat.input = ''
  testing.value = true
  try {
    const res = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, messages, stream: chat.stream && !config.force_non_stream })
    })
    const text = await res.text()
    if (!res.ok) throw new Error(pretty(text))
    const data = JSON.parse(text)
    const answer = data?.choices?.[0]?.message?.content || data?.choices?.[0]?.delta?.content || ''
    chat.messages.push({ role: 'assistant', content: answer || config.empty_response_fallback || '空响应' })
  } catch (err) {
    chat.messages.push({ role: 'assistant', content: `调用失败：${err.message}` })
  } finally {
    testing.value = false
  }
}

async function readLogs(reset = false) {
  if (!auth.authenticated) return
  try {
    const query = reset || logs.offset === null ? '?tail=60000' : `?offset=${logs.offset}`
    const data = await api(`/admin/api/logs${query}`)
    logs.offset = data.offset
    logs.size = data.size
    logs.text = reset ? data.content : logs.text + data.content
    if (!data.exists && reset) logs.text = data.error ? `日志暂不可用：${data.error}` : '暂无日志文件，服务产生输出后会显示在这里。'
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
  logTimer.value = autoLogs.value && auth.authenticated ? setInterval(() => readLogs(false), 1800) : null
}

async function copyText(text, label = '已复制') {
  await navigator.clipboard.writeText(text || '')
  message.success(label)
}

function openUrl(url) {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

watch(autoLogs, toggleLogTimer)
watch(active, (value) => {
  if (value === 'network' && !network.public_ip && !networkLoading.value) loadNetwork()
})

onMounted(checkAuth)

onBeforeUnmount(() => {
  if (logTimer.value) clearInterval(logTimer.value)
})
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides">
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
              <NTag :type="healthyType" round>{{ status.ok ? '服务正常' : '服务异常' }}</NTag>
              <NButton secondary :loading="loading" @click="loadStatus(true)"><template #icon><NIcon :component="RefreshOutline" /></template>刷新</NButton>
              <NButton type="primary" secondary @click="active = 'chat'"><template #icon><NIcon :component="ChatbubbleEllipsesOutline" /></template>对话</NButton>
              <NButton secondary @click="logout"><template #icon><NIcon :component="LogOutOutline" /></template>退出</NButton>
            </div>
          </header>

          <NSpin :show="loading && !status.version">
            <section v-show="active === 'overview'" class="content-grid">
              <div class="panel span-4 metric"><div class="metric-label">版本</div><div class="metric-value">{{ status.version || '-' }}</div><div class="metric-note">{{ status.admin_static?.ready ? '前端已构建' : '使用缺失提示页' }}</div></div>
              <div class="panel span-4 metric"><div class="metric-label">模型</div><div class="metric-value">{{ status.models.length }}</div><div class="metric-note">默认：{{ config.default_model || '-' }}</div></div>
              <div class="panel span-4 metric"><div class="metric-label">公网 IP</div><div class="metric-value small-value">{{ network.public_ip || '未获取' }}</div><div class="metric-note">{{ locationText }}</div></div>

              <div class="panel span-8">
                <div class="panel-head"><h2 class="panel-title">调用地址</h2><NButton text type="primary" @click="copyText(JSON.stringify(status.urls, null, 2))"><template #icon><NIcon :component="CopyOutline" /></template>复制全部</NButton></div>
                <div class="url-list">
                  <div v-for="(value, key) in status.urls" :key="key" class="url-row">
                    <div class="url-label">{{ key }}</div><div class="url-value">{{ value || '未配置' }}</div><NButton size="small" secondary @click="copyText(value)"><template #icon><NIcon :component="CopyOutline" /></template></NButton>
                  </div>
                </div>
              </div>

              <div class="panel span-4">
                <h2 class="panel-title">运行环境</h2>
                <NSpace vertical size="large">
                  <NStatistic label="Cookie" :value="cookieState" />
                  <NStatistic label="代理" :value="proxyState" />
                  <NStatistic label="API 密钥" :value="apiKeysText ? '已启用' : '未启用'" />
                  <NStatistic label="管理台目录" :value="status.admin_static?.ready ? 'ready' : 'missing'" />
                </NSpace>
              </div>
            </section>

            <section v-show="active === 'chat'" class="content-grid">
              <div class="panel span-8 chat-panel">
                <div class="panel-head"><h2 class="panel-title">对话</h2><NSpace align="center" wrap><NTag type="info" round>{{ config.force_non_stream ? '全局非流式' : (chat.stream ? '流式请求' : '非流式请求') }}</NTag><NButton secondary @click="chat.messages = []"><template #icon><NIcon :component="TrashOutline" /></template>清空</NButton></NSpace></div>
                <div class="chat-list">
                  <div v-if="!chat.messages.length" class="chat-empty">选择模型后输入内容，即可用当前服务发起对话。</div>
                  <div v-for="(item, index) in chat.messages" :key="index" class="chat-message" :class="item.role">
                    <div class="chat-role">{{ item.role === 'user' ? '你' : '助手' }}</div>
                    <div class="chat-bubble">{{ item.content }}</div>
                  </div>
                </div>
                <NForm label-placement="top"><div class="form-grid">
                  <NFormItem label="模型"><NSelect v-model:value="chat.model" :options="modelOptions" filterable tag /></NFormItem>
                  <NFormItem label="流式输出"><NSwitch v-model:value="chat.stream" :disabled="config.force_non_stream" /></NFormItem>
                  <NFormItem label="内容" class="full"><NInput v-model:value="chat.input" type="textarea" placeholder="输入对话内容" :autosize="{ minRows: 4, maxRows: 10 }" @keydown.ctrl.enter.prevent="sendChat" /></NFormItem>
                </div></NForm>
                <div class="button-row"><NButton type="primary" :loading="testing" @click="sendChat"><template #icon><NIcon :component="PlayOutline" /></template>发送</NButton><NButton secondary @click="copyText(JSON.stringify(chat.messages, null, 2), '对话已复制')"><template #icon><NIcon :component="CopyOutline" /></template>复制对话</NButton></div>
              </div>
              <div class="panel span-4">
                <h2 class="panel-title">调用说明</h2>
                <pre class="code-box compact-code">{{ callGuide }}</pre>
              </div>
            </section>

            <section v-show="active === 'network'" class="content-grid">
              <div class="panel span-12">
                <div class="panel-head"><h2 class="panel-title">网络信息</h2><NButton type="primary" :loading="networkLoading" @click="loadNetwork(true)"><template #icon><NIcon :component="RefreshOutline" /></template>获取公网 IP / 测试连通性</NButton></div>
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
                <h2 class="panel-title">Gemini 连通性</h2>
                <pre class="code-box compact-code">{{ pretty(network.connectivity?.gemini || {}) }}</pre>
              </div>
              <div class="panel span-6">
                <h2 class="panel-title">Google 连通性</h2>
                <pre class="code-box compact-code">{{ pretty(network.connectivity?.google || {}) }}</pre>
              </div>
            </section>

            <section v-show="active === 'test'" class="content-grid">
              <div class="panel span-6">
                <h2 class="panel-title">请求</h2>
                <NForm label-placement="top"><div class="form-grid">
                  <NFormItem label="接口"><NSelect v-model:value="test.endpoint" :options="endpointOptions" /></NFormItem>
                  <NFormItem label="模型"><NSelect v-model:value="test.model" :options="modelOptions" filterable tag /></NFormItem>
                  <NFormItem label="流式输出"><NSwitch v-model:value="test.stream" :disabled="test.endpoint !== 'chat'" /></NFormItem>
                  <NFormItem label="调用方法"><NInput :value="currentEndpoint?.label || ''" readonly /></NFormItem>
                  <NFormItem label="Prompt" class="full"><NInput v-model:value="test.prompt" type="textarea" :autosize="{ minRows: 8, maxRows: 16 }" /></NFormItem>
                </div></NForm>
                <div class="button-row"><NButton type="primary" :loading="testing" @click="runTest"><template #icon><NIcon :component="PlayOutline" /></template>运行测试</NButton><NButton secondary @click="copyText(curlCommand, 'curl 已复制')"><template #icon><NIcon :component="ClipboardOutline" /></template>复制 curl</NButton><NButton secondary @click="test.result = ''"><template #icon><NIcon :component="TrashOutline" /></template>清空</NButton></div>
              </div>
              <div class="panel span-6"><h2 class="panel-title">响应</h2><pre class="code-box result-box">{{ test.result || '等待测试结果' }}</pre></div>
              <div class="panel span-12"><div class="panel-head"><h2 class="panel-title">调用方法</h2><NButton text type="primary" @click="copyText(callGuide, '调用说明已复制')"><template #icon><NIcon :component="CopyOutline" /></template>复制说明</NButton></div><pre class="code-box compact-code">{{ callGuide }}</pre></div>
            </section>

            <section v-show="active === 'settings'" class="content-grid">
              <div class="panel span-12 settings-panel">
                <h2 class="panel-title">配置</h2>
                <NForm label-placement="top">
                  <div class="form-grid settings-grid">
                    <NFormItem label="API 密钥" class="full">
                      <div class="secret-manager">
                        <div class="inline-editor"><NInput v-model:value="apiKeyDraft" type="password" show-password-on="click" placeholder="输入 API 密钥" @keyup.enter="addApiKey" /><NButton type="primary" @click="addApiKey">{{ editingApiKeyIndex === null ? '新增' : '保存' }}</NButton></div>
                        <table class="secret-table"><thead><tr><th>序号</th><th>密钥</th><th>操作</th></tr></thead><tbody><tr v-if="!apiKeyItems.length"><td colspan="3" class="empty-cell">未启用密钥</td></tr><tr v-for="(item, index) in apiKeyItems" :key="`${item}-${index}`" @click="copyApiKey(index)"><td>{{ index + 1 }}</td><td class="secret-value">{{ editingApiKeyIndex === index ? item : maskSecret(item) }}</td><td><NSpace size="small" @click.stop><NButton size="small" secondary @click="editApiKey(index)">修改</NButton><NButton size="small" tertiary type="error" @click="deleteApiKey(index)">删除</NButton></NSpace></td></tr></tbody></table>
                      </div>
                    </NFormItem>
                    <NFormItem label="Cookie" class="full">
                      <div class="secret-manager">
                        <NInput v-model:value="cookieDraft" type="textarea" placeholder="粘贴完整 Cookie；可新增多条，默认第一条有效" :autosize="{ minRows: 2, maxRows: 5 }" />
                        <div class="button-row tight"><NButton type="primary" @click="addCookie">{{ editingCookieIndex === null ? '新增 Cookie' : '保存 Cookie' }}</NButton><NButton secondary @click="cookieDraft = ''; editingCookieIndex = null">取消</NButton></div>
                        <table class="secret-table"><thead><tr><th>序号</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-if="!cookieItems.length"><td colspan="3" class="empty-cell">未配置 Cookie</td></tr><tr v-for="(item, index) in cookieItems" :key="`${item.path}-${index}`"><td>{{ index + 1 }}</td><td class="secret-value">{{ item.content ? maskSecret(item.content) : (item.path || '待保存') }}</td><td><NSpace size="small"><NButton size="small" secondary @click="editCookie(index)">修改</NButton><NButton size="small" tertiary type="error" @click="deleteCookie(index)">删除</NButton></NSpace></td></tr></tbody></table>
                      </div>
                    </NFormItem>
                    <NFormItem label="新管理员密码"><NInput v-model:value="config.admin_password" type="password" show-password-on="click" placeholder="留空表示不修改; 默认 sk-admin" /></NFormItem>
                    <NFormItem label="代理"><NInput v-model:value="config.proxy" placeholder="例如 http://127.0.0.1:7890" /></NFormItem>
                    <NFormItem label="默认模型"><NSelect v-model:value="config.default_model" :options="modelOptions" filterable tag /></NFormItem>
                    <NFormItem label="强制非流式输出"><NSwitch v-model:value="config.force_non_stream" /></NFormItem>
                    <NFormItem label="公网 Base URL"><NInput v-model:value="config.public_base_url" placeholder="例如 https://your-project.vercel.app/v1" /></NFormItem>
                    <NFormItem label="空响应兜底文案"><NInput v-model:value="config.empty_response_fallback" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" /></NFormItem>
                  </div>
                </NForm>
                <div class="button-row"><NButton type="primary" :loading="saving" @click="saveConfig"><template #icon><NIcon :component="SaveOutline" /></template>保存配置</NButton><NButton secondary @click="loadStatus(true)"><template #icon><NIcon :component="RefreshOutline" /></template>重新读取</NButton></div>
              </div>
              <div class="panel span-12"><h2 class="panel-title">当前配置</h2><pre class="code-box compact-code">{{ pretty({ ...config, cookie_content: '', cookie_contents: cookieItems.map((item) => item.content ? '待更新' : item.path).filter(Boolean), admin_password: config.admin_password ? '待更新' : '', api_keys: apiKeyItems }) }}</pre></div>
            </section>

            <section v-show="active === 'logs'" class="content-grid">
              <div class="panel span-12">
                <div class="panel-head"><h2 class="panel-title">运行日志</h2><NSpace align="center" wrap><NCheckbox v-model:checked="stickToBottom">自动滚动</NCheckbox><NSwitch v-model:value="autoLogs" /><NButton secondary @click="readLogs(true)"><template #icon><NIcon :component="RefreshOutline" /></template>重新载入</NButton><NButton secondary @click="copyText(logs.text, '日志已复制')"><template #icon><NIcon :component="DocumentTextOutline" /></template>复制</NButton><NButton secondary @click="logs.text = ''"><template #icon><NIcon :component="TrashOutline" /></template>清空视图</NButton></NSpace></div>
                <pre v-if="logs.text" ref="logBox" class="code-box log-box">{{ logs.text }}</pre><NEmpty v-else description="暂无日志" />
              </div>
            </section>
          </NSpin>
        </main>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>
