"""
Event Bus Layer — Centralized async-safe event bus for Ishani-Core.

Supports publish/subscribe across all brains, logs every event to DB,
and exposes REST APIs for publishing, querying the log, and listing subscriptions.
"""

import asyncio
import inspect
import json
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PublishEventRequest(BaseModel):
    event_type: str
    source_brain: str
    payload: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_event_bus_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    log = ctx["log"]

    # In-memory registry: event_type → list of async handler callables
    _subscribers: Dict[str, List[Callable]] = defaultdict(list)

    # -----------------------------------------------------------------------
    # DB setup
    # -----------------------------------------------------------------------

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS event_bus_log (
                id              TEXT PRIMARY KEY,
                event_type      TEXT NOT NULL,
                source_brain    TEXT NOT NULL DEFAULT '',
                payload_json    TEXT NOT NULL DEFAULT '{}',
                subscriber_count INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Core bus functions
    # -----------------------------------------------------------------------

    def subscribe(event_type: str, handler_fn: Callable) -> None:
        """Register *handler_fn* to be called whenever *event_type* is published."""
        _subscribers[event_type].append(handler_fn)
        log.info("[EventBus] subscribed handler for '%s': %s", event_type, getattr(handler_fn, "__name__", repr(handler_fn)))

    async def publish(event_type: str, payload: Dict[str, Any], source_brain: str = "system") -> Dict[str, Any]:
        """Publish an event; dispatch to all subscribers concurrently."""
        event_id = new_id("evt")
        timestamp = now_iso()

        event = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "source_brain": source_brain,
            "payload": payload,
        }

        handlers = list(_subscribers.get(event_type, []))
        subscriber_count = len(handlers)

        # Dispatch to all handlers concurrently; isolate failures
        if handlers:
            async def _safe_call(fn, ev):
                try:
                    if inspect.iscoroutinefunction(fn):
                        await fn(ev)
                    else:
                        result = fn(ev)
                        if asyncio.isfuture(result) or asyncio.iscoroutine(result):
                            await result
                except Exception as exc:
                    log.warning("[EventBus] handler %s failed for event %s: %s", getattr(fn, "__name__", fn), event_id, exc)

            await asyncio.gather(*[_safe_call(h, event) for h in handlers])

        # Persist to DB
        db_exec(
            "INSERT INTO event_bus_log (id, event_type, source_brain, payload_json, subscriber_count, created_at) VALUES (?,?,?,?,?,?)",
            (event_id, event_type, source_brain, json.dumps(payload), subscriber_count, timestamp),
        )

        log.info("[EventBus] published '%s' (id=%s, subscribers=%d)", event_type, event_id, subscriber_count)
        return event

    def list_subscriptions() -> List[Dict[str, Any]]:
        result = []
        for event_type, handlers in _subscribers.items():
            for fn in handlers:
                result.append({
                    "event_type": event_type,
                    "handler": getattr(fn, "__name__", repr(fn)),
                })
        return result

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.post("/api/events/publish")
    async def api_publish_event(body: PublishEventRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") not in ("master", "operator"):
            raise HTTPException(status_code=403, detail="Master/operator only")

        event = await publish(body.event_type, body.payload, source_brain=body.source_brain)
        return {"ok": True, "event": event}

    @app.get("/api/events/log")
    async def api_event_log(request: Request, limit: int = 50):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all(
            "SELECT id, event_type, source_brain, payload_json, subscriber_count, created_at FROM event_bus_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "event_type": r[1],
                "source_brain": r[2],
                "payload": json.loads(r[3] or "{}"),
                "subscriber_count": r[4],
                "created_at": r[5],
            })
        return {"ok": True, "events": result}

    @app.get("/api/events/subscriptions")
    async def api_event_subscriptions(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        return {"ok": True, "subscriptions": list_subscriptions()}

    # Expose helpers back to ctx for downstream layers
    ctx["event_bus_subscribe"] = subscribe
    ctx["event_bus_publish"] = publish
    ctx["event_bus_list_subscriptions"] = list_subscriptions

    log.info("[EventBus] layer installed")
    return ctx
