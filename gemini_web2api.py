#!/usr/bin/env python3
"""
gemini-web2api - Gemini Web to OpenAI API proxy.

Converts Google Gemini's web interface into an OpenAI-compatible API server.
Zero authentication required. Works on any platform (Windows/macOS/Linux).

Usage:
    pip install httpx
    python gemini_web2api.py [--port 8081] [--config config.json]

Client configuration (Cherry Studio, ChatBox, etc.):
    Base URL: http://localhost:8081/v1
    API Key: (anything or empty)

How it works:
    Sends requests directly to Gemini's public StreamGenerate endpoint.
    The backend does not verify authentication for basic text generation.
    Model selection via MODE_CATEGORY field [79] in the request payload.
    This is NOT a user-tier spoofing attack - the endpoint simply doesn't
    require auth for anonymous access.
"""
import json
import urllib.request
import urllib.parse
import time
import ssl
import sys
import uuid
import re
import os
import hashlib
import argparse
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from gemini_web2api.admin import admin_config_payload, admin_static_status, clear_admin_cookie, log_status, make_admin_cookie, network_diagnostics, read_admin_asset, read_admin_index, read_logs, save_config, service_urls, verify_admin_cookie, verify_admin_password

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

__version__ = "1.1.0"

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "port": 8081,
    "host": "0.0.0.0",
    "retry_attempts": 3,
    "retry_delay_sec": 2,
    "request_timeout_sec": 180,
    "gemini_bl": "boq_assistant-bard-web-server_20260525.09_p0",
    "default_model": "gemini-3.5-flash",
    "log_requests": True,
    "cookie_file": None,
    "proxy": None,
    "empty_response_fallback": "Upstream returned an empty response. Please adjust the prompt or try again.",
    "admin_password": "sk-admin",
}

CONFIG = dict(DEFAULT_CONFIG)

# ─── Models ──────────────────────────────────────────────────────────────────
# Mapping from JS source: MODE_CATEGORY enum (028-6eb337387583.js)
#   1=FAST, 2=THINKING, 3=PRO, 4=AUTO, 5=FAST_DYNAMIC_THINKING, 6=FLASH_LITE

MODELS = {
    "gemini-3.5-flash": {
        "mode": 1, "think": 4,
        "desc": "Fast general-purpose model",
    },
    "gemini-3.5-flash-thinking": {
        "mode": 2, "think": 0,
        "desc": "Deep thinking mode, longest output (~20k chars)",
    },
    "gemini-3.1-pro": {
        "mode": 3, "think": 4,
        "desc": "Pro model (requires cookie for real routing)",
    },
    "gemini-auto": {
        "mode": 4, "think": 4,
        "desc": "Auto model selection",
    },
    "gemini-3.5-flash-thinking-lite": {
        "mode": 5, "think": 0,
        "desc": "Dynamic thinking with adaptive depth",
    },
    "gemini-flash-lite": {
        "mode": 6, "think": 4,
        "desc": "Lightweight fast model",
    },
}

# ─── Utilities ───────────────────────────────────────────────────────────────

def log(msg: str):
    if CONFIG["log_requests"]:
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        sys.stderr.flush()


def load_cookie() -> tuple:
    """Load cookie from file. Returns (cookie_str, sapisid)."""
    cookie_file = CONFIG.get("cookie_file")
    if not cookie_file:
        return "", None
    if not os.path.exists(cookie_file):
        return "", None
    try:
        with open(cookie_file, "r") as f:
            content = f.read().strip()
        if content.startswith("{"):
            data = json.loads(content)
            cookie_str = data.get("cookie", "")
            sapisid = data.get("sapisid", "")
        else:
            cookie_str = content
            pairs = dict(p.split("=", 1) for p in cookie_str.split("; ") if "=" in p)
            sapisid = pairs.get("SAPISID", "")
        return cookie_str, sapisid if sapisid else None
    except Exception as e:
        log(f"Cookie load error: {e}")
        return "", None


