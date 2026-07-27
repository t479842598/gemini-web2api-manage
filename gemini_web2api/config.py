"""Configuration management."""
import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "port": 8081,
    "host": "0.0.0.0",
    "retry_attempts": 3,
    "retry_delay_sec": 2,
    "request_timeout_sec": 180,
    "gemini_base_url": None,
    "gemini_bl": "boq_assistant-bard-web-server_20260716.08_p0",
    "auth_user": None,
    "xsrf_token": None,
    "default_model": "gemini-3.6-flash",
    "log_requests": True,
    "cookie_file": None,
    "cookie_files": [],
    "proxy": None,
    "api_keys": [],
    "admin_password": "sk-admin",
    "force_non_stream": False,
    "empty_response_fallback": "Gemini 返回了空内容。可能原因：Cookie 失效、内容被安全策略拦截、上下文过长或当前模型暂不可用。请查看管理台日志中的空响应诊断后重试。",
}

CONFIG = dict(DEFAULT_CONFIG)


def _load_dotenv(path: str = None):
    """Load .env file manually (no external dep needed)."""
    if path is None:
        candidates = [".env", os.path.expanduser("~/.config/gemini-web2api/.env")]
        for p in candidates:
            if os.path.exists(p):
                path = p
                break
    if not path or not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key:
                os.environ.setdefault(key, value)


def apply_env_config():
    """Apply deployment-specific environment overrides.

    Priority: Vercel env > .env file > config.json defaults.
    Environment variables take precedence over all file-based config.
    """
    # Load .env file first (os.environ.setdefault, so won't override existing)
    _load_dotenv()

    # GEMINI_COOKIE -> write to temp cookie file
    cookie = os.environ.get("GEMINI_COOKIE")
    if cookie:
        cookie_path = os.environ.get(
            "GEMINI_COOKIE_FILE",
            os.path.join(os.environ.get("TMPDIR", "/tmp"), "gemini_cookie.txt")
        )
        Path(cookie_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cookie_path).write_text(cookie, encoding="utf-8")
        CONFIG["cookie_file"] = cookie_path
        CONFIG["cookie_files"] = [cookie_path]

    gemini_base_url = os.environ.get("GEMINI_BASE_URL")
    if gemini_base_url:
        CONFIG["gemini_base_url"] = gemini_base_url

    # API keys from environment
    api_keys = os.environ.get("API_KEYS") or os.environ.get("GEMINI_WEB2API_API_KEYS")
    if api_keys:
        CONFIG["api_keys"] = [item.strip() for item in api_keys.split(",") if item.strip()]

    # Proxy, admin_password, etc.
    for env_key, config_key in [
        ("PROXY", "proxy"),
        ("ADMIN_PASSWORD", "admin_password"),
        ("DEFAULT_MODEL", "default_model"),
        ("GEMINI_BL", "gemini_bl"),
        ("PUBLIC_BASE_URL", "public_base_url"),
        ("EMPTY_RESPONSE_FALLBACK", "empty_response_fallback"),
    ]:
        val = os.environ.get(env_key)
        if val:
            CONFIG[config_key] = val

    # Boolean/int overrides
    for env_key, config_key in [
        ("RETRY_ATTEMPTS", "retry_attempts"),
        ("RETRY_DELAY_SEC", "retry_delay_sec"),
        ("REQUEST_TIMEOUT_SEC", "request_timeout_sec"),
    ]:
        try:
            val = os.environ.get(env_key)
            if val is not None:
                CONFIG[config_key] = int(val)
        except (TypeError, ValueError):
            pass

    force = os.environ.get("FORCE_NON_STREAM")
    if force is not None:
        CONFIG["force_non_stream"] = force.strip().lower() in ("1", "true", "yes")


def load_config(path: str = None):
    """Load config from JSON file, then apply environment overrides."""
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            CONFIG.update(json.load(f))
    apply_env_config()
    return CONFIG


def find_config():
    """Search for config file in standard locations."""
    for p in ["./config.json", os.path.expanduser("~/.config/gemini-web2api/config.json")]:
        if os.path.exists(p):
            return p
    return None
