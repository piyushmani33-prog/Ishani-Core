"""
Voice profile router – member-readable voice settings.

Handles:
  GET /api/voice/profile — Return the current voice configuration (member-only)

Full voice control (wake, settings, TTS) is managed by voice_runtime_layer.py.
This router exposes the read-only profile that member pages need on load.
"""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_voice_profile_router(ctx: Dict[str, Any]) -> APIRouter:
    """Return an APIRouter with the /api/voice/profile route."""

    session_user = ctx["session_user"]
    get_state = ctx["get_state"]

    router = APIRouter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def require_member(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return user

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @router.get("/api/voice/profile")
    async def voice_profile(request: Request):
        require_member(request)
        state = get_state()
        voice = state.get("voice", {})
        return {
            "language": voice.get("language", "en-IN"),
            "rate": voice.get("rate", 0.94),
            "pitch": voice.get("pitch", 1.08),
            "profile": voice.get("voice_profile", "sovereign_female"),
            "wake_words": voice.get("wake_words", ["hey jinn", "my king commands"]),
            "always_listening": voice.get("always_listening", False),
        }

    return router
