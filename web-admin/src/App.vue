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
  OpenOutline,
  PlayOutline,
  RefreshOutline,
  SaveOutline,
  SettingsOutline,
  TerminalOutline,
  TrashOutline
} from '@vicons/ionicons5'

const { message } = createDiscreteApi(['message'])

const themeOverrides = {
  common: {
    primaryColor: '#2f6f73',
    primaryColorHover: '#3f8589',
    primaryColorPressed: '#245b5f',
    borderRadius: '8px',
    fontFamily: 'Lato, "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
    fontFamilyMono: '"Fira Code", Consolas, monospace'
  }
}

const navItems = [
  { key: 'overview', label: '概览', icon: AnalyticsOutline },
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
const autoLogs = ref(true)
const stickToBottom = ref(true)
const logBox = ref(null)
const logTimer = ref(null)

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
  proxy: '',
  default_model: '',
  public_base_url: '',
  empty_response_fallback: ''
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
  test: ['服务测试', '发起一次兼容 OpenAI 或 Gemini 的调用'],
  settings: ['配置', '调整 Cookie、代理、默认模型和公开地址'],
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
    const reason = data?.error?.message || data?.error || res.statusText
    throw new Error(reason)
  }
  return data
}

function applyStatus(data) {
  Object.assign(status, data)
  Object.assign(config, data.config || {})
  if (!test.model && status.models.length) test.model = status.models[0].id
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

async function saveConfig() {
  saving.value = true
  try {
    const data = await api('/admin/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
    Object.assign(config, data.config || {})
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
  try {
    const query = reset || logs.offset === null ? '?tail=60000' : `?offset=${logs.offset}`
    const data = await api(`/admin/api/logs${query}`)
    logs.offset = data.offset
    logs.size = data.size
    logs.text = reset ? data.content : logs.text + data.content
    if (stickToBottom.value) await scrollLogs()
  } catch (err) {
    message.error(`日志读取失败：${err.message}`)
  }
}

async function scrollLogs() {
  await nextTick()
  if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
}

function toggleLogTimer() {
  if (logTimer.value) clearInterval(logTimer.value)
  logTimer.value = autoLogs.value ? setInterval(() => readLogs(false), 1800) : null
}

async function copyText(text, label = '已复制') {
  await navigator.clipboard.writeText(text || '')
  message.success(label)
}

function openUrl(url) {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

watch(autoLogs, toggleLogTimer)

onMounted(async () => {
  await loadStatus()
  await readLogs(true)
  toggleLogTimer()
})

onBeforeUnmount(() => {
  if (logTimer.value) clearInterval(logTimer.value)
})
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div class="app-shell">
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
              <NButton secondary :loading="loading" @click="loadStatus(true)">
                <template #icon><NIcon :component="RefreshOutline" /></template>
                刷新
              </NButton>
              <NButton secondary @click="openUrl(status.urls.admin)">
                <template #icon><NIcon :component="OpenOutline" /></template>
                Web
              </NButton>
            </div>
          </header>

          <NSpin :show="loading && !status.version">
            <section v-show="active === 'overview'" class="content-grid">
              <div class="panel span-4 metric">
                <div class="metric-label">版本</div>
                <div class="metric-value">{{ status.version || '-' }}</div>
                <div class="metric-note">{{ status.admin_static?.ready ? '前端已构建' : '使用缺失提示页' }}</div>
              </div>
              <div class="panel span-4 metric">
                <div class="metric-label">模型</div>
                <div class="metric-value">{{ status.models.length }}</div>
                <div class="metric-note">默认：{{ config.default_model || '-' }}</div>
              </div>
              <div class="panel span-4 metric">
                <div class="metric-label">日志</div>
                <div class="metric-value">{{ Math.ceil((status.logs?.size || 0) / 1024) }} KB</div>
                <div class="metric-note">{{ status.logs?.path || '-' }}</div>
              </div>

              <div class="panel span-8">
                <div class="panel-head">
                  <h2 class="panel-title">调用地址</h2>
                  <NButton text type="primary" @click="copyText(JSON.stringify(status.urls, null, 2))">
                    <template #icon><NIcon :component="CopyOutline" /></template>
                    复制全部
                  </NButton>
                </div>
                <div class="url-list">
                  <div v-for="(value, key) in status.urls" :key="key" class="url-row">
                    <div class="url-label">{{ key }}</div>
                    <div class="url-value">{{ value || '未配置' }}</div>
                    <NButton size="small" secondary @click="copyText(value)"><template #icon><NIcon :component="CopyOutline" /></template></NButton>
                  </div>
                </div>
              </div>

              <div class="panel span-4">
                <h2 class="panel-title">运行环境</h2>
                <NSpace vertical size="large">
                  <NStatistic label="Cookie" :value="cookieState" />
                  <NStatistic label="代理" :value="proxyState" />
                  <NStatistic label="管理台目录" :value="status.admin_static?.ready ? 'ready' : 'missing'" />
                </NSpace>
              </div>
            </section>

            <section v-show="active === 'test'" class="content-grid">
              <div class="panel span-6">
                <h2 class="panel-title">请求</h2>
                <NForm label-placement="top">
                  <div class="form-grid">
                    <NFormItem label="接口">
                      <NSelect v-model:value="test.endpoint" :options="endpointOptions" />
                    </NFormItem>
                    <NFormItem label="模型">
                      <NSelect v-model:value="test.model" :options="modelOptions" filterable tag />
                    </NFormItem>
                    <NFormItem label="流式输出">
                      <NSwitch v-model:value="test.stream" :disabled="test.endpoint !== 'chat'" />
                    </NFormItem>
                    <NFormItem label="调用方法">
                      <NInput :value="currentEndpoint?.label || ''" readonly />
                    </NFormItem>
                    <NFormItem label="Prompt" class="full">
                      <NInput v-model:value="test.prompt" type="textarea" :autosize="{ minRows: 8, maxRows: 16 }" />
                    </NFormItem>
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
            </section>

            <section v-show="active === 'settings'" class="content-grid">
              <div class="panel span-8">
                <h2 class="panel-title">配置</h2>
                <NForm label-placement="top">
                  <NFormItem label="Cookie 文件路径">
                    <NInput v-model:value="config.cookie_file" placeholder="例如 D:\\cookies\\gemini_cookie.json" />
                  </NFormItem>
                  <NFormItem label="代理">
                    <NInput v-model:value="config.proxy" placeholder="例如 http://127.0.0.1:7890" />
                  </NFormItem>
                  <NFormItem label="默认模型">
                    <NSelect v-model:value="config.default_model" :options="modelOptions" filterable tag />
                  </NFormItem>
                  <NFormItem label="公网 Base URL">
                    <NInput v-model:value="config.public_base_url" placeholder="例如 http://example.com:8881/v1" />
                  </NFormItem>
                  <NFormItem label="空响应兜底文案">
                    <NInput v-model:value="config.empty_response_fallback" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
                  </NFormItem>
                </NForm>
                <div class="button-row">
                  <NButton type="primary" :loading="saving" @click="saveConfig"><template #icon><NIcon :component="SaveOutline" /></template>保存配置</NButton>
                  <NButton secondary @click="loadStatus(true)"><template #icon><NIcon :component="RefreshOutline" /></template>重新读取</NButton>
                </div>
              </div>
              <div class="panel span-4">
                <h2 class="panel-title">当前配置</h2>
                <pre class="code-box">{{ pretty(config) }}</pre>
              </div>
            </section>

            <section v-show="active === 'logs'" class="content-grid">
              <div class="panel span-12">
                <div class="panel-head">
                  <h2 class="panel-title">运行日志</h2>
                  <NSpace align="center" wrap>
                    <NCheckbox v-model:checked="stickToBottom">自动滚动</NCheckbox>
                    <NSwitch v-model:value="autoLogs" />
                    <NButton secondary @click="readLogs(true)"><template #icon><NIcon :component="RefreshOutline" /></template>重新载入</NButton>
                    <NButton secondary @click="copyText(logs.text, '日志已复制')"><template #icon><NIcon :component="DocumentTextOutline" /></template>复制</NButton>
                    <NButton secondary @click="logs.text = ''"><template #icon><NIcon :component="TrashOutline" /></template>清空视图</NButton>
                  </NSpace>
                </div>
                <pre v-if="logs.text" ref="logBox" class="code-box log-box">{{ logs.text }}</pre>
                <NEmpty v-else description="暂无日志" />
              </div>
            </section>
          </NSpin>
        </main>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>
