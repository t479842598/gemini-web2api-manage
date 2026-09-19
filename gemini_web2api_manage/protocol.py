"""Gemini 官网协议对齐层（manage 侧 monkeypatch，不改 _upstream submodule）。

本模块把 2026-08-31 用真实 Chrome headless + CDP 抓包得到的官网请求/响应形态，
套到上游 `gemini_web2api.gemini` 上。所有增强都遵循同一条降级原则：
**取不到、解析失败、配置为空时一律退回上游原行为，绝不让增强逻辑本身弄挂请求。**

挂点分两类，改动时务必分清（这是最容易出错的地方）：
  1. 模块全局查找的函数（`_build_headers` / `_get_url` / `_build_payload` /
     `_extract_texts_from_line`）——上游内部互相调用时在运行时解析全局名，
     替换 `gemini_web2api.gemini` 上的属性即可生效。
  2. `from x import y` 按值绑定的名字（`server.py` 里的 `generate` /
     `generate_stream`）——必须同时替换 `gemini_web2api.server` 上的引用。
     `MODELS` 是 dict，原地 mutate 而非重新绑定，已持有引用的模块才看得到。

实测结论（详见 spec 03-01 与 CHANGELOG）：
  * 匿名模式下 payload `inner[79]`(mode) 与 `inner[17]`(think) 对 Google 路由无效，
    mode 取 1..6 响应 `inner[42]` 一律回报 `3.5 Flash-Lite`。
  * 注入真实浏览器抓到的 `inner[3]`（1.6KB protobuf token）与 `inner[4]`（32hex）
    **不改变**服务模型 —— 已验证无收益，故本层不生成这两个字段，保持 null。
"""
import itertools
import json
import random
import re
import threading
import time
import urllib.parse
import uuid as _uuid

import gemini_web2api.gemini as _g

from .config import CONFIG

# ─── Chrome 浏览器画像（唯一维护点，随 Chrome 大版本只改这里）─────────────────
# 来源：2026-09-19 本机 Chrome 153.0.8010.50 headless + CDP 抓包（macOS 27.0）。
# 复核方式：tools/capture_baseline.mjs 抓一份官网基线 → tools/align_check.py 比对。
# 若官网开始校验画像与实际客户端不一致，把 BROWSER_PROFILE 整体降回上一份
# verified 基线即可，或在 config.json 里用 browser_profile 键覆盖，无需改代码。
#
# 2026-09-19 修正（对比 08-31 那份）：full_version 153.0.8010.12 → 实测 .50；
# platform_version 26.7.0 → 27.0.0；sec-ch-ua 的品牌写法与顺序改为官网实测的
# `"Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"`
# （旧版写的是 `Not/A)Brand`，且把 Google Chrome 排在最后）。
BROWSER_PROFILE = {
    "chrome_major": "153",
    "chrome_full_version": "153.0.8010.50",
    # 注意：UA 里的版本只到大版本（Chrome 的 UA Reduction）
    "user_agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
    ),
    "sec_ch_ua": (
        '"Google Chrome";v="153", "Not_A Brand";v="8", '
        '"Chromium";v="153"'
    ),
    "sec_ch_ua_full_version_list": (
        '"Google Chrome";v="153.0.8010.50", "Not_A Brand";v="8.0.0.0", '
        '"Chromium";v="153.0.8010.50"'
    ),
    "sec_ch_ua_platform": '"macOS"',
    "sec_ch_ua_platform_version": '"27.0.0"',
    "sec_ch_ua_arch": '"arm"',
    "sec_ch_ua_bitness": '"64"',
    "sec_ch_ua_model": '""',
    "sec_ch_ua_form_factors": '"Desktop"',
    # 官网网络层实测 accept-language 为 `zh-CN,zh;q=0.9`（不带 en 项）。
    "accept_language": "zh-CN,zh;q=0.9",
    # 官网显式携带的 Chrome 自述头（值随版本滚动，2026-09-19 实测）。
    "browser_channel": "stable",
    "browser_copyright": "Copyright 2026 Google LLC. All Rights Reserved.",
    "browser_year": "2026",
}

# 官网真实请求里带的 Google 私有扩展头（含义未逆向，本层只对齐"存在性与结构"，
# 不假装能通过服务端校验；实测薄头也能 10/10 成功，这属于指纹加固而非止血）。
_XGOOG_525001261_HEX = "".join(random.choice("0123456789abcdef") for _ in range(16))

