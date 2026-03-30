"""
Decision / Aggregator Layer — Merges compatible tasks, resolves conflicts,
and prioritises actions across brains.

Authority order (lowest number = highest authority):
  executive > secretary > domain > machine > tool > atom
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

# Brain layer authority (lower = more authority)
_LAYER_AUTHORITY = {
    "mother": 0,
    "executive": 1,
    "secretary": 2,
    "domain": 3,
    "machine": 4,
    "tool": 5,
    "atom": 6,
}

# Brains known to be in the executive layer
_EXECUTIVE_BRAINS = {"recruitment_executive", "cabinet_brain", "akshaya_brain", "carbon_brain", "interpreter_brain"}


class AggregatorRunRequest(BaseModel):
    event_id: str


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_decision_aggregator_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    log = ctx["log"]
    get_pending_tasks = ctx["task_get_pending"]
    update_task_status = ctx["task_update_status"]
    task_create = ctx["task_create"]

    # -----------------------------------------------------------------------
    # DB setup
    # -----------------------------------------------------------------------

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS aggregation_results (
                id                  TEXT PRIMARY KEY,
                event_id            TEXT NOT NULL,
                merged_tasks_json   TEXT NOT NULL DEFAULT '[]',
                conflicts_json      TEXT NOT NULL DEFAULT '[]',
                final_actions_json  TEXT NOT NULL DEFAULT '[]',
                created_at          TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Core aggregation logic
    # -----------------------------------------------------------------------

    def _brain_authority(brain_id: str) -> int:
        if brain_id in _EXECUTIVE_BRAINS:
            return _LAYER_AUTHORITY["executive"]
        return _LAYER_AUTHORITY["atom"]

    def aggregate_event(event_id: str) -> Dict[str, Any]:
        """Aggregate all pending tasks for *event_id*.

        Returns a dict with merged_tasks, conflicts, and final_actions.
        """
        pending = get_pending_tasks(event_id=event_id)
        if not pending:
            return {"merged_tasks": [], "conflicts": [], "final_actions": []}

        # Group by task_type
        by_type: Dict[str, List[Dict]] = {}
        for task in pending:
            by_type.setdefault(task["task_type"], []).append(task)

        merged_tasks: List[Dict] = []
        conflicts: List[Dict] = []
        final_actions: List[Dict] = []

        for task_type, tasks in by_type.items():
            if len(tasks) == 1:
                # Single task — promote straight to final_actions
                final_actions.append(tasks[0])
                update_task_status(tasks[0]["id"], "aggregated")
                continue

            # Sort by authority (most authoritative first), then priority (lower = higher priority)
            tasks_sorted = sorted(tasks, key=lambda t: (_brain_authority(t["brain_id"]), t["priority"]))

            # Check for contradictions: if output_data differs in intent, flag conflict
            # Simple heuristic: if tasks have different "message" prefixes
            unique_messages = set()
            for t in tasks_sorted:
                msg = t.get("output_data", {}).get("message", "")
                unique_messages.add(msg[:60])  # compare first 60 chars as rough intent key

            if len(unique_messages) > 1 and task_type not in ("alert", "status_update"):
                # Potential conflict — flag all, create resolution task
                for t in tasks_sorted:
                    update_task_status(t["id"], "conflict")
                    conflicts.append(t)

                resolution = task_create(
                    brain_id="system_aggregator",
                    event_id=event_id,
                    task_type=task_type,
                    input_data={"conflicting_task_ids": [t["id"] for t in tasks_sorted]},
                    output_data={"message": f"CONFLICT: {len(tasks_sorted)} brains disagree on task_type '{task_type}' — human review required."},
                    priority=1,
                )
                final_actions.append(resolution)
            else:
                # Merge: keep most authoritative, mark others as aggregated
                winner = tasks_sorted[0]

                # Merge output messages from all brains into winner's output
                combined_messages = " | ".join(
                    t.get("output_data", {}).get("message", "") for t in tasks_sorted if t.get("output_data", {}).get("message")
                )
                winner_output = dict(winner.get("output_data", {}))
                winner_output["merged_message"] = combined_messages
                winner_output["merged_from"] = [t["brain_id"] for t in tasks_sorted]

                db_exec(
                    "UPDATE brain_tasks SET output_json=? WHERE id=?",
                    (json.dumps(winner_output), winner["id"]),
                )
                update_task_status(winner["id"], "aggregated")
                for t in tasks_sorted[1:]:
                    update_task_status(t["id"], "aggregated")

                winner["output_data"] = winner_output
                merged_tasks.append(winner)
                final_actions.append(winner)

        # Persist result
        result_id = new_id("aggr")
        created_at = now_iso()
        db_exec(
            "INSERT INTO aggregation_results (id, event_id, merged_tasks_json, conflicts_json, final_actions_json, created_at) VALUES (?,?,?,?,?,?)",
            (
                result_id,
                event_id,
                json.dumps(merged_tasks),
                json.dumps(conflicts),
                json.dumps(final_actions),
                created_at,
            ),
        )

        log.info("[Aggregator] event=%s merged=%d conflicts=%d final=%d", event_id, len(merged_tasks), len(conflicts), len(final_actions))
        return {
            "id": result_id,
            "event_id": event_id,
            "merged_tasks": merged_tasks,
            "conflicts": conflicts,
            "final_actions": final_actions,
            "created_at": created_at,
        }

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.post("/api/aggregator/run")
    async def api_aggregator_run(body: AggregatorRunRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        result = aggregate_event(body.event_id)
        return {"ok": True, "result": result}

    @app.get("/api/aggregator/results/{event_id}")
    async def api_aggregator_results(event_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all(
            "SELECT id, event_id, merged_tasks_json, conflicts_json, final_actions_json, created_at FROM aggregation_results WHERE event_id=? ORDER BY created_at DESC",
            (event_id,),
        )
        results = [
            {
                "id": r[0],
                "event_id": r[1],
                "merged_tasks": json.loads(r[2] or "[]"),
                "conflicts": json.loads(r[3] or "[]"),
                "final_actions": json.loads(r[4] or "[]"),
                "created_at": r[5],
            }
            for r in rows
        ]
        return {"ok": True, "results": results}

    @app.post("/api/aggregator/auto")
    async def api_aggregator_auto(request: Request):
        """Run aggregation on all events that have pending tasks but no aggregation result yet."""
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Find event_ids with pending tasks
        rows = db_all(
            "SELECT DISTINCT event_id FROM brain_tasks WHERE status='pending' AND event_id IS NOT NULL"
        )
        event_ids = [r[0] for r in rows if r[0]]

        # Exclude already-aggregated events
        processed = []
        for eid in event_ids:
            existing = db_all("SELECT id FROM aggregation_results WHERE event_id=?", (eid,))
            if not existing:
                result = aggregate_event(eid)
                processed.append(result)

        return {"ok": True, "processed": len(processed), "results": processed}

    # Export to ctx
    ctx["aggregator_run"] = aggregate_event

    log.info("[Aggregator] layer installed")
    return ctx
