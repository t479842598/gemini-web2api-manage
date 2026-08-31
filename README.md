# Gemini Web2API Manage

<p align="center">
  <img src="logo.png" width="180" alt="Gemini Web2API Manage logo">
</p>

<p align="center">
  <strong>将 Google Gemini 网页端转换为 OpenAI 兼容 API，并提供完整 Web 管理台</strong>
</p>

<p align="center">
  <a href="https://github.com/t479842598/gemini-web2api-manage/releases/tag/v3.1.0">v3.1.0</a>
  · <a href="README_EN.md">English</a>
  · <a href="LICENSE">MIT License</a>
</p>

![登录页](docs/admin-login.png)

![概览页](docs/admin-dashboard.png)

## 项目简介

`gemini-web2api-manage` 是一个基于 Gemini Web 端协议的 API 管理服务。它把 Gemini 网页端能力包装为 OpenAI 兼容接口，同时提供一个可直接由 Python 服务托管的管理台。

项目适合以下场景：

- 在本地、VPS 或 Docker 中运行一个私有 Gemini API 网关。
- 使用 OpenAI SDK、Cherry Studio、ChatBox、Codex CLI 或其他兼容客户端调用 Gemini。
- 通过管理台配置 Cookie、代理、API Key、默认模型并查看运行日志。
- 在概览页查看请求量、成功率、Token 用量和模型用量。
- 在对话页测试多轮对话、文件上下文和 Agent 工具循环。

> 本项目依赖 Gemini 网页端协议，协议字段可能随 Google 网页端更新而变化。请勿将 Cookie、API Key 或管理员密码提交到 Git 仓库。

## v3.1.0 更新内容

- 对话页支持文件上传、服务器文件列表、文件内容读取和删除。
- 对话页支持 Agent 工具循环：`get_weather`、`calc`、`get_time`、`read_file`。
- 对话页支持图片选择、粘贴预览和 OpenAI `image_url` 消息格式。
- 前端从 Vue 3 + Naive UI 迁移到 React 19 + TypeScript + Tailwind CSS 4 + shadcn/base-ui。
- 概览页增加请求统计、成功率、Token、平均耗时、模型用量和 API Key 用量。
- Cookie 与代理配置统一写入稳定数据目录，服务重启或服务器重启后不会因工作目录变化而丢失。
- 增加 Google `at`/XSRF Token 自动提取与失败重试。
- 增加 SOCKS5 代理支持：通过本地 HTTP 桥接兼容 urllib 与 httpx。
- 增加 SPA 路由回退，支持直接访问 `/admin/login`、`/admin/dashboard` 等管理台路径。

## 技术栈

### 后端

- Python 3.8+
- 基于上游 `gemini-web2api` 子模块的 Gemini Web 协议实现
- `httpx`：流式请求与 HTTP 客户端
- `PySocks`：SOCKS5 代理桥接
- `http.server` + `ThreadingMixIn`：轻量 HTTP 服务，无需额外 Web 框架
- JSON 配置、JSONL 请求统计和文件系统持久化

### 前端

前端技术栈与 `freebuff2apiNew/web` 对齐：

- React 19
- TypeScript
- Vite 8
- Tailwind CSS 4
- shadcn/base-ui 组件风格
- Geist Variable 字体
- `lucide-react` 图标
- `sonner` Toast 通知
- `react-router-dom` 客户端路由
- `marked` Markdown 渲染

构建产物位于 `gemini_web2api_manage/admin_static/`，由后端通过 `/admin` 直接托管，不需要额外的前端服务器。

## 项目结构

