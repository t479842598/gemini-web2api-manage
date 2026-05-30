# gemini-web2ai-manage

<p align="center">
  <img src="logo.png" width="200" alt="gemini-web2ai-manage logo">
</p>

[中文文档](README.md)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=ADMIN_PASSWORD,API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2ai-manage&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

Convert Google Gemini's web interface into an OpenAI-compatible API. Zero authentication, zero cost, cross-platform.

## Features

- **Optional API Keys**: no auth when `api_keys` is empty, OpenAI-style Bearer auth when configured
- **OpenAI Compatible**: Drop-in replacement for `/v1/chat/completions` and `/v1/models`
- **Tool Calling**: Full function calling support (OpenAI format)
- **Multiple Models**: Flash, Flash Thinking (20k+ char output), Pro, Auto, Lite
- **Thinking Depth**: Adjustable via `@think=N` suffix (0=deepest, 4=shallowest)
- **Web Search**: Built-in internet access (Gemini's native search)
- **Cross-Platform**: Pure Python, no dependencies beyond stdlib
- **Streaming**: SSE streaming support
- **Codex CLI**: Responses API (`/v1/responses`) for OpenAI Codex integration
- **Gemini CLI**: Google native API (`/v1beta/models`) for Gemini CLI compatibility
- **Web Admin Console**: Vue 3 + Naive UI dashboard for status, testing, config, and logs
- **Desktop Manager**: Windows manager for one-click start, stop, restart, opening Web UI, and viewing detailed logs
- **Vercel Ready**: Serverless entrypoint and one-click deploy button with environment-variable configuration

## Quick Start

```bash
python gemini_web2api.py
```

Server starts at `http://localhost:8081/v1`.

Open the Web Admin Console at `http://localhost:8081/admin`.

## Web Admin Console

![GeminiWeb2API admin console](docs/admin-console.png)

The admin console is built with Vue 3 + Naive UI and is served by the Python process from `/admin`.

| Page | What it does |
|------|--------------|
| Login | Default admin password is `sk-admin`; you can change it from Settings after signing in. |
| Overview | Shows service health, version, model count, local/LAN/public URLs, log size, cookie state, proxy state, and whether the built admin assets are ready. |
| Network | Gets local IP, public IP, location, ISP/ASN, and tests Gemini/Google connectivity. |
| Service Test | Sends requests to OpenAI Chat Completions, OpenAI Responses, Google `generateContent`, or Google `streamGenerateContent`; supports model selection, streaming toggle, response preview, and curl copy. |
| Settings | Edits `cookie_file`, `proxy`, `default_model`, `public_base_url`, and `empty_response_fallback`, then saves them back to `config.json`. |
| Logs | Reads `logs/gemini_web2api.log`, supports incremental refresh, pause/resume auto refresh, copy, clear view, and scroll-to-bottom. |

### Desktop Manager

On Windows, run `manager.pyw` or the packaged `GeminiWeb2API_Manager.exe` to manage the local service without a terminal.

- `Start`, `Stop`, and `Restart` control the background API process.
- `Open Web Admin Console` opens `http://127.0.0.1:{port}/admin`.
- `Open API URL` opens `http://127.0.0.1:{port}/v1`.
- The log panel tails the same `logs/gemini_web2api.log` file used by the Web Admin Console.

### Rebuild the Admin Console

Only needed when editing files under `web-admin/`:

```bash
cd web-admin
npm install
npm run build
```

The build output is written to `gemini_web2api/admin_static/` and is included by the PyInstaller specs.

## Client Configuration

### Cherry Studio / ChatBox / any OpenAI client

| Field | Value |
|-------|-------|
| Base URL | `http://localhost:8081/v1` |
| API Key | any `api_keys` value from `config.json`; anything if not configured |
| Model | `gemini-3.5-flash-thinking` |

### curl

```bash
curl http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-key" \
  -d '{"model":"gemini-3.5-flash","messages":[{"role":"user","content":"Hello!"}]}'
```

### OpenAI Python SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8081/v1", api_key="sk-your-key")
resp = client.chat.completions.create(
    model="gemini-3.5-flash-thinking",
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)
print(resp.choices[0].message.content)
```

### Gemini CLI

```bash
export GEMINI_API_KEY=none
export GOOGLE_GEMINI_BASE_URL=http://localhost:8081
gemini
```

Supports Google native API endpoints:
- `GET /v1beta/models` — list models
- `POST /v1beta/models/{model}:generateContent` — non-streaming
- `POST /v1beta/models/{model}:streamGenerateContent` — streaming (SSE)

## Available Models

| Model | Description | Output |
|-------|-------------|--------|
| `gemini-3.5-flash` | Fast general-purpose | ~12k chars |
| `gemini-3.5-flash-thinking` | Deep thinking, longest output | **~20k chars** |
| `gemini-3.5-flash-thinking-lite` | Adaptive thinking depth | ~15k chars |
| `gemini-3.1-pro` | Pro (needs cookie for real routing) | ~12k chars |
| `gemini-auto` | Auto model selection | varies |
| `gemini-flash-lite` | Lightweight fast | ~10k chars |

### Thinking Depth

Append `@think=N` to any model name:

```
gemini-3.5-flash-thinking@think=0   # deepest (default)
gemini-3.5-flash-thinking@think=2   # medium
gemini-3.5-flash-thinking@think=4   # shallowest
```

## Optional: Cookie for Pro

Anonymous access works for all models, but `gemini-3.1-pro` routes to Flash without authentication. To get real Pro routing, provide a cookie file:

```bash
python gemini_web2api.py --cookie-file cookie.txt
```

### How to get cookies

1. Open Chrome, go to [gemini.google.com](https://gemini.google.com) and sign in with any free Google account
2. Open DevTools (F12) → Application → Cookies → `https://gemini.google.com`
3. Copy these cookie values: `SID`, `HSID`, `SSID`, `APISID`, `SAPISID`, `__Secure-1PSID`
4. Create `cookie.txt` in this format:

```
SID=your_sid_value; HSID=your_hsid_value; SSID=your_ssid_value; APISID=your_apisid_value; SAPISID=your_sapisid_value; __Secure-1PSID=your_1psid_value
```

Or use the JSON format:
```json
{"cookie": "SID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SAPISID=xxx; __Secure-1PSID=xxx", "sapisid": "your_sapisid_value"}
```

**Alternative (browser extension)**: Use any "Export Cookies" extension to export cookies for `gemini.google.com` in Netscape format, then convert to the single-line format above.

No paid subscription needed — a free Google account is sufficient.

## Configuration

Create `config.json` in the same directory:

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
  "default_model": "gemini-3.5-flash",
  "public_base_url": null,
  "empty_response_fallback": "Upstream returned an empty response. Please adjust the prompt or try again.",
  "log_requests": true
}
```

When `api_keys` is `[]`, authentication is disabled. When one or more keys are set, `/v1/*` endpoints require `Authorization: Bearer <key>` or `x-api-key: <key>`.

## Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=ADMIN_PASSWORD,API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2ai-manage&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

This repository includes `api/index.py` and `vercel.json`, so Vercel can run it as a Python Serverless Function. `/`, `/admin`, `/admin/api/*`, `/v1/*`, and `/v1beta/*` are routed to the same handler.

### Before you deploy

1. Prepare a GitHub account and a Vercel account.
2. For a quick trial, you can leave all environment variables empty; anonymous Flash requests still work.
3. To protect your endpoint, prepare one or more API keys such as `sk-my-private-key`.
4. To improve real Pro routing for `gemini-3.1-pro`, prepare `GEMINI_COOKIE`. See the cookie section above.
5. If the Vercel region cannot reach `gemini.google.com` reliably, prepare an HTTP/HTTPS proxy and set `PROXY`.

### Option 1: one-click deploy

1. Click **Deploy with Vercel** above.
2. Vercel opens the new project import page. The repository defaults to `t479842598/gemini-web2api-manage`.
3. Keep the default Project Name if you like. Framework Preset can be `Other` or Vercel auto-detection.
4. Fill in Environment Variables only if needed. You can leave them empty for a first deployment.
5. Click **Deploy** and wait for the build to finish.
6. Open the Production domain from the Vercel project page.

### Option 2: deploy your fork

1. Fork this repository to your own GitHub account.
2. In Vercel, click **Add New... → Project**.
3. Select your forked repository and import it.
4. Keep Build & Output Settings as default; `vercel.json` handles routing.
5. Add the environment variables you need.
6. Click **Deploy**. Future GitHub pushes will trigger automatic redeploys.

### Option 3: deploy with Vercel CLI

```bash
npm i -g vercel
vercel login
vercel
vercel --prod
```

The first CLI run asks for project name, team, and whether to link an existing project. To add variables from CLI:

```bash
vercel env add API_KEYS production
vercel env add GEMINI_COOKIE production
vercel env add DEFAULT_MODEL production
vercel --prod
```

### Environment variables

| Name | Required | Example | Description |
|------|----------|---------|-------------|
| `ADMIN_PASSWORD` | No | `sk-admin` | Web Admin Console password. Defaults to `sk-admin`; change it in production. |
| `API_KEYS` | No | `sk-one,sk-two` | Comma-separated keys. Empty means no auth. Clients send `Authorization: Bearer <key>` or `x-api-key`. |
| `GEMINI_COOKIE` | No | `SID=...; HSID=...; ...` | Full Gemini cookie string. Use this for real Pro routing on serverless deployments where `cookie_file` is not available. |
| `DEFAULT_MODEL` | No | `gemini-3.5-flash-thinking` | Default model when the request omits `model`. |
| `PROXY` | No | `http://user:pass@host:port` | HTTP/HTTPS proxy used by upstream Gemini requests. Do not use SOCKS URLs here. |
| `PUBLIC_BASE_URL` | No | `https://your-project.vercel.app/v1` | Public URL displayed in the admin console. |
| `GEMINI_BL` | No | `boq_assistant-bard-web-server_...` | Gemini web build label. Usually leave the default. |
| `RETRY_ATTEMPTS` | No | `3` | Number of upstream retry attempts. |
| `RETRY_DELAY_SEC` | No | `2` | Delay between upstream retries. |
| `REQUEST_TIMEOUT_SEC` | No | `60` | Upstream request timeout. Keep it within your Vercel function duration. |
| `LOG_REQUESTS` | No | `true` | Enables serverless function logs. View them in Vercel Logs. |

### Recommended examples

Public trial without auth:

```text
DEFAULT_MODEL=gemini-3.5-flash-thinking
PUBLIC_BASE_URL=https://your-project.vercel.app/v1
LOG_REQUESTS=true
```

Private use with API key:

```text
API_KEYS=sk-your-private-key
ADMIN_PASSWORD=change-this-admin-password
DEFAULT_MODEL=gemini-3.5-flash-thinking
PUBLIC_BASE_URL=https://your-project.vercel.app/v1
```

Cookie and proxy:

```text
API_KEYS=sk-your-private-key
GEMINI_COOKIE=SID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SAPISID=xxx; __Secure-1PSID=xxx
PROXY=http://user:pass@proxy.example.com:8080
REQUEST_TIMEOUT_SEC=60
```

### Verify after deployment

Replace `your-project.vercel.app` with your domain:

```bash
curl https://your-project.vercel.app/
curl https://your-project.vercel.app/v1/models
curl https://your-project.vercel.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-private-key" \
  -d '{"model":"gemini-3.5-flash","messages":[{"role":"user","content":"hello"}]}'
```

If `API_KEYS` is not configured, remove the `Authorization` header. The Web Admin Console is available at:

```text
https://your-project.vercel.app/admin
```

OpenAI-compatible clients should use:

| Field | Value |
|-------|-------|
| Base URL | `https://your-project.vercel.app/v1` |
| API Key | any value from `API_KEYS`; anything if unset |
| Model | `gemini-3.5-flash-thinking` |

### Update a deployment

- If you deployed from GitHub, push code changes and Vercel will redeploy automatically.
- If you only changed environment variables, update them in Vercel Project Settings → Environment Variables, then redeploy Production from Deployments.
- If you changed the admin frontend locally, run `cd web-admin && npm run build`, then commit `gemini_web2api/admin_static/`.

### Troubleshooting

- `401 invalid api key`: `API_KEYS` is configured, but the client did not send `Authorization: Bearer <key>` or `x-api-key`.
- `upstream error` or timeout: the Vercel region may not reach Gemini reliably. Configure `PROXY` or increase `REQUEST_TIMEOUT_SEC`.
- Pro still behaves like Flash: `GEMINI_COOKIE` is missing, expired, or the account lacks the capability.
- `/admin` opens but logs are empty: Vercel logs live in the Vercel project Logs page; local log files are mainly for desktop and Docker runs.
- Streaming stops early: serverless functions have duration limits. Reduce request length or use local/Docker deployment for long streams.

### Vercel notes

- Avoid committing real cookies or API keys. Put secrets in Vercel Project Settings → Environment Variables.
- Vercel is serverless, not a long-running process. Each request is handled by a function invocation.
- Free-plan limits and regional network quality vary. For stable long streaming output, desktop manager or Docker is more controllable.

## Docker

```bash
cp config.example.json config.json
docker build -t gemini-web2ai-manage .
docker run -d --name gemini-web2ai-manage -p 8081:8081 -v ./config.json:/app/config.json gemini-web2ai-manage
```

Or use Docker Compose:

```bash
cp config.example.json config.json
docker compose up -d
```

To mount a cookie file:

```bash
docker run -d --name gemini-web2ai-manage -p 8081:8081 -v ./config.json:/app/config.json -v ./cookie.txt:/app/cookie.txt gemini-web2ai-manage
```

Set `"cookie_file": "/app/cookie.txt"` in `config.json`.

## Proxy

If you cannot access `gemini.google.com` directly (connection timeout), configure a proxy:

**Method 1: CLI argument**
```bash
python gemini_web2api.py --proxy http://127.0.0.1:7890
```

**Method 2: config.json**
```json
{"proxy": "http://127.0.0.1:7890"}
```

**Method 3: Environment variable** (auto-detected)
```bash
export HTTPS_PROXY=http://127.0.0.1:7890
python gemini_web2api.py
```

Works with Clash, V2Ray, Shadowsocks, or any HTTP proxy.

## Tool Calling

```python
resp = client.chat.completions.create(
    model="gemini-3.5-flash",
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a city",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        }
    }]
)
```

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)
- Network access to `gemini.google.com` (proxy/VPN may be needed in some regions)

## How It Works

This tool reverse-engineers Google Gemini's web StreamGenerate protocol. It sends requests to the same endpoint that the Gemini web app uses, converting between OpenAI's API format and Gemini's internal protobuf-like format.

The model selection is controlled by field `[79]` in the request payload, mapped from Gemini's frontend JavaScript source (`MODE_CATEGORY` enum).

## Acknowledgments

- [linux.do](https://linux.do) community
- Inspired by the open-source API proxy ecosystem

## License

MIT
