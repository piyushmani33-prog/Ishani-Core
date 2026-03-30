"""
Task System Layer — Brain task store with approve/reject workflows.

Multiple brains can create tasks simultaneously for the same event.
Tasks move through: pending → aggregated → approved/rejected → executed.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    brain_id: str
    event_id: Optional[str] = None
    task_type: str  # alert, draft, recommendation, follow_up, status_update
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    priority: int = 5


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_task_system_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    db_one = ctx.get("db_one")
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
            CREATE TABLE IF NOT EXISTS brain_tasks (
                id          TEXT PRIMARY KEY,
                brain_id    TEXT NOT NULL,
                event_id    TEXT,
                task_type   TEXT NOT NULL,
                input_json  TEXT NOT NULL DEFAULT '{}',
                output_json TEXT NOT NULL DEFAULT '{}',
                priority    INTEGER NOT NULL DEFAULT 5,
                status      TEXT NOT NULL DEFAULT 'pending',
                created_at  TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Helper functions (also exported via ctx)
    # -----------------------------------------------------------------------

    def create_task(
        brain_id: str,
        event_id: Optional[str],
        task_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        priority: int = 5,
    ) -> Dict[str, Any]:
        task_id = new_id("task")
        created_at = now_iso()
        db_exec(
            "INSERT INTO brain_tasks (id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (task_id, brain_id, event_id, task_type, json.dumps(input_data), json.dumps(output_data), priority, "pending", created_at),
        )
        log.info("[TaskSystem] task created: %s by brain=%s type=%s", task_id, brain_id, task_type)
        return {
            "id": task_id,
            "brain_id": brain_id,
            "event_id": event_id,
            "task_type": task_type,
            "input_data": input_data,
            "output_data": output_data,
            "priority": priority,
            "status": "pending",
            "created_at": created_at,
        }

    def _row_to_dict(r) -> Dict[str, Any]:
        return {
            "id": r[0],
            "brain_id": r[1],
            "event_id": r[2],
            "task_type": r[3],
            "input_data": json.loads(r[4] or "{}"),
            "output_data": json.loads(r[5] or "{}"),
            "priority": r[6],
            "status": r[7],
            "created_at": r[8],
            "resolved_at": r[9],
        }

    def get_pending_tasks(brain_id: Optional[str] = None, event_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if brain_id and event_id:
            rows = db_all(
                "SELECT id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at, resolved_at FROM brain_tasks WHERE status='pending' AND brain_id=? AND event_id=? ORDER BY priority ASC, created_at ASC",
                (brain_id, event_id),
            )
        elif brain_id:
            rows = db_all(
                "SELECT id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at, resolved_at FROM brain_tasks WHERE status='pending' AND brain_id=? ORDER BY priority ASC, created_at ASC",
                (brain_id,),
            )
        elif event_id:
            rows = db_all(
                "SELECT id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at, resolved_at FROM brain_tasks WHERE status='pending' AND event_id=? ORDER BY priority ASC, created_at ASC",
                (event_id,),
            )
        else:
            rows = db_all(
                "SELECT id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at, resolved_at FROM brain_tasks WHERE status='pending' ORDER BY priority ASC, created_at ASC",
            )
        return [_row_to_dict(r) for r in rows]

    def update_task_status(task_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        resolved_at = now_iso() if new_status in ("approved", "executed", "rejected", "conflict") else None
        db_exec(
            "UPDATE brain_tasks SET status=?, resolved_at=? WHERE id=?",
            (new_status, resolved_at, task_id),
        )
        rows = db_all(
            "SELECT id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at, resolved_at FROM brain_tasks WHERE id=?",
            (task_id,),
        )
        return _row_to_dict(rows[0]) if rows else None

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.get("/api/tasks")
    async def api_list_tasks(
        request: Request,
        brain_id: Optional[str] = None,
        status: Optional[str] = None,
        event_id: Optional[str] = None,
        limit: int = 100,
    ):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Build dynamic query
        conditions = []
        params: List[Any] = []
        if brain_id:
            conditions.append("brain_id=?")
            params.append(brain_id)
        if status:
            conditions.append("status=?")
            params.append(status)
        if event_id:
            conditions.append("event_id=?")
            params.append(event_id)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = db_all(
            f"SELECT id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at, resolved_at FROM brain_tasks {where} ORDER BY priority ASC, created_at DESC LIMIT ?",
            tuple(params),
        )
        return {"ok": True, "tasks": [_row_to_dict(r) for r in rows]}

    @app.get("/api/tasks/{task_id}")
    async def api_get_task(task_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all(
            "SELECT id, brain_id, event_id, task_type, input_json, output_json, priority, status, created_at, resolved_at FROM brain_tasks WHERE id=?",
            (task_id,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"ok": True, "task": _row_to_dict(rows[0])}

    @app.post("/api/tasks/{task_id}/approve")
    async def api_approve_task(task_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")

        task = update_task_status(task_id, "approved")
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"ok": True, "task": task}

    @app.post("/api/tasks/{task_id}/reject")
    async def api_reject_task(task_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")

        task = update_task_status(task_id, "rejected")
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"ok": True, "task": task}

    # Export helpers to ctx
    ctx["task_create"] = create_task
    ctx["task_get_pending"] = get_pending_tasks
    ctx["task_update_status"] = update_task_status

    log.info("[TaskSystem] layer installed")
    return ctx
