# gemini-web2ai-manage

<p align="center">
  <img src="logo.png" width="200" alt="gemini-web2ai-manage logo">
</p>

[English](README_EN.md)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=ADMIN_PASSWORD,API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2ai-manage&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

将 Google Gemini 网页端转换为 OpenAI 兼容 API. 零认证, 零成本, 跨平台.

## 特性

- **可选密钥**: `api_keys` 为空时免密, 填入密钥后按 OpenAI Bearer Key 校验
- **OpenAI 兼容**: 直接替换 `/v1/chat/completions` 和 `/v1/models`
- **工具调用**: 完整的 Function Calling 支持 (OpenAI 格式)，`tool_choice=auto` 时自动引导模型优先调用工具
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

### 方式一：本地运行（推荐）

```bash
# 1. 安装依赖
pip install httpx

# 2. 配置 Cookie（可选，可匿名使用）
#    复制 .env.example 为 .env，填入你的 Gemini Cookie
cp .env.example .env

# 3. 启动服务
python -m gemini_web2api_manage
```

服务启动在 `http://localhost:8081/v1`. Web 管理台地址是 `http://localhost:8081/admin`.

### 方式二：桌面管理器（Windows）

双击 `manager.pyw` 启动桌面管理器，支持一键启动、关闭、重启、查看日志。

### 方式三：Docker

```bash
docker build -t gemini-web2api .
docker run -p 8081:8081 -e GEMINI_COOKIE="your_cookie" gemini-web2api
```

## Web 管理台

![GeminiWeb2API 管理台截图](docs/admin-console.png)

管理台使用 Vue 3 + Naive UI 编写, 由 Python 服务在 `/admin` 直接托管.

| 页面 | 功能 |
|------|------|
| 登录 | 默认管理员密码是 `sk-admin`; 登录后可在配置页修改管理员密码. |
| 概览 | 查看服务健康状态、版本、模型数量、本机/局域网/公网地址、日志大小、Cookie 状态、代理状态和前端构建状态. |
| 网络 | 获取本机 IP、公网 IP、所在地区、运营商/ASN, 并测试 Gemini 与 Google 连通性. |
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
| `gemini-3.6-flash` | 最新快速通用模型 | ~1.2万字 |
| `gemini-3.5-flash` | `gemini-3.6-flash` 兼容别名 | ~1.2万字 |
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

匿名访问对所有模型有效, 但 `gemini-3.1-pro` 在无认证时会路由到 Flash. 要获得真正的 Pro 路由, 提供 Cookie.

### 方式一：.env 文件（推荐）

复制 `.env.example` 为 `.env`，填入 Cookie 字符串：

```bash
cp .env.example .env
# 编辑 .env，设置 GEMINI_COOKIE="SID=xxx; HSID=xxx; ..."
```

### 方式二：命令行参数

```bash
python -m gemini_web2api --cookie-file cookie.txt
```

### 方式三：环境变量 (Vercel/Serverless)

