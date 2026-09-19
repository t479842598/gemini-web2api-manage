#!/usr/bin/env python3
"""把「我们实际会发出的请求」与「官网真实抓包基线」逐字段比对。

用法：
    node tools/capture_baseline.mjs /tmp/gemini_baseline.json   # 先抓基线
    python3 tools/align_check.py /tmp/gemini_baseline.json

退出码 0 = 对齐；1 = 有漂移（逐条列出）。

为什么需要它：官网请求形态（画像版本号、头集合、payload 下标）会随 Google
前端发版漂移，而这类漂移不会立刻报错 —— 只会让指纹悄悄变得不像浏览器。
上次（2026-08-31）的基线到 2026-09-19 已经漂了 5 处，靠人肉 diff 才发现。
"""
import json
import os
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "_upstream"))

import gemini_web2api_manage  # noqa: E402  触发 protocol.install()
import gemini_web2api.gemini as g  # noqa: E402

# 不可比 / 故意不同的头：
#   cookie, authorization      —— 凭据，基线是匿名态
#   content-length             —— 由 payload 长度决定
#   accept-encoding            —— 由 HTTP 客户端自己协商（urllib/httpx 各不同）
#   x-goog-ext-525005358-jspb  —— 含每请求随机 UUID，只比结构
#   x-goog-ext-525001261-jspb  —— 含每请求 UUID + 会话内滚动的时间戳
#   x-browser-validation       —— 官网带的校验和，未逆向出算法，本层故意不伪造
#   user-agent                 —— 基线是 headless Chrome，我们固定发稳定版 UA；
#                                 只比「完整 Chrome/版本段」是否在
#   sec-ch-ua-full-version     —— 官网带引号、我们发裸值（HTTP 头语义等价）
IGNORE = {
    "cookie", "authorization", "content-length", "accept-encoding",
    "x-goog-ext-525005358-jspb", "x-goog-ext-525001261-jspb",
    "x-browser-validation", "user-agent", "sec-ch-ua-full-version",
    # HTTP/2 伪头，curl/urllib 不发，无意义
    ":authority", ":method", ":path", ":scheme",
}

# 这些头“我们发、官网不发”不算错：浏览器的 H2 传输层行为，或我们主动加的兼容头。
ALLOW_EXTRA = {
    "connection", "host", "content-length", "accept-encoding",
    "x-goog-authuser", "at",
}
# 只比「结构」不比「内容」的头
STRUCTURAL = {
    "x-goog-ext-525005358-jspb": lambda v: [len(v), v[1] if len(v) > 1 else None],
    "x-goog-ext-525001261-jspb": lambda v: [len(v)] + [v[i] for i in (0, 3, 7, 8, 10, 14) if i < len(v)],
}

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))


