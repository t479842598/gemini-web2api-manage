# gemini-web2api

<p align="center">
  <img src="logo.png" width="200" alt="gemini-web2api logo">
</p>

[English](README.md)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2api&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

将 Google Gemini 网页端转换为 OpenAI 兼容 API. 零认证, 零成本, 跨平台.

## 特性

- **可选密钥**: `api_keys` 为空时免密, 填入密钥后按 OpenAI Bearer Key 校验
- **OpenAI 兼容**: 直接替换 `/v1/chat/completions` 和 `/v1/models`
- **工具调用**: 完整的 Function Calling 支持 (OpenAI 格式)
- **多模型**: Flash, Flash Thinking (2万字+输出), Pro, Auto, Lite
- **思考深度**: 通过 `@think=N` 后缀调节 (0=最深, 4=最浅)
- **联网搜索**: 内置互联网访问 (Gemini 原生搜索能力)
- **跨平台**: 纯 Python, 无外部依赖
- **流式输出**: SSE Streaming 支持
- **Codex CLI**: Responses API (`/v1/responses`) 兼容 OpenAI Codex
- **Gemini CLI**: Google 原生 API (`/v1beta/models`) 兼容 Gemini CLI
- **Web 管理台**: Vue 3 + Naive UI 页面, 可查看状态、测试接口、编辑配置、看详细日志
- **桌面管理器**: Windows 本地管理器, 支持一键启动、关闭、重启、打开 Web 端和查看日志
- **Vercel 部署**: 内置 Serverless 入口和一键部署按钮, 支持通过环境变量配置

## 快速开始

```bash
python gemini_web2api.py
```

服务启动在 `http://localhost:8081/v1`.

Web 管理台地址是 `http://localhost:8081/admin`.

## Web 管理台

![GeminiWeb2API 管理台截图](docs/admin-console.png)

管理台使用 Vue 3 + Naive UI 编写, 由 Python 服务在 `/admin` 直接托管.

| 页面 | 功能 |
|------|------|
| 概览 | 查看服务健康状态、版本、模型数量、本机/局域网/公网地址、日志大小、Cookie 状态、代理状态和前端构建状态. |
| 服务测试 | 可测试 OpenAI Chat Completions、OpenAI Responses、Google `generateContent`、Google `streamGenerateContent`; 支持选择模型、流式开关、响应预览和复制 curl. |
| 配置 | 编辑 `cookie_file`、`proxy`、`default_model`、`public_base_url`、`empty_response_fallback`, 并保存回 `config.json`. |
| 日志 | 读取 `logs/gemini_web2api.log`, 支持增量刷新、暂停/恢复自动刷新、复制、清空视图和自动滚动到底部. |

### 桌面管理器

Windows 下运行 `manager.pyw` 或打包后的 `GeminiWeb2API_Manager.exe`, 即可不用打开终端来管理本地服务.

- `启动`、`停止`、`重启` 控制后台 API 服务进程.
- `打开 Web 管理台` 打开 `http://127.0.0.1:{port}/admin`.
- `打开 API 地址` 打开 `http://127.0.0.1:{port}/v1`.
- 日志区域会实时读取同一个 `logs/gemini_web2api.log`, Web 管理台也使用这个日志文件.

### 重新构建管理台

只有修改 `web-admin/` 下的前端源码时才需要执行:

```bash
cd web-admin
npm install
npm run build
```

构建产物会写入 `gemini_web2api/admin_static/`, PyInstaller 配置也会把它打进 exe.

## 客户端配置

### Cherry Studio / ChatBox / 任何 OpenAI 兼容客户端

| 字段 | 值 |
|------|-----|
| Base URL | `http://localhost:8081/v1` |
| API Key | `config.json` 中的任意 `api_keys`；未配置时随便填 |
| Model | `gemini-3.5-flash-thinking` |

### curl

```bash
curl http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-key" \
  -d '{"model":"gemini-3.5-flash","messages":[{"role":"user","content":"你好!"}]}'
```

