"""Admin console helpers and static asset serving."""
import json
import hashlib
import hmac
import mimetypes
import os
import socket
import sys
import time
from pathlib import Path
from urllib.parse import unquote
import urllib.error
import urllib.request


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


def admin_password(config: dict) -> str:
    return str(config.get("admin_password") or os.environ.get("ADMIN_PASSWORD") or "sk-admin")


def _session_signature(config: dict, expires: str, nonce: str) -> str:
    secret = admin_password(config).encode("utf-8")
    return hmac.new(secret, f"{expires}:{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()


def make_admin_cookie(config: dict, max_age: int = 7 * 24 * 3600, secure: bool = False) -> str:
    expires = str(int(time.time()) + max_age)
    nonce = hashlib.sha256(os.urandom(24)).hexdigest()[:24]
    signature = _session_signature(config, expires, nonce)
    value = f"{expires}.{nonce}.{signature}"
    cookie = f"gw_admin={value}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}"
    if secure:
        cookie += "; Secure"
    return cookie


def clear_admin_cookie() -> str:
    return "gw_admin=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def verify_admin_password(config: dict, password: str) -> bool:
    return hmac.compare_digest(str(password or ""), admin_password(config))


def verify_admin_cookie(config: dict, cookie_header: str) -> bool:
    cookies = {}
    for item in (cookie_header or "").split(";"):
        if "=" in item:
            key, value = item.strip().split("=", 1)
            cookies[key] = value
    value = cookies.get("gw_admin")
    if not value:
        return False
    try:
        expires, nonce, signature = value.split(".", 2)
        if int(expires) < int(time.time()):
            return False
    except (ValueError, TypeError):
        return False
    expected = _session_signature(config, expires, nonce)
    return hmac.compare_digest(signature, expected)


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return key[:2] + "*" * (len(key) - 2)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def admin_config_payload(config: dict) -> dict:
    raw_keys = config.get("api_keys") or []
    masked_keys = [_mask_key(k) for k in raw_keys]
    return {
        "cookie_file": config.get("cookie_file") or "",
        "cookie_files": config.get("cookie_files") or ([config.get("cookie_file")] if config.get("cookie_file") else []),
        "cookie_content": "",
        "cookie_contents": [],
        "cookie_source": cookie_status(config),
        "proxy": config.get("proxy") or "",
        "default_model": config.get("default_model") or "",
        "public_base_url": config.get("public_base_url") or "",
        "empty_response_fallback": config.get("empty_response_fallback") or "",
        "api_keys": masked_keys,
        "force_non_stream": bool(config.get("force_non_stream")),
        "admin_password_set": bool(admin_password(config)),
    }


def _url_json(url: str, timeout: float = 8, proxy: str = None) -> dict:
    opener = urllib.request.build_opener()
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    req = urllib.request.Request(url, headers={"User-Agent": "gemini-web2ai-manage-admin/1.0"})
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _check_url(url: str, proxy: str = None, timeout: float = 8) -> dict:
    started = time.time()
    try:
        opener = urllib.request.build_opener()
        if proxy:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        req = urllib.request.Request(url, headers={"User-Agent": "gemini-web2ai-manage-admin/1.0"})
        with opener.open(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
        return {"ok": 200 <= status < 500, "status": status, "latency_ms": int((time.time() - started) * 1000)}
    except Exception as exc:
        return {"ok": False, "status": None, "latency_ms": int((time.time() - started) * 1000), "error": str(exc)}


def network_diagnostics(config: dict) -> dict:
    proxy = config.get("proxy") or None
    public = {}
    try:
        public = _url_json("https://ipapi.co/json/", proxy=proxy)
    except Exception as exc:
        public = {"error": str(exc)}
        try:
            public.update(_url_json("https://api.ipify.org?format=json", proxy=proxy))
        except Exception:
            pass
    return {
        "local_ip": get_lan_ip(),
        "public_ip": public.get("ip") or "",
        "city": public.get("city") or "",
        "region": public.get("region") or public.get("region_code") or "",
        "country": public.get("country_name") or public.get("country") or "",
        "org": public.get("org") or public.get("asn") or "",
        "timezone": public.get("timezone") or "",
        "proxy_enabled": bool(proxy),
        "connectivity": {
            "gemini": _check_url("https://gemini.google.com/", proxy=proxy),
            "google": _check_url("https://www.google.com/generate_204", proxy=proxy),
        },
        "raw_error": public.get("error") or "",
    }


def app_dir() -> Path:
    return Path.cwd()


def writable_app_dir() -> Path:
    root = app_dir()
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".gemini_web2api_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return root
    except OSError:
        fallback = Path(os.environ.get("TMPDIR") or "/tmp") / "gemini-web2api"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def config_path() -> Path:
    return app_dir() / "config.json"


def writable_config_path() -> Path:
    return writable_app_dir() / "config.json"


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
    paths = [config_path(), writable_config_path()]
    seen = set()
    for path in paths:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        try:
            with path.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    return data


def cookie_content_path() -> Path:
    return writable_app_dir() / "cookie.txt"


def cookie_status(config: dict) -> dict:
    env_cookie = os.environ.get("GEMINI_COOKIE")
    cookie_files = config.get("cookie_files") or ([config.get("cookie_file")] if config.get("cookie_file") else [])
    target = Path(cookie_files[0]) if cookie_files else cookie_content_path()
    files = []
    for item in cookie_files:
        path = Path(item)
        try:
            stat = path.stat()
            files.append({"path": str(path), "exists": path.is_file(), "size": stat.st_size if path.is_file() else 0})
        except OSError:
            files.append({"path": str(path), "exists": False, "size": 0})
    exists = False
    size = 0
    try:
        stat = target.stat()
        exists = target.is_file()
        size = stat.st_size if exists else 0
    except OSError:
        pass
    return {
        "env": bool(env_cookie),
        "path": str(target),
        "exists": exists,
        "size": size,
        "files": files,
    }


def write_cookie_content(config: dict, content: str) -> str:
    target = Path(config.get("cookie_file") or cookie_content_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.strip() + "\n", encoding="utf-8")
    return str(target)


def write_cookie_contents(contents: list) -> list:
    paths = []
    root = writable_app_dir()
    for index, content in enumerate(contents, start=1):
        value = str(content or "").strip()
        if not value:
            continue
        target = root / f"cookie_{index}.txt"
        target.write_text(value + "\n", encoding="utf-8")
        paths.append(str(target))
    return paths


def save_config(current_config: dict, updates: dict) -> dict:
    allowed = {
        "cookie_file",
        "proxy",
        "default_model",
        "public_base_url",
        "empty_response_fallback",
        "api_keys",
        "admin_password",
        "cookie_content",
        "cookie_contents",
        "cookie_files",
        "force_non_stream",
    }
    data = read_config(current_config)
    for key in allowed:
        if key in updates:
            value = updates[key]
            if key == "api_keys":
                if isinstance(value, str):
                    parts = value.replace(",", "\n").splitlines()
                    data[key] = [item.strip() for item in parts if item.strip()]
                elif isinstance(value, list):
                    data[key] = [str(item).strip() for item in value if str(item).strip()]
                continue
            if key == "cookie_content":
                if value not in ("", None):
                    cookie_file = write_cookie_content(data, str(value))
                    data["cookie_file"] = cookie_file
                    data["cookie_files"] = [cookie_file]
                    current_config["cookie_file"] = cookie_file
                continue
            if key == "cookie_contents":
                if isinstance(value, list):
                    cookie_files = write_cookie_contents(value)
                    if cookie_files:
                        data["cookie_files"] = cookie_files
                        data["cookie_file"] = cookie_files[0]
                        current_config["cookie_files"] = cookie_files
                        current_config["cookie_file"] = cookie_files[0]
                continue
            if key == "cookie_files":
                if isinstance(value, str):
                    items = value.replace(",", "\n").splitlines()
                elif isinstance(value, list):
                    items = value
                else:
                    items = []
                files = [str(item).strip() for item in items if str(item).strip()]
                data["cookie_files"] = files
                data["cookie_file"] = files[0] if files else None
                continue
            if key == "force_non_stream":
                data[key] = bool(value)
                continue
            if key == "admin_password" and value in ("", None):
                continue
            data[key] = value if value not in ("", None) else None
    writable_config_path().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
    try:
        if not path.exists():
            return {"content": "", "offset": 0, "size": 0, "path": str(path), "exists": False}
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
            "path": str(path),
            "exists": True,
        }
    except OSError as exc:
        return {"content": "", "offset": 0, "size": 0, "path": str(path), "exists": False, "error": str(exc)}
