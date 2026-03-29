"""
HQ (Headquarters) router – master-only client & revenue desk.

Handles /api/hq/* endpoints:
  - Client pipeline management (add, move stage, delete)
  - Revenue & expense tracking
  - Team member management
  - AI-powered strategy planning
"""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class HQClientReq(BaseModel):
    name: str
    industry: str = ""
    value: float = 0
    stage: str = "prospect"
    contact: str = ""
    notes: str = ""


class HQClientMoveReq(BaseModel):
    stage: str


class HQRevenueReq(BaseModel):
    type: str = "revenue"
    amount: float
    source: str = ""
    category: str = ""


class HQTeamReq(BaseModel):
    name: str
    role: str = ""
    email: str = ""
    department: str = ""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_hq_router(ctx: Dict[str, Any]) -> APIRouter:
    """Return an APIRouter with all /api/hq/* routes registered."""

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
    emit_carbon = ctx["emit_carbon"]
    carbon_modes: Dict[str, Any] = ctx["CARBON_MODES"]

    router = APIRouter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def require_master(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user or user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Imperial access required")
        return user

    async def ai_text(
        prompt: str,
        *,
        workspace: str,
        source: str,
        max_tokens: int = 500,
        use_web_search: bool = False,
    ) -> Dict[str, Any]:
        return await generate_text(
            prompt,
            system=(
                f"You are {ai_name}, the {core_identity} mother-brain of {company_name}. "
                "Be specific, practical, and structured. Prefer actionable outputs over vague metaphors."
            ),
            max_tokens=max_tokens,
            use_web_search=use_web_search,
            workspace=workspace,
            source=source,
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @router.get("/api/hq/state")
    async def hq_get_state(request: Request):
        user = require_master(request)
        clients = db_all("SELECT * FROM hq_clients WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        revenue = db_all("SELECT * FROM hq_revenue WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        team = db_all("SELECT * FROM hq_team WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        total_revenue = sum(float(item.get("amount", 0) or 0) for item in revenue if item.get("type") == "revenue")
        total_expenses = sum(float(item.get("amount", 0) or 0) for item in revenue if item.get("type") == "expense")
        state = get_state()
        insight_result = await ai_text(
            (
                f"Give a sharp 2-sentence strategic insight for {company_name}.\n"
                f"Clients: {len(clients)}\nTeam: {len(team)}\nRevenue: ₹{total_revenue:,.0f}\n"
                f"Praapti hunts: {len(state.get('praapti_hunts', []))}\n"
                "Focus on today's highest-leverage move."
            ),
            workspace="hq",
            source="hq_insight",
            max_tokens=140,
        )
        return {
            "clients": clients,
            "revenue": revenue,
            "team": team,
            "metrics": {
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "net_profit": total_revenue - total_expenses,
                "active_clients": len([c for c in clients if c.get("stage") == "active"]),
                "prospects": len([c for c in clients if c.get("stage") == "prospect"]),
                "won": len([c for c in clients if c.get("stage") == "closed_won"]),
                "team_size": len(team),
                "praapti_hunts": len(state.get("praapti_hunts", [])),
                "vault_items": len(state.get("vault", [])),
            },
            "ai_insight": insight_result["text"],
            "carbon_mode": get_state().get("settings", {}).get("carbon_mode", "graphene"),
            "provider": insight_result["provider"],
        }

    @router.post("/api/hq/clients")
    async def hq_add_client(req: HQClientReq, request: Request):
        user = require_master(request)
        client_id = new_id("cl")
        db_exec(
            """
            INSERT INTO hq_clients(id,user_id,name,industry,value,stage,contact,notes,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (client_id, user["id"], req.name, req.industry, req.value, req.stage, req.contact, req.notes, now_iso(), now_iso()),
        )
        emit_carbon("client_added", {"name": req.name, "stage": req.stage}, "nanotube")
        return {"ok": True, "id": client_id}

    @router.put("/api/hq/clients/{client_id}/stage")
    async def hq_move_client(client_id: str, req: HQClientMoveReq, request: Request):
        user = require_master(request)
        db_exec("UPDATE hq_clients SET stage=?, updated_at=? WHERE id=? AND user_id=?", (req.stage, now_iso(), client_id, user["id"]))
        emit_carbon("client_moved", {"id": client_id, "stage": req.stage}, "nanotube")
        return {"ok": True}

    @router.delete("/api/hq/clients/{client_id}")
    async def hq_delete_client(client_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM hq_clients WHERE id=? AND user_id=?", (client_id, user["id"]))
        return {"ok": True}

    @router.post("/api/hq/revenue")
    async def hq_add_revenue(req: HQRevenueReq, request: Request):
        user = require_master(request)
        revenue_id = new_id("rev")
        db_exec(
            """
            INSERT INTO hq_revenue(id,user_id,type,amount,source,category,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (revenue_id, user["id"], req.type, req.amount, req.source, req.category, now_iso()),
        )
        emit_carbon("revenue_entry", {"type": req.type, "amount": req.amount}, "nanotube")
        return {"ok": True, "id": revenue_id}

    @router.post("/api/hq/team")
    async def hq_add_team(req: HQTeamReq, request: Request):
        user = require_master(request)
        team_id = new_id("tm")
        db_exec(
            """
            INSERT INTO hq_team(id,user_id,name,role,email,department,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (team_id, user["id"], req.name, req.role, req.email, req.department, now_iso()),
        )
        return {"ok": True, "id": team_id}

    @router.delete("/api/hq/team/{team_id}")
    async def hq_delete_team(team_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM hq_team WHERE id=? AND user_id=?", (team_id, user["id"]))
        return {"ok": True}

    @router.post("/api/hq/strategy")
    async def hq_strategy(request: Request):
        user = require_master(request)
        body = await request.json()
        goal = body.get("goal", "Grow TechBuzz revenue")
        mode = body.get("mode", "diamond")
        mode_info = carbon_modes.get(mode, carbon_modes["diamond"])
        revenue = db_all("SELECT * FROM hq_revenue WHERE user_id=?", (user["id"],)) or []
        clients = db_all("SELECT * FROM hq_clients WHERE user_id=?", (user["id"],)) or []
        total_revenue = sum(float(item.get("amount", 0) or 0) for item in revenue if item.get("type") == "revenue")
        result = await ai_text(
            (
                f"Operate in {mode_info['name']} mode.\n"
                f"Goal: {goal}\n"
                f"Active clients: {len([c for c in clients if c.get('stage') == 'active'])}\n"
                f"Total revenue: ₹{total_revenue:,.0f}\n"
                "Provide sections: Immediate Actions, Growth Levers, Risks, Next 7 Days."
            ),
            workspace="hq",
            source="hq_strategy",
            max_tokens=780,
        )
        emit_carbon("strategy_run", {"goal": goal[:100], "mode": mode}, mode)
        return {"result": result["text"], "mode": mode, "mode_info": mode_info, "provider": result["provider"]}

    return router
