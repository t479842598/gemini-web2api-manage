"""Request statistics recorder for the admin console.

Records every /v1 generate call (endpoint, model, masked api key, success,
duration, token usage) to an append-only JSONL file in the stable data dir,
then aggregates it on demand for GET /admin/api/stats?range=...

Data source is the JSONL file (single source of truth), so stats survive
service restarts.
"""
import json
import threading
import time
from datetime import datetime
from pathlib import Path

from .admin import data_dir

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB rolling window
DEFAULT_MAX_ENTRIES = 20000

_RANGES = {
    "1d": 86400,
    "3d": 259200,
    "7d": 604800,
    "30d": 2592000,
    "all": None,
}


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 12:
        return key[:7]
    return f"{key[:7]}...{key[-4:]}"


def endpoint_from_path(path: str) -> str:
    if "streamGenerateContent" in path:
        return "google-stream"
    if ":generateContent" in path:
        return "google"
    if path.startswith("/v1/responses"):
        return "responses"
    return "chat"


class CapturingWriter:
    """Wraps the handler's wfile to capture the response body up to a cap.

    Forwards all writes/flushes to the original stream, so upstream behavior
    is unchanged; the captured bytes are used to extract model / usage / error
    for statistics.
    """

    def __init__(self, original, max_bytes: int = 256 * 1024):
        self.original = original
        self.max_bytes = max_bytes
        self.buffer = bytearray()
        self.capture_ok = True

    def write(self, data):
        self.original.write(data)
        if self.capture_ok:
            remaining = self.max_bytes - len(self.buffer)
            if remaining > 0:
                self.buffer.extend(data[:remaining])
            else:
                self.capture_ok = False  # stop capturing further chunks

    def flush(self):
        self.original.flush()


def parse_captured(buffer: bytes):
    """Best-effort extraction of {model, usage, ok} from a captured response.

    Handles both plain JSON bodies and SSE streams (looks at every data line).
    """
    model = None
    usage = {}
    ok = True
    text = buffer.decode("utf-8", errors="replace")
    # Strip HTTP response headers (send_response writes headers via wfile too)
    sep = text.find("\r\n\r\n")
    if sep >= 0:
        head, _, _ = text.partition("\r\n\r\n")
        status_line = head.split("\r\n", 1)[0] if head else ""
        if " 200" not in status_line:
            ok = False
        text = text[sep + 4:]
    candidates = []
    if text.lstrip().startswith("{") and "\n" not in text[:2000]:
        candidates = [text]
    else:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload and payload != "[DONE]" and payload.startswith("{"):
                    candidates.append(payload)
    for cand in candidates:
        try:
            data = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if "error" in data and data["error"]:
            ok = False
        if not model:
            model = (
                data.get("model")
                or data.get("modelVersion")
                or (data.get("response") or {}).get("model")
            )
        usage.update(_extract_usage(data))
    return {"model": model, "usage": usage, "ok": ok}


def _extract_usage(data: dict) -> dict:
    usage = {}
    if isinstance(data.get("usage"), dict):
        u = data["usage"]
        for src, dst in (
            ("prompt_tokens", "prompt"),
            ("completion_tokens", "completion"),
            ("total_tokens", "total"),
            ("input_tokens", "prompt"),
            ("output_tokens", "completion"),
        ):
            if u.get(src) is not None:
                usage[dst] = int(u[src])
    if isinstance(data.get("usageMetadata"), dict):
        um = data["usageMetadata"]
        if um.get("promptTokenCount") is not None:
            usage["prompt"] = int(um["promptTokenCount"])
        if um.get("candidatesTokenCount") is not None:
            usage["completion"] = int(um["candidatesTokenCount"])
        if um.get("totalTokenCount") is not None:
            usage["total"] = int(um["totalTokenCount"])
    return usage


