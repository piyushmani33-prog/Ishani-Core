"""
Phase Exposure Layer
====================
Controls *what is exposed to the user* based on the current product phase (1-5).
All brains, learning engines and autonomous loops remain active internally at
all times — only the UI/API surface presented to users is narrowed.

Install with:
    from phase_exposure_layer import install_phase_exposure_layer
    install_phase_exposure_layer(app, ctx)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Phase Configuration
# ---------------------------------------------------------------------------

PHASE_CONFIG: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Recruitment Launch",
        "description": "Core recruitment platform — ATS, careers, jobs, and candidate public agent.",
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
        "description": "Adds agent, navigator, and network intel for internal operators.",
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
        "description": "Unlocks neural dashboard, research panel, and brain pulse queries.",
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
        "description": "Adds empire portals, browser suite, and spread/phantom routing.",
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
        "description": "Full access — all brains, dashboards, and advanced systems exposed.",
        "visible_modules": ["ALL"],
        "visible_actions": ["ALL"],
        "visible_dashboards": ["ALL"],
        "hidden_advanced": [],
    },
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SetPhaseRequest(BaseModel):
    phase: int


class CheckVisibilityRequest(BaseModel):
    role: Optional[str] = None
    module: Optional[str] = None
    action: Optional[str] = None
    dashboard: Optional[str] = None


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------


def install_phase_exposure_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    session_user = ctx["session_user"]
    now_iso = ctx["now_iso"]
    DATA_DIR: str = ctx["DATA_DIR"]
    log = ctx["log"]

    _STATE_PATH = os.path.join(DATA_DIR, "phase_state.json")

    # -----------------------------------------------------------------------
    # Persistence helpers
    # -----------------------------------------------------------------------

    def _load_phase() -> int:
        """Load the current phase number from disk (default: 1)."""
        try:
            if os.path.exists(_STATE_PATH):
                with open(_STATE_PATH, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    return int(data.get("current_phase", 1))
        except Exception as exc:
            log.warning("phase_exposure_layer: could not read phase_state.json: %s", exc)
        return 1

    def _save_phase(phase: int) -> None:
        """Persist the current phase number to disk."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(_STATE_PATH, "w", encoding="utf-8") as fh:
                json.dump(
                    {"current_phase": phase, "updated_at": now_iso()},
                    fh,
                    indent=2,
                )
        except Exception as exc:
            log.error("phase_exposure_layer: could not write phase_state.json: %s", exc)

    # -----------------------------------------------------------------------
    # Visibility helpers
    # -----------------------------------------------------------------------

    def _is_master(user: Optional[Dict[str, Any]]) -> bool:
        return bool(user and user.get("role") == "master")

    def _effective_phase(user: Optional[Dict[str, Any]]) -> int:
        """Master users always see phase 5 (full access)."""
        if _is_master(user):
            return 5
        return _load_phase()

    def _visibility_payload(phase: int) -> Dict[str, Any]:
        cfg = PHASE_CONFIG.get(phase, PHASE_CONFIG[1])
        return {
            "phase": phase,
            "name": cfg["name"],
            "description": cfg["description"],
            "visible_modules": cfg["visible_modules"],
            "visible_actions": cfg["visible_actions"],
            "visible_dashboards": cfg["visible_dashboards"],
            "hidden_advanced": cfg["hidden_advanced"],
            "all_access": phase == 5,
        }

    def _is_visible(cfg: Dict[str, Any], kind: str, value: str) -> bool:
        """Return True if value is visible in cfg for the given kind."""
        lst: List[str] = cfg.get(kind, [])
        return "ALL" in lst or value in lst

    # -----------------------------------------------------------------------
    # Endpoints
    # -----------------------------------------------------------------------

    @app.get("/api/phase/current")
    async def api_phase_current(request: Request):
        """Return the current phase number, name, and visibility config."""
        phase = _load_phase()
        cfg = PHASE_CONFIG.get(phase, PHASE_CONFIG[1])
        return {
            "ok": True,
            "current_phase": phase,
            "name": cfg["name"],
            "description": cfg["description"],
            "config": _visibility_payload(phase),
        }

    @app.post("/api/phase/set")
    async def api_phase_set(body: SetPhaseRequest, request: Request):
        """(Owner-only) Set the current active phase (1-5)."""
        user = session_user(request)
        if not _is_master(user):
            raise HTTPException(status_code=403, detail="Master access required to change phase.")
        if body.phase not in PHASE_CONFIG:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phase {body.phase}. Must be 1–5.",
            )
        _save_phase(body.phase)
        log.info("phase_exposure_layer: phase set to %s by %s", body.phase, user.get("email"))
        return {
            "ok": True,
            "current_phase": body.phase,
            "name": PHASE_CONFIG[body.phase]["name"],
        }

    @app.get("/api/phase/visibility")
    async def api_phase_visibility(request: Request):
        """Return what's visible for the current user's role + phase."""
        user = session_user(request)
        phase = _effective_phase(user)
        payload = _visibility_payload(phase)
        payload["is_master"] = _is_master(user)
        return {"ok": True, **payload}

    @app.post("/api/phase/check")
    async def api_phase_check(body: CheckVisibilityRequest, request: Request):
        """Check if a specific module/action/dashboard is visible for a role."""
        user = session_user(request)
        phase = _effective_phase(user)
        cfg = _visibility_payload(phase)

        result: Dict[str, Any] = {
            "ok": True,
            "phase": phase,
            "is_master": _is_master(user),
        }

        if body.module is not None:
            result["module"] = body.module
            result["module_visible"] = _is_visible(cfg, "visible_modules", body.module)

        if body.action is not None:
            result["action"] = body.action
            result["action_allowed"] = _is_visible(cfg, "visible_actions", body.action)

        if body.dashboard is not None:
            result["dashboard"] = body.dashboard
            result["dashboard_visible"] = _is_visible(cfg, "visible_dashboards", body.dashboard)

        return result

    log.info("phase_exposure_layer: installed (current phase: %s)", _load_phase())

    return {
        "load_phase": _load_phase,
        "save_phase": _save_phase,
        "phase_visibility_payload": _visibility_payload,
        "phase_config": PHASE_CONFIG,
    }
