"""
Provider Status Layer — real provider connectivity checks.

Provides:
    GET /api/provider/status

For each configured provider this endpoint checks:
- Ollama:    HTTP GET {host}/api/version with a 3-second timeout
- OpenAI:    key format check (starts with sk-)
- Gemini:    key format check (starts with AIza)
- Anthropic: key format check (starts with sk-ant-)

Response shape:
{
    "providers": {
        "ollama":    {"configured", "reachable", "model", "host"},
        "openai":    {"configured", "key_format_valid"},
        "gemini":    {"configured", "key_format_valid"},
        "anthropic": {"configured", "key_format_valid"},
    },
    "active_provider":  str,   # first provider that is ready
    "fallback_active":  bool,  # True when no real provider is ready
    "ready_for_chat":   bool,  # at least one provider (including built-in) is usable
    "checked_at":       str,   # ISO-8601 timestamp
}

Register in app.py:
    from provider_status_layer import install_provider_status_layer
    install_provider_status_layer(app, _PLATFORM_CTX)
"""

from __future__ import annotations

import datetime
import os
from typing import Any, Dict, Optional

import httpx


def install_provider_status_layer(app: Any, ctx: Dict[str, Any]) -> None:
    """Register GET /api/provider/status on *app*."""

    @app.get("/api/provider/status")
    async def provider_status():
        """
        Real provider connectivity status.

        Checks each configured provider's actual reachability (or key format
        for cloud providers where a network round-trip is too slow for a
        status endpoint).  Never fakes a healthy status.
        """
        return await _build_provider_status()


async def _build_provider_status() -> Dict[str, Any]:
    """Collect per-provider status and return the unified payload."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral").strip() or "mistral"
    fallback_enabled = os.getenv("AI_FALLBACK_ENABLED", "true").lower() != "false"

    providers: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Ollama — real HTTP ping
    # ------------------------------------------------------------------
    ollama_reachable = False
    ollama_error: Optional[str] = None
    if ollama_host:
        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                resp = await client.get(f"{ollama_host.rstrip('/')}/api/version")
            ollama_reachable = resp.status_code == 200
            if not ollama_reachable:
                ollama_error = f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            ollama_error = "connection timed out (3 s)"
        except Exception as exc:
            ollama_error = str(exc)[:200]

    providers["ollama"] = {
        "configured": bool(ollama_host),
        "reachable": ollama_reachable,
        "model": ollama_model,
        "host": ollama_host,
        **({"error": ollama_error} if ollama_error else {}),
    }

    # ------------------------------------------------------------------
    # OpenAI — key format check only
    # ------------------------------------------------------------------
    openai_valid = bool(openai_key) and openai_key.startswith("sk-")
    providers["openai"] = {
        "configured": bool(openai_key),
        "key_format_valid": openai_valid,
        **({"error": "Key does not start with 'sk-'"} if openai_key and not openai_valid else {}),
    }

    # ------------------------------------------------------------------
    # Gemini — key format check only
    # ------------------------------------------------------------------
    gemini_valid = bool(gemini_key) and gemini_key.startswith("AIza")
    providers["gemini"] = {
        "configured": bool(gemini_key),
        "key_format_valid": gemini_valid,
        **({"error": "Key does not start with 'AIza'"} if gemini_key and not gemini_valid else {}),
    }

    # ------------------------------------------------------------------
    # Anthropic — key format check only
    # ------------------------------------------------------------------
    anthropic_valid = bool(anthropic_key) and anthropic_key.startswith("sk-ant-")
    providers["anthropic"] = {
        "configured": bool(anthropic_key),
        "key_format_valid": anthropic_valid,
        **({"error": "Key does not start with 'sk-ant-'"} if anthropic_key and not anthropic_valid else {}),
    }

    # ------------------------------------------------------------------
    # Derive active provider (Ollama preferred, then cloud keys)
    # ------------------------------------------------------------------
    active_provider = "built-in"
    if ollama_reachable:
        active_provider = f"ollama/{ollama_model}"
    elif openai_valid:
        active_provider = "openai"
    elif gemini_valid:
        active_provider = "gemini"
    elif anthropic_valid:
        active_provider = "anthropic"

    fallback_active = active_provider == "built-in"
    ready_for_chat = not fallback_active or fallback_enabled

    return {
        "providers": providers,
        "active_provider": active_provider,
        "fallback_active": fallback_active,
        "ready_for_chat": ready_for_chat,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
