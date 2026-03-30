from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Default contract templates per brain layer
# ---------------------------------------------------------------------------

_LAYER_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "mother": {
        "role": "Supreme orchestrator — issues directives to all child brains and maintains whole-system coherence.",
        "allowed_events": ["system_boot", "shutdown", "policy_change", "escalation", "alert", "report_all"],
        "allowed_tools": ["all"],
        "allowed_memory_namespaces": ["all"],
        "task_types_can_create": ["directive", "policy", "escalation", "system_task"],
        "task_types_can_resolve": ["directive", "escalation", "system_task"],
        "disclosure_level": "full",
        "evolution_scope": "Can evolve any aspect of the system with human approval.",
    },
    "executive": {
        "role": "Cabinet-level brain — translates mother mandates into actionable lane orders.",
        "allowed_events": ["directive", "lane_report", "escalation", "mutation_request", "knowledge_update"],
        "allowed_tools": ["llm_bridge", "memory_store", "task_queue"],
        "allowed_memory_namespaces": ["cabinet", "executive", "shared"],
        "task_types_can_create": ["lane_task", "secretary_directive", "analysis"],
        "task_types_can_resolve": ["lane_task", "secretary_directive"],
        "disclosure_level": "guided",
        "evolution_scope": "Can propose mutations within its lane; requires mother approval for cross-lane changes.",
    },
    "secretary": {
        "role": "Lane owner — executes and coordinates tasks within a single operational lane.",
        "allowed_events": ["lane_task", "report_request", "tool_call", "knowledge_update"],
        "allowed_tools": ["lane_tools", "document_studio", "task_queue"],
        "allowed_memory_namespaces": ["lane", "shared"],
        "task_types_can_create": ["tool_task", "sub_task", "report"],
        "task_types_can_resolve": ["tool_task", "sub_task", "report"],
        "disclosure_level": "guided",
        "evolution_scope": "Can update own learning targets; cannot mutate lane boundaries without cabinet approval.",
    },
    "domain": {
        "role": "Domain specialist — owns a vertical knowledge domain and delivers expertise.",
        "allowed_events": ["domain_query", "knowledge_update", "tool_call"],
        "allowed_tools": ["domain_tools", "knowledge_store"],
        "allowed_memory_namespaces": ["domain", "shared"],
        "task_types_can_create": ["domain_analysis", "knowledge_item"],
        "task_types_can_resolve": ["domain_analysis", "knowledge_item"],
        "disclosure_level": "guided",
        "evolution_scope": "Can expand domain knowledge; cannot cross into other domains without secretary approval.",
    },
    "machine": {
        "role": "Infrastructure brain — runs low-level compute, model inference, and system services.",
        "allowed_events": ["compute_request", "model_load", "inference", "health_check"],
        "allowed_tools": ["ollama", "local_llm", "system_exec"],
        "allowed_memory_namespaces": ["machine", "shared"],
        "task_types_can_create": ["compute_task", "inference_task"],
        "task_types_can_resolve": ["compute_task", "inference_task"],
        "disclosure_level": "minimal",
        "evolution_scope": "Can tune inference parameters; model swaps require executive approval.",
    },
    "tool": {
        "role": "Utility brain — provides reusable tool capabilities to higher-layer brains.",
        "allowed_events": ["tool_request", "health_check"],
        "allowed_tools": ["self"],
        "allowed_memory_namespaces": ["tool", "shared"],
        "task_types_can_create": ["tool_result"],
        "task_types_can_resolve": ["tool_result"],
        "disclosure_level": "minimal",
        "evolution_scope": "Can extend own toolset with secretary approval.",
    },
    "atom": {
        "role": "Micro-agent — handles atomic, single-purpose operations.",
        "allowed_events": ["atomic_task", "health_check"],
        "allowed_tools": ["atomic_tools"],
        "allowed_memory_namespaces": ["atom"],
        "task_types_can_create": ["atomic_result"],
        "task_types_can_resolve": ["atomic_result"],
        "disclosure_level": "minimal",
        "evolution_scope": "Cannot self-evolve; must be updated by parent tool or secretary brain.",
    },
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ContractUpdateRequest(BaseModel):
    role: Optional[str] = None
    mission: Optional[str] = None
    allowed_events: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None
    allowed_memory_namespaces: Optional[List[str]] = None
    task_types_can_create: Optional[List[str]] = None
    task_types_can_resolve: Optional[List[str]] = None
    disclosure_level: Optional[str] = None
    learning_targets: Optional[List[str]] = None
    evolution_scope: Optional[str] = None


