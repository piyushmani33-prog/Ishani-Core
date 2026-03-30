"""
Action Output Layer — Converts approved/aggregated tasks into concrete action
drafts (alerts, drafts, recommendations).

No auto-send: every action requires explicit human approval.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


class ExecuteActionRequest(BaseModel):
    pass  # body may be empty


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_action_output_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
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
            CREATE TABLE IF NOT EXISTS action_drafts (
                id          TEXT PRIMARY KEY,
                task_id     TEXT NOT NULL,
                action_type TEXT NOT NULL,
                content_json TEXT NOT NULL DEFAULT '{}',
                status      TEXT NOT NULL DEFAULT 'draft',
                created_at  TEXT NOT NULL,
                executed_at TEXT
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Helper functions
    # -----------------------------------------------------------------------

    def _row_to_dict(r) -> Dict[str, Any]:
        return {
            "id": r[0],
            "task_id": r[1],
            "action_type": r[2],
            "content": json.loads(r[3] or "{}"),
            "status": r[4],
            "created_at": r[5],
            "executed_at": r[6],
        }

    def create_action_from_task(task: Dict[str, Any]) -> Dict[str, Any]:
        """Derive an action_draft from an approved/aggregated task."""
        task_type = task.get("task_type", "alert")
        output = task.get("output_data", {})
        task_id = task.get("id", "")

        action_type_map = {
            "alert": "alert",
            "draft": "draft",
            "recommendation": "recommendation",
            "follow_up": "draft",
            "status_update": "alert",
        }
        action_type = action_type_map.get(task_type, "alert")

        content = {
            "brain_id": task.get("brain_id"),
            "event_id": task.get("event_id"),
            "message": output.get("message", ""),
            "details": output,
        }

        action_id = new_id("act")
        created_at = now_iso()
        db_exec(
            "INSERT INTO action_drafts (id, task_id, action_type, content_json, status, created_at) VALUES (?,?,?,?,?,?)",
            (action_id, task_id, action_type, json.dumps(content), "draft", created_at),
        )
        log.info("[ActionOutput] action_draft created: %s type=%s for task=%s", action_id, action_type, task_id)
        return {"id": action_id, "task_id": task_id, "action_type": action_type, "content": content, "status": "draft", "created_at": created_at}

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.get("/api/actions")
    async def api_list_actions(
        request: Request,
        status: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
    ):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        conditions = []
        params: List[Any] = []
        if status:
            conditions.append("status=?")
            params.append(status)
        if action_type:
            conditions.append("action_type=?")
            params.append(action_type)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = db_all(
            f"SELECT id, task_id, action_type, content_json, status, created_at, executed_at FROM action_drafts {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return {"ok": True, "actions": [_row_to_dict(r) for r in rows]}

    @app.post("/api/actions/{action_id}/execute")
    async def api_execute_action(action_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")

        rows = db_all("SELECT id, status FROM action_drafts WHERE id=?", (action_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Action not found")
        current_status = rows[0][1]
        if current_status not in ("draft", "approved"):
            raise HTTPException(status_code=400, detail=f"Cannot execute action in status '{current_status}'")

        executed_at = now_iso()
        db_exec("UPDATE action_drafts SET status='executed', executed_at=? WHERE id=?", (executed_at, action_id))
        return {"ok": True, "action_id": action_id, "status": "executed", "executed_at": executed_at}

    @app.post("/api/actions/{action_id}/dismiss")
    async def api_dismiss_action(action_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all("SELECT id FROM action_drafts WHERE id=?", (action_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Action not found")

        db_exec("UPDATE action_drafts SET status='dismissed' WHERE id=?", (action_id,))
        return {"ok": True, "action_id": action_id, "status": "dismissed"}

    # Export to ctx
    ctx["action_create_from_task"] = create_action_from_task

    log.info("[ActionOutput] layer installed")
    return ctx
