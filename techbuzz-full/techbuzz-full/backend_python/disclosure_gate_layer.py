"""
Disclosure Gate Layer — Controlled-disclosure output filter.

Sits between internal brain outputs and user-facing responses.  Filters based
on user role, current task context, product phase, and permission level.

Output policy enforced:
  ✗ Never expose: internal reasoning chains, raw system logs, irrelevant data,
    sensitive system-level knowledge.
  ✓ Always expose: actionable insights, clear outputs, human-readable results.

Every filtering decision is logged to an audit table for traceability.
"""

import json
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Sensitive patterns that must NEVER leak to non-master users
# ---------------------------------------------------------------------------

_REDACT_PATTERNS = [
    re.compile(r"(api[_-]?key|secret|password|token|credential)[\"']?\s*[:=]\s*[\"']?[^\s\"',}{]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),           # OpenAI-style key
    re.compile(r"AIza[A-Za-z0-9_-]{35}"),          # Google API key
    re.compile(r"ANTHROPIC_API_KEY\s*=\s*\S+", re.IGNORECASE),
]

# Keys in output dicts that indicate internal reasoning
_INTERNAL_KEYS = frozenset({
    "internal_reasoning", "debug_trace", "raw_log", "system_prompt",
    "error_traceback", "stack_trace", "internal_notes", "chain_of_thought",
    "provider_usage", "token_usage", "raw_llm_response",
})

# Role → maximum disclosure level mapping
_ROLE_DISCLOSURE_LEVEL: Dict[str, int] = {
    "master": 100,      # sees everything
    "operator": 80,
    "admin": 60,
    "member": 40,
    "viewer": 20,
    "public": 10,
}


class DisclosureCheckRequest(BaseModel):
    content: Dict[str, Any]
    user_role: str = "member"
    context: str = ""


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_disclosure_gate_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
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
            CREATE TABLE IF NOT EXISTS disclosure_audit_log (
                id            TEXT PRIMARY KEY,
                user_role     TEXT NOT NULL,
                context       TEXT NOT NULL DEFAULT '',
                input_keys    TEXT NOT NULL DEFAULT '[]',
                redacted_keys TEXT NOT NULL DEFAULT '[]',
                decision      TEXT NOT NULL DEFAULT 'allowed',
                created_at    TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    # -----------------------------------------------------------------------
    # Core filtering functions
    # -----------------------------------------------------------------------

    def _disclosure_level_for_role(role: str) -> int:
        return _ROLE_DISCLOSURE_LEVEL.get(role, _ROLE_DISCLOSURE_LEVEL["public"])

    def _scrub_sensitive_strings(text: str) -> str:
        """Replace known secret patterns with [REDACTED]."""
        for pat in _REDACT_PATTERNS:
            text = pat.sub("[REDACTED]", text)
        return text

    def filter_output(
        content: Dict[str, Any],
        *,
        user_role: str = "member",
        context: str = "",
        phase: str = "production",
    ) -> Dict[str, Any]:
        """Apply the disclosure gate to *content*.

        Returns a new dict with internal/sensitive keys removed and string
        values scrubbed of secret patterns.  Masters bypass most filters
        but sensitive credential strings are still scrubbed.
        """
        level = _disclosure_level_for_role(user_role)
        input_keys = list(content.keys())
        redacted_keys: List[str] = []
        filtered: Dict[str, Any] = {}

        for key, value in content.items():
            # Always strip internal keys for non-master users
            if key in _INTERNAL_KEYS and level < 100:
                redacted_keys.append(key)
                continue

            # Recursively filter nested dicts
            if isinstance(value, dict):
                value = filter_output(value, user_role=user_role, context=context, phase=phase)
            elif isinstance(value, str):
                # Scrub secrets from all string values regardless of role
                value = _scrub_sensitive_strings(value)
            elif isinstance(value, list):
                cleaned = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned.append(filter_output(item, user_role=user_role, context=context, phase=phase))
                    elif isinstance(item, str):
                        cleaned.append(_scrub_sensitive_strings(item))
                    else:
                        cleaned.append(item)
                value = cleaned

            filtered[key] = value

        # Audit log
        decision = "redacted" if redacted_keys else "allowed"
        db_exec(
            "INSERT INTO disclosure_audit_log (id, user_role, context, input_keys, redacted_keys, decision, created_at) VALUES (?,?,?,?,?,?,?)",
            (new_id("disc"), user_role, context, json.dumps(input_keys), json.dumps(redacted_keys), decision, now_iso()),
        )

        return filtered

    def filter_action_for_user(action: Dict[str, Any], user_role: str = "member") -> Dict[str, Any]:
        """Convenience wrapper: filter a single action_draft for user display."""
        return filter_output(action, user_role=user_role, context="action_display")

    def filter_task_for_user(task: Dict[str, Any], user_role: str = "member") -> Dict[str, Any]:
        """Convenience wrapper: filter a single task for user display."""
        return filter_output(task, user_role=user_role, context="task_display")

    # -----------------------------------------------------------------------
    # REST APIs
    # -----------------------------------------------------------------------

    @app.post("/api/disclosure/check")
    async def api_disclosure_check(body: DisclosureCheckRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        role = body.user_role or user.get("role", "member")
        filtered = filter_output(body.content, user_role=role, context=body.context)
        return {"ok": True, "filtered": filtered}

    @app.get("/api/disclosure/audit")
    async def api_disclosure_audit(request: Request, limit: int = 50):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master only")

        rows = db_all(
            "SELECT id, user_role, context, input_keys, redacted_keys, decision, created_at FROM disclosure_audit_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return {
            "ok": True,
            "audit": [
                {
                    "id": r[0],
                    "user_role": r[1],
                    "context": r[2],
                    "input_keys": json.loads(r[3] or "[]"),
                    "redacted_keys": json.loads(r[4] or "[]"),
                    "decision": r[5],
                    "created_at": r[6],
                }
                for r in rows
            ],
        }

    @app.get("/api/disclosure/policy")
    async def api_disclosure_policy(request: Request):
        """Return the current disclosure policy summary (public info)."""
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        return {
            "ok": True,
            "policy": {
                "never_expose": [
                    "internal reasoning chains",
                    "raw system logs",
                    "irrelevant data",
                    "sensitive system-level knowledge",
                    "API keys and credentials",
                ],
                "always_expose": [
                    "actionable insights",
                    "clear outputs",
                    "human-readable results",
                ],
                "role_levels": {role: level for role, level in _ROLE_DISCLOSURE_LEVEL.items()},
                "internal_keys_filtered": sorted(_INTERNAL_KEYS),
            },
        }

    # Export to ctx
    ctx["disclosure_filter_output"] = filter_output
    ctx["disclosure_filter_action"] = filter_action_for_user
    ctx["disclosure_filter_task"] = filter_task_for_user

    log.info("[DisclosureGate] layer installed")
    return ctx
