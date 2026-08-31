"""Extended HTTP server for gemini-web2api-manage.

Inherits the upstream GeminiHandler and adds admin console routes
(/admin, /admin/api/*) before falling back to upstream behavior.
"""
import json
import re
import time
from urllib.parse import urlparse

from .config import CONFIG
from . import __version__
from . import protocol
from .admin import (
    admin_config_payload,
    admin_static_status,
    clear_admin_cookie,
    delete_upload,
    list_uploads,
    log_status,
    make_admin_cookie,
    network_diagnostics,
    read_admin_asset,
    read_admin_index,
    read_logs,
    read_upload_content,
    save_config,
    save_upload,
    service_urls,
    verify_admin_cookie,
    verify_admin_password,
)
from .stats import (
    CapturingWriter,
    endpoint_from_path,
    mask_key,
    parse_captured,
    recorder,
)
from .socks_bridge import apply_proxy_bridge

from gemini_web2api.server import GeminiHandler as UpstreamGeminiHandler
from gemini_web2api.server import ThreadedServer as UpstreamThreadedServer
from gemini_web2api.models import MODELS, resolve_model


class ThreadedServer(UpstreamThreadedServer):
    """上游 ThreadedServer + 跳过 `server_bind()` 里的反向 DNS。

    CPython 的 `HTTPServer.server_bind()` 会调 `socket.getfqdn(host)` 取服务名；
    当 host 为 `0.0.0.0`（默认配置）时这是一次必然超时的反向查询 —— 实测本机
    耗时正好 30.0 秒，表现为“启动后 30 秒内端口不监听、探活全部失败”。
    该服务名仅用于日志，对功能无用，这里直接给个不查网的实现。
    """

    def server_bind(self):
        import socket as _sock
        _orig = _sock.getfqdn
        _sock.getfqdn = lambda host="": host or "localhost"
        try:
            super().server_bind()
        finally:
            _sock.getfqdn = _orig


# 只改每行 JSON 里第一次出现的顶层 "model": "..."（它在 choices 之前），
# 因此不会误改 assistant 文本内容里碰巧出现的同名字串。
_MODEL_FIELD_RE = re.compile(r'("model"[ \t]*:[ \t]*)(?:"(?:[^"\\]|\\.)*"|null)')

_GENERATION_OBJECTS = {"chat.completion", "chat.completion.chunk",
                       "response", "text-completion"}


def _estimate_usage(prompt_chars: int, response_chars: int) -> dict:
    """估算 token 用量（官网响应不提供真实计数，已 2026-08-31 实测确认）。

    修掉的缺陷：上游用 `len(text)//4`，导致单个字符的回答被算成 0
    completion tokens（生产实测复现：回答 "9" → completion_tokens: 0）。
    这里改为向上取整且非空至少 1，空回答仍为 0。
    """
    def est(n):
        n = max(0, int(n or 0))
        return 0 if n == 0 else max(1, -(-n // 4))
    p, c = est(prompt_chars), est(response_chars)
    return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}


def _is_generation_response(data) -> bool:
    """区分 OpenAI/Google 生成响应与管理台自身的 JSON，后者不得被改。"""
    if not isinstance(data, dict):
        return False
    if data.get("object") in _GENERATION_OBJECTS:
        return True
    # Google generateContent / streamGenerateContent 形态
    return "candidates" in data or "usageMetadata" in data


class _SseModelRewriter:
    """包装 wfile，把 SSE data 行里的 `model` 改写成官网回报的真实服务模型。

    规则：**至多暂存一次写**。首块（role delta）发出时元数据还未就绪，
    先暂存；下一次写时元数据已可用，再把暂存块改写后一并落盘。
    因此不会丢字节、不会乱序；异常路径由 protocol.generate_stream 的
    finally 与本类的 finish() 强制 flush。
    """

    def __init__(self, raw):
        self.original = raw
        self._pending = None

    # -- 内部 ---------------------------------------------------------------
    def _enabled(self) -> bool:
        return bool(CONFIG.get("expose_served_model", True))

    def _served(self):
        if not self._enabled():
            return None
        return (protocol.get_meta() or {}).get("served_model")

    def _rewrite(self, data):
        served = self._served()
        if not served or isinstance(data, str):
            return data
        try:
            text = data.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return data
        new = _MODEL_FIELD_RE.sub(
            lambda m: m.group(1) + json.dumps(served, ensure_ascii=False),
            text, count=1)
        return new.encode("utf-8")

    def _emit(self, data):
        out = self._rewrite(data)
        self.original.write(out)
        self.original.flush()
        return len(out)

    # -- 文件对象接口 --------------------------------------------------------
    def write(self, data):
        try:
            if self._pending is not None:
                held, self._pending = self._pending, None
                self._emit(held)
            if self._served() or not self._enabled():
                return self._emit(data)
            self._pending = data
            return len(data)
        finally:
            # 无论是否暂存，都让底层 flush 一次，保持与原来一致的行为
            try:
                self.original.flush()
            except Exception:
                pass

    def flush(self):
        self.original.flush()

    def finish(self):
        """强制落盘暂存块（流结束 / 异常 / 恢复 wfile 前调用）。"""
        if self._pending is not None:
            held, self._pending = self._pending, None
            try:
                self._emit(held)
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self.original, name)