# ─── 进程级会话标识 ────────────────────────────────────────────────────────
_LOCK = threading.Lock()
# 官网 _reqid 是 7 位且会话内递增（实测 2174817 → 2174870 → 2275014）。
# 上游用 int(time.time())%1000000，同一秒内的并发请求必然撞号 —— 这里改成
# 随机起点 + 进程内递增，保证唯一。
_REQID_START = random.randint(1_000_000, 9_900_000)
_REQID_COUNTER = itertools.count(_REQID_START)
# f.sid：官网为 19 位带符号整数，进程启动时生成一次并复用
F_SID = random.randint(-(2 ** 62), 2 ** 62)

# ─── 线程局部：每请求的 UUID 与响应元数据 ─────────────────────────────────
_tls = threading.local()
_LAST_META: dict = {}


def _next_reqid() -> int:
    with _LOCK:
        return next(_REQID_COUNTER)


def _request_uuid() -> str:
    """本次请求的 UUID。

    上游 generate/generate_stream 的调用顺序是先 _build_payload 再
    _build_headers，所以该值在 _build_payload 里生成并暂存，供
    _build_headers 复用 —— 官网正是同一个 UUID 同时出现在
    x-goog-ext-525005358-jspb 与 payload inner[59]。

    fallback 路径（未经 _build_payload 直接取头）也必须写回 _tls，
    否则同一请求内两处会拿到不同的 UUID（线上就是这个 bug）。
    """
    existing = getattr(_tls, "uuid", None)
    if existing:
        return existing
    value = str(_uuid.uuid4()).upper()
    _tls.uuid = value
    return value


def _set_request_uuid(value: str) -> None:
    _tls.uuid = value


def reset_meta() -> None:
    """清空当前线程的响应元数据（每次发起请求前调用，避免跨请求串味）。"""
    _tls.meta = {}


def reset_continuation() -> None:
    """清掉本线程登记的续接会话。"""
    _tls.cont = None


def get_meta() -> dict:
    """返回当前线程最近一次响应解析出的元数据副本。"""
    return dict(getattr(_tls, "meta", None) or {})


def set_continuation(conversation_id, response_id) -> None:
    """登记本次请求要续接的 Gemini 会话。

    实测（2026-09-01，带 Cookie）：payload 的 inner[2] 前两位放
    [conversation_id, response_id] 时，服务端会真正续接会话且不再报 1097；
    放错位置（如 ["", cid, rid]）则返回空回复。两个 id 来自上一次响应
    inner[1]，我们已通过 gemini_conversation_id / gemini_response_id 透出。
    需要有效登录态 —— 匿名下 1097 仍被硬拒。
    """
    if conversation_id and response_id:
        _tls.cont = (str(conversation_id), str(response_id))
    else:
        _tls.cont = None


def get_continuation():
    return getattr(_tls, "cont", None)


def set_sse_writer(writer) -> None:
    """登记当前线程的 SSE 改写包装器，供流式结束时强制 flush 暂存块。"""
    _tls.sse_writer = writer


def get_sse_writer():
    return getattr(_tls, "sse_writer", None)


def _store_meta(**kwargs) -> None:
    meta = getattr(_tls, "meta", None)
    if meta is None:
        meta = {}
        _tls.meta = meta
    for k, v in kwargs.items():
        if v is not None:
            meta[k] = v
    if kwargs:
        # 同时记一份进程级“最近一次”，供管理台状态接口展示
        global _LAST_META
        with _LOCK:
            merged = dict(_LAST_META)
            merged.update({k: v for k, v in kwargs.items() if v is not None})
            merged["updated_at"] = time.time()
            _LAST_META = merged


def last_meta() -> dict:
    """进程级“最近一次成功生成”的元数据（跨线程汇总，非当前线程）。"""
    with _LOCK:
        return dict(_LAST_META)


def _profile() -> dict:
    """允许用 config 的 browser_profile 覆盖任意画像字段。"""
    override = CONFIG.get("browser_profile") or {}
    p = dict(BROWSER_PROFILE)
    if isinstance(override, dict):
        for k, v in override.items():
            if v:
                p[k] = v
    return p


def _hl() -> str:
    return (CONFIG.get("gemini_hl") or "en").strip() or "en"


# ─── 1. 请求头 ─────────────────────────────────────────────────────────────
_orig_build_headers = _g._build_headers


