"""gemini-web2api-manage: Web management console for gemini-web2api."""
import os
import sys

# Add upstream submodule to Python path so `import gemini_web2api` resolves
_upstream = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_upstream')
if os.path.isdir(_upstream) and _upstream not in sys.path:
    sys.path.insert(0, _upstream)

__version__ = "2.0.0"