def make_sapisidhash(sapisid: str) -> str:
    ts = int(time.time())
    h = hashlib.sha1(f"{ts} {sapisid} https://gemini.google.com".encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{h}"


# ─── Gemini Protocol ─────────────────────────────────────────────────────────

def gemini_stream_generate(prompt: str, model_id: int, think_mode: int) -> str:
    """Send prompt to Gemini StreamGenerate with retry."""
    inner = [None] * 80
    inner[0] = [prompt, 0, None, None, None, None, 0]
    inner[1] = ["en"]
    inner[2] = ["", "", "", None, None, None, None, None, None, ""]
    inner[6] = [0]
    inner[7] = 1
    inner[10] = 1
    inner[11] = 0
    inner[17] = [[think_mode]]
    inner[18] = 0
    inner[27] = 1
    inner[30] = [4]
    inner[41] = [2]
    inner[53] = 0
    inner[59] = str(uuid.uuid4())
    inner[61] = []
    inner[68] = 1
    inner[79] = model_id

    outer = [None, json.dumps(inner)]
    body = urllib.parse.urlencode({"f.req": json.dumps(outer)}).encode()
    reqid = int(time.time()) % 1000000
    url = (
        "https://gemini.google.com/_/BardChatUi/data/"
        "assistant.lamda.BardFrontendService/StreamGenerate"
        f"?bl={CONFIG['gemini_bl']}&hl=en&_reqid={reqid}&rt=c"
    )
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://gemini.google.com",
        "Referer": "https://gemini.google.com/app",
        "X-Same-Domain": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    cookie_str, sapisid = load_cookie()
    if cookie_str:
        headers["Cookie"] = cookie_str
    if sapisid:
        headers["Authorization"] = make_sapisidhash(sapisid)

    last_err = None
    for attempt in range(CONFIG["retry_attempts"]):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            ctx = ssl.create_default_context()
            proxy = CONFIG.get("proxy")
            if proxy:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({"http": proxy, "https": proxy}),
                    urllib.request.HTTPSHandler(context=ctx)
                )
                resp = opener.open(req, timeout=CONFIG["request_timeout_sec"])
            else:
                resp = urllib.request.urlopen(req, context=ctx, timeout=CONFIG["request_timeout_sec"])
            return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if attempt < CONFIG["retry_attempts"] - 1:
                log(f"Retry {attempt+1}/{CONFIG['retry_attempts']}: {e}")
                time.sleep(CONFIG["retry_delay_sec"])
    raise last_err


def gemini_stream_generate_iter(prompt: str, model_id: int, think_mode: int):
    """Send prompt and yield incremental text deltas using httpx streaming."""
    inner = [None] * 80
    inner[0] = [prompt, 0, None, None, None, None, 0]
    inner[1] = ["en"]
    inner[2] = ["", "", "", None, None, None, None, None, None, ""]
    inner[6] = [0]
    inner[7] = 1
    inner[10] = 1
    inner[11] = 0
    inner[17] = [[think_mode]]
    inner[18] = 0
    inner[27] = 1
    inner[30] = [4]
    inner[41] = [2]
    inner[53] = 0
    inner[59] = str(uuid.uuid4())
    inner[61] = []
    inner[68] = 1
    inner[79] = model_id

    outer = [None, json.dumps(inner)]
    body = urllib.parse.urlencode({"f.req": json.dumps(outer)})
    reqid = int(time.time()) % 1000000
    url = (
        "https://gemini.google.com/_/BardChatUi/data/"
        "assistant.lamda.BardFrontendService/StreamGenerate"
        f"?bl={CONFIG['gemini_bl']}&hl=en&_reqid={reqid}&rt=c"
    )
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://gemini.google.com",
        "Referer": "https://gemini.google.com/app",
        "X-Same-Domain": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    cookie_str, sapisid = load_cookie()
    if cookie_str:
        headers["Cookie"] = cookie_str
    if sapisid:
        headers["Authorization"] = make_sapisidhash(sapisid)

    proxy = CONFIG.get("proxy")

    if not HAS_HTTPX:
        # Fallback: non-streaming with urllib
        raw = gemini_stream_generate(prompt, model_id, think_mode)
        text = extract_response_text(raw)
        if text:
            yield text
        return

    prev_text = ""
    transport = httpx.HTTPTransport(proxy=proxy) if proxy else None
    with httpx.Client(transport=transport, timeout=CONFIG["request_timeout_sec"], verify=True) as client:
        with client.stream("POST", url, content=body, headers=headers) as resp:
            buf = ""
            for chunk in resp.iter_text():
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if '"wrb.fr"' not in line or len(line) < 200:
                        continue
                    try:
                        arr = json.loads(line)
                        inner_str = arr[0][2]
                        if not inner_str or len(inner_str) < 50:
                            continue
                        inner2 = json.loads(inner_str)
                        if isinstance(inner2, list) and len(inner2) > 4 and inner2[4]:
                            for part in inner2[4]:
                                if isinstance(part, list) and len(part) > 1 and part[1] and isinstance(part[1], list):
                                    for t in part[1]:
                                        if isinstance(t, str) and len(t) > len(prev_text):
                                            delta = t[len(prev_text):]
                                            delta = clean_gemini_text(delta)
                                            if delta:
                                                yield delta
                                            prev_text = t
                    except (json.JSONDecodeError, IndexError, TypeError):
                        pass


