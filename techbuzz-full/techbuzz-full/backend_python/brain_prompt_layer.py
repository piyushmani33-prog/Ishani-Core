"""Brain Prompt Layer — FastAPI layer following the install_* pattern.

Provides:
  - brain_aware_generate: wrapper around generate_text with registry lookup
  - brain_aware_local_llm: wrapper around call_local_llm with registry lookup
  - API endpoints for the brain prompt registry
  - LLM call logging (brain_llm_log, brain_prompt_overrides tables)
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

from brain_prompt_registry import (
    BRAIN_REGISTRY,
    DOCTRINE_PACKS,
    build_brain_context,
    get_brain_profile,
    hash_system_prompt,
    shape_output_instructions,
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class BrainPromptPreviewRequest(BaseModel):
    task_context: str = ""
    event_context: str = ""
    shared_memory: Optional[Dict[str, Any]] = None


class BrainPromptOverrideRequest(BaseModel):
    field_name: str
    override_value: str
    created_by: str = ""


# ---------------------------------------------------------------------------
# Installer
# ---------------------------------------------------------------------------

def install_brain_prompt_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    db_one = ctx["db_one"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
    call_local_llm = ctx["call_local_llm"]
    log = ctx["log"]

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_llm_log(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL DEFAULT '',
                doctrine_keys_json TEXT NOT NULL DEFAULT '[]',
                system_prompt_hash TEXT NOT NULL DEFAULT '',
                prompt_preview TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                token_estimate INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_prompt_overrides(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                override_value TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT ''
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

    def _apply_overrides(brain_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Apply any runtime overrides stored in brain_prompt_overrides."""
        rows = db_all(
            "SELECT field_name, override_value FROM brain_prompt_overrides WHERE brain_id=? ORDER BY created_at DESC",
            (brain_id,),
        )
        seen: set = set()
        for row in rows:
            fname = row.get("field_name", "")
            if fname in seen or fname not in profile:
                continue
            seen.add(fname)
            profile[fname] = row.get("override_value", "")
        return profile

    def _token_estimate(text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return max(1, len(text) // 4)

    def _log_llm_call(
        *,
        brain_id: str,
        doctrine_keys: List[str],
        system_prompt: str,
        prompt: str,
        provider: str,
    ) -> None:
        try:
            db_exec(
                """
                INSERT INTO brain_llm_log(id, brain_id, doctrine_keys_json, system_prompt_hash, prompt_preview, provider, token_estimate, created_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    new_id("bll"),
                    brain_id,
                    json.dumps(doctrine_keys),
                    hash_system_prompt(system_prompt),
                    prompt[:200],
                    provider,
                    _token_estimate(system_prompt + prompt),
                    now_iso(),
                ),
            )
        except Exception as exc:
            log.warning("brain_llm_log insert failed: %s", exc)

    # ------------------------------------------------------------------
    # Core wrappers
    # ------------------------------------------------------------------
    async def brain_aware_generate(
        prompt: str,
        *,
        brain_id: str = "default",
        task_context: str = "",
        event_context: str = "",
        shared_memory: Optional[Dict[str, Any]] = None,
        max_tokens: int = 500,
        use_web_search: bool = False,
        source: str = "manual",
        workspace: str = "brain",
    ) -> Dict[str, Any]:
        """Wrapper around generate_text that loads the brain's registry entry first."""
        ctx_data = build_brain_context(
            brain_id,
            task_context=task_context,
            event_context=event_context,
            shared_memory=shared_memory,
        )
        # Apply any runtime overrides (non-system_prompt fields like tone/style)
        _apply_overrides(brain_id, ctx_data["profile"])

        full_system = ctx_data["system_prompt"]
        full_prompt = prompt
        if ctx_data.get("prompt_prefix"):
            full_prompt = ctx_data["prompt_prefix"] + "\n\n" + prompt

        _start = time.time()
        result = await generate_text(
            full_prompt,
            system=full_system,
            max_tokens=max_tokens,
            use_web_search=use_web_search,
            source=source,
            workspace=workspace,
        )
        _latency_ms = int((time.time() - _start) * 1000)
        provider = result.get("provider", "built-in")
        _log_llm_call(
            brain_id=brain_id,
            doctrine_keys=ctx_data["doctrine_keys"],
            system_prompt=full_system,
            prompt=full_prompt,
            provider=provider,
        )
        return {
            **result,
            "brain_id": brain_id,
            "doctrine_keys": ctx_data["doctrine_keys"],
            "profile_tone": ctx_data["profile"].get("tone", ""),
            "disclosure_level": ctx_data["profile"].get("disclosure_level", "operator_safe"),
            "latency_ms": _latency_ms,
        }

    async def brain_aware_local_llm(
        prompt: str,
        *,
        brain_id: str = "default",
        task_context: str = "",
        event_context: str = "",
        shared_memory: Optional[Dict[str, Any]] = None,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """Wrapper around call_local_llm that loads the brain's registry entry first."""
        profile = _apply_overrides(brain_id, get_brain_profile(brain_id))
        ctx_data = build_brain_context(
            brain_id,
            task_context=task_context,
            event_context=event_context,
            shared_memory=shared_memory,
        )
        full_system = ctx_data["system_prompt"]
        full_prompt = prompt
        if ctx_data.get("prompt_prefix"):
            full_prompt = ctx_data["prompt_prefix"] + "\n\n" + prompt

        _start = time.time()
        result = await call_local_llm(
            system=full_system,
            prompt=full_prompt,
            max_tokens=max_tokens,
        )
        _latency_ms = int((time.time() - _start) * 1000)
        provider = f"ollama/{result.get('model', 'local')}".strip("/")
        _log_llm_call(
            brain_id=brain_id,
            doctrine_keys=ctx_data["doctrine_keys"],
            system_prompt=full_system,
            prompt=full_prompt,
            provider=provider,
        )
        return {
            **result,
            "brain_id": brain_id,
            "doctrine_keys": ctx_data["doctrine_keys"],
            "profile_tone": profile.get("tone", ""),
            "disclosure_level": profile.get("disclosure_level", "operator_safe"),
            "latency_ms": _latency_ms,
        }

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    @app.get("/api/brain/prompt-registry")
    async def list_brain_registry(request: Request):
        user = require_user(request)
        is_master = user.get("role") == "master"
        result = []
        for bid, profile in BRAIN_REGISTRY.items():
            entry: Dict[str, Any] = {
                "brain_id": bid,
                "mission": profile.get("mission", ""),
                "tone": profile.get("tone", ""),
                "style": profile.get("style", ""),
                "disclosure_level": profile.get("disclosure_level", ""),
                "doctrine_keys": profile.get("doctrine_keys", []),
                "allowed_output_types": profile.get("allowed_output_types", []),
                "memory_namespaces": profile.get("memory_namespaces", []),
            }
            # Only admins see full system prompts
            if is_master:
                entry["system_prompt"] = profile.get("system_prompt", "")
            result.append(entry)
        return {"brains": result, "total": len(result)}

    @app.get("/api/brain/prompt-registry/doctrines")
    async def list_doctrine_packs(request: Request):
        user = require_user(request)
        is_master = user.get("role") == "master"
        result = []
        for key, text in DOCTRINE_PACKS.items():
            entry: Dict[str, Any] = {"key": key, "length_chars": len(text)}
            if is_master:
                entry["text"] = text
            result.append(entry)
        return {"doctrines": result, "total": len(result)}

    @app.get("/api/brain/prompt-registry/{brain_id}")
    async def get_brain_registry_entry(brain_id: str, request: Request):
        user = require_user(request)
        is_master = user.get("role") == "master"
        profile = get_brain_profile(brain_id)
        # get_brain_profile always returns a dict (default profile for unknown IDs)
        result: Dict[str, Any] = {
            "brain_id": profile.get("brain_id", brain_id),
            "mission": profile.get("mission", ""),
            "tone": profile.get("tone", ""),
            "style": profile.get("style", ""),
            "disclosure_level": profile.get("disclosure_level", ""),
            "doctrine_keys": profile.get("doctrine_keys", []),
            "allowed_output_types": profile.get("allowed_output_types", []),
            "memory_namespaces": profile.get("memory_namespaces", []),
            "output_instructions": shape_output_instructions(brain_id),
        }
        if is_master:
            result["system_prompt"] = profile.get("system_prompt", "")
        return result

    @app.post("/api/brain/prompt-registry/{brain_id}/preview")
    async def preview_brain_context(
        brain_id: str,
        req: BrainPromptPreviewRequest,
        request: Request,
    ):
        user = require_master(request)
        ctx_data = build_brain_context(
            brain_id,
            task_context=req.task_context,
            event_context=req.event_context,
            shared_memory=req.shared_memory,
        )
        return {
            "brain_id": brain_id,
            "system_prompt": ctx_data["system_prompt"],
            "prompt_prefix": ctx_data.get("prompt_prefix", ""),
            "doctrine_keys": ctx_data["doctrine_keys"],
            "profile": {
                k: v
                for k, v in ctx_data["profile"].items()
                if k != "system_prompt"
            },
        }

    @app.get("/api/brain/llm-log")
    async def get_llm_log(request: Request, brain_id: Optional[str] = None, limit: int = 50):
        require_master(request)
        limit = max(1, min(limit, 200))
        if brain_id:
            rows = db_all(
                "SELECT * FROM brain_llm_log WHERE brain_id=? ORDER BY created_at DESC LIMIT ?",
                (brain_id, limit),
            )
        else:
            rows = db_all(
                "SELECT * FROM brain_llm_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return {
            "entries": [
                {
                    "id": row.get("id", ""),
                    "brain_id": row.get("brain_id", ""),
                    "doctrine_keys": json.loads(row.get("doctrine_keys_json", "[]")),
                    "system_prompt_hash": row.get("system_prompt_hash", ""),
                    "prompt_preview": row.get("prompt_preview", ""),
                    "provider": row.get("provider", ""),
                    "token_estimate": row.get("token_estimate", 0),
                    "created_at": row.get("created_at", ""),
                }
                for row in rows
            ],
            "total": len(rows),
        }

    log.info("Brain prompt layer loaded: %d brain profiles, %d doctrine packs", len(BRAIN_REGISTRY), len(DOCTRINE_PACKS))

    return {
        "brain_aware_generate": brain_aware_generate,
        "brain_aware_local_llm": brain_aware_local_llm,
        "get_brain_profile": get_brain_profile,
        "build_brain_context": build_brain_context,
    }