```text
gemini-web2api-manage/
├── gemini_web2api_manage/       # 管理版 Python 包
│   ├── __main__.py              # 启动入口与配置加载
│   ├── config.py                # 管理版默认配置与环境变量适配
│   ├── admin.py                 # 管理台静态资源、配置、Cookie、文件管理
│   ├── server.py                # 管理 API、SPA 回退、上游请求统计接入
│   ├── stats.py                 # 请求记录与统计聚合
│   ├── xsrf.py                  # Gemini at/XSRF 自动获取与重试
│   ├── socks_bridge.py          # SOCKS5 到本地 HTTP 代理桥接
│   └── admin_static/            # React 构建产物
├── _upstream/                   # gemini-web2api Git submodule
├── web-admin/                   # React 管理台源代码
│   └── src/
│       ├── components/          # layout、theme、shared、ui
│       ├── pages/               # 登录、概览、对话、网络、测试、配置、日志
│       ├── hooks/               # 认证与轮询
│       ├── lib/                 # API Client 与工具函数
│       └── types/               # TypeScript 类型
├── api/index.py                 # Vercel Serverless 入口
├── docs/                        # README 截图与文档资源
├── config.example.json          # 配置模板
├── requirements.txt             # Python 依赖
├── Dockerfile
├── docker-compose.local.yml
└── manager.pyw                  # Windows 桌面管理器
```

## 快速开始

### 1. 克隆仓库并初始化子模块

```bash
git clone --recurse-submodules https://github.com/t479842598/gemini-web2api-manage.git
cd gemini-web2api-manage
```

如果已经克隆但子模块为空：

```bash
git submodule update --init --recursive
```

### 2. 创建 Python 环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt
```

### 3. 构建管理台

仓库已经包含构建产物。修改前端源码后重新构建：

```bash
cd web-admin
npm install
npm run build
cd ..
```

构建结果会写入：

```text
gemini_web2api_manage/admin_static/
```

### 4. 启动服务

```bash
python -m gemini_web2api_manage
```

默认地址：

- API：`http://127.0.0.1:8081/v1`
- 管理台：`http://127.0.0.1:8081/admin`

常用参数：

```bash
python -m gemini_web2api_manage --port 8081
python -m gemini_web2api_manage --config /path/to/config.json
python -m gemini_web2api_manage --cookie-file /path/to/cookie.txt
python -m gemini_web2api_manage --proxy http://127.0.0.1:7890
```

## 管理台功能

### 登录

管理台默认密码为 `sk-admin`。生产部署必须在配置中修改为独立密码。登录使用 HttpOnly 会话 Cookie，不会把管理员密码存入浏览器 localStorage。

### 概览

概览页提供：

- 服务健康状态、版本和默认模型。
- 可用模型数量与模型列表。
- 当前地址、局域网地址、公网地址和管理台地址。
- Cookie、代理、API Key、流式模式和鉴权状态。
- 请求总量、成功量、失败量、成功率、Token 总量和平均耗时。
- 按时间范围查看请求统计：当天、近 3 天、近 7 天、近 30 天、全部。
- 按模型和 API Key 查看 Token 用量。

### 对话

对话页提供：

- 多轮上下文对话。
- System Prompt。
- 流式/非流式切换。
- Markdown 回复渲染。
- Markdown 和 JSON 导出。
- localStorage 对话持久化。
- 图片选择、粘贴和预览。
- 文件上传到服务器。
- 服务器文件列表、读取文本和删除。
- Agent 模式，自动执行工具调用循环。

### 网络检测

查看本机 IP、公网 IP、地区、运营商/ASN、时区和代理状态，并分别检测 Gemini 与 Google 连通性。

### 服务测试

支持测试：

- OpenAI Chat Completions
- OpenAI Responses
- Google `generateContent`
- Google `streamGenerateContent`

页面支持模型选择、Prompt 编辑、流式切换、响应预览和复制 curl 命令。

### 配置

支持管理：

- 多个 API Key
- 多条 Gemini Cookie
- HTTP/HTTPS 代理
- SOCKS5 代理
- Gemini Base URL
- Google 账号序号
- XSRF Token
- Gemini BL
- 默认模型
- 临时对话
- 强制非流式
- 公网 Base URL
- 空响应兜底文案
- 管理员密码

### 日志

日志页支持增量轮询、搜索过滤、自动滚动、自动更新、复制和清空视图。

## API 端点

### OpenAI 兼容接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/v1/models` | 模型列表 |
| `POST` | `/v1/chat/completions` | Chat Completions，支持流式、工具和图片消息格式 |
| `POST` | `/v1/responses` | Responses API，兼容 Codex CLI |