def collect_stream_text(prompt: str, model_id: int, think_mode: int) -> str:
    """Collect streaming deltas into one complete response."""
    if not HAS_HTTPX:
        return ""
    chunks = []
    for delta in gemini_stream_generate_iter(prompt, model_id, think_mode):
        if delta:
            chunks.append(delta)
    return "".join(chunks).strip()


def clean_gemini_text(text: str) -> str:
    """Remove internal code execution artifacts."""
    text = re.sub(
        r'```(?:python|javascript|text)\?code_(?:reference|stdout)&code_event_index=\d+\n.*?```\n?',
        '', text, flags=re.DOTALL
    )
    return text.strip()


def extract_response_text(raw: str) -> str:
    """Parse StreamGenerate response to extract final text."""
    texts = []
    for line in raw.split("\n"):
        if '"wrb.fr"' not in line or len(line) < 200:
            continue
        try:
            arr = json.loads(line)
            inner_str = arr[0][2]
            if not inner_str or len(inner_str) < 50:
                continue
            inner = json.loads(inner_str)
            if isinstance(inner, list) and len(inner) > 4 and inner[4]:
                for part in inner[4]:
                    if isinstance(part, list) and len(part) > 1 and part[1]:
                        if isinstance(part[1], list):
                            for t in part[1]:
                                if isinstance(t, str) and len(t) > 0:
                                    texts.append(t)
        except (json.JSONDecodeError, IndexError, TypeError):
            pass
    text = ""
    for t in reversed(texts):
        if t.strip():
            text = t
            break
    return clean_gemini_text(text)


# ─── OpenAI Format Helpers ───────────────────────────────────────────────────

def messages_to_prompt(messages: list, tools: list = None) -> str:
    """Convert OpenAI messages to prompt string."""
    parts = []
    if tools:
        tool_defs = []
        for tool in tools:
            fn = tool.get("function", tool) if tool.get("type") == "function" else tool
            tool_defs.append({
                "name": fn.get("name", tool.get("name", "")),
                "description": fn.get("description", tool.get("description", "")),
                "parameters": fn.get("parameters", tool.get("parameters", {})),
            })
        if tool_defs:
            parts.append(
                "[System instruction]: You have access to tools. "
                "To call a tool, respond with:\n"
                '```tool_call\n{"name": "func_name", "arguments": {...}}\n```\n'
                "Only use tool_call blocks when needed.\n\n"
                f"Available tools:\n{json.dumps(tool_defs, indent=2)}"
            )
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content
                if c.get("type") in ("text", "input_text")
            )
        if role == "system":
            parts.append(f"[System instruction]: {content}")
        elif role == "assistant":
            if msg.get("tool_calls"):
                tc_strs = []
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    tc_strs.append(
                        f'```tool_call\n{{"name": "{fn.get("name")}", '
                        f'"arguments": {fn.get("arguments", "{}")}}}\n```'
                    )
                parts.append(f"[Assistant]: {content or ''}\n" + "\n".join(tc_strs))
            else:
                parts.append(f"[Assistant]: {content}")
        elif role == "tool":
            parts.append(f"[Tool result for {msg.get('name', '')}]: {content}")
        else:
            parts.append(content if content else "")
    return "\n\n".join(p for p in parts if p)


