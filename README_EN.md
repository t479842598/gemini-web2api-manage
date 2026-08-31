# Gemini Web2API Manage

<p align="center">
  <img src="logo.png" width="180" alt="Gemini Web2API Manage logo">
</p>

<p align="center">
  <strong>Google Gemini Web gateway with an OpenAI-compatible API and a full React admin console.</strong>
</p>

<p align="center">
  <a href="https://github.com/t479842598/gemini-web2api-manage/releases/tag/v3.1.0">v3.1.0</a>
  · <a href="README.md">中文文档</a>
  · <a href="LICENSE">MIT License</a>
</p>

![Login page](docs/admin-login.png)

![Dashboard page](docs/admin-dashboard.png)

## Overview

`gemini-web2api-manage` wraps the Google Gemini web protocol as an OpenAI-compatible API and serves a production-oriented admin console from the same Python process.

It is designed for local machines, VPS deployments, Docker, and short-lived serverless experiments. The project includes Cookie persistence, proxy support, request statistics, file attachments, Agent tool loops, and a React management UI.

> This project depends on an undocumented Gemini web protocol. Google may change protocol fields, model routes, token formats, or upload behavior without notice. Never commit Cookies, API keys, or admin passwords.

## Highlights in v3.1.0

- File upload, listing, text preview, and deletion from the chat page.
- Server-file context injection for conversations.
- Agent mode with automatic `read_file`, `calc`, `get_weather`, and `get_time` tool loops.
- Image paste/upload and OpenAI `image_url` message construction.
- React 19 + TypeScript + Vite 8 + Tailwind CSS 4 + shadcn/base-ui admin console.
- Dashboard request statistics, success rate, Token usage, model usage, and API-key usage.
- Stable data directory for Cookie, proxy, statistics, logs, and uploads.
- Automatic Gemini `at`/XSRF extraction and retry.
- SOCKS5-to-HTTP bridge for urllib and httpx compatibility.

## Technology

### Backend

- Python 3.8+
- `gemini-web2api` Git submodule for the upstream Gemini web protocol
- `httpx` for streaming HTTP
- `PySocks` for SOCKS5 tunneling
- `http.server` and `ThreadingMixIn` for the lightweight HTTP service
- JSON configuration, JSONL statistics, and filesystem persistence

### Frontend

The frontend follows the same stack and visual language as `freebuff2apiNew/web`:

- React 19
- TypeScript
- Vite 8
- Tailwind CSS 4
- shadcn/base-ui components
- Geist Variable font
- `lucide-react` icons
- `sonner` notifications
- `react-router-dom` client-side routing
- `marked` Markdown rendering

The production bundle is written to `gemini_web2api_manage/admin_static/` and is served by the Python process at `/admin`.

## Architecture

```text
Client / SDK / CLI
        │
        ├── /v1/chat/completions
        ├── /v1/responses
        └── /v1beta/models/*
                │
        GeminiWeb2API Manage Handler
                │
        ├── upstream Gemini Web protocol
        ├── Cookie + SAPISID authentication
        ├── HTTP/SOCKS5 proxy bridge
        ├── XSRF token recovery
        └── request recorder → requests.jsonl

Browser ── /admin ── React SPA
                │
        /admin/api/*
        ├── auth / status / config
        ├── network / stats / logs
        └── files (uploads, read, delete)
```

## Repository layout

```text
gemini-web2api-manage/
├── gemini_web2api_manage/       # Manage-specific Python package
│   ├── __main__.py              # CLI entrypoint and startup config loading
│   ├── config.py                # Defaults and deployment environment config
│   ├── admin.py                 # Admin APIs, persistence, Cookie, files
│   ├── server.py                # Admin routes, SPA fallback, request hook
│   ├── stats.py                 # JSONL recorder and aggregations
│   ├── xsrf.py                  # Automatic Gemini at-token retry
│   ├── socks_bridge.py          # SOCKS5 → local HTTP bridge
│   └── admin_static/            # Built React assets
├── _upstream/                   # gemini-web2api Git submodule
├── web-admin/                   # React + TypeScript source
├── api/index.py                 # Vercel Serverless entrypoint
├── docs/                        # Release screenshots and documentation assets
├── config.example.json
├── requirements.txt
├── Dockerfile
├── docker-compose.local.yml
└── manager.pyw                  # Windows desktop manager
```

## Quick start

### Clone with the upstream submodule

```bash
git clone --recurse-submodules https://github.com/t479842598/gemini-web2api-manage.git
cd gemini-web2api-manage
```

For an existing clone:

```bash
git submodule update --init --recursive
```

### Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt
```

### Build the admin console

The repository contains built assets. Rebuild after changing `web-admin/`:

```bash
cd web-admin
npm install
npm run build
cd ..
```

The output is written to:

```text
gemini_web2api_manage/admin_static/
```

### Start

```bash
python -m gemini_web2api_manage
```

Default endpoints:

- API: `http://127.0.0.1:8081/v1`
- Admin: `http://127.0.0.1:8081/admin`

Useful options:

```bash
python -m gemini_web2api_manage --port 8081
python -m gemini_web2api_manage --config /path/to/config.json
python -m gemini_web2api_manage --cookie-file /path/to/cookie.txt
python -m gemini_web2api_manage --proxy http://127.0.0.1:7890
```

## Admin console

### Login and dashboard

The admin console uses a signed HttpOnly session Cookie. The default password is `sk-admin`; change it before exposing the console publicly.

The dashboard shows service health, available models, URLs, runtime configuration, request totals, success/error rates, Token usage, model usage, API-key usage, and time-range trends.

### Chat

The chat page includes:

- Multi-turn context and System Prompt.
- Streaming/non-streaming toggle.
- Markdown rendering and Markdown/JSON export.
- localStorage conversation persistence.
- Image selection, paste preview, and `image_url` request construction.
- File upload and server-file context injection.
- Agent mode with automatic tool-call loops.

### Other pages

- **Network**: local/public IP, region, provider, proxy state, Gemini connectivity, Google connectivity.
- **Service Test**: Chat Completions, Responses, `generateContent`, `streamGenerateContent`, model selection, response preview, and curl copy.
- **Settings**: API keys, Cookies, proxy, model, XSRF, BL, public URL, stream behavior, and admin password.
- **Logs**: incremental polling, filtering, auto-scroll, copy, and clear view.

## API endpoints

### OpenAI-compatible

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/models` | List models |
| `POST` | `/v1/chat/completions` | Chat Completions, streaming and tools |
| `POST` | `/v1/responses` | Responses API for Codex-compatible clients |

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | No auth required. Returns `status`, `version`, `models`, `gemini_bl`, `gemini_base_url`, `cookie_configured`, `streaming`, `proxy`, `default_model`, `expose_served_model` |

### About the actually served model (important)

Gemini's web endpoint is a reverse-engineered interface. **Measured on 2026-08-31: in anonymous mode the model tier (`mode`) and thinking tier (`think`) in the request body have no effect on Google's routing** — for mode 1/2/3/4/5/6 the upstream-reported served model (response `inner[42]`) is always `3.5 Flash-Lite`. It was also verified that injecting the real browser's `inner[3]` (1.6 KB protobuf token) and `inner[4]` (32-hex) does **not** change routing either.

Since v3.2.0 generation responses (including streaming chunks) report the model that actually served the request:

| Field | Meaning |
|---|---|
| `model` | The model **actually serving** the request (e.g. `3.5 Flash-Lite`) |
| `requested_model` | The model name you asked for (e.g. `gemini-3.1-pro`) |
| `served_model` | Same as `model`, more explicit |
| `gemini_conversation_id` / `gemini_response_id` | Upstream conversation / response IDs |
| `gemini_region` / `gemini_region_code` | Egress IP region as seen by Google (useful for regional rate-limit debugging) |

Notes:

- All model keys are preserved, so existing clients keep working; `/v1/models` descriptions now state the anonymous limitation and Cookie dependency per tier.
- Set `expose_served_model: false` (or `EXPOSE_SERVED_MODEL=false`) to restore the old behaviour where `model` only echoes the requested name. Editable in the admin console without a restart.
- `/admin/api/stats` (`by_model`) and `/admin/api/status` (`last_generation`) surface the real model distribution and the latest egress region.
- **Whether a Cookie unlocks real model routing is not yet verified** (requires testing with a valid Cookie).

### Google-compatible

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1beta/models` | Gemini CLI model list |
| `POST` | `/v1beta/models/{model}:generateContent` | Non-streaming generation |
| `POST` | `/v1beta/models/{model}:streamGenerateContent` | Streaming generation |

### Admin API

All admin endpoints except login, logout, and session check require the signed admin session.

| Method | Path | Description |
|---|---|---|
| `POST` | `/admin/api/login` | Admin login |
| `POST` | `/admin/api/logout` | Admin logout |
| `GET` | `/admin/api/auth` | Session check |
| `GET` | `/admin/api/status` | Service/config/model status |
| `POST` | `/admin/api/config` | Save config and Cookie snapshot |
| `GET` | `/admin/api/network` | Network diagnostics |
| `GET` | `/admin/api/stats?range=7d` | Request statistics |
| `GET` | `/admin/api/logs` | Incremental logs |
| `GET` | `/admin/api/files` | Uploaded file list |
| `POST` | `/admin/api/files` | Base64 file upload |
| `GET` | `/admin/api/files/content?name=xxx` | Read uploaded text |
| `DELETE` | `/admin/api/files?name=xxx` | Delete uploaded file |