### 探活接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/health` | 无需鉴权。返回 `status`、`version`、`models`、`gemini_bl`、`gemini_base_url`、`cookie_configured`、`streaming`、`proxy`、`default_model`、`expose_served_model`，用于部署健康检查与排障 |

### 关于实际服务模型（重重要）

Gemini 网页端是逆向接口。**实测（2026-08-31）证明：匿名模式下请求体里的模型档位（mode）与思考档位（think）对 Google 的路由完全无效** —— mode 取 1/2/3/4/5/6 时，官网回报的实际服务模型（响应 `inner[42]`）一律为 `3.5 Flash-Lite`。另已验证：注入真实浏览器抓到的 `inner[3]`（1.6KB protobuf token）与 `inner[4]`（32hex）**也不改变路由**。

因此自 v3.2.0 起，生成响应（含流式 chunk）会如实回报官网实际服务的模型：

| 字段 | 含义 |
|---|---|
| `model` | **官网实际服务的模型**（如 `3.5 Flash-Lite`） |
| `requested_model` | 你请求的模型名（如 `gemini-3.1-pro`） |
| `served_model` | 与 `model` 同值，语义更显式 |
| `gemini_conversation_id` / `gemini_response_id` | 官网回报的会话 / 响应 ID |
| `gemini_region` / `gemini_region_code` | 官网看到的出口 IP 归属地（排查区域限流用） |

行为说明：

- 模型键名全部保留，不影响已有调用方；`/v1/models` 的 `description` 已标注各档位的匿名限制与 Cookie 依赖。
- 设 `expose_served_model: false`（或环境变量 `EXPOSE_SERVED_MODEL=false`，管理台配置页可改、无需重启）可退回旧行为，`model` 只回显请求名。
- 管理台 `/admin/api/stats` 的 `by_model` 与 `/admin/api/status` 的 `last_generation` 会展示真实模型分布与最近一次出口地区。
- **Cookie 能否解锁真实模型路由尚未验证**（需带 Cookie 实测）。

### Google 原生接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/v1beta/models` | Gemini CLI 模型列表 |
| `POST` | `/v1beta/models/{model}:generateContent` | 非流式 Gemini 请求 |
| `POST` | `/v1beta/models/{model}:streamGenerateContent` | 流式 Gemini 请求 |

### 管理接口

管理接口除登录、登出、认证检查外都需要管理会话 Cookie。

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/admin/api/login` | 管理员登录 |
| `POST` | `/admin/api/logout` | 管理员登出 |
| `GET` | `/admin/api/auth` | 检查登录状态 |
| `GET` | `/admin/api/status` | 服务、模型、配置和地址状态 |
| `POST` | `/admin/api/config` | 保存配置和 Cookie 快照 |
| `GET` | `/admin/api/network` | 网络和连通性检测 |
| `GET` | `/admin/api/stats?range=7d` | 请求统计 |
| `GET` | `/admin/api/logs` | 增量读取日志 |
| `GET` | `/admin/api/files` | 上传文件列表 |
| `POST` | `/admin/api/files` | Base64 上传文件 |
| `GET` | `/admin/api/files/content?name=xxx` | 读取上传文件文本 |
| `DELETE` | `/admin/api/files?name=xxx` | 删除上传文件 |

## 客户端调用

### curl

未配置 `api_keys` 时可以不传 Authorization；配置后请传入有效 Key：

```bash
curl http://127.0.0.1:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer sk-gemini' \
  -d '{
    "model": "gemini-3.6-flash",
    "messages": [{"role": "user", "content": "你好，请介绍一下自己。"}]
  }'
```

流式请求：

```bash
curl http://127.0.0.1:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gemini-3.6-flash",
    "stream": true,
    "messages": [{"role": "user", "content": "写一首短诗。"}]
  }'
```

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8081/v1",
    api_key="sk-gemini",
)

response = client.chat.completions.create(
    model="gemini-3.6-flash",
    messages=[{"role": "user", "content": "解释量子计算。"}],
)
print(response.choices[0].message.content)
```

