"""Prompt Adaptation Layer — Learning-to-Prompt system for Ishani Mind.

Tracks real usage outcomes to generate data-driven improvement proposals for
brain prompts and doctrine packs. All prompt changes are human-reviewed
(never auto-applied).

Tables created:
  prompt_outcome_log       — tracks outcome of each LLM call
  prompt_variants          — stores prompt variants per brain
  prompt_proposals         — human-reviewable improvement proposals
  doctrine_effectiveness   — aggregated doctrine performance data

API endpoints added:
  POST /api/brain/prompt-outcome
  POST /api/brain/prompt-variants
  GET  /api/brain/prompt-variants/{brain_id}
  POST /api/brain/prompt-variants/{variant_id}/activate
  DELETE /api/brain/prompt-variants/{variant_id}
  POST /api/brain/prompt-recommendations/{brain_id}
  GET  /api/brain/prompt-proposals
  POST /api/brain/prompt-proposals/{proposal_id}/review
  GET  /api/brain/prompt-performance
  GET  /api/brain/prompt-performance/{brain_id}
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

from brain_prompt_registry import (
    BRAIN_REGISTRY,
    list_all_brain_ids,
    list_all_doctrine_keys,
    get_brain_profile,
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class OutcomeRequest(BaseModel):
    brain_id: str
    outcome: str  # approved | rejected | edited | copied | ignored | fallback | pending
    llm_log_id: str = ""
    prompt_hash: str = ""
    doctrine_keys: List[str] = []
    latency_ms: int = 0
    token_count: int = 0
    trust_delta: float = 0.0
    feedback_text: str = ""


class CreateVariantRequest(BaseModel):
    brain_id: str
    variant_label: str
    system_prompt: str = ""
    doctrine_keys: List[str] = []
    tone: str = ""
    style: str = ""


class ProposalReviewRequest(BaseModel):
    action: str  # accept | reject


# ---------------------------------------------------------------------------
# Installer
# ---------------------------------------------------------------------------

def install_prompt_adaptation_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    db_one = ctx["db_one"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    log = ctx.get("log")

    # Optional ctx values from brain_prompt_layer
    get_brain_profile_fn = ctx.get("get_brain_profile", get_brain_profile)

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS prompt_outcome_log(
                id TEXT PRIMARY KEY,
                llm_log_id TEXT NOT NULL DEFAULT '',
                brain_id TEXT NOT NULL,
                prompt_hash TEXT NOT NULL DEFAULT '',
                doctrine_keys_json TEXT NOT NULL DEFAULT '[]',
                outcome TEXT NOT NULL DEFAULT 'pending',
                latency_ms INTEGER NOT NULL DEFAULT 0,
                token_count INTEGER NOT NULL DEFAULT 0,
                trust_delta REAL NOT NULL DEFAULT 0.0,
                feedback_text TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS prompt_variants(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL,
                variant_label TEXT NOT NULL DEFAULT 'default',
                system_prompt TEXT NOT NULL DEFAULT '',
                doctrine_keys_json TEXT NOT NULL DEFAULT '[]',
                tone TEXT NOT NULL DEFAULT '',
                style TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 0,
                total_calls INTEGER NOT NULL DEFAULT 0,
                total_approvals INTEGER NOT NULL DEFAULT 0,
                total_rejections INTEGER NOT NULL DEFAULT 0,
                avg_latency_ms REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT ''
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS prompt_proposals(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL,
                proposal_type TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                current_value TEXT NOT NULL DEFAULT '',
                proposed_value TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.0,
                evidence_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS doctrine_effectiveness(
                id TEXT PRIMARY KEY,
                doctrine_key TEXT NOT NULL,
                brain_id TEXT NOT NULL DEFAULT '',
                total_calls INTEGER NOT NULL DEFAULT 0,
                approvals INTEGER NOT NULL DEFAULT 0,
                rejections INTEGER NOT NULL DEFAULT 0,
                edits INTEGER NOT NULL DEFAULT 0,
                avg_latency_ms REAL NOT NULL DEFAULT 0.0,
                effectiveness_score REAL NOT NULL DEFAULT 0.0,
                last_updated_at TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def require_master(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user or user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master access required")
        return user

    def require_user(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        return user

    def _compute_effectiveness(approvals: int, rejections: int, edits: int) -> float:
        denom = approvals + rejections + edits
        if denom == 0:
            return 0.0
        return round(approvals / denom, 4)

    def _upsert_doctrine_effectiveness(
        doctrine_key: str,
        brain_id: str,
        outcome: str,
        latency_ms: int,
    ) -> None:
        """Update or insert a doctrine_effectiveness row for the given key+brain."""
        row = db_one(
            "SELECT * FROM doctrine_effectiveness WHERE doctrine_key=? AND brain_id=?",
            (doctrine_key, brain_id),
        )
        ts = now_iso()
        if row is None:
            approvals = 1 if outcome == "approved" else 0
            rejections = 1 if outcome == "rejected" else 0
            edits = 1 if outcome == "edited" else 0
            score = _compute_effectiveness(approvals, rejections, edits)
            db_exec(
                """
                INSERT INTO doctrine_effectiveness(id, doctrine_key, brain_id, total_calls, approvals, rejections, edits, avg_latency_ms, effectiveness_score, last_updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_id("de"),
                    doctrine_key,
                    brain_id,
                    1,
                    approvals,
                    rejections,
                    edits,
                    float(latency_ms),
                    score,
                    ts,
                ),
            )
        else:
            total = (row.get("total_calls") or 0) + 1
            approvals = (row.get("approvals") or 0) + (1 if outcome == "approved" else 0)
            rejections = (row.get("rejections") or 0) + (1 if outcome == "rejected" else 0)
            edits = (row.get("edits") or 0) + (1 if outcome == "edited" else 0)
            old_avg = row.get("avg_latency_ms") or 0.0
            new_avg = round((old_avg * (total - 1) + latency_ms) / total, 2)
            score = _compute_effectiveness(approvals, rejections, edits)
            db_exec(
                """
                UPDATE doctrine_effectiveness
                SET total_calls=?, approvals=?, rejections=?, edits=?, avg_latency_ms=?, effectiveness_score=?, last_updated_at=?
                WHERE doctrine_key=? AND brain_id=?
                """,
                (total, approvals, rejections, edits, new_avg, score, ts, doctrine_key, brain_id),
            )

    def _update_variant_stats(
        brain_id: str,
        outcome: str,
        latency_ms: int,
    ) -> None:
        """Update stats on the currently active variant for the given brain."""
        row = db_one(
            "SELECT * FROM prompt_variants WHERE brain_id=? AND is_active=1",
            (brain_id,),
        )
        if row is None:
            return
        total = (row.get("total_calls") or 0) + 1
        approvals = (row.get("total_approvals") or 0) + (1 if outcome == "approved" else 0)
        rejections = (row.get("total_rejections") or 0) + (1 if outcome == "rejected" else 0)
        old_avg = row.get("avg_latency_ms") or 0.0
        new_avg = round((old_avg * (total - 1) + latency_ms) / total, 2)
        db_exec(
            """
            UPDATE prompt_variants
            SET total_calls=?, total_approvals=?, total_rejections=?, avg_latency_ms=?
            WHERE id=?
            """,
            (total, approvals, rejections, new_avg, row["id"]),
        )

    # ------------------------------------------------------------------
    # Core functions
    # ------------------------------------------------------------------

    def record_outcome(
        *,
        llm_log_id: str = "",
        brain_id: str,
        prompt_hash: str = "",
        doctrine_keys: Optional[List[str]] = None,
        outcome: str,
        latency_ms: int = 0,
        token_count: int = 0,
        trust_delta: float = 0.0,
        feedback_text: str = "",
    ) -> str:
        """Record the outcome of an LLM call and update related tables."""
        if doctrine_keys is None:
            doctrine_keys = []
        valid_outcomes = {"approved", "rejected", "edited", "copied", "ignored", "fallback", "pending"}
        if outcome not in valid_outcomes:
            outcome = "pending"

        rec_id = new_id("pol")
        db_exec(
            """
            INSERT INTO prompt_outcome_log(id, llm_log_id, brain_id, prompt_hash, doctrine_keys_json, outcome, latency_ms, token_count, trust_delta, feedback_text, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                rec_id,
                llm_log_id,
                brain_id,
                prompt_hash,
                json.dumps(doctrine_keys),
                outcome,
                latency_ms,
                token_count,
                trust_delta,
                feedback_text,
                now_iso(),
            ),
        )

        # Update doctrine effectiveness for each doctrine key (global + per-brain)
        for dk in doctrine_keys:
            _upsert_doctrine_effectiveness(dk, brain_id, outcome, latency_ms)
            _upsert_doctrine_effectiveness(dk, "", outcome, latency_ms)

        # Update active variant stats
        _update_variant_stats(brain_id, outcome, latency_ms)

        return rec_id

    def create_variant(
        *,
        brain_id: str,
        variant_label: str,
        system_prompt: str = "",
        doctrine_keys: Optional[List[str]] = None,
        tone: str = "",
        style: str = "",
        created_by: str = "",
    ) -> Dict[str, Any]:
        """Create a new candidate prompt variant for a brain."""
        if doctrine_keys is None:
            doctrine_keys = []
        # If no system_prompt provided, copy from the registry profile
        if not system_prompt:
            profile = get_brain_profile_fn(brain_id)
            system_prompt = profile.get("system_prompt", "")
        if not tone:
            profile = get_brain_profile_fn(brain_id)
            tone = profile.get("tone", "")
        if not style:
            profile = get_brain_profile_fn(brain_id)
            style = profile.get("style", "")
        if not doctrine_keys:
            profile = get_brain_profile_fn(brain_id)
            doctrine_keys = list(profile.get("doctrine_keys", []))

        vid = new_id("pv")
        db_exec(
            """
            INSERT INTO prompt_variants(id, brain_id, variant_label, system_prompt, doctrine_keys_json, tone, style, is_active, total_calls, total_approvals, total_rejections, avg_latency_ms, created_at, created_by)
            VALUES(?,?,?,?,?,?,?,0,0,0,0,0.0,?,?)
            """,
            (
                vid,
                brain_id,
                variant_label,
                system_prompt,
                json.dumps(doctrine_keys),
                tone,
                style,
                now_iso(),
                created_by,
            ),
        )
        return {"id": vid, "brain_id": brain_id, "variant_label": variant_label}

    def activate_variant(variant_id: str) -> None:
        """Set a variant as active and deactivate all others for that brain."""
        row = db_one("SELECT brain_id FROM prompt_variants WHERE id=?", (variant_id,))
        if row is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        brain_id = row["brain_id"]
        db_exec("UPDATE prompt_variants SET is_active=0 WHERE brain_id=?", (brain_id,))
        db_exec("UPDATE prompt_variants SET is_active=1 WHERE id=?", (variant_id,))

    def get_variants(brain_id: str) -> List[Dict[str, Any]]:
        """List all variants for a brain with their stats."""
        rows = db_all(
            "SELECT * FROM prompt_variants WHERE brain_id=? ORDER BY created_at DESC",
            (brain_id,),
        )
        result = []
        for row in rows:
            entry = dict(row)
            entry["doctrine_keys"] = json.loads(entry.pop("doctrine_keys_json", "[]"))
            result.append(entry)
        return result

    def generate_recommendations(brain_id: str) -> List[Dict[str, Any]]:
        """Analyse recent outcomes for a brain and create improvement proposals."""
        limit = 100
        rows = db_all(
            "SELECT * FROM prompt_outcome_log WHERE brain_id=? ORDER BY created_at DESC LIMIT ?",
            (brain_id, limit),
        )
        total = len(rows)
        proposals: List[Dict[str, Any]] = []

        if total == 0:
            return proposals

        # Basic counts
        approved = sum(1 for r in rows if r.get("outcome") == "approved")
        rejected = sum(1 for r in rows if r.get("outcome") == "rejected")
        edited = sum(1 for r in rows if r.get("outcome") == "edited")
        fallback = sum(1 for r in rows if r.get("outcome") == "fallback")
        latencies = [r.get("latency_ms") or 0 for r in rows]
        tokens = [r.get("token_count") or 0 for r in rows]
        avg_latency = sum(latencies) / total
        avg_tokens = sum(tokens) / total

        rejection_rate = rejected / total
        edit_rate = edited / total
        fallback_rate = fallback / total

        def _add_proposal(
            proposal_type: str,
            description: str,
            current_value: str,
            proposed_value: str,
            confidence: float,
            evidence: Dict[str, Any],
        ) -> None:
            pid = new_id("pp")
            db_exec(
                """
                INSERT INTO prompt_proposals(id, brain_id, proposal_type, description, current_value, proposed_value, confidence, evidence_json, status, reviewed_by, reviewed_at, created_at)
                VALUES(?,?,?,?,?,?,?,?,'pending','','',?)
                """,
                (
                    pid,
                    brain_id,
                    proposal_type,
                    description,
                    current_value,
                    proposed_value,
                    round(confidence, 4),
                    json.dumps(evidence),
                    now_iso(),
                ),
            )
            proposals.append({
                "id": pid,
                "brain_id": brain_id,
                "proposal_type": proposal_type,
                "description": description,
                "confidence": round(confidence, 4),
                "status": "pending",
            })

        # --- Rule 1: High rejection rate → simplify instructions or adjust tone
        if rejection_rate > 0.30:
            profile = get_brain_profile_fn(brain_id)
            _add_proposal(
                proposal_type="simplify_instructions",
                description=f"Rejection rate is {rejection_rate:.0%} (>30%). Consider simplifying instructions.",
                current_value=profile.get("system_prompt", "")[:300],
                proposed_value="Review and simplify the system prompt to reduce rejections.",
                confidence=min(0.5 + rejection_rate, 1.0),
                evidence={"rejection_rate": rejection_rate, "total": total, "rejected": rejected},
            )
            _add_proposal(
                proposal_type="adjust_tone",
                description=f"Rejection rate is {rejection_rate:.0%}. Adjusting tone may improve acceptance.",
                current_value=profile.get("tone", ""),
                proposed_value="neutral",
                confidence=min(0.4 + rejection_rate, 1.0),
                evidence={"rejection_rate": rejection_rate, "total": total},
            )

        # --- Rule 2: High edit rate → tighten output
        if edit_rate > 0.40:
            _add_proposal(
                proposal_type="tighten_output",
                description=f"Edit rate is {edit_rate:.0%} (>40%). Outputs are frequently modified before use.",
                current_value="",
                proposed_value="Add more specific output format constraints to reduce post-generation edits.",
                confidence=min(0.4 + edit_rate, 1.0),
                evidence={"edit_rate": edit_rate, "total": total, "edited": edited},
            )

        # --- Rule 3: High fallback rate → replace prompt
        if fallback_rate > 0.20:
            profile = get_brain_profile_fn(brain_id)
            _add_proposal(
                proposal_type="replace_prompt",
                description=f"Fallback rate is {fallback_rate:.0%} (>20%). The current prompt may be causing LLM failures.",
                current_value=profile.get("system_prompt", "")[:300],
                proposed_value="Replace the system prompt with a more robust version.",
                confidence=min(0.5 + fallback_rate, 1.0),
                evidence={"fallback_rate": fallback_rate, "total": total, "fallbacks": fallback},
            )

        # --- Rule 4: Doctrine appearing in >60% of rejected outcomes → remove_doctrine
        profile = get_brain_profile_fn(brain_id)
        active_doctrines = set(profile.get("doctrine_keys", []))
        rejected_rows = [r for r in rows if r.get("outcome") == "rejected"]
        if rejected_rows:
            doctrine_rejection_counts: Dict[str, int] = {}
            for r in rejected_rows:
                for dk in json.loads(r.get("doctrine_keys_json") or "[]"):
                    doctrine_rejection_counts[dk] = doctrine_rejection_counts.get(dk, 0) + 1
            for dk, count in doctrine_rejection_counts.items():
                if dk in active_doctrines and count / len(rejected_rows) > 0.60:
                    _add_proposal(
                        proposal_type="remove_doctrine",
                        description=f"Doctrine '{dk}' appears in {count/len(rejected_rows):.0%} of rejected outcomes.",
                        current_value=dk,
                        proposed_value="",
                        confidence=min(0.5 + count / len(rejected_rows) * 0.5, 1.0),
                        evidence={"doctrine_key": dk, "rejection_count": count, "total_rejections": len(rejected_rows)},
                    )

        # --- Rule 5: Doctrine appearing in >70% of approved outcomes for OTHER brains but not used here → add_doctrine
        approved_rows = [r for r in rows if r.get("outcome") == "approved"]
        other_brain_rows = db_all(
            "SELECT doctrine_keys_json FROM prompt_outcome_log WHERE brain_id!=? AND outcome='approved' ORDER BY created_at DESC LIMIT 200",
            (brain_id,),
        )
        if other_brain_rows:
            other_doctrine_counts: Dict[str, int] = {}
            other_total = len(other_brain_rows)
            for r in other_brain_rows:
                for dk in json.loads(r.get("doctrine_keys_json") or "[]"):
                    other_doctrine_counts[dk] = other_doctrine_counts.get(dk, 0) + 1
            for dk, count in other_doctrine_counts.items():
                if dk not in active_doctrines and count / other_total > 0.70:
                    _add_proposal(
                        proposal_type="add_doctrine",
                        description=f"Doctrine '{dk}' appears in {count/other_total:.0%} of approved outcomes for other brains but is not used by {brain_id}.",
                        current_value="",
                        proposed_value=dk,
                        confidence=min(0.4 + count / other_total * 0.5, 1.0),
                        evidence={"doctrine_key": dk, "other_approval_rate": count / other_total, "other_total": other_total},
                    )

        # --- Rule 6: High latency + high token count → prefer_shorter
        if avg_latency > 5000 and avg_tokens > 300:
            _add_proposal(
                proposal_type="prefer_shorter",
                description=f"Average latency is {avg_latency:.0f}ms with {avg_tokens:.0f} tokens. Consider requesting shorter outputs.",
                current_value=f"avg_latency={avg_latency:.0f}ms, avg_tokens={avg_tokens:.0f}",
                proposed_value="Add instruction to prefer concise outputs and reduce max_tokens.",
                confidence=0.6,
                evidence={"avg_latency_ms": avg_latency, "avg_tokens": avg_tokens},
            )

        # --- Rule 7: Candidate variant with better stats than active → promote_variant
        active_variant = db_one(
            "SELECT * FROM prompt_variants WHERE brain_id=? AND is_active=1",
            (brain_id,),
        )
        if active_variant:
            active_approvals = active_variant.get("total_approvals") or 0
            active_total = active_variant.get("total_calls") or 0
            active_approval_rate = active_approvals / active_total if active_total > 0 else 0.0
            candidates = db_all(
                "SELECT * FROM prompt_variants WHERE brain_id=? AND is_active=0 AND total_calls>=5",
                (brain_id,),
            )
            for cand in candidates:
                cand_total = cand.get("total_calls") or 0
                cand_approvals = cand.get("total_approvals") or 0
                cand_rate = cand_approvals / cand_total if cand_total > 0 else 0.0
                if cand_rate > active_approval_rate + 0.10:
                    _add_proposal(
                        proposal_type="promote_variant",
                        description=f"Variant '{cand.get('variant_label')}' has approval rate {cand_rate:.0%} vs active {active_approval_rate:.0%}.",
                        current_value=active_variant.get("id", ""),
                        proposed_value=cand.get("id", ""),
                        confidence=min(0.5 + (cand_rate - active_approval_rate), 1.0),
                        evidence={"candidate_id": cand.get("id"), "candidate_approval_rate": cand_rate, "active_approval_rate": active_approval_rate},
                    )

        return proposals

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    @app.post("/api/brain/prompt-outcome")
    async def post_prompt_outcome(req: OutcomeRequest, request: Request):
        require_user(request)
        rec_id = record_outcome(
            llm_log_id=req.llm_log_id,
            brain_id=req.brain_id,
            prompt_hash=req.prompt_hash,
            doctrine_keys=req.doctrine_keys,
            outcome=req.outcome,
            latency_ms=req.latency_ms,
            token_count=req.token_count,
            trust_delta=req.trust_delta,
            feedback_text=req.feedback_text,
        )
        return {"id": rec_id, "status": "recorded"}

    @app.post("/api/brain/prompt-variants")
    async def post_create_variant(req: CreateVariantRequest, request: Request):
        user = require_master(request)
        result = create_variant(
            brain_id=req.brain_id,
            variant_label=req.variant_label,
            system_prompt=req.system_prompt,
            doctrine_keys=req.doctrine_keys,
            tone=req.tone,
            style=req.style,
            created_by=user.get("username", ""),
        )
        return result

    @app.get("/api/brain/prompt-variants/{brain_id}")
    async def get_brain_variants(brain_id: str, request: Request):
        require_user(request)
        user = session_user(request)
        is_master = user.get("role") == "master" if user else False
        variants = get_variants(brain_id)
        # Non-master users don't see full system prompts
        if not is_master:
            for v in variants:
                v.pop("system_prompt", None)
        return {"brain_id": brain_id, "variants": variants, "total": len(variants)}

    @app.post("/api/brain/prompt-variants/{variant_id}/activate")
    async def post_activate_variant(variant_id: str, request: Request):
        require_master(request)
        activate_variant(variant_id)
        return {"variant_id": variant_id, "status": "activated"}

    @app.delete("/api/brain/prompt-variants/{variant_id}")
    async def delete_variant(variant_id: str, request: Request):
        require_master(request)
        row = db_one("SELECT * FROM prompt_variants WHERE id=?", (variant_id,))
        if row is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        if row.get("is_active") == 1:
            raise HTTPException(status_code=400, detail="Cannot delete the active variant")
        db_exec("DELETE FROM prompt_variants WHERE id=?", (variant_id,))
        return {"variant_id": variant_id, "status": "deleted"}

    @app.post("/api/brain/prompt-recommendations/{brain_id}")
    async def post_generate_recommendations(brain_id: str, request: Request):
        require_master(request)
        proposals = generate_recommendations(brain_id)
        return {"brain_id": brain_id, "proposals_created": len(proposals), "proposals": proposals}

    @app.get("/api/brain/prompt-proposals")
    async def get_prompt_proposals(
        request: Request,
        brain_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ):
        require_master(request)
        limit = max(1, min(limit, 200))
        clauses = []
        params: list = []
        if brain_id:
            clauses.append("brain_id=?")
            params.append(brain_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        rows = db_all(
            f"SELECT * FROM prompt_proposals {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        proposals = []
        for row in rows:
            entry = dict(row)
            if "evidence_json" in entry:
                try:
                    entry["evidence"] = json.loads(entry.pop("evidence_json"))
                except Exception:
                    entry["evidence"] = {}
            proposals.append(entry)
        return {"proposals": proposals, "total": len(proposals)}

    @app.post("/api/brain/prompt-proposals/{proposal_id}/review")
    async def post_review_proposal(
        proposal_id: str,
        req: ProposalReviewRequest,
        request: Request,
    ):
        user = require_master(request)
        row = db_one("SELECT * FROM prompt_proposals WHERE id=?", (proposal_id,))
        if row is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        if row.get("status") != "pending":
            raise HTTPException(status_code=400, detail="Proposal is not pending")
        if req.action not in ("accept", "reject"):
            raise HTTPException(status_code=400, detail="action must be 'accept' or 'reject'")

        new_status = "accepted" if req.action == "accept" else "rejected"
        reviewer = user.get("username", "")
        reviewed_at = now_iso()

        db_exec(
            "UPDATE prompt_proposals SET status=?, reviewed_by=?, reviewed_at=? WHERE id=?",
            (new_status, reviewer, reviewed_at, proposal_id),
        )

        # Side-effects on acceptance
        if new_status == "accepted":
            proposal_type = row.get("proposal_type", "")
            brain_id = row.get("brain_id", "")
            proposed_value = row.get("proposed_value", "")

            if proposal_type == "promote_variant":
                # Activate the proposed variant
                variant_id = proposed_value
                try:
                    activate_variant(variant_id)
                except HTTPException:
                    pass  # variant may have been deleted; still mark proposal accepted

            elif proposal_type in ("add_doctrine", "remove_doctrine"):
                # Create a brain_prompt_overrides entry
                # We store the updated doctrine_keys list as JSON in override_value
                profile = get_brain_profile_fn(brain_id)
                current_keys: List[str] = list(profile.get("doctrine_keys", []))
                if proposal_type == "add_doctrine" and proposed_value not in current_keys:
                    current_keys.append(proposed_value)
                elif proposal_type == "remove_doctrine" and proposed_value in current_keys:
                    current_keys.remove(proposed_value)
                try:
                    db_exec(
                        """
                        INSERT INTO brain_prompt_overrides(id, brain_id, field_name, override_value, created_at, created_by)
                        VALUES(?,?,?,?,?,?)
                        """,
                        (
                            new_id("bpo"),
                            brain_id,
                            "doctrine_keys",
                            json.dumps(current_keys),
                            reviewed_at,
                            reviewer,
                        ),
                    )
                except Exception as exc:
                    if log:
                        log.warning("brain_prompt_overrides insert failed: %s", exc)

        return {
            "proposal_id": proposal_id,
            "status": new_status,
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
        }

    @app.get("/api/brain/prompt-performance")
    async def get_prompt_performance(request: Request):
        require_master(request)
        brain_ids = list_all_brain_ids()

        brain_stats = []
        for bid in brain_ids:
            rows = db_all(
                "SELECT outcome, latency_ms FROM prompt_outcome_log WHERE brain_id=? ORDER BY created_at DESC LIMIT 100",
                (bid,),
            )
            total = len(rows)
            if total == 0:
                brain_stats.append({
                    "brain_id": bid,
                    "total_calls": 0,
                    "approval_rate": 0.0,
                    "rejection_rate": 0.0,
                    "edit_rate": 0.0,
                    "fallback_rate": 0.0,
                    "avg_latency_ms": 0.0,
                })
                continue
            approved = sum(1 for r in rows if r.get("outcome") == "approved")
            rejected = sum(1 for r in rows if r.get("outcome") == "rejected")
            edited = sum(1 for r in rows if r.get("outcome") == "edited")
            fallback_c = sum(1 for r in rows if r.get("outcome") == "fallback")
            avg_lat = sum(r.get("latency_ms") or 0 for r in rows) / total
            brain_stats.append({
                "brain_id": bid,
                "total_calls": total,
                "approval_rate": round(approved / total, 4),
                "rejection_rate": round(rejected / total, 4),
                "edit_rate": round(edited / total, 4),
                "fallback_rate": round(fallback_c / total, 4),
                "avg_latency_ms": round(avg_lat, 2),
            })

        # Doctrine effectiveness global ranking
        doctrine_rows = db_all(
            "SELECT * FROM doctrine_effectiveness WHERE brain_id='' ORDER BY effectiveness_score DESC LIMIT 20",
            (),
        )
        doctrine_ranking = [
            {
                "doctrine_key": r.get("doctrine_key"),
                "effectiveness_score": r.get("effectiveness_score"),
                "total_calls": r.get("total_calls"),
                "approvals": r.get("approvals"),
                "rejections": r.get("rejections"),
            }
            for r in doctrine_rows
        ]

        # Active variants per brain
        active_variants = {}
        for bid in brain_ids:
            row = db_one("SELECT id, variant_label, total_calls, total_approvals FROM prompt_variants WHERE brain_id=? AND is_active=1", (bid,))
            if row:
                active_variants[bid] = dict(row)

        # Pending proposals count
        pending_count_row = db_one("SELECT COUNT(*) as cnt FROM prompt_proposals WHERE status='pending'", ())
        pending_count = pending_count_row.get("cnt", 0) if pending_count_row else 0

        # Best/worst performing brains
        scored = sorted(
            [b for b in brain_stats if b["total_calls"] > 0],
            key=lambda x: x["approval_rate"],
            reverse=True,
        )
        best = scored[0]["brain_id"] if scored else None
        worst = scored[-1]["brain_id"] if scored else None

        return {
            "brain_stats": brain_stats,
            "doctrine_ranking": doctrine_ranking,
            "active_variants": active_variants,
            "pending_proposals_count": pending_count,
            "best_performing_brain": best,
            "worst_performing_brain": worst,
        }

    @app.get("/api/brain/prompt-performance/{brain_id}")
    async def get_brain_prompt_performance(brain_id: str, request: Request):
        require_master(request)

        # Outcome distribution
        outcome_rows = db_all(
            "SELECT outcome, COUNT(*) as cnt FROM prompt_outcome_log WHERE brain_id=? GROUP BY outcome",
            (brain_id,),
        )
        outcome_dist = {r.get("outcome"): r.get("cnt") for r in outcome_rows}

        # Doctrine effectiveness breakdown for this brain
        doctrine_rows = db_all(
            "SELECT * FROM doctrine_effectiveness WHERE brain_id=? ORDER BY effectiveness_score DESC",
            (brain_id,),
        )
        doctrine_breakdown = [
            {
                "doctrine_key": r.get("doctrine_key"),
                "total_calls": r.get("total_calls"),
                "approvals": r.get("approvals"),
                "rejections": r.get("rejections"),
                "edits": r.get("edits"),
                "effectiveness_score": r.get("effectiveness_score"),
            }
            for r in doctrine_rows
        ]

        # Variant comparison
        variants = get_variants(brain_id)
        # Remove system_prompt from variant comparison for safety
        for v in variants:
            v.pop("system_prompt", None)

        # Recent proposals
        proposal_rows = db_all(
            "SELECT id, proposal_type, description, confidence, status, created_at FROM prompt_proposals WHERE brain_id=? ORDER BY created_at DESC LIMIT 20",
            (brain_id,),
        )
        recent_proposals = [dict(r) for r in proposal_rows]

        # Trend: last 7 days of outcomes grouped by day
        trend_rows = db_all(
            """
            SELECT substr(created_at, 1, 10) as day, outcome, COUNT(*) as cnt
            FROM prompt_outcome_log
            WHERE brain_id=? AND created_at >= datetime('now', '-7 days')
            GROUP BY day, outcome
            ORDER BY day ASC
            """,
            (brain_id,),
        )
        trend: Dict[str, Dict[str, int]] = {}
        for r in trend_rows:
            day = r.get("day", "")
            if day not in trend:
                trend[day] = {}
            trend[day][r.get("outcome", "")] = r.get("cnt", 0)

        return {
            "brain_id": brain_id,
            "outcome_distribution": outcome_dist,
            "doctrine_effectiveness": doctrine_breakdown,
            "variant_comparison": variants,
            "recent_proposals": recent_proposals,
            "trend_last_7_days": trend,
        }

    if log:
        log.info("Prompt adaptation layer loaded")

    return {
        "record_prompt_outcome": record_outcome,
        "generate_prompt_recommendations": generate_recommendations,
    }