def _build_headers() -> dict:
    """在保留上游 Cookie / SAPISIDHASH / X-Goog-AuthUser 逻辑的前提下补齐指纹。"""
    headers = _orig_build_headers()
    p = _profile()

    # Origin / Referer 跟随实际请求域名：上游把它们硬编码为官网，若配了
    # gemini_base_url 反代域名就会与实际目标不一致（反而更像伪造）。
    # Authorization 的 SAPISIDHASH 仍按上游原逻辑用真实 Google 域名计算，
    # 不在本层动 —— 带 Cookie 场景待实测后再定。
    # 2026-09-19 网络层抓包（Network.requestWillBeSentExtraInfo，含浏览器自动加的头）
    # 修正了上一版基于 requestWillBeSent 的误判：官网**确实发** Origin 与 Accept，
    # 只是它们不在 CDP 的“开发者设置头”那一栏。accept-language 实测为
    # `zh-CN,zh;q=0.9`（无 en 项）；Referer 是裸域名（不带 /app、不带 account prefix）。
    base = _base_url()
    headers["Origin"] = base
    headers["Referer"] = f"{base}/"

    headers["Accept"] = "*/*"
    headers["Accept-Language"] = p["accept_language"]
    headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
    headers["User-Agent"] = p["user_agent"]
    # Fetch 元数据头：同源 XHR 的固定形态，官网必带
    headers["sec-fetch-dest"] = "empty"
    headers["sec-fetch-mode"] = "cors"
    headers["sec-fetch-site"] = "same-origin"
    headers["priority"] = "u=1, i"
    headers["x-browser-channel"] = p["browser_channel"]
    headers["x-browser-copyright"] = p["browser_copyright"]
    headers["x-browser-year"] = p["browser_year"]
    headers["sec-ch-ua"] = p["sec_ch_ua"]
    headers["sec-ch-ua-platform"] = p["sec_ch_ua_platform"]
    headers["sec-ch-ua-bitness"] = p["sec_ch_ua_bitness"]
    headers["sec-ch-ua-model"] = p["sec_ch_ua_model"]
    headers["sec-ch-ua-mobile"] = "?0"
    headers["sec-ch-ua-wow64"] = "?0"
    headers["sec-ch-ua-form-factors"] = p["sec_ch_ua_form_factors"]
    headers["sec-ch-ua-arch"] = p["sec_ch_ua_arch"]
    headers["sec-ch-ua-platform-version"] = p["sec_ch_ua_platform_version"]
    headers["sec-ch-ua-full-version"] = p["chrome_full_version"]
    headers["sec-ch-ua-full-version-list"] = p["sec_ch_ua_full_version_list"]

    # 官网另带 x-browser-validation（形如 "KBOSoI/ydlNGP7OTQlJKEOIWpXE="，疑为
    # 基于画像字段的校验和）。未逆向出生成算法，且实测缺失不影响请求成功，
    # 故**不伪造** —— 填一个假的校验和比不发更可疑。

    # Google 私有扩展头：结构与官网一致，UUID 与本请求 payload inner[59] 同源
    ruuid = _request_uuid()
    headers["x-goog-ext-525001261-jspb"] = json.dumps(
        [1, None, None, None, _XGOOG_525001261_HEX, None, None, 0, [4, 6, 4, 6],
         None, None, 1, None, None, 6, None, ruuid], separators=(",", ":"))
    headers["x-goog-ext-525005358-jspb"] = json.dumps(
        [ruuid, 1], separators=(",", ":"))
    headers["x-goog-ext-73010989-jspb"] = "[0]"
    headers["x-goog-ext-73010990-jspb"] = "[0,0,0]"
    return headers


# ─── 2. URL ────────────────────────────────────────────────────────────────
_orig_get_url = _g._get_url


def _base_url() -> str:
    """生成请求的域名。

    修一个既有缺陷：`gemini_base_url` 这个配置键在管理台配置页（admin.py）
    和网络检测里都被读取，但上游 `_get_url()` 把域名硬编码成了
    `https://gemini.google.com`，导致“私有反代域名”对实际生成请求完全无效。
    本层接管 URL 构造后把它真正接上。
    """
    base = (CONFIG.get("gemini_base_url") or "https://gemini.google.com").strip()
    return base.rstrip("/") or "https://gemini.google.com"