def parse_tool_calls(text: str) -> tuple:
    """Extract tool_call blocks. Returns (clean_text, tool_calls_list)."""
    tool_calls = []
    pattern = r'```tool_call\s*\n(.*?)\n```'
    for match in re.findall(pattern, text, re.DOTALL):
        try:
            data = json.loads(match.strip())
            tool_calls.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": data["name"],
                    "arguments": json.dumps(data.get("arguments", {}), ensure_ascii=False),
                },
            })
        except (json.JSONDecodeError, KeyError):
            pass
    clean = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    return clean, tool_calls


def empty_response_fallback() -> str:
    return CONFIG.get("empty_response_fallback") or (
        "Upstream returned an empty response. Please adjust the prompt or try again."
    )


def extract_text_from_response_payload(payload) -> str:
    """Extract assistant text from OpenAI- or Gemini-shaped response payloads."""
    texts = []

    def add(value):
        if isinstance(value, str) and value:
            texts.append(value)
        elif isinstance(value, list):
            for item in value:
                add(item)
        elif isinstance(value, dict):
            add(value.get("text") or value.get("content"))

    if isinstance(payload, list):
        for item in payload:
            extracted = extract_text_from_response_payload(item)
            if extracted:
                texts.append(extracted)
        return "\n".join(t for t in texts if t.strip()).strip()

    if not isinstance(payload, dict):
        return ""

    source = payload.get("response") if isinstance(payload.get("response"), dict) else payload

    choices = source.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            msg = choice.get("message") or choice.get("delta") or {}
            if isinstance(msg, dict):
                add(msg.get("content"))

    candidates = source.get("candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content") or {}
            if isinstance(content, dict):
                parts = content.get("parts") or []
                for part in parts:
                    if isinstance(part, dict):
                        add(part.get("text"))
                    elif isinstance(part, str):
                        add(part)

    return "\n".join(t for t in texts if t.strip()).strip()


def normalize_generated_text(text: str) -> str:
    """Keep normal text, but unwrap JSON response objects that contain model text."""
    if not text:
        return ""
    if not isinstance(text, str):
        extracted = extract_text_from_response_payload(text)
        return extracted or ""
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return text
    try:
        payload = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return text
    extracted = extract_text_from_response_payload(payload)
    return extracted or ""


