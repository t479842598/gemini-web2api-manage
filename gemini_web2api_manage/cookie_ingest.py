"""Cookie 获取与应用层（spec 04-00）。

解决三个实际痛点：
  1. 浏览器控制台里 `document.cookie` **取不到 HttpOnly cookie**，而本项目鉴权
     最关键的 `SAPISID` / `__Secure-1PSID` / `__Secure-3PSID` 全是 HttpOnly，
     所以"控制台脚本自动提取"这条路对用户根本走不通 —— 只能靠扩展的
     `chrome.cookies.getAll()`（见 tools/gemini-cookie-sync/）。
  2. Chrome「Application → Cookies」面板一条一行，手工拼 `k=v; k=v` 极易出错。
  3. 上游扩展只导出一个 `gemini-auth.json` 文件，之后还要 cp 到项目、用 jq 把
     `cookie_file` / `auth_user` / `xsrf_token` / `gemini_bl` 四个键写进
     config.json 再重启 —— 服务在远程机器时这条链路基本走不通。

本模块提供两个能力：
  * `normalize_cookie_input(text)` —— 宽容识别四种输入并归一为纯 cookie 串，
    放在服务端，所以 React 管理台**不改前端**就能直接粘 cURL。
  * `apply_cookie(...)` —— 写盘 + 更新 CONFIG + 落 config.json + 清上游缓存，
    做到"推送即生效、重启不丢"，任一环节失败回滚原值。

安全：cookie 串等同 Google 登录态。本模块任何日志与返回值都不得回显明文，
只回条数与关键字段的存在性。
"""
import json
import re
import time

# Cookie 名允许的字符（RFC 6265 token 集）
_NAME_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")

# cURL 里携带 cookie 的选项
_COOKIE_FLAGS = {"-b", "--cookie"}
# cURL 里可能装著 Cookie: 头的选项
_HEADER_FLAGS = {"-H", "--header"}

# 归一后可丢弃的噪声项（对鉴权无意义且体积大）
_DROP_NAMES = frozenset()


def detect_format(text: str) -> str:
    """识别输入形态：json / curl / header / raw / empty。"""
    s = (text or "").strip()
    if not s:
        return "empty"
    if s[0] in "{[":
        return "json"
    low = s.lower()
    if "curl " in low[:200] or low.startswith("curl"):
        return "curl"
    if low.startswith("cookie:"):
        return "header"
    # DevTools 复制的整块请求头：含 cookie: 行且还有其他请求头行。
    # 必须带 re.I —— 实际头部是 `Cookie:` 大写开头，漏了大小写不敏感
    # 会让整块输入落到 raw 分支，把 `charset=UTF-8` 当成 cookie 名。
    if (re.search(r"(?m)^\s*cookie\s*:", s, re.I)
            and re.search(r"(?m)^\s*[\w-]+\s*:", s)):
        return "header"
    return "raw"


def _shell_tokenize(s: str) -> list:
    """按 shell 语义切词，支持单引号、双引号与反斜杠转义。

    DevTools 的「Copy as cURL」是带续行反斜杠的 shell 命令，必须按引号感知
    地切，否则 cookie 值里的特殊字符会把解析带偏。
    """
    # 先合并续行反斜杠：`\` + 换行
    s = re.sub(r"\\\r?\n", " ", s)
    toks, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t\n":
            i += 1
            continue
        buf, quote = [], None
        while i < n:
            c = s[i]
            if quote == "'":
                if c == "'":
                    quote = None
                else:
                    buf.append(c)
            elif quote == '"':
                if c == '"':
                    quote = None
                elif c == "\\" and i + 1 < n:
                    buf.append(s[i + 1])
                    i += 2
                    continue
                else:
                    buf.append(c)
            else:
                if c == "'":
                    quote = "'"
                elif c == '"':
                    quote = '"'
                elif c == "\\" and i + 1 < n:
                    buf.append(s[i + 1])
                    i += 2
                    continue
                elif c in " \t\n":
                    break
                else:
                    buf.append(c)
            i += 1
        toks.append("".join(buf))
    return toks


def _parse_pairs(s: str) -> list:
    """把 `k=v; k=v` / 换行分隔 / `Cookie:` 前缀形式解析成 [(name, value)]。"""
    out = []
    if not s:
        return out
    s = re.sub(r"^\s*cookie\s*:\s*", "", s, flags=re.I)
    for chunk in re.split(r"[;\n\r]", s):
        chunk = chunk.strip().rstrip(";").strip()
        if not chunk or "=" not in chunk:
            continue
        name, value = chunk.split("=", 1)
        name = name.strip().strip("\"'")
        value = value.strip().strip("\"'")
        if not name or not value:
            continue
        if not _NAME_RE.match(name):
            continue
        out.append((name, value))
    return out


