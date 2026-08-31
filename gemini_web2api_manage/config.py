"""Extended configuration for gemini-web2api-manage.

Imports the upstream CONFIG dict and adds manage-specific keys.
Because CONFIG is a shared mutable dict, all modules (upstream + manage)
see the same configuration object.
"""
import json
import os
from pathlib import Path

from gemini_web2api.config import CONFIG, DEFAULT_CONFIG as UPSTREAM_DEFAULT

# Manage-specific default keys injected into the shared CONFIG dict
MANAGE_DEFAULTS = {
    "admin_password": "sk-admin",
    "public_base_url": None,
    "force_non_stream": False,
    "empty_response_fallback": (
        "Gemini \u8fd4\u56de\u4e86\u7a7a\u5185\u5bb9\u3002"
        "\u53ef\u80fd\u539f\u56e0\uff1aCookie \u5931\u6548\u3001"
        "\u5185\u5bb9\u88ab\u5b89\u5168\u7b56\u7565\u62e6\u622a\u3001"
        "\u4e0a\u4e0b\u6587\u8fc7\u957f\u6216\u5f53\u524d\u6a21\u578b"
        "\u6682\u4e0d\u53ef\u7528\u3002\u8bf7\u67e5\u770b\u7ba1\u7406"
        "\u53f0\u65e5\u5fd7\u4e2d\u7684\u7a7a\u54cd\u5e94\u8bca\u65ad"
        "\u540e\u91cd\u8bd5\u3002"
    ),
    "cookie_files": [],

    # —— 协议对齐层（spec 03-01）——
    # 官网 URL 与 payload 的语言标记；上游旧实现硬编码 "en"。
    "gemini_hl": "en",
    # bl 版本号后台刷新间隔（秒），下限 300。
    "bl_refresh_sec": 21600,
    # 整体覆盖浏览器画像字段（空表示用 protocol.BROWSER_PROFILE 默认值）。
    # 例：{"user_agent": "...", "chrome_full_version": "152.0.7977.65"}
    "browser_profile": {},
    # 是否把官网回报的真实服务模型透出到响应（关闭则只回显请求的模型名）。
    "expose_served_model": True,
}

for key, value in MANAGE_DEFAULTS.items():
    if key not in CONFIG:
        CONFIG[key] = value


def _env_bool(name: str, default=None):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default=None):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def apply_env_config() -> dict:
    """Apply deployment environment variables to the shared CONFIG dict.

    This is primarily used by the Vercel entrypoint, where a persistent
    config.json or cookie file cannot be mounted. Cookie text is materialized
    under the runtime temp/data directory and consumed by the upstream client.
    """
    text_fields = {
        "proxy": "PROXY",
        "default_model": "DEFAULT_MODEL",
        "public_base_url": "PUBLIC_BASE_URL",
        "gemini_bl": "GEMINI_BL",
        "gemini_base_url": "GEMINI_BASE_URL",
        "xsrf_token": "XSRF_TOKEN",
        "gemini_hl": "GEMINI_HL",
    }
    for config_key, env_key in text_fields.items():
        value = os.environ.get(env_key)
        if value:
            CONFIG[config_key] = value

    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_password:
        CONFIG["admin_password"] = admin_password

    api_keys = os.environ.get("API_KEYS")
    if api_keys:
        try:
            parsed = json.loads(api_keys) if api_keys.lstrip().startswith("[") else None
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            CONFIG["api_keys"] = [str(item).strip() for item in parsed if str(item).strip()]
        else:
            CONFIG["api_keys"] = [item.strip() for item in api_keys.replace(",", "\n").splitlines() if item.strip()]

    cookie = os.environ.get("GEMINI_COOKIE")
    if cookie:
        root = Path(os.environ.get("GEMINI_WEB2API_DATA_DIR") or "/tmp/gemini-web2api")
        root.mkdir(parents=True, exist_ok=True)
        cookie_path = root / "env-cookie.txt"
        cookie_path.write_text(cookie.strip() + "\n", encoding="utf-8")
        CONFIG["cookie_file"] = str(cookie_path)
        CONFIG["cookie_files"] = [str(cookie_path)]

    int_fields = {
        "port": "PORT",
        "retry_attempts": "RETRY_ATTEMPTS",
        "retry_delay_sec": "RETRY_DELAY_SEC",
        "request_timeout_sec": "REQUEST_TIMEOUT_SEC",
        "auth_user": "AUTH_USER",
        "bl_refresh_sec": "BL_REFRESH_SEC",
    }
    for config_key, env_key in int_fields.items():
        value = _env_int(env_key)
        if value is not None:
            CONFIG[config_key] = value

    bool_fields = {
        "log_requests": "LOG_REQUESTS",
        "temporary_chats": "TEMPORARY_CHATS",
        "force_non_stream": "FORCE_NON_STREAM",
        "expose_served_model": "EXPOSE_SERVED_MODEL",
    }
    for config_key, env_key in bool_fields.items():
        value = _env_bool(env_key)
        if value is not None:
            CONFIG[config_key] = value

    host = os.environ.get("HOST")
    if host:
        CONFIG["host"] = host
    return CONFIG
