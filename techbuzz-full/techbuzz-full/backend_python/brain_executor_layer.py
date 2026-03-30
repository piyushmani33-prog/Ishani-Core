"""
Brain Executor Layer — Independent, concurrent brain execution per event.

Each registered brain handler processes events in isolation; failures in one
brain do not affect others.  Brain registration is also exposed to ctx so that
downstream layers (task system, aggregator …) can register additional brains.
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TriggerEventRequest(BaseModel):
    event_type: str
    source_brain: str = "manual"
    payload: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_brain_executor_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    log = ctx["log"]
    event_bus_subscribe = ctx["event_bus_subscribe"]
    event_bus_publish = ctx["event_bus_publish"]

    # brain_id → {event_types: [...], handler: fn, description: str}
    _brain_handlers: Dict[str, Dict[str, Any]] = {}

    # -----------------------------------------------------------------------
    # DB setup
    # -----------------------------------------------------------------------

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_execution_log (
                id          TEXT PRIMARY KEY,
                brain_id    TEXT NOT NULL,
                event_id    TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'ok',
                error_msg   TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------------

    def register_brain_handler(
        brain_id: str,
        event_types: List[str],
        handler_fn: Callable,
        description: str = "",
    ) -> None:
        """Register *handler_fn* to run whenever any of *event_types* fires."""
        _brain_handlers[brain_id] = {
            "event_types": event_types,
            "handler": handler_fn,
            "description": description,
        }
        for et in event_types:
            event_bus_subscribe(et, _make_dispatch(brain_id, handler_fn))
        log.info("[BrainExecutor] registered brain '%s' for events: %s", brain_id, event_types)

    def _make_dispatch(brain_id: str, handler_fn: Callable) -> Callable:
        """Wrap *handler_fn* so each invocation is logged and fault-isolated."""
        async def _dispatch(event: Dict[str, Any]) -> None:
            exec_id = new_id("bexec")
            created_at = now_iso()
            event_id = event.get("event_id", "")
            event_type = event.get("event_type", "")
            status = "ok"
            error_msg = None
            try:
                result = handler_fn(event)
                if asyncio.isfuture(result) or asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                status = "error"
                error_msg = str(exc)
                log.warning("[BrainExecutor] brain '%s' failed on event '%s': %s", brain_id, event_id, exc)
            finally:
                db_exec(
                    "INSERT INTO brain_execution_log (id, brain_id, event_id, event_type, status, error_msg, created_at) VALUES (?,?,?,?,?,?,?)",
                    (exec_id, brain_id, event_id, event_type, status, error_msg, created_at),
                )
        _dispatch.__name__ = f"dispatch_{brain_id}"
        return _dispatch

    # -----------------------------------------------------------------------
    # Built-in brain handlers — these create tasks via task_system helpers
    # registered after task_system_layer is available (lazy via ctx lookup)
    # -----------------------------------------------------------------------

    def _ats_kanban_handler(event: Dict[str, Any]) -> None:
        """tool_ats_kanban: reacts to tracker.updated and candidate.inactive."""
        create_task = ctx.get("task_create")
        if create_task is None:
            return
        event_type = event.get("event_type", "")
        event_id = event.get("event_id", "")
        payload = event.get("payload", {})

        if event_type == "tracker.updated":
            create_task(
                brain_id="tool_ats_kanban",
                event_id=event_id,
                task_type="status_update",
                input_data=payload,
                output_data={"message": "ATS Kanban board refreshed for updated tracker row.", "row_id": payload.get("row_id")},
                priority=4,
            )
        elif event_type == "candidate.inactive":
            create_task(
                brain_id="tool_ats_kanban",
                event_id=event_id,
                task_type="follow_up",
                input_data=payload,
                output_data={"message": f"Candidate {payload.get('candidate_name', '')} flagged as inactive — follow-up recommended."},
                priority=3,
            )

    def _interpreter_handler(event: Dict[str, Any]) -> None:
        """interpreter_brain: logs every event as an alert task."""
        create_task = ctx.get("task_create")
        if create_task is None:
            return
        create_task(
            brain_id="interpreter_brain",
            event_id=event.get("event_id", ""),
            task_type="alert",
            input_data=event.get("payload", {}),
            output_data={"message": f"[Interpreter] Event '{event.get('event_type')}' received and logged."},
            priority=7,
        )

    def _recruitment_executive_handler(event: Dict[str, Any]) -> None:
        """recruitment_executive: high-level oversight task for every event."""
        create_task = ctx.get("task_create")
        if create_task is None:
            return
        create_task(
            brain_id="recruitment_executive",
            event_id=event.get("event_id", ""),
            task_type="recommendation",
            input_data=event.get("payload", {}),
            output_data={"message": f"Executive review required for event '{event.get('event_type')}'."},
            priority=2,
        )

    # Register built-in brains
    register_brain_handler(
        "tool_ats_kanban",
        ["tracker.updated", "candidate.inactive"],
        _ats_kanban_handler,
        description="ATS Kanban board updater",
    )
    register_brain_handler(
        "interpreter_brain",
        ["tracker.updated", "candidate.inactive", "interview.scheduled"],
        _interpreter_handler,
        description="Interpreter brain — logs all events",
    )
    register_brain_handler(
        "recruitment_executive",
        ["tracker.updated", "candidate.inactive", "interview.scheduled"],
        _recruitment_executive_handler,
        description="Recruitment executive oversight",
    )

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.post("/api/brain-executor/trigger")
    async def api_trigger_event(body: TriggerEventRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        event = await event_bus_publish(body.event_type, body.payload, source_brain=body.source_brain)
        return {"ok": True, "event": event}

    @app.get("/api/brain-executor/handlers")
    async def api_list_handlers(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        handlers = []
        for brain_id, info in _brain_handlers.items():
            handlers.append({
                "brain_id": brain_id,
                "event_types": info["event_types"],
                "description": info["description"],
            })
        return {"ok": True, "handlers": handlers}

    @app.get("/api/brain-executor/log")
    async def api_execution_log(request: Request, limit: int = 50):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all(
            "SELECT id, brain_id, event_id, event_type, status, error_msg, created_at FROM brain_execution_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return {
            "ok": True,
            "log": [
                {"id": r[0], "brain_id": r[1], "event_id": r[2], "event_type": r[3], "status": r[4], "error_msg": r[5], "created_at": r[6]}
                for r in rows
            ],
        }

    ctx["register_brain_handler"] = register_brain_handler

    log.info("[BrainExecutor] layer installed")
    return ctx
