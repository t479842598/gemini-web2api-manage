# gemini-web2api

<p align="center">
  <img src="logo.png" width="200" alt="gemini-web2api logo">
</p>

[中文文档](README_CN.md)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2api&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

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
| Overview | Shows service health, version, model count, local/LAN/public URLs, log size, cookie state, proxy state, and whether the built admin assets are ready. |
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

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage&env=API_KEYS,GEMINI_COOKIE,DEFAULT_MODEL,PROXY,PUBLIC_BASE_URL&envDescription=Optional%20runtime%20settings%20for%20gemini-web2api&envLink=https%3A%2F%2Fgithub.com%2Ft479842598%2Fgemini-web2api-manage%23vercel)

This repository includes `api/index.py` and `vercel.json`, so Vercel can run it as a Python Serverless Function. `/`, `/admin`, `/admin/api/*`, `/v1/*`, and `/v1beta/*` are routed to the same handler.

### One-click deploy

1. Click **Deploy with Vercel**.
2. Import the repository into your Vercel account. If you deploy from your own fork, replace the button repository URL with your fork URL.
3. Fill in any environment variables you need. All variables below are optional unless you want API-key auth or authenticated Gemini cookies.
4. Deploy, then use `https://your-project.vercel.app/v1` as the OpenAI-compatible Base URL and `https://your-project.vercel.app/admin` as the Web Admin Console.

### Environment variables

| Name | Required | Example | Description |
|------|----------|---------|-------------|
| `API_KEYS` | No | `sk-one,sk-two` | Comma-separated keys. Empty means no auth. Clients send `Authorization: Bearer <key>` or `x-api-key`. |
| `GEMINI_COOKIE` | No | `SID=...; HSID=...; ...` | Full Gemini cookie string. Use this for real Pro routing on serverless deployments where `cookie_file` is not available. |
| `DEFAULT_MODEL` | No | `gemini-3.5-flash-thinking` | Default model when the request omits `model`. |
| `PROXY` | No | `http://user:pass@host:port` | HTTP/HTTPS proxy used by upstream Gemini requests. |
| `PUBLIC_BASE_URL` | No | `https://your-project.vercel.app/v1` | Public URL displayed in the admin console. |
| `GEMINI_BL` | No | `boq_assistant-bard-web-server_...` | Gemini web build label. Usually leave the default. |
| `RETRY_ATTEMPTS` | No | `3` | Number of upstream retry attempts. |
| `RETRY_DELAY_SEC` | No | `2` | Delay between upstream retries. |
| `REQUEST_TIMEOUT_SEC` | No | `60` | Upstream request timeout. Keep it within your Vercel function duration. |
| `LOG_REQUESTS` | No | `true` | Enables serverless function logs. View them in Vercel Logs. |

### Vercel notes

- Vercel deployments are serverless. Long streaming responses are limited by your Vercel plan and function duration.
- The Web Admin Console can view status and test requests, but serverless logs live in Vercel Logs; local `logs/gemini_web2api.log` is mainly for desktop/Docker runs.
- Avoid committing real cookies or API keys. Put secrets in Vercel Project Settings → Environment Variables.

## Docker

```bash
cp config.example.json config.json
docker build -t gemini-web2api .
docker run -d --name gemini-web2api -p 8081:8081 -v ./config.json:/app/config.json gemini-web2api
```

Or use Docker Compose:

```bash
cp config.example.json config.json
docker compose up -d
```

To mount a cookie file:

```bash
docker run -d --name gemini-web2api -p 8081:8081 -v ./config.json:/app/config.json -v ./cookie.txt:/app/cookie.txt gemini-web2api
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
