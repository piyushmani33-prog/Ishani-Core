"""phase_exposure_layer.py

Phase Exposure System for TechBuzz / Ishani Core.

Keeps all brains and features active internally while exposing the correct
owner brain, workflows, and UI progressively based on the active product phase.

Hidden features remain active and keep generating learning signals – only their
*exposure* to the end-user is controlled by the current phase.

Install pattern (matches all other layers):
    from phase_exposure_layer import install_phase_exposure_layer
    install_phase_exposure_layer(app, ctx)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Phase configuration
# ---------------------------------------------------------------------------

PHASE_CONFIG: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Recruitment Launch",
        "visible_modules": ["recruitment", "ats", "career", "jobs", "public_agent"],
        "visible_actions": [
            "post_job",
            "screen_candidate",
            "schedule_interview",
            "recruiter_chat",
        ],
        "visible_dashboards": [
            "recruiter-mode",
            "career",
            "jobs",
            "ats",
            "company-portal",
        ],
        "hidden_advanced": [
            "neural",
            "spread",
            "empire",
            "research",
            "browser_suite",
            "photon",
            "brain_hierarchy",
        ],
    },
    2: {
        "name": "Operator Expansion",
        "visible_modules": [
            "recruitment",
            "ats",
            "career",
            "jobs",
            "public_agent",
            "agent",
            "navigator",
            "network",
        ],
        "visible_actions": [
            "post_job",
            "screen_candidate",
            "schedule_interview",
            "recruiter_chat",
            "agent_task",
            "navigator_search",
            "network_intel",
        ],
        "visible_dashboards": [
            "recruiter-mode",
            "career",
            "jobs",
            "ats",
            "company-portal",
            "agent",
            "navigator",
            "network",
            "network-intel",
        ],
        "hidden_advanced": [
            "neural",
            "spread",
            "empire",
            "research",
            "photon",
            "brain_hierarchy",
        ],
    },
    3: {
        "name": "Intelligence Layer",
        "visible_modules": [
            "recruitment",
            "ats",
            "career",
            "jobs",
            "public_agent",
            "agent",
            "navigator",
            "network",
            "neural",
            "research",
            "intel_panel",
        ],
        "visible_actions": [
            "post_job",
            "screen_candidate",
            "schedule_interview",
            "recruiter_chat",
            "agent_task",
            "navigator_search",
            "network_intel",
            "brain_pulse",
            "research_cycle",
            "intel_query",
        ],
        "visible_dashboards": [
            "recruiter-mode",
            "career",
            "jobs",
            "ats",
            "company-portal",
            "agent",
            "navigator",
            "network",
            "network-intel",
            "neural",
            "research",
        ],
        "hidden_advanced": ["spread", "empire", "photon", "brain_hierarchy"],
    },
    4: {
        "name": "Empire Operations",
        "visible_modules": [
            "recruitment",
            "ats",
            "career",
            "jobs",
            "public_agent",
            "agent",
            "navigator",
            "network",
            "neural",
            "research",
            "intel_panel",
            "empire",
            "browser_suite",
            "spread",
        ],
        "visible_actions": [
            "post_job",
            "screen_candidate",
            "schedule_interview",
            "recruiter_chat",
            "agent_task",
            "navigator_search",
            "network_intel",
            "brain_pulse",
            "research_cycle",
            "intel_query",
            "empire_merge",
            "phantom_route",
            "spread_ops",
        ],
        "visible_dashboards": [
            "recruiter-mode",
            "career",
            "jobs",
            "ats",
            "company-portal",
            "agent",
            "navigator",
            "network",
            "network-intel",
            "neural",
            "research",
            "empire-portals",
            "browser",
            "spread",
        ],
        "hidden_advanced": ["photon", "brain_hierarchy"],
    },
    5: {
        "name": "Full Sovereignty (Master)",
        "visible_modules": ["*"],
        "visible_actions": ["*"],
        "visible_dashboards": ["*"],
        "hidden_advanced": [],
    },
}

_ALL_MODULES = list(
    {
        m
        for ph in PHASE_CONFIG.values()
        if ph["visible_modules"] != ["*"]
        for m in ph["visible_modules"]
    }
    | {
        "neural",
        "spread",
        "empire",
        "research",
        "browser_suite",
        "photon",
        "brain_hierarchy",
        "intel_panel",
    }
)

_ALL_ACTIONS = list(
    {
        a
        for ph in PHASE_CONFIG.values()
        if ph["visible_actions"] != ["*"]
        for a in ph["visible_actions"]
    }
)

_ALL_DASHBOARDS = list(
    {
        d
        for ph in PHASE_CONFIG.values()
        if ph["visible_dashboards"] != ["*"]
        for d in ph["visible_dashboards"]
    }
    | {"photon", "brain-hierarchy", "leazy", "hq", "neural", "spread"}
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_phase(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a phase config with wildcard lists expanded."""
    result = dict(config)
    if result["visible_modules"] == ["*"]:
        result["visible_modules"] = _ALL_MODULES
    if result["visible_actions"] == ["*"]:
        result["visible_actions"] = _ALL_ACTIONS
    if result["visible_dashboards"] == ["*"]:
        result["visible_dashboards"] = _ALL_DASHBOARDS
    return result


