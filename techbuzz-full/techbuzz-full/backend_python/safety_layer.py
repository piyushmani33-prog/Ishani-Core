"""
Safety Layer — Prevents duplicate actions, conflicting outputs, and enforces
human-approval flow.

Deduplication uses a content hash of (action_type + target + content_json).
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

# Default deduplication window in seconds (1 hour)
_DEDUP_WINDOW_SECONDS = 3600


class SafetyOverrideRequest(BaseModel):
    reason: str = ""


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_safety_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
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
            CREATE TABLE IF NOT EXISTS safety_log (
                id          TEXT PRIMARY KEY,
                action_id   TEXT NOT NULL,
                check_type  TEXT NOT NULL,
                result      TEXT NOT NULL DEFAULT 'passed',
                reason      TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS safety_blocks (
                id          TEXT PRIMARY KEY,
                action_id   TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                reason      TEXT,
                overridden  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _content_hash(action_type: str, target: str, content_json: str) -> str:
        raw = f"{action_type}|{target}|{content_json}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _log_check(action_id: str, check_type: str, result: str, reason: str = "") -> None:
        db_exec(
            "INSERT INTO safety_log (id, action_id, check_type, result, reason, created_at) VALUES (?,?,?,?,?,?)",
            (new_id("safe"), action_id, check_type, result, reason, now_iso()),
        )

    def check_duplicate(action_id: str, action_type: str, target: str, content_json: str, window_seconds: int = _DEDUP_WINDOW_SECONDS) -> Dict[str, Any]:
        """Check if an identical action was executed recently.

        Deduplication key = SHA-256(action_type | target | content_json).
        The *target* argument should identify the entity the action targets
        (e.g. candidate_id, row_id).  Pass an empty string if not applicable.

        Returns {"passed": True} or {"passed": False, "reason": "..."}
        """
        content_hash = _content_hash(action_type, target, content_json)
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()

        # Compare against recently executed actions using the same hash
        rows = db_all(
            "SELECT id FROM safety_blocks WHERE content_hash=? AND overridden=0 AND created_at >= ?",
            (content_hash, cutoff),
        )
        if rows:
            reason = f"Duplicate of recently blocked/executed action (hash={content_hash[:12]}…) within {window_seconds}s window"
            _log_check(action_id, "duplicate", "blocked", reason)
            db_exec(
                "INSERT OR IGNORE INTO safety_blocks (id, action_id, content_hash, reason, overridden, created_at) VALUES (?,?,?,?,0,?)",
                (new_id("blk"), action_id, content_hash, reason, now_iso()),
            )
            return {"passed": False, "reason": reason, "content_hash": content_hash}

        _log_check(action_id, "duplicate", "passed")
        return {"passed": True, "content_hash": content_hash}

    def check_approval(action_id: str) -> Dict[str, Any]:
        """Verify that the action has been explicitly approved (status != draft)."""
        rows = db_all("SELECT id, status FROM action_drafts WHERE id=?", (action_id,))
        if not rows:
            return {"passed": False, "reason": "Action not found"}
        status = rows[0][1]
        if status not in ("approved", "executed"):
            reason = f"Action {action_id} has not been approved (status={status})"
            _log_check(action_id, "approval", "blocked", reason)
            return {"passed": False, "reason": reason}
        _log_check(action_id, "approval", "passed")
        return {"passed": True}

    def run_all_checks(action_id: str, action_type: str = "", target: str = "", content_json: str = "{}") -> Dict[str, Any]:
        """Run all safety checks for an action. Returns first failure or overall pass."""
        dedup = check_duplicate(action_id, action_type, target, content_json)
        if not dedup["passed"]:
            return {"safe": False, "check": "duplicate", "reason": dedup["reason"]}
        approval = check_approval(action_id)
        if not approval["passed"]:
            return {"safe": False, "check": "approval", "reason": approval["reason"]}
        return {"safe": True}

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.get("/api/safety/log")
    async def api_safety_log(request: Request, limit: int = 50):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all(
            "SELECT id, action_id, check_type, result, reason, created_at FROM safety_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return {
            "ok": True,
            "log": [
                {"id": r[0], "action_id": r[1], "check_type": r[2], "result": r[3], "reason": r[4], "created_at": r[5]}
                for r in rows
            ],
        }

    @app.get("/api/safety/blocked")
    async def api_safety_blocked(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all(
            "SELECT id, action_id, content_hash, reason, overridden, created_at FROM safety_blocks WHERE overridden=0 ORDER BY created_at DESC",
        )
        return {
            "ok": True,
            "blocked": [
                {"id": r[0], "action_id": r[1], "content_hash": r[2], "reason": r[3], "overridden": bool(r[4]), "created_at": r[5]}
                for r in rows
            ],
        }

    @app.post("/api/safety/override/{action_id}")
    async def api_safety_override(action_id: str, body: SafetyOverrideRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")

        db_exec("UPDATE safety_blocks SET overridden=1 WHERE action_id=?", (action_id,))
        reason = body.reason or "Master override"
        _log_check(action_id, "override", "passed", reason)
        return {"ok": True, "action_id": action_id, "overridden": True, "reason": reason}

    # Export to ctx
    ctx["safety_check_duplicate"] = check_duplicate
    ctx["safety_check_approval"] = check_approval
    ctx["safety_run_all_checks"] = run_all_checks

    log.info("[SafetyLayer] layer installed")
    return ctx
