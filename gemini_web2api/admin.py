"""Admin console helpers and static asset serving."""
import json
import mimetypes
import os
import socket
import sys
from pathlib import Path
from urllib.parse import unquote


ADMIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GeminiWeb2API Admin</title>
  <style>
    body { margin: 0; font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif; background: #f5f7fb; color: #172033; }
    main { max-width: 760px; margin: 12vh auto; padding: 32px; background: #fff; border: 1px solid #e3e8f0; border-radius: 8px; box-shadow: 0 16px 36px rgba(18,31,53,.08); }
    h1 { margin: 0 0 12px; font-size: 24px; }
    p { color: #667085; line-height: 1.7; }
    code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
  </style>
</head>
<body>
  <main>
    <h1>Web 管理台尚未构建</h1>
    <p>请在项目根目录运行 <code>cd web-admin && npm install && npm run build</code>，然后刷新此页面。</p>
  </main>
</body>
</html>
"""


def package_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "gemini_web2api"
    return Path(__file__).resolve().parent


def admin_static_dir() -> Path:
    return package_dir() / "admin_static"


def admin_index_path() -> Path:
    return admin_static_dir() / "index.html"


def read_admin_index() -> str:
    path = admin_index_path()
    if not path.exists():
        return ADMIN_HTML
    return path.read_text(encoding="utf-8")


def read_admin_asset(path: str):
    prefix = "/admin/"
    if not path.startswith(prefix):
        return None
    rel = unquote(path[len(prefix):]).replace("\\", "/").lstrip("/")
    if not rel or rel == "index.html":
        return None
    root = admin_static_dir().resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    if not target.is_file():
        return None
    content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return target.read_bytes(), content_type


def log_status() -> dict:
    path = log_path()
    try:
        stat = path.stat()
        return {
            "path": str(path),
            "exists": True,
            "size": stat.st_size,
            "modified": int(stat.st_mtime),
        }
    except OSError:
        return {"path": str(path), "exists": False, "size": 0, "modified": None}


def admin_static_status() -> dict:
    index = admin_index_path()
    return {
        "path": str(admin_static_dir()),
        "index": str(index),
        "ready": index.exists(),
    }


def app_dir() -> Path:
    return Path.cwd()


def config_path() -> Path:
    return app_dir() / "config.json"


def log_path() -> Path:
    return app_dir() / "logs" / "gemini_web2api.log"


def get_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def read_config(default_config: dict) -> dict:
    data = dict(default_config)
    path = config_path()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    return data


def save_config(current_config: dict, updates: dict) -> dict:
    allowed = {
        "cookie_file",
        "proxy",
        "default_model",
        "public_base_url",
        "empty_response_fallback",
    }
    data = read_config(current_config)
    for key in allowed:
        if key in updates:
            value = updates[key]
            data[key] = value if value not in ("", None) else None
    config_path().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    current_config.update(data)
    return data


def service_urls(host_header: str, port: int, public_base_url: str = None) -> dict:
    host = (host_header or "").split(",")[0].strip()
    current_origin = f"http://{host}" if host else f"http://127.0.0.1:{port}"
    public_url = public_base_url
    if not public_url and host and not host.startswith(("127.", "localhost")):
        public_url = current_origin.rstrip("/") + "/v1"
    return {
        "local": f"http://127.0.0.1:{port}/v1",
        "lan": f"http://{get_lan_ip()}:{port}/v1",
        "public": public_url or "",
        "current": current_origin.rstrip("/") + "/v1",
        "admin": current_origin.rstrip("/") + "/admin",
    }


def read_logs(offset: int = None, tail: int = 40000) -> dict:
    path = log_path()
    if not path.exists():
        return {"content": "", "offset": 0, "size": 0}
    size = path.stat().st_size
    if offset is None:
        offset = max(size - max(tail, 0), 0)
    if offset < 0 or offset > size:
        offset = 0
    with path.open("rb") as fh:
        fh.seek(offset)
        data = fh.read()
        new_offset = fh.tell()
    return {
        "content": data.decode("utf-8", errors="replace"),
        "offset": new_offset,
        "size": size,
    }
