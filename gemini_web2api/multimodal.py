"""Multimodal: image upload via Gemini ProcessFile RPC."""
import json
import base64
import urllib.request
import urllib.parse
import time
import ssl

from .config import CONFIG
from .gemini import load_cookie, make_sapisidhash, _get_ssl_ctx, log


def upload_image(image_bytes: bytes, filename: str = "image.png", mime_type: str = "image/png") -> str:
    """Upload image via ProcessFile and return file reference for StreamGenerate."""
    b64_data = base64.b64encode(image_bytes).decode("ascii")

    rk = [None] * 11
    rk[1] = filename
    rk[10] = [b64_data, mime_type, 1]

    process_file_req = [None] * 4
    process_file_req[0] = rk
    process_file_req[2] = 1
    process_file_req[3] = ["en"]

    outer = [None, json.dumps(process_file_req)]
    body = urllib.parse.urlencode({"f.req": json.dumps(outer)}).encode()

    reqid = int(time.time()) % 1000000
    url = (
        "https://gemini.google.com/_/BardChatUi/data/"
        "assistant.lamda.BardFrontendService/ProcessFile"
        f"?bl={CONFIG['gemini_bl']}&hl=en&_reqid={reqid}&rt=c"
    )

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://gemini.google.com",
        "Referer": "https://gemini.google.com/app",
        "X-Same-Domain": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    cookie_str, sapisid = load_cookie()
    if cookie_str:
        headers["Cookie"] = cookie_str
    if sapisid:
        headers["Authorization"] = make_sapisidhash(sapisid)

    ctx = _get_ssl_ctx()
    proxy = CONFIG.get("proxy")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}),
            urllib.request.HTTPSHandler(context=ctx)
        )
        resp = opener.open(req, timeout=CONFIG["request_timeout_sec"])
    else:
        resp = urllib.request.urlopen(req, context=ctx, timeout=CONFIG["request_timeout_sec"])

    raw = resp.read().decode("utf-8", errors="replace")
    file_ref = _parse_process_file_response(raw)
    if not file_ref:
        raise RuntimeError("Failed to extract file reference from ProcessFile response")
    log(f"Image uploaded: {filename} -> {file_ref[:40]}...")
    return file_ref


def _parse_process_file_response(raw: str) -> str:
    """Extract file reference (If) from ProcessFile response."""
    for line in raw.split("\n"):
        if '"wrb.fr"' not in line:
            continue
        try:
            arr = json.loads(line)
            inner_str = arr[0][2]
            if not inner_str:
                continue
            inner = json.loads(inner_str)
            if isinstance(inner, list) and len(inner) > 0:
                dg = inner[0]
                if isinstance(dg, list) and len(dg) > 5:
                    file_ref = dg[5]
                    if isinstance(file_ref, str) and file_ref:
                        return file_ref
        except (json.JSONDecodeError, IndexError, TypeError):
            continue
    return None


def fetch_image_bytes(url: str) -> bytes:
    """Fetch image from URL."""
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        return resp.read()
    except Exception as e:
        log(f"Image fetch failed: {e}")
        return b""
