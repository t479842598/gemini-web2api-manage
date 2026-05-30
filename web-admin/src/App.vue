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
  OpenOutline,
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
  cookie_content: '',
  cookie_source: {},
  proxy: '',
  default_model: '',
  public_base_url: '',
  empty_response_fallback: '',
  api_keys: [],
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

const logs = reactive({
  text: '',
  offset: null,
  size: 0
})

const pageMeta = computed(() => ({
  overview: ['概览', '查看服务状态、调用地址和运行环境'],
  network: ['网络', '查看公网 IP、所在地区并测试连通性'],
  test: ['服务测试', '发起一次兼容 OpenAI 或 Gemini 的调用'],
  settings: ['配置', '调整 Cookie、代理、密钥、管理员密码和公开地址'],
  logs: ['日志', '实时查看服务与桌面管理器输出']
}[active.value]))

const modelOptions = computed(() => status.models.map((item) => ({
  label: `${item.id} - ${item.description || 'model'}`,
  value: item.id
})))

const currentEndpoint = computed(() => endpointOptions.find((item) => item.value === test.endpoint))
const healthyType = computed(() => status.ok ? 'success' : 'error')
const cookieState = computed(() => config.cookie_file ? '已配置' : '匿名模式')
const proxyState = computed(() => config.proxy ? config.proxy : '系统环境')
const locationText = computed(() => [network.country, network.region, network.city].filter(Boolean).join(' / ') || '未获取')

const curlCommand = computed(() => {
  const model = test.model || 'gemini-3.5-flash'
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
  apiKeysText.value = (data.config?.api_keys || []).join('\n')
  if (!test.model && status.models.length) test.model = status.models[0].id
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
    const apiKeys = apiKeysText.value.replace(/,/g, '\n').split('\n').map((item) => item.trim()).filter(Boolean)
    const payload = { ...config, api_keys: apiKeys }
    const data = await api('/admin/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    Object.assign(config, data.config || {})
    config.admin_password = ''
    apiKeysText.value = (data.config?.api_keys || []).join('\n')
    await loadStatus()
    message.success('配置已保存')
  } catch (err) {
    message.error(`保存失败：${err.message}`)
  } finally {
    saving.value = false
  }
}

function requestForTest() {
  const model = test.model || config.default_model || 'gemini-3.5-flash'
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
              <NButton secondary @click="openUrl(status.urls.admin)"><template #icon><NIcon :component="OpenOutline" /></template>Web</NButton>
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
            </section>

            <section v-show="active === 'settings'" class="content-grid">
              <div class="panel span-12 settings-panel">
                <h2 class="panel-title">配置</h2>
                <NForm label-placement="top">
                  <div class="form-grid settings-grid">
                    <NFormItem label="API 密钥" class="full"><NInput v-model:value="apiKeysText" type="textarea" placeholder="每行一个, 或用英文逗号分隔; 留空表示不校验" :autosize="{ minRows: 2, maxRows: 5 }" /></NFormItem>
                    <NFormItem label="Cookie 内容" class="full"><NInput v-model:value="config.cookie_content" type="textarea" placeholder="粘贴 SID=...; HSID=...; __Secure-1PSID=...，留空表示不修改当前 Cookie" :autosize="{ minRows: 3, maxRows: 7 }" /></NFormItem>
                    <NFormItem label="Cookie 文件路径"><NInput v-model:value="config.cookie_file" placeholder="留空则保存到项目 cookie.txt；Vercel 建议用 GEMINI_COOKIE 环境变量" /></NFormItem>
                    <NFormItem label="新管理员密码"><NInput v-model:value="config.admin_password" type="password" show-password-on="click" placeholder="留空表示不修改; 默认 sk-admin" /></NFormItem>
                    <NFormItem label="代理"><NInput v-model:value="config.proxy" placeholder="例如 http://127.0.0.1:7890" /></NFormItem>
                    <NFormItem label="默认模型"><NSelect v-model:value="config.default_model" :options="modelOptions" filterable tag /></NFormItem>
                    <NFormItem label="公网 Base URL"><NInput v-model:value="config.public_base_url" placeholder="例如 https://your-project.vercel.app/v1" /></NFormItem>
                    <NFormItem label="空响应兜底文案"><NInput v-model:value="config.empty_response_fallback" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" /></NFormItem>
                  </div>
                </NForm>
                <div class="button-row"><NButton type="primary" :loading="saving" @click="saveConfig"><template #icon><NIcon :component="SaveOutline" /></template>保存配置</NButton><NButton secondary @click="loadStatus(true)"><template #icon><NIcon :component="RefreshOutline" /></template>重新读取</NButton></div>
              </div>
              <div class="panel span-12"><h2 class="panel-title">当前配置</h2><pre class="code-box compact-code">{{ pretty({ ...config, cookie_content: config.cookie_content ? '待更新' : '', admin_password: config.admin_password ? '待更新' : '', api_keys: apiKeysText ? apiKeysText.split('\n').filter(Boolean) : [] }) }}</pre></div>
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