def _dedupe(pairs: list) -> list:
    """同名保留首次出现（浏览器里更具体的域优先，扩展已排过序）。"""
    seen, out = set(), []
    for name, value in pairs:
        if name in _DROP_NAMES or name in seen:
            continue
        seen.add(name)
        out.append((name, value))
    return out


def _render(pairs: list) -> str:
    return "; ".join(f"{k}={v}" for k, v in pairs)


def _from_curl(text: str):
    """从 DevTools「Copy as cURL」里抽 cookie。

    支持 `-b '<cookie>'`、`--cookie "<cookie>"`、`-H 'Cookie: <cookie>'`、
    `--header 'cookie: <cookie>'`。多个来源合并，先出现的优先。
    """
    toks = _shell_tokenize(text)
    chunks = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in _COOKIE_FLAGS and i + 1 < len(toks):
            chunks.append(toks[i + 1])
            i += 2
            continue
        if t in _HEADER_FLAGS and i + 1 < len(toks):
            hv = toks[i + 1]
            m = re.match(r"^\s*cookie\s*:\s*(.*)$", hv, flags=re.I | re.S)
            if m:
                chunks.append(m.group(1))
            i += 2
            continue
        # `--cookie=value` 形式
        if t.startswith("--cookie="):
            chunks.append(t.split("=", 1)[1])
        i += 1
    pairs = []
    for c in chunks:
        pairs.extend(_parse_pairs(c))
    return _dedupe(pairs)


def _from_header_block(text: str):
    """从 `Cookie: ...` 头（或整块请求头）里抽 cookie 行。"""
    lines = text.replace("\\\n", "\n").splitlines()
    collected, capture = [], False
    buf = ""
    for line in lines:
        m = re.match(r"^\s*cookie\s*:\s*(.*)$", line, flags=re.I)
        if m:
            capture, buf = True, m.group(1)
            continue
        if capture:
            # 折叠的续行以空白开头，属于同一个头值
            if line[:1] in (" ", "\t") and line.strip():
                buf += "; " + line.strip()
                continue
            capture = False
        if not line.strip() or re.match(r"^\s*[\w-]+\s*:", line):
            continue
    if buf:
        collected.append(buf)
    if not collected:
        # 没有显式 Cookie: 前缀时，整段当作裸串试一次
        collected.append(text)
    pairs = []
    for c in collected:
        pairs.extend(_parse_pairs(c))
    return _dedupe(pairs)


def normalize_cookie_input(text: str):
    """宽容识别并归一 cookie 输入。

    返回 `(cookie_str, extras)`：
      * `cookie_str` —— 归一后的 `name=value; name=value`，失败为 ""
      * `extras`     —— 仅 JSON 来源会带：`sapisid` / `auth_user` /
                        `xsrf_token` / `gemini_bl`（只放非空值）
    """
    fmt = detect_format(text)
    extras = {}
    if fmt == "empty":
        return "", extras
    if fmt == "json":
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            data = None
        if isinstance(data, dict):
            for k in ("sapisid", "xsrf_token", "gemini_bl"):
                v = data.get(k)
                if isinstance(v, str) and v.strip():
                    extras[k] = v.strip()
            if data.get("auth_user") is not None and data.get("auth_user") != "":
                try:
                    extras["auth_user"] = int(data["auth_user"])
                except (TypeError, ValueError):
                    pass
            inner = data.get("cookie") or data.get("cookie_string") or ""
            pairs = _parse_pairs(inner)
            if not pairs and isinstance(data.get("cookies"), list):
                for item in data["cookies"]:
                    if isinstance(item, dict) and item.get("name") and item.get("value"):
                        pairs.append((str(item["name"]), str(item["value"])))
            if not pairs and inner:
                # cookie 字段不是 k=v 形态时，退一步整段再试
                pairs = _parse_pairs(str(inner))
        elif isinstance(data, list):
            pairs = []
            for item in data:
                if isinstance(item, dict) and item.get("name") and item.get("value"):
                    pairs.append((str(item["name"]), str(item["value"])))
        else:
            pairs = _parse_pairs(text)
        pairs = _dedupe(pairs)
        if not extras.get("sapisid"):
            for n, v in pairs:
                if n == "SAPISID":
                    extras["sapisid"] = v
                    break
        return _render(pairs), extras

    if fmt == "curl":
        pairs = _from_curl(text)
    elif fmt == "header":
        pairs = _from_header_block(text)
    else:
        pairs = _dedupe(_parse_pairs(text))
    return _render(pairs), extras


def summarize(cookie_str: str) -> dict:
    """给响应/日志用的安全摘要 —— 只含条数与存在性，绝不含明文。"""
    pairs = _dedupe(_parse_pairs(cookie_str or ""))
    names = {n for n, _ in pairs}
    return {
        "cookie_count": len(pairs),
        "cookie_length": len(cookie_str or ""),
        "names": sorted(names),
        "has_sapisid": "SAPISID" in names,
        "has_session_psid": bool(
            {"__Secure-1PSID", "__Secure-3PSID", "SID"} & names),
    }


