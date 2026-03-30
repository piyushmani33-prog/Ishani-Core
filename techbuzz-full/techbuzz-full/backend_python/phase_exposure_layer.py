"""
phase_exposure_layer.py
-----------------------
Phase Exposure System for TechBuzz / Ishani Core.

Controls which modules, actions, and dashboards are *exposed* to the user
based on the active product phase (1–5).  All brains and features remain
active internally at all times — only surface-level visibility is gated.

Follows the install_*_layer(app, ctx) pattern used by other layers.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("phase_exposure_layer")

# ---------------------------------------------------------------------------
# Phase configuration
# ---------------------------------------------------------------------------

_P1_MODULES = ["recruitment", "ats", "career", "jobs", "public_agent"]
_P1_ACTIONS = ["post_job", "screen_candidate", "schedule_interview", "recruiter_chat"]
_P1_DASHBOARDS = ["recruiter-mode", "career", "jobs", "ats", "company-portal"]
_P1_HIDDEN = ["neural", "spread", "empire", "research", "browser_suite", "photon", "brain_hierarchy"]

_P2_MODULES = _P1_MODULES + ["agent", "navigator", "network"]
_P2_ACTIONS = _P1_ACTIONS + ["agent_task", "navigator_search", "network_intel"]
_P2_DASHBOARDS = _P1_DASHBOARDS + ["agent", "navigator", "network", "network-intel"]
_P2_HIDDEN = ["neural", "spread", "empire", "research", "photon", "brain_hierarchy"]

_P3_MODULES = _P2_MODULES + ["neural", "research", "intel_panel"]
_P3_ACTIONS = _P2_ACTIONS + ["brain_pulse", "research_cycle", "intel_query"]
_P3_DASHBOARDS = _P2_DASHBOARDS + ["neural", "research"]
_P3_HIDDEN = ["spread", "empire", "photon", "brain_hierarchy"]

_P4_MODULES = _P3_MODULES + ["empire", "browser_suite", "spread"]
_P4_ACTIONS = _P3_ACTIONS + ["empire_merge", "phantom_route", "spread_ops"]
_P4_DASHBOARDS = _P3_DASHBOARDS + ["empire-portals", "browser", "spread"]
_P4_HIDDEN = ["photon", "brain_hierarchy"]

_ALL_MODULES = list(
    dict.fromkeys(
        _P4_MODULES + ["photon", "brain_hierarchy", "brain_communication", "voice", "local_ai"]
    )
)
_ALL_ACTIONS = list(
    dict.fromkeys(
        _P4_ACTIONS + ["photon_ops", "voice_command", "local_ai_run", "full_sovereignty"]
    )
)
_ALL_DASHBOARDS = list(
    dict.fromkeys(
        _P4_DASHBOARDS + ["photon", "neural", "leazy", "hq", "mission", "brain-hierarchy"]
    )
)

PHASE_CONFIG: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Recruitment Launch",
        "visible_modules": _P1_MODULES,
        "visible_actions": _P1_ACTIONS,
        "visible_dashboards": _P1_DASHBOARDS,
        "hidden_advanced": _P1_HIDDEN,
    },
    2: {
        "name": "Operator Expansion",
        "visible_modules": _P2_MODULES,
        "visible_actions": _P2_ACTIONS,
        "visible_dashboards": _P2_DASHBOARDS,
        "hidden_advanced": _P2_HIDDEN,
    },
    3: {
        "name": "Intelligence Layer",
        "visible_modules": _P3_MODULES,
        "visible_actions": _P3_ACTIONS,
        "visible_dashboards": _P3_DASHBOARDS,
        "hidden_advanced": _P3_HIDDEN,
    },
    4: {
        "name": "Empire Operations",
        "visible_modules": _P4_MODULES,
        "visible_actions": _P4_ACTIONS,
        "visible_dashboards": _P4_DASHBOARDS,
        "hidden_advanced": _P4_HIDDEN,
    },
    5: {
        "name": "Full Sovereignty (Master)",
        "visible_modules": _ALL_MODULES,
        "visible_actions": _ALL_ACTIONS,
        "visible_dashboards": _ALL_DASHBOARDS,
        "hidden_advanced": [],
    },
}

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

_DEFAULT_PHASE = 1


def _load_phase(state_path: Path) -> int:
    try:
        if state_path.exists():
            data = json.loads(state_path.read_text(encoding="utf-8"))
            phase = int(data.get("current_phase", _DEFAULT_PHASE))
            if phase in PHASE_CONFIG:
                return phase
    except Exception as exc:  # pragma: no cover
        log.warning("phase_exposure_layer: could not load phase state: %s", exc)
    return _DEFAULT_PHASE


def _save_phase(state_path: Path, phase: int) -> None:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"current_phase": phase}, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover
        log.warning("phase_exposure_layer: could not save phase state: %s", exc)


# ---------------------------------------------------------------------------
# Role-based phase overrides
# ---------------------------------------------------------------------------

def _effective_phase_for_role(phase: int, role: Optional[str]) -> int:
    """Master/owner always gets phase 5 regardless of the active phase setting."""
    if role == "master":
        return 5
    return phase


# ---------------------------------------------------------------------------
# Layer installer
# ---------------------------------------------------------------------------

def install_phase_exposure_layer(app: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Install Phase Exposure Layer into the FastAPI app."""
    session_user = ctx["session_user"]
    DATA_DIR = Path(ctx["DATA_DIR"])

    state_path = DATA_DIR / "phase_state.json"
    _current: Dict[str, int] = {"phase": _load_phase(state_path)}

    def get_phase() -> int:
        return _current["phase"]

    def set_phase(phase: int) -> None:
        _current["phase"] = phase
        _save_phase(state_path, phase)

    def visibility_for(phase: int) -> Dict[str, Any]:
        cfg = PHASE_CONFIG[phase]
        return {
            "phase": phase,
            "phase_name": cfg["name"],
            "visible_modules": cfg["visible_modules"],
            "visible_actions": cfg["visible_actions"],
            "visible_dashboards": cfg["visible_dashboards"],
            "hidden_advanced": cfg["hidden_advanced"],
        }

    # ------------------------------------------------------------------
    # GET /api/phase/current
    # ------------------------------------------------------------------
    @app.get("/api/phase/current")
    async def api_phase_current(request: Request) -> JSONResponse:
        user = session_user(request)
        role = user.get("role") if user else None
        effective = _effective_phase_for_role(get_phase(), role)
        cfg = PHASE_CONFIG[effective]
        return JSONResponse(
            {
                "current_phase": effective,
                "phase_name": cfg["name"],
                "configured_phase": get_phase(),
                "visibility": visibility_for(effective),
            }
        )

    # ------------------------------------------------------------------
    # POST /api/phase/set  (owner-only)
    # ------------------------------------------------------------------
    @app.post("/api/phase/set")
    async def api_phase_set(request: Request) -> JSONResponse:
        user = session_user(request)
        if not user or user.get("role") != "master":
            return JSONResponse({"detail": "Owner access required."}, status_code=403)
        try:
            body = await request.json()
            phase = int(body.get("phase", 0))
        except Exception:
            return JSONResponse({"detail": "Invalid request body."}, status_code=400)
        if phase not in PHASE_CONFIG:
            return JSONResponse(
                {"detail": f"Phase must be one of {list(PHASE_CONFIG.keys())}."},
                status_code=400,
            )
        set_phase(phase)
        return JSONResponse({"ok": True, "current_phase": phase, "phase_name": PHASE_CONFIG[phase]["name"]})

    # ------------------------------------------------------------------
    # GET /api/phase/visibility
    # ------------------------------------------------------------------
    @app.get("/api/phase/visibility")
    async def api_phase_visibility(request: Request) -> JSONResponse:
        user = session_user(request)
        role = user.get("role") if user else None
        effective = _effective_phase_for_role(get_phase(), role)
        return JSONResponse(visibility_for(effective))

    # ------------------------------------------------------------------
    # POST /api/phase/check
    # ------------------------------------------------------------------
    @app.post("/api/phase/check")
    async def api_phase_check(request: Request) -> JSONResponse:
        user = session_user(request)
        role = user.get("role") if user else None
        effective = _effective_phase_for_role(get_phase(), role)
        cfg = PHASE_CONFIG[effective]
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"detail": "Invalid request body."}, status_code=400)
        kind = body.get("kind", "")
        item = body.get("item", "")
        if kind == "module":
            visible = item in cfg["visible_modules"]
        elif kind == "action":
            visible = item in cfg["visible_actions"]
        elif kind == "dashboard":
            visible = item in cfg["visible_dashboards"]
        else:
            return JSONResponse({"detail": "kind must be one of: module, action, dashboard."}, status_code=400)
        return JSONResponse(
            {
                "kind": kind,
                "item": item,
                "visible": visible,
                "phase": effective,
                "phase_name": cfg["name"],
            }
        )

    log.info("phase_exposure_layer: installed (active phase=%d)", get_phase())

    return {
        "get_phase": get_phase,
        "set_phase": set_phase,
        "phase_config": PHASE_CONFIG,
        "visibility_for": visibility_for,
    }
