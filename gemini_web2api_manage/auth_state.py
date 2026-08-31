"""Cookie 认证态探测（spec 03-01 / T-012）。

背景：实测发现推送的 Cookie 会在一段时间后被 Google 悄悄当作匿名 —— 表现是
`served_model` 恒为 3.5 Flash-Lite、多模态返回 1003「anonymous mode」。服务本身
不报错，用户只能看到"模型变笨了"，完全不知道是登录态掉了。本模块把这件事变成
一个明确的状态。

判据（2026-09-01 实测确立，比看 served_model 可靠）：
    带 Cookie 但**不带 `at`** 发一次请求
      → HTTP 400  = Google 在校验 at ⇒ **登录态有效**
      → HTTP 200  = Google 不校验 at ⇒ **被当作匿名**
  之所以不用 served_model 当判据：匿名恒为 lite，但登录态下 lite 也可能是正常的
  低档位请求，会误判；而 `at` 是否被强制只取决于会话是否被识别。

探测一次要消耗一个真实 Google 请求，所以结果按 TTL 缓存，且只在配了 Cookie 时才探。
"""
import threading
import time

from .config import CONFIG

_LOCK = threading.Lock()
_STATE = {
    "state": "unknown",       # authenticated | anonymous | no_cookie | unknown | error
    "detail": "",
    "checked_at": 0.0,
    "previous": None,
    "flipped_at": None,
}

VALID_STATES = ("authenticated", "anonymous", "no_cookie", "unknown", "error")


def _ttl() -> int:
    try:
        return max(60, int(CONFIG.get("auth_probe_ttl_sec") or 600))
    except (TypeError, ValueError):
        return 600


def _has_cookie() -> bool:
    return bool(CONFIG.get("cookie_file") or CONFIG.get("cookie_files"))


def _probe_now():
    """发一次「带 Cookie、不带 at」的请求，返回 (state, detail)。"""
    import urllib.error
    import urllib.request
    from . import protocol

    if not _has_cookie():
        return "no_cookie", "未配置 Cookie，按匿名模式运行"

    saved = CONFIG.get("xsrf_token")
    try:
        # 必须走 protocol 的构造器而不是 `_g._build_payload`：后者已被 xsrf 层
        # 包装成「CONFIG 里没有 xsrf_token 时就把缓存的 at 追加回去」，那样就
        # 造不出「不带 at」的请求，判据会失效。
        CONFIG["xsrf_token"] = None
        body = protocol._build_payload("Reply with OK", 1, 4).encode()
        url = protocol._get_url()
        headers = protocol._build_headers()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=45)
            raw = resp.read().decode("utf-8", "replace")
            status = getattr(resp, "status", 200)
        except urllib.error.HTTPError as e:
            status = e.code
            raw = e.read().decode("utf-8", "replace") if e.fp else ""
        except Exception as e:
            return "error", f"探测请求失败：{type(e).__name__}"
    finally:
        CONFIG["xsrf_token"] = saved

    if status == 400:
        return "authenticated", "Google 在校验 at（缺 at 返回 400）⇒ 登录态有效"
    if status == 200:
        return "anonymous", ("Google 未校验 at（缺 at 仍返回 200）⇒ 已被当作匿名，"
                             "请在浏览器重新登录 Gemini 后用扩展再推送一次")
    return "unknown", f"未预期的响应状态 {status}"


def check(force: bool = False) -> dict:
    """返回认证态快照；命中缓存则不发请求。force=True 忽略缓存。"""
    now = time.time()
    with _LOCK:
        fresh = (now - _STATE["checked_at"]) < _ttl()
        if fresh and not force and _STATE["state"] != "unknown":
            return dict(_STATE)
    state, detail = _probe_now()
    with _LOCK:
        prev = _STATE["state"]
        _STATE.update({
            "state": state, "detail": detail, "checked_at": now,
            "previous": prev,
            "flipped_at": now if (prev != state and prev != "unknown") else _STATE["flipped_at"],
        })
        if prev == "authenticated" and state == "anonymous":
            _STATE["checked_at"] = now
            try:
                from gemini_web2api.gemini import log
                log("AUTH DEGRADED: Cookie 登录态已失效，Google 现按匿名处理 —— "
                    "请重新登录 Gemini 后用扩展再推送 Cookie")
            except Exception:
                pass
        return dict(_STATE)


def snapshot() -> dict:
    """只读快照，不发请求（供 /health 这类高频端点用）。"""
    with _LOCK:
        out = dict(_STATE)
    out["has_cookie"] = _has_cookie()
    age = time.time() - out.get("checked_at", 0)
    out["age_sec"] = int(age) if out.get("checked_at") else None
    out["stale"] = bool(out.get("checked_at")) and age > _ttl()
    return out


def start_background_monitor(interval_sec: int = None):
    """后台定期探测，让 /health 与告警保持新鲜（不阻塞请求路径）。"""
    if interval_sec is None:
        interval_sec = _ttl()
    interval_sec = max(120, int(interval_sec))

    def loop():
        while True:
            try:
                check(force=True)
            except Exception:
                pass
            time.sleep(interval_sec)

    t = threading.Thread(target=loop, name="gemini-auth-probe", daemon=True)
    t.start()
    return t
