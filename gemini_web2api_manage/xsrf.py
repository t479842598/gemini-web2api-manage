"""Automatic XSRF (`at`) token support for the upstream gemini client.

Google's StreamGenerate endpoint requires the `at` query param. When it is
missing or stale, the endpoint answers 400 and embeds a fresh token in the
error body: `...["xsrf","ADR5zao0e-...:<ts>"...]...`.

Strategy (manage-side patch, upstream submodule stays untouched):
  1. `_build_payload` is patched to append `at=<token>` when we hold a cached
     token (and no explicit `xsrf_token` is configured).
  2. `generate` / `generate_stream` are wrapped so that a 400/403 whose body
     carries an xsrf token caches that token and retries once.

The cache self-heals: stale tokens yield another 400 with a fresh token.
"""
import re
import time
import urllib.error
from urllib.parse import quote_plus

import gemini_web2api.gemini as _g

from .config import CONFIG

_AT = {"token": None, "ts": 0}
_TTL = 3600  # seconds


def _fresh_at() -> str:
    if _AT["token"] and (time.time() - _AT["ts"]) < _TTL:
        return _AT["token"]
    return None



def _store_at(token: str):
    _AT["token"] = token
    _AT["ts"] = time.time()


def _extract_xsrf(raw: str):
    m = re.search(r'\["xsrf","([^"]+)"', raw or "")
    return m.group(1) if m else None


_orig_build_payload = _g._build_payload
_orig_generate = _g.generate
_orig_generate_stream = _g.generate_stream


def _patched_build_payload(prompt, model_id, think_mode, file_refs=None, extra_fields=None):
    text = _orig_build_payload(prompt, model_id, think_mode, file_refs, extra_fields)
    if not CONFIG.get("xsrf_token"):
        at = _fresh_at()
        if at and "&at=" not in text:
            text += "&at=" + quote_plus(at)
    return text


def _handle_error(raw_or_err) -> bool:
    """Extract & cache an xsrf token from an error payload. Returns True on cache."""
    raw = raw_or_err if isinstance(raw_or_err, str) else ""
    if not raw:
        try:
            raw = raw_or_err.read().decode("utf-8", "replace")
        except Exception:
            return False
    token = _extract_xsrf(raw)
    if token and not CONFIG.get("xsrf_token"):
        _store_at(token)
        from gemini_web2api.gemini import log
        log(f"xsrf: cached fresh token from upstream ({token[:24]}...)")
        return True
    return False


def _patched_generate(*args, **kwargs):
    try:
        return _orig_generate(*args, **kwargs)
    except urllib.error.HTTPError as e:
        if _handle_error(e):
            return _orig_generate(*args, **kwargs)
        raise


def _patched_generate_stream(*args, **kwargs):
    it = _orig_generate_stream(*args, **kwargs)
    while True:
        try:
            chunk = next(it)
            yield chunk
        except StopIteration:
            return
        except urllib.error.HTTPError as e:
            if _handle_error(e):
                it = _orig_generate_stream(*args, **kwargs)
                continue
            raise
        except Exception as e:
            resp = getattr(e, "response", None)
            status = getattr(resp, "status_code", None)
            if status in (400, 403):
                try:
                    raw = resp.text
                except Exception:
                    raw = ""
                if _handle_error(raw):
                    it = _orig_generate_stream(*args, **kwargs)
                    continue
            raise


_installed = False


def install():
    global _installed
    if _installed:
        return
    _g._build_payload = _patched_build_payload
    _g.generate = _patched_generate
    _g.generate_stream = _patched_generate_stream
    # 供 protocol.py 的 httpx 非流式路径复用本层的 token 自愈能力：
    # 传入响应体文本，抽到新 token 则缓存并返回 True（表示可重试）。
    _g._xsrf_maybe_handle = _handle_error
    # server.py binds `from .gemini import generate, generate_stream` at import
    # time; patch those references too so the HTTP handlers use our wrappers.
    try:
        import gemini_web2api.server as _s
        _s.generate = _patched_generate
        _s.generate_stream = _patched_generate_stream
    except Exception:
        pass
    _installed = True


install()
