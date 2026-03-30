"""role_router_layer.py

Universal Role Router for TechBuzz / Ishani Core.

Detects the active user's role and maps it to its designated owner brain.
All helper brains remain alive and continue working internally; only the
owner brain surfaces its output directly to the user.

The disclosure gate and safety layer from brain_communication_layer.py still
apply to every outbound message.

Install pattern (matches all other layers):
    from role_router_layer import install_role_router_layer
    install_role_router_layer(app, ctx)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Role → Brain mapping
# ---------------------------------------------------------------------------

ROLE_BRAIN_MAP: Dict[str, Dict[str, str]] = {
    "recruiter": {
        "owner_brain": "recruitment_secretary",
        "label": "Recruitment Brain",
    },
    "candidate": {
        "owner_brain": "public_agent",
        "label": "Career Assistant",
    },
    "founder_admin": {
        "owner_brain": "mother",
        "label": "Mother Brain (Ishani)",
    },
    "operator_research": {
        "owner_brain": "operations_executive",
        "label": "Operations Brain",
    },
}

# ---------------------------------------------------------------------------
# Role detection
# ---------------------------------------------------------------------------


def detect_role(user: Optional[Dict[str, Any]], request: Optional[Request] = None) -> str:
    """Derive the role string for a user dict (or None for anonymous).

    Priority order
    --------------
    1. No authenticated user (or public/unauthenticated path) → ``candidate``
    2. The platform ``master`` role → ``founder_admin``
    3. User has a ``recruiter`` flag or role set → ``recruiter``
    4. Fallback → ``operator_research``
    """
    if not user:
        return "candidate"

    platform_role: str = user.get("role", "")
    user_flags: str = user.get("flags", "")

    if platform_role == "master":
        return "founder_admin"

    if platform_role == "recruiter" or "recruiter" in str(user_flags):
        return "recruiter"

    return "operator_research"


# ---------------------------------------------------------------------------
# Layer installer
# ---------------------------------------------------------------------------


def install_role_router_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Install the Role Router API into the FastAPI *app*.

    Follows the ``install_*_layer(app, ctx)`` convention.
    """
    session_user = ctx["session_user"]
    log = ctx.get("log")

    # Try to get phase helpers if the phase exposure layer was installed first
    load_phase = ctx.get("load_phase")
    visibility_for_role = ctx.get("visibility_for_role")
    phase_config = ctx.get("phase_config")

    # In-memory role override store  {session_token: role_string}
    _overrides: Dict[str, str] = {}

    def _token(request: Request) -> str:
        """Extract the raw session token from the request."""
        return (
            request.cookies.get("techbuzz_session", "")
            or request.headers.get("X-Session-Token", "")
        )

    def _effective_role(user: Optional[Dict[str, Any]], request: Request) -> str:
        tok = _token(request)
        if tok and tok in _overrides:
            return _overrides[tok]
        return detect_role(user, request)

    # -----------------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------------

    @app.get("/api/role/current")
    async def api_role_current(request: Request):
        """Return the current user's detected role and their owner brain."""
        user = session_user(request)
        role = _effective_role(user, request)
        brain_info = ROLE_BRAIN_MAP.get(role, ROLE_BRAIN_MAP["operator_research"])
        return JSONResponse(
            {
                "role": role,
                "owner_brain": brain_info["owner_brain"],
                "label": brain_info["label"],
            }
        )

    @app.get("/api/role/brain-map")
    async def api_role_brain_map(request: Request):
        """Return the full role-to-brain mapping. Owner-only."""
        user = session_user(request)
        if not user or user.get("role") != "master":
            return JSONResponse(
                {"error": "Master access required."}, status_code=403
            )
        return JSONResponse({"brain_map": ROLE_BRAIN_MAP})

    @app.post("/api/role/override")
    async def api_role_override(request: Request):
        """Temporarily override a session's role for testing. Owner-only."""
        user = session_user(request)
        if not user or user.get("role") != "master":
            return JSONResponse(
                {"error": "Master access required."}, status_code=403
            )
        body: Dict[str, Any] = {}
        try:
            body = await request.json()
        except Exception:
            pass

        target_token: str = body.get("token", _token(request))
        override_role: str = str(body.get("role", ""))

        if override_role and override_role not in ROLE_BRAIN_MAP:
            return JSONResponse(
                {
                    "error": f"Unknown role '{override_role}'. Valid roles: {list(ROLE_BRAIN_MAP.keys())}"
                },
                status_code=400,
            )

        if not override_role:
            # Clear override
            _overrides.pop(target_token, None)
            return JSONResponse({"ok": True, "cleared": True, "token": target_token})

        _overrides[target_token] = override_role
        return JSONResponse(
            {
                "ok": True,
                "token": target_token,
                "role": override_role,
                "owner_brain": ROLE_BRAIN_MAP[override_role]["owner_brain"],
            }
        )

    @app.get("/api/role/visibility")
    async def api_role_visibility(request: Request):
        """Combined: returns role + phase visibility in one payload."""
        user = session_user(request)
        role = _effective_role(user, request)
        brain_info = ROLE_BRAIN_MAP.get(role, ROLE_BRAIN_MAP["operator_research"])

        payload: Dict[str, Any] = {
            "role": role,
            "owner_brain": brain_info["owner_brain"],
            "label": brain_info["label"],
        }

        if load_phase and visibility_for_role and phase_config:
            phase = load_phase()
            vis = visibility_for_role(phase_config[phase], role)
            payload.update(
                {
                    "phase": phase,
                    "phase_name": phase_config[phase]["name"],
                    "visible_modules": vis["visible_modules"],
                    "visible_actions": vis["visible_actions"],
                    "visible_dashboards": vis["visible_dashboards"],
                    "hidden_advanced": vis["hidden_advanced"],
                }
            )
        else:
            payload.update(
                {
                    "phase": None,
                    "phase_name": None,
                    "visible_modules": [],
                    "visible_actions": [],
                    "visible_dashboards": [],
                    "hidden_advanced": [],
                }
            )

        return JSONResponse(payload)

    layer_ctx: Dict[str, Any] = {
        "detect_role": detect_role,
        "role_brain_map": ROLE_BRAIN_MAP,
    }

    if log:
        log.info("role_router_layer: installed")

    return layer_ctx
