"""
Brain Self-Scheduling System
=============================
Allows each brain to define recurring jobs with interval, allowed task types,
purpose, and a max-runs-per-hour safety cap.  An autonomous background loop
triggers scheduled work without human intervention while enforcing all safety
guardrails.

Safety guarantees
-----------------
* No auto-send of external communications.
* No code self-modification.
* Duplicate scheduling is prevented (same brain + same task type).
* Runaway loops are capped via max_runs_per_hour and cooldown enforcement.
* All run records are stored and auditable.

Data is persisted in SQLite at ``data/brain_schedules.db``.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _get_db(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS brain_schedules (
                id                TEXT PRIMARY KEY,
                brain_id          TEXT NOT NULL,
                task_type         TEXT NOT NULL,
                interval_seconds  INTEGER NOT NULL DEFAULT 3600,
                purpose           TEXT DEFAULT '',
                max_runs_per_hour INTEGER NOT NULL DEFAULT 4,
                active            INTEGER NOT NULL DEFAULT 1,
                next_run_at       TEXT,
                created_at        TEXT NOT NULL,
                UNIQUE (brain_id, task_type)
            );

            CREATE TABLE IF NOT EXISTS schedule_run_log (
                id           TEXT PRIMARY KEY,
                schedule_id  TEXT NOT NULL,
                brain_id     TEXT NOT NULL,
                task_type    TEXT NOT NULL,
                status       TEXT NOT NULL,   -- success | failure | skipped
                detail       TEXT DEFAULT '',
                ran_at       TEXT NOT NULL
            );
            """
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Scheduler state
# ---------------------------------------------------------------------------

_scheduler_state: Dict[str, Any] = {
    "running": False,
    "thread": None,
    "tick_interval": 30,  # how often the loop checks in seconds
}
_state_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CreateScheduleRequest(BaseModel):
    brain_id: str
    task_type: str
    interval_seconds: int = 3600
    purpose: str = ""
    max_runs_per_hour: int = 4


# ---------------------------------------------------------------------------
# Internal loop helpers
# ---------------------------------------------------------------------------


def _count_runs_last_hour(
    conn: sqlite3.Connection, schedule_id: str
) -> int:
    from datetime import timedelta
    one_hour_ago = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    rows = conn.execute(
        "SELECT COUNT(*) FROM schedule_run_log WHERE schedule_id = ? AND ran_at >= ?",
        (schedule_id, one_hour_ago),
    ).fetchone()
    return rows[0] if rows else 0


def _tick(db_path: Path, new_id: Callable, now_iso: Callable, log: Any) -> None:
    """One tick of the scheduler: fire any due schedules that respect safety caps."""
    now = datetime.now(UTC).isoformat()
    try:
        with _get_db(db_path) as conn:
            due = conn.execute(
                "SELECT * FROM brain_schedules WHERE active = 1 AND (next_run_at IS NULL OR next_run_at <= ?)",
                (now,),
            ).fetchall()

            for sched in due:
                sid = sched["id"]
                brain_id = sched["brain_id"]
                task_type = sched["task_type"]
                interval = sched["interval_seconds"]
                max_per_hour = sched["max_runs_per_hour"]

                # Safety cap: check runs in the last hour
                runs_this_hour = _count_runs_last_hour(conn, sid)
                if runs_this_hour >= max_per_hour:
                    log.info(
                        "Scheduler: skipping %s/%s — cap reached (%d/%d per hour)",
                        brain_id,
                        task_type,
                        runs_this_hour,
                        max_per_hour,
                    )
                    # Still advance next_run_at so we don't spin tight
                    next_run = _add_seconds(now, interval)
                    conn.execute(
                        "UPDATE brain_schedules SET next_run_at = ? WHERE id = ?",
                        (next_run, sid),
                    )
                    conn.execute(
                        "INSERT INTO schedule_run_log (id, schedule_id, brain_id, task_type, status, detail, ran_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (new_id(), sid, brain_id, task_type, "skipped", "hourly cap reached", now_iso()),
                    )
                    conn.commit()
                    continue

                # Execute the scheduled work (autonomous, safe stub)
                status = "success"
                detail = f"auto-triggered {task_type} for {brain_id}"
                try:
                    _execute_scheduled_work(brain_id, task_type, log)
                except Exception as exc:
                    status = "failure"
                    detail = str(exc)
                    log.warning("Scheduled work failed: %s", exc)

                next_run = _add_seconds(now, interval)
                conn.execute(
                    "UPDATE brain_schedules SET next_run_at = ? WHERE id = ?",
                    (next_run, sid),
                )
                conn.execute(
                    "INSERT INTO schedule_run_log (id, schedule_id, brain_id, task_type, status, detail, ran_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (new_id(), sid, brain_id, task_type, status, detail, now_iso()),
                )
                conn.commit()
                log.info(
                    "Scheduler tick: brain=%s task=%s status=%s", brain_id, task_type, status
                )
    except Exception as exc:
        log.error("Scheduler tick error: %s", exc)


def _add_seconds(iso_ts: str, seconds: int) -> str:
    """Add *seconds* to an ISO-format timestamp string and return the result."""
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    from datetime import timedelta
    return (dt + timedelta(seconds=seconds)).isoformat()