## Client examples

### curl

```bash
curl http://127.0.0.1:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer sk-gemini' \
  -d '{
    "model": "gemini-3.6-flash",
    "messages": [{"role": "user", "content": "Hello"}]
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
    messages=[{"role": "user", "content": "Explain quantum computing."}],
)
print(response.choices[0].message.content)
```

## Models

The authoritative model list is returned by `GET /v1/models`. The current build includes:

| Model | Description |
|---|---|
| `gemini-3.7-flash` | Latest general Flash route |
| `gemini-3.6-flash` | General Flash route |
| `gemini-3.5-flash` | Compatibility alias |
| `gemini-3.5-flash-thinking` | Deep-thinking route |
| `gemini-3.1-pro` | Pro route; usually requires a valid Cookie |
| `gemini-3.1-pro-enhanced` | Experimental enhanced Pro route |
| `gemini-auto` | Automatic model selection |
| `gemini-3.5-flash-thinking-lite` | Lightweight thinking route |
| `gemini-flash-lite` | Fast lightweight route |

## Cookie, proxy, and persistence

### Cookie

Use **Settings → Cookie** in the admin console and click **Save config**. The Cookie is stored in the stable data directory and referenced by `cookie_files` in `config.json`.

A text Cookie file can also be supplied:

```text
SID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SAPISID=xxx; __Secure-1PSID=xxx
```

```bash
python -m gemini_web2api_manage --cookie-file ./cookie.txt
```

### One-click Cookie acquisition (recommended)

The cookies that matter for auth are all **HttpOnly** (`SAPISID`,
`__Secure-1PSID`, `SNlM0e`), so `document.cookie` in the page console
**cannot read them at all**, and copying rows one by one out of Chrome's
"Application → Cookies" panel into a `k=v; k=v` string is error-prone.
Two working paths:

#### Path A: extension one-click push (best when the server is remote)

The bundled extension at `tools/gemini-cookie-sync/` reads the full cookie set
including HttpOnly via `chrome.cookies.getAll()` and **pushes it straight to the
server — effective immediately, no restart, no config file editing**.

```text
1. chrome://extensions → enable Developer mode → Load unpacked → pick tools/gemini-cookie-sync
2. Enable a push token on the server (below)
3. In the extension, fill server URL + token → Save & grant origin
4. Click "Push to server"
```

Enable the push token (when empty the endpoint is fully off and returns 404,
indistinguishable from "route does not exist"):

```bash
COOKIE_PUSH_TOKEN="$(openssl rand -hex 24)"
```

Tokens shorter than 16 characters are rejected. Setting it back to empty
disables the feature; changing it invalidates the old token immediately. The
endpoint uses constant-time comparison and per-IP sliding-window rate limiting
(8 failures within 5 minutes → 429).

#### Path B: no extension — paste Copy as cURL

1. Open `https://gemini.google.com/app` while signed in
2. F12 → **Network** → pick any request to `gemini.google.com`
3. Right-click → **Copy** → **Copy as cURL**
4. In the admin console under "Config → Cookie", paste the whole thing as-is → Save

The server auto-detects and normalises four input shapes (so the **React
frontend needs no change**):

| Format | Source |
|---|---|
| Raw `SID=...; SAPISID=...` | Manual, or the extension's "Copy to clipboard" |
| `curl '...' -b '...'` / `-H 'Cookie: ...'` | DevTools Copy as cURL (both bash and cmd line-continuation styles) |
| `{"cookie": "...", "auth_user": 1, ...}` | The extension's `gemini-auth.json` |
| `Cookie: ...` or a whole header block | DevTools Headers pane |

When JSON is pasted, the accompanying `auth_user` / `xsrf_token` / `gemini_bl`
values are applied too.

> **Security**: a cookie string is equivalent to your Google session. Server logs
> and API responses only report cookie counts and field presence — never the raw
> values. Use HTTPS only in production.

See [tools/gemini-cookie-sync/README.md](tools/gemini-cookie-sync/README.md)
for extension permissions and troubleshooting.

### Proxy

HTTP/HTTPS:

```json
{"proxy": "http://127.0.0.1:7890"}
```

SOCKS5:

```json
{"proxy": "socks5://user:password@proxy.example.com:443"}
```

The service starts an in-process local HTTP bridge for SOCKS5, so both urllib and httpx can use it. Proxy settings are persisted and restored on restart.

### Stable data directory

