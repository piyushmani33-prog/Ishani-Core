"""
Shared Memory Layer — Key-value + structured memory store for all brains.

Supports namespaces (candidate, tracker, action_history), optimistic
concurrency via version counter, and full version history.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


class MemorySetRequest(BaseModel):
    value: Dict[str, Any]
    updated_by: str = "system"


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_shared_memory_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
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
            CREATE TABLE IF NOT EXISTS shared_memory (
                key         TEXT NOT NULL,
                namespace   TEXT NOT NULL,
                value_json  TEXT NOT NULL DEFAULT '{}',
                updated_by  TEXT NOT NULL DEFAULT 'system',
                version     INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                PRIMARY KEY (namespace, key)
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS shared_memory_history (
                id          TEXT PRIMARY KEY,
                namespace   TEXT NOT NULL,
                key         TEXT NOT NULL,
                value_json  TEXT NOT NULL DEFAULT '{}',
                updated_by  TEXT NOT NULL DEFAULT 'system',
                version     INTEGER NOT NULL DEFAULT 1,
                recorded_at TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Helper functions
    # -----------------------------------------------------------------------

    def memory_get(namespace: str, key: str) -> Optional[Dict[str, Any]]:
        rows = db_all(
            "SELECT key, namespace, value_json, updated_by, version, created_at, updated_at FROM shared_memory WHERE namespace=? AND key=?",
            (namespace, key),
        )
        if not rows:
            return None
        r = rows[0]
        return {
            "key": r[0],
            "namespace": r[1],
            "value": json.loads(r[2] or "{}"),
            "updated_by": r[3],
            "version": r[4],
            "created_at": r[5],
            "updated_at": r[6],
        }

    def memory_set(namespace: str, key: str, value: Dict[str, Any], updated_by: str = "system") -> Dict[str, Any]:
        now = now_iso()
        existing = memory_get(namespace, key)
        if existing:
            new_version = existing["version"] + 1
            # Archive current version to history
            db_exec(
                "INSERT INTO shared_memory_history (id, namespace, key, value_json, updated_by, version, recorded_at) VALUES (?,?,?,?,?,?,?)",
                (new_id("smh"), namespace, key, json.dumps(existing["value"]), existing["updated_by"], existing["version"], now),
            )
            db_exec(
                "UPDATE shared_memory SET value_json=?, updated_by=?, version=?, updated_at=? WHERE namespace=? AND key=?",
                (json.dumps(value), updated_by, new_version, now, namespace, key),
            )
        else:
            new_version = 1
            db_exec(
                "INSERT INTO shared_memory (key, namespace, value_json, updated_by, version, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (key, namespace, json.dumps(value), updated_by, new_version, now, now),
            )
        log.info("[SharedMemory] set %s/%s v%d by %s", namespace, key, new_version, updated_by)
        return {"key": key, "namespace": namespace, "value": value, "updated_by": updated_by, "version": new_version, "updated_at": now}

    def memory_list(namespace: str) -> List[Dict[str, Any]]:
        rows = db_all(
            "SELECT key, namespace, value_json, updated_by, version, created_at, updated_at FROM shared_memory WHERE namespace=? ORDER BY key ASC",
            (namespace,),
        )
        return [
            {
                "key": r[0],
                "namespace": r[1],
                "value": json.loads(r[2] or "{}"),
                "updated_by": r[3],
                "version": r[4],
                "created_at": r[5],
                "updated_at": r[6],
            }
            for r in rows
        ]

    def memory_history(namespace: str, key: str) -> List[Dict[str, Any]]:
        rows = db_all(
            "SELECT id, namespace, key, value_json, updated_by, version, recorded_at FROM shared_memory_history WHERE namespace=? AND key=? ORDER BY version DESC",
            (namespace, key),
        )
        return [
            {
                "id": r[0],
                "namespace": r[1],
                "key": r[2],
                "value": json.loads(r[3] or "{}"),
                "updated_by": r[4],
                "version": r[5],
                "recorded_at": r[6],
            }
            for r in rows
        ]

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.get("/api/memory/{namespace}")
    async def api_memory_list(namespace: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"ok": True, "entries": memory_list(namespace)}

    @app.get("/api/memory/{namespace}/{key}")
    async def api_memory_get(namespace: str, key: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        entry = memory_get(namespace, key)
        if entry is None:
            raise HTTPException(status_code=404, detail="Memory entry not found")
        return {"ok": True, "entry": entry}

    @app.post("/api/memory/{namespace}/{key}")
    async def api_memory_set(namespace: str, key: str, body: MemorySetRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        entry = memory_set(namespace, key, body.value, updated_by=body.updated_by)
        return {"ok": True, "entry": entry}

    # Export to ctx
    ctx["memory_get"] = memory_get
    ctx["memory_set"] = memory_set
    ctx["memory_list"] = memory_list
    ctx["memory_history"] = memory_history

    log.info("[SharedMemory] layer installed")
    return ctx
