"""Entry point: python -m gemini_web2api_manage"""
import argparse
import os

from gemini_web2api_manage import __version__
from gemini_web2api_manage.config import CONFIG  # noqa: F401 - loads manage defaults
from gemini_web2api_manage.server import GeminiHandler
from gemini_web2api_manage.admin import config_path as legacy_config_path, writable_config_path
from gemini_web2api_manage import xsrf  # noqa: F401 - installs automatic at-token retry
from gemini_web2api_manage.socks_bridge import apply_proxy_bridge

from gemini_web2api.models import MODELS
from gemini_web2api.gemini import HAS_HTTPX, fetch_latest_bl
from gemini_web2api.config import load_config, find_config
from gemini_web2api.server import ThreadedServer


def resolve_config_path(args_config):
    """Resolve the config file to load on startup.

    Priority:
      1. explicit --config / $GEMINI_WEB2API_CONFIG
      2. stable data dir (same path the admin console writes to) — this is
         what makes cookie/proxy/keys survive restarts under systemd/docker
         where cwd differs from the data dir.
      3. legacy cwd config.json (old deployments)
      4. upstream default locations
    """
    if args_config or os.environ.get("GEMINI_WEB2API_CONFIG"):
        return args_config or os.environ.get("GEMINI_WEB2API_CONFIG")
    stable = writable_config_path()
    if stable.exists():
        return str(stable)
    legacy = legacy_config_path()
    if legacy.exists():
        return str(legacy)
    return find_config()


def main():
    parser = argparse.ArgumentParser(description="Gemini Web to OpenAI API (Manage Edition)")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--cookie-file", type=str, default=None)
    parser.add_argument("--proxy", type=str, default=None, help="HTTP proxy, e.g. http://127.0.0.1:7890")
    parser.add_argument("--version", action="version", version=f"gemini-web2api-manage {__version__}")
    args = parser.parse_args()

    config_path = resolve_config_path(args.config)
    if config_path:
        load_config(config_path)

    if args.port:
        CONFIG["port"] = args.port
    if args.cookie_file:
        CONFIG["cookie_file"] = args.cookie_file
        CONFIG["cookie_files"] = [args.cookie_file]
    if args.proxy:
        CONFIG["proxy"] = args.proxy

    apply_proxy_bridge(CONFIG)

    new_bl = fetch_latest_bl()
    if new_bl:
        CONFIG["gemini_bl"] = new_bl

    port = CONFIG["port"]
    server = ThreadedServer((CONFIG["host"], port), GeminiHandler)
    print(f"gemini-web2api-manage v{__version__}")
    print(f"  Listening: http://0.0.0.0:{port}")
    print(f"  Base URL:  http://localhost:{port}/v1")
    print(f"  Admin:     http://localhost:{port}/admin")
    print(f"  Models:    {', '.join(MODELS.keys())}")
    print(f"  Cookie:    {'yes' if CONFIG.get('cookie_file') else 'none (anonymous)'}")
    print(f"  Proxy:     {CONFIG.get('proxy') or 'system env'}")
    print(f"  Streaming: {'httpx (true streaming)' if HAS_HTTPX else 'urllib (buffered)'}")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
