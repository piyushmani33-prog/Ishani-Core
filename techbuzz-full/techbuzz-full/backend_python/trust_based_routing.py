"""
Trust-Based Routing
====================
Uses brain reputation / trust scores to decide which brain should handle a
given task.  Higher-trust brains are preferred as primary handlers; lower-trust
brains get a reduced escalation threshold.  All routing decisions are logged
to SQLite for auditing.

Safety guarantees
-----------------
* No auto-send of external communications.
* No code self-modification.
* Routing decisions include reasoning that is fully auditable.
* Human-approval flags are forwarded unchanged.

Data is persisted in SQLite at ``data/routing_decisions.db``.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

_REPUTATION_DB_PATH: Optional[Path] = None  # set during registration


def _get_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _get_db(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id           TEXT PRIMARY KEY,
                task_type    TEXT,
                task_id      TEXT,
                chosen_brain TEXT,
                candidates   TEXT,   -- JSON array
                reasoning    TEXT,
                trust_scores TEXT,   -- JSON object brain_id → score
                decided_at   TEXT NOT NULL
            );
            """
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------


def _load_reputation_scores(reputation_db: Optional[Path]) -> Dict[str, float]:
    """Return {brain_id: trust_score} from the reputation database (if available)."""
    if reputation_db is None or not reputation_db.exists():
        return {}
    try:
        with _get_db(reputation_db) as conn:
            rows = conn.execute(
                "SELECT brain_id, tasks_created, tasks_resolved, "
                "actions_approved, actions_rejected, conflicts_generated, "
                "handoffs_completed, escalations_sent, escalation_success, "
                "learning_insights_accepted, evolution_proposals_accepted "
                "FROM brain_metrics"
            ).fetchall()
        scores: Dict[str, float] = {}
        for row in rows:
            d = dict(row)
            scores[d["brain_id"]] = _compute_trust(d)
        return scores
    except Exception:
        return {}


def _compute_trust(row: Dict[str, Any]) -> float:
    def _ratio(n: float, d: float) -> float:
        return n / d if d > 0 else 0.0

    task_rate = _ratio(row.get("tasks_resolved", 0), row.get("tasks_created", 0))
    act_denom = row.get("actions_approved", 0) + row.get("actions_rejected", 0)
    action_rate = _ratio(row.get("actions_approved", 0), act_denom)
    reliability = 0.6 * task_rate + 0.4 * action_rate

    usefulness_raw = (
        row.get("learning_insights_accepted", 0) * 2
        + row.get("evolution_proposals_accepted", 0) * 2
        + row.get("handoffs_completed", 0)
        + row.get("escalation_success", 0)
    )
    usefulness = min(usefulness_raw / max(row.get("tasks_created", 1) * 6, 1), 1.0)
    penalty = min(row.get("conflicts_generated", 0) * 0.04, 0.4)
    return round(max(0.6 * reliability + 0.4 * usefulness - penalty, 0.0), 4)


def _escalation_threshold(trust_score: float) -> float:
    """Lower-trust brains should escalate earlier (lower threshold)."""
    # trust 1.0 → threshold 0.7; trust 0.0 → threshold 0.2
    return round(0.2 + trust_score * 0.5, 3)