def _get_url() -> str:
    prefix = _g._account_prefix()
    return (
        f"{_base_url()}{prefix}/_/BardChatUi/data/"
        "assistant.lamda.BardFrontendService/StreamGenerate"
        f"?bl={CONFIG['gemini_bl']}&f.sid={F_SID}&hl={_hl()}"
        f"&_reqid={_next_reqid()}&rt=c"
    )


# ─── 3. Payload ────────────────────────────────────────────────────────────
_orig_build_payload = _g._build_payload

# 官网内层数组实测长度 99（上游写死 102，多出的尾部 null 目前不被校验，
# 这里对齐以免 Google 将来加长度校验时踩雷）。
# 2026-09-19 抓包复核：从 08-31 观测的 97 变成 99，尾部多出 [97]=null、[98]=1。
_INNER_LEN = 99


def _build_payload(prompt, model_id, think_mode, file_refs=None, extra_fields=None) -> str:
    inner = [None] * _INNER_LEN
    if file_refs:
        refs = [[None, None, ref] for ref in file_refs]
        inner[0] = [prompt, 0, None, refs, None, None, 0]
    else:
        inner[0] = [prompt, 0, None, None, None, None, 0]
    inner[1] = [_hl()]
    inner[2] = ["", "", "", None, None, None, None, None, None, ""]
    # 只在配了 Cookie 时才尝试续接：匿名下带真实 ID 实测返回 1096，
    # 等于把一个本来可用的请求变成报错。宁可不上优化，也不能引入回归。
    cont = get_continuation() if (CONFIG.get("cookie_file")
                                  or CONFIG.get("cookie_files")) else None
    if cont:
        inner[2] = [cont[0], cont[1], "", None, None, None, None, None, None, ""]
    # inner[3] / inner[4] 故意留 null：实测注入真实浏览器 token 不改变模型路由。
    inner[6] = [1]          # 上游原为 [0]，官网为 [1]
    inner[7] = 1
    inner[10] = 1
    inner[11] = 0
    inner[17] = [[think_mode]]
    inner[18] = 0
    inner[27] = 1
    inner[30] = [4]
    _g.apply_chat_persistence_flags(inner)
    inner[53] = 0
    ruuid = str(_uuid.uuid4()).upper()
    _set_request_uuid(ruuid)
    inner[59] = ruuid       # 与 x-goog-ext-525005358-jspb 同源
    inner[61] = []
    inner[68] = 2           # 上游原为 1，官网为 2
    inner[79] = model_id
    inner[91] = 0           # 上游未设置
    inner[96] = 0           # 上游未设置
    inner[98] = 1           # 2026-09-19 官网实测尾部为 1（inner[97] 保持 null）
    if extra_fields:
        for k, v in extra_fields.items():
            inner[k] = v
    outer = [None, json.dumps(inner)]
    params = {"f.req": json.dumps(outer)}
    if CONFIG.get("xsrf_token"):
        params["at"] = CONFIG["xsrf_token"]
    return urllib.parse.urlencode(params)


# ─── 4. 响应元数据解析 ─────────────────────────────────────────────────────
_orig_extract_texts = _g._extract_texts_from_line


def _extract_texts_from_line(line: str) -> list:
    """一次 json.loads 同时产出文本与元数据。

    官网响应帧结构（实测）：
      inner[1]  = ["c_xxx", "r_xxx"]        会话 ID / 响应 ID
      inner[5]  = ["United States", "SWML_DESCRIPTION_FROM_YOUR_INTERNET_ADDRESS", ...]
      inner[8]  = "US"                       出口 IP 国家码
      inner[42] = "3.5 Flash-Lite"           实际服务的模型名
    所有下标读取都做存在性与类型校验，取不到就跳过。
    """
    if '"wrb.fr"' not in line or len(line) < 200:
        return []
    try:
        arr = json.loads(line)
        inner_str = arr[0][2]
        if not inner_str or len(inner_str) < 50:
            return []
        inner = json.loads(inner_str)
    except (json.JSONDecodeError, IndexError, TypeError):
        return []
    if not (isinstance(inner, list) and len(inner) > 4):
        return []

    # —— 元数据提取（失败不影响文本返回）——
    try:
        ids = inner[1]
        if isinstance(ids, list) and len(ids) >= 2:
            if isinstance(ids[0], str) and ids[0]:
                _store_meta(conversation_id=ids[0])
            if isinstance(ids[1], str) and ids[1]:
                _store_meta(response_id=ids[1])
        if len(inner) > 42 and isinstance(inner[42], str) and inner[42]:
            _store_meta(served_model=inner[42])
        if len(inner) > 8:
            geo = inner[5]
            if isinstance(geo, list) and geo and isinstance(geo[0], str) and geo[0]:
                _store_meta(region=geo[0])
            if isinstance(inner[8], str) and inner[8]:
                _store_meta(region_code=inner[8])
    except Exception:
        pass

    # —— 文本提取（与上游语义保持一致）——
    if not (len(inner) > 4 and inner[4]):
        return []
    texts = []
    for part in inner[4]:
        if isinstance(part, list) and len(part) > 1 and part[1] and isinstance(part[1], list):
            for t in part[1]:
                if isinstance(t, str) and t:
                    texts.append(t)
    return texts


