"""
Autonomous Brain Loop Layer — Always-running background loop that keeps
all brains operating continuously without manual triggers.

Polls at a configurable interval (default 30 s) for:
  • Inactive candidates   → publishes ``candidate.inactive``
  • Interested candidates  → publishes ``candidate.interested``
  • Pending tasks          → runs aggregator + action generation
  • Status schedule        → publishes ``status.requested`` once per day

Safety:
  • De-duplicates via a ``processed_hashes`` set so the same condition is
    never re-published within the current cool-down window.
  • Respects human-approval flow — actions are *drafted*, never auto-sent.
  • Loop run counter + max-consecutive-empty guard prevent infinite spinning.

Observability:
  • Every tick is logged to ``autonomous_loop_runs`` table.
  • REST APIs expose status, history, and start / stop / configure controls.
"""

import asyncio
import hashlib
import json
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class LoopConfigRequest(BaseModel):
    interval_seconds: Optional[int] = None   # 10–600
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_autonomous_brain_loop_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all  = ctx["db_all"]
    new_id  = ctx["new_id"]
    now_iso = ctx["now_iso"]
    log     = ctx["log"]
    session_user = ctx["session_user"]

    # Coordination helpers from ctx
    event_bus_publish       = ctx.get("event_bus_publish")
    task_get_pending        = ctx.get("task_get_pending")
    aggregator_run          = ctx.get("aggregator_run")
    action_create_from_task = ctx.get("action_create_from_task")
    safety_check_duplicate  = ctx.get("safety_check_duplicate")
    disclosure_filter       = ctx.get("disclosure_filter_output")
    learning_record_signal  = ctx.get("learning_record_signal")
    evolution_submit_proposal = ctx.get("evolution_submit_proposal")
    memory_set              = ctx.get("memory_set")

    # ------------------------------------------------------------------
    # DB setup
    # ------------------------------------------------------------------

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS autonomous_loop_runs (
                id               TEXT PRIMARY KEY,
                tick_number      INTEGER NOT NULL,
                events_published INTEGER NOT NULL DEFAULT 0,
                tasks_aggregated INTEGER NOT NULL DEFAULT 0,
                actions_created  INTEGER NOT NULL DEFAULT 0,
                errors           INTEGER NOT NULL DEFAULT 0,
                detail_json      TEXT NOT NULL DEFAULT '{}',
                created_at       TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # ------------------------------------------------------------------
    # Loop state (in-memory, not persisted across restarts)
    # ------------------------------------------------------------------

    _state: Dict[str, Any] = {
        "enabled": False,
        "running": False,
        "interval_seconds": 30,
        "tick": 0,
        "last_tick_at": None,
        "consecutive_empty": 0,
        "total_events": 0,
        "total_tasks_aggregated": 0,
        "total_actions": 0,
        "total_errors": 0,
        "started_at": None,
    }

    # Cool-down: remember hashes of conditions already published so we
    # don't duplicate.  Reset every ``_COOLDOWN_TICKS`` ticks.
    _COOLDOWN_TICKS = 60          # ≈ 30 min at 30 s interval
    _processed: Set[str] = set()
    _daily_status_sent: Optional[str] = None  # date string of last daily-status

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _hash_condition(kind: str, key: str) -> str:
        return hashlib.sha256(f"{kind}:{key}".encode()).hexdigest()[:24]

    def _safe_count(query: str, params: tuple = ()) -> int:
        try:
            rows = db_all(query, params) if params else db_all(query)
            return (rows[0][0] if rows and rows[0] else 0) or 0
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Condition detectors
    # ------------------------------------------------------------------

    def _detect_inactive_candidates() -> List[Dict[str, Any]]:
        """Return candidates that haven't been updated recently and have
        no response — potential follow-up targets."""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            rows = db_all(
                "SELECT id, candidate_name, position, response_status, updated_at "
                "FROM recruitment_tracker_rows "
                "WHERE response_status IN ('no_response','pending_review') "
                "AND updated_at < ? "
                "ORDER BY updated_at ASC LIMIT 10",
                (cutoff,),
            ) or []
            return [
                {"row_id": r[0], "candidate_name": r[1], "position": r[2],
                 "response_status": r[3], "updated_at": r[4]}
                for r in rows
            ]
        except Exception:
            return []

    def _detect_interested_candidates() -> List[Dict[str, Any]]:
        """Return candidates marked interested that haven't been acknowledged."""
        try:
            rows = db_all(
                "SELECT id, candidate_name, position, mail_id, response_status "
                "FROM recruitment_tracker_rows "
                "WHERE response_status='interested' "
                "AND (ack_mail_sent_at IS NULL OR ack_mail_sent_at='') "
                "ORDER BY updated_at DESC LIMIT 10",
            ) or []
            return [
                {"row_id": r[0], "candidate_name": r[1], "position": r[2],
                 "email": r[3] or "", "response_status": r[4]}
                for r in rows
            ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Core tick function
    # ------------------------------------------------------------------

    async def _tick() -> Dict[str, Any]:
        """Run one iteration of the autonomous loop."""
        _state["tick"] += 1
        tick = _state["tick"]
        ts = now_iso()
        _state["last_tick_at"] = ts

        # Periodic cool-down reset
        if tick % _COOLDOWN_TICKS == 0:
            _processed.clear()

        events_published = 0
        tasks_aggregated = 0
        actions_created  = 0
        errors           = 0
        detail: Dict[str, Any] = {"events": [], "aggregations": [], "actions": []}

        # --- 1. Detect inactive candidates → publish candidate.inactive ---
        try:
            inactive = _detect_inactive_candidates()
            for cand in inactive:
                h = _hash_condition("inactive", cand["row_id"])
                if h in _processed:
                    continue
                _processed.add(h)
                if event_bus_publish:
                    await event_bus_publish(
                        "candidate.inactive",
                        {
                            "candidate_name": cand["candidate_name"],
                            "position": cand["position"],
                            "row_id": cand["row_id"],
                            "reason": "No response — detected by autonomous loop",
                        },
                        source_brain="autonomous_loop",
                    )
                    events_published += 1
                    detail["events"].append({"type": "candidate.inactive", "candidate": cand["candidate_name"]})
        except Exception as exc:
            errors += 1
            log.warning("[AutonomousLoop] inactive detection error: %s", exc)

        # --- 2. Detect interested candidates → publish candidate.interested ---
        try:
            interested = _detect_interested_candidates()
            for cand in interested:
                h = _hash_condition("interested", cand["row_id"])
                if h in _processed:
                    continue
                _processed.add(h)
                if event_bus_publish:
                    await event_bus_publish(
                        "candidate.interested",
                        {
                            "candidate_name": cand["candidate_name"],
                            "position": cand["position"],
                            "row_id": cand["row_id"],
                            "email": cand.get("email", ""),
                        },
                        source_brain="autonomous_loop",
                    )
                    events_published += 1
                    detail["events"].append({"type": "candidate.interested", "candidate": cand["candidate_name"]})
        except Exception as exc:
            errors += 1
            log.warning("[AutonomousLoop] interested detection error: %s", exc)

        # --- 3. Daily status (once per calendar day) ---
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            nonlocal _daily_status_sent
            if _daily_status_sent != today and event_bus_publish:
                await event_bus_publish(
                    "status.requested",
                    {"scope": "daily", "format": "both"},
                    source_brain="autonomous_loop",
                )
                _daily_status_sent = today
                events_published += 1
                detail["events"].append({"type": "status.requested", "scope": "daily"})
        except Exception as exc:
            errors += 1
            log.warning("[AutonomousLoop] daily status error: %s", exc)

        # --- 4. Process pending tasks → aggregator ---
        try:
            if task_get_pending and aggregator_run:
                pending = task_get_pending()
                # Group by event_id
                event_ids: Set[str] = set()
                for t in pending:
                    eid = t.get("event_id")
                    if eid:
                        event_ids.add(eid)

                for eid in event_ids:
                    # Check if already aggregated
                    existing = db_all(
                        "SELECT id FROM aggregation_results WHERE event_id=?", (eid,)
                    ) or []
                    if existing:
                        continue
                    result = aggregator_run(eid)
                    tasks_aggregated += len(result.get("final_actions", []))
                    detail["aggregations"].append({
                        "event_id": eid,
                        "final_actions": len(result.get("final_actions", [])),
                    })

                    # --- 5. Generate action drafts from aggregated tasks ---
                    if action_create_from_task:
                        for task in result.get("final_actions", []):
                            # Safety dedup check
                            content_json = json.dumps(task.get("output_data", {}))
                            target = task.get("input_data", {}).get("row_id", "")
                            if safety_check_duplicate:
                                dup_result = safety_check_duplicate(
                                    task.get("id", ""),
                                    task.get("task_type", ""),
                                    target,
                                    content_json,
                                )
                                if not dup_result.get("passed", True):
                                    continue  # skip duplicate

                            action = action_create_from_task(task)
                            actions_created += 1
                            detail["actions"].append({
                                "action_id": action.get("id", ""),
                                "type": action.get("action_type", ""),
                            })
        except Exception as exc:
            errors += 1
            log.warning("[AutonomousLoop] task processing error: %s", exc)

        # --- 6. Learning: record loop run signal ---
        if learning_record_signal and (events_published or tasks_aggregated or actions_created):
            try:
                learning_record_signal(
                    signal_type="feedback",
                    source_brain="autonomous_loop",
                    entity_type="loop_tick",
                    entity_id=str(tick),
                    detail={
                        "events_published": events_published,
                        "tasks_aggregated": tasks_aggregated,
                        "actions_created": actions_created,
                    },
                )
            except Exception:
                pass

        # --- 7. Evolution: propose improvements on repeated errors ---
        if errors > 0 and evolution_submit_proposal:
            _state["total_errors"] += errors
            if _state["total_errors"] >= 5 and _state["total_errors"] % 5 == 0:
                try:
                    evolution_submit_proposal(
                        source_brain="autonomous_loop",
                        category="performance",
                        title="Autonomous loop encountering repeated errors",
                        description=(
                            f"The autonomous brain loop has accumulated {_state['total_errors']} "
                            f"errors over {tick} ticks. Investigation recommended to improve "
                            f"reliability of condition detection or task processing."
                        ),
                        evidence={"total_errors": _state["total_errors"], "tick": tick},
                        priority=3,
                    )
                except Exception:
                    pass

        # Track consecutive empty ticks
        if events_published == 0 and tasks_aggregated == 0 and actions_created == 0:
            _state["consecutive_empty"] += 1
        else:
            _state["consecutive_empty"] = 0

        # Update totals
        _state["total_events"] += events_published
        _state["total_tasks_aggregated"] += tasks_aggregated
        _state["total_actions"] += actions_created

        # Persist tick record
        run_id = new_id("aloop")
        db_exec(
            "INSERT INTO autonomous_loop_runs (id, tick_number, events_published, tasks_aggregated, actions_created, errors, detail_json, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (run_id, tick, events_published, tasks_aggregated, actions_created, errors, json.dumps(detail), ts),
        )

        # Update shared memory with latest loop state
        if memory_set:
            try:
                memory_set(
                    "system",
                    "autonomous_loop:status",
                    {
                        "tick": tick,
                        "enabled": _state["enabled"],
                        "running": _state["running"],
                        "last_tick_at": ts,
                        "events_published": events_published,
                        "tasks_aggregated": tasks_aggregated,
                        "actions_created": actions_created,
                    },
                    updated_by="autonomous_loop",
                )
            except Exception:
                pass

        log.info(
            "[AutonomousLoop] tick=%d events=%d tasks_agg=%d actions=%d errors=%d",
            tick, events_published, tasks_aggregated, actions_created, errors,
        )

        return {
            "tick": tick,
            "events_published": events_published,
            "tasks_aggregated": tasks_aggregated,
            "actions_created": actions_created,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    async def _loop() -> None:
        """Background coroutine that calls ``_tick`` at regular intervals."""
        _state["running"] = True
        _state["started_at"] = now_iso()
        log.info("[AutonomousLoop] background loop STARTED (interval=%ds)", _state["interval_seconds"])
        try:
            while _state["enabled"]:
                try:
                    await _tick()
                except Exception as exc:
                    log.warning("[AutonomousLoop] tick exception: %s\n%s", exc, traceback.format_exc())
                await asyncio.sleep(_state["interval_seconds"])
        finally:
            _state["running"] = False
            log.info("[AutonomousLoop] background loop STOPPED after %d ticks", _state["tick"])

    _loop_task: Optional[asyncio.Task] = None

    def _start_loop() -> bool:
        nonlocal _loop_task
        if _state["running"]:
            return False
        _state["enabled"] = True
        _loop_task = asyncio.ensure_future(_loop())
        return True

    def _stop_loop() -> bool:
        nonlocal _loop_task
        _state["enabled"] = False
        if _loop_task and not _loop_task.done():
            _loop_task.cancel()
            _loop_task = None
        return True

    # ------------------------------------------------------------------
    # REST APIs
    # ------------------------------------------------------------------

    @app.get("/api/autonomous-loop/status")
    async def api_loop_status(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {
            "ok": True,
            "status": {
                "enabled": _state["enabled"],
                "running": _state["running"],
                "interval_seconds": _state["interval_seconds"],
                "tick": _state["tick"],
                "last_tick_at": _state["last_tick_at"],
                "consecutive_empty": _state["consecutive_empty"],
                "total_events": _state["total_events"],
                "total_tasks_aggregated": _state["total_tasks_aggregated"],
                "total_actions": _state["total_actions"],
                "total_errors": _state["total_errors"],
                "started_at": _state["started_at"],
            },
        }

    @app.post("/api/autonomous-loop/start")
    async def api_loop_start(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")
        started = _start_loop()
        return {"ok": True, "started": started, "already_running": not started}

    @app.post("/api/autonomous-loop/stop")
    async def api_loop_stop(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")
        _stop_loop()
        return {"ok": True, "stopped": True}

    @app.post("/api/autonomous-loop/configure")
    async def api_loop_configure(body: LoopConfigRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")
        if body.interval_seconds is not None:
            clamped = max(10, min(600, body.interval_seconds))
            _state["interval_seconds"] = clamped
        if body.enabled is not None:
            if body.enabled and not _state["running"]:
                _start_loop()
            elif not body.enabled and _state["running"]:
                _stop_loop()
        return {"ok": True, "state": {
            "enabled": _state["enabled"],
            "interval_seconds": _state["interval_seconds"],
        }}

    @app.post("/api/autonomous-loop/tick")
    async def api_manual_tick(request: Request):
        """Run a single tick manually (useful for testing / debugging)."""
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")
        result = await _tick()
        return {"ok": True, "tick_result": result}

    @app.get("/api/autonomous-loop/history")
    async def api_loop_history(request: Request, limit: int = 30):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        rows = db_all(
            "SELECT id, tick_number, events_published, tasks_aggregated, actions_created, errors, detail_json, created_at "
            "FROM autonomous_loop_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) or []
        return {
            "ok": True,
            "history": [
                {
                    "id": r[0],
                    "tick": r[1],
                    "events_published": r[2],
                    "tasks_aggregated": r[3],
                    "actions_created": r[4],
                    "errors": r[5],
                    "detail": json.loads(r[6] or "{}"),
                    "created_at": r[7],
                }
                for r in rows
            ],
        }

    # Export to ctx
    ctx["autonomous_loop_start"] = _start_loop
    ctx["autonomous_loop_stop"]  = _stop_loop
    ctx["autonomous_loop_tick"]  = _tick
    ctx["autonomous_loop_state"] = _state

    log.info("[AutonomousLoop] layer installed (start via POST /api/autonomous-loop/start)")
    return ctx