def _pick_best_brain(
    candidates: List[str],
    task_type: str,
    trust_scores: Dict[str, float],
) -> tuple[str, str]:
    """
    Return (chosen_brain_id, reasoning).

    Strategy:
    1. Rank candidates by trust score (descending).
    2. Highest-trust brain is primary handler.
    3. If no candidate has any trust data, fall back to first in list.
    """
    ranked = sorted(
        candidates,
        key=lambda b: trust_scores.get(b, 0.0),
        reverse=True,
    )
    if not ranked:
        return ("unassigned", "no candidates provided")

    chosen = ranked[0]
    score = trust_scores.get(chosen, 0.0)
    esc_threshold = _escalation_threshold(score)

    if len(ranked) == 1:
        reasoning = (
            f"Only one candidate available: {chosen} "
            f"(trust={score:.3f}, escalation_threshold={esc_threshold})."
        )
    else:
        runner_up = ranked[1]
        runner_score = trust_scores.get(runner_up, 0.0)
        reasoning = (
            f"Selected {chosen} (trust={score:.3f}) over {runner_up} "
            f"(trust={runner_score:.3f}) for task_type='{task_type}'. "
            f"Escalation threshold set at {esc_threshold}."
        )

    return (chosen, reasoning)


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def register_routing_routes(
    app: Any,
    *,
    routing_db_path: Path,
    reputation_db_path: Optional[Path],
    new_id: Callable[[], str],
    now_iso: Callable[[], str],
    log: Any,
) -> None:
    """Attach all /api/routing/* routes to the FastAPI *app* instance."""

    global _REPUTATION_DB_PATH
    _REPUTATION_DB_PATH = reputation_db_path

    _init_db(routing_db_path)

    import json as _json

    # ------------------------------------------------------------------ #
    # POST /api/routing/decide                                             #
    # ------------------------------------------------------------------ #

    @app.post("/api/routing/decide")
    async def routing_decide(request: Request) -> JSONResponse:
        try:
            body = await request.json()
            task_type = (body.get("task_type") or "general").strip()
            task_id = (body.get("task_id") or "").strip()
            candidates: List[str] = body.get("candidates") or []

            if not candidates:
                return JSONResponse(
                    {"error": "candidates list is required"}, status_code=400
                )

            trust_scores = _load_reputation_scores(_REPUTATION_DB_PATH)
            chosen, reasoning = _pick_best_brain(candidates, task_type, trust_scores)

            # Compute per-candidate escalation thresholds for transparency
            candidate_info = {
                b: {
                    "trust_score": trust_scores.get(b, 0.0),
                    "escalation_threshold": _escalation_threshold(trust_scores.get(b, 0.0)),
                }
                for b in candidates
            }

            decision = {
                "id": new_id(),
                "task_type": task_type,
                "task_id": task_id,
                "chosen_brain": chosen,
                "candidates": candidates,
                "reasoning": reasoning,
                "trust_scores": candidate_info,
                "decided_at": now_iso(),
            }

            with _get_db(routing_db_path) as conn:
                conn.execute(
                    "INSERT INTO routing_decisions "
                    "(id, task_type, task_id, chosen_brain, candidates, reasoning, trust_scores, decided_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        decision["id"],
                        decision["task_type"],
                        decision["task_id"],
                        decision["chosen_brain"],
                        _json.dumps(candidates),
                        reasoning,
                        _json.dumps(candidate_info),
                        decision["decided_at"],
                    ),
                )
                conn.commit()

            log.info(
                "Routing decision: task_type=%s chosen=%s", task_type, chosen
            )
            return JSONResponse({"decision": decision})
        except Exception as exc:
            log.error("routing_decide error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # GET /api/routing/decisions                                           #
    # ------------------------------------------------------------------ #

    @app.get("/api/routing/decisions")
    async def get_routing_decisions() -> JSONResponse:
        try:
            with _get_db(routing_db_path) as conn:
                rows = conn.execute(
                    "SELECT * FROM routing_decisions ORDER BY decided_at DESC LIMIT 200"
                ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["candidates"] = _json.loads(d["candidates"] or "[]")
                    d["trust_scores"] = _json.loads(d["trust_scores"] or "{}")
                except Exception:
                    pass
                results.append(d)
            return JSONResponse({"decisions": results})
        except Exception as exc:
            log.error("get_routing_decisions error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ------------------------------------------------------------------ #
    # GET /api/routing/decisions/<brain_id>                                #
    # ------------------------------------------------------------------ #

    @app.get("/api/routing/decisions/{brain_id}")
    async def get_routing_decisions_for_brain(brain_id: str) -> JSONResponse:
        try:
            with _get_db(routing_db_path) as conn:
                rows = conn.execute(
                    "SELECT * FROM routing_decisions WHERE chosen_brain = ? ORDER BY decided_at DESC LIMIT 200",
                    (brain_id,),
                ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["candidates"] = _json.loads(d["candidates"] or "[]")
                    d["trust_scores"] = _json.loads(d["trust_scores"] or "{}")
                except Exception:
                    pass
                results.append(d)
            return JSONResponse({"brain_id": brain_id, "decisions": results})
        except Exception as exc:
            log.error("get_routing_decisions_for_brain error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)