def chat_stream_chunk(cid: str, model_name: str, delta: dict, finish_reason=None) -> dict:
    return {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


# ─── HTTP Handler ────────────────────────────────────────────────────────────

class GeminiHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log(fmt % args)

    def send_json(self, data, status=200, headers=None):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str, status=200):
        self.send_bytes(html.encode("utf-8"), "text/html; charset=utf-8", status)

    def send_bytes(self, body: bytes, content_type: str, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def _admin_authorized(self):
        return verify_admin_cookie(CONFIG, self.headers.get("Cookie", ""))

    def _require_admin(self):
        if self._admin_authorized():
            return True
        self.send_json({"error": {"message": "admin login required"}}, 401)
        return False

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path in ("/admin", "/admin/"):
                self.send_html(read_admin_index())
            elif path == "/admin/api/auth":
                self.send_json({"authenticated": self._admin_authorized()})
            elif path == "/admin/api/status":
                if not self._require_admin():
                    return
                self._handle_admin_status()
            elif path == "/admin/api/logs":
                if not self._require_admin():
                    return
                self._handle_admin_logs(parsed.query)
            elif path == "/admin/api/network":
                if not self._require_admin():
                    return
                self.send_json(network_diagnostics(CONFIG))
            elif path.startswith("/admin/"):
                asset = read_admin_asset(path)
                if asset:
                    body, content_type = asset
                    self.send_bytes(body, content_type)
                else:
                    self.send_json({"error": "admin asset not found"}, 404)
            elif path == "/v1/models":
                self.send_json({"object": "list", "data": [
                    {"id": n, "object": "model", "created": 1700000000,
                     "owned_by": "google", "description": c["desc"]}
                    for n, c in MODELS.items()
                ]})
            elif path.startswith("/v1beta/models"):
                self._handle_google_models_list()
            elif path == "/":
                self.send_json({"status": "ok", "version": __version__,
                                "models": list(MODELS.keys())})
            else:
                self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            log(f"GET error: {e}")

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            if path == "/admin/api/login":
                self._handle_admin_login(body)
            elif path == "/admin/api/logout":
                self.send_json({"ok": True}, headers={"Set-Cookie": clear_admin_cookie()})
            elif path == "/admin/api/config":
                if not self._require_admin():
                    return
                self._handle_admin_config(body)
            elif path == "/v1/chat/completions":
                self.handle_chat(body)
            elif path == "/v1/responses":
                self.handle_responses(body)
            elif ":generateContent" in path:
                self._handle_google_generate(body, stream=False)
            elif ":streamGenerateContent" in path:
                self._handle_google_generate(body, stream=True)
            else:
                self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            log(f"POST error: {e}")
            try:
                self.send_json({"error": {"message": str(e)}}, 500)
            except:
                pass

    def _handle_admin_status(self):
        port = int(CONFIG.get("port") or self.server.server_address[1])
        models = [
            {"id": name, "description": cfg.get("desc", "")}
            for name, cfg in MODELS.items()
        ]
        config = admin_config_payload(CONFIG)
        config["empty_response_fallback"] = config["empty_response_fallback"] or empty_response_fallback()
        self.send_json({
            "ok": True,
            "version": __version__,
            "models": models,
            "config": config,
            "urls": service_urls(self.headers.get("Host", ""), port, config["public_base_url"]),
            "logs": log_status(),
            "admin_static": admin_static_status(),
        })

    def _handle_admin_logs(self, query: str):
        params = urllib.parse.parse_qs(query or "")
        offset = params.get("offset", [None])[0]
        tail = params.get("tail", [40000])[0]
        try:
            offset = int(offset) if offset is not None else None
        except ValueError:
            offset = None
        try:
            tail = int(tail)
        except (TypeError, ValueError):
            tail = 40000
        self.send_json(read_logs(offset=offset, tail=tail))

    def _handle_admin_login(self, body: bytes):
        try:
            req = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        if not verify_admin_password(CONFIG, req.get("password", "")):
            self.send_json({"error": {"message": "invalid admin password"}}, 401)
            return
        self.send_json({"ok": True}, headers={"Set-Cookie": make_admin_cookie(CONFIG)})

    def _handle_admin_config(self, body: bytes):
        try:
            req = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        try:
            updated = save_config(CONFIG, req)
        except OSError as e:
            self.send_json({"error": {"message": f"save config failed: {e}"}}, 500)
            return
        config = admin_config_payload(updated)
        config["empty_response_fallback"] = config["empty_response_fallback"] or empty_response_fallback()
        self.send_json({"ok": True, "config": config})

    def _resolve_model(self, model_name):
        think_override = None
        if "@think=" in model_name:
            model_name, think_str = model_name.rsplit("@think=", 1)
            think_override = int(think_str)
        cfg = MODELS.get(model_name)
        if not cfg:
            return None, None, None, f"Unknown model: {model_name}"
        return model_name, cfg["mode"], (think_override if think_override is not None else cfg["think"]), None

    def _call_gemini(self, prompt, model_id, think_mode, tools):
        raw = gemini_stream_generate(prompt, model_id, think_mode)
        text = normalize_generated_text(extract_response_text(raw))
        if not text:
            log("Empty non-stream parse; retrying with streaming collector")
            text = normalize_generated_text(collect_stream_text(prompt, model_id, think_mode))
        tool_calls = None
        if tools and text:
            text, tool_calls = parse_tool_calls(text)
        return text or "", tool_calls

    def handle_chat(self, body: bytes):
        req = json.loads(body)
        model_name, model_id, think_mode, err = self._resolve_model(
            req.get("model", CONFIG["default_model"]))
        if err:
            self.send_json({"error": {"message": err}}, 400)
            return

        tools = req.get("tools")
        prompt = messages_to_prompt(req.get("messages", []), tools)
        if not prompt.strip():
            self.send_json({"error": {"message": "empty prompt"}}, 400)
            return

        stream = req.get("stream", False)
        cid = f"chatcmpl-{uuid.uuid4().hex[:12]}"

        if stream and not tools:
            # True streaming: forward chunks as they arrive
            started = False
            emitted = False
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                started = True
                chunk = chat_stream_chunk(cid, model_name, {"role": "assistant"})
                self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
                for delta_text in gemini_stream_generate_iter(prompt, model_id, think_mode):
                    if not delta_text:
                        continue
                    emitted = True
                    chunk = chat_stream_chunk(cid, model_name, {"content": delta_text})
                    self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                    self.wfile.flush()
                if not emitted:
                    chunk = chat_stream_chunk(cid, model_name, {"content": empty_response_fallback()})
                    self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                chunk = chat_stream_chunk(cid, model_name, {}, "stop")
                self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                log(f"Stream error: {e}")
                if started:
                    try:
                        if not emitted:
                            chunk = chat_stream_chunk(cid, model_name, {"content": empty_response_fallback()})
                            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                        chunk = chat_stream_chunk(cid, model_name, {}, "stop")
                        self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        pass
            return

        # Non-streaming (or tool calling which needs full response)
        try:
            text, tool_calls = self._call_gemini(prompt, model_id, think_mode, tools)
        except Exception as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return

        msg = {"role": "assistant", "content": text or None}
        if not text and not tool_calls:
            text = empty_response_fallback()
            msg["content"] = text
        if tool_calls:
            msg["tool_calls"] = tool_calls
        finish = "tool_calls" if tool_calls else "stop"

        if stream:
            # Stream mode with tools: send as single chunk (need full parse for tool_calls)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            chunk = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()),
                     "model": model_name, "choices": [{"index": 0, "delta": msg, "finish_reason": finish}]}
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            self.send_json({
                "id": cid, "object": "chat.completion", "created": int(time.time()),
                "model": model_name,
                "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                "usage": {"prompt_tokens": len(prompt)//4, "completion_tokens": len(text)//4,
                          "total_tokens": (len(prompt)+len(text))//4},
            })

    def handle_responses(self, body: bytes):
        """OpenAI Responses API for Codex CLI compatibility."""
        req = json.loads(body)
        model_name, model_id, think_mode, err = self._resolve_model(
            req.get("model", CONFIG["default_model"]))
        if err:
            self.send_json({"error": {"message": err}}, 400)
            return

        input_items = req.get("input", [])
        tools = req.get("tools")

        messages = []
        if req.get("instructions"):
            messages.append({"role": "system", "content": req["instructions"]})
        if isinstance(input_items, str):
            messages.append({"role": "user", "content": input_items})
        elif isinstance(input_items, list):
            for item in input_items:
                if isinstance(item, str):
                    messages.append({"role": "user", "content": item})
                elif isinstance(item, dict):
                    if item.get("type") == "function_call_output":
                        messages.append({"role": "tool", "tool_call_id": item.get("call_id", ""),
                                         "name": item.get("name", ""), "content": item.get("output", "")})
                    elif item.get("role") == "assistant" or (item.get("type") == "message" and item.get("role") == "assistant"):
                        cp = item.get("content", [])
                        text_acc, tc_list = "", []
                        if isinstance(cp, list):
                            for c in cp:
                                if isinstance(c, dict):
                                    if c.get("type") == "output_text": text_acc += c.get("text", "")
                                    elif c.get("type") == "function_call": tc_list.append(c)
                        elif isinstance(cp, str):
                            text_acc = cp
                        m = {"role": "assistant", "content": text_acc or None}
                        if tc_list:
                            m["tool_calls"] = [{"id": tc.get("call_id", f"call_{i}"), "type": "function",
                                                "function": {"name": tc.get("name",""), "arguments": tc.get("arguments","{}")}}
                                               for i, tc in enumerate(tc_list)]
                        messages.append(m)
                    else:
                        role = item.get("role", "user")
                        content = item.get("content", "")
                        if isinstance(content, list):
                            content = " ".join(c.get("text", "") for c in content if c.get("type") in ("text", "input_text"))
                        messages.append({"role": role, "content": content})

        if tools:
            tools = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters", {})}}
                     if t.get("type") == "function" and "function" not in t else t for t in tools]

        prompt = messages_to_prompt(messages, tools)
        if not prompt.strip():
            self.send_json({"error": {"message": "empty input"}}, 400)
            return

        try:
            text, tool_calls = self._call_gemini(prompt, model_id, think_mode, tools)
        except Exception as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return

        if not text and not tool_calls:
            text = empty_response_fallback()

        rid = f"resp_{uuid.uuid4().hex[:16]}"
        mid = f"msg_{uuid.uuid4().hex[:12]}"
        output = []
        if tool_calls:
            for tc in tool_calls:
                output.append({"type": "function_call", "id": tc["id"], "call_id": tc["id"],
                               "name": tc["function"]["name"], "arguments": tc["function"]["arguments"], "status": "completed"})
        if text or not tool_calls:
            output.append({"type": "message", "id": mid, "role": "assistant", "status": "completed",
                           "content": [{"type": "output_text", "text": text or "", "annotations": []}]})

        if req.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            ev = {"type": "response.created", "response": {"id": rid, "object": "response", "status": "in_progress", "model": model_name, "output": []}}
            self.wfile.write(f"event: response.created\ndata: {json.dumps(ev)}\n\n".encode())
            for item in output:
                if item["type"] == "function_call":
                    ev = {"type": "response.function_call_arguments.done", "item_id": item["id"], "call_id": item["call_id"], "name": item["name"], "arguments": item["arguments"]}
                    self.wfile.write(f"event: response.function_call_arguments.done\ndata: {json.dumps(ev)}\n\n".encode())
                elif item["type"] == "message":
                    for ci, cp in enumerate(item["content"]):
                        ev = {"type": "response.output_text.done", "item_id": item["id"], "content_index": ci, "text": cp["text"]}
                        self.wfile.write(f"event: response.output_text.done\ndata: {json.dumps(ev)}\n\n".encode())
            resp_obj = {"id": rid, "object": "response", "status": "completed", "model": model_name, "output": output,
                        "usage": {"input_tokens": len(prompt)//4, "output_tokens": len(text)//4, "total_tokens": (len(prompt)+len(text))//4}}
            self.wfile.write(f"event: response.completed\ndata: {json.dumps({'type': 'response.completed', 'response': resp_obj})}\n\n".encode())
            self.wfile.flush()
        else:
            self.send_json({"id": rid, "object": "response", "created_at": int(time.time()), "status": "completed",
                            "model": model_name, "output": output,
                            "usage": {"input_tokens": len(prompt)//4, "output_tokens": len(text)//4, "total_tokens": (len(prompt)+len(text))//4}})


    # ─── Google Native API (Gemini CLI compatible) ────────────────────────────

    def _parse_google_model_from_path(self):
        """Extract model name from /v1beta/models/{model}:method path."""
        m = re.match(r'/v1beta/models/([^:?]+)', self.path)
        if m:
            return m.group(1)
        return None

    def _handle_google_models_list(self):
        """GET /v1beta/models — Google AI format model list."""
        models = []
        for name, cfg in MODELS.items():
            models.append({
                "name": f"models/{name}",
                "displayName": name,
                "description": cfg["desc"],
                "supportedGenerationMethods": ["generateContent", "streamGenerateContent"],
            })
        self.send_json({"models": models})

    def _google_contents_to_prompt(self, req: dict) -> str:
        """Convert Google API contents format to prompt string."""
        parts = []
        sys_inst = req.get("systemInstruction")
        if sys_inst:
            sys_parts = sys_inst.get("parts", [])
            sys_text = " ".join(p.get("text", "") for p in sys_parts if p.get("text"))
            if sys_text:
                parts.append(f"[System instruction]: {sys_text}")

        for content in req.get("contents", []):
            role = content.get("role", "user")
            text_parts = []
            for p in content.get("parts", []):
                if p.get("text"):
                    text_parts.append(p["text"])
            text = " ".join(text_parts)
            if role == "model":
                parts.append(f"[Assistant]: {text}")
            else:
                parts.append(text)
        return "\n\n".join(p for p in parts if p)

    def _handle_google_generate(self, body: bytes, stream: bool):
        """Handle Google native generateContent / streamGenerateContent."""
        req = json.loads(body)
        model_name = self._parse_google_model_from_path()
        if not model_name:
            self.send_json({"error": {"message": "model not specified in path"}}, 400)
            return

        model_name, model_id, think_mode, err = self._resolve_model(model_name)
        if err:
            self.send_json({"error": {"message": err}}, 400)
            return

        prompt = self._google_contents_to_prompt(req)
        if not prompt.strip():
            self.send_json({"error": {"message": "empty content"}}, 400)
            return

        try:
            text, _ = self._call_gemini(prompt, model_id, think_mode, None)
        except Exception as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return

        candidate = {
            "content": {"parts": [{"text": text or ""}], "role": "model"},
            "finishReason": "STOP",
            "index": 0,
        }
        usage = {
            "promptTokenCount": len(prompt) // 4,
            "candidatesTokenCount": len(text) // 4,
            "totalTokenCount": (len(prompt) + len(text)) // 4,
        }
        response_obj = {
            "candidates": [candidate],
            "usageMetadata": usage,
            "modelVersion": model_name,
        }

        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(f"data: {json.dumps(response_obj)}\n\n".encode())
            self.wfile.flush()
        else:
            self.send_json(response_obj)


# ─── Main ────────────────────────────────────────────────────────────────────

def load_config(path: str):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            CONFIG.update(json.load(f))
        log(f"Config loaded: {path}")


def main():
    parser = argparse.ArgumentParser(description="Gemini Web to OpenAI API")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--cookie-file", type=str, default=None, help="Path to cookie file")
    parser.add_argument("--proxy", type=str, default=None, help="HTTP proxy, e.g. http://127.0.0.1:7890")
    parser.add_argument("--version", action="version", version=f"gemini-web2api {__version__}")
    args = parser.parse_args()

    config_path = args.config or os.environ.get("GEMINI_WEB2API_CONFIG")
    if not config_path:
        for p in ["./config.json", os.path.expanduser("~/.config/gemini-web2api/config.json")]:
            if os.path.exists(p):
                config_path = p
                break
    load_config(config_path)

    if args.port:
        CONFIG["port"] = args.port
    if args.cookie_file:
        CONFIG["cookie_file"] = args.cookie_file
    if args.proxy:
        CONFIG["proxy"] = args.proxy

    class ThreadedServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    port = CONFIG["port"]
    server = ThreadedServer((CONFIG["host"], port), GeminiHandler)
    print(f"gemini-web2api v{__version__}")
    print(f"  Listening: http://0.0.0.0:{port}")
    print(f"  Base URL:  http://localhost:{port}/v1")
    print(f"  Admin:     http://localhost:{port}/admin")
    print(f"  Models:    {', '.join(MODELS.keys())}")
    print(f"  Cookie:    {'yes (' + CONFIG['cookie_file'] + ')' if CONFIG.get('cookie_file') else 'none (anonymous)'}")
    print(f"  Proxy:     {CONFIG.get('proxy') or 'none (uses system env HTTP_PROXY/HTTPS_PROXY)'}")
    print(f"  Retry:     {CONFIG['retry_attempts']}x / {CONFIG['retry_delay_sec']}s")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