### OpenAI Python SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8081/v1", api_key="sk-your-key")
resp = client.chat.completions.create(
    model="gemini-3.5-flash-thinking",
    messages=[{"role": "user", "content": "解释量子计算"}]
)
print(resp.choices[0].message.content)
```

### Gemini CLI

```bash
export GEMINI_API_KEY=none
export GOOGLE_GEMINI_BASE_URL=http://localhost:8081
gemini
```

支持 Google 原生 API 端点:
- `GET /v1beta/models` — 模型列表
- `POST /v1beta/models/{model}:generateContent` — 非流式生成
- `POST /v1beta/models/{model}:streamGenerateContent` — 流式生成 (SSE)

## 可用模型

| 模型 | 说明 | 输出量 |
|------|------|--------|
| `gemini-3.5-flash` | 快速通用 | ~1.2万字 |
| `gemini-3.5-flash-thinking` | 深度思考, 最长输出 | **~2万字** |
| `gemini-3.5-flash-thinking-lite` | 自适应思考深度 | ~1.5万字 |
| `gemini-3.1-pro` | Pro (需 cookie 才能真正路由) | ~1.2万字 |
| `gemini-auto` | 自动选择模型 | 不定 |
| `gemini-flash-lite` | 轻量快速 | ~1万字 |

### 思考深度

在模型名后追加 `@think=N`:

```
gemini-3.5-flash-thinking@think=0   # 最深 (默认)
gemini-3.5-flash-thinking@think=2   # 中等
gemini-3.5-flash-thinking@think=4   # 最浅
```

## 可选: Cookie 配置 (Pro 模型)

匿名访问对所有模型有效, 但 `gemini-3.1-pro` 在无认证时会路由到 Flash. 要获得真正的 Pro 路由, 提供 cookie 文件:

```bash
python gemini_web2api.py --cookie-file cookie.txt
```

### 如何获取 Cookie

1. 打开 Chrome, 访问 [gemini.google.com](https://gemini.google.com) 并登录任意免费 Google 账号
2. 打开开发者工具 (F12) → Application → Cookies → `https://gemini.google.com`
3. 复制以下 cookie 值: `SID`, `HSID`, `SSID`, `APISID`, `SAPISID`, `__Secure-1PSID`
4. 创建 `cookie.txt`, 格式如下:

```
SID=你的SID值; HSID=你的HSID值; SSID=你的SSID值; APISID=你的APISID值; SAPISID=你的SAPISID值; __Secure-1PSID=你的1PSID值
```

或使用 JSON 格式:
```json
{"cookie": "SID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SAPISID=xxx; __Secure-1PSID=xxx", "sapisid": "你的SAPISID值"}
```

**替代方案 (浏览器扩展)**: 使用任意 "Export Cookies" 扩展导出 `gemini.google.com` 的 cookie, 然后转换为上述单行格式.

不需要付费订阅 — 免费 Google 账号即可.

## 配置文件

在同目录创建 `config.json`:

```json
{
  "port": 8081,
  "host": "0.0.0.0",
  "retry_attempts": 3,
  "retry_delay_sec": 2,
  "request_timeout_sec": 180,
  "api_keys": ["sk-your-key"],
  "cookie_file": null,
  "proxy": null,
  "default_model": "gemini-3.5-flash",
  "public_base_url": null,
  "empty_response_fallback": "Upstream returned an empty response. Please adjust the prompt or try again.",
  "log_requests": true
}
```

`api_keys` 为空数组 `[]` 时不校验密钥；填入一个或多个密钥后, `/v1/*` 接口需要 `Authorization: Bearer <key>` 或 `x-api-key: <key>`.

## Vercel 部署

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2api&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

仓库已包含 `api/index.py` 和 `vercel.json`, Vercel 会把它作为 Python Serverless Function 运行. `/`、`/admin`、`/admin/api/*`、`/v1/*`、`/v1beta/*` 都会路由到同一个处理器.

### 一键部署步骤