Resolution order:

1. `GEMINI_WEB2API_DATA_DIR`
2. Project root
3. Frozen executable directory
4. Temporary fallback

For production, set it explicitly:

```bash
export GEMINI_WEB2API_DATA_DIR=/var/lib/gemini-web2api
```

The directory contains `config.json`, `config.json.bak`, Cookie files, `uploads/`, `requests.jsonl`, and logs. Put it on a persistent disk to survive service and host reboots.

## Configuration

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

Never commit real credentials.

## Deployment

### Linux x86_64 binary (official release path)

The official release ships a single Linux x86_64 executable. The server does not need Python, Node.js, or the source tree; it only needs a persistent data directory.

Download a GitHub Release:

```bash
VERSION=3.1.0
mkdir -p /opt/gemini-web2api-manage /var/lib/gemini-web2api
curl -fL -o /tmp/gemini-web2api-manage.tar.gz \
  "https://github.com/t479842598/gemini-web2api-manage/releases/download/v${VERSION}/gemini-web2api-manage-linux-x86_64-v${VERSION}.tar.gz"
tar -xzf /tmp/gemini-web2api-manage.tar.gz -C /opt/gemini-web2api-manage --strip-components=1
cp /opt/gemini-web2api-manage/config.example.json /var/lib/gemini-web2api/config.json
chmod +x /opt/gemini-web2api-manage/gemini-web2api-manage
```

Install the systemd service:

```bash
sudo useradd --system --home /var/lib/gemini-web2api --shell /usr/sbin/nologin geminiweb || true
sudo chown -R geminiweb:geminiweb /opt/gemini-web2api-manage /var/lib/gemini-web2api
sudo cp /opt/gemini-web2api-manage/gemini-web2api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gemini-web2api
sudo systemctl status gemini-web2api
```

The release service stores all mutable data under `/var/lib/gemini-web2api`:

- `config.json` and `config.json.bak`
- Gemini Cookie files
- `requests.jsonl` request statistics
- `uploads/` chat attachments
- runtime logs

This keeps configuration and data across both service and host reboots.

Build the Linux x86_64 binary from source:

```bash
./deploy/build-linux-x86_64.sh
```

The script installs PyInstaller, builds the manage entrypoint, and creates a binary bundle, config template, systemd unit, README, CHANGELOG, and checksums under `release/`. PyInstaller does not cross-compile native bootloaders; build the Linux artifact on Linux x86_64 or a Linux CI runner.

### systemd (source checkout)

If you prefer not to use the Release binary, run the source checkout from a Python virtual environment:

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

The API is `https://gemini.example.com/v1` and the console is `https://gemini.example.com/admin`.

### Docker (not the official release path)

The v3.1.0 official release is the Linux x86_64 binary. The repository keeps Docker files for source users, but Docker is not part of the official release verification; use the Release binary + systemd for production.

### Windows desktop manager

Windows users can run `manager.pyw`. Windows PyInstaller packaging remains available through the existing manager spec; it is a separate target from the Linux x86_64 release. Do not build the Linux executable on macOS.

### Vercel

`api/index.py` and `vercel.json` provide a Serverless entrypoint. Vercel is suitable for short requests and experiments; a Linux Release binary with systemd is recommended for persistent files, long streams, request history, and stable Cookie storage.

## Statistics and logs

Request records are stored in `requests.jsonl` with endpoint, model, masked API key, success state, duration, and estimated Token usage. The file is size-limited and can be queried through `/admin/api/stats?range=1d|3d|7d|30d|all`.

## Known limitations

1. **Image recognition**: the image upload and `image_url` request path is implemented, but the upstream fork's file-binding work is still WIP. Gemini may return `BardErrorInfo [1003]`, meaning the upload succeeds while the model response is empty.
2. **Web protocol changes**: Google may change model IDs, BL values, XSRF formats, or upload binding behavior.
3. **Cookie lifetime**: an expired Cookie must be exported again and saved from Settings.
4. **Serverless persistence**: Vercel temporary storage is not suitable for long-term Cookie, statistics, or file storage.
5. **Token counts**: usage values come from upstream usage fields or character estimates and are not official billing counts.

## Release verification

v3.1.0 was verified with Python compilation, a production frontend build, local browser page checks, production admin login, real Gemini multi-turn calls, Pro/Flash model calls, Agent `read_file → calc` execution, file upload/list/read/delete, SPA routing, and persistent Cookie/statistics behavior.

## License

MIT

## Acknowledgements

- [Sophomoresty/gemini-web2api](https://github.com/Sophomoresty/gemini-web2api)
- [freebuff2api](https://github.com/t479842598/freebuff2api)
- The open-source API community