# ---------------------------------------------------------------------------
# Layer installer
# ---------------------------------------------------------------------------


def install_brain_contract_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    db_one = ctx["db_one"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    brain_hierarchy_payload = ctx["brain_hierarchy_payload"]
    can_control_brain = ctx["can_control_brain"]
    log = ctx["log"]

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    db_exec(
        """
        CREATE TABLE IF NOT EXISTS brain_contracts (
            brain_id TEXT PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            layer TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT '',
            mission TEXT NOT NULL DEFAULT '',
            allowed_events TEXT NOT NULL DEFAULT '[]',
            allowed_tools TEXT NOT NULL DEFAULT '[]',
            allowed_memory_namespaces TEXT NOT NULL DEFAULT '[]',
            task_types_can_create TEXT NOT NULL DEFAULT '[]',
            task_types_can_resolve TEXT NOT NULL DEFAULT '[]',
            disclosure_level TEXT NOT NULL DEFAULT 'guided',
            learning_targets TEXT NOT NULL DEFAULT '[]',
            evolution_scope TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )

    db_exec(
        """
        CREATE TABLE IF NOT EXISTS contract_violations (
            id TEXT PRIMARY KEY,
            brain_id TEXT NOT NULL DEFAULT '',
            action_type TEXT NOT NULL DEFAULT '',
            action_detail TEXT NOT NULL DEFAULT '',
            blocked_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        )
        """
    )

    db_exec(
        """
        CREATE TABLE IF NOT EXISTS brain_health_metrics (
            brain_id TEXT PRIMARY KEY,
            tasks_created INTEGER NOT NULL DEFAULT 0,
            tasks_resolved INTEGER NOT NULL DEFAULT 0,
            actions_approved INTEGER NOT NULL DEFAULT 0,
            actions_rejected INTEGER NOT NULL DEFAULT 0,
            conflicts_generated INTEGER NOT NULL DEFAULT 0,
            learning_score REAL NOT NULL DEFAULT 0.5,
            health_score REAL NOT NULL DEFAULT 1.0,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _json_load(raw: Any) -> List[str]:
        if isinstance(raw, list):
            return raw
        try:
            return json.loads(raw or "[]")
        except Exception:
            return []

    def _get_contract(brain_id: str) -> Optional[Dict[str, Any]]:
        row = db_one("SELECT * FROM brain_contracts WHERE brain_id = ?", (brain_id,))
        if not row:
            return None
        return {
            "brain_id": row["brain_id"],
            "name": row["name"],
            "layer": row["layer"],
            "role": row["role"],
            "mission": row["mission"],
            "allowed_events": _json_load(row["allowed_events"]),
            "allowed_tools": _json_load(row["allowed_tools"]),
            "allowed_memory_namespaces": _json_load(row["allowed_memory_namespaces"]),
            "task_types_can_create": _json_load(row["task_types_can_create"]),
            "task_types_can_resolve": _json_load(row["task_types_can_resolve"]),
            "disclosure_level": row["disclosure_level"],
            "learning_targets": _json_load(row["learning_targets"]),
            "evolution_scope": row["evolution_scope"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _log_violation(brain_id: str, action_type: str, action_detail: str, blocked_reason: str) -> None:
        try:
            db_exec(
                """
                INSERT INTO contract_violations (id, brain_id, action_type, action_detail, blocked_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (new_id("cv"), brain_id, action_type, action_detail[:500], blocked_reason[:500], now_iso()),
            )
        except Exception as exc:  # pragma: no cover
            log.warning("Failed to log contract violation: %s", exc)

    # ------------------------------------------------------------------
    # Contract enforcement functions (exposed via ctx)
    # ------------------------------------------------------------------

    def check_event_allowed(brain_id: str, event_type: str) -> bool:
        contract = _get_contract(brain_id)
        if not contract:
            return True  # no contract → no restriction
        allowed = contract["allowed_events"]
        if "all" in allowed or not allowed:
            return True
        if event_type in allowed:
            return True
        _log_violation(brain_id, "event", event_type, f"Event '{event_type}' not in allowed_events for brain '{brain_id}'")
        return False

    def check_task_create_allowed(brain_id: str, task_type: str) -> bool:
        contract = _get_contract(brain_id)
        if not contract:
            return True
        allowed = contract["task_types_can_create"]
        if "all" in allowed or not allowed:
            return True
        if task_type in allowed:
            return True
        _log_violation(brain_id, "task_create", task_type, f"Task type '{task_type}' not in task_types_can_create for brain '{brain_id}'")
        return False

    def check_task_resolve_allowed(brain_id: str, task_type: str) -> bool:
        contract = _get_contract(brain_id)
        if not contract:
            return True
        allowed = contract["task_types_can_resolve"]
        if "all" in allowed or not allowed:
            return True
        if task_type in allowed:
            return True
        _log_violation(brain_id, "task_resolve", task_type, f"Task type '{task_type}' not in task_types_can_resolve for brain '{brain_id}'")
        return False

    def check_tool_allowed(brain_id: str, tool_name: str) -> bool:
        contract = _get_contract(brain_id)
        if not contract:
            return True
        allowed = contract["allowed_tools"]
        if "all" in allowed or "self" in allowed or not allowed:
            return True
        if tool_name in allowed:
            return True
        _log_violation(brain_id, "tool", tool_name, f"Tool '{tool_name}' not in allowed_tools for brain '{brain_id}'")
        return False

    # ------------------------------------------------------------------
    # Health metric tracking (exposed via ctx)
    # ------------------------------------------------------------------

    _VALID_METRICS = {
        "tasks_created",
        "tasks_resolved",
        "actions_approved",
        "actions_rejected",
        "conflicts_generated",
    }

    def record_brain_metric(brain_id: str, metric_name: str, delta: float = 1.0) -> None:
        if metric_name not in _VALID_METRICS and metric_name not in {"learning_score"}:
            log.debug("Unknown brain metric: %s", metric_name)
            return
        try:
            existing = db_one("SELECT * FROM brain_health_metrics WHERE brain_id = ?", (brain_id,))
            ts = now_iso()
            if not existing:
                db_exec(
                    """
                    INSERT INTO brain_health_metrics
                        (brain_id, tasks_created, tasks_resolved, actions_approved, actions_rejected,
                         conflicts_generated, learning_score, health_score, updated_at)
                    VALUES (?, 0, 0, 0, 0, 0, 0.5, 1.0, ?)
                    """,
                    (brain_id, ts),
                )
                existing = db_one("SELECT * FROM brain_health_metrics WHERE brain_id = ?", (brain_id,))
            if not existing:
                return
            if metric_name == "learning_score":
                new_val = max(0.0, min(1.0, float(existing.get("learning_score", 0.5)) + delta))
                db_exec(
                    "UPDATE brain_health_metrics SET learning_score = ?, updated_at = ? WHERE brain_id = ?",
                    (new_val, ts, brain_id),
                )
            else:
                # Use an explicit column-to-SQL mapping to avoid dynamic SQL construction
                _METRIC_SQL = {
                    "tasks_created": "UPDATE brain_health_metrics SET tasks_created = ?, updated_at = ? WHERE brain_id = ?",
                    "tasks_resolved": "UPDATE brain_health_metrics SET tasks_resolved = ?, updated_at = ? WHERE brain_id = ?",
                    "actions_approved": "UPDATE brain_health_metrics SET actions_approved = ?, updated_at = ? WHERE brain_id = ?",
                    "actions_rejected": "UPDATE brain_health_metrics SET actions_rejected = ?, updated_at = ? WHERE brain_id = ?",
                    "conflicts_generated": "UPDATE brain_health_metrics SET conflicts_generated = ?, updated_at = ? WHERE brain_id = ?",
                }
                sql = _METRIC_SQL.get(metric_name)
                if not sql:
                    return
                new_val = max(0, int(existing.get(metric_name, 0) or 0) + int(delta))
                db_exec(sql, (new_val, ts, brain_id))
            # Recompute health score
            row = db_one("SELECT * FROM brain_health_metrics WHERE brain_id = ?", (brain_id,))
            if row:
                approved = int(row.get("actions_approved", 0) or 0)
                rejected = int(row.get("actions_rejected", 0) or 0)
                conflicts = int(row.get("conflicts_generated", 0) or 0)
                total_actions = approved + rejected
                approval_rate = (approved / total_actions) if total_actions > 0 else 1.0
                conflict_penalty = min(0.3, conflicts * 0.02)
                health = max(0.0, min(1.0, approval_rate - conflict_penalty))
                db_exec(
                    "UPDATE brain_health_metrics SET health_score = ?, updated_at = ? WHERE brain_id = ?",
                    (round(health, 3), ts, brain_id),
                )
        except Exception as exc:
            log.warning("record_brain_metric error for %s/%s: %s", brain_id, metric_name, exc)

    # ------------------------------------------------------------------
    # Contract seeding
    # ------------------------------------------------------------------

    def _seed_contracts() -> None:
        try:
            hierarchy = brain_hierarchy_payload()
        except Exception as exc:
            log.warning("brain_contract_layer: could not seed contracts — %s", exc)
            return
        ts = now_iso()
        for brain in hierarchy.get("brains", []):
            brain_id = brain.get("id")
            if not brain_id:
                continue
            existing = db_one("SELECT brain_id FROM brain_contracts WHERE brain_id = ?", (brain_id,))
            if existing:
                continue
            layer = brain.get("layer", "tool")
            defaults = _LAYER_DEFAULTS.get(layer, _LAYER_DEFAULTS["tool"])
            learning_targets = brain.get("learning_targets", [])
            if not isinstance(learning_targets, list):
                learning_targets = []
            mission = brain.get("mission") or brain.get("authority") or defaults["role"]
            db_exec(
                """
                INSERT INTO brain_contracts
                    (brain_id, name, layer, role, mission,
                     allowed_events, allowed_tools, allowed_memory_namespaces,
                     task_types_can_create, task_types_can_resolve,
                     disclosure_level, learning_targets, evolution_scope,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brain_id,
                    brain.get("name", brain_id),
                    layer,
                    defaults["role"],
                    mission[:500],
                    json.dumps(defaults["allowed_events"]),
                    json.dumps(defaults["allowed_tools"]),
                    json.dumps(defaults["allowed_memory_namespaces"]),
                    json.dumps(defaults["task_types_can_create"]),
                    json.dumps(defaults["task_types_can_resolve"]),
                    defaults["disclosure_level"],
                    json.dumps(learning_targets[:10]),
                    defaults["evolution_scope"],
                    ts,
                    ts,
                ),
            )
            # Bootstrap health metrics row
            existing_health = db_one("SELECT brain_id FROM brain_health_metrics WHERE brain_id = ?", (brain_id,))
            if not existing_health:
                db_exec(
                    """
                    INSERT INTO brain_health_metrics
                        (brain_id, tasks_created, tasks_resolved, actions_approved, actions_rejected,
                         conflicts_generated, learning_score, health_score, updated_at)
                    VALUES (?, 0, 0, 0, 0, 0, ?, 1.0, ?)
                    """,
                    (brain_id, round(float(brain.get("learning_score", 0.5)), 3), ts),
                )
        log.info("brain_contract_layer: contracts seeded for all known brains.")

    _seed_contracts()

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    @app.get("/api/brain/contracts")
    async def list_brain_contracts(request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        rows = db_all("SELECT * FROM brain_contracts ORDER BY layer, brain_id")
        contracts = []
        for row in rows:
            contracts.append({
                "brain_id": row["brain_id"],
                "name": row["name"],
                "layer": row["layer"],
                "role": row["role"],
                "mission": row["mission"],
                "allowed_events": _json_load(row["allowed_events"]),
                "allowed_tools": _json_load(row["allowed_tools"]),
                "allowed_memory_namespaces": _json_load(row["allowed_memory_namespaces"]),
                "task_types_can_create": _json_load(row["task_types_can_create"]),
                "task_types_can_resolve": _json_load(row["task_types_can_resolve"]),
                "disclosure_level": row["disclosure_level"],
                "learning_targets": _json_load(row["learning_targets"]),
                "evolution_scope": row["evolution_scope"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return {"ok": True, "contracts": contracts, "total": len(contracts)}

    @app.get("/api/brain/contracts/violations")
    async def list_contract_violations(request: Request, limit: int = 50):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        rows = db_all(
            "SELECT * FROM contract_violations ORDER BY created_at DESC LIMIT ?",
            (min(limit, 200),),
        )
        return {"ok": True, "violations": list(rows), "total": len(rows)}

    @app.get("/api/brain/contracts/{brain_id}")
    async def get_brain_contract(brain_id: str, request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        contract = _get_contract(brain_id)
        if not contract:
            raise HTTPException(status_code=404, detail=f"No contract found for brain '{brain_id}'.")
        return {"ok": True, "contract": contract}

    @app.post("/api/brain/contracts/{brain_id}")
    async def update_brain_contract(brain_id: str, req: ContractUpdateRequest, request: Request):
        viewer = session_user(request)
        if not viewer or viewer.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master access required to modify brain contracts.")
        contract = _get_contract(brain_id)
        if not contract:
            raise HTTPException(status_code=404, detail=f"No contract found for brain '{brain_id}'.")
        ts = now_iso()
        updates: Dict[str, Any] = {"updated_at": ts}
        if req.role is not None:
            updates["role"] = req.role[:500]
        if req.mission is not None:
            updates["mission"] = req.mission[:500]
        if req.allowed_events is not None:
            updates["allowed_events"] = json.dumps(req.allowed_events)
        if req.allowed_tools is not None:
            updates["allowed_tools"] = json.dumps(req.allowed_tools)
        if req.allowed_memory_namespaces is not None:
            updates["allowed_memory_namespaces"] = json.dumps(req.allowed_memory_namespaces)
        if req.task_types_can_create is not None:
            updates["task_types_can_create"] = json.dumps(req.task_types_can_create)
        if req.task_types_can_resolve is not None:
            updates["task_types_can_resolve"] = json.dumps(req.task_types_can_resolve)
        if req.disclosure_level is not None:
            if req.disclosure_level not in {"full", "guided", "minimal"}:
                raise HTTPException(status_code=400, detail="disclosure_level must be 'full', 'guided', or 'minimal'.")
            updates["disclosure_level"] = req.disclosure_level
        if req.learning_targets is not None:
            updates["learning_targets"] = json.dumps(req.learning_targets[:20])
        if req.evolution_scope is not None:
            updates["evolution_scope"] = req.evolution_scope[:500]
        # Use explicit column allowlist for SQL construction to avoid injection risks
        _CONTRACT_COLUMNS = {
            "role", "mission", "allowed_events", "allowed_tools",
            "allowed_memory_namespaces", "task_types_can_create", "task_types_can_resolve",
            "disclosure_level", "learning_targets", "evolution_scope", "updated_at",
        }
        safe_updates = {k: v for k, v in updates.items() if k in _CONTRACT_COLUMNS}
        set_clause = ", ".join(f"{k} = ?" for k in safe_updates)
        db_exec(
            "UPDATE brain_contracts SET " + set_clause + " WHERE brain_id = ?",
            tuple(safe_updates.values()) + (brain_id,),
        )
        return {"ok": True, "brain_id": brain_id, "updated_fields": list(safe_updates.keys()), "contract": _get_contract(brain_id)}

    # ------------------------------------------------------------------
    # Health endpoints
    # ------------------------------------------------------------------

    def _health_row(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "brain_id": row["brain_id"],
            "tasks_created": int(row.get("tasks_created", 0) or 0),
            "tasks_resolved": int(row.get("tasks_resolved", 0) or 0),
            "actions_approved": int(row.get("actions_approved", 0) or 0),
            "actions_rejected": int(row.get("actions_rejected", 0) or 0),
            "conflicts_generated": int(row.get("conflicts_generated", 0) or 0),
            "learning_score": round(float(row.get("learning_score", 0.5) or 0.5), 3),
            "health_score": round(float(row.get("health_score", 1.0) or 1.0), 3),
            "updated_at": row.get("updated_at", ""),
        }

    @app.get("/api/brain/health")
    async def list_brain_health(request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        rows = db_all("SELECT * FROM brain_health_metrics ORDER BY health_score ASC")
        return {"ok": True, "health": [_health_row(r) for r in rows], "total": len(rows)}

    @app.get("/api/brain/health/{brain_id}")
    async def get_brain_health(brain_id: str, request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        row = db_one("SELECT * FROM brain_health_metrics WHERE brain_id = ?", (brain_id,))
        if not row:
            raise HTTPException(status_code=404, detail=f"No health metrics found for brain '{brain_id}'.")
        return {"ok": True, "health": _health_row(row)}

    log.info("brain_contract_layer: loaded — contracts, violations, health metrics active.")

    return {
        "status": "loaded",
        "check_event_allowed": check_event_allowed,
        "check_task_create_allowed": check_task_create_allowed,
        "check_task_resolve_allowed": check_task_resolve_allowed,
        "check_tool_allowed": check_tool_allowed,
        "record_brain_metric": record_brain_metric,
    }