1. 点击上面的 **Deploy with Vercel** 按钮.
2. 将仓库导入你的 Vercel 账号. 如果你部署自己的 fork, 把按钮里的 repository URL 换成你的 fork 地址.
3. 按需填写环境变量. 下面的变量都是可选项, 只有需要 API Key 校验或真实 Pro 路由时才必须配置相关项.
4. 部署完成后, 使用 `https://your-project.vercel.app/v1` 作为 OpenAI 兼容 Base URL, 使用 `https://your-project.vercel.app/admin` 打开 Web 管理台.

### 环境变量

| 变量名 | 必填 | 示例 | 说明 |
|--------|------|------|------|
| `API_KEYS` | 否 | `sk-one,sk-two` | 多个密钥用英文逗号分隔. 留空表示不校验. 客户端用 `Authorization: Bearer <key>` 或 `x-api-key` 传入. |
| `GEMINI_COOKIE` | 否 | `SID=...; HSID=...; ...` | 完整 Gemini Cookie 字符串. Vercel 不能挂载本地 `cookie_file`, 所以云端部署用这个变量. |
| `DEFAULT_MODEL` | 否 | `gemini-3.5-flash-thinking` | 请求里没有 `model` 时使用的默认模型. |
| `PROXY` | 否 | `http://user:pass@host:port` | 上游访问 Gemini 时使用的 HTTP/HTTPS 代理. |
| `PUBLIC_BASE_URL` | 否 | `https://your-project.vercel.app/v1` | 管理台里展示的公网调用地址. |
| `GEMINI_BL` | 否 | `boq_assistant-bard-web-server_...` | Gemini 网页端 build label, 一般保持默认即可. |
| `RETRY_ATTEMPTS` | 否 | `3` | 上游请求重试次数. |
| `RETRY_DELAY_SEC` | 否 | `2` | 每次重试之间的等待秒数. |
| `REQUEST_TIMEOUT_SEC` | 否 | `60` | 上游请求超时时间, 建议不要超过当前 Vercel 套餐的函数时长. |
| `LOG_REQUESTS` | 否 | `true` | 是否输出函数日志. 云端日志请在 Vercel Logs 中查看. |

### Vercel 注意事项

- Vercel 是 Serverless 环境, 长时间流式响应会受到套餐和函数时长限制.
- Web 管理台可以查看状态和测试接口, 但云端日志主要在 Vercel Logs 里; 本地的 `logs/gemini_web2api.log` 更适合桌面版和 Docker 部署.
- 不要把真实 Cookie 或 API Key 提交到仓库. 请放到 Vercel Project Settings → Environment Variables.

## Docker 部署

```bash
cp config.example.json config.json
docker build -t gemini-web2api .
docker run -d --name gemini-web2api -p 8081:8081 -v ./config.json:/app/config.json gemini-web2api
```

或使用 Docker Compose:

```bash
cp config.example.json config.json
docker compose up -d
```

如需挂载 Cookie 文件:

```bash
docker run -d --name gemini-web2api -p 8081:8081 -v ./config.json:/app/config.json -v ./cookie.txt:/app/cookie.txt gemini-web2api
```

此时 `config.json` 中设置 `"cookie_file": "/app/cookie.txt"`.

## 代理配置

如果无法直接访问 `gemini.google.com` (连接超时), 需要配置代理:

**方式 1: 命令行参数**
```bash
python gemini_web2api.py --proxy http://127.0.0.1:7890
```

**方式 2: config.json**
```json
{"proxy": "http://127.0.0.1:7890"}
```

**方式 3: 环境变量** (自动检测)
```bash
set HTTPS_PROXY=http://127.0.0.1:7890
python gemini_web2api.py
```

支持 Clash, V2Ray, Shadowsocks 等任何 HTTP 代理.

## 系统要求

- Python 3.8+
- 无外部依赖 (仅标准库)
- 需要能访问 `gemini.google.com` (部分地区需代理)

## 工作原理

逆向 Google Gemini 网页端的 StreamGenerate 协议, 将 OpenAI API 格式与 Gemini 内部 protobuf-like 格式互转. 模型选择通过请求 payload 的 `[79]` 字段控制, 映射自 Gemini 前端 JS 源码中的 `MODE_CATEGORY` 枚举.

## 致谢

- [linux.do](https://linux.do) 社区
- 开源 API 代理生态

## License

MIT
