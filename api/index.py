"""Vercel serverless entrypoint for gemini-web2api-manage."""
from gemini_web2api_manage.server import GeminiHandler
from gemini_web2api_manage.config import CONFIG  # noqa: F401 - ensures manage defaults loaded
from gemini_web2api.config import apply_env_config

apply_env_config()


class handler(GeminiHandler):
    pass