# ─── 5. BL 版本号后台定期刷新 ──────────────────────────────────────────────
_bl_thread = None
_bl_stop = threading.Event()


def _bl_loop(interval: int) -> None:
    while not _bl_stop.is_set():
        if _bl_stop.wait(interval):
            break
        try:
            new_bl = _g.fetch_latest_bl()
        except Exception as e:  # 刷新失败绝不影响在途请求
            _g.log(f"BL refresh error (keep {CONFIG.get('gemini_bl')}): {e}")
            continue
        if new_bl and new_bl != CONFIG.get("gemini_bl"):
            _g.log(f"BL periodic refresh: {CONFIG['gemini_bl']} -> {new_bl}")
            CONFIG["gemini_bl"] = new_bl


def start_bl_refresher(interval: int = None) -> bool:
    """启动 BL 定期刷新守护线程。返回 True 表示本次调用启动了新线程。"""
    global _bl_thread
    if _bl_thread is not None and _bl_thread.is_alive():
        return False
    if interval is None:
        interval = CONFIG.get("bl_refresh_sec") or 21600
    try:
        interval = max(300, int(interval))
    except (TypeError, ValueError):
        interval = 21600
    _bl_stop.clear()
    _bl_thread = threading.Thread(
        target=_bl_loop, args=(interval,), name="gemini-bl-refresh", daemon=True)
    _bl_thread.start()
    return True


def stop_bl_refresher() -> None:
    _bl_stop.set()


# ─── 6. 非流式统一到 httpx（连接复用）──────────────────────────────────────
_orig_generate = _g.generate


def _httpx_post_raw(client, url: str, body: bytes, headers: dict) -> str:
    resp = client.post(url, content=body, headers=headers)
    if resp.status_code == 405:
        raise _g_http_error(405, resp.text)
    resp.raise_for_status()
    return resp.text


class _FakeHTTPError(Exception):
    """让 httpx 路径复用上游既有的 405→刷 BL 重试分支。"""

    def __init__(self, code, text=""):
        super().__init__(f"HTTP {code}")
        self.code = code
        self.body = text


def _g_http_error(code, text):
    return _FakeHTTPError(code, text)


def generate(prompt, model_id, think_mode, file_refs=None, extra_fields=None) -> str:
    """非流式生成：httpx 可用时走共享客户端，否则回落上游 urllib 实现。

    带续接 ID 时若命中续接类错误，清掉 ID 按无状态重试一次。
    """
    cont_used = get_continuation()
    try:
        return _generate_once(prompt, model_id, think_mode, file_refs, extra_fields)
    except _g.BardError as e:
        if not (cont_used and e.code in _CONTINUATION_FAILURE_CODES):
            raise
        _g.log(f"continuation failed ({e.code}); retrying stateless")
        set_continuation(None, None)
        return _generate_once(prompt, model_id, think_mode, file_refs, extra_fields)