### Gemini CLI

```bash
export GEMINI_API_KEY=none
export GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:8081
gemini
```

### Codex / Responses API

将 Base URL 指向：

```text
http://127.0.0.1:8081/v1
```

并使用 `/v1/responses`。

## 模型列表

实际模型列表以 `GET /v1/models` 为准。当前管理台展示：

| 模型 | 说明 |
|---|---|
| `gemini-3.7-flash` | 最新通用 Flash 模型 |
| `gemini-3.6-flash` | 通用 Flash 模型 |
| `gemini-3.5-flash` | 兼容别名，映射到 Flash 路由 |
| `gemini-3.5-flash-thinking` | 深度思考模式 |
| `gemini-3.1-pro` | Pro 路由，通常需要有效 Cookie |
| `gemini-3.1-pro-enhanced` | 增强 Pro 实验路由 |
| `gemini-auto` | 自动选择模型 |
| `gemini-3.5-flash-thinking-lite` | 轻量思考模式 |
| `gemini-flash-lite` | 快速轻量模型 |

部分模型支持 `@think=N` 后缀调整思考深度：

```text
gemini-3.5-flash-thinking@think=0
gemini-3.5-flash-thinking@think=2
gemini-3.5-flash-thinking@think=4
```

## Cookie、代理与持久化

### Cookie

推荐通过管理台「配置 → Cookie」导入。导入后必须点击「保存配置」。Cookie 会写入稳定数据目录并记录到 `config.json` 的 `cookie_files`。

也可以准备文本文件：

```text
SID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SAPISID=xxx; __Secure-1PSID=xxx
```

再使用：

```bash
python -m gemini_web2api_manage --cookie-file ./cookie.txt
```

### 一键获取 Cookie（推荐）

关键鉴权 cookie 全是 **HttpOnly**（`SAPISID`、`__Secure-1PSID`、`SNlM0e`），
所以在网页控制台跑 `document.cookie` **根本拿不到**，从 Chrome「Application → Cookies」
面板一条条手工拼 `k=v; k=v` 也极易出错。本项目提供两条可用路径：

#### 路径 A：扩展一键推送（服务在远程机器时首选）

自带扩展 `tools/gemini-cookie-sync/`，用 `chrome.cookies.getAll()` 读取含 HttpOnly
的完整 cookie，**点一下直接推送到服务器并立即生效**，无需重启、无需碰配置文件。

```text
1. chrome://extensions → 开启开发者模式 → 加载已解压的扩展程序 → 选 tools/gemini-cookie-sync
2. 服务端启用推送令牌（下面）
3. 扩展里填服务地址与令牌 → 保存并授权该域名
4. 点「一键推送到服务器」
```

启用推送令牌（为空时端点完全关闭，返回 404 且与“端点不存在”不可区分）：

```bash
# 环境变量方式
COOKIE_PUSH_TOKEN="$(openssl rand -hex 24)"

# 或管理台 API（需先登录）
curl -X POST https://<你的域名>/admin/api/config \
  -H 'Content-Type: application/json' -b "gw_admin=<会话cookie>" \
  -d '{"cookie_push_token":"<至少 16 字符的随机串>"}'
```

令牌少于 16 字符会被拒绝；改回空串即关闭功能，改令牌即刻作废旧令牌。
端点采用常量时间比较与按 IP 滑窗限流（5 分钟内 8 次失败即 429）。

#### 路径 B：不装扩展，粘 Copy as cURL

1. 打开 `https://gemini.google.com/app` 并确保已登录
2. F12 → **Network** → 任选一条发往 `gemini.google.com` 的请求
3. 右键 → **Copy** → **Copy as cURL**
4. 管理台「配置 → Cookie」把整段 cURL **原样粘进输入框** → 保存配置

服务端自动识别并归一四种输入（因此 **React 前端无需改动**）：

