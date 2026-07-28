"""Extended HTTP server for gemini-web2api-manage.

Inherits the upstream GeminiHandler and adds admin console routes
(/admin, /admin/api/*) before falling back to upstream behavior.
"""
import json
from urllib.parse import urlparse

from .config import CONFIG
from . import __version__
from .admin import (
    admin_config_payload,
    admin_static_status,
    clear_admin_cookie,
    log_status,
    make_admin_cookie,
    network_diagnostics,
    read_admin_asset,
    read_admin_index,
    read_logs,
    save_config,
    service_urls,
    verify_admin_cookie,
    verify_admin_password,
)

from gemini_web2api.server import GeminiHandler as UpstreamGeminiHandler
from gemini_web2api.models import MODELS, resolve_model


class GeminiHandler(UpstreamGeminiHandler):
    """Extends the upstream handler with admin console routes."""

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
            if path.startswith("/admin/"):
                asset = read_admin_asset(path)
                if asset:
                    body, content_type = asset
                    self.send_bytes(body, content_type)
                else:
                    self.send_json({"error": "admin asset not found"}, 404)
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

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""

            # Admin login/logout/config
            if path == "/admin/api/login":
                self._handle_admin_login(body)
                return
            if path == "/admin/api/logout":
                self.send_json(
                    {"ok": True},
                    headers={"Set-Cookie": clear_admin_cookie()},
                )
                return
            if (
                path == "/admin/api/config"
                and not self._require_admin()
            ):
                return
            if path == "/admin/api/config":
                self._handle_admin_config(body)
                return

            # Fall through to upstream handler
            super().do_POST()

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
        config = admin_config_payload(updated)
        config["empty_response_fallback"] = (
            config["empty_response_fallback"] or self._empty_response_fallback()
        )
        self.send_json({"ok": True, "config": config})
