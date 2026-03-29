"""
Carbon Bond / Think / Stream router.

Handles /api/carbon/* endpoints (master-only) and the SSE event stream
that powers the empire bridge dashboard.
"""
import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CarbonBondReq(BaseModel):
    bond_type: str
    source_system: str
    target_system: str
    protocol_mode: str = "graphene"
    signal: str = ""


class CarbonThinkReq(BaseModel):
    problem: str
    mode: str = "graphene"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_carbon_router(ctx: Dict[str, Any]) -> APIRouter:
    """Return an APIRouter with all /api/carbon/* routes registered."""

    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
    get_state = ctx["get_state"]
    ai_name = ctx["AI_NAME"]
    company_name = ctx["COMPANY_NAME"]
    core_identity = ctx["CORE_IDENTITY"]
    carbon_events: List[Dict[str, Any]] = ctx["carbon_events"]
    carbon_modes: Dict[str, Any] = ctx["CARBON_MODES"]
    emit_carbon = ctx["emit_carbon"]  # shared helper from empire_merge_layer

    router = APIRouter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def require_master(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user or user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Imperial access required")
        return user

    async def ai_text(prompt: str, *, workspace: str, source: str, max_tokens: int = 500) -> Dict[str, Any]:
        return await generate_text(
            prompt,
            system=(
                f"You are {ai_name}, the {core_identity} mother-brain of {company_name}. "
                "Be specific, practical, and structured. Prefer actionable outputs over vague metaphors."
            ),
            max_tokens=max_tokens,
            use_web_search=False,
            workspace=workspace,
            source=source,
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @router.get("/api/carbon/status")
    async def carbon_status(request: Request):
        require_master(request)
        state = get_state()
        bonds = db_all("SELECT * FROM carbon_bonds WHERE status='active' ORDER BY created_at DESC LIMIT 20") or []
        return {
            "modes": carbon_modes,
            "active_bonds": len(bonds),
            "bonds": bonds[:10],
            "events": carbon_events[-20:],
            "current_mode": state.get("settings", {}).get("carbon_mode", "graphene"),
            "identity": state.get("meta", {}).get("identity", core_identity),
        }

    @router.post("/api/carbon/bond")
    async def carbon_bond(req: CarbonBondReq, request: Request):
        user = require_master(request)
        result = await ai_text(
            (
                f"Explain the operational bond between {req.source_system} and {req.target_system}.\n"
                f"Bond type: {req.bond_type}\nMode: {req.protocol_mode}\nSignal: {req.signal}\n"
                "Return a concise operational analysis of what should flow, what must be protected, and the expected value."
            ),
            workspace="bridge",
            source="carbon",
            max_tokens=280,
        )
        bond_id = new_id("cbond")
        db_exec(
            """
            INSERT INTO carbon_bonds(id,user_id,bond_type,source_system,target_system,protocol_mode,signal,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (bond_id, user["id"], req.bond_type, req.source_system, req.target_system, req.protocol_mode, req.signal, "active", now_iso()),
        )
        emit_carbon("bond_formed", {"source": req.source_system, "target": req.target_system, "signal": req.signal}, req.protocol_mode)
        return {
            "id": bond_id,
            "bond": req.model_dump(),
            "analysis": result["text"],
            "provider": result["provider"],
            "mode": carbon_modes.get(req.protocol_mode, carbon_modes["graphene"]),
        }

    @router.post("/api/carbon/think")
    async def carbon_think(req: CarbonThinkReq, request: Request):
        require_master(request)
        mode_info = carbon_modes.get(req.mode, carbon_modes["graphene"])
        result = await ai_text(
            (
                f"Operate in {mode_info['name']} mode.\n"
                f"Mode description: {mode_info['desc']}\n"
                f"Best use: {mode_info['use']}\n\n"
                f"Problem: {req.problem}\n\n"
                "Return a structured response with: Focus, Observations, Action Plan."
            ),
            workspace="bridge",
            source="carbon",
            max_tokens=700,
        )
        emit_carbon("think", {"mode": req.mode, "problem": req.problem[:120]}, req.mode)
        return {"mode": req.mode, "mode_info": mode_info, "result": result["text"], "provider": result["provider"]}

    @router.get("/api/carbon/stream")
    async def carbon_stream(request: Request):
        async def gen():
            while True:
                if await request.is_disconnected():
                    break
                state = get_state()
                payload = {
                    "avatars": state.get("avatar_state", {}).get("active", ["RAMA"]),
                    "protection": state.get("avatar_state", {}).get("protection_meter", 100),
                    "guardian": state.get("meta", {}).get("memory_guardian", "eternal"),
                    "hunt_count": len(state.get("praapti_hunts", [])),
                    "proposals": len([p for p in state.get("nirmaan_proposals", []) if not p.get("approved")]),
                    "vault_size": len(state.get("vault", [])),
                    "carbon_events": carbon_events[-5:],
                    "carbon_mode": state.get("settings", {}).get("carbon_mode", "graphene"),
                    "identity": state.get("meta", {}).get("identity", core_identity),
                    "at": now_iso(),
                }
                blob = json.dumps(payload, ensure_ascii=False)
                yield f"event: snapshot\ndata: {blob}\n\n"
                yield f"data: {blob}\n\n"
                await asyncio.sleep(6)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