def load_baseline(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def our_request(prompt="1+1等于几？只回答数字。"):
    """用真实代码路径造一份「我们会发出的请求」，不实际发包。"""
    import gemini_web2api.models as m
    _name, model_id, think, err, extra = m.resolve_model("gemini-3.6-flash")
    if err:
        raise SystemExit(f"resolve_model 失败：{err}")
    body = g._build_payload(prompt, model_id, think, extra_fields=extra)
    headers = g._build_headers()
    url = g._get_url()
    form = urllib.parse.parse_qs(body)
    inner = json.loads(json.loads(form["f.req"][0])[1])
    return {"url": url, "headers": headers, "inner": inner, "form": form}


def norm_headers(h):
    return {k.lower(): v for k, v in h.items()}


def compare_headers(base_h, ours_h):
    b, o = norm_headers(base_h), norm_headers(ours_h)
    bk, ok_ = set(b) - IGNORE, set(o) - IGNORE
    missing = sorted(bk - ok_)
    extra = sorted(k for k in ok_ - bk if k not in ALLOW_EXTRA)
    differ = []
    for k in sorted(bk & ok_):
        if k in STRUCTURAL:
            try:
                bv, ov = STRUCTURAL[k](json.loads(b[k])), STRUCTURAL[k](json.loads(o[k]))
            except Exception:
                bv, ov = b[k], o[k]
        else:
            bv, ov = b[k], o[k]
        if str(bv) != str(ov):
            differ.append(f"{k}: 官网={b[k]!r} 我们={o[k]!r}")
    check("请求头集合覆盖官网基线（除凭据/校验和）", not missing,
          ("缺失: " + ", ".join(missing)) if missing else "")
    check("未发送官网没有的头（多发的头也是指纹差异）", not extra,
          ("多发: " + ", ".join(extra)) if extra else "")
    check("共有头取值一致", not differ, "\n        ".join(differ))
    # 基线是 headless Chrome，UA 必然不同；单独校验我们的 UA 形态正确
    ua = o.get("user-agent", "")
    check("UA 含完整 Chrome 段（KHTML, like Gecko + 版本号 + Safari）",
          "(KHTML, like Gecko) Chrome/" in ua and "Safari/537.36" in ua and "Headless" not in ua,
          ua)


def compare_url(base_url, ours_url):
    bq = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(base_url).query))
    oq = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(ours_url).query))
    check("URL query 键集合一致", set(bq) == set(oq),
          f"官网={sorted(bq)} 我们={sorted(oq)}")
    check("URL path 一致",
          urllib.parse.urlparse(base_url).path == urllib.parse.urlparse(ours_url).path,
          f"官网={urllib.parse.urlparse(base_url).path}")


def compare_payload(base_post, ours):
    base_form = urllib.parse.parse_qs(base_post)
    base_inner = json.loads(json.loads(base_form["f.req"][0])[1])
    ours_inner, ours_form = ours["inner"], ours["form"]
    check("payload 内层数组长度与官网一致",
          len(base_inner) == len(ours_inner),
          f"官网={len(base_inner)} 我们={len(ours_inner)}")
    # 每请求随机的下标：3/4（未逆向的 token，负结果：注入无收益，本层故意留 null）、
    # 59（本请求 UUID）。这些不参与逐值比对。
    # 剩下的漂移分两类：我们固定发 gemini_hl（默认 en）、固定默认档（mode=1/think=4），
    # 而基线是「中文界面 + 上次选择的模式」——这属于请求参数差异，不是协议漂移，
    # 单独列出供人判断，不计入失败。
    RANDOM = {3, 4, 59}
    PARAM_DRIFT = {1, 17, 79}   # 语言 / think / mode
    drift, param = [], []
    for i in range(min(len(base_inner), len(ours_inner))):
        bv, ov = base_inner[i], ours_inner[i]
        if i in RANDOM:
            continue
        if bv != ov:
            msg = (f"[{i}] 官网={json.dumps(bv, ensure_ascii=False)[:60]} "
                   f"我们={json.dumps(ov, ensure_ascii=False)[:60]}")
            (param if i in PARAM_DRIFT else drift).append(msg)
    check("payload 逐下标与官网一致（跳过随机下标 3/4/59）",
          not drift, "\n        ".join(drift[:12]))
    if param:
        print("INFO  请求参数差异（非协议漂移，由 gemini_hl / 模型档位决定）:\n        "
              + "\n        ".join(param))
    # at 只在我们持有 xsrf_token 时才发（匿名官网也不发），不参与比对
    check("form 字段集合一致", set(base_form) == set(ours_form),
          f"官网={sorted(base_form)} 我们={sorted(ours_form)}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gemini_baseline.json"
    if not os.path.exists(path):
        print(f"基线文件不存在：{path}\n先跑 node tools/capture_baseline.mjs {path}")
        return 2
    base = load_baseline(path)
    req = base["request"]
    ours = our_request()

    print(f"基线抓取时间: {base.get('captured_at')}")
    print(f"官网 served : {base.get('response_meta', {}).get('served_model')}\n")

    compare_headers(req["headers"], ours["headers"])
    compare_url(req["url"], ours["url"])
    compare_payload(req["postData"], ours)

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
