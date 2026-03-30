"""
Learning Engine Layer — Continuous-learning system for all brains.

Stores every decision signal (actions taken, approvals, rejections, user edits,
success/failure outcomes) and distils them into shared memory so that prompts,
templates, and decision rules can improve over time.

Key tables:
  learning_signals  — raw outcome records
  learning_insights — distilled improvement recommendations
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Signal types
# ---------------------------------------------------------------------------

SIGNAL_TYPES = frozenset({
    "action_approved",
    "action_rejected",
    "action_executed",
    "action_dismissed",
    "task_approved",
    "task_rejected",
    "user_edit",
    "outcome_success",
    "outcome_failure",
    "feedback",
})


class RecordSignalRequest(BaseModel):
    signal_type: str
    source_brain: str = "system"
    entity_type: str = ""       # task / action / event
    entity_id: str = ""
    detail: Dict[str, Any] = {}


class RecordInsightRequest(BaseModel):
    category: str               # prompt / template / decision_rule / workflow
    summary: str
    source_brain: str = "system"
    detail: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_learning_engine_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
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
            CREATE TABLE IF NOT EXISTS learning_signals (
                id           TEXT PRIMARY KEY,
                signal_type  TEXT NOT NULL,
                source_brain TEXT NOT NULL DEFAULT 'system',
                entity_type  TEXT NOT NULL DEFAULT '',
                entity_id    TEXT NOT NULL DEFAULT '',
                detail_json  TEXT NOT NULL DEFAULT '{}',
                created_at   TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS learning_insights (
                id           TEXT PRIMARY KEY,
                category     TEXT NOT NULL,
                summary      TEXT NOT NULL,
                source_brain TEXT NOT NULL DEFAULT 'system',
                detail_json  TEXT NOT NULL DEFAULT '{}',
                status       TEXT NOT NULL DEFAULT 'proposed',
                created_at   TEXT NOT NULL,
                resolved_at  TEXT
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Core functions
    # -----------------------------------------------------------------------

    def record_signal(
        signal_type: str,
        source_brain: str = "system",
        entity_type: str = "",
        entity_id: str = "",
        detail: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a learning signal (approval, rejection, edit, outcome…)."""
        if signal_type not in SIGNAL_TYPES:
            log.warning("[LearningEngine] unknown signal_type '%s' — recording anyway", signal_type)
        sig_id = new_id("lsig")
        created_at = now_iso()
        db_exec(
            "INSERT INTO learning_signals (id, signal_type, source_brain, entity_type, entity_id, detail_json, created_at) VALUES (?,?,?,?,?,?,?)",
            (sig_id, signal_type, source_brain, entity_type, entity_id, json.dumps(detail or {}), created_at),
        )
        log.info("[LearningEngine] signal recorded: %s %s/%s", signal_type, entity_type, entity_id)

        # Auto-update shared memory with latest signal summary
        memory_set = ctx.get("memory_set")
        if memory_set:
            memory_set(
                "action_history",
                f"{entity_type}:{entity_id}:last_signal",
                {"signal_type": signal_type, "source_brain": source_brain, "detail": detail or {}, "at": created_at},
                updated_by=source_brain,
            )

        return {"id": sig_id, "signal_type": signal_type, "created_at": created_at}

    def record_insight(
        category: str,
        summary: str,
        source_brain: str = "system",
        detail: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a learning insight (proposed improvement)."""
        insight_id = new_id("lins")
        created_at = now_iso()
        db_exec(
            "INSERT INTO learning_insights (id, category, summary, source_brain, detail_json, status, created_at) VALUES (?,?,?,?,?,?,?)",
            (insight_id, category, summary, source_brain, json.dumps(detail or {}), "proposed", created_at),
        )
        log.info("[LearningEngine] insight recorded: [%s] %s", category, summary[:80])
        return {"id": insight_id, "category": category, "summary": summary, "status": "proposed", "created_at": created_at}

    def get_signals(
        signal_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if signal_type:
            conditions.append("signal_type=?")
            params.append(signal_type)
        if entity_type:
            conditions.append("entity_type=?")
            params.append(entity_type)
        if entity_id:
            conditions.append("entity_id=?")
            params.append(entity_id)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = db_all(
            f"SELECT id, signal_type, source_brain, entity_type, entity_id, detail_json, created_at FROM learning_signals {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return [
            {
                "id": r[0], "signal_type": r[1], "source_brain": r[2],
                "entity_type": r[3], "entity_id": r[4],
                "detail": json.loads(r[5] or "{}"), "created_at": r[6],
            }
            for r in rows
        ]

    def get_insights(
        category: Optional[str] = None,
        status: Optional[str] = None,
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
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = db_all(
            f"SELECT id, category, summary, source_brain, detail_json, status, created_at, resolved_at FROM learning_insights {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return [
            {
                "id": r[0], "category": r[1], "summary": r[2], "source_brain": r[3],
                "detail": json.loads(r[4] or "{}"), "status": r[5],
                "created_at": r[6], "resolved_at": r[7],
            }
            for r in rows
        ]

    def update_insight_status(insight_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        resolved_at = now_iso() if new_status in ("accepted", "rejected", "implemented") else None
        db_exec(
            "UPDATE learning_insights SET status=?, resolved_at=? WHERE id=?",
            (new_status, resolved_at, insight_id),
        )
        rows = db_all(
            "SELECT id, category, summary, source_brain, detail_json, status, created_at, resolved_at FROM learning_insights WHERE id=?",
            (insight_id,),
        )
        if not rows:
            return None
        r = rows[0]
        return {
            "id": r[0], "category": r[1], "summary": r[2], "source_brain": r[3],
            "detail": json.loads(r[4] or "{}"), "status": r[5],
            "created_at": r[6], "resolved_at": r[7],
        }

    def learning_stats() -> Dict[str, Any]:
        """Return aggregate stats for the learning engine."""
        signal_count = db_all("SELECT COUNT(*) FROM learning_signals")
        insight_count = db_all("SELECT COUNT(*) FROM learning_insights")
        type_counts = db_all("SELECT signal_type, COUNT(*) as cnt FROM learning_signals GROUP BY signal_type ORDER BY cnt DESC")
        category_counts = db_all("SELECT category, COUNT(*) as cnt FROM learning_insights GROUP BY category ORDER BY cnt DESC")
        return {
            "total_signals": signal_count[0][0] if signal_count else 0,
            "total_insights": insight_count[0][0] if insight_count else 0,
            "signals_by_type": {r[0]: r[1] for r in type_counts} if type_counts else {},
            "insights_by_category": {r[0]: r[1] for r in category_counts} if category_counts else {},
        }

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.post("/api/learning/signal")
    async def api_record_signal(body: RecordSignalRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        sig = record_signal(
            signal_type=body.signal_type,
            source_brain=body.source_brain,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            detail=body.detail,
        )
        return {"ok": True, "signal": sig}

    @app.get("/api/learning/signals")
    async def api_list_signals(
        request: Request,
        signal_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
    ):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"ok": True, "signals": get_signals(signal_type=signal_type, entity_type=entity_type, entity_id=entity_id, limit=limit)}

    @app.post("/api/learning/insight")
    async def api_record_insight(body: RecordInsightRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        ins = record_insight(
            category=body.category,
            summary=body.summary,
            source_brain=body.source_brain,
            detail=body.detail,
        )
        return {"ok": True, "insight": ins}

    @app.get("/api/learning/insights")
    async def api_list_insights(
        request: Request,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"ok": True, "insights": get_insights(category=category, status=status, limit=limit)}

    @app.post("/api/learning/insights/{insight_id}/accept")
    async def api_accept_insight(insight_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")
        result = update_insight_status(insight_id, "accepted")
        if not result:
            raise HTTPException(status_code=404, detail="Insight not found")
        return {"ok": True, "insight": result}

    @app.post("/api/learning/insights/{insight_id}/reject")
    async def api_reject_insight(insight_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")
        result = update_insight_status(insight_id, "rejected")
        if not result:
            raise HTTPException(status_code=404, detail="Insight not found")
        return {"ok": True, "insight": result}

    @app.get("/api/learning/stats")
    async def api_learning_stats(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"ok": True, "stats": learning_stats()}

    # Export to ctx
    ctx["learning_record_signal"] = record_signal
    ctx["learning_record_insight"] = record_insight
    ctx["learning_get_signals"] = get_signals
    ctx["learning_get_insights"] = get_insights
    ctx["learning_update_insight"] = update_insight_status
    ctx["learning_stats"] = learning_stats

    log.info("[LearningEngine] layer installed")
    return ctx
