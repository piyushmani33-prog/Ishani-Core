"""
Brain Reputation Engine
=======================
Tracks per-brain performance metrics, computes reliability / usefulness /
trust scores, and exposes them through FastAPI routes.

Data is persisted in SQLite at ``data/brain_reputation.db``.

Safety guarantees
-----------------
* No auto-send of external communications.
* No code self-modification.
* All operations are logged and auditable through the event_log table.
* Human-approval flags are preserved; this module only reads / writes metrics.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_EVENTS = {
    "task_created",
    "task_resolved",
    "action_approved",
    "action_rejected",
    "conflict_generated",
    "handoff_sent",
    "handoff_completed",
    "escalation_sent",
    "escalation_success",
    "learning_insight_accepted",
    "evolution_proposal_accepted",
}

_WEAK_TRUST_THRESHOLD = 0.35  # brains below this are flagged as "weak"

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
            CREATE TABLE IF NOT EXISTS brain_metrics (
                brain_id                    TEXT PRIMARY KEY,
                tasks_created               INTEGER DEFAULT 0,
                tasks_resolved              INTEGER DEFAULT 0,
                actions_approved            INTEGER DEFAULT 0,
                actions_rejected            INTEGER DEFAULT 0,
                conflicts_generated         INTEGER DEFAULT 0,
                handoffs_sent               INTEGER DEFAULT 0,
                handoffs_completed          INTEGER DEFAULT 0,
                escalations_sent            INTEGER DEFAULT 0,
                escalation_success          INTEGER DEFAULT 0,
                learning_insights_accepted  INTEGER DEFAULT 0,
                evolution_proposals_accepted INTEGER DEFAULT 0,
                updated_at                  TEXT
            );

            CREATE TABLE IF NOT EXISTS reputation_event_log (
                id          TEXT    PRIMARY KEY,
                brain_id    TEXT    NOT NULL,
                event_type  TEXT    NOT NULL,
                recorded_at TEXT    NOT NULL
            );
            """
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def _compute_scores(row: Dict[str, Any]) -> Dict[str, float]:
    tasks_created = row.get("tasks_created", 0)
    tasks_resolved = row.get("tasks_resolved", 0)
    actions_approved = row.get("actions_approved", 0)
    actions_rejected = row.get("actions_rejected", 0)
    conflicts_generated = row.get("conflicts_generated", 0)
    handoffs_completed = row.get("handoffs_completed", 0)
    learning_insights = row.get("learning_insights_accepted", 0)
    evolution_proposals = row.get("evolution_proposals_accepted", 0)
    escalation_success = row.get("escalation_success", 0)
    escalations_sent = row.get("escalations_sent", 0)

    # reliability: task resolution rate (60%) + action approval rate (40%)
    task_rate = _safe_ratio(tasks_resolved, tasks_created)
    action_denom = actions_approved + actions_rejected
    action_rate = _safe_ratio(actions_approved, action_denom)
    reliability_score = round(0.6 * task_rate + 0.4 * action_rate, 4)

    # usefulness: learning, evolution, handoff completion, escalation success
    usefulness_raw = (
        learning_insights * 2
        + evolution_proposals * 2
        + handoffs_completed
        + escalation_success
    )
    usefulness_denom = (
        max(tasks_created, 1) * 6  # normalise against tasks as a proxy
    )
    usefulness_score = round(min(usefulness_raw / usefulness_denom, 1.0), 4)

    # conflict penalty: each conflict reduces trust
    conflict_penalty = min(conflicts_generated * 0.04, 0.4)

    trust_score = round(
        max(0.6 * reliability_score + 0.4 * usefulness_score - conflict_penalty, 0.0),
        4,
    )

    return {
        "reliability_score": reliability_score,
        "usefulness_score": usefulness_score,
        "trust_score": trust_score,
    }


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class RecordEventRequest(BaseModel):
    event_type: str


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def register_reputation_routes(
    app: Any,
    *,
    db_path: Path,
    new_id: Callable[[], str],
    now_iso: Callable[[], str],
    log: Any,
) -> None:
    """Attach all /api/reputation/* routes to the FastAPI *app* instance."""

    _init_db(db_path)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _ensure_brain(conn: sqlite3.Connection, brain_id: str) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO brain_metrics (brain_id, updated_at) VALUES (?, ?)",
            (brain_id, now_iso()),
        )
        conn.commit()

    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d.update(_compute_scores(d))
        return d

    def _get_all_reputations(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = conn.execute("SELECT * FROM brain_metrics ORDER BY brain_id").fetchall()
        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # GET /api/reputation                                                  #
    # ------------------------------------------------------------------ #

    @app.get("/api/reputation")
    async def get_all_reputations() -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                reputations = _get_all_reputations(conn)
            return JSONResponse({"reputations": reputations})
        except Exception as exc:
            log.error("get_all_reputations error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # GET /api/reputation/leaderboard                                      #
    # ------------------------------------------------------------------ #

    @app.get("/api/reputation/leaderboard")
    async def get_leaderboard() -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                reputations = _get_all_reputations(conn)
            reputations.sort(key=lambda r: r["trust_score"], reverse=True)
            return JSONResponse({"leaderboard": reputations})
        except Exception as exc:
            log.error("get_leaderboard error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # GET /api/reputation/weak-brains                                      #
    # ------------------------------------------------------------------ #

    @app.get("/api/reputation/weak-brains")
    async def get_weak_brains() -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                reputations = _get_all_reputations(conn)
            weak = [r for r in reputations if r["trust_score"] < _WEAK_TRUST_THRESHOLD]
            for r in weak:
                r["recommendation"] = _build_recommendation(r)
            return JSONResponse({"weak_brains": weak, "threshold": _WEAK_TRUST_THRESHOLD})
        except Exception as exc:
            log.error("get_weak_brains error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # GET /api/reputation/<brain_id>                                       #
    # ------------------------------------------------------------------ #

    @app.get("/api/reputation/{brain_id}")
    async def get_reputation(brain_id: str) -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                _ensure_brain(conn, brain_id)
                row = conn.execute(
                    "SELECT * FROM brain_metrics WHERE brain_id = ?", (brain_id,)
                ).fetchone()
            if row is None:
                return JSONResponse({"error": "not found"}, status_code=404)
            return JSONResponse({"reputation": _row_to_dict(row)})
        except Exception as exc:
            log.error("get_reputation error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # POST /api/reputation/<brain_id>/record                               #
    # ------------------------------------------------------------------ #

    @app.post("/api/reputation/{brain_id}/record")
    async def record_event(brain_id: str, request: Request) -> JSONResponse:
        try:
            body = await request.json()
            event_type = (body.get("event_type") or "").strip()
            if event_type not in _VALID_EVENTS:
                return JSONResponse(
                    {"error": f"Unknown event_type '{event_type}'. Valid: {sorted(_VALID_EVENTS)}"},
                    status_code=400,
                )

            # Map event_type to column name
            col_map = {
                "task_created": "tasks_created",
                "task_resolved": "tasks_resolved",
                "action_approved": "actions_approved",
                "action_rejected": "actions_rejected",
                "conflict_generated": "conflicts_generated",
                "handoff_sent": "handoffs_sent",
                "handoff_completed": "handoffs_completed",
                "escalation_sent": "escalations_sent",
                "escalation_success": "escalation_success",
                "learning_insight_accepted": "learning_insights_accepted",
                "evolution_proposal_accepted": "evolution_proposals_accepted",
            }
            col = col_map[event_type]
            # col is validated against col_map keys (all hardcoded column names),
            # so string interpolation here is safe — no user input reaches the SQL.
            _VALID_METRIC_COLS = frozenset(col_map.values())
            if col not in _VALID_METRIC_COLS:
                return JSONResponse({"error": "Invalid metric column"}, status_code=400)

            with _get_db(db_path) as conn:
                _ensure_brain(conn, brain_id)
                conn.execute(
                    f"UPDATE brain_metrics SET {col} = {col} + 1, updated_at = ? WHERE brain_id = ?",
                    (now_iso(), brain_id),
                )
                conn.execute(
                    "INSERT INTO reputation_event_log (id, brain_id, event_type, recorded_at) VALUES (?,?,?,?)",
                    (new_id(), brain_id, event_type, now_iso()),
                )
                conn.commit()

            log.info("Reputation event recorded: brain=%s event=%s", brain_id, event_type)
            return JSONResponse({"ok": True, "brain_id": brain_id, "event_type": event_type})
        except Exception as exc:
            log.error("record_event error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # GET /api/reputation/<brain_id>/history                               #
    # ------------------------------------------------------------------ #

    @app.get("/api/reputation/{brain_id}/history")
    async def get_event_history(brain_id: str) -> JSONResponse:
        try:
            with _get_db(db_path) as conn:
                rows = conn.execute(
                    "SELECT * FROM reputation_event_log WHERE brain_id = ? ORDER BY recorded_at DESC LIMIT 200",
                    (brain_id,),
                ).fetchall()
            return JSONResponse({"history": [dict(r) for r in rows]})
        except Exception as exc:
            log.error("get_event_history error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)


# ---------------------------------------------------------------------------
# Recommendation helper
# ---------------------------------------------------------------------------


def _build_recommendation(rep: Dict[str, Any]) -> str:
    suggestions: List[str] = []
    if rep.get("reliability_score", 0) < 0.3:
        suggestions.append("improve task completion and action approval rates")
    if rep.get("usefulness_score", 0) < 0.2:
        suggestions.append("contribute more learning insights or evolution proposals")
    if rep.get("conflicts_generated", 0) > 5:
        suggestions.append("reduce conflict generation")
    if not suggestions:
        suggestions.append("monitor metrics closely and increase activity")
    return "; ".join(suggestions)
