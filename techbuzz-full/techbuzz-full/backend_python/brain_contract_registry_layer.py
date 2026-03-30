"""
Brain Contract Registry Layer — Formal identity, role, permissions,
responsibilities, learning targets, and evolution boundaries for every brain.

Each brain has a runtime contract that defines:
  • brain_id, name, layer, role, mission
  • allowed_events — events this brain may process
  • allowed_tools — tools this brain may invoke
  • allowed_memory_namespaces — memory namespaces it may read/write
  • task_types_can_create / task_types_can_resolve
  • disclosure_level — controls what information the brain may expose
  • learning_targets — what the brain should learn from
  • evolution_scope — boundaries for self-improvement proposals

The autonomous loop and brain executor consult these contracts before
dispatching work, ensuring brains stay within their defined boundaries.

Violations (out-of-contract events, forbidden task types, etc.) are logged
for audit and never silently dropped.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Default contracts — seeded for every known brain
# ---------------------------------------------------------------------------

_DEFAULT_CONTRACTS: List[Dict[str, Any]] = [
    # --- Mother ---
    {
        "brain_id": "mother_brain",
        "name": "Mother Brain",
        "layer": "mother",
        "role": "system_guardian",
        "mission": "Provide guidance, permissions, monitoring, task assignment, and motivational alignment to every child brain.",
        "allowed_events": ["*"],
        "allowed_tools": ["*"],
        "allowed_memory_namespaces": ["*"],
        "task_types_can_create": ["*"],
        "task_types_can_resolve": ["*"],
        "disclosure_level": "master",
        "learning_targets": ["system_outcomes", "cross_brain_coherence", "revenue_signals"],
        "evolution_scope": "full",
    },
    # --- Executive: Cabinet ---
    {
        "brain_id": "cabinet_brain",
        "name": "Cabinet Brain",
        "layer": "executive",
        "role": "prime_minister",
        "mission": "Translate the mother mandate into cabinet orders, lane priorities, and permissions for child brains.",
        "allowed_events": ["tracker.updated", "candidate.inactive", "interview.scheduled", "status.requested"],
        "allowed_tools": ["task_system", "decision_aggregator", "action_output"],
        "allowed_memory_namespaces": ["system", "recruitment", "strategy"],
        "task_types_can_create": ["recommendation", "status_update", "alert"],
        "task_types_can_resolve": ["recommendation", "status_update"],
        "disclosure_level": "operator",
        "learning_targets": ["cabinet_decisions", "secretary_performance", "delivery_tempo"],
        "evolution_scope": "workflow",
    },
    # --- Executive: Akshaya Memory ---
    {
        "brain_id": "akshaya_brain",
        "name": "Akshaya Memory Brain",
        "layer": "executive",
        "role": "memory_guardian",
        "mission": "Preserve, compress, recall, and verify the memory chain before it flows back into active work.",
        "allowed_events": ["memory.updated", "archive.requested"],
        "allowed_tools": ["shared_memory", "learning_engine"],
        "allowed_memory_namespaces": ["*"],
        "task_types_can_create": ["alert", "status_update"],
        "task_types_can_resolve": ["alert"],
        "disclosure_level": "operator",
        "learning_targets": ["recall_accuracy", "archive_integrity"],
        "evolution_scope": "performance",
    },
    # --- Executive: Carbon Bond ---
    {
        "brain_id": "carbon_brain",
        "name": "Carbon Bond Brain",
        "layer": "executive",
        "role": "system_connector",
        "mission": "Bond every domain, machine, tool, and report lane into one shared nervous system.",
        "allowed_events": ["*"],
        "allowed_tools": ["event_bus", "neural_mesh"],
        "allowed_memory_namespaces": ["system", "signals"],
        "task_types_can_create": ["alert", "status_update"],
        "task_types_can_resolve": ["alert"],
        "disclosure_level": "operator",
        "learning_targets": ["signal_integrity", "routing_efficiency"],
        "evolution_scope": "integration",
    },
    # --- Executive: Interpreter ---
    {
        "brain_id": "interpreter_brain",
        "name": "Interpreter Bridge Brain",
        "layer": "executive",
        "role": "translator",
        "mission": "Translate operator language into brain directives and brain output back into human language.",
        "allowed_events": ["tracker.updated", "candidate.inactive", "interview.scheduled"],
        "allowed_tools": ["task_system", "learning_engine"],
        "allowed_memory_namespaces": ["system", "conversations"],
        "task_types_can_create": ["alert"],
        "task_types_can_resolve": ["alert"],
        "disclosure_level": "member",
        "learning_targets": ["translation_accuracy", "command_clarity"],
        "evolution_scope": "template",
    },
    # --- Tool: ATS Kanban ---
    {
        "brain_id": "tool_ats_kanban",
        "name": "ATS Kanban Brain",
        "layer": "tool",
        "role": "tracker_updater",
        "mission": "Keep ATS Kanban board in sync with recruitment events.",
        "allowed_events": ["tracker.updated", "candidate.inactive"],
        "allowed_tools": ["task_system"],
        "allowed_memory_namespaces": ["recruitment"],
        "task_types_can_create": ["status_update", "follow_up"],
        "task_types_can_resolve": ["status_update"],
        "disclosure_level": "member",
        "learning_targets": ["follow_up_effectiveness", "status_accuracy"],
        "evolution_scope": "workflow",
    },
    # --- Recruitment Executive ---
    {
        "brain_id": "recruitment_executive",
        "name": "Recruitment Executive Brain",
        "layer": "executive",
        "role": "recruitment_oversight",
        "mission": "Provide executive-level oversight for all recruitment events.",
        "allowed_events": ["tracker.updated", "candidate.inactive", "interview.scheduled"],
        "allowed_tools": ["task_system", "decision_aggregator"],
        "allowed_memory_namespaces": ["recruitment", "strategy"],
        "task_types_can_create": ["recommendation", "alert"],
        "task_types_can_resolve": ["recommendation"],
        "disclosure_level": "operator",
        "learning_targets": ["hiring_quality", "pipeline_velocity"],
        "evolution_scope": "decision_rule",
    },
    # --- Recruitment Autopilot Brains ---
    {
        "brain_id": "recruitment_followup_brain",
        "name": "Recruitment Follow-Up Brain",
        "layer": "tool",
        "role": "followup_specialist",
        "mission": "Draft follow-up messages for inactive candidates.",
        "allowed_events": ["candidate.inactive"],
        "allowed_tools": ["task_system", "action_output"],
        "allowed_memory_namespaces": ["recruitment"],
        "task_types_can_create": ["follow_up", "alert"],
        "task_types_can_resolve": ["follow_up"],
        "disclosure_level": "member",
        "learning_targets": ["follow_up_response_rate"],
        "evolution_scope": "template",
    },
    {
        "brain_id": "recruitment_compliance_brain",
        "name": "Recruitment Compliance Brain",
        "layer": "tool",
        "role": "compliance_checker",
        "mission": "Ensure recruitment actions comply with communication policies.",
        "allowed_events": ["candidate.inactive", "candidate.interested"],
        "allowed_tools": ["task_system", "safety"],
        "allowed_memory_namespaces": ["recruitment", "compliance"],
        "task_types_can_create": ["alert"],
        "task_types_can_resolve": ["alert"],
        "disclosure_level": "member",
        "learning_targets": ["compliance_accuracy"],
        "evolution_scope": "decision_rule",
    },
    {
        "brain_id": "recruitment_ack_brain",
        "name": "Recruitment Acknowledgment Brain",
        "layer": "tool",
        "role": "ack_specialist",
        "mission": "Draft acknowledgment messages for interested candidates.",
        "allowed_events": ["candidate.interested"],
        "allowed_tools": ["task_system", "action_output"],
        "allowed_memory_namespaces": ["recruitment"],
        "task_types_can_create": ["draft", "alert"],
        "task_types_can_resolve": ["draft"],
        "disclosure_level": "member",
        "learning_targets": ["ack_timeliness"],
        "evolution_scope": "template",
    },
    {
        "brain_id": "recruitment_tracker_brain",
        "name": "Recruitment Tracker Brain",
        "layer": "tool",
        "role": "tracker_syncer",
        "mission": "Keep tracker records in sync with candidate status changes.",
        "allowed_events": ["candidate.interested", "tracker.updated"],
        "allowed_tools": ["task_system"],
        "allowed_memory_namespaces": ["recruitment"],
        "task_types_can_create": ["status_update"],
        "task_types_can_resolve": ["status_update"],
        "disclosure_level": "member",
        "learning_targets": ["sync_accuracy"],
        "evolution_scope": "workflow",
    },
    {
        "brain_id": "recruitment_status_brain",
        "name": "Recruitment Status Brain",
        "layer": "tool",
        "role": "status_reporter",
        "mission": "Generate daily/weekly recruitment status summaries.",
        "allowed_events": ["status.requested"],
        "allowed_tools": ["task_system"],
        "allowed_memory_namespaces": ["recruitment"],
        "task_types_can_create": ["status_update", "alert"],
        "task_types_can_resolve": ["status_update"],
        "disclosure_level": "member",
        "learning_targets": ["report_usefulness"],
        "evolution_scope": "template",
    },
]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ContractUpdateRequest(BaseModel):
    allowed_events: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None
    task_types_can_create: Optional[List[str]] = None
    task_types_can_resolve: Optional[List[str]] = None
    disclosure_level: Optional[str] = None
    evolution_scope: Optional[str] = None


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_brain_contract_registry_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all  = ctx["db_all"]
    new_id  = ctx["new_id"]
    now_iso = ctx["now_iso"]
    log     = ctx["log"]
    session_user = ctx["session_user"]

    # ------------------------------------------------------------------
    # DB setup
    # ------------------------------------------------------------------

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_contracts (
                brain_id            TEXT PRIMARY KEY,
                name                TEXT NOT NULL DEFAULT '',
                layer               TEXT NOT NULL DEFAULT '',
                role                TEXT NOT NULL DEFAULT '',
                mission             TEXT NOT NULL DEFAULT '',
                allowed_events_json TEXT NOT NULL DEFAULT '[]',
                allowed_tools_json  TEXT NOT NULL DEFAULT '[]',
                allowed_memory_ns_json TEXT NOT NULL DEFAULT '[]',
                task_create_json    TEXT NOT NULL DEFAULT '[]',
                task_resolve_json   TEXT NOT NULL DEFAULT '[]',
                disclosure_level    TEXT NOT NULL DEFAULT 'member',
                learning_targets_json TEXT NOT NULL DEFAULT '[]',
                evolution_scope     TEXT NOT NULL DEFAULT 'none',
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_health_metrics (
                brain_id            TEXT PRIMARY KEY,
                tasks_created       INTEGER NOT NULL DEFAULT 0,
                tasks_resolved      INTEGER NOT NULL DEFAULT 0,
                actions_approved    INTEGER NOT NULL DEFAULT 0,
                actions_rejected    INTEGER NOT NULL DEFAULT 0,
                conflicts_generated INTEGER NOT NULL DEFAULT 0,
                events_processed    INTEGER NOT NULL DEFAULT 0,
                violations          INTEGER NOT NULL DEFAULT 0,
                learning_score      REAL NOT NULL DEFAULT 0.0,
                health_score        REAL NOT NULL DEFAULT 1.0,
                updated_at          TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_contract_violations (
                id          TEXT PRIMARY KEY,
                brain_id    TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                detail_json TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # ------------------------------------------------------------------
    # Seed default contracts
    # ------------------------------------------------------------------

    def _seed_contracts() -> None:
        ts = now_iso()
        for contract in _DEFAULT_CONTRACTS:
            existing = db_all(
                "SELECT brain_id FROM brain_contracts WHERE brain_id=?",
                (contract["brain_id"],),
            )
            if existing:
                continue
            db_exec(
                "INSERT INTO brain_contracts "
                "(brain_id, name, layer, role, mission, allowed_events_json, allowed_tools_json, "
                "allowed_memory_ns_json, task_create_json, task_resolve_json, disclosure_level, "
                "learning_targets_json, evolution_scope, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    contract["brain_id"],
                    contract.get("name", ""),
                    contract.get("layer", ""),
                    contract.get("role", ""),
                    contract.get("mission", ""),
                    json.dumps(contract.get("allowed_events", [])),
                    json.dumps(contract.get("allowed_tools", [])),
                    json.dumps(contract.get("allowed_memory_namespaces", [])),
                    json.dumps(contract.get("task_types_can_create", [])),
                    json.dumps(contract.get("task_types_can_resolve", [])),
                    contract.get("disclosure_level", "member"),
                    json.dumps(contract.get("learning_targets", [])),
                    contract.get("evolution_scope", "none"),
                    ts,
                    ts,
                ),
            )
            # Seed health metrics row
            db_exec(
                "INSERT OR IGNORE INTO brain_health_metrics "
                "(brain_id, tasks_created, tasks_resolved, actions_approved, actions_rejected, "
                "conflicts_generated, events_processed, violations, learning_score, health_score, updated_at) "
                "VALUES (?,0,0,0,0,0,0,0,0.0,1.0,?)",
                (contract["brain_id"], ts),
            )

    try:
        _seed_contracts()
    except Exception as exc:
        log.warning("[BrainContractRegistry] seeding error: %s", exc)

    # ------------------------------------------------------------------
    # Contract lookup
    # ------------------------------------------------------------------

    def _row_to_contract(r) -> Dict[str, Any]:
        return {
            "brain_id": r[0],
            "name": r[1],
            "layer": r[2],
            "role": r[3],
            "mission": r[4],
            "allowed_events": json.loads(r[5] or "[]"),
            "allowed_tools": json.loads(r[6] or "[]"),
            "allowed_memory_namespaces": json.loads(r[7] or "[]"),
            "task_types_can_create": json.loads(r[8] or "[]"),
            "task_types_can_resolve": json.loads(r[9] or "[]"),
            "disclosure_level": r[10],
            "learning_targets": json.loads(r[11] or "[]"),
            "evolution_scope": r[12],
            "created_at": r[13],
            "updated_at": r[14],
        }

    def get_contract(brain_id: str) -> Optional[Dict[str, Any]]:
        rows = db_all(
            "SELECT brain_id, name, layer, role, mission, allowed_events_json, allowed_tools_json, "
            "allowed_memory_ns_json, task_create_json, task_resolve_json, disclosure_level, "
            "learning_targets_json, evolution_scope, created_at, updated_at "
            "FROM brain_contracts WHERE brain_id=?",
            (brain_id,),
        )
        return _row_to_contract(rows[0]) if rows else None

    def list_contracts() -> List[Dict[str, Any]]:
        rows = db_all(
            "SELECT brain_id, name, layer, role, mission, allowed_events_json, allowed_tools_json, "
            "allowed_memory_ns_json, task_create_json, task_resolve_json, disclosure_level, "
            "learning_targets_json, evolution_scope, created_at, updated_at "
            "FROM brain_contracts ORDER BY layer, brain_id",
        ) or []
        return [_row_to_contract(r) for r in rows]

    # ------------------------------------------------------------------
    # Contract enforcement
    # ------------------------------------------------------------------

    def check_event_allowed(brain_id: str, event_type: str) -> bool:
        """Return True if *brain_id* is allowed to process *event_type*."""
        contract = get_contract(brain_id)
        if not contract:
            return True  # no contract = unrestricted (backwards compat)
        allowed = contract.get("allowed_events", [])
        if "*" in allowed:
            return True
        return event_type in allowed

    def check_task_create_allowed(brain_id: str, task_type: str) -> bool:
        """Return True if *brain_id* is allowed to create *task_type*."""
        contract = get_contract(brain_id)
        if not contract:
            return True
        allowed = contract.get("task_types_can_create", [])
        if "*" in allowed:
            return True
        return task_type in allowed

    def check_task_resolve_allowed(brain_id: str, task_type: str) -> bool:
        """Return True if *brain_id* is allowed to resolve *task_type*."""
        contract = get_contract(brain_id)
        if not contract:
            return True
        allowed = contract.get("task_types_can_resolve", [])
        if "*" in allowed:
            return True
        return task_type in allowed

    # ------------------------------------------------------------------
    # Violation logging
    # ------------------------------------------------------------------

    def log_violation(brain_id: str, violation_type: str, detail: Optional[Dict[str, Any]] = None) -> None:
        vid = new_id("cviol")
        ts = now_iso()
        db_exec(
            "INSERT INTO brain_contract_violations (id, brain_id, violation_type, detail_json, created_at) "
            "VALUES (?,?,?,?,?)",
            (vid, brain_id, violation_type, json.dumps(detail or {}), ts),
        )
        # Increment violation counter in health metrics
        db_exec(
            "UPDATE brain_health_metrics SET violations = violations + 1, updated_at=? WHERE brain_id=?",
            (ts, brain_id),
        )
        log.warning("[BrainContractRegistry] VIOLATION brain=%s type=%s detail=%s", brain_id, violation_type, detail)

    # ------------------------------------------------------------------
    # Health metrics
    # ------------------------------------------------------------------

    def _health_row_to_dict(r) -> Dict[str, Any]:
        return {
            "brain_id": r[0],
            "tasks_created": r[1],
            "tasks_resolved": r[2],
            "actions_approved": r[3],
            "actions_rejected": r[4],
            "conflicts_generated": r[5],
            "events_processed": r[6],
            "violations": r[7],
            "learning_score": round(float(r[8] or 0), 3),
            "health_score": round(float(r[9] or 1), 3),
            "updated_at": r[10],
        }

    def get_health(brain_id: str) -> Optional[Dict[str, Any]]:
        rows = db_all(
            "SELECT brain_id, tasks_created, tasks_resolved, actions_approved, actions_rejected, "
            "conflicts_generated, events_processed, violations, learning_score, health_score, updated_at "
            "FROM brain_health_metrics WHERE brain_id=?",
            (brain_id,),
        )
        return _health_row_to_dict(rows[0]) if rows else None

    def list_health() -> List[Dict[str, Any]]:
        rows = db_all(
            "SELECT brain_id, tasks_created, tasks_resolved, actions_approved, actions_rejected, "
            "conflicts_generated, events_processed, violations, learning_score, health_score, updated_at "
            "FROM brain_health_metrics ORDER BY health_score DESC",
        ) or []
        return [_health_row_to_dict(r) for r in rows]

    def record_metric(brain_id: str, metric: str, increment: int = 1) -> None:
        """Increment a metric counter for *brain_id*.

        Valid metrics: tasks_created, tasks_resolved, actions_approved,
        actions_rejected, conflicts_generated, events_processed.
        """
        valid_metrics = {
            "tasks_created", "tasks_resolved", "actions_approved",
            "actions_rejected", "conflicts_generated", "events_processed",
        }
        if metric not in valid_metrics:
            return
        ts = now_iso()
        # Ensure row exists
        existing = db_all("SELECT brain_id FROM brain_health_metrics WHERE brain_id=?", (brain_id,))
        if not existing:
            db_exec(
                "INSERT INTO brain_health_metrics "
                "(brain_id, tasks_created, tasks_resolved, actions_approved, actions_rejected, "
                "conflicts_generated, events_processed, violations, learning_score, health_score, updated_at) "
                "VALUES (?,0,0,0,0,0,0,0,0.0,1.0,?)",
                (brain_id, ts),
            )
        # Use pre-built queries keyed by validated metric name to avoid f-string SQL
        _METRIC_QUERIES = {
            "tasks_created":       "UPDATE brain_health_metrics SET tasks_created = tasks_created + ?, updated_at=? WHERE brain_id=?",
            "tasks_resolved":      "UPDATE brain_health_metrics SET tasks_resolved = tasks_resolved + ?, updated_at=? WHERE brain_id=?",
            "actions_approved":    "UPDATE brain_health_metrics SET actions_approved = actions_approved + ?, updated_at=? WHERE brain_id=?",
            "actions_rejected":    "UPDATE brain_health_metrics SET actions_rejected = actions_rejected + ?, updated_at=? WHERE brain_id=?",
            "conflicts_generated": "UPDATE brain_health_metrics SET conflicts_generated = conflicts_generated + ?, updated_at=? WHERE brain_id=?",
            "events_processed":    "UPDATE brain_health_metrics SET events_processed = events_processed + ?, updated_at=? WHERE brain_id=?",
        }
        db_exec(_METRIC_QUERIES[metric], (increment, ts, brain_id))
        # Recompute health score
        _recompute_health(brain_id)

    def _recompute_health(brain_id: str) -> None:
        """Recompute health_score and learning_score based on metrics."""
        rows = db_all(
            "SELECT tasks_created, tasks_resolved, actions_approved, actions_rejected, "
            "conflicts_generated, events_processed, violations "
            "FROM brain_health_metrics WHERE brain_id=?",
            (brain_id,),
        )
        if not rows:
            return
        r = rows[0]
        created = r[0] or 0
        resolved = r[1] or 0
        approved = r[2] or 0
        rejected = r[3] or 0
        conflicts = r[4] or 0
        processed = r[5] or 0
        violations = r[6] or 0

        # Learning score: ratio of resolved + approved to total activity
        total_activity = created + resolved + approved + rejected + 1
        learning = min(1.0, (resolved + approved) / total_activity)

        # Health score: penalty for rejections, conflicts, violations
        health = 1.0
        if total_activity > 1:
            health -= min(0.3, rejected / total_activity * 0.5)
            health -= min(0.2, conflicts / total_activity * 0.3)
            health -= min(0.3, violations / max(total_activity, 1) * 0.5)
        health = max(0.0, min(1.0, health))

        ts = now_iso()
        db_exec(
            "UPDATE brain_health_metrics SET learning_score=?, health_score=?, updated_at=? WHERE brain_id=?",
            (round(learning, 3), round(health, 3), ts, brain_id),
        )

    # ------------------------------------------------------------------
    # REST APIs
    # ------------------------------------------------------------------

    @app.get("/api/brain-contracts")
    async def api_list_contracts(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        contracts = list_contracts()
        return {"ok": True, "contracts": contracts}

    @app.get("/api/brain-contracts/{brain_id}")
    async def api_get_contract(brain_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        contract = get_contract(brain_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        health = get_health(brain_id)
        return {"ok": True, "contract": contract, "health": health}

    @app.put("/api/brain-contracts/{brain_id}")
    async def api_update_contract(brain_id: str, body: ContractUpdateRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")

        contract = get_contract(brain_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        ts = now_iso()
        updates: List[str] = []
        params: List[Any] = []

        if body.allowed_events is not None:
            updates.append("allowed_events_json=?")
            params.append(json.dumps(body.allowed_events))
        if body.allowed_tools is not None:
            updates.append("allowed_tools_json=?")
            params.append(json.dumps(body.allowed_tools))
        if body.task_types_can_create is not None:
            updates.append("task_create_json=?")
            params.append(json.dumps(body.task_types_can_create))
        if body.task_types_can_resolve is not None:
            updates.append("task_resolve_json=?")
            params.append(json.dumps(body.task_types_can_resolve))
        if body.disclosure_level is not None:
            updates.append("disclosure_level=?")
            params.append(body.disclosure_level)
        if body.evolution_scope is not None:
            updates.append("evolution_scope=?")
            params.append(body.evolution_scope)

        if updates:
            updates.append("updated_at=?")
            params.append(ts)
            params.append(brain_id)
            db_exec(
                f"UPDATE brain_contracts SET {', '.join(updates)} WHERE brain_id=?",
                tuple(params),
            )

        return {"ok": True, "contract": get_contract(brain_id)}

    @app.get("/api/brain-contracts/health/all")
    async def api_all_health(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"ok": True, "health": list_health()}

    @app.get("/api/brain-contracts/{brain_id}/health")
    async def api_brain_health(brain_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        health = get_health(brain_id)
        if not health:
            raise HTTPException(status_code=404, detail="Health record not found")
        return {"ok": True, "health": health}

    @app.get("/api/brain-contracts/violations/recent")
    async def api_recent_violations(request: Request, limit: int = 50):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        rows = db_all(
            "SELECT id, brain_id, violation_type, detail_json, created_at "
            "FROM brain_contract_violations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) or []
        return {
            "ok": True,
            "violations": [
                {
                    "id": r[0],
                    "brain_id": r[1],
                    "violation_type": r[2],
                    "detail": json.loads(r[3] or "{}"),
                    "created_at": r[4],
                }
                for r in rows
            ],
        }

    # ------------------------------------------------------------------
    # Export to ctx
    # ------------------------------------------------------------------

    ctx["contract_get"] = get_contract
    ctx["contract_list"] = list_contracts
    ctx["contract_check_event"] = check_event_allowed
    ctx["contract_check_task_create"] = check_task_create_allowed
    ctx["contract_check_task_resolve"] = check_task_resolve_allowed
    ctx["contract_log_violation"] = log_violation
    ctx["contract_record_metric"] = record_metric
    ctx["contract_get_health"] = get_health
    ctx["contract_list_health"] = list_health

    log.info("[BrainContractRegistry] layer installed — %d contracts seeded", len(_DEFAULT_CONTRACTS))
    return ctx