| 格式 | 来源 |
|---|---|
| 裸串 `SID=...; SAPISID=...` | 手工或扩展「复制到剪贴板」 |
| `curl '...' -b '...'` / `-H 'Cookie: ...'` | DevTools Copy as cURL（bash 与 cmd 两种续行风格均支持） |
| `{"cookie": "...", "auth_user": 1, ...}` | 扩展导出的 `gemini-auth.json` |
| `Cookie: ...` 或整块请求头 | DevTools Headers 区 |

粘贴 JSON 时，随带的 `auth_user` / `xsrf_token` / `gemini_bl` 会一并应用。

> **安全**：Cookie 串等同 Google 账号登录态。服务端日志与接口响应只记录条数与
> 关键字段存在性，绝不回显明文；生产请仅通过 HTTPS 使用推送。

扩展的权限说明、故障排查与更多细节见
[tools/gemini-cookie-sync/README.md](tools/gemini-cookie-sync/README.md)。

### 代理

支持 HTTP/HTTPS 代理：

```json
{"proxy": "http://127.0.0.1:7890"}
```

也支持 SOCKS5：

```json
{"proxy": "socks5://user:password@proxy.example.com:443"}
```

服务会自动启动本地 HTTP 桥接，使 urllib 和 httpx 都能使用 SOCKS5。代理可在管理台配置，保存后重启自动恢复。

### 稳定数据目录

数据目录解析顺序：

1. `GEMINI_WEB2API_DATA_DIR`
2. 项目根目录
3. PyInstaller 可执行文件目录
4. 最后的临时目录兜底

生产环境建议显式设置：

```bash
export GEMINI_WEB2API_DATA_DIR=/var/lib/gemini-web2api
```

数据目录包含：

```text
config.json              # 当前配置
config.json.bak          # 保存前的上一份配置
cookie.txt / cookies/    # Cookie 文件
uploads/                 # 对话页上传文件
requests.jsonl           # 请求统计
logs/                    # 运行日志
```

只要数据目录位于持久化磁盘，服务重启和服务器重启都不会丢失 Cookie、代理配置、统计和上传文件。

## 配置文件

最小配置示例：

```json
{
  "port": 8081,
  "host": "0.0.0.0",
  "default_model": "gemini-3.6-flash",
  "api_keys": ["sk-gemini"],
  "admin_password": "change-this-password",
  "cookie_file": null,
  "cookie_files": [],
  "proxy": null,
  "log_requests": true,
  "temporary_chats": false
}
```

不要把真实 Cookie、API Key、管理员密码写入 Git。生产环境优先通过管理台或受保护的数据目录配置。

## 生产部署

### Linux x86_64 二进制（正式发布方式）

正式版提供 Linux x86_64 单文件可执行程序。它不要求服务器安装 Python、Node.js 或仓库源码；只需要准备一个持久化数据目录。

从 GitHub Release 下载：

```bash
VERSION=3.1.0
mkdir -p /opt/gemini-web2api-manage /var/lib/gemini-web2api
curl -fL -o /tmp/gemini-web2api-manage.tar.gz \
  "https://github.com/t479842598/gemini-web2api-manage/releases/download/v${VERSION}/gemini-web2api-manage-linux-x86_64-v${VERSION}.tar.gz"
tar -xzf /tmp/gemini-web2api-manage.tar.gz -C /opt/gemini-web2api-manage --strip-components=1
cp /opt/gemini-web2api-manage/config.example.json /var/lib/gemini-web2api/config.json
chmod +x /opt/gemini-web2api-manage/gemini-web2api-manage
```

创建服务用户并安装 systemd 服务：

```bash
sudo useradd --system --home /var/lib/gemini-web2api --shell /usr/sbin/nologin geminiweb || true
sudo chown -R geminiweb:geminiweb /opt/gemini-web2api-manage /var/lib/gemini-web2api
sudo cp /opt/gemini-web2api-manage/gemini-web2api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gemini-web2api
sudo systemctl status gemini-web2api
```

正式版服务文件将数据固定到 `/var/lib/gemini-web2api`，包括：

- `config.json` 和 `config.json.bak`
- Gemini Cookie 文件
- `requests.jsonl` 请求统计
- `uploads/` 对话上传文件
- 运行日志