在 Vercel 环境变量中设置 `GEMINI_COOKIE`。

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
  "admin_password": "sk-admin",
  "cookie_file": null,
  "proxy": null,
  "default_model": "gemini-3.6-flash",
  "public_base_url": null,
  "empty_response_fallback": "Gemini 返回了空内容。可能原因：Cookie 失效、内容被安全策略拦截、上下文过长或当前模型暂不可用。请查看管理台日志中的空响应诊断后重试。",
  "log_requests": true
}
```

`api_keys` 为空数组 `[]` 时不校验密钥；填入一个或多个密钥后, `/v1/*` 和 `/v1beta/*` 接口支持 `Authorization: Bearer <key>`、`x-api-key`、`x-goog-api-key` 或 `?key=<key>`.

## Vercel 部署

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=ADMIN_PASSWORD,API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2ai-manage&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

仓库已包含 `api/index.py` 和 `vercel.json`, Vercel 会把它作为 Python Serverless Function 运行. `/`、`/admin`、`/admin/api/*`、`/v1/*`、`/v1beta/*` 都会路由到同一个处理器.

### 部署前准备

1. 准备一个 GitHub 账号和 Vercel 账号.
2. 如果只是快速体验, 可以不配置任何环境变量, 匿名模式也能调用 Flash 系列模型.
3. 如果要限制别人调用你的接口, 准备一个或多个自定义 API Key, 例如 `sk-my-private-key`.
4. 如果要让 `gemini-3.1-pro` 尽量按真实 Pro 路由, 准备 `GEMINI_COOKIE`. Cookie 获取方式见上面的 Cookie 配置章节.
5. 如果你的 Vercel 部署区域访问 `gemini.google.com` 不稳定, 准备一个 HTTP/HTTPS 代理地址并填入 `PROXY`.

### 方式一: 一键部署

1. 点击上方 **Deploy with Vercel** 按钮.
2. Vercel 会打开新项目导入页, Repository 默认指向 `t479842598/gemini-web2api-manage`.
3. Project Name 可以保持默认, Framework Preset 选择 `Other` 或保持 Vercel 自动识别.
4. 在 Environment Variables 页面按需填写变量. 只想先跑起来可以全部留空.
5. 点击 **Deploy** 等待构建完成.
6. 部署完成后进入 Vercel 项目页, 打开 Production 域名.

### 方式二: Fork 后部署

1. 在 GitHub 上 Fork 本仓库到自己的账号.
2. 登录 Vercel, 点击 **Add New... → Project**.
3. 选择你 Fork 后的仓库并导入.
4. Build & Output Settings 保持默认即可, `vercel.json` 会负责路由.
5. 在 Environment Variables 中填入需要的变量.
6. 点击 **Deploy**. 之后你推送到 GitHub, Vercel 会自动重新部署.

### 方式三: Vercel CLI 部署

```bash
npm i -g vercel
vercel login
vercel
vercel --prod
```

CLI 首次运行会询问项目名称、团队和是否链接现有项目. 如果需要通过 CLI 添加变量:

```bash
vercel env add API_KEYS production
vercel env add GEMINI_COOKIE production
vercel env add DEFAULT_MODEL production
vercel --prod
```

### 环境变量

| 变量名 | 必填 | 示例 | 说明 |
|--------|------|------|------|
| `ADMIN_PASSWORD` | 否 | `sk-admin` | Web 管理台登录密码. 不配置时默认 `sk-admin`, 建议生产环境改掉. |
| `API_KEYS` | 否 | `sk-one,sk-two` | 多个密钥用英文逗号分隔. 留空表示不校验. 客户端用 `Authorization: Bearer <key>` 或 `x-api-key` 传入. |
| `GEMINI_COOKIE` | 否 | `SID=...; HSID=...; ...` | 完整 Gemini Cookie 字符串. Vercel 不能挂载本地 `cookie_file`, 所以云端部署用这个变量. |
| `DEFAULT_MODEL` | 否 | `gemini-3.6-flash` | 请求里没有 `model` 时使用的默认模型. |
| `PROXY` | 否 | `http://user:pass@host:port` | 上游访问 Gemini 时使用的 HTTP/HTTPS 代理. 注意不要填写 SOCKS 地址. |
| `PUBLIC_BASE_URL` | 否 | `https://your-project.vercel.app/v1` | 管理台里展示的公网调用地址. |
| `GEMINI_BL` | 否 | `boq_assistant-bard-web-server_...` | Gemini 网页端 build label, 一般保持默认即可. |
| `RETRY_ATTEMPTS` | 否 | `3` | 上游请求重试次数. |
| `RETRY_DELAY_SEC` | 否 | `2` | 每次重试之间的等待秒数. |
| `REQUEST_TIMEOUT_SEC` | 否 | `60` | 上游请求超时时间, 建议不要超过当前 Vercel 套餐的函数时长. |
| `LOG_REQUESTS` | 否 | `true` | 是否输出函数日志. 云端日志请在 Vercel Logs 中查看. |

### 推荐配置示例

公开测试, 不加鉴权:

```text
DEFAULT_MODEL=gemini-3.5-flash-thinking
PUBLIC_BASE_URL=https://your-project.vercel.app/v1
LOG_REQUESTS=true
```

私人使用, 加 API Key:

```text
API_KEYS=sk-your-private-key
ADMIN_PASSWORD=change-this-admin-password
DEFAULT_MODEL=gemini-3.5-flash-thinking
PUBLIC_BASE_URL=https://your-project.vercel.app/v1
```

带 Cookie 和代理:

```text
API_KEYS=sk-your-private-key
GEMINI_COOKIE=SID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SAPISID=xxx; __Secure-1PSID=xxx
PROXY=http://user:pass@proxy.example.com:8080
REQUEST_TIMEOUT_SEC=60
```

### 部署后验证

把 `your-project.vercel.app` 换成自己的域名:

```bash
curl https://your-project.vercel.app/
curl https://your-project.vercel.app/v1/models
curl https://your-project.vercel.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-private-key" \
  -d '{"model":"gemini-3.5-flash","messages":[{"role":"user","content":"hello"}]}'
```

如果没有配置 `API_KEYS`, 可以去掉 `Authorization` 请求头. Web 管理台地址是:

```text
https://your-project.vercel.app/admin
```

OpenAI 兼容客户端填写:

| 字段 | 值 |
|------|-----|
| Base URL | `https://your-project.vercel.app/v1` |
| API Key | `API_KEYS` 中的任意一个; 未配置时可随便填 |
| Model | `gemini-3.5-flash-thinking` |

### 更新部署

- 如果使用一键部署导入的仓库, 后续修改代码后推送到 GitHub, Vercel 会自动重新部署.
- 如果只改环境变量, 在 Vercel Project Settings → Environment Variables 修改后, 进入 Deployments 重新部署一次生产环境.
- 如果本地改了前端管理台, 先运行 `cd web-admin && npm run build`, 再提交 `gemini_web2api/admin_static/` 的构建产物.

### 常见问题

- `401 invalid api key`: 你配置了 `API_KEYS`, 但客户端没有传 `Authorization: Bearer <key>` 或 `x-api-key`.
- `upstream error` 或请求超时: Vercel 所在区域可能访问 Gemini 不稳定, 尝试配置 `PROXY` 或调大 `REQUEST_TIMEOUT_SEC`.
- Pro 模型仍像 Flash: 没有配置 `GEMINI_COOKIE`, Cookie 过期, 或当前账号本身没有对应能力.
- `/admin` 能打开但日志为空: Vercel 日志在 Vercel 项目页的 Logs 中查看, 本地日志文件主要用于桌面版和 Docker.
- 流式响应中断: Serverless 函数有执行时长限制, 长输出建议降低请求长度或使用本地/Docker 部署.

### Vercel 注意事项

- 不要把真实 Cookie 或 API Key 提交到仓库, 请放到 Vercel Project Settings → Environment Variables.
- Vercel 是 Serverless 环境, 不适合当成长期常驻进程; 每次请求会由函数处理.
- 免费套餐和不同区域的网络表现可能不同, 如果需要稳定长流式输出, 本地桌面管理器或 Docker 更可控.

## Docker 部署

```bash
cp config.example.json config.json
docker build -t gemini-web2ai-manage .
docker run -d --name gemini-web2ai-manage -p 8081:8081 -v ./config.json:/app/config.json gemini-web2ai-manage
```

或使用 Docker Compose:

```bash
cp config.example.json config.json
docker compose up -d
```

如需挂载 Cookie 文件:

```bash
docker run -d --name gemini-web2ai-manage -p 8081:8081 -v ./config.json:/app/config.json -v ./cookie.txt:/app/cookie.txt gemini-web2ai-manage
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

## 更新日志

### v2.0.1 (2026-07-30)

**修复工具调用与请求分发**
- 修复 manage 层 `do_POST` 提前消费请求 body 导致所有 API 请求（`/v1/chat/completions`、`/v1/responses`、Google `:generateContent`）返回 400 "invalid JSON" 的严重 bug。manage 层现在仅对 admin 路由读取 body，其余路径直接转交 upstream 处理
- 增强 `tool_choice=auto` 工具调用引导：Gemini Web 逆向接口靠 prompt 注入模拟工具调用，auto 模式下模型常选择直接编答案而非触发 tool_call。现对 auto 模式追加软引导提示，推动模型在请求匹配工具能力时优先调用工具，同时保留模型裁量权
- 修正 README 启动命令为 `python -m gemini_web2api_manage`

### v2.0.0 (2026-07-28)

**项目结构重构**
- 上游 `Sophomoresty/gemini-web2api` 引入为 git submodule（`_upstream/`），后续只需 `git submodule update --remote` 即可同步
- 新建 `gemini_web2api_manage/` 扩展包，继承上游 `GeminiHandler` 并注入管理台路由
- 启动命令从 `python -m gemini_web2api` 改为 `python -m gemini_web2api_manage`

**前端管理台视觉重构**
- 概览页新增 hero 健康状态卡片（绿/红色渐变边框 + 大图标 + 版本/模型/IP 概要）
- 概览页新增快捷操作栏（一键直达对话、测试、复制 URL、日志、网络检测）
- 调用地址列表改为中文标签 + 打开/复制按钮
- 运行环境改为独立卡片 + 图标 + 彩色状态文字
- 新增可用模型列表面板（点击跳转到服务测试页）

**前端功能增强**
- 导航栏服务异常时显示红色 badge
- 顶栏新增"复制 URL"快捷按钮
- 对话页支持 localStorage 持久化（刷新不丢失）
- 对话页新增 System Prompt 输入框
- 对话页新增导出 Markdown 按钮
- 日志页新增关键词搜索过滤
- 网络页连通性面板新增 status tag（连通/不可达 + 延迟 ms）

## 致谢

- [linux.do](https://linux.do) 社区
- 开源 API 代理生态

## License

MIT
