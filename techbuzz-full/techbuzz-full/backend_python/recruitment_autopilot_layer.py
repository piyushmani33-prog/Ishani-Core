"""
Recruitment Autopilot Layer — End-to-end recruiter workflows using
the full brain coordination stack.

Three loops run through the entire pipeline:
  1. Follow-Up Loop   (candidate.inactive)
  2. Acknowledgment Loop (candidate.interested)
  3. Daily Status Loop   (status.requested)

Each loop:
  • Publishes an event on the event bus
  • Brains react independently and create tasks
  • Aggregator merges / resolves conflicts
  • Action output creates drafts
  • Disclosure gate filters for user display
  • Human approves / rejects / copies
  • Learning engine records outcome
  • Evolution layer proposes improvements (where appropriate)

No auto-send — every user-facing action needs explicit approval.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class FollowUpRequest(BaseModel):
    candidate_name: str
    position: str = ""
    row_id: str = ""
    reason: str = "No response within expected window"


class AcknowledgmentRequest(BaseModel):
    candidate_name: str
    position: str = ""
    row_id: str = ""
    email: str = ""


class StatusRequest(BaseModel):
    scope: str = "daily"          # daily | weekly
    format: str = "summary"       # summary | sheet | both


class WorkflowActionRequest(BaseModel):
    action: str                   # approve | reject | copy | edit
    edited_content: str = ""


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_recruitment_autopilot_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    log = ctx["log"]

    # Layer helpers from ctx (set by earlier layers)
    event_bus_publish = ctx.get("event_bus_publish")
    register_brain_handler = ctx.get("register_brain_handler")
    task_create = ctx.get("task_create")
    aggregator_run = ctx.get("aggregator_run")
    action_create_from_task = ctx.get("action_create_from_task")
    disclosure_filter = ctx.get("disclosure_filter_output")
    learning_record_signal = ctx.get("learning_record_signal")
    evolution_submit_proposal = ctx.get("evolution_submit_proposal")
    memory_set = ctx.get("memory_set")

    # -----------------------------------------------------------------------
    # DB setup — autopilot-specific tracking
    # -----------------------------------------------------------------------

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_autopilot_runs (
                id           TEXT PRIMARY KEY,
                workflow     TEXT NOT NULL,
                event_id     TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'running',
                summary_json TEXT NOT NULL DEFAULT '{}',
                created_at   TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Brain handlers — registered on the brain executor via event bus
    # -----------------------------------------------------------------------

    def _follow_up_brain_handler(event: Dict[str, Any]) -> None:
        """Recruitment follow-up brain: creates a follow_up draft task."""
        if task_create is None:
            return
        payload = event.get("payload", {})
        candidate = payload.get("candidate_name", "Candidate")
        position = payload.get("position", "open role")
        task_create(
            brain_id="recruitment_followup_brain",
            event_id=event.get("event_id", ""),
            task_type="follow_up",
            input_data=payload,
            output_data={
                "message": f"Follow-up recommended for {candidate} ({position}). Draft a follow-up message reminding the candidate of the opportunity and asking for their current status.",
                "action": "send_followup",
                "candidate_name": candidate,
                "position": position,
                "draft": f"Hi {candidate},\n\nI wanted to follow up regarding the {position} position. We haven't heard back from you and would love to know if you're still interested.\n\nPlease let us know your availability for a quick chat.\n\nBest regards",
            },
            priority=3,
        )

    def _follow_up_compliance_handler(event: Dict[str, Any]) -> None:
        """Compliance brain: checks follow-up frequency limits."""
        if task_create is None:
            return
        payload = event.get("payload", {})
        candidate = payload.get("candidate_name", "Candidate")
        task_create(
            brain_id="recruitment_compliance_brain",
            event_id=event.get("event_id", ""),
            task_type="alert",
            input_data=payload,
            output_data={
                "message": f"Compliance check: Ensure follow-up for {candidate} respects communication frequency limits. Max 3 follow-ups per candidate per week.",
                "action": "compliance_check",
            },
            priority=5,
        )

    def _ack_brain_handler(event: Dict[str, Any]) -> None:
        """Acknowledgment brain: prepares ack draft."""
        if task_create is None:
            return
        payload = event.get("payload", {})
        candidate = payload.get("candidate_name", "Candidate")
        position = payload.get("position", "open role")
        email = payload.get("email", "")
        task_create(
            brain_id="recruitment_ack_brain",
            event_id=event.get("event_id", ""),
            task_type="draft",
            input_data=payload,
            output_data={
                "message": f"Acknowledgment draft prepared for {candidate} ({position}).",
                "action": "send_acknowledgment",
                "candidate_name": candidate,
                "position": position,
                "email": email,
                "draft": f"Dear {candidate},\n\nThank you for expressing interest in the {position} position. We have received your application and our team is reviewing it.\n\nWe will get back to you within the next few business days with an update on next steps.\n\nBest regards",
            },
            priority=2,
        )

    def _ack_tracker_handler(event: Dict[str, Any]) -> None:
        """Tracker brain: updates candidate status on acknowledgment."""
        if task_create is None:
            return
        payload = event.get("payload", {})
        candidate = payload.get("candidate_name", "Candidate")
        task_create(
            brain_id="recruitment_tracker_brain",
            event_id=event.get("event_id", ""),
            task_type="status_update",
            input_data=payload,
            output_data={
                "message": f"Tracker updated: {candidate} marked as 'acknowledged'. Process stage moved to screening.",
                "action": "update_tracker",
                "new_status": "acknowledged",
            },
            priority=4,
        )

    def _status_brain_handler(event: Dict[str, Any]) -> None:
        """Status brain: produces recruitment status summary."""
        if task_create is None:
            return
        payload = event.get("payload", {})
        scope = payload.get("scope", "daily")
        fmt = payload.get("format", "summary")

        # Build summary from available tracker data (safe: table may not exist yet)
        total = active = pending = interested = 0
        try:
            total_rows = db_all("SELECT COUNT(*) FROM recruitment_tracker_rows") or []
            total = total_rows[0][0] if total_rows and total_rows[0] else 0

            active_rows = db_all("SELECT COUNT(*) FROM recruitment_tracker_rows WHERE response_status NOT IN ('rejected','dropped','ghosted')") or []
            active = active_rows[0][0] if active_rows and active_rows[0] else 0

            pending_rows = db_all("SELECT COUNT(*) FROM recruitment_tracker_rows WHERE response_status IN ('pending_review','no_response')") or []
            pending = pending_rows[0][0] if pending_rows and pending_rows[0] else 0

            interested_rows = db_all("SELECT COUNT(*) FROM recruitment_tracker_rows WHERE response_status='interested'") or []
            interested = interested_rows[0][0] if interested_rows and interested_rows[0] else 0
        except Exception:
            pass  # Table may not exist; proceed with zero counts

        summary_text = (
            f"Recruitment {scope.title()} Status:\n"
            f"- Total candidates tracked: {total}\n"
            f"- Active pipeline: {active}\n"
            f"- Pending response: {pending}\n"
            f"- Interested: {interested}\n"
            f"- Format: {fmt}"
        )

        output_data: Dict[str, Any] = {
            "message": summary_text,
            "action": "display_status",
            "scope": scope,
            "format": fmt,
            "stats": {
                "total": total,
                "active": active,
                "pending": pending,
                "interested": interested,
            },
        }

        # If sheet format requested, add CSV-style output
        if fmt in ("sheet", "both"):
            try:
                rows = db_all(
                    "SELECT candidate_name, position, response_status, process_stage, updated_at "
                    "FROM recruitment_tracker_rows ORDER BY updated_at DESC LIMIT 50"
                ) or []
            except Exception:
                rows = []
            sheet_lines = ["Candidate,Position,Status,Stage,Updated"]
            for r in rows:
                sheet_lines.append(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]}")
            output_data["sheet_csv"] = "\n".join(sheet_lines)

        task_create(
            brain_id="recruitment_status_brain",
            event_id=event.get("event_id", ""),
            task_type="status_update",
            input_data=payload,
            output_data=output_data,
            priority=4,
        )

    # -----------------------------------------------------------------------
    # Register brain handlers on the bus
    # -----------------------------------------------------------------------

    if register_brain_handler:
        register_brain_handler(
            "recruitment_followup_brain",
            ["candidate.inactive"],
            _follow_up_brain_handler,
            description="Recruitment follow-up draft generator",
        )
        register_brain_handler(
            "recruitment_compliance_brain",
            ["candidate.inactive"],
            _follow_up_compliance_handler,
            description="Recruitment compliance checker for follow-ups",
        )
        register_brain_handler(
            "recruitment_ack_brain",
            ["candidate.interested"],
            _ack_brain_handler,
            description="Recruitment acknowledgment draft generator",
        )
        register_brain_handler(
            "recruitment_tracker_brain",
            ["candidate.interested"],
            _ack_tracker_handler,
            description="Recruitment tracker updater on acknowledgment",
        )
        register_brain_handler(
            "recruitment_status_brain",
            ["status.requested"],
            _status_brain_handler,
            description="Recruitment daily/weekly status summariser",
        )

    # -----------------------------------------------------------------------
    # Pipeline runner — executes the full loop for a given workflow
    # -----------------------------------------------------------------------

    async def _run_pipeline(
        workflow: str,
        event_type: str,
        payload: Dict[str, Any],
        user_role: str = "member",
    ) -> Dict[str, Any]:
        """Execute the complete pipeline: publish → aggregate → actions → disclose."""
        run_id = new_id("aprun")
        created_at = now_iso()

        # 1. Publish event (triggers all subscribed brains)
        event = {}
        if event_bus_publish:
            event = await event_bus_publish(event_type, payload, source_brain="recruitment_autopilot")
        event_id = event.get("event_id", "")

        # 2. Run aggregator on the event's tasks
        aggregation = {}
        if aggregator_run and event_id:
            aggregation = aggregator_run(event_id)

        # 3. Create action drafts from final_actions
        actions_created: List[Dict[str, Any]] = []
        final_actions = aggregation.get("final_actions", [])
        if action_create_from_task:
            for task in final_actions:
                action = action_create_from_task(task)
                actions_created.append(action)

        # 4. Apply disclosure gate to each action
        filtered_actions: List[Dict[str, Any]] = []
        for action in actions_created:
            if disclosure_filter:
                filtered = disclosure_filter(
                    action.get("content", action),
                    user_role=user_role,
                    context=f"recruitment_{workflow}",
                )
                filtered_action = dict(action)
                filtered_action["content"] = filtered
                filtered_actions.append(filtered_action)
            else:
                filtered_actions.append(action)

        # 5. Update shared memory with run info
        if memory_set:
            memory_set(
                "tracker",
                f"autopilot:{workflow}:latest_run",
                {
                    "run_id": run_id,
                    "event_id": event_id,
                    "actions_count": len(filtered_actions),
                    "at": created_at,
                },
                updated_by="recruitment_autopilot",
            )

        # 6. Persist autopilot run record
        summary = {
            "event_id": event_id,
            "aggregation_id": aggregation.get("id", ""),
            "merged_count": len(aggregation.get("merged_tasks", [])),
            "conflict_count": len(aggregation.get("conflicts", [])),
            "actions_count": len(filtered_actions),
            "action_ids": [a["id"] for a in filtered_actions],
        }
        db_exec(
            "INSERT INTO recruitment_autopilot_runs (id, workflow, event_id, status, summary_json, created_at) VALUES (?,?,?,?,?,?)",
            (run_id, workflow, event_id, "awaiting_approval", json.dumps(summary), created_at),
        )

        log.info(
            "[RecruitmentAutopilot] %s pipeline completed: run=%s event=%s actions=%d",
            workflow, run_id, event_id, len(filtered_actions),
        )

        return {
            "run_id": run_id,
            "workflow": workflow,
            "event_id": event_id,
            "aggregation": {
                "id": aggregation.get("id", ""),
                "merged_count": len(aggregation.get("merged_tasks", [])),
                "conflict_count": len(aggregation.get("conflicts", [])),
            },
            "actions": filtered_actions,
            "status": "awaiting_approval",
            "created_at": created_at,
        }

    # -----------------------------------------------------------------------
    # Workflow action handler (approve/reject/copy/edit)
    # -----------------------------------------------------------------------

    def _handle_workflow_action(
        run_id: str,
        action_id: str,
        user_action: str,
        edited_content: str = "",
        user_role: str = "member",
    ) -> Dict[str, Any]:
        """Process a user's decision on a workflow action draft."""

        # Record learning signal
        signal_map = {
            "approve": "action_approved",
            "reject": "action_rejected",
            "copy": "action_executed",
            "edit": "user_edit",
        }
        signal_type = signal_map.get(user_action, "feedback")

        detail: Dict[str, Any] = {"run_id": run_id, "action_id": action_id, "user_action": user_action}
        if edited_content:
            detail["edited_content"] = edited_content[:2000]

        if learning_record_signal:
            learning_record_signal(
                signal_type=signal_type,
                source_brain="recruitment_autopilot",
                entity_type="action",
                entity_id=action_id,
                detail=detail,
            )

        # Update action status in DB
        if user_action == "approve":
            db_exec("UPDATE action_drafts SET status='approved' WHERE id=?", (action_id,))
        elif user_action == "reject":
            db_exec("UPDATE action_drafts SET status='dismissed' WHERE id=?", (action_id,))
        elif user_action == "copy":
            db_exec("UPDATE action_drafts SET status='executed' WHERE id=?", (action_id,))
        elif user_action == "edit":
            # Store edited version in content
            rows = db_all("SELECT content_json FROM action_drafts WHERE id=?", (action_id,))
            if rows:
                content = json.loads(rows[0][0] or "{}")
                content["user_edited_draft"] = edited_content[:2000]
                db_exec(
                    "UPDATE action_drafts SET content_json=?, status='approved' WHERE id=?",
                    (json.dumps(content), action_id),
                )

        # Check if all actions in run are resolved
        run_rows = db_all("SELECT summary_json FROM recruitment_autopilot_runs WHERE id=?", (run_id,))
        if run_rows:
            summary = json.loads(run_rows[0][0] or "{}")
            action_ids = summary.get("action_ids", [])
            if action_ids:
                placeholders = ",".join("?" for _ in action_ids)
                status_rows = db_all(
                    f"SELECT status FROM action_drafts WHERE id IN ({placeholders})",
                    tuple(action_ids),
                )
                all_resolved = all(r[0] in ("approved", "executed", "dismissed") for r in status_rows) if status_rows else False
                if all_resolved:
                    db_exec(
                        "UPDATE recruitment_autopilot_runs SET status='completed', completed_at=? WHERE id=?",
                        (now_iso(), run_id),
                    )

        # Propose evolution improvement after repeated rejections
        if user_action == "reject" and evolution_submit_proposal:
            # Count recent rejections for this workflow
            rejection_count_rows = db_all(
                "SELECT COUNT(*) FROM learning_signals WHERE signal_type='action_rejected' AND source_brain='recruitment_autopilot' AND created_at > datetime('now', '-7 days')"
            ) or []
            rejection_count = rejection_count_rows[0][0] if rejection_count_rows and rejection_count_rows[0] else 0
            if rejection_count >= 3:
                evolution_submit_proposal(
                    source_brain="recruitment_autopilot",
                    category="template",
                    title="Follow-up/acknowledgment templates may need refinement",
                    description=f"There have been {rejection_count} rejections of recruitment autopilot drafts in the past 7 days. The templates used for follow-up and acknowledgment messages may need updating to better match recruiter preferences.",
                    evidence={"rejection_count_7d": rejection_count},
                    priority=4,
                )

        return {"ok": True, "action_id": action_id, "user_action": user_action, "signal_type": signal_type}

    # -----------------------------------------------------------------------
    # REST APIs — Workflow triggers
    # -----------------------------------------------------------------------

    @app.post("/api/recruitment/autopilot/follow-up")
    async def api_followup_loop(body: FollowUpRequest, request: Request):
        """Trigger the Follow-Up Loop for an inactive candidate."""
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        result = await _run_pipeline(
            workflow="follow_up",
            event_type="candidate.inactive",
            payload={
                "candidate_name": body.candidate_name,
                "position": body.position,
                "row_id": body.row_id,
                "reason": body.reason,
            },
            user_role=user.get("role", "member"),
        )
        return {"ok": True, "result": result}

    @app.post("/api/recruitment/autopilot/acknowledgment")
    async def api_ack_loop(body: AcknowledgmentRequest, request: Request):
        """Trigger the Acknowledgment Loop for an interested candidate."""
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        result = await _run_pipeline(
            workflow="acknowledgment",
            event_type="candidate.interested",
            payload={
                "candidate_name": body.candidate_name,
                "position": body.position,
                "row_id": body.row_id,
                "email": body.email,
            },
            user_role=user.get("role", "member"),
        )
        return {"ok": True, "result": result}

    @app.post("/api/recruitment/autopilot/status")
    async def api_status_loop(body: StatusRequest, request: Request):
        """Trigger the Daily Status Loop."""
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        result = await _run_pipeline(
            workflow="daily_status",
            event_type="status.requested",
            payload={
                "scope": body.scope,
                "format": body.format,
            },
            user_role=user.get("role", "member"),
        )

        # Record format preference in learning engine
        if learning_record_signal:
            learning_record_signal(
                signal_type="feedback",
                source_brain="recruitment_autopilot",
                entity_type="status_format",
                entity_id=body.format,
                detail={"scope": body.scope, "format": body.format},
            )

        return {"ok": True, "result": result}

    # -----------------------------------------------------------------------
    # REST API — Action approval/rejection for workflow outputs
    # -----------------------------------------------------------------------

    @app.post("/api/recruitment/autopilot/runs/{run_id}/actions/{action_id}")
    async def api_workflow_action(run_id: str, action_id: str, body: WorkflowActionRequest, request: Request):
        """Approve, reject, copy, or edit a workflow action draft."""
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        if body.action not in ("approve", "reject", "copy", "edit"):
            raise HTTPException(status_code=400, detail="action must be approve, reject, copy, or edit")

        result = _handle_workflow_action(
            run_id=run_id,
            action_id=action_id,
            user_action=body.action,
            edited_content=body.edited_content,
            user_role=user.get("role", "member"),
        )
        return result

    # -----------------------------------------------------------------------
    # REST API — List / view autopilot runs
    # -----------------------------------------------------------------------

    @app.get("/api/recruitment/autopilot/runs")
    async def api_list_runs(request: Request, workflow: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        conditions: List[str] = []
        params: List[Any] = []
        if workflow:
            conditions.append("workflow=?")
            params.append(workflow)
        if status:
            conditions.append("status=?")
            params.append(status)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)

        rows = db_all(
            f"SELECT id, workflow, event_id, status, summary_json, created_at, completed_at FROM recruitment_autopilot_runs {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return {
            "ok": True,
            "runs": [
                {
                    "id": r[0],
                    "workflow": r[1],
                    "event_id": r[2],
                    "status": r[3],
                    "summary": json.loads(r[4] or "{}"),
                    "created_at": r[5],
                    "completed_at": r[6],
                }
                for r in rows
            ],
        }

    @app.get("/api/recruitment/autopilot/runs/{run_id}")
    async def api_get_run(run_id: str, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        rows = db_all(
            "SELECT id, workflow, event_id, status, summary_json, created_at, completed_at FROM recruitment_autopilot_runs WHERE id=?",
            (run_id,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Run not found")
        r = rows[0]
        run_data = {
            "id": r[0],
            "workflow": r[1],
            "event_id": r[2],
            "status": r[3],
            "summary": json.loads(r[4] or "{}"),
            "created_at": r[5],
            "completed_at": r[6],
        }

        # Fetch associated actions
        action_ids = run_data["summary"].get("action_ids", [])
        actions = []
        for aid in action_ids:
            action_rows = db_all(
                "SELECT id, task_id, action_type, content_json, status, created_at, executed_at FROM action_drafts WHERE id=?",
                (aid,),
            )
            if action_rows:
                ar = action_rows[0]
                action_data = {
                    "id": ar[0],
                    "task_id": ar[1],
                    "action_type": ar[2],
                    "content": json.loads(ar[3] or "{}"),
                    "status": ar[4],
                    "created_at": ar[5],
                    "executed_at": ar[6],
                }
                # Apply disclosure filtering
                if disclosure_filter:
                    action_data["content"] = disclosure_filter(
                        action_data["content"],
                        user_role=user.get("role", "member"),
                        context="recruitment_autopilot_action",
                    )
                actions.append(action_data)

        run_data["actions"] = actions
        return {"ok": True, "run": run_data}

    # -----------------------------------------------------------------------
    # REST API — Summary stats for autopilot
    # -----------------------------------------------------------------------

    @app.get("/api/recruitment/autopilot/stats")
    async def api_autopilot_stats(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        total_rows = db_all("SELECT COUNT(*) FROM recruitment_autopilot_runs") or []
        total = total_rows[0][0] if total_rows and total_rows[0] else 0

        by_workflow = db_all(
            "SELECT workflow, COUNT(*) as cnt FROM recruitment_autopilot_runs GROUP BY workflow ORDER BY cnt DESC"
        ) or []

        by_status = db_all(
            "SELECT status, COUNT(*) as cnt FROM recruitment_autopilot_runs GROUP BY status ORDER BY cnt DESC"
        ) or []

        return {
            "ok": True,
            "stats": {
                "total_runs": total,
                "by_workflow": {r[0]: r[1] for r in by_workflow},
                "by_status": {r[0]: r[1] for r in by_status},
            },
        }

    # Export to ctx
    ctx["autopilot_run_pipeline"] = _run_pipeline
    ctx["autopilot_handle_action"] = _handle_workflow_action

    log.info("[RecruitmentAutopilot] layer installed — follow_up, acknowledgment, daily_status loops active")
    return ctx