class GeminiHandler(UpstreamGeminiHandler):
    """Extends the upstream handler with admin console routes."""

    # ── 生成响应增强（spec 03-01 F-05/F-06/F-08）─────────────────────

    def _enrich_generation(self, data):
        """把官网回报却被上游丢弃的元数据注入生成响应。

        只新增字段、不改已有字段语义（除把 model 换为真实服务模型）。
        """
        try:
            meta = protocol.get_meta() or {}
            served = meta.get("served_model")
            if (CONFIG.get("expose_served_model", True) and served
                    and data.get("model")):
                data["requested_model"] = data["model"]
                data["model"] = served
                data["served_model"] = served
            for src, dst in (("conversation_id", "gemini_conversation_id"),
                             ("response_id", "gemini_response_id"),
                             ("region", "gemini_region"),
                             ("region_code", "gemini_region_code")):
                if meta.get(src):
                    data[dst] = meta[src]
            # usage 修正：仅在我们能拿到字符数时重算，否则保留上游值
            if "prompt_chars" in meta and isinstance(data.get("usage"), dict):
                data["usage"].update(
                    _estimate_usage(meta.get("prompt_chars"),
                                    meta.get("response_chars")))
            um = data.get("usageMetadata")
            if "prompt_chars" in meta and isinstance(um, dict):
                est = _estimate_usage(meta.get("prompt_chars"),
                                      meta.get("response_chars"))
                um["promptTokenCount"] = est["prompt_tokens"]
                um["candidatesTokenCount"] = est["completion_tokens"]
                um["totalTokenCount"] = est["total_tokens"]
        except Exception:
            # 增强失败绝不影响响应发出
            pass
        return data

    def _start_sse(self):
        """上游发完 SSE 头后，把 wfile 换为模型名改写包装器。

        注意包装顺序：此时 self.wfile 已被 `_run_upstream_post` 换成了
        CapturingWriter，包在它上面意味着统计记录的也是客户端实际收到的字节。
        """
        super()._start_sse()
        if not CONFIG.get("expose_served_model", True):
            return
        writer = _SseModelRewriter(self.wfile)
        self.wfile = writer
        protocol.set_sse_writer(writer)

    def send_json(self, data, status=200, headers=None):
        """Send JSON response; optional extra response headers (e.g. Set-Cookie)."""
        if _is_generation_response(data):
            data = self._enrich_generation(data)
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

    def _empty_response_fallback(self) -> str:
        return CONFIG.get("empty_response_fallback") or (
            "Gemini 返回了空内容。可能原因：Cookie 失效、内容被安全策略拦截、"
            "上下文过长或当前模型暂不可用。请查看管理台日志中的空响应诊断后重试。"
        )

    # ─── Admin auth ────────────────────────────────────────────────────────

    def _admin_authorized(self):
        return verify_admin_cookie(CONFIG, self.headers.get("Cookie", ""))

    def _require_admin(self):
        if self._admin_authorized():
            return True
        self.send_json({"error": {"message": "admin login required"}}, 401)
        return False

    # ─── Route dispatch override ──────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            # 无鉴权探活端点（部署健康检查 / 排障用）
            if path == "/health":
                from gemini_web2api.gemini import HAS_HTTPX
                self.send_json({
                    "status": "ok",
                    "version": __version__,
                    "models": len(MODELS),
                    "gemini_bl": CONFIG.get("gemini_bl"),
                    "gemini_base_url": CONFIG.get("gemini_base_url")
                        or "https://gemini.google.com",
                    "cookie_configured": bool(CONFIG.get("cookie_file")),
                    "cookie_files": len(CONFIG.get("cookie_files") or []),
                    "streaming": bool(HAS_HTTPX),
                    "proxy": CONFIG.get("proxy") or None,
                    "default_model": CONFIG.get("default_model"),
                    "expose_served_model": bool(
                        CONFIG.get("expose_served_model", True)),
                })
                return

            # Admin routes have priority
            if path in ("/admin", "/admin/"):
                self.send_html(read_admin_index())
                return
            if path == "/admin/api/auth":
                self.send_json({"authenticated": self._admin_authorized()})
                return
            if path == "/admin/api/status":
                if not self._require_admin():
                    return
                self._handle_admin_status()
                return
            if path == "/admin/api/logs":
                if not self._require_admin():
                    return
                self._handle_admin_logs(parsed.query)
                return
            if path == "/admin/api/network":
                if not self._require_admin():
                    return
                self.send_json(network_diagnostics(CONFIG))
                return
            if path == "/admin/api/stats":
                if not self._require_admin():
                    return
                self._handle_admin_stats(parsed.query)
                return
            if path == "/admin/api/files" or path.startswith("/admin/api/files/"):
                if not self._require_admin():
                    return
                self._handle_admin_files(parsed.query)
                return
            if path.startswith("/admin/"):
                if path.startswith("/admin/api/"):
                    self.send_json({"error": "admin api not found"}, 404)
                    return
                asset = read_admin_asset(path)
                if asset:
                    body, content_type = asset
                    self.send_bytes(body, content_type)
                else:
                    # SPA fallback: client-side routes (/admin/login, /admin/dashboard ...)
                    self.send_html(read_admin_index())
                return
            if path == "/":
                self.send_response(302)
                self.send_header("Location", "/admin")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            # Fall through to upstream handler
            super().do_GET()

        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            # Only read the body for admin routes. For all other paths we must
            # leave the stream untouched so the upstream handler can read it
            # itself — reading here would consume the body and make upstream
            # see an empty payload (400 "invalid JSON").
            if path in ("/admin/api/login", "/admin/api/logout", "/admin/api/config", "/admin/api/files"):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b""

                if path == "/admin/api/login":
                    self._handle_admin_login(body)
                    return
                if path == "/admin/api/logout":
                    self.send_json(
                        {"ok": True},
                        headers={"Set-Cookie": clear_admin_cookie()},
                    )
                    return
                # /admin/api/config or /admin/api/files
                if not self._require_admin():
                    return
                if path == "/admin/api/files":
                    self._handle_admin_upload(body)
                else:
                    self._handle_admin_config(body)
                return

            # Fall through to upstream handler (body not yet consumed)
            self._run_upstream_post()
            return

        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            from gemini_web2api.gemini import log
            log(f"Manage POST error: {e}")
            try:
                self.send_json({"error": {"message": str(e)}}, 500)
            except Exception:
                pass

    # ─── Admin API handlers ───────────────────────────────────────────────

    def do_DELETE(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/admin/api/files":
                if not self._require_admin():
                    return
                self._handle_admin_file_delete(parsed.query)
                return
            self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle_admin_files(self, query: str):
        from urllib.parse import parse_qs
        params = parse_qs(query or "")
        name = params.get("name", [None])[0]
        if name:
            try:
                self.send_json(read_upload_content(name))
            except (ValueError, FileNotFoundError) as e:
                self.send_json({"error": {"message": str(e)}}, 400)
            return
        self.send_json(list_uploads())

    def _handle_admin_upload(self, body: bytes):
        import base64
        req = self._parse_body(body)
        if req is None:
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        name = str(req.get("name") or "").strip()
        content_b64 = req.get("content") or ""
        try:
            content = base64.b64decode(content_b64) if content_b64 else b""
            self.send_json(save_upload(name, content))
        except Exception as e:
            self.send_json({"error": {"message": str(e)}}, 400)

    def _handle_admin_file_delete(self, query: str):
        from urllib.parse import parse_qs
        params = parse_qs(query or "")
        name = params.get("name", [None])[0]
        if not name:
            self.send_json({"error": {"message": "name required"}}, 400)
            return
        try:
            self.send_json(delete_upload(name))
        except (ValueError, FileNotFoundError) as e:
            self.send_json({"error": {"message": str(e)}}, 400)

    def _handle_admin_stats(self, query: str):
        from urllib.parse import parse_qs
        params = parse_qs(query or "")
        range_key = params.get("range", ["7d"])[0]
        self.send_json(recorder.query_stats(range_key))

    def _request_api_key(self):
        key = None
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:]
        if not key:
            key = self.headers.get("x-api-key") or self.headers.get("x-goog-api-key")
        if not key:
            q = urlparse(self.path).query
            for pair in q.split("&"):
                if pair.startswith("key="):
                    key = pair[4:]
                    break
        return mask_key(key or "")

    def _run_upstream_post(self):
        """Run the upstream POST handler while capturing response stats for
        /v1 generate calls (chat / responses / google)."""
        is_call = self.path.startswith("/v1") or self.path.startswith("/v1beta")
        if not is_call or not CONFIG.get("log_requests", True):
            super().do_POST()
            return
        started = time.time()
        capture = CapturingWriter(self.wfile)
        self.wfile = capture
        finished = False
        outcome = {"ok": True}

        def finish():
            nonlocal finished
            if finished:
                return
            finished = True
            # 先强制落盘 SSE 改写器里可能暂存的最后一块，再恢复 wfile，
            # 否则暂存块会随包装器一起被丢弃。
            writer = protocol.get_sse_writer()
            if writer is not None:
                try:
                    writer.finish()
                except Exception:
                    pass
                protocol.set_sse_writer(None)
            self.wfile = capture.original
            try:
                info = parse_captured(bytes(capture.buffer))
                recorder.record(
                    endpoint=endpoint_from_path(self.path),
                    model=info.get("model"),
                    api_key=self._request_api_key(),
                    success=outcome["ok"] and info.get("ok", True),
                    duration_ms=int((time.time() - started) * 1000),
                    usage=info.get("usage") or {},
                )
            except Exception:
                pass

        try:
            super().do_POST()
        except (BrokenPipeError, ConnectionResetError):
            outcome["ok"] = False
            finish()
            raise
        except Exception:
            outcome["ok"] = False
            finish()
            raise
        finally:
            finish()

    def _handle_admin_status(self):
        port = int(CONFIG.get("port") or self.server.server_address[1])
        models = [
            {"id": name, "description": cfg.get("desc", "")}
            for name, cfg in MODELS.items()
        ]
        config = admin_config_payload(CONFIG)
        config["empty_response_fallback"] = (
            config["empty_response_fallback"] or self._empty_response_fallback()
        )
        self.send_json({
            "ok": True,
            "version": __version__,
            "models": models,
            "config": config,
            "last_generation": protocol.last_meta(),
            "urls": service_urls(
                self.headers.get("Host", ""),
                port,
                config["public_base_url"],
            ),
            "logs": log_status(),
            "admin_static": admin_static_status(),
        })

    def _handle_admin_logs(self, query: str):
        from urllib.parse import parse_qs
        params = parse_qs(query or "")
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
        req = self._parse_body(body)
        if req is None:
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        if not verify_admin_password(CONFIG, req.get("password", "")):
            self.send_json({"error": {"message": "invalid admin password"}}, 401)
            return
        self.send_json(
            {"ok": True},
            headers={"Set-Cookie": make_admin_cookie(CONFIG)},
        )

    def _handle_admin_config(self, body: bytes):
        req = self._parse_body(body)
        if req is None:
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        try:
            updated = save_config(CONFIG, req)
        except OSError as e:
            self.send_json(
                {"error": {"message": f"save config failed: {e}"}}, 500
            )
            return
        apply_proxy_bridge(CONFIG)
        config = admin_config_payload(CONFIG)
        config["empty_response_fallback"] = (
            config["empty_response_fallback"] or self._empty_response_fallback()
        )
        self.send_json({"ok": True, "config": config})
