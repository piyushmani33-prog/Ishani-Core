"""
Evolution Layer — Brain evolution / self-improvement system.

Allows brains to propose workflow improvements, template refinements, and
decision-rule optimisations.  All proposals go through human review — the
system NEVER modifies its own code or deploys changes automatically.

Key tables:
  evolution_proposals — improvement suggestions from brains
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Proposal categories
# ---------------------------------------------------------------------------

PROPOSAL_CATEGORIES = frozenset({
    "workflow",         # improve an operational workflow
    "template",         # refine a prompt or message template
    "decision_rule",    # change how conflicts or priorities are resolved
    "integration",      # suggest a new data source or tool integration
    "performance",      # speed / efficiency improvement
    "ux",               # user-experience improvement
})


class SubmitProposalRequest(BaseModel):
    source_brain: str
    category: str           # must be one of PROPOSAL_CATEGORIES
    title: str
    description: str
    proposed_change: Dict[str, Any] = {}
    evidence: Dict[str, Any] = {}   # supporting data (signal counts, examples…)
    priority: int = 5               # 1 = critical, 10 = nice-to-have


class ReviewProposalRequest(BaseModel):
    decision: str           # accepted | rejected | deferred
    review_notes: str = ""


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_evolution_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    log = ctx["log"]

    # -----------------------------------------------------------------------
    # DB setup
    # -----------------------------------------------------------------------

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS evolution_proposals (
                id              TEXT PRIMARY KEY,
                source_brain    TEXT NOT NULL,
                category        TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT NOT NULL DEFAULT '',
                proposed_change TEXT NOT NULL DEFAULT '{}',
                evidence_json   TEXT NOT NULL DEFAULT '{}',
                priority        INTEGER NOT NULL DEFAULT 5,
                status          TEXT NOT NULL DEFAULT 'proposed',
                review_notes    TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL,
                reviewed_at     TEXT
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Core functions
    # -----------------------------------------------------------------------

    def _row_to_dict(r) -> Dict[str, Any]:
        return {
            "id": r[0],
            "source_brain": r[1],
            "category": r[2],
            "title": r[3],
            "description": r[4],
            "proposed_change": json.loads(r[5] or "{}"),
            "evidence": json.loads(r[6] or "{}"),
            "priority": r[7],
            "status": r[8],
            "review_notes": r[9],
            "created_at": r[10],
            "reviewed_at": r[11],
        }

    def submit_proposal(
        source_brain: str,
        category: str,
        title: str,
        description: str = "",
        proposed_change: Optional[Dict[str, Any]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        priority: int = 5,
    ) -> Dict[str, Any]:
        if category not in PROPOSAL_CATEGORIES:
            log.warning("[Evolution] unknown category '%s' — recording anyway", category)
        prop_id = new_id("evol")
        created_at = now_iso()
        db_exec(
            "INSERT INTO evolution_proposals (id, source_brain, category, title, description, proposed_change, evidence_json, priority, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (prop_id, source_brain, category, title, description, json.dumps(proposed_change or {}), json.dumps(evidence or {}), priority, "proposed", created_at),
        )
        log.info("[Evolution] proposal submitted by %s: [%s] %s", source_brain, category, title[:60])
        return {
            "id": prop_id, "source_brain": source_brain, "category": category,
            "title": title, "status": "proposed", "created_at": created_at,
        }

    def review_proposal(proposal_id: str, decision: str, review_notes: str = "") -> Optional[Dict[str, Any]]:
        if decision not in ("accepted", "rejected", "deferred"):
            raise ValueError(f"Invalid decision '{decision}'; must be accepted, rejected, or deferred")
        reviewed_at = now_iso() if decision in ("accepted", "rejected") else None
        db_exec(
            "UPDATE evolution_proposals SET status=?, review_notes=?, reviewed_at=? WHERE id=?",
            (decision, review_notes, reviewed_at, proposal_id),
        )
        rows = db_all(
            "SELECT id, source_brain, category, title, description, proposed_change, evidence_json, priority, status, review_notes, created_at, reviewed_at FROM evolution_proposals WHERE id=?",
            (proposal_id,),
        )
        return _row_to_dict(rows[0]) if rows else None

    def list_proposals(
        category: Optional[str] = None,
        status: Optional[str] = None,
        source_brain: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if category:
            conditions.append("category=?")
            params.append(category)
        if status:
            conditions.append("status=?")
            params.append(status)
        if source_brain:
            conditions.append("source_brain=?")
            params.append(source_brain)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = db_all(
            f"SELECT id, source_brain, category, title, description, proposed_change, evidence_json, priority, status, review_notes, created_at, reviewed_at FROM evolution_proposals {where} ORDER BY priority ASC, created_at DESC LIMIT ?",
            tuple(params),
        )
        return [_row_to_dict(r) for r in rows]

    def evolution_stats() -> Dict[str, Any]:
        total = db_all("SELECT COUNT(*) FROM evolution_proposals")
        by_status = db_all("SELECT status, COUNT(*) as cnt FROM evolution_proposals GROUP BY status ORDER BY cnt DESC")
        by_cat = db_all("SELECT category, COUNT(*) as cnt FROM evolution_proposals GROUP BY category ORDER BY cnt DESC")
        return {
            "total_proposals": total[0][0] if total else 0,
            "by_status": {r[0]: r[1] for r in by_status} if by_status else {},
            "by_category": {r[0]: r[1] for r in by_cat} if by_cat else {},
        }

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.post("/api/evolution/propose")
    async def api_submit_proposal(body: SubmitProposalRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        prop = submit_proposal(
            source_brain=body.source_brain,
            category=body.category,
            title=body.title,
            description=body.description,
            proposed_change=body.proposed_change,
            evidence=body.evidence,
            priority=body.priority,
        )
        return {"ok": True, "proposal": prop}

    @app.get("/api/evolution/proposals")
    async def api_list_proposals(
        request: Request,
        category: Optional[str] = None,
        status: Optional[str] = None,
        source_brain: Optional[str] = None,
        limit: int = 50,
    ):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"ok": True, "proposals": list_proposals(category=category, status=status, source_brain=source_brain, limit=limit)}

    @app.get("/api/evolution/proposals/{proposal_id}")
    async def api_get_proposal(proposal_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        rows = db_all(
            "SELECT id, source_brain, category, title, description, proposed_change, evidence_json, priority, status, review_notes, created_at, reviewed_at FROM evolution_proposals WHERE id=?",
            (proposal_id,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return {"ok": True, "proposal": _row_to_dict(rows[0])}

    @app.post("/api/evolution/proposals/{proposal_id}/review")
    async def api_review_proposal(proposal_id: str, body: ReviewProposalRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")
        try:
            result = review_proposal(proposal_id, body.decision, body.review_notes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if not result:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return {"ok": True, "proposal": result}

    @app.get("/api/evolution/stats")
    async def api_evolution_stats(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"ok": True, "stats": evolution_stats()}

    # Export to ctx
    ctx["evolution_submit_proposal"] = submit_proposal
    ctx["evolution_review_proposal"] = review_proposal
    ctx["evolution_list_proposals"] = list_proposals
    ctx["evolution_stats"] = evolution_stats

    log.info("[Evolution] layer installed")
    return ctx