def _generate_once(prompt, model_id, think_mode, file_refs=None, extra_fields=None) -> str:
    client = _g._get_httpx_client() if _g.HAS_HTTPX else None
    if client is None:
        reset_meta()
        text = _orig_generate(prompt, model_id, think_mode, file_refs, extra_fields)
        _store_meta(prompt_chars=len(prompt or ""), response_chars=len(text or ""))
        return text

    reset_meta()
    # 必须经 `_g.` 间接调用而非用本模块局部函数名：xsrf.py 会在本模块之后
    # 安装它自己的 `_build_payload` 包装（把 at 参数追到 body 上），
    # 只有走模块属性才能与其正确组合。
    body = _g._build_payload(
        prompt, model_id, think_mode, file_refs, extra_fields).encode()
    url = _g._get_url()
    headers = _g._build_headers()
    attempts = CONFIG.get("retry_attempts", 1) or 1
    delay = CONFIG.get("retry_delay_sec", 2)

    last_err = None
    for attempt in range(attempts):
        try:
            raw = _httpx_post_raw(client, url, body, headers)
            text = _g.extract_response_text(raw)
            _store_meta(prompt_chars=len(prompt or ""), response_chars=len(text or ""))
            return text
        except _g.BardError as e:
            last_err = e
            if e.code not in _g._TRANSIENT_BARD_ERRORS:
                raise
            if attempt < attempts - 1:
                _g.log(f"Retry {attempt+1}/{attempts}: BardErrorInfo [{e.code}]")
                time.sleep(delay)
        except _FakeHTTPError as e:
            last_err = e
            if e.code == 405 and _g.update_bl_if_needed():
                url = _g._get_url()
                headers = _g._build_headers()
                _g.log("Retrying with updated BL...")
                continue
            if e.code in (400, 403) and _feed_xsrf(e.body):
                continue
            if attempt < attempts - 1:
                _g.log(f"Retry {attempt+1}/{attempts}: HTTP {e.code}")
                time.sleep(delay)
        except Exception as e:
            last_err = e
            # httpx 的 HTTPStatusError 带 .response.text，交给 xsrf 自愈
            resp = getattr(e, "response", None)
            status = getattr(resp, "status_code", 0)
            if status in (400, 403) and _feed_xsrf(getattr(resp, "text", "")):
                continue
            if attempt < attempts - 1:
                _g.log(f"Retry {attempt+1}/{attempts}: {e}")
                time.sleep(delay)
    raise last_err


def _feed_xsrf(text):
    """把带新 xsrf token 的响应体交给 xsrf 层缓存，返回 True 表示可重试。

    钩子由 xsrf.install() 挂在 `_g._xsrf_maybe_handle` 上；未安装（纯上游
    部署）时静默跳过，不影响原有行为。
    """
    handler = getattr(_g, "_xsrf_maybe_handle", None)
    if not handler or not text:
        return False
    try:
        return bool(handler(text))
    except Exception:
        return False


# ─── 7. 流式：仅补 reset_meta 与 finally flush，文本逻辑仍走上游 ────────────
_orig_generate_stream = _g.generate_stream


def generate_stream(prompt, model_id, think_mode, file_refs=None, extra_fields=None):
    reset_meta()
    cont_used = get_continuation()
    emitted = 0
    try:
        try:
            for delta in _orig_generate_stream(
                    prompt, model_id, think_mode, file_refs, extra_fields):
                emitted += len(delta or "")
                yield delta
        except _g.BardError as e:
            # 仅在尚未输出任何内容时才降级重试，避免重复输出
            if not (cont_used and emitted == 0
                    and e.code in _CONTINUATION_FAILURE_CODES):
                raise
            _g.log(f"stream continuation failed ({e.code}); retrying stateless")
            set_continuation(None, None)
            for delta in _orig_generate_stream(
                    prompt, model_id, think_mode, file_refs, extra_fields):
                emitted += len(delta or "")
                yield delta
    finally:
        _store_meta(prompt_chars=len(prompt or ""), response_chars=emitted)
        # 通知 SSE 改写包装器：流已结束，把暂存的块强制 flush，保证不丢字节
        writer = getattr(_tls, "sse_writer", None)
        if writer is not None:
            try:
                writer.finish()
            except Exception:
                pass


# ─── 9. 认证态相关的错误码处置 ─────────────────────────────────────────────
# 实测（2026-09-01，带 Cookie）：
#   * 1099 是**瞬时**错误 —— 推送 Cookie 后首个请求报 1099，紧接着 6/6 全成功；
#     社区描述也指向"认证握手/会话冲突"类抖动。故与 1060 一样纳入重试。
#   * 1003 的原文案说"先配 Cookie"，但**配了 Cookie 仍可能收到 1003** ——
#     那意味着 Google 已把该会话降级为匿名（Cookie 失效/被风控），照原文案提示
#     会把用户引向错误方向，故按实际状态改写。
_TRANSIENT_CODES_WITH_COOKIE = frozenset({1060, 1099})

# 会话续接失败的错误码（实测）：1096 匿名续接被拒、1097 旧文档记录的续接拒绝、
# 1003 引用不被接受（含伪造 ID）。命中这些且本次确实带了续接 ID 时，
# 清掉续接按无状态方式重试一次 —— 续接是优化，不该因为它把可用请求变成报错。
_CONTINUATION_FAILURE_CODES = frozenset({1096, 1097, 1003})