因此服务重启和服务器重启都不会因为工作目录变化而丢失配置或数据。

从源码构建 Linux x86_64 二进制：

```bash
./deploy/build-linux-x86_64.sh
```

该脚本会安装 PyInstaller、构建管理版入口，并在 `release/` 生成二进制、配置模板、systemd 文件、README、CHANGELOG 和校验文件。PyInstaller 不能用 macOS 产物替代 Linux 产物，Linux 二进制必须在 Linux x86_64 或 Linux CI runner 上构建。

### systemd（源码运行方式）

如果不使用 Release 二进制，也可以使用 Python 虚拟环境从源码运行：

```ini
[Unit]
Description=Gemini Web2API Manage
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=geminiweb
Group=geminiweb
WorkingDirectory=/opt/gemini-web2api-manage
Environment=PYTHONUNBUFFERED=1
Environment=GEMINI_WEB2API_DATA_DIR=/var/lib/gemini-web2api
ExecStart=/opt/gemini-web2api-manage/.venv/bin/python -m gemini_web2api_manage --config /var/lib/gemini-web2api/config.json
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gemini-web2api
sudo systemctl status gemini-web2api
journalctl -u gemini-web2api -f
```

### Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name gemini.example.com;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

管理台地址为 `https://gemini.example.com/admin`，API 地址为 `https://gemini.example.com/v1`。

### Docker（非正式发布路径）

本次 v3.1.0 正式发布只提供 Linux x86_64 二进制。仓库中的 Docker 文件仅为源码用户保留，不纳入正式发布验证；生产环境请优先使用上面的 Release 二进制 + systemd。

### Windows 桌面管理器

Windows 用户可以运行 `manager.pyw`。Windows 桌面打包仍可使用现有 PyInstaller 管理器 spec；它与 Linux x86_64 Release 二进制是两个独立目标，不要在 macOS 上直接生成 Linux 可执行文件。

### Vercel

仓库保留 `api/index.py` 和 `vercel.json` 作为 Serverless 入口。Vercel 适合短请求和快速体验；长时间流式输出、持久化上传文件、请求统计和本地 Cookie 文件更推荐 Linux Release 二进制 + systemd。

## 统计与日志

请求统计写入 `requests.jsonl`，记录：

- 端点
- 模型
- 脱敏后的 API Key
- 成功/失败
- 请求耗时
- 估算的输入/输出/总 Token

统计文件会滚动限制大小，管理台通过 `/admin/api/stats?range=1d|3d|7d|30d|all` 聚合读取。

## 已知限制

1. **图片识别**：图片上传链路和 `image_url` 消息格式已经接入，但当前上游 fork 的 file binding 仍处于 WIP 状态，Gemini 可能返回 `BardErrorInfo [1003]`，表现为上传成功但模型内容为空。
2. **网页协议变化**：Google 更新网页端协议后，模型 ID、BL、Token 或图片绑定协议可能变化。
3. **Cookie 有效期**：Cookie 失效后需要重新从浏览器导出并在管理台保存。
4. **Vercel 持久化**：Serverless 临时文件不适合作为长期 Cookie、统计或上传文件存储。
5. **统计 Token**：Token 数来自上游响应 usage 或字符估算，不等同于官方计费 Token。

## 测试与发布验证

本版本已完成：

- Python 模块编译检查。
- React TypeScript + Vite 生产构建。
- 本地浏览器登录、概览、对话、网络、服务测试、配置、日志页面验证。
- 服务器公网管理台登录和 SPA 路由验证。
- 真实 Gemini 多轮对话、Pro/Flash 模型调用验证。
- Agent `read_file → calc` 服务器文件读取与计算验证。
- 文件上传、列表、读取、删除及路径穿越防护验证。

## 许可证

MIT

## 致谢

- [Sophomoresty/gemini-web2api](https://github.com/Sophomoresty/gemini-web2api)
- [freebuff2api](https://github.com/t479842598/freebuff2api)
- 开源 API 社区
