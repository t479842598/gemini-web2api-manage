"""Vercel serverless entrypoint."""
import os
from pathlib import Path

from gemini_web2api.config import CONFIG
from gemini_web2api.server import GeminiHandler


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _apply_env_config() -> None:
    api_keys = os.environ.get("API_KEYS") or os.environ.get("GEMINI_WEB2API_API_KEYS")
    if api_keys:
        CONFIG["api_keys"] = [item.strip() for item in api_keys.split(",") if item.strip()]

    mapping = {
        "DEFAULT_MODEL": "default_model",
        "GEMINI_BL": "gemini_bl",
        "PROXY": "proxy",
        "PUBLIC_BASE_URL": "public_base_url",
        "EMPTY_RESPONSE_FALLBACK": "empty_response_fallback",
        "ADMIN_PASSWORD": "admin_password",
    }
    for env_name, config_name in mapping.items():
        value = os.environ.get(env_name)
        if value:
            CONFIG[config_name] = value

    CONFIG["retry_attempts"] = _env_int("RETRY_ATTEMPTS", CONFIG["retry_attempts"])
    CONFIG["retry_delay_sec"] = _env_int("RETRY_DELAY_SEC", CONFIG["retry_delay_sec"])
    CONFIG["request_timeout_sec"] = _env_int("REQUEST_TIMEOUT_SEC", CONFIG["request_timeout_sec"])
    CONFIG["log_requests"] = _env_bool("LOG_REQUESTS", CONFIG["log_requests"])

    cookie = os.environ.get("GEMINI_COOKIE")
    if cookie:
        cookie_path = Path("/tmp/gemini_cookie.txt")
        cookie_path.write_text(cookie, encoding="utf-8")
        CONFIG["cookie_file"] = str(cookie_path)


_apply_env_config()


class handler(GeminiHandler):
    pass
