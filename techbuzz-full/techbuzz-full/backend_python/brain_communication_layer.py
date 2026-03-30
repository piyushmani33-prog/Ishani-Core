import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request
from pydantic import BaseModel

VALID_MESSAGE_TYPES = {
    "request_help",
    "handoff_task",
    "escalate",
    "attach_evidence",
    "request_decision",
    "return_result",
    "broadcast_signal",
}

VALID_PRIORITIES = {"low", "normal", "high", "critical"}

# Numeric layer order for contract checks (lower number = higher in hierarchy)
_KIND_LAYER: Dict[str, int] = {
    "mother": 0,
    "executive": 1,
    "secretary": 2,
    "tool": 3,
    "domain": 4,
    "machine": 5,
    "atom": 6,
}


class SendMessageRequest(BaseModel):
    from_brain: str
    to_brain: str
    message_type: str
    task_id: str = ""
    payload: Optional[Any] = None
    priority: str = "normal"


class ResolveMessageRequest(BaseModel):
    message_id: str
    resolved_by: str
    response_payload: Optional[Any] = None


class BroadcastSignalRequest(BaseModel):
    from_brain: str
    signal_type: str
    payload: Optional[Any] = None


_INTERNAL_FIELDS = {"resolved_by", "response_payload"}


def sanitize_message_for_display(message: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal-only fields and return a safe-to-display message dict."""
    safe = {k: v for k, v in message.items() if k not in _INTERNAL_FIELDS}
    # Respect disclosure_level in payload
    payload = safe.get("payload", {})
    if isinstance(payload, dict) and payload.get("disclosure_level") == "internal":
        safe["payload"] = {"disclosure_level": "internal", "content": "[REDACTED]"}
    return safe


def install_brain_communication_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    db_one = ctx.get("db_one")
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    find_brain = ctx["find_brain"]
    brain_hierarchy_payload = ctx["brain_hierarchy_payload"]
    log = ctx["log"]

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_messages(
                id TEXT PRIMARY KEY,
                from_brain TEXT NOT NULL,
                to_brain TEXT NOT NULL,
                message_type TEXT NOT NULL,
                task_id TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL DEFAULT '{}',
                priority TEXT NOT NULL DEFAULT 'normal',
                status TEXT NOT NULL DEFAULT 'pending',
                response_payload TEXT NOT NULL DEFAULT '{}',
                resolved_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                resolved_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_message_violations(
                id TEXT PRIMARY KEY,
                from_brain TEXT NOT NULL,
                to_brain TEXT NOT NULL,
                message_type TEXT NOT NULL,
                violation_reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    def _brain_layer(brain: Dict[str, Any]) -> int:
        return _KIND_LAYER.get(brain.get("kind") or brain.get("layer") or "", 6)

    def _safe_json(value: Any) -> str:
        if value is None:
            return "{}"
        if isinstance(value, str):
            try:
                json.loads(value)
                return value
            except Exception:
                return json.dumps({"raw": value})
        return json.dumps(value)

    def _parse_payload(raw: str) -> Any:
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}

    def _enrich_messages(rows: List[Dict[str, Any]], brains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        brain_map: Dict[str, Dict[str, Any]] = {b["id"]: b for b in brains}
        result = []
        for row in rows:
            entry = dict(row)
            fb = brain_map.get(entry["from_brain"], {})
            tb = brain_map.get(entry["to_brain"], {})
            entry["from_brain_name"] = fb.get("name", entry["from_brain"])
            entry["to_brain_name"] = tb.get("name", entry["to_brain"])
            entry["payload"] = _parse_payload(entry.get("payload", "{}"))
            entry["response_payload"] = _parse_payload(entry.get("response_payload", "{}"))
            result.append(entry)
        return result

    def _log_violation(from_brain: str, to_brain: str, message_type: str, reason: str) -> None:
        db_exec(
            """
            INSERT INTO brain_message_violations(id, from_brain, to_brain, message_type, violation_reason, created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (new_id(), from_brain, to_brain, message_type, reason, now_iso()),
        )
        log.warning("Brain message contract violation: %s -> %s [%s]: %s", from_brain, to_brain, message_type, reason)

    def _check_contract(from_brain_obj: Dict[str, Any], to_brain_obj: Dict[str, Any], message_type: str) -> Optional[str]:
        """Return a violation reason string if the message violates contract rules, else None."""
        from_layer = _brain_layer(from_brain_obj)
        to_layer = _brain_layer(to_brain_obj)

        if message_type == "escalate":
            # Escalation must go UP the hierarchy (to a brain with a lower layer number)
            if to_layer >= from_layer:
                return f"Escalation must go up the hierarchy (from layer {from_layer} to a lower layer number, but target is layer {to_layer})"

        elif message_type == "handoff_task":
            # Handoffs go DOWN or LATERAL
            if to_layer < from_layer:
                return f"Handoff must go down or lateral in hierarchy (from layer {from_layer}, but target is layer {to_layer})"

        elif message_type in ("request_help", "request_decision", "return_result", "attach_evidence"):
            # Must be within 2 layers
            if abs(from_layer - to_layer) > 2:
                return f"Message type '{message_type}' must be within 2 hierarchy layers (distance is {abs(from_layer - to_layer)})"

        elif message_type == "broadcast_signal":
            # Only layer 0 (mother) or layer 1 (executive) can broadcast
            if from_layer > 1:
                return f"Broadcast signals can only be sent by layer 0 (mother) or layer 1 (executive) brains (sender is layer {from_layer})"

        return None

    @app.post("/api/brain/message/send")
    async def send_brain_message(body: SendMessageRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if body.message_type not in VALID_MESSAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid message_type. Must be one of: {', '.join(sorted(VALID_MESSAGE_TYPES))}",
            )

        priority = body.priority if body.priority in VALID_PRIORITIES else "normal"

        from_brain_obj = find_brain(body.from_brain)
        if not from_brain_obj:
            raise HTTPException(status_code=404, detail=f"Sender brain '{body.from_brain}' not found")

        to_brain_obj = find_brain(body.to_brain)
        if not to_brain_obj:
            raise HTTPException(status_code=404, detail=f"Receiver brain '{body.to_brain}' not found")

        violation_reason = _check_contract(from_brain_obj, to_brain_obj, body.message_type)
        if violation_reason:
            _log_violation(body.from_brain, body.to_brain, body.message_type, violation_reason)
            raise HTTPException(status_code=422, detail=f"Contract violation: {violation_reason}")

        msg_id = new_id()
        created = now_iso()
        payload_str = _safe_json(body.payload)

        db_exec(
            """
            INSERT INTO brain_messages(id, from_brain, to_brain, message_type, task_id, payload, priority, status, response_payload, resolved_by, created_at, resolved_at)
            VALUES(?,?,?,?,?,?,?,'pending','{}','',?,'' )
            """,
            (msg_id, body.from_brain, body.to_brain, body.message_type, body.task_id or "", payload_str, priority, created),
        )

        rows = db_all("SELECT * FROM brain_messages WHERE id=? LIMIT 1", (msg_id,)) or []
        msg = rows[0] if rows else {}
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        enriched = _enrich_messages([msg], brains)
        return {"ok": True, "message": enriched[0] if enriched else msg}

    @app.post("/api/brain/message/resolve")
    async def resolve_brain_message(body: ResolveMessageRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        rows = db_all("SELECT * FROM brain_messages WHERE id=? LIMIT 1", (body.message_id,)) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Message not found")

        response_str = _safe_json(body.response_payload)
        resolved = now_iso()

        db_exec(
            """
            UPDATE brain_messages SET status='resolved', resolved_by=?, response_payload=?, resolved_at=? WHERE id=?
            """,
            (body.resolved_by, response_str, resolved, body.message_id),
        )

        rows = db_all("SELECT * FROM brain_messages WHERE id=? LIMIT 1", (body.message_id,)) or []
        msg = rows[0] if rows else {}
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        enriched = _enrich_messages([msg], brains)
        return {"ok": True, "message": enriched[0] if enriched else msg}

    @app.get("/api/brain/messages")
    async def list_brain_messages(
        request: Request,
        status: Optional[str] = Query(None),
        brain_id: Optional[str] = Query(None),
        message_type: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=200),
    ):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        clauses = []
        params: List[Any] = []

        if status:
            clauses.append("status=?")
            params.append(status)
        if brain_id:
            clauses.append("(from_brain=? OR to_brain=?)")
            params.extend([brain_id, brain_id])
        if message_type:
            clauses.append("message_type=?")
            params.append(message_type)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        rows = (
            db_all(
                f"SELECT * FROM brain_messages {where} ORDER BY created_at DESC LIMIT ?",
                tuple(params),
            )
            or []
        )

        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        return {"messages": _enrich_messages(rows, brains), "total": len(rows)}

    @app.get("/api/brain/messages/pending")
    async def pending_brain_messages(request: Request, brain_id: str = Query(...)):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        rows = (
            db_all(
                "SELECT * FROM brain_messages WHERE status='pending' AND (from_brain=? OR to_brain=?) ORDER BY created_at DESC",
                (brain_id, brain_id),
            )
            or []
        )

        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        return {"messages": _enrich_messages(rows, brains), "total": len(rows)}

    @app.post("/api/brain/message/process-pending")
    async def process_pending_messages(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        pending = (
            db_all(
                "SELECT * FROM brain_messages WHERE status='pending' ORDER BY created_at ASC LIMIT 100"
            )
            or []
        )

        processed = 0
        handoffs = 0
        escalations = 0
        decisions_queued = 0
        now = now_iso()

        for msg in pending:
            msg_type = msg.get("message_type", "")
            msg_id = msg.get("id", "")

            if msg_type == "handoff_task":
                db_exec(
                    "UPDATE brain_messages SET status='in_progress', resolved_at=? WHERE id=?",
                    (now, msg_id),
                )
                handoffs += 1
                processed += 1

            elif msg_type == "escalate":
                db_exec(
                    "UPDATE brain_messages SET status='in_progress', resolved_at=? WHERE id=?",
                    (now, msg_id),
                )
                escalations += 1
                processed += 1

            elif msg_type == "request_decision":
                db_exec(
                    "UPDATE brain_messages SET status='in_progress', resolved_at=? WHERE id=?",
                    (now, msg_id),
                )
                decisions_queued += 1
                processed += 1

        return {
            "ok": True,
            "processed": processed,
            "handoffs_initiated": handoffs,
            "escalations_flagged": escalations,
            "decisions_queued": decisions_queued,
            "total_pending": len(pending),
        }

    @app.get("/api/brain/messages/violations")
    async def list_violations(request: Request, limit: int = Query(50, ge=1, le=200)):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        rows = (
            db_all(
                "SELECT * FROM brain_message_violations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            or []
        )

        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        brain_map: Dict[str, str] = {b["id"]: b.get("name", b["id"]) for b in brains}

        enriched = []
        for row in rows:
            entry = dict(row)
            entry["from_brain_name"] = brain_map.get(entry["from_brain"], entry["from_brain"])
            entry["to_brain_name"] = brain_map.get(entry["to_brain"], entry["to_brain"])
            enriched.append(entry)

        return {"violations": enriched, "total": len(enriched)}

    @app.get("/api/brain/messages/stats")
    async def message_stats(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        all_messages = db_all("SELECT * FROM brain_messages ORDER BY created_at DESC") or []
        violations = db_all("SELECT COUNT(*) as cnt FROM brain_message_violations") or []
        violation_count = violations[0]["cnt"] if violations else 0

        total = len(all_messages)
        pending_count = sum(1 for m in all_messages if m.get("status") == "pending")
        resolved_count = sum(1 for m in all_messages if m.get("status") == "resolved")

        by_type: Dict[str, int] = {}
        for m in all_messages:
            t = m.get("message_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        brain_map: Dict[str, str] = {b["id"]: b.get("name", b["id"]) for b in brains}

        by_brain: Dict[str, int] = {}
        for m in all_messages:
            fb = brain_map.get(m.get("from_brain", ""), m.get("from_brain", "unknown"))
            by_brain[fb] = by_brain.get(fb, 0) + 1

        recent_handoffs = _enrich_messages(
            [m for m in all_messages if m.get("message_type") == "handoff_task"][:10],
            brains,
        )
        recent_escalations = _enrich_messages(
            [m for m in all_messages if m.get("message_type") == "escalate"][:10],
            brains,
        )
        recent_messages = _enrich_messages(all_messages[:20], brains)

        return {
            "total": total,
            "pending": pending_count,
            "resolved": resolved_count,
            "violations": violation_count,
            "by_type": by_type,
            "by_brain": by_brain,
            "recent_messages": recent_messages,
            "recent_handoffs": recent_handoffs,
            "recent_escalations": recent_escalations,
        }

    @app.get("/api/brain/messages/handoffs")
    async def list_handoff_messages(request: Request, limit: int = Query(50, ge=1, le=200)):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        rows = (
            db_all(
                "SELECT * FROM brain_messages WHERE message_type='handoff_task' ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            or []
        )
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        return {"messages": _enrich_messages(rows, brains), "total": len(rows)}

    @app.get("/api/brain/messages/escalations")
    async def list_escalation_messages(request: Request, limit: int = Query(50, ge=1, le=200)):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        rows = (
            db_all(
                "SELECT * FROM brain_messages WHERE message_type='escalate' ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            or []
        )
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        return {"messages": _enrich_messages(rows, brains), "total": len(rows)}

    @app.get("/api/brain/messages/{message_id}")
    async def get_single_brain_message(message_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        msg = db_one("SELECT * FROM brain_messages WHERE id=?", (message_id,)) if db_one else (
            (db_all("SELECT * FROM brain_messages WHERE id=? LIMIT 1", (message_id,)) or [None])[0]
        )
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")

        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        enriched = _enrich_messages([msg], brains)
        return {"message": sanitize_message_for_display(enriched[0])}

    @app.post("/api/brain/messages/broadcast")
    async def broadcast_signal_endpoint(body: BroadcastSignalRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master access required")

        from_brain_obj = find_brain(body.from_brain)
        if not from_brain_obj:
            raise HTTPException(status_code=404, detail=f"Sender brain '{body.from_brain}' not found")

        from_layer = _brain_layer(from_brain_obj)
        if from_layer > 1:
            _log_violation(body.from_brain, "ALL", "broadcast_signal",
                           f"Broadcast signals can only be sent by layer 0 or 1 brains (sender is layer {from_layer})")
            raise HTTPException(status_code=422, detail="Only Mother or Executive brains can broadcast")

        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        payload_str = _safe_json(body.payload or {"signal_type": body.signal_type})
        now = now_iso()
        sent = []

        for brain in brains:
            if brain["id"] == body.from_brain:
                continue
            msg_id = new_id()
            db_exec(
                """
                INSERT INTO brain_messages(id, from_brain, to_brain, message_type, task_id, payload, priority,
                    status, response_payload, resolved_by, created_at, resolved_at)
                VALUES(?,?,?,'broadcast_signal','',?,'normal','pending','{}','',?,'')
                """,
                (msg_id, body.from_brain, brain["id"], payload_str, now),
            )
            sent.append(brain["id"])

        return {"ok": True, "broadcast_to": len(sent), "recipients": sent}

    # ── ctx-exposed runtime functions ─────────────────────────────────────────

    def _ctx_send_brain_message(
        from_brain: str,
        to_brain: str,
        message_type: str,
        payload: Any,
        task_id: str = "",
        priority: str = "normal",
    ) -> Dict[str, Any]:
        if message_type not in VALID_MESSAGE_TYPES:
            return {"error": f"Invalid message_type: {message_type}"}
        from_obj = find_brain(from_brain)
        to_obj = find_brain(to_brain)
        if not from_obj:
            return {"error": f"Sender brain '{from_brain}' not found"}
        if not to_obj:
            return {"error": f"Receiver brain '{to_brain}' not found"}
        reason = _check_contract(from_obj, to_obj, message_type)
        if reason:
            _log_violation(from_brain, to_brain, message_type, reason)
            return {"error": f"Contract violation: {reason}"}
        priority = priority if priority in VALID_PRIORITIES else "normal"
        msg_id = new_id()
        created = now_iso()
        db_exec(
            """
            INSERT INTO brain_messages(id, from_brain, to_brain, message_type, task_id, payload, priority,
                status, response_payload, resolved_by, created_at, resolved_at)
            VALUES(?,?,?,?,?,?,?,'pending','{}','',?,'')
            """,
            (msg_id, from_brain, to_brain, message_type, task_id or "", _safe_json(payload), priority, created),
        )
        row = (db_one("SELECT * FROM brain_messages WHERE id=?", (msg_id,)) if db_one else
               (db_all("SELECT * FROM brain_messages WHERE id=? LIMIT 1", (msg_id,)) or [None])[0])
        return row if row else {"id": msg_id}

    def _ctx_get_pending_messages(brain_id: str) -> List[Dict[str, Any]]:
        rows = (
            db_all(
                "SELECT * FROM brain_messages WHERE status='pending' AND (from_brain=? OR to_brain=?) ORDER BY created_at ASC",
                (brain_id, brain_id),
            )
            or []
        )
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        return _enrich_messages(rows, brains)

    def _ctx_process_brain_message(
        message_id: str,
        response_payload: Any = None,
        new_status: str = "completed",
    ) -> Dict[str, Any]:
        existing = (db_one("SELECT id FROM brain_messages WHERE id=?", (message_id,)) if db_one else
                    (db_all("SELECT id FROM brain_messages WHERE id=? LIMIT 1", (message_id,)) or [None])[0])
        if not existing:
            return {"error": "Message not found"}
        db_exec(
            "UPDATE brain_messages SET status=?, response_payload=?, resolved_at=? WHERE id=?",
            (new_status, _safe_json(response_payload), now_iso(), message_id),
        )
        updated = (db_one("SELECT * FROM brain_messages WHERE id=?", (message_id,)) if db_one else
                   (db_all("SELECT * FROM brain_messages WHERE id=? LIMIT 1", (message_id,)) or [None])[0])
        return updated if updated else {}

    def _ctx_get_brain_message(message_id: str) -> Optional[Dict[str, Any]]:
        row = (db_one("SELECT * FROM brain_messages WHERE id=?", (message_id,)) if db_one else
               (db_all("SELECT * FROM brain_messages WHERE id=? LIMIT 1", (message_id,)) or [None])[0])
        if not row:
            return None
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        enriched = _enrich_messages([row], brains)
        return enriched[0] if enriched else None

    def _ctx_broadcast_signal(from_brain: str, signal_type: str, payload: Any) -> Dict[str, Any]:
        from_obj = find_brain(from_brain)
        if not from_obj:
            return {"error": f"Brain '{from_brain}' not found"}
        from_layer = _brain_layer(from_obj)
        if from_layer > 1:
            _log_violation(from_brain, "ALL", "broadcast_signal",
                           f"Broadcast signals can only be sent by layer 0 or 1 brains (sender is layer {from_layer})")
            return {"error": "Only Mother or Executive brains can broadcast"}
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        payload_merged = _safe_json(payload or {"signal_type": signal_type})
        now = now_iso()
        sent = []
        for brain in brains:
            if brain["id"] == from_brain:
                continue
            msg_id = new_id()
            db_exec(
                """
                INSERT INTO brain_messages(id, from_brain, to_brain, message_type, task_id, payload, priority,
                    status, response_payload, resolved_by, created_at, resolved_at)
                VALUES(?,?,?,'broadcast_signal','',?,'normal','pending','{}','',?,'')
                """,
                (msg_id, from_brain, brain["id"], payload_merged, now),
            )
            sent.append(brain["id"])
        return {"broadcast_to": len(sent), "recipients": sent}

    def _ctx_process_pending_brain_messages() -> Dict[str, Any]:
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        pending = (
            db_all("SELECT * FROM brain_messages WHERE status='pending' ORDER BY created_at ASC LIMIT 100")
            or []
        )
        pending.sort(key=lambda m: (priority_order.get(m.get("priority", "normal"), 2),))
        processed = 0
        handoffs = 0
        escalations = 0
        decisions_queued = 0
        now = now_iso()

        for msg in pending:
            msg_type = msg.get("message_type", "")
            msg_id = msg.get("id", "")

            if msg_type == "handoff_task":
                db_exec(
                    "UPDATE brain_messages SET status='in_progress', resolved_at=? WHERE id=?",
                    (now, msg_id),
                )
                handoffs += 1
                processed += 1
            elif msg_type == "escalate":
                db_exec(
                    "UPDATE brain_messages SET status='in_progress', resolved_at=? WHERE id=?",
                    (now, msg_id),
                )
                escalations += 1
                processed += 1
            elif msg_type == "request_decision":
                db_exec(
                    "UPDATE brain_messages SET status='in_progress', resolved_at=? WHERE id=?",
                    (now, msg_id),
                )
                decisions_queued += 1
                processed += 1

        return {
            "processed": processed,
            "handoffs_initiated": handoffs,
            "escalations_flagged": escalations,
            "decisions_queued": decisions_queued,
            "total_pending": len(pending),
        }

    log.info("Brain communication layer installed")
    return {
        "send_brain_message": _ctx_send_brain_message,
        "get_pending_messages": _ctx_get_pending_messages,
        "process_brain_message": _ctx_process_brain_message,
        "get_brain_message": _ctx_get_brain_message,
        "broadcast_signal": _ctx_broadcast_signal,
        "process_pending_brain_messages": _ctx_process_pending_brain_messages,
        "sanitize_message_for_display": sanitize_message_for_display,
    }
