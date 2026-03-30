"""
Role Router Layer
=================
Detects the current user's role, maps it to the correct owner brain, and
returns combined role + phase visibility information.

All brains remain alive and running at all times.  Only the *owner brain* for
the user's role speaks directly to the user; helper brains continue working
internally and feed their outputs into the owner brain through the existing
contract-based routing in brain_communication_layer.py.

Install with:
    from role_router_layer import install_role_router_layer
    install_role_router_layer(app, ctx)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Role → Brain mapping
# ---------------------------------------------------------------------------

ROLE_BRAIN_MAP: Dict[str, Dict[str, str]] = {
    "recruiter": {
        "owner_brain": "recruitment_secretary",
        "label": "Recruitment Brain",
        "description": "Manages ATS, job postings, candidate screening, and recruiter workflows.",
    },
    "candidate": {
        "owner_brain": "public_agent",
        "label": "Career Assistant",
        "description": "Guides candidates through job discovery, applications, and status tracking.",
    },
    "founder_admin": {
        "owner_brain": "mother",
        "label": "Mother Brain (Ishani)",
        "description": "Full-access root brain — all executive, secretary, and domain brains report here.",
    },
    "operator_research": {
        "owner_brain": "operations_executive",
        "label": "Operations Brain",
        "description": "Drives operator-level research, network intel, and sourcing workflows.",
    },
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RoleOverrideRequest(BaseModel):
    session_id: str
    role: str


# ---------------------------------------------------------------------------
# In-memory override store (clears on restart; owner-only testing tool)
# ---------------------------------------------------------------------------

_ROLE_OVERRIDES: Dict[str, str] = {}


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------


def install_role_router_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    session_user = ctx["session_user"]
    log = ctx["log"]

    # Try to get phase visibility helper from ctx if phase layer was installed first
    _get_phase_visibility = ctx.get("phase_visibility_payload")

    # -----------------------------------------------------------------------
    # Role detection
    # -----------------------------------------------------------------------

    def _detect_role(request: Request, user: Optional[Dict[str, Any]]) -> str:
        """Detect the role for the current request/user.

        Priority:
          1. In-memory override (owner testing tool)
          2. Unauthenticated / public routes → candidate
          3. Master user → founder_admin
          4. Session role field = 'recruiter' → recruiter
          5. Fallback → operator_research
        """
        if user is None:
            return "candidate"

        user_id: str = user.get("id", "")
        session_id: str = user.get("session_id", "")

        # Override check (by user_id or session_id)
        override = _ROLE_OVERRIDES.get(user_id) or _ROLE_OVERRIDES.get(session_id)
        if override and override in ROLE_BRAIN_MAP:
            return override

        # Master user → founder_admin
        if user.get("role") == "master":
            return "founder_admin"

        # Session role tag for recruiter accounts
        if user.get("role") == "recruiter":
            return "recruiter"

        # plan_id / metadata hints (extensible)
        plan_id: str = str(user.get("plan_id", "")).lower()
        if "recruit" in plan_id:
            return "recruiter"

        return "operator_research"

    def _role_payload(role: str) -> Dict[str, Any]:
        brain_info = ROLE_BRAIN_MAP.get(role, ROLE_BRAIN_MAP["operator_research"])
        return {
            "role": role,
            "owner_brain": brain_info["owner_brain"],
            "label": brain_info["label"],
            "description": brain_info["description"],
        }

    # -----------------------------------------------------------------------
    # Endpoints
    # -----------------------------------------------------------------------

    @app.get("/api/role/current")
    async def api_role_current(request: Request):
        """Return the current user's detected role and their owner brain."""
        user = session_user(request)
        role = _detect_role(request, user)
        payload = _role_payload(role)
        return {
            "ok": True,
            **payload,
            "authenticated": user is not None,
        }

    @app.get("/api/role/brain-map")
    async def api_role_brain_map(request: Request):
        """(Owner-only) Return the full role-to-brain mapping."""
        user = session_user(request)
        if not (user and user.get("role") == "master"):
            raise HTTPException(status_code=403, detail="Master access required.")
        return {
            "ok": True,
            "brain_map": ROLE_BRAIN_MAP,
        }

    @app.post("/api/role/override")
    async def api_role_override(body: RoleOverrideRequest, request: Request):
        """(Owner-only) Temporarily override a session's role for testing."""
        user = session_user(request)
        if not (user and user.get("role") == "master"):
            raise HTTPException(status_code=403, detail="Master access required.")
        if body.role not in ROLE_BRAIN_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown role '{body.role}'. Valid roles: {list(ROLE_BRAIN_MAP.keys())}",
            )
        _ROLE_OVERRIDES[body.session_id] = body.role
        log.info(
            "role_router_layer: role override set — session=%s role=%s by %s",
            body.session_id,
            body.role,
            user.get("email"),
        )
        return {
            "ok": True,
            "session_id": body.session_id,
            "overridden_role": body.role,
        }

    @app.get("/api/role/visibility")
    async def api_role_visibility(request: Request):
        """Combined: returns role + phase visibility in one payload."""
        user = session_user(request)
        role = _detect_role(request, user)
        role_info = _role_payload(role)

        # Build phase visibility — use helper from phase layer if available,
        # otherwise return a minimal stub so this endpoint still works even
        # when phase_exposure_layer is not installed.
        phase_data: Dict[str, Any] = {"phase": 1, "name": "Recruitment Launch"}
        if _get_phase_visibility is not None:
            try:
                is_master = bool(user and user.get("role") == "master")
                effective_phase = 5 if is_master else 1
                # Try reading persisted phase if phase layer provided a loader
                phase_loader = ctx.get("load_phase")
                if phase_loader is not None:
                    effective_phase = 5 if is_master else phase_loader()
                phase_data = _get_phase_visibility(effective_phase)
            except Exception as exc:
                log.warning("role_router_layer: could not get phase data: %s", exc)

        return {
            "ok": True,
            "authenticated": user is not None,
            **role_info,
            "phase": phase_data,
        }

    log.info("role_router_layer: installed (roles: %s)", list(ROLE_BRAIN_MAP.keys()))

    return {
        "detect_role": _detect_role,
        "role_payload": _role_payload,
        "role_brain_map": ROLE_BRAIN_MAP,
    }