def _visibility_for_role(phase_cfg: Dict[str, Any], role: str) -> Dict[str, Any]:
    """Apply role-level restrictions on top of phase visibility."""
    cfg = _resolve_phase(phase_cfg)
    # master / founder_admin sees everything in the current phase
    if role in ("master", "founder_admin"):
        return cfg

    hidden = set(cfg.get("hidden_advanced", []))

    modules = [m for m in cfg["visible_modules"] if m not in hidden]
    actions = list(cfg["visible_actions"])
    dashboards = [d for d in cfg["visible_dashboards"] if d not in hidden]

    # candidates see only career / public-agent surface
    if role == "candidate":
        modules = [m for m in modules if m in ("career", "jobs", "public_agent")]
        actions = [a for a in actions if a in ("screen_candidate",)]
        dashboards = [d for d in dashboards if d in ("career", "jobs")]

    return {
        "visible_modules": modules,
        "visible_actions": actions,
        "visible_dashboards": dashboards,
        "hidden_advanced": cfg["hidden_advanced"],
    }


# ---------------------------------------------------------------------------
# Layer installer
# ---------------------------------------------------------------------------


def install_phase_exposure_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Install the Phase Exposure API into the FastAPI *app*.

    Follows the ``install_*_layer(app, ctx)`` convention used by all other
    layers in this project.
    """
    session_user = ctx["session_user"]
    DATA_DIR = Path(ctx["DATA_DIR"])
    log = ctx.get("log")

    state_path = DATA_DIR / "phase_state.json"

    # -----------------------------------------------------------------------
    # Persistence helpers
    # -----------------------------------------------------------------------

    def _load_phase() -> int:
        try:
            with open(state_path) as fh:
                data = json.load(fh)
                phase = int(data.get("phase", 1))
                return max(1, min(5, phase))
        except Exception:
            return 1

    def _save_phase(phase: int) -> None:
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(state_path, "w") as fh:
                json.dump({"phase": phase}, fh)
        except Exception as exc:
            if log:
                log.warning("phase_exposure_layer: could not save phase state: %s", exc)

    # Ensure the state file exists on first run
    if not state_path.exists():
        _save_phase(1)

    # -----------------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------------

    @app.get("/api/phase/current")
    async def api_phase_current(request: Request):
        """Return the current phase number, name, and visibility config."""
        phase = _load_phase()
        cfg = _resolve_phase(PHASE_CONFIG[phase])
        return JSONResponse(
            {
                "phase": phase,
                "name": PHASE_CONFIG[phase]["name"],
                "visible_modules": cfg["visible_modules"],
                "visible_actions": cfg["visible_actions"],
                "visible_dashboards": cfg["visible_dashboards"],
                "hidden_advanced": cfg["hidden_advanced"],
            }
        )

    @app.post("/api/phase/set")
    async def api_phase_set(request: Request):
        """Set the current active phase (1-5). Owner-only."""
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
        phase = int(body.get("phase", 1))
        if phase < 1 or phase > 5:
            return JSONResponse(
                {"error": "Phase must be between 1 and 5."}, status_code=400
            )
        _save_phase(phase)
        return JSONResponse(
            {
                "ok": True,
                "phase": phase,
                "name": PHASE_CONFIG[phase]["name"],
            }
        )

    @app.get("/api/phase/visibility")
    async def api_phase_visibility(request: Request):
        """Return what's visible for the current user's role + current phase."""
        user = session_user(request)
        role = user.get("role", "member") if user else "candidate"
        phase = _load_phase()
        vis = _visibility_for_role(PHASE_CONFIG[phase], role)
        return JSONResponse(
            {
                "phase": phase,
                "phase_name": PHASE_CONFIG[phase]["name"],
                "role": role,
                **vis,
            }
        )

    @app.post("/api/phase/check")
    async def api_phase_check(request: Request):
        """Check if a specific module/action/dashboard is visible for a role."""
        user = session_user(request)
        role = user.get("role", "member") if user else "candidate"
        body: Dict[str, Any] = {}
        try:
            body = await request.json()
        except Exception:
            pass

        phase = _load_phase()
        vis = _visibility_for_role(PHASE_CONFIG[phase], role)

        module_id: Optional[str] = body.get("module")
        action_id: Optional[str] = body.get("action")
        dashboard_id: Optional[str] = body.get("dashboard")

        def _check(key: str, collection: List[str]) -> Optional[bool]:
            if key is None:
                return None
            return key in collection

        return JSONResponse(
            {
                "phase": phase,
                "role": role,
                "module": _check(module_id, vis["visible_modules"]),
                "action": _check(action_id, vis["visible_actions"]),
                "dashboard": _check(dashboard_id, vis["visible_dashboards"]),
            }
        )

    layer_ctx = {
        "load_phase": _load_phase,
        "save_phase": _save_phase,
        "phase_config": PHASE_CONFIG,
        "visibility_for_role": _visibility_for_role,
    }

    if log:
        log.info("phase_exposure_layer: installed (current phase: %d)", _load_phase())

    return layer_ctx
