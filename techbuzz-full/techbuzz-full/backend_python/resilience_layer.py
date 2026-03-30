"""Resilience Layer — FastAPI layer following the install_* pattern.

Provides:
  - compute_confidence: analyze output and store uncertainty metadata
  - resilient_generate: retry/fallback/recovery wrapper around generate_text
  - detect_conflicts: check for conflicting data and preserve both versions
  - record_override: log human corrections as learning signals
  - API endpoints for resilience dashboard, conflicts, assumptions, overrides
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RecordConfidenceRequest(BaseModel):
    brain_id: str = ""
    source_action: str = ""
    input_text: str = ""
    output_text: str = ""
    provider: str = ""
    fallback_used: bool = False
    latency_ms: int = 0
    known_missing_fields: Optional[List[str]] = None
    known_conflicts: Optional[List[str]] = None


class OverrideRequest(BaseModel):
    brain_id: str = ""
    output_meta_id: str = ""
    override_type: str
    original_output: str = ""
    corrected_output: str = ""
    reroute_to_brain: str = ""
    override_reason: str = ""


class CorrectAssumptionRequest(BaseModel):
    correction_text: str


class ResolveConflictRequest(BaseModel):
    resolution: str  # "a", "b", "merged", "deferred"
    note: str = ""


# ---------------------------------------------------------------------------
# Installer
# ---------------------------------------------------------------------------

def install_resilience_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    db_one = ctx["db_one"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
    call_local_llm = ctx["call_local_llm"]
    log = ctx["log"]
    brain_aware_generate = ctx.get("brain_aware_generate")

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS resilience_output_meta(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL DEFAULT '',
                source_action TEXT NOT NULL DEFAULT '',
                confidence_score REAL NOT NULL DEFAULT 0.0,
                risk_level TEXT NOT NULL DEFAULT 'low',
                missing_data_flags_json TEXT NOT NULL DEFAULT '[]',
                conflict_flags_json TEXT NOT NULL DEFAULT '[]',
                assumptions_json TEXT NOT NULL DEFAULT '[]',
                fallback_used INTEGER NOT NULL DEFAULT 0,
                fallback_detail TEXT NOT NULL DEFAULT '',
                provider_chain_json TEXT NOT NULL DEFAULT '[]',
                latency_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS resilience_assumptions(
                id TEXT PRIMARY KEY,
                output_meta_id TEXT NOT NULL DEFAULT '',
                brain_id TEXT NOT NULL DEFAULT '',
                assumption_text TEXT NOT NULL DEFAULT '',
                source_context TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'unconfirmed',
                correction_text TEXT NOT NULL DEFAULT '',
                corrected_by TEXT NOT NULL DEFAULT '',
                corrected_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS resilience_conflicts(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL DEFAULT '',
                conflict_type TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                version_a_json TEXT NOT NULL DEFAULT '{}',
                version_b_json TEXT NOT NULL DEFAULT '{}',
                resolution_status TEXT NOT NULL DEFAULT 'unresolved',
                resolved_by TEXT NOT NULL DEFAULT '',
                resolution_note TEXT NOT NULL DEFAULT '',
                resolved_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS resilience_recovery_log(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT '',
                failure_type TEXT NOT NULL DEFAULT '',
                failure_detail TEXT NOT NULL DEFAULT '',
                recovery_strategy TEXT NOT NULL DEFAULT '',
                recovery_result TEXT NOT NULL DEFAULT '',
                partial_work_json TEXT NOT NULL DEFAULT '{}',
                retry_count INTEGER NOT NULL DEFAULT 0,
                total_latency_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS resilience_overrides(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL DEFAULT '',
                output_meta_id TEXT NOT NULL DEFAULT '',
                override_type TEXT NOT NULL DEFAULT '',
                original_output TEXT NOT NULL DEFAULT '',
                corrected_output TEXT NOT NULL DEFAULT '',
                reroute_to_brain TEXT NOT NULL DEFAULT '',
                override_reason TEXT NOT NULL DEFAULT '',
                overridden_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # ------------------------------------------------------------------
    # Auth helpers
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

    # ------------------------------------------------------------------
    # Core helper: compute_confidence
    # ------------------------------------------------------------------
    def compute_confidence(
        *,
        brain_id: str = "",
        source_action: str = "",
        input_text: str = "",
        output_text: str = "",
        provider: str = "",
        fallback_used: bool = False,
        fallback_detail: str = "",
        provider_chain: List[str] = None,
        latency_ms: int = 0,
        known_missing_fields: List[str] = None,
        known_conflicts: List[str] = None,
    ) -> Dict[str, Any]:
        """Analyze an output and compute confidence/uncertainty metadata."""
        if provider_chain is None:
            provider_chain = []
        if known_missing_fields is None:
            known_missing_fields = []
        if known_conflicts is None:
            known_conflicts = []

        score = 0.7

        # Adjustments
        if fallback_used:
            score -= 0.1
        score -= 0.05 * len(known_missing_fields)
        score -= 0.1 * len(known_conflicts)
        if latency_ms > 5000:
            score -= 0.05
        # Primary providers get a small boost
        provider_lower = provider.lower()
        if provider_lower and "fallback" not in provider_lower and "deterministic" not in provider_lower:
            score += 0.05

        # Detect missing-data phrases in output
        missing_phrases = [
            "i don't have",
            "no data available",
            "information is missing",
            "not specified",
            "unknown",
            "unclear",
        ]
        auto_missing: List[str] = list(known_missing_fields)
        output_lower = output_text.lower()
        for phrase in missing_phrases:
            if phrase in output_lower and phrase not in auto_missing:
                auto_missing.append(phrase)
                score -= 0.05

        # Detect assumption phrases
        assumption_phrases = [
            "i assume",
            "presumably",
            "likely",
            "it appears",
            "based on limited",
            "inferring",
        ]
        auto_assumptions: List[str] = []
        for phrase in assumption_phrases:
            idx = output_lower.find(phrase)
            while idx != -1:
                end = min(idx + 120, len(output_text))
                snippet = output_text[idx:end].strip()
                if snippet not in auto_assumptions:
                    auto_assumptions.append(snippet)
                idx = output_lower.find(phrase, idx + 1)

        # Risk level
        score = max(0.0, min(1.0, score))
        if score < 0.3:
            risk_level = "critical"
        elif score < 0.5:
            risk_level = "high"
        elif score < 0.7:
            risk_level = "medium"
        else:
            risk_level = "low"

        output_meta_id = new_id("rom")
        created = now_iso()

        try:
            db_exec(
                """
                INSERT INTO resilience_output_meta(
                    id, brain_id, source_action, confidence_score, risk_level,
                    missing_data_flags_json, conflict_flags_json, assumptions_json,
                    fallback_used, fallback_detail, provider_chain_json, latency_ms, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    output_meta_id,
                    brain_id,
                    source_action,
                    score,
                    risk_level,
                    json.dumps(auto_missing),
                    json.dumps(known_conflicts),
                    json.dumps(auto_assumptions),
                    1 if fallback_used else 0,
                    fallback_detail,
                    json.dumps(provider_chain),
                    latency_ms,
                    created,
                ),
            )
        except Exception as exc:
            log.warning("resilience_output_meta insert failed: %s", exc)

        # Insert assumptions
        for assumption_text in auto_assumptions:
            try:
                db_exec(
                    """
                    INSERT INTO resilience_assumptions(
                        id, output_meta_id, brain_id, assumption_text, source_context,
                        status, correction_text, corrected_by, corrected_at, created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        new_id("rasm"),
                        output_meta_id,
                        brain_id,
                        assumption_text,
                        source_action,
                        "unconfirmed",
                        "",
                        "",
                        "",
                        created,
                    ),
                )
            except Exception as exc:
                log.warning("resilience_assumptions insert failed: %s", exc)

        return {
            "output_meta_id": output_meta_id,
            "brain_id": brain_id,
            "source_action": source_action,
            "confidence_score": score,
            "risk_level": risk_level,
            "missing_data_flags": auto_missing,
            "conflict_flags": known_conflicts,
            "assumptions": auto_assumptions,
            "fallback_used": fallback_used,
            "fallback_detail": fallback_detail,
            "provider_chain": provider_chain,
            "latency_ms": latency_ms,
            "created_at": created,
        }

    # ------------------------------------------------------------------
    # Core helper: resilient_generate
    # ------------------------------------------------------------------
    async def resilient_generate(
        prompt: str,
        *,
        brain_id: str = "",
        source_action: str = "",
        system: str = "",
        max_tokens: int = 500,
        use_web_search: bool = False,
        source: str = "manual",
        workspace: str = "resilience",
        max_retries: int = 2,
        known_missing_fields: List[str] = None,
        known_conflicts: List[str] = None,
    ) -> Dict[str, Any]:
        """Wrapper around generate_text with retry/fallback/recovery."""
        if known_missing_fields is None:
            known_missing_fields = []
        if known_conflicts is None:
            known_conflicts = []

        provider_chain: List[str] = []
        start_time = time.time()
        partial_work: Dict[str, Any] = {}
        retry_count = 0

        async def _try_primary() -> Dict[str, Any]:
            if brain_aware_generate:
                return await brain_aware_generate(
                    prompt,
                    brain_id=brain_id or "default",
                    max_tokens=max_tokens,
                    use_web_search=use_web_search,
                    source=source,
                    workspace=workspace,
                )
            return await generate_text(
                prompt,
                system=system,
                max_tokens=max_tokens,
                use_web_search=use_web_search,
                source=source,
                workspace=workspace,
            )

        # Primary attempts with retries
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                result = await _try_primary()
                prov = result.get("provider", "built-in")
                provider_chain.append(prov)
                latency_ms = int((time.time() - start_time) * 1000)
                meta = compute_confidence(
                    brain_id=brain_id,
                    source_action=source_action,
                    input_text=prompt,
                    output_text=result.get("text", ""),
                    provider=prov,
                    fallback_used=False,
                    provider_chain=provider_chain,
                    latency_ms=latency_ms,
                    known_missing_fields=known_missing_fields,
                    known_conflicts=known_conflicts,
                )
                return {**result, "resilience": meta}
            except Exception as exc:
                last_exc = exc
                retry_count = attempt
                # Log recovery attempt
                try:
                    db_exec(
                        """
                        INSERT INTO resilience_recovery_log(
                            id, brain_id, action, failure_type, failure_detail,
                            recovery_strategy, recovery_result, partial_work_json,
                            retry_count, total_latency_ms, created_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            new_id("rrl"),
                            brain_id,
                            source_action or "resilient_generate",
                            "provider_error",
                            str(exc)[:500],
                            "retry" if attempt < max_retries else "fallback_provider",
                            "failed",
                            json.dumps(partial_work),
                            attempt,
                            int((time.time() - start_time) * 1000),
                            now_iso(),
                        ),
                    )
                except Exception as log_exc:
                    log.warning("resilience_recovery_log insert failed: %s", log_exc)

        # Fallback: try local LLM
        try:
            provider_chain.append("local_llm_fallback")
            local_result = await call_local_llm(
                system=system,
                prompt=prompt,
                max_tokens=max_tokens,
            )
            prov = f"ollama/{local_result.get('model', 'local')}".strip("/")
            provider_chain[-1] = prov
            latency_ms = int((time.time() - start_time) * 1000)
            meta = compute_confidence(
                brain_id=brain_id,
                source_action=source_action,
                input_text=prompt,
                output_text=local_result.get("text", ""),
                provider=prov,
                fallback_used=True,
                fallback_detail="local_llm_fallback",
                provider_chain=provider_chain,
                latency_ms=latency_ms,
                known_missing_fields=known_missing_fields,
                known_conflicts=known_conflicts,
            )
            try:
                db_exec(
                    """
                    INSERT INTO resilience_recovery_log(
                        id, brain_id, action, failure_type, failure_detail,
                        recovery_strategy, recovery_result, partial_work_json,
                        retry_count, total_latency_ms, created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        new_id("rrl"),
                        brain_id,
                        source_action or "resilient_generate",
                        "provider_error",
                        str(last_exc)[:500] if last_exc else "",
                        "fallback_provider",
                        "success",
                        json.dumps(partial_work),
                        retry_count,
                        latency_ms,
                        now_iso(),
                    ),
                )
            except Exception as log_exc:
                log.warning("resilience_recovery_log insert failed: %s", log_exc)
            return {**local_result, "provider": prov, "resilience": meta}
        except Exception as fallback_exc:
            log.warning("resilience local LLM fallback failed: %s", fallback_exc)

        # Deterministic fallback
        latency_ms = int((time.time() - start_time) * 1000)
        provider_chain.append("deterministic_fallback")
        degrade_text = (
            f"I was unable to complete this request due to a system issue. "
            f"The request has been preserved for retry. "
            f"Action: {source_action}, Brain: {brain_id}"
        )
        meta = compute_confidence(
            brain_id=brain_id,
            source_action=source_action,
            input_text=prompt,
            output_text=degrade_text,
            provider="deterministic_fallback",
            fallback_used=True,
            fallback_detail="deterministic_fallback",
            provider_chain=provider_chain,
            latency_ms=latency_ms,
            known_missing_fields=known_missing_fields,
            known_conflicts=known_conflicts,
        )
        try:
            db_exec(
                """
                INSERT INTO resilience_recovery_log(
                    id, brain_id, action, failure_type, failure_detail,
                    recovery_strategy, recovery_result, partial_work_json,
                    retry_count, total_latency_ms, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_id("rrl"),
                    brain_id,
                    source_action or "resilient_generate",
                    "provider_error",
                    str(last_exc)[:500] if last_exc else "",
                    "deterministic_output",
                    "failed",
                    json.dumps(partial_work),
                    retry_count,
                    latency_ms,
                    now_iso(),
                ),
            )
        except Exception as log_exc:
            log.warning("resilience_recovery_log insert failed: %s", log_exc)

        return {
            "text": degrade_text,
            "provider": "deterministic_fallback",
            "resilience": meta,
        }

    # ------------------------------------------------------------------
    # Core helper: detect_conflicts
    # ------------------------------------------------------------------
    def detect_conflicts(
        brain_id: str,
        field_name: str,
        new_value: Any,
        existing_value: Any,
        context: str = "",
    ) -> Optional[str]:
        """Check for conflicting data and insert a conflict record if found."""
        # Normalize for comparison
        def _norm(v: Any) -> str:
            return str(v).strip().lower()

        if _norm(new_value) == _norm(existing_value):
            return None

        conflict_id = new_id("rcon")
        try:
            db_exec(
                """
                INSERT INTO resilience_conflicts(
                    id, brain_id, conflict_type, description,
                    version_a_json, version_b_json,
                    resolution_status, resolved_by, resolution_note, resolved_at, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    conflict_id,
                    brain_id,
                    "data_mismatch",
                    f"Field '{field_name}' conflict. Context: {context}",
                    json.dumps({"field": field_name, "value": existing_value}),
                    json.dumps({"field": field_name, "value": new_value}),
                    "unresolved",
                    "",
                    "",
                    "",
                    now_iso(),
                ),
            )
        except Exception as exc:
            log.warning("resilience_conflicts insert failed: %s", exc)
            return None
        return conflict_id

    # ------------------------------------------------------------------
    # Core helper: record_override
    # ------------------------------------------------------------------
    def record_override(
        *,
        brain_id: str = "",
        output_meta_id: str = "",
        override_type: str,
        original_output: str = "",
        corrected_output: str = "",
        reroute_to_brain: str = "",
        override_reason: str = "",
        overridden_by: str = "",
    ) -> str:
        override_id = new_id("rovr")
        try:
            db_exec(
                """
                INSERT INTO resilience_overrides(
                    id, brain_id, output_meta_id, override_type,
                    original_output, corrected_output, reroute_to_brain,
                    override_reason, overridden_by, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    override_id,
                    brain_id,
                    output_meta_id,
                    override_type,
                    original_output,
                    corrected_output,
                    reroute_to_brain,
                    override_reason,
                    overridden_by,
                    now_iso(),
                ),
            )
        except Exception as exc:
            log.warning("resilience_overrides insert failed: %s", exc)

        # If edit, mark linked assumptions as corrected
        if override_type == "edit" and output_meta_id:
            try:
                db_exec(
                    """
                    UPDATE resilience_assumptions
                    SET status='corrected', correction_text=?, corrected_by=?, corrected_at=?
                    WHERE output_meta_id=? AND status='unconfirmed'
                    """,
                    (corrected_output, overridden_by, now_iso(), output_meta_id),
                )
            except Exception as exc:
                log.warning("resilience_assumptions update failed: %s", exc)

        return override_id

    # ------------------------------------------------------------------
    # API Endpoints
    # ------------------------------------------------------------------

    @app.post("/api/resilience/record-confidence")
    async def api_record_confidence(req: RecordConfidenceRequest, request: Request):
        require_user(request)
        meta = compute_confidence(
            brain_id=req.brain_id,
            source_action=req.source_action,
            input_text=req.input_text,
            output_text=req.output_text,
            provider=req.provider,
            fallback_used=req.fallback_used,
            latency_ms=req.latency_ms,
            known_missing_fields=req.known_missing_fields or [],
            known_conflicts=req.known_conflicts or [],
        )
        return {"ok": True, "metadata": meta}

    @app.post("/api/resilience/override")
    async def api_record_override(req: OverrideRequest, request: Request):
        user = require_user(request)
        valid_types = {"approve", "reject", "edit", "defer", "reroute"}
        if req.override_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid override_type. Must be one of: {', '.join(valid_types)}")
        override_id = record_override(
            brain_id=req.brain_id,
            output_meta_id=req.output_meta_id,
            override_type=req.override_type,
            original_output=req.original_output,
            corrected_output=req.corrected_output,
            reroute_to_brain=req.reroute_to_brain,
            override_reason=req.override_reason,
            overridden_by=user.get("id", ""),
        )
        return {"ok": True, "override_id": override_id}

    @app.post("/api/resilience/assumption/{assumption_id}/confirm")
    async def api_confirm_assumption(assumption_id: str, request: Request):
        require_user(request)
        row = db_one("SELECT id FROM resilience_assumptions WHERE id=?", (assumption_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Assumption not found")
        db_exec(
            "UPDATE resilience_assumptions SET status='confirmed' WHERE id=?",
            (assumption_id,),
        )
        return {"ok": True, "assumption_id": assumption_id, "status": "confirmed"}

    @app.post("/api/resilience/assumption/{assumption_id}/correct")
    async def api_correct_assumption(
        assumption_id: str,
        req: CorrectAssumptionRequest,
        request: Request,
    ):
        user = require_user(request)
        row = db_one("SELECT id FROM resilience_assumptions WHERE id=?", (assumption_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Assumption not found")
        db_exec(
            """
            UPDATE resilience_assumptions
            SET status='corrected', correction_text=?, corrected_by=?, corrected_at=?
            WHERE id=?
            """,
            (req.correction_text, user.get("id", ""), now_iso(), assumption_id),
        )
        return {"ok": True, "assumption_id": assumption_id, "status": "corrected"}

    @app.post("/api/resilience/conflict/{conflict_id}/resolve")
    async def api_resolve_conflict(
        conflict_id: str,
        req: ResolveConflictRequest,
        request: Request,
    ):
        require_master(request)
        row = db_one("SELECT id FROM resilience_conflicts WHERE id=?", (conflict_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Conflict not found")
        valid = {"a", "b", "merged", "deferred"}
        if req.resolution not in valid:
            raise HTTPException(status_code=400, detail=f"resolution must be one of: {', '.join(valid)}")
        status_map = {"a": "resolved_a", "b": "resolved_b", "merged": "merged", "deferred": "deferred"}
        user = session_user(request)
        db_exec(
            """
            UPDATE resilience_conflicts
            SET resolution_status=?, resolved_by=?, resolution_note=?, resolved_at=?
            WHERE id=?
            """,
            (
                status_map[req.resolution],
                user.get("id", "") if user else "",
                req.note,
                now_iso(),
                conflict_id,
            ),
        )
        return {"ok": True, "conflict_id": conflict_id, "resolution_status": status_map[req.resolution]}

    @app.get("/api/resilience/conflicts")
    async def api_list_conflicts(
        request: Request,
        brain_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ):
        require_master(request)
        limit = max(1, min(limit, 200))
        query = "SELECT * FROM resilience_conflicts WHERE 1=1"
        params: List[Any] = []
        if brain_id:
            query += " AND brain_id=?"
            params.append(brain_id)
        if status:
            query += " AND resolution_status=?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = db_all(query, tuple(params))
        return {
            "conflicts": [
                {
                    "id": r.get("id"),
                    "brain_id": r.get("brain_id"),
                    "conflict_type": r.get("conflict_type"),
                    "description": r.get("description"),
                    "version_a": json.loads(r.get("version_a_json", "{}")),
                    "version_b": json.loads(r.get("version_b_json", "{}")),
                    "resolution_status": r.get("resolution_status"),
                    "resolved_by": r.get("resolved_by"),
                    "resolution_note": r.get("resolution_note"),
                    "resolved_at": r.get("resolved_at"),
                    "created_at": r.get("created_at"),
                }
                for r in rows
            ],
            "total": len(rows),
        }

    @app.get("/api/resilience/assumptions")
    async def api_list_assumptions(
        request: Request,
        brain_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ):
        require_master(request)
        limit = max(1, min(limit, 200))
        query = "SELECT * FROM resilience_assumptions WHERE 1=1"
        params: List[Any] = []
        if brain_id:
            query += " AND brain_id=?"
            params.append(brain_id)
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = db_all(query, tuple(params))
        return {
            "assumptions": [
                {
                    "id": r.get("id"),
                    "output_meta_id": r.get("output_meta_id"),
                    "brain_id": r.get("brain_id"),
                    "assumption_text": r.get("assumption_text"),
                    "source_context": r.get("source_context"),
                    "status": r.get("status"),
                    "correction_text": r.get("correction_text"),
                    "corrected_by": r.get("corrected_by"),
                    "corrected_at": r.get("corrected_at"),
                    "created_at": r.get("created_at"),
                }
                for r in rows
            ],
            "total": len(rows),
        }

    @app.get("/api/resilience/overrides")
    async def api_list_overrides(
        request: Request,
        brain_id: Optional[str] = None,
        override_type: Optional[str] = None,
        limit: int = 50,
    ):
        require_master(request)
        limit = max(1, min(limit, 200))
        query = "SELECT * FROM resilience_overrides WHERE 1=1"
        params: List[Any] = []
        if brain_id:
            query += " AND brain_id=?"
            params.append(brain_id)
        if override_type:
            query += " AND override_type=?"
            params.append(override_type)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = db_all(query, tuple(params))
        return {
            "overrides": [
                {
                    "id": r.get("id"),
                    "brain_id": r.get("brain_id"),
                    "output_meta_id": r.get("output_meta_id"),
                    "override_type": r.get("override_type"),
                    "original_output": r.get("original_output"),
                    "corrected_output": r.get("corrected_output"),
                    "reroute_to_brain": r.get("reroute_to_brain"),
                    "override_reason": r.get("override_reason"),
                    "overridden_by": r.get("overridden_by"),
                    "created_at": r.get("created_at"),
                }
                for r in rows
            ],
            "total": len(rows),
        }

    @app.get("/api/resilience/recovery-log")
    async def api_recovery_log(
        request: Request,
        brain_id: Optional[str] = None,
        recovery_result: Optional[str] = None,
        limit: int = 50,
    ):
        require_master(request)
        limit = max(1, min(limit, 200))
        query = "SELECT * FROM resilience_recovery_log WHERE 1=1"
        params: List[Any] = []
        if brain_id:
            query += " AND brain_id=?"
            params.append(brain_id)
        if recovery_result:
            query += " AND recovery_result=?"
            params.append(recovery_result)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = db_all(query, tuple(params))
        return {
            "recovery_log": [
                {
                    "id": r.get("id"),
                    "brain_id": r.get("brain_id"),
                    "action": r.get("action"),
                    "failure_type": r.get("failure_type"),
                    "failure_detail": r.get("failure_detail"),
                    "recovery_strategy": r.get("recovery_strategy"),
                    "recovery_result": r.get("recovery_result"),
                    "partial_work": json.loads(r.get("partial_work_json", "{}")),
                    "retry_count": r.get("retry_count"),
                    "total_latency_ms": r.get("total_latency_ms"),
                    "created_at": r.get("created_at"),
                }
                for r in rows
            ],
            "total": len(rows),
        }

    @app.get("/api/resilience/dashboard")
    async def api_dashboard(request: Request):
        require_master(request)

        # Summary aggregates
        total_outputs = (db_one("SELECT COUNT(*) as c FROM resilience_output_meta", ()) or {}).get("c", 0)
        avg_conf_row = db_one("SELECT AVG(confidence_score) as a FROM resilience_output_meta", ())
        avg_confidence = round(float((avg_conf_row or {}).get("a") or 0.0), 4)

        risk_counts: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for level in risk_counts:
            row = db_one(
                "SELECT COUNT(*) as c FROM resilience_output_meta WHERE risk_level=?",
                (level,),
            )
            risk_counts[level] = (row or {}).get("c", 0)

        fallback_count = (
            db_one("SELECT COUNT(*) as c FROM resilience_output_meta WHERE fallback_used=1", ()) or {}
        ).get("c", 0)
        fallback_rate = round(fallback_count / total_outputs, 4) if total_outputs else 0.0

        total_assumptions = (db_one("SELECT COUNT(*) as c FROM resilience_assumptions", ()) or {}).get("c", 0)
        unconfirmed_assumptions = (
            db_one("SELECT COUNT(*) as c FROM resilience_assumptions WHERE status='unconfirmed'", ()) or {}
        ).get("c", 0)
        corrected_assumptions = (
            db_one("SELECT COUNT(*) as c FROM resilience_assumptions WHERE status='corrected'", ()) or {}
        ).get("c", 0)

        total_conflicts = (db_one("SELECT COUNT(*) as c FROM resilience_conflicts", ()) or {}).get("c", 0)
        unresolved_conflicts = (
            db_one("SELECT COUNT(*) as c FROM resilience_conflicts WHERE resolution_status='unresolved'", ()) or {}
        ).get("c", 0)

        total_recoveries = (db_one("SELECT COUNT(*) as c FROM resilience_recovery_log", ()) or {}).get("c", 0)
        success_recoveries = (
            db_one("SELECT COUNT(*) as c FROM resilience_recovery_log WHERE recovery_result='success'", ()) or {}
        ).get("c", 0)
        recovery_success_rate = round(success_recoveries / total_recoveries, 4) if total_recoveries else 0.0

        total_overrides = (db_one("SELECT COUNT(*) as c FROM resilience_overrides", ()) or {}).get("c", 0)
        override_breakdown: Dict[str, int] = {"approve": 0, "reject": 0, "edit": 0, "defer": 0, "reroute": 0}
        for otype in override_breakdown:
            row = db_one(
                "SELECT COUNT(*) as c FROM resilience_overrides WHERE override_type=?",
                (otype,),
            )
            override_breakdown[otype] = (row or {}).get("c", 0)

        # Recent high-risk outputs
        high_risk_rows = db_all(
            "SELECT * FROM resilience_output_meta WHERE risk_level IN ('high','critical') ORDER BY created_at DESC LIMIT 10",
            (),
        )
        recent_high_risk = [
            {
                "id": r.get("id"),
                "brain_id": r.get("brain_id"),
                "source_action": r.get("source_action"),
                "confidence_score": r.get("confidence_score"),
                "risk_level": r.get("risk_level"),
                "fallback_used": bool(r.get("fallback_used")),
                "created_at": r.get("created_at"),
            }
            for r in high_risk_rows
        ]

        # Recent unresolved conflicts
        unresolved_rows = db_all(
            "SELECT * FROM resilience_conflicts WHERE resolution_status='unresolved' ORDER BY created_at DESC LIMIT 10",
            (),
        )
        recent_unresolved = [
            {
                "id": r.get("id"),
                "brain_id": r.get("brain_id"),
                "conflict_type": r.get("conflict_type"),
                "description": r.get("description"),
                "created_at": r.get("created_at"),
            }
            for r in unresolved_rows
        ]

        # Recent recoveries
        recovery_rows = db_all(
            "SELECT * FROM resilience_recovery_log ORDER BY created_at DESC LIMIT 10",
            (),
        )
        recent_recoveries = [
            {
                "id": r.get("id"),
                "brain_id": r.get("brain_id"),
                "action": r.get("action"),
                "failure_type": r.get("failure_type"),
                "recovery_strategy": r.get("recovery_strategy"),
                "recovery_result": r.get("recovery_result"),
                "total_latency_ms": r.get("total_latency_ms"),
                "created_at": r.get("created_at"),
            }
            for r in recovery_rows
        ]

        # Brain confidence ranking
        brain_rank_rows = db_all(
            """
            SELECT brain_id, AVG(confidence_score) as avg_conf, COUNT(*) as total
            FROM resilience_output_meta
            WHERE brain_id != ''
            GROUP BY brain_id
            ORDER BY avg_conf DESC
            LIMIT 20
            """,
            (),
        )
        brain_confidence_ranking = [
            {
                "brain_id": r.get("brain_id"),
                "avg_confidence": round(float(r.get("avg_conf") or 0.0), 4),
                "total_outputs": r.get("total"),
            }
            for r in brain_rank_rows
        ]

        return {
            "summary": {
                "total_outputs": total_outputs,
                "avg_confidence": avg_confidence,
                "outputs_by_risk_level": risk_counts,
                "fallback_rate": fallback_rate,
                "total_assumptions": total_assumptions,
                "unconfirmed_assumptions": unconfirmed_assumptions,
                "corrected_assumptions": corrected_assumptions,
                "total_conflicts": total_conflicts,
                "unresolved_conflicts": unresolved_conflicts,
                "total_recoveries": total_recoveries,
                "recovery_success_rate": recovery_success_rate,
                "total_overrides": total_overrides,
                "override_breakdown": override_breakdown,
            },
            "recent_high_risk_outputs": recent_high_risk,
            "recent_unresolved_conflicts": recent_unresolved,
            "recent_recoveries": recent_recoveries,
            "brain_confidence_ranking": brain_confidence_ranking,
        }

    @app.get("/api/resilience/dashboard/{brain_id}")
    async def api_brain_dashboard(brain_id: str, request: Request):
        require_master(request)

        # Output confidence distribution
        outputs = db_all(
            "SELECT confidence_score, risk_level, fallback_used, latency_ms, created_at FROM resilience_output_meta WHERE brain_id=? ORDER BY created_at DESC LIMIT 100",
            (brain_id,),
        )

        total_outputs = len(outputs)
        avg_conf = round(sum(float(r.get("confidence_score") or 0) for r in outputs) / total_outputs, 4) if total_outputs else 0.0
        risk_dist: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for r in outputs:
            rl = r.get("risk_level", "low")
            if rl in risk_dist:
                risk_dist[rl] += 1

        # Assumption accuracy
        assumptions = db_all(
            "SELECT status FROM resilience_assumptions WHERE brain_id=?",
            (brain_id,),
        )
        assumption_stats = {"confirmed": 0, "corrected": 0, "unconfirmed": 0, "withdrawn": 0}
        for a in assumptions:
            s = a.get("status", "unconfirmed")
            if s in assumption_stats:
                assumption_stats[s] += 1

        # Conflict history
        conflicts = db_all(
            "SELECT id, conflict_type, description, resolution_status, created_at FROM resilience_conflicts WHERE brain_id=? ORDER BY created_at DESC LIMIT 20",
            (brain_id,),
        )

        # Recovery patterns
        recoveries = db_all(
            "SELECT failure_type, recovery_strategy, recovery_result, total_latency_ms, created_at FROM resilience_recovery_log WHERE brain_id=? ORDER BY created_at DESC LIMIT 20",
            (brain_id,),
        )

        # Override history
        overrides = db_all(
            "SELECT override_type, override_reason, overridden_by, created_at FROM resilience_overrides WHERE brain_id=? ORDER BY created_at DESC LIMIT 20",
            (brain_id,),
        )

        # Trend data: last 7 days (outputs per day)
        trend_rows = db_all(
            """
            SELECT substr(created_at, 1, 10) as day, COUNT(*) as count, AVG(confidence_score) as avg_conf
            FROM resilience_output_meta
            WHERE brain_id=? AND created_at >= date('now', '-7 days')
            GROUP BY day ORDER BY day
            """,
            (brain_id,),
        )
        trend = [
            {
                "day": r.get("day"),
                "output_count": r.get("count"),
                "avg_confidence": round(float(r.get("avg_conf") or 0.0), 4),
            }
            for r in trend_rows
        ]

        return {
            "brain_id": brain_id,
            "output_confidence": {
                "total": total_outputs,
                "avg_confidence": avg_conf,
                "risk_distribution": risk_dist,
            },
            "assumption_accuracy": assumption_stats,
            "conflict_history": [
                {
                    "id": r.get("id"),
                    "conflict_type": r.get("conflict_type"),
                    "description": r.get("description"),
                    "resolution_status": r.get("resolution_status"),
                    "created_at": r.get("created_at"),
                }
                for r in conflicts
            ],
            "recovery_patterns": [
                {
                    "failure_type": r.get("failure_type"),
                    "recovery_strategy": r.get("recovery_strategy"),
                    "recovery_result": r.get("recovery_result"),
                    "total_latency_ms": r.get("total_latency_ms"),
                    "created_at": r.get("created_at"),
                }
                for r in recoveries
            ],
            "override_history": [
                {
                    "override_type": r.get("override_type"),
                    "override_reason": r.get("override_reason"),
                    "overridden_by": r.get("overridden_by"),
                    "created_at": r.get("created_at"),
                }
                for r in overrides
            ],
            "trend_last_7_days": trend,
        }

    log.info("Resilience layer loaded: 5 tables, core helpers, and dashboard APIs registered")

    return {
        "compute_confidence": compute_confidence,
        "resilient_generate": resilient_generate,
        "detect_conflicts": detect_conflicts,
        "record_override": record_override,
    }