# 文案必须与"当前是否已配 Cookie"无关：install() 执行时 Cookie 往往还没推送进来，
# 按安装时状态定文案会永远停在错误的"请先配置 Cookie"上。
_REVISED_HINTS = {
    # 实测修正（2026-09-01）：1003 在**认证态明确有效**时依然出现 —— 同一份 Cookie
    # 下 served=3.1 Pro、缺 at 返回 400，但带图请求仍报 1003。所以 1003 与登录态
    # 无关，是上游 file binding 链路本身未被 Gemini 接受（上游标注 WIP）。
    # 之前写成"Cookie 失效/被降级"会把用户引向错误方向，故按实测改回准确表述。
    # 实测（2026-09-01）1003 是通用的"引用不被接受"：伪造的会话续接 ID 与
    # 附件引用都会触发它，且带有效 Cookie 时附件仍被拒 —— 与登录态无关。
    1003: ("Gemini 拒绝了请求里的引用（附件 file_refs 或会话续接 ID）。"
           "附件路径在有效登录态下仍被拒，属上游 file binding 未打通；"
           "若你传了 gemini_conversation_id，请确认它来自上一次真实响应"),
    # 匿名续接实测返回 1096（既有文档写的 1097 未复现，一并保留兼容）
    1096: "Gemini 拒绝匿名会话续接：续接需要有效登录态，请配置 Cookie 或改为携带完整历史",
    1099: ("Gemini 认证握手抖动（瞬时，已自动重试）。若持续出现，通常说明 Cookie 已失效，"
           "请在浏览器里重新登录 Gemini 后用扩展再推送一次"),
}


def _patch_bard_error_semantics() -> None:
    """扩展瞬时错误集合 + 修正 1003/1099 的提示文案。"""
    try:
        _g._TRANSIENT_BARD_ERRORS = _TRANSIENT_CODES_WITH_COOKIE
    except Exception:
        pass
    hints = getattr(_g, "_BARD_ERROR_HINTS", None)
    if isinstance(hints, dict):
        hints.update(_REVISED_HINTS)


# ─── 10. 从请求里捕获续接会话 ID ───────────────────────────────────────────
# 上游各 handler 都先调 `self._parse_body(body)` 拿请求，这是唯一的公共入口，
# 在这里把 gemini_conversation_id / gemini_response_id 摘出来登记到 thread-local，
# 就不必复制上游那 100 多行 _handle_chat。客户端把上一次响应里的这两个字段
# 原样带回即可续接（响应字段由 server.py 的注入逻辑提供）。
_orig_parse_body = None


def _patched_parse_body(self, body):
    req = _orig_parse_body(self, body)
    try:
        if isinstance(req, dict):
            cid = req.get("gemini_conversation_id") or req.get("conversation_id")
            rid = req.get("gemini_response_id") or req.get("response_id")
            set_continuation(cid, rid)
    except Exception:
        pass
    return req


def _install_continuation_hook() -> None:
    global _orig_parse_body
    try:
        import gemini_web2api.server as _s
        cls = getattr(_s, "GeminiHandler", None)
        if cls is None or _orig_parse_body is not None:
            return
        _orig_parse_body = cls._parse_body
        cls._parse_body = _patched_parse_body
    except Exception:
        pass


# ─── 安装 ──────────────────────────────────────────────────────────────────
_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    _g._build_headers = _build_headers
    _g._get_url = _get_url
    _g._build_payload = _build_payload
    _g._extract_texts_from_line = _extract_texts_from_line
    _patch_bard_error_semantics()
    _install_continuation_hook()
    _g.generate = generate
    _g.generate_stream = generate_stream
    # server.py 是 `from .gemini import generate, generate_stream` 按值绑定，
    # 必须同步替换，否则 HTTP 处理路径仍用旧函数。
    try:
        import gemini_web2api.server as _s
        _s.generate = generate
        _s.generate_stream = generate_stream
    except Exception:
        pass
    _installed = True