def _execute_scheduled_work(brain_id: str, task_type: str, log: Any) -> None:
    """
    Stub for autonomous brain work.

    Safety: this only logs the intent.  No external communications are sent,
    no code is modified.  Real implementations should call the task system
    via the internal coordination context after validating contract permissions.
    """
    log.info(
        "SCHEDULED WORK: brain=%s task_type=%s  [stub — extend with real task dispatch]",
        brain_id,
        task_type,
    )


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def register_scheduling_routes(
    app: Any,
    *,
    db_path: Path,
    new_id: Callable[[], str],
    now_iso: Callable[[], str],
    log: Any,
) -> None:
    """Attach all /api/schedules/* routes to the FastAPI *app* instance."""

    _init_db(db_path)

    # ------------------------------------------------------------------ #
    # GET /api/schedules                                                   #
    # ------------------------------------------------------------------ #

    @app.get("/api/schedules")
    async def list_schedules() -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                rows = conn.execute(
                    "SELECT * FROM brain_schedules ORDER BY brain_id, task_type"
                ).fetchall()
            return JSONResponse({"schedules": [dict(r) for r in rows]})
        except Exception as exc:
            log.error("list_schedules error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # POST /api/schedules                                                  #
    # ------------------------------------------------------------------ #

    @app.post("/api/schedules")
    async def create_schedule(request: Request) -> JSONResponse:
        try:
            body = await request.json()
            brain_id = (body.get("brain_id") or "").strip()
            task_type = (body.get("task_type") or "").strip()
            interval_seconds = int(body.get("interval_seconds") or 3600)
            purpose = (body.get("purpose") or "").strip()
            max_runs_per_hour = int(body.get("max_runs_per_hour") or 4)

            if not brain_id or not task_type:
                return JSONResponse(
                    {"error": "brain_id and task_type are required"}, status_code=400
                )
            if interval_seconds < 60:
                return JSONResponse(
                    {"error": "interval_seconds must be at least 60"}, status_code=400
                )
            if max_runs_per_hour < 1 or max_runs_per_hour > 60:
                return JSONResponse(
                    {"error": "max_runs_per_hour must be between 1 and 60"}, status_code=400
                )

            sid = new_id()
            ts = now_iso()
            with _get_db(db_path) as conn:
                try:
                    conn.execute(
                        "INSERT INTO brain_schedules "
                        "(id, brain_id, task_type, interval_seconds, purpose, max_runs_per_hour, active, next_run_at, created_at) "
                        "VALUES (?,?,?,?,?,?,1,?,?)",
                        (sid, brain_id, task_type, interval_seconds, purpose, max_runs_per_hour, ts, ts),
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    return JSONResponse(
                        {"error": f"Schedule for brain '{brain_id}' + task '{task_type}' already exists"},
                        status_code=409,
                    )

            log.info("Schedule created: id=%s brain=%s task=%s", sid, brain_id, task_type)
            return JSONResponse(
                {"ok": True, "id": sid, "brain_id": brain_id, "task_type": task_type},
                status_code=201,
            )
        except Exception as exc:
            log.error("create_schedule error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # DELETE /api/schedules/<schedule_id>                                  #
    # ------------------------------------------------------------------ #

    @app.delete("/api/schedules/{schedule_id}")
    async def delete_schedule(schedule_id: str) -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                result = conn.execute(
                    "DELETE FROM brain_schedules WHERE id = ?", (schedule_id,)
                )
                conn.commit()
            if result.rowcount == 0:
                return JSONResponse({"error": "schedule not found"}, status_code=404)
            log.info("Schedule deleted: id=%s", schedule_id)
            return JSONResponse({"ok": True})
        except Exception as exc:
            log.error("delete_schedule error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # GET /api/schedules/<brain_id>/runs                                   #
    # ------------------------------------------------------------------ #

    @app.get("/api/schedules/{brain_id}/runs")
    async def get_brain_runs(brain_id: str) -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                rows = conn.execute(
                    "SELECT * FROM schedule_run_log WHERE brain_id = ? ORDER BY ran_at DESC LIMIT 200",
                    (brain_id,),
                ).fetchall()
            return JSONResponse({"runs": [dict(r) for r in rows]})
        except Exception as exc:
            log.error("get_brain_runs error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # POST /api/schedules/start                                            #
    # ------------------------------------------------------------------ #

    @app.post("/api/schedules/start")
    async def start_scheduler() -> JSONResponse:
        with _state_lock:
            if _scheduler_state["running"]:
                return JSONResponse({"ok": True, "status": "already_running"})

            def _loop() -> None:
                while _scheduler_state["running"]:
                    _tick(db_path, new_id, now_iso, log)
                    time.sleep(_scheduler_state["tick_interval"])

            _scheduler_state["running"] = True
            t = threading.Thread(target=_loop, daemon=True, name="brain-scheduler")
            _scheduler_state["thread"] = t
            t.start()

        log.info("Brain scheduler started")
        return JSONResponse({"ok": True, "status": "started"})

    # ------------------------------------------------------------------ #
    # POST /api/schedules/stop                                             #
    # ------------------------------------------------------------------ #

    @app.post("/api/schedules/stop")
    async def stop_scheduler() -> JSONResponse:
        with _state_lock:
            if not _scheduler_state["running"]:
                return JSONResponse({"ok": True, "status": "already_stopped"})
            _scheduler_state["running"] = False

        log.info("Brain scheduler stopped")
        return JSONResponse({"ok": True, "status": "stopped"})

    # ------------------------------------------------------------------ #
    # GET /api/schedules/status                                            #
    # ------------------------------------------------------------------ #

    @app.get("/api/schedules/status")
    async def scheduler_status() -> JSONResponse:
        return JSONResponse(
            {
                "running": _scheduler_state["running"],
                "tick_interval_seconds": _scheduler_state["tick_interval"],
            }
        )
