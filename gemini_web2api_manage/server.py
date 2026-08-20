"""Extended HTTP server for gemini-web2api-manage.

Inherits the upstream GeminiHandler and adds admin console routes
(/admin, /admin/api/*) before falling back to upstream behavior.
"""
import json
import time
from urllib.parse import urlparse

from .config import CONFIG
from . import __version__
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
from gemini_web2api.models import MODELS, resolve_model


class GeminiHandler(UpstreamGeminiHandler):
    """Extends the upstream handler with admin console routes."""

    def send_json(self, data, status=200, headers=None):
        """Send JSON response; optional extra response headers (e.g. Set-Cookie)."""
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
