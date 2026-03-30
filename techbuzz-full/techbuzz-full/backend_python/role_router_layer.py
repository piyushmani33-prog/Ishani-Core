"""
role_router_layer.py
--------------------
Universal Role Router for TechBuzz / Ishani Core.

Maps each user session to a primary owner brain.  All brains remain alive
and running internally at all times — only the owner brain speaks directly
to the user.  Helper brains continue working internally and their outputs
feed into the owner brain.

Follows the install_*_layer(app, ctx) pattern used by other layers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from phase_exposure_layer import PHASE_CONFIG, _effective_phase_for_role

log = logging.getLogger("role_router_layer")

# ---------------------------------------------------------------------------
# Role → brain mapping
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

_ROLE_OVERRIDES: Dict[str, str] = {}  # session_token -> role (testing only)


def detect_role(request: Request, session_user_fn: Any) -> str:
    """Return the detected role string for the incoming request."""
    user = session_user_fn(request)

    # 1. Unauthenticated / public route → candidate
    if not user:
        return "candidate"

    # 2. Session-level override (owner-only testing feature)
    token = (
        request.cookies.get("techbuzz_session", "")
        or request.headers.get("X-Ishani-Session", "")
    )
    if token and token in _ROLE_OVERRIDES:
        override = _ROLE_OVERRIDES[token]
        if override in ROLE_BRAIN_MAP:
            return override

    # 3. Owner / master account → founder_admin
    if user.get("role") == "master":
        return "founder_admin"

    # 4. Explicit role field in the user record
    user_role = user.get("app_role", "")
    if user_role in ROLE_BRAIN_MAP:
        return user_role

    # 5. Recruiter flag (stored as plan_id or a recruiter flag)
    plan_id = user.get("plan_id", "")
    if plan_id in ("recruiter", "recruiter_pro") or user.get("is_recruiter"):
        return "recruiter"

    # 6. Default → operator_research for authenticated members
    return "operator_research"


# ---------------------------------------------------------------------------
# Layer installer
# ---------------------------------------------------------------------------

def install_role_router_layer(app: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Install Role Router Layer into the FastAPI app."""
    session_user = ctx["session_user"]

    def get_role(request: Request) -> str:
        return detect_role(request, session_user)

    def brain_for_role(role: str) -> Dict[str, str]:
        return ROLE_BRAIN_MAP.get(role, ROLE_BRAIN_MAP["operator_research"])

    # ------------------------------------------------------------------
    # GET /api/role/current
    # ------------------------------------------------------------------
    @app.get("/api/role/current")
    async def api_role_current(request: Request) -> JSONResponse:
        role = get_role(request)
        brain_info = brain_for_role(role)
        return JSONResponse(
            {
                "role": role,
                "owner_brain": brain_info["owner_brain"],
                "brain_label": brain_info["label"],
            }
        )

    # ------------------------------------------------------------------
    # GET /api/role/brain-map  (owner-only)
    # ------------------------------------------------------------------
    @app.get("/api/role/brain-map")
    async def api_role_brain_map(request: Request) -> JSONResponse:
        user = session_user(request)
        if not user or user.get("role") != "master":
            return JSONResponse({"detail": "Owner access required."}, status_code=403)
        return JSONResponse({"role_brain_map": ROLE_BRAIN_MAP})

    # ------------------------------------------------------------------
    # POST /api/role/override  (owner-only)
    # ------------------------------------------------------------------
    @app.post("/api/role/override")
    async def api_role_override(request: Request) -> JSONResponse:
        user = session_user(request)
        if not user or user.get("role") != "master":
            return JSONResponse({"detail": "Owner access required."}, status_code=403)
        try:
            body = await request.json()
            token = str(body.get("session_token", "")).strip()
            role = str(body.get("role", "")).strip()
        except Exception:
            return JSONResponse({"detail": "Invalid request body."}, status_code=400)
        if not token:
            return JSONResponse({"detail": "session_token is required."}, status_code=400)
        if role and role not in ROLE_BRAIN_MAP:
            return JSONResponse(
                {"detail": f"role must be one of {list(ROLE_BRAIN_MAP.keys())} or empty to clear."},
                status_code=400,
            )
        if role:
            _ROLE_OVERRIDES[token] = role
            return JSONResponse({"ok": True, "session_token": token, "overridden_role": role})
        else:
            _ROLE_OVERRIDES.pop(token, None)
            return JSONResponse({"ok": True, "session_token": token, "overridden_role": None, "cleared": True})

    # ------------------------------------------------------------------
    # GET /api/role/visibility  (combined role + phase)
    # ------------------------------------------------------------------
    @app.get("/api/role/visibility")
    async def api_role_visibility(request: Request) -> JSONResponse:
        user = session_user(request)
        sys_role = user.get("role") if user else None
        role = get_role(request)
        brain_info = brain_for_role(role)

        # Determine active phase (read from ctx if the phase layer has been installed)
        get_phase_fn = ctx.get("get_phase")
        base_phase = get_phase_fn() if callable(get_phase_fn) else 1
        effective_phase = _effective_phase_for_role(base_phase, sys_role)
        phase_cfg = PHASE_CONFIG[effective_phase]

        return JSONResponse(
            {
                "role": role,
                "owner_brain": brain_info["owner_brain"],
                "brain_label": brain_info["label"],
                "phase": effective_phase,
                "phase_name": phase_cfg["name"],
                "visible_modules": phase_cfg["visible_modules"],
                "visible_actions": phase_cfg["visible_actions"],
                "visible_dashboards": phase_cfg["visible_dashboards"],
                "hidden_advanced": phase_cfg["hidden_advanced"],
            }
        )

    log.info("role_router_layer: installed")

    return {
        "get_role": get_role,
        "brain_for_role": brain_for_role,
        "role_brain_map": ROLE_BRAIN_MAP,
        "role_overrides": _ROLE_OVERRIDES,
    }