class RequestRecorder:
    def __init__(self, log_path: Path = None, max_bytes: int = DEFAULT_MAX_BYTES,
                 max_entries: int = DEFAULT_MAX_ENTRIES):
        self._lock = threading.Lock()
        self._max_bytes = max_bytes
        self._max_entries = max_entries
        self._log_path = Path(log_path) if log_path else (data_dir() / "requests.jsonl")

    def record(self, *, endpoint: str, model, api_key, success: bool,
               duration_ms: int, usage: dict):
        entry = {
            "ts": int(time.time() * 1000),
            "endpoint": endpoint or "unknown",
            "model": model or "",
            "api_key": api_key or "",
            "ok": bool(success),
            "duration_ms": int(duration_ms),
            "usage": usage or {},
        }
        try:
            line = json.dumps(entry, ensure_ascii=False) + "\n"
            with self._lock:
                self._log_path.parent.mkdir(parents=True, exist_ok=True)
                with self._log_path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                self._maybe_truncate()
        except OSError:
            pass

    def _maybe_truncate(self):
        try:
            if self._log_path.stat().st_size > self._max_bytes:
                lines = self._log_path.read_text(
                    encoding="utf-8", errors="replace").splitlines()
                keep = lines[-self._max_entries:]
                with self._log_path.open("w", encoding="utf-8") as fh:
                    fh.write("\n".join(keep) + "\n")
        except OSError:
            pass

    def load_entries(self, limit: int = None) -> list:
        if not self._log_path.exists():
            return []
        limit = limit or self._max_entries
        try:
            lines = self._log_path.read_text(
                encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue
        return entries

    def query_stats(self, range_key: str) -> dict:
        range_key = range_key if range_key in _RANGES else "7d"
        window = _RANGES[range_key]
        now = time.time()
        entries = []
        for e in self.load_entries():
            if window is not None and (now - e.get("ts", 0) / 1000.0) > window:
                continue
            entries.append(e)

        total = len(entries)
        success = sum(1 for e in entries if e.get("ok"))
        error = total - success
        total_tokens = sum((e.get("usage") or {}).get("total") or 0 for e in entries)
        prompt_tokens = sum((e.get("usage") or {}).get("prompt") or 0 for e in entries)
        completion_tokens = sum((e.get("usage") or {}).get("completion") or 0 for e in entries)
        durations = [e.get("duration_ms") or 0 for e in entries]
        avg_duration = int(sum(durations) / len(durations)) if durations else 0

        def bucket_by(e, key):
            return e.get(key) or "未知"

        def aggregate(key):
            agg = {}
            for e in entries:
                k = bucket_by(e, key)
                item = agg.setdefault(k, {
                    "count": 0, "prompt_tokens": 0, "completion_tokens": 0,
                    "total_tokens": 0, "success": 0,
                })
                u = e.get("usage") or {}
                item["count"] += 1
                item["prompt_tokens"] += u.get("prompt") or 0
                item["completion_tokens"] += u.get("completion") or 0
                item["total_tokens"] += u.get("total") or 0
                if e.get("ok"):
                    item["success"] += 1
            return agg

        return {
            "ok": True,
            "range": range_key,
            "total": total,
            "success": success,
            "error": error,
            "success_rate": round(success / total, 4) if total else 0,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "avg_duration_ms": avg_duration,
            "by_model": aggregate("model"),
            "by_api_key": aggregate("api_key"),
            "by_endpoint": aggregate("endpoint"),
            "trend": self._trend(entries, range_key),
        }

    def _trend(self, entries: list, range_key: str) -> list:
        hourly = range_key == "1d"
        buckets = {}
        for e in entries:
            try:
                dt = datetime.fromtimestamp(e.get("ts", 0) / 1000.0)
            except (ValueError, OSError):
                continue
            key = dt.strftime("%Y-%m-%d %H:00" if hourly else "%Y-%m-%d")
            item = buckets.setdefault(key, {"bucket": key, "count": 0, "success": 0})
            item["count"] += 1
            if e.get("ok"):
                item["success"] += 1
        return [buckets[k] for k in sorted(buckets)]


recorder = RequestRecorder()
