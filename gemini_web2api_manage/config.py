"""Extended configuration for gemini-web2api-manage.

Imports the upstream CONFIG dict and adds manage-specific keys.
Because CONFIG is a shared mutable dict, all modules (upstream + manage)
see the same configuration object.
"""
from gemini_web2api.config import CONFIG, DEFAULT_CONFIG as UPSTREAM_DEFAULT

# Manage-specific default keys injected into the shared CONFIG dict
MANAGE_DEFAULTS = {
    "admin_password": "sk-admin",
    "public_base_url": None,
    "force_non_stream": False,
    "empty_response_fallback": (
        "Gemini \u8fd4\u56de\u4e86\u7a7a\u5185\u5bb9\u3002"
        "\u53ef\u80fd\u539f\u56e0\uff1aCookie \u5931\u6548\u3001"
        "\u5185\u5bb9\u88ab\u5b89\u5168\u7b56\u7565\u62e6\u622a\u3001"
        "\u4e0a\u4e0b\u6587\u8fc7\u957f\u6216\u5f53\u524d\u6a21\u578b"
        "\u6682\u4e0d\u53ef\u7528\u3002\u8bf7\u67e5\u770b\u7ba1\u7406"
        "\u53f0\u65e5\u5fd7\u4e2d\u7684\u7a7a\u54cd\u5e94\u8bca\u65ad"
        "\u540e\u91cd\u8bd5\u3002"
    ),
    "cookie_files": [],
}

for key, value in MANAGE_DEFAULTS.items():
    if key not in CONFIG:
        CONFIG[key] = value