# ─── 应用 ──────────────────────────────────────────────────────────────────
class CookieApplyError(RuntimeError):
    pass


def clear_upstream_cookie_cache() -> None:
    """重置上游 `load_cookie()` 的 mtime 缓存，保证不重启即用新 cookie。

    上游按文件 mtime 判断是否重读；我们写的是**新文件**（新路径），若不清
    缓存，进程内仍会持有旧串。
    """
    try:
        import gemini_web2api.gemini as _g
        cache = getattr(_g, "_cookie_cache", None)
        if isinstance(cache, dict):
            cache.update({"str": "", "sapisid": None, "mtime": 0})
    except Exception:
        pass


def apply_cookie(cookie_str: str, extras: dict = None, *, label: str = None,
                 persist: bool = True) -> dict:
    """把一份 cookie 应用到运行中的服务并（可选）落盘。

    写 cookies/cookie_N.txt → 更新 CONFIG 的 cookie_file/cookie_files →
    同步 auth_user / xsrf_token / gemini_bl（仅当来源携带且非空）→ 落盘
    config.json → 清上游缓存。任一写盘失败则回滚 CONFIG 原值并抛错。

    返回安全摘要（不含 cookie 明文）。
    """
    # 延迟导入：admin.py 在 save_config 里会反向调用本模块，避免模块级循环
    from .admin import cookies_dir, writable_config_path, _next_cookie_index
    from .config import CONFIG

    extras = extras or {}
    cookie_str = (cookie_str or "").strip()
    if not cookie_str:
        raise CookieApplyError("cookie 内容为空或无法解析")

    root = cookies_dir()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise CookieApplyError(f"无法创建 cookie 目录：{e}")

    # 备份将被修改的 CONFIG 原值，失败时回滚
    snapshot = {
        "cookie_file": CONFIG.get("cookie_file"),
        "cookie_files": list(CONFIG.get("cookie_files") or []),
        "auth_user": CONFIG.get("auth_user"),
        "xsrf_token": CONFIG.get("xsrf_token"),
        "gemini_bl": CONFIG.get("gemini_bl"),
    }

    target = None
    try:
        index = _next_cookie_index(root)
        while (root / f"cookie_{index}.txt").exists():
            index += 1
        suffix = f"_{label}" if label and re.match(r"^[A-Za-z0-9_-]{1,24}$", label) else ""
        target = root / f"cookie_{index}{suffix}.txt"
        target.write_text(cookie_str + "\n", encoding="utf-8")
        try:
            target.chmod(0o600)
        except OSError:
            pass

        CONFIG["cookie_file"] = str(target)
        # 新 cookie 放到列表首位：上游按 cookie_files 顺序取用
        CONFIG["cookie_files"] = [str(target)] + [
            p for p in (snapshot["cookie_files"] or []) if p != str(target)]

        applied = {}
        if "auth_user" in extras:
            CONFIG["auth_user"] = extras["auth_user"]
            applied["auth_user"] = extras["auth_user"]
        if extras.get("xsrf_token"):
            CONFIG["xsrf_token"] = extras["xsrf_token"]
            applied["xsrf_token"] = True
        if extras.get("gemini_bl"):
            CONFIG["gemini_bl"] = extras["gemini_bl"]
            applied["gemini_bl"] = extras["gemini_bl"]

        if persist:
            cfg_path = writable_config_path()
            try:
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                if cfg_path.exists():
                    (cfg_path.parent / (cfg_path.name + ".pre-push.bak")).write_text(
                        cfg_path.read_text(encoding="utf-8"), encoding="utf-8")
                cfg_path.write_text(
                    json.dumps(_serializable_config(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
            except OSError as e:
                raise CookieApplyError(f"配置落盘失败：{e}")

        clear_upstream_cookie_cache()
        result = summarize(cookie_str)
        result.update({
            "ok": True,
            "cookie_file": str(target),
            "cookie_files": list(CONFIG.get("cookie_files") or []),
            "applied": applied,
            "at": time.time(),
        })
        return result
    except Exception:
        # 回滚 CONFIG，坏推送不能把可用配置搞坏
        CONFIG.update(snapshot)
        if target:
            try:
                target.unlink()
            except OSError:
                pass
        clear_upstream_cookie_cache()
        raise


def _serializable_config() -> dict:
    """导出可 JSON 化的配置（跳过不可序列化项）。"""
    from .config import CONFIG
    out = {}
    for k, v in CONFIG.items():
        try:
            json.dumps(v)
        except (TypeError, ValueError):
            continue
        out[k] = v
    return out
