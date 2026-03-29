"""
Network router – master network desk + member network.

Handles:
  /api/network/*         — master-only professional network (connections, posts, signal scans)
  /api/member-network/*  — authenticated member network (connections, posts, openings, candidate journey)
"""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class NetworkPostReq(BaseModel):
    content: str
    kind: str = "post"


class NetworkConnReq(BaseModel):
    name: str
    title: str = ""
    company: str = ""
    linkedin: str = ""
    notes: str = ""


class NetworkSignalReq(BaseModel):
    query: str
    mode: str = "graphene"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_network_router(ctx: Dict[str, Any]) -> APIRouter:
    """Return an APIRouter with all /api/network/* and /api/member-network/* routes."""

    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
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

    def require_member(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
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

    def safe_db_all(query: str, params=()) -> List[Dict[str, Any]]:
        try:
            return db_all(query, params) or []
        except Exception:
            return []

    def member_network_state_payload(viewer=None) -> Dict[str, Any]:
        """Build the full member-network state payload for the given viewer."""
        user_id = (viewer or {}).get("id", "")
        user_email = ((viewer or {}).get("email") or "").strip().lower()
        connections = (
            safe_db_all("SELECT * FROM network_connections WHERE user_id=? ORDER BY created_at DESC LIMIT 24", (user_id,))
            if user_id
            else []
        )
        posts = (
            safe_db_all("SELECT * FROM network_posts WHERE user_id=? ORDER BY created_at DESC LIMIT 24", (user_id,))
            if user_id
            else []
        )
        openings = safe_db_all(
            """
            SELECT id,title,company_name,location,remote,job_type,experience_min,experience_max,skills,created_at
            FROM public_jobs
            WHERE lower(coalesce(status,''))='open'
            ORDER BY created_at DESC
            LIMIT 12
            """
        )
        companies = safe_db_all(
            """
            SELECT slug,name,tagline,website,city,plan,created_at
            FROM public_companies
            ORDER BY created_at DESC
            LIMIT 8
            """
        )
        profile: Dict[str, Any] = {}
        journeys: List[Dict[str, Any]] = []
        next_move = ""
        if user_email:
            profile_rows = safe_db_all(
                "SELECT * FROM candidate_profiles WHERE lower(email)=lower(?) ORDER BY updated_at DESC LIMIT 1",
                (user_email,),
            )
            if profile_rows:
                profile = profile_rows[0]
                journeys = safe_db_all(
                    "SELECT * FROM candidate_job_journeys WHERE profile_id=? ORDER BY updated_at DESC LIMIT 10",
                    (profile["id"],),
                )
                applications = int(profile.get("applications_count") or 0)
                interviews = int(profile.get("interviews_count") or 0)
                offers = int(profile.get("offers_count") or 0)
                if offers:
                    next_move = "Protect the best offer, confirm joining intent, and close loose interview loops."
                elif interviews:
                    next_move = "Stay ready for feedback and keep at least two active backup pipelines open."
                elif applications:
                    next_move = "Follow up on submitted roles, sharpen the resume for gaps, and keep sourcing."
                elif (profile.get("job_change_intent") or "") in {"active", "passive"}:
                    next_move = "Open to change is active. Apply to matching jobs and keep recruiter conversations warm."
        stats = {
            "connections": len(connections),
            "posts": len(posts),
            "openings": len(openings),
            "companies": len(companies),
            "applications": int(profile.get("applications_count") or 0),
            "interviews": int(profile.get("interviews_count") or 0),
            "offers": int(profile.get("offers_count") or 0),
        }
        return {
            "auth": {
                "authenticated": bool(viewer),
                "role": (viewer or {}).get("role", "guest"),
            },
            "viewer": {
                "name": (viewer or {}).get("name", ""),
                "email": (viewer or {}).get("email", ""),
                "role": (viewer or {}).get("role", "guest"),
            },
            "profile": profile,
            "journeys": journeys,
            "next_move": next_move,
            "connections": connections,
            "posts": posts,
            "openings": openings,
            "companies": companies,
            "stats": stats,
            "summary": {
                "headline": "One professional network for candidates, recruiters, and live hiring demand.",
                "member_message": (
                    "Your posts, connections, resume profile, and job journey stay local to your workspace."
                    if viewer
                    else "Sign in to turn this network into your private candidate desk with ATS-linked job journeys."
                ),
            },
        }

    # ------------------------------------------------------------------
    # Member-network routes (authenticated members)
    # ------------------------------------------------------------------

    @router.get("/api/member-network/public-state")
    async def member_network_public_state():
        return member_network_state_payload(None)

    @router.get("/api/member-network/state")
    async def member_network_get_state(request: Request):
        user = require_member(request)
        return member_network_state_payload(user)

    @router.post("/api/member-network/connect")
    async def member_network_add_connection(req: NetworkConnReq, request: Request):
        user = require_member(request)
        connection_id = new_id("mconn")
        db_exec(
            """
            INSERT INTO network_connections(id,user_id,name,title,company,linkedin,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (connection_id, user["id"], req.name, req.title, req.company, req.linkedin, req.notes, now_iso()),
        )
        return {"ok": True, "id": connection_id}

    @router.delete("/api/member-network/connections/{connection_id}")
    async def member_network_delete_connection(connection_id: str, request: Request):
        user = require_member(request)
        db_exec("DELETE FROM network_connections WHERE id=? AND user_id=?", (connection_id, user["id"]))
        return {"ok": True}

    @router.post("/api/member-network/post")
    async def member_network_create_post(req: NetworkPostReq, request: Request):
        user = require_member(request)
        result = await ai_text(
            (
                "Enhance this professional network update for a candidate and recruiter audience.\n"
                f"Kind: {req.kind}\n"
                f"Original:\n{req.content}\n\n"
                "Keep it human, credible, and concise. Do not sound robotic."
            ),
            workspace="network",
            source="member_network_post",
            max_tokens=220,
        )
        post_id = new_id("mpost")
        enhanced = result["text"] or req.content
        db_exec(
            """
            INSERT INTO network_posts(id,user_id,content,enhanced,kind,likes,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (post_id, user["id"], req.content, enhanced, req.kind, 0, now_iso()),
        )
        return {"ok": True, "id": post_id, "enhanced": enhanced, "provider": result["provider"]}

    @router.post("/api/member-network/posts/{post_id}/like")
    async def member_network_like_post(post_id: str, request: Request):
        user = require_member(request)
        db_exec("UPDATE network_posts SET likes = likes + 1 WHERE id=? AND user_id=?", (post_id, user["id"]))
        return {"ok": True}

    # ------------------------------------------------------------------
    # Master network routes
    # ------------------------------------------------------------------

    @router.get("/api/network/state")
    async def network_get_state(request: Request):
        user = require_master(request)
        conns = db_all("SELECT * FROM network_connections WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        posts = db_all("SELECT * FROM network_posts WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (user["id"],)) or []
        signals = db_all("SELECT * FROM network_signals WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user["id"],)) or []
        return {
            "connections": conns,
            "posts": posts,
            "signals": signals,
            "stats": {"connections": len(conns), "posts": len(posts), "signals": len(signals)},
        }

    @router.post("/api/network/connect")
    async def network_add_connection(req: NetworkConnReq, request: Request):
        user = require_master(request)
        connection_id = new_id("conn")
        db_exec(
            """
            INSERT INTO network_connections(id,user_id,name,title,company,linkedin,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (connection_id, user["id"], req.name, req.title, req.company, req.linkedin, req.notes, now_iso()),
        )
        emit_carbon("connection_added", {"name": req.name, "company": req.company}, "graphene")
        return {"ok": True, "id": connection_id}

    @router.delete("/api/network/connections/{connection_id}")
    async def network_delete_connection(connection_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM network_connections WHERE id=? AND user_id=?", (connection_id, user["id"]))
        return {"ok": True}

    @router.post("/api/network/post")
    async def network_create_post(req: NetworkPostReq, request: Request):
        user = require_master(request)
        result = await ai_text(
            (
                "Enhance this professional TechBuzz post for LinkedIn.\n"
                f"Kind: {req.kind}\nOriginal:\n{req.content}\n\n"
                "Keep it concise, specific, and credible."
            ),
            workspace="network",
            source="network_post",
            max_tokens=260,
        )
        post_id = new_id("post")
        enhanced = result["text"] or req.content
        db_exec(
            """
            INSERT INTO network_posts(id,user_id,content,enhanced,kind,likes,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (post_id, user["id"], req.content, enhanced, req.kind, 0, now_iso()),
        )
        emit_carbon("post_created", {"kind": req.kind}, "graphene")
        return {"ok": True, "id": post_id, "enhanced": enhanced, "provider": result["provider"]}

    @router.post("/api/network/signal")
    async def network_signal_scan(req: NetworkSignalReq, request: Request):
        user = require_master(request)
        mode_info = carbon_modes.get(req.mode, carbon_modes["graphene"])
        query_lower = (req.query or "").strip().lower()
        short_signal = any(term in query_lower for term in ("one line", "short line", "keep it short", "one short sentence"))
        result = await ai_text(
            (
                f"Analyze this market signal for {company_name}.\n"
                f"Mode: {mode_info['name']} - {mode_info['desc']}\n"
                f"Query: {req.query}\n"
                + (
                    "Return one short human line with the clearest market signal and the next move."
                    if short_signal
                    else "Return 4 concrete findings: talent market, pricing, competitor motion, opportunity."
                )
            ),
            workspace="network",
            source="network_signal",
            max_tokens=90 if short_signal else 520,
            use_web_search=True,
        )
        signal_id = new_id("sig")
        db_exec(
            """
            INSERT INTO network_signals(id,user_id,query,analysis,carbon_mode,created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (signal_id, user["id"], req.query, result["text"], req.mode, now_iso()),
        )
        emit_carbon("signal_scan", {"query": req.query, "mode": req.mode}, req.mode)
        return {
            "ok": True,
            "id": signal_id,
            "query": req.query,
            "analysis": result["text"],
            "mode": req.mode,
            "mode_info": mode_info,
            "provider": result["provider"],
        }

    @router.post("/api/network/posts/{post_id}/like")
    async def network_like_post(post_id: str, request: Request):
        user = require_master(request)
        db_exec("UPDATE network_posts SET likes = likes + 1 WHERE id=? AND user_id=?", (post_id, user["id"]))
        return {"ok": True}

    return router
