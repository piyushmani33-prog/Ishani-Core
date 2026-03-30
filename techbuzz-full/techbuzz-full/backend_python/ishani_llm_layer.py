"""
Ishani LLM Layer — Centralized Intelligence Runtime
====================================================
Provides a unified LLM interface ("Ishani Mind") used by all brains for:
  - Free-form text generation
  - Structured JSON output
  - Classification
  - Summarization

Supports local (Ollama/llama.cpp/exl2), external, and hybrid modes.
All calls are safety-checked, disclosure-stripped, and logged.

Pattern: install_ishani_llm_layer(app, ctx) -> Dict[str, Any]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel


# ── Pydantic models ──────────────────────────────────────────────────────────

class LLMConfigRequest(BaseModel):
    mode: Optional[str] = None              # local_only | external_only | hybrid
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[float] = None
    cache_ttl_seconds: Optional[int] = None
    max_context_tokens: Optional[int] = None


class LLMTestRequest(BaseModel):
    prompt: str = "Hello, introduce yourself in one sentence."
    brain_id: str = "test"


# ── Install function ─────────────────────────────────────────────────────────

def install_ishani_llm_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    call_ollama = ctx["call_ollama"]
    extract_ollama_text = ctx["extract_ollama_text"]
    generate_text = ctx["generate_text"]
    sanitize_operator_multiline = ctx["sanitize_operator_multiline"]
    OLLAMA_MODEL = ctx["OLLAMA_MODEL"]
    AI_NAME = ctx["AI_NAME"]
    CORE_IDENTITY = ctx["CORE_IDENTITY"]
    log = ctx["log"]

    # ── Default config (env-driven) ──────────────────────────────────────────
    _runtime_config: Dict[str, Any] = {
        "mode": os.getenv("ISHANI_MODE", "hybrid"),
        "model_name": os.getenv("ISHANI_MODEL_NAME", "") or OLLAMA_MODEL or "llama3",
        "temperature": float(os.getenv("ISHANI_TEMPERATURE", "0.3")),
        "max_tokens": int(os.getenv("ISHANI_MAX_TOKENS", "1024")),
        "timeout_seconds": float(os.getenv("ISHANI_TIMEOUT_SECONDS", "45.0")),
        "cache_ttl_seconds": int(os.getenv("ISHANI_CACHE_TTL_SECONDS", "60")),
        "max_context_tokens": int(os.getenv("ISHANI_MAX_CONTEXT_TOKENS", "2000")),
    }

    # ── In-memory prompt cache (key -> {text, ts}) ───────────────────────────
    _prompt_cache: Dict[str, Any] = {}

    # ── DB table setup ───────────────────────────────────────────────────────
    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS ishani_llm_call_log (
                id              TEXT PRIMARY KEY,
                brain_id        TEXT,
                call_type       TEXT,
                prompt_sanitized TEXT,
                output_sanitized TEXT,
                task_id         TEXT,
                event_id        TEXT,
                model_used      TEXT,
                provider        TEXT,
                latency_ms      REAL,
                token_estimate  INTEGER,
                status          TEXT,
                created_at      TEXT
            )
            """
        )

    ensure_tables()

    # ── Auth helper ──────────────────────────────────────────────────────────
    def require_master(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user or user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master access required")
        return user

    # ── Config accessor ──────────────────────────────────────────────────────
    def _config() -> Dict[str, Any]:
        return dict(_runtime_config)

    # ── Token estimation (~4 chars/token) ────────────────────────────────────
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    # ── Prompt cache helpers ─────────────────────────────────────────────────
    def _cache_key(prompt: str, system: str, model: str) -> str:
        raw = f"{model}|{system}|{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_get(key: str) -> Optional[str]:
        entry = _prompt_cache.get(key)
        if not entry:
            return None
        ttl = _runtime_config.get("cache_ttl_seconds", 60)
        if time.monotonic() - entry["ts"] > ttl:
            _prompt_cache.pop(key, None)
            return None
        return entry["text"]

    def _cache_set(key: str, text: str) -> None:
        _prompt_cache[key] = {"text": text, "ts": time.monotonic()}

    # ── Logging helper ───────────────────────────────────────────────────────
    def _log_call(
        *,
        call_id: str,
        brain_id: str,
        call_type: str,
        prompt: str,
        output: str,
        task_id: str = "",
        event_id: str = "",
        model_used: str,
        provider: str,
        latency_ms: float,
        status: str,
    ) -> None:
        token_estimate = _estimate_tokens(prompt) + _estimate_tokens(output)
        try:
            db_exec(
                """
                INSERT INTO ishani_llm_call_log
                (id, brain_id, call_type, prompt_sanitized, output_sanitized,
                 task_id, event_id, model_used, provider, latency_ms,
                 token_estimate, status, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    call_id,
                    brain_id or "",
                    call_type,
                    prompt[:2000],
                    output[:2000],
                    task_id or "",
                    event_id or "",
                    model_used or "",
                    provider or "",
                    latency_ms,
                    token_estimate,
                    status,
                    now_iso(),
                ),
            )
        except Exception as exc:
            log.warning("ishani_llm_layer: failed to log call: %s", exc)

    # ── Disclosure strip ─────────────────────────────────────────────────────
    _REDACT_PATTERN = re.compile(
        r"(?i)(password|api[_\s]?key|secret|token)\s*[=:\"'\s][^\n\r]{0,200}"
    )

    def _disclosure_strip(text: str) -> str:
        return _REDACT_PATTERN.sub("[REDACTED]", text)

    # ── Safety guard (sync lexical fallback) ─────────────────────────────────
    _RISKY_TOKENS = (
        "password",
        "credit card",
        "cvv",
        "ssn",
        "aadhaar",
        "violent attack",
        "bomb recipe",
    )

    def _guard_text_sync(text: str) -> Dict[str, Any]:
        lower = text.lower()
        risky = any(token in lower for token in _RISKY_TOKENS)
        return {
            "allowed": not risky,
            "mode": "rule_fallback",
            "label": "blocked" if risky else "safe",
        }

    # ── Local backend call ───────────────────────────────────────────────────
    async def _call_local(
        *,
        prompt: str,
        system: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: float,
    ) -> Dict[str, Any]:
        """Try Ollama, then llama.cpp, then exl2."""
        llama_cpp_url = os.getenv("TECHBUZZ_LLAMA_CPP_URL", "").strip()
        exl2_url = os.getenv("TECHBUZZ_EXL2_URL", "").strip()

        # 1. Ollama
        try:
            result = await call_ollama(
                prompt=prompt,
                system=system,
                model=model,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            )
            return {"text": extract_ollama_text(result), "provider": f"ollama/{model}"}
        except Exception:
            pass

        # 2. llama.cpp server
        if llama_cpp_url:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            try:
                async with httpx.AsyncClient(
                    timeout=timeout_seconds + 5, follow_redirects=False
                ) as client:
                    resp = await client.post(
                        f"{llama_cpp_url.rstrip('/')}/v1/chat/completions", json=payload
                    )
                if resp.status_code == 200:
                    body = resp.json()
                    choices = body.get("choices") or []
                    if choices:
                        text = (choices[0].get("message") or {}).get("content", "") or ""
                        return {"text": text.strip(), "provider": f"llama_cpp/{model}"}
            except Exception:
                pass

        # 3. exl2 server
        if exl2_url:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            try:
                async with httpx.AsyncClient(
                    timeout=timeout_seconds + 5, follow_redirects=False
                ) as client:
                    resp = await client.post(
                        f"{exl2_url.rstrip('/')}/v1/chat/completions", json=payload
                    )
                if resp.status_code == 200:
                    body = resp.json()
                    choices = body.get("choices") or []
                    if choices:
                        text = (choices[0].get("message") or {}).get("content", "") or ""
                        return {"text": text.strip(), "provider": f"exl2/{model}"}
            except Exception:
                pass

        raise HTTPException(status_code=503, detail="Local LLM backend unavailable")

    # ── External backend call ────────────────────────────────────────────────
    async def _call_external(
        *, prompt: str, system: str, max_tokens: int
    ) -> Dict[str, Any]:
        return await generate_text(
            prompt,
            system=system,
            max_tokens=max_tokens,
            use_web_search=False,
            source="ishani_llm",
            workspace="ishani_llm",
        )

    # ── Core dispatcher ──────────────────────────────────────────────────────
    async def _run_llm(
        *,
        prompt: str,
        system: str,
        brain_id: str,
        call_type: str,
        task_id: str = "",
        event_id: str = "",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch to local / external / hybrid with caching, retry, and logging."""
        cfg = _config()
        opts = options or {}
        model = (opts.get("model_name") or "").strip() or cfg["model_name"]
        temperature = float(opts.get("temperature", cfg["temperature"]))
        max_tokens = int(opts.get("max_tokens", cfg["max_tokens"]))
        timeout_secs = float(opts.get("timeout_seconds", cfg["timeout_seconds"]))
        mode = (opts.get("mode") or "").strip() or cfg["mode"]

        # Cache lookup
        cache_key = _cache_key(prompt, system, model)
        cached = _cache_get(cache_key)
        if cached:
            return {"text": cached, "provider": "cache", "from_cache": True}

        call_id = new_id("llm")
        t0 = time.monotonic()
        text = ""
        provider = ""
        status = "error"

        if mode == "local_only":
            try:
                result = await _call_local(
                    prompt=prompt,
                    system=system,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout_seconds=timeout_secs,
                )
                text = result.get("text", "")
                provider = result.get("provider", "local")
                status = "success"
            except Exception as exc:
                log.warning("ishani_llm_layer: local call failed: %s", exc)

        elif mode == "external_only":
            try:
                result = await _call_external(
                    prompt=prompt, system=system, max_tokens=max_tokens
                )
                text = result.get("text", "")
                provider = result.get("provider", "external")
                status = "success"
            except Exception as exc:
                log.warning("ishani_llm_layer: external call failed: %s", exc)

        else:  # hybrid: local first, fallback to external
            try:
                result = await _call_local(
                    prompt=prompt,
                    system=system,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout_seconds=timeout_secs,
                )
                text = result.get("text", "")
                provider = result.get("provider", "local")
                status = "success"
            except Exception:
                try:
                    result = await _call_external(
                        prompt=prompt, system=system, max_tokens=max_tokens
                    )
                    text = result.get("text", "")
                    provider = result.get("provider", "external")
                    status = "fallback"
                except Exception as exc:
                    log.warning("ishani_llm_layer: all providers failed: %s", exc)
                    text = ""
                    provider = "none"
                    status = "error"

        latency_ms = (time.monotonic() - t0) * 1000.0

        # Safety guard
        guard = _guard_text_sync(text)
        if not guard.get("allowed", True):
            text = "[Content blocked by safety guardrail]"
            status = "blocked"

        # Disclosure strip
        text = _disclosure_strip(text)

        # Cache successful result
        if text and status in ("success", "fallback"):
            _cache_set(cache_key, text)

        # Log the call
        _log_call(
            call_id=call_id,
            brain_id=brain_id,
            call_type=call_type,
            prompt=sanitize_operator_multiline(prompt),
            output=text,
            task_id=task_id,
            event_id=event_id,
            model_used=model,
            provider=provider,
            latency_ms=latency_ms,
            status=status,
        )

        return {
            "text": text,
            "provider": provider,
            "call_id": call_id,
            "status": status,
        }

    # ── Context builder (RAG-lite) ────────────────────────────────────────────
    def build_context(
        *,
        brain_id: str,
        entity_id: str = "",
        namespace: str = "",
        max_context_tokens: Optional[int] = None,
    ) -> str:
        """
        Assemble a context string from:
          - brain_knowledge entries (matched by brain_id + namespace)
          - recent follow_up_tasks for the entity
          - recent recruitment_journey_events for the entity

        Respects token budget and excludes internal-only data.
        """
        cfg = _config()
        max_tokens = max_context_tokens or cfg.get("max_context_tokens", 2000)
        max_chars = max_tokens * 4  # ~4 chars per token
        parts: List[str] = []

        # Brain knowledge snippets (doctrine, rules, etc.)
        try:
            rows = db_all(
                "SELECT content FROM brain_knowledge "
                "WHERE brain_id=? AND namespace=? "
                "ORDER BY created_at DESC LIMIT 10",
                (brain_id, namespace or brain_id),
            )
            for r in rows:
                snippet = (r.get("content") or "").strip()
                if snippet:
                    parts.append(snippet)
        except Exception:
            pass

        # Recent follow-up tasks for the tracker row (entity)
        if entity_id:
            try:
                rows = db_all(
                    "SELECT candidate_name, position, reason, status "
                    "FROM follow_up_tasks "
                    "WHERE row_id=? ORDER BY created_at DESC LIMIT 5",
                    (entity_id,),
                )
                for r in rows:
                    parts.append(
                        f"Follow-up: {r.get('candidate_name','')} | "
                        f"{r.get('position','')} | "
                        f"{r.get('reason','')} | "
                        f"{r.get('status','')}"
                    )
            except Exception:
                pass

            # Recent recruitment journey events for the tracker row (entity)
            try:
                rows = db_all(
                    "SELECT event_type, summary "
                    "FROM recruitment_journey_events "
                    "WHERE row_id=? ORDER BY created_at DESC LIMIT 5",
                    (entity_id,),
                )
                for r in rows:
                    parts.append(
                        f"Journey: {r.get('event_type','')} — {r.get('summary','')}"
                    )
            except Exception:
                pass

        # Token-aware trim
        context_str = "\n".join(filter(None, parts))
        if len(context_str) > max_chars:
            context_str = context_str[:max_chars]
        return context_str

    # ── Unified LLM functions ─────────────────────────────────────────────────

    async def ishani_generate_text(
        input_text: str,
        *,
        context: str = "",
        brain_id: str = "default",
        options: Optional[Dict[str, Any]] = None,
        task_id: str = "",
        event_id: str = "",
    ) -> Dict[str, Any]:
        """Free-form text generation routed through the Ishani runtime."""
        system = (
            f"You are {AI_NAME}, the {CORE_IDENTITY} intelligence engine. "
            "Be helpful, factual, and concise."
        )
        prompt = f"{input_text}\n\nContext:\n{context}" if context else input_text
        return await _run_llm(
            prompt=prompt,
            system=system,
            brain_id=brain_id,
            call_type="generate_text",
            task_id=task_id,
            event_id=event_id,
            options=options,
        )

    async def ishani_generate_structured(
        input_text: str,
        *,
        schema: Dict[str, Any],
        context: str = "",
        brain_id: str = "default",
        options: Optional[Dict[str, Any]] = None,
        task_id: str = "",
        event_id: str = "",
    ) -> Dict[str, Any]:
        """JSON-structured output generation."""
        schema_str = json.dumps(schema, indent=2)
        system = (
            f"You are {AI_NAME}, the {CORE_IDENTITY} intelligence engine. "
            "Respond ONLY with valid JSON matching the given schema. "
            "No markdown, no explanation."
        )
        prompt = f"{input_text}\n\nRequired JSON schema:\n{schema_str}"
        if context:
            prompt += f"\n\nContext:\n{context}"
        result = await _run_llm(
            prompt=prompt,
            system=system,
            brain_id=brain_id,
            call_type="generate_structured",
            task_id=task_id,
            event_id=event_id,
            options=options,
        )
        # Attempt to parse JSON from the raw text
        raw_text = result.get("text", "")
        try:
            result["parsed"] = json.loads(raw_text)
        except Exception:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                try:
                    result["parsed"] = json.loads(match.group())
                except Exception:
                    result["parsed"] = None
            else:
                result["parsed"] = None
        return result

    async def ishani_classify(
        input_text: str,
        *,
        labels: List[str],
        context: str = "",
        brain_id: str = "default",
        options: Optional[Dict[str, Any]] = None,
        task_id: str = "",
        event_id: str = "",
    ) -> Dict[str, Any]:
        """Classify input into one of the given labels."""
        labels_str = ", ".join(labels)
        system = (
            f"You are {AI_NAME}, the {CORE_IDENTITY} classification engine. "
            f"Classify the input into exactly one of these labels: {labels_str}. "
            "Respond with ONLY the label name, nothing else."
        )
        prompt = input_text
        if context:
            prompt += f"\n\nContext:\n{context}"
        result = await _run_llm(
            prompt=prompt,
            system=system,
            brain_id=brain_id,
            call_type="classify",
            task_id=task_id,
            event_id=event_id,
            options=options,
        )
        raw = (result.get("text") or "").strip()
        matched = next(
            (label for label in labels if label.lower() in raw.lower()),
            labels[0] if labels else raw,
        )
        result["label"] = matched
        return result

    async def ishani_summarize(
        input_text: str,
        *,
        context: str = "",
        brain_id: str = "default",
        options: Optional[Dict[str, Any]] = None,
        task_id: str = "",
        event_id: str = "",
    ) -> Dict[str, Any]:
        """Summarize the provided text."""
        system = (
            f"You are {AI_NAME}, the {CORE_IDENTITY} summarization engine. "
            "Provide a concise, factual summary. Use bullet points where helpful."
        )
        prompt = f"Summarize the following:\n\n{input_text}"
        if context:
            prompt += f"\n\nAdditional context:\n{context}"
        return await _run_llm(
            prompt=prompt,
            system=system,
            brain_id=brain_id,
            call_type="summarize",
            task_id=task_id,
            event_id=event_id,
            options=options,
        )

    # ── API routes ────────────────────────────────────────────────────────────

    @app.get("/api/llm/config")
    async def llm_get_config(request: Request):
        require_master(request)
        return {"config": _config()}

    @app.post("/api/llm/config")
    async def llm_update_config(req: LLMConfigRequest, request: Request):
        require_master(request)
        patch: Dict[str, Any] = {}
        if req.mode is not None:
            if req.mode in {"local_only", "external_only", "hybrid"}:
                patch["mode"] = req.mode
        if req.model_name is not None:
            patch["model_name"] = (req.model_name or "").strip() or _runtime_config["model_name"]
        if req.temperature is not None:
            patch["temperature"] = max(0.0, min(float(req.temperature), 2.0))
        if req.max_tokens is not None:
            patch["max_tokens"] = max(64, min(int(req.max_tokens), 4096))
        if req.timeout_seconds is not None:
            patch["timeout_seconds"] = max(5.0, min(float(req.timeout_seconds), 300.0))
        if req.cache_ttl_seconds is not None:
            patch["cache_ttl_seconds"] = max(0, int(req.cache_ttl_seconds))
        if req.max_context_tokens is not None:
            patch["max_context_tokens"] = max(200, int(req.max_context_tokens))
        _runtime_config.update(patch)
        return {"message": "Ishani LLM runtime config updated.", "config": _config()}

    @app.post("/api/llm/test")
    async def llm_test(req: LLMTestRequest, request: Request):
        require_master(request)
        prompt = sanitize_operator_multiline(
            req.prompt or "Hello, introduce yourself in one sentence."
        )
        result = await ishani_generate_text(
            prompt,
            brain_id=req.brain_id or "test",
            options={"max_tokens": 150},
        )
        return {"result": result, "config": _config()}

    @app.get("/api/llm/health")
    async def llm_health(request: Request):
        cfg = _config()
        local_ok = False
        local_error = ""
        try:
            result = await call_ollama(
                prompt="ping",
                system="Respond with: pong",
                model=cfg["model_name"],
                max_tokens=10,
                timeout_seconds=8.0,
            )
            text = extract_ollama_text(result) or ""
            local_ok = bool(text)
        except Exception as exc:
            local_error = str(exc)[:200]
        return {
            "status": "ok" if local_ok else "degraded",
            "local_model": {
                "available": local_ok,
                "model": cfg["model_name"],
                "error": local_error,
            },
            "mode": cfg["mode"],
        }

    # ── Exported API ──────────────────────────────────────────────────────────
    return {
        "ishani_generate_text": ishani_generate_text,
        "ishani_generate_structured": ishani_generate_structured,
        "ishani_classify": ishani_classify,
        "ishani_summarize": ishani_summarize,
        "build_context": build_context,
    }