# ─── 8. 模型目录对齐与诚实化 ─────────────────────────────────────────────
# 对齐记录（2026-09-08，官方 API 文档 ai.google.dev/gemini-api/docs/models 实测）：
#   官方已发布的 Flash 系：gemini-3.8-flash / 3.7 / 3.6 / 3.5 / 3.5-flash-lite /
#   3.1-flash-lite ...。3.8-flash 已出现在官方模型表并排首位（早前检索显示它还在
#   内部测试，文档现确认发布）。
#   网页端（BardChatUi）没有"按名字路由"的通道 —— 只有 mode 枚举，且 Google 会把
#   FAST 档（mode=1）滚动指向当下最新 Flash。所以：
#     * 请求名只是"档位意图"，实际服务版本看响应 served_model；
#     * 2026-09-01 带 Cookie 实测：mode=1 曾落到 3.1 Pro / 3.6 Flash ——
#       档位与版本号之间由 Google 侧决定，不能保证精确命中请求名；
#     * 匿名恒为 3.5 Flash-Lite（服务端封顶）。
# 注意：必须**原地 mutate** MODELS 这个 dict。上游 server.py 用
# `from .models import MODELS` 按值绑定了该对象，重新绑定名字它看不到。
_ANON_CAP_NOTE = "匿名模式实测被服务端封顶为 3.5 Flash-Lite"
_ROLL_NOTE = ("网页端按档位路由且档位会滚动到最新 Flash，"
              "实际服务版本以响应 served_model 为准，无法保证精确命中请求名")

_MODEL_CATALOG = {
    "gemini-3.8-flash": (1, 4,
        "官方 API 已发布的当前最新 Flash（2026-09-08 文档确认，排模型表首位）。"
        f"经网页端 mode=1 档请求；{_ROLL_NOTE}；{_ANON_CAP_NOTE}，需 Cookie"),
    "gemini-3.7-flash": (1, 4,
        "属 mode=1 档位别名而非独立模型（与 gemini-3.6/3.5 同档，官方 API 才是"
        f"独立端点；官网模式菜单里也只列出 3.5 Flash-Lite / 3.6 Flash / 3.1 Pro）；"
        f"{_ROLL_NOTE}；{_ANON_CAP_NOTE}，需 Cookie 才可能真实路由"),
    "gemini-3.6-flash": (1, 4,
        f"mode=1 档位名（官方 API 独立端点）；{_ROLL_NOTE}；{_ANON_CAP_NOTE}"),
    "gemini-3.5-flash": (1, 4,
        f"mode=1 档位名（官方 API 独立端点）；{_ROLL_NOTE}；{_ANON_CAP_NOTE}"),
    "gemini-3.5-flash-thinking": (2, 0,
        f"深度思考档（mode=2）；{_ROLL_NOTE}；{_ANON_CAP_NOTE}，需 Cookie"),
    "gemini-3.1-pro": (3, 4,
        "高级推理档（mode=3），对应官网菜单「3.1 Pro」（官方 API 端点为 "
        f"gemini-3.1-pro-preview）。{_ANON_CAP_NOTE}，必须配置 Cookie 才可能真实路由"),
    "gemini-3.1-pro-enhanced": (3, 4,
        f"Pro 增强输出实验档（mode=3 + 额外字段）；{_ANON_CAP_NOTE}，需 Cookie"),
    "gemini-auto": (4, 4,
        f"自动选档（mode=4）；{_ANON_CAP_NOTE}"),
    "gemini-3.5-flash-thinking-lite": (5, 0,
        f"动态思考档（mode=5）；{_ANON_CAP_NOTE}，需 Cookie"),
    "gemini-3.5-flash-lite": (6, 4,
        "官方 API 的 lite 档命名，与 gemini-flash-lite 同为 mode=6。"
        f"{_ANON_CAP_NOTE}"),
    "gemini-3.1-flash-lite": (6, 4,
        "官方 API 更早的 lite 档命名，同为 mode=6。"
        f"{_ANON_CAP_NOTE}"),
    "gemini-flash-lite": (6, 4,
        f"轻量档（mode=6）；匿名实测唯一真实可用的模型即为此档（3.5 Flash-Lite）"),
}


def install_model_catalog() -> None:
    """把对齐后的模型目录写进上游 MODELS dict（原地 mutate，幂等）。"""
    try:
        from gemini_web2api.models import MODELS
    except Exception:
        return
    for name, (mode, think, desc) in _MODEL_CATALOG.items():
        cfg = MODELS.get(name)
        if cfg is None:
            # 新增键：直接插入（resolve_model 与 /v1/models 都读这个 dict）
            MODELS[name] = {"mode": mode, "think": think, "desc": desc}
        elif isinstance(cfg, dict):
            cfg["desc"] = desc
