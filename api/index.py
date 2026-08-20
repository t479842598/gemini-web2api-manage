"""Vercel serverless entrypoint for gemini-web2api-manage."""
from gemini_web2api_manage.server import GeminiHandler
from gemini_web2api_manage.config import CONFIG, apply_env_config  # noqa: F401
from gemini_web2api_manage.socks_bridge import apply_proxy_bridge
from gemini_web2api_manage import xsrf  # noqa: F401 - installs at-token retry

apply_env_config()
apply_proxy_bridge(CONFIG)


class handler(GeminiHandler):
    pass
