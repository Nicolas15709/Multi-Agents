from __future__ import annotations

import os
from typing import Dict


def detect_execution_backend() -> Dict[str, object]:
    anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    openrouter_key = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
    openai_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    default_model = (os.environ.get("DEFAULT_MODEL") or "").strip()

    if anthropic_key:
        return {
            "mode": "live",
            "provider": "anthropic",
            "model": default_model or "claude-sonnet-4-6",
            "supported": True,
            "reason": "ANTHROPIC_API_KEY configured",
        }

    configured_provider = None
    if openrouter_key:
        configured_provider = "openrouter"
    elif openai_key:
        configured_provider = "openai"

    if configured_provider:
        return {
            "mode": "simulation",
            "provider": configured_provider,
            "model": default_model or None,
            "supported": False,
            "reason": (
                f"{configured_provider.upper()} credentials are configured, "
                "but live task execution is still Anthropic-backed in the current runtime."
            ),
        }

    return {
        "mode": "simulation",
        "provider": None,
        "model": default_model or None,
        "supported": False,
        "reason": "No supported live task execution backend configured",
    }
