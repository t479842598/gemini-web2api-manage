"""gemini-web2api-manage: Web management console for gemini-web2api."""
import os
import sys

# Add upstream submodule to Python path so `import gemini_web2api` resolves
_upstream = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_upstream')
if os.path.isdir(_upstream) and _upstream not in sys.path:
    sys.path.insert(0, _upstream)

__version__ = "2.1.0"


# ─── Enhance tool_choice=auto prompt without modifying the upstream submodule ──
# Gemini Web is a reverse-engineered interface that simulates tool calling via
# prompt injection. Under tool_choice=auto the upstream prompt only tells the
# model it "can" call tools, so the model often answers directly instead of
# emitting a tool_call block. We append a soft nudge that biases the model
# toward calling a tool when the user's request clearly matches a tool's
# capability, while still preserving the model's discretion (not a MUST).
_AUTO_TOOL_NUDGE = (
    "\n\nGuidance: When the user's request can be fulfilled by one of the "
    "available tools, prefer calling that tool instead of answering from your "
    "own knowledge. Only answer directly when no tool is relevant."
)


def _patch_auto_tool_prompt():
    """Wrap upstream prompt builders so tool_choice=auto gets a soft nudge."""
    import gemini_web2api.tools as _tools
    import gemini_web2api.server as _server

    _orig_messages = _tools.messages_to_prompt
    _orig_google = _tools.google_contents_to_prompt

    def _messages_to_prompt(messages, tools=None, tool_choice=None):
        prompt, images = _orig_messages(messages, tools, tool_choice)
        if tools and tool_choice == "auto" and prompt:
            prompt = prompt + _AUTO_TOOL_NUDGE
        return prompt, images

    def _google_contents_to_prompt(req):
        prompt, images = _orig_google(req)
        fc_mode = req.get("toolConfig", {}).get(
            "functionCallingConfig", {}
        ).get("mode", "AUTO")
        if req.get("tools") and fc_mode == "AUTO" and prompt:
            prompt = prompt + _AUTO_TOOL_NUDGE
        return prompt, images

    # Patch both the tools module and the server module (server imported the
    # names by value at import time, so both references must be updated).
    _tools.messages_to_prompt = _messages_to_prompt
    _server.messages_to_prompt = _messages_to_prompt
    _tools.google_contents_to_prompt = _google_contents_to_prompt
    _server.google_contents_to_prompt = _google_contents_to_prompt


_patch_auto_tool_prompt()
