import hashlib
import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


class InterpreterTranslateRequest(BaseModel):
    command: str = ""
    message: str = ""
    context: str = ""
    source: str = "manual"
    prefer_external: bool = False
    target_brain: Optional[str] = None


class BrainSkillLearnRequest(BaseModel):
    brain_id: str
    skill_name: str
    summary: str = ""
    source: str = "manual"
    proof: str = ""
    target_agent: str = ""


class BrainMutationProposeRequest(BaseModel):
    brain_id: str
    skill_name: Optional[str] = None
    target_agent: str = ""
    prefer_external: bool = False


def install_interpreter_brain_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_one = ctx["db_one"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    can_control_brain = ctx["can_control_brain"]
    find_brain = ctx["find_brain"]
    brain_hierarchy_payload = ctx["brain_hierarchy_payload"]
    broadcast_brain_lesson = ctx["broadcast_brain_lesson"]
    sanitize_operator_line = ctx["sanitize_operator_line"]
    sanitize_operator_multiline = ctx["sanitize_operator_multiline"]
    parse_json_blob = ctx["parse_json_blob"]
    get_state = ctx["get_state"]
    call_local_llm = ctx["call_local_llm"]
    ollama_status = ctx["ollama_status"]
    generate_text = ctx["generate_text"]
    provider_config = ctx["provider_config"]
    active_provider_label = ctx["active_provider_label"]
    external_ai_allowed_for_source = ctx["external_ai_allowed_for_source"]
    brain_aware_generate = ctx.get("brain_aware_generate")
    brain_aware_local_llm = ctx.get("brain_aware_local_llm")
    AI_NAME = ctx["AI_NAME"]
    CORE_IDENTITY = ctx["CORE_IDENTITY"]
    log = ctx["log"]

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_skill_ledger(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL,
                skill_key TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual',
                proof TEXT NOT NULL DEFAULT '',
                target_agent TEXT NOT NULL DEFAULT '',
                learned_at TEXT NOT NULL,
                UNIQUE(brain_id, skill_key)
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_mutation_ledger(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL,
                mutation_identity TEXT NOT NULL,
                trigger_skill_key TEXT NOT NULL,
                trigger_skill_name TEXT NOT NULL,
                target_agent TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                rewrite_scope_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'ready',
                first_mutation INTEGER NOT NULL DEFAULT 0,
                proposal_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_interpreter_events(
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target_brain_id TEXT NOT NULL DEFAULT '',
                command_text TEXT NOT NULL,
                translated_task TEXT NOT NULL DEFAULT '',
                operator_reply TEXT NOT NULL DEFAULT '',
                provider_chain_json TEXT NOT NULL DEFAULT '[]',
                used_external INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    def slug(value: str) -> str:
        clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in (value or "").strip())
        clean = "_".join(part for part in clean.split("_") if part)
        return clean[:80] or "skill"

    def brain_identity(brain_id: str) -> Dict[str, str]:
        digest = hashlib.sha256(brain_id.encode("utf-8")).hexdigest()
        return {
            "mutation_identity": f"{brain_id}.mutation.{digest[:12]}",
            "rewrite_signature": f"{brain_id}.forge.{digest[12:20]}",
        }

    def recent_skill_rows(brain_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if brain_ids:
            placeholders = ",".join("?" for _ in brain_ids)
            return db_all(
                f"""
                SELECT brain_id, skill_key, skill_name, summary, source, proof, target_agent, learned_at
                FROM brain_skill_ledger
                WHERE brain_id IN ({placeholders})
                ORDER BY learned_at DESC
                """,
                tuple(brain_ids),
            )
        return db_all(
            """
            SELECT brain_id, skill_key, skill_name, summary, source, proof, target_agent, learned_at
            FROM brain_skill_ledger
            ORDER BY learned_at DESC
            """
        )

    def mutation_rows(brain_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if brain_ids:
            placeholders = ",".join("?" for _ in brain_ids)
            return db_all(
                f"""
                SELECT brain_id, mutation_identity, trigger_skill_key, trigger_skill_name, target_agent, title, summary, rewrite_scope_json, status, first_mutation, proposal_json, created_at, updated_at
                FROM brain_mutation_ledger
                WHERE brain_id IN ({placeholders})
                ORDER BY created_at DESC
                """,
                tuple(brain_ids),
            )
        return db_all(
            """
            SELECT brain_id, mutation_identity, trigger_skill_key, trigger_skill_name, target_agent, title, summary, rewrite_scope_json, status, first_mutation, proposal_json, created_at, updated_at
            FROM brain_mutation_ledger
            ORDER BY created_at DESC
            """
        )

    def skill_digest(brain_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        skill_rows = recent_skill_rows(brain_ids)
        mutation_data = mutation_rows(brain_ids)
        output: Dict[str, Dict[str, Any]] = {}
        for row in skill_rows:
            brain_id = row["brain_id"]
            current = output.setdefault(
                brain_id,
                {
                    **brain_identity(brain_id),
                    "skill_count": 0,
                    "latest_skill": "",
                    "latest_skill_summary": "",
                    "latest_skill_at": "",
                    "latest_skill_target_agent": "",
                    "mutation_count": 0,
                    "mutation_state": "dormant",
                    "mutation_ready": False,
                    "next_mutation_skill": "",
                    "can_rewrite_descendants": False,
                    "last_mutation_at": "",
                    "last_mutation_title": "",
                },
            )
            current["skill_count"] += 1
            if not current["latest_skill"]:
                current["latest_skill"] = row.get("skill_name", "")
                current["latest_skill_summary"] = row.get("summary", "")
                current["latest_skill_at"] = row.get("learned_at", "")
                current["latest_skill_target_agent"] = row.get("target_agent", "")
        for row in mutation_data:
            brain_id = row["brain_id"]
            current = output.setdefault(
                brain_id,
                {
                    **brain_identity(brain_id),
                    "skill_count": 0,
                    "latest_skill": "",
                    "latest_skill_summary": "",
                    "latest_skill_at": "",
                    "latest_skill_target_agent": "",
                    "mutation_count": 0,
                    "mutation_state": "dormant",
                    "mutation_ready": False,
                    "next_mutation_skill": "",
                    "can_rewrite_descendants": False,
                    "last_mutation_at": "",
                    "last_mutation_title": "",
                },
            )
            current["mutation_count"] += 1
            if not current["last_mutation_at"]:
                current["last_mutation_at"] = row.get("updated_at") or row.get("created_at", "")
                current["last_mutation_title"] = row.get("title", "") or row.get("trigger_skill_name", "")
            if row.get("status") in {"ready", "proposed"}:
                current["mutation_ready"] = True
                current["next_mutation_skill"] = row.get("trigger_skill_name", "")
        for brain_id, current in output.items():
            current["can_rewrite_descendants"] = current["mutation_count"] > 0
            if current["mutation_ready"]:
                current["mutation_state"] = "ready_for_skill_mutation"
            elif current["mutation_count"] > 0:
                current["mutation_state"] = "adaptive"
            elif current["skill_count"] > 0:
                current["mutation_state"] = "learning"
        return output

    def brain_enrichment_snapshot(brain_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        return skill_digest(brain_ids)

    async def translate_command(
        command: str,
        *,
        context: str = "",
        source: str = "manual",
        prefer_external: bool = False,
        target_brain: Optional[str] = None,
    ) -> Dict[str, Any]:
        cleaned_command = sanitize_operator_multiline(command, "Ask for a clean operator instruction.")
        if not cleaned_command.strip():
            raise HTTPException(status_code=400, detail="A clear command is required")

        hierarchy = brain_hierarchy_payload()
        brain_rows = hierarchy.get("brains", [])
        if target_brain:
            brain_rows = [brain for brain in brain_rows if brain.get("id") == target_brain] or brain_rows
        lowered = cleaned_command.lower()
        guess = next((brain for brain in brain_rows if brain.get("id") == target_brain), None)
        if not guess:
            scored: List[tuple[int, Dict[str, Any]]] = []
            for brain in brain_rows:
                tokens = [
                    brain.get("name", "").lower(),
                    brain.get("layer", "").lower(),
                    brain.get("role_title", "").lower(),
                    brain.get("mission", "").lower(),
                    brain.get("assigned_task", "").lower(),
                ]
                score = sum(1 for token in tokens if token and token in lowered)
                if score:
                    scored.append((score, brain))
            scored.sort(key=lambda item: item[0], reverse=True)
            guess = scored[0][1] if scored else (brain_rows[0] if brain_rows else None)
        translation: Dict[str, Any] = {
            "target_brain_id": guess.get("id", "mother_brain") if guess else "mother_brain",
            "intent": "operator_instruction",
            "translated_task": cleaned_command,
            "response_style": "calm_human",
            "operator_reply": "I understood the instruction and routed it into the right brain lane.",
            "skill_name": "",
            "mutation_signal": False,
            "target_agent": "",
            "escalation_needed": False,
            "confidence": 0.68 if guess else 0.62,
        }
        system_prompt = (
            "You are the offline interpreter between the operator and the mother brain. "
            "Return strict JSON with keys: operator_reply, intent, skill_name, mutation_signal, target_agent, confidence. "
            "Keep operator_reply short, human, and practical."
        )
        guess_summary = (
            f"Target brain: {guess.get('id')} | {guess.get('name')} | role={guess.get('role_title', guess.get('layer', 'brain'))} | mission={guess.get('mission', guess.get('assigned_task', ''))}"
            if guess
            else "Target brain: mother_brain"
        )
        user_prompt = (
            f"Operator source: {source}\n"
            f"Context: {context or 'none'}\n"
            f"{guess_summary}\n\n"
            f"Operator command:\n{cleaned_command}"
        )
        local_provider_chain = ["built-in"]
        try:
            active_brain_id = (target_brain or "interpreter_brain")
            if brain_aware_local_llm:
                local = await brain_aware_local_llm(
                    user_prompt,
                    brain_id=active_brain_id,
                    max_tokens=96 if source == "voice" else 180,
                )
            else:
                local = await call_local_llm(
                    system=system_prompt,
                    prompt=user_prompt,
                    max_tokens=96 if source == "voice" else 180,
                )
            local_provider_chain = [local.get("provider", f"ollama/{local.get('model', 'local')}".strip("/"))]
            parsed = parse_json_blob(local.get("text", ""))
            if isinstance(parsed, dict):
                translation.update(parsed)
        except Exception as exc:
            log.warning("Interpreter local translation fallback: %s", exc)

        target_brain_id = sanitize_operator_line(str(translation.get("target_brain_id", target_brain or "mother_brain")), "mother_brain")
        translated_task = sanitize_operator_multiline(
            str(translation.get("translated_task", cleaned_command)),
            cleaned_command,
        )
        operator_reply = sanitize_operator_multiline(
            str(translation.get("operator_reply", "I understood the request and mapped it into the right lane.")),
            "I understood the request and mapped it into the right lane.",
        )
        skill_name = sanitize_operator_line(str(translation.get("skill_name", "")), "")
        target_agent_name = sanitize_operator_line(str(translation.get("target_agent", "")), "")
        mutation_signal = bool(translation.get("mutation_signal")) and bool(skill_name)
        provider_chain = list(local_provider_chain)
        external_reply = ""

        if (
            prefer_external
            and external_ai_allowed_for_source(source)
            and any(provider_config().get(name, {}).get("configured") for name in ("openai", "anthropic", "gemini"))
        ):
            try:
                external = await generate_text(
                    (
                        f"Rewrite this operator-facing response so it sounds natural, short, and human.\n\n"
                        f"Original response:\n{operator_reply}\n\n"
                        f"Translated task:\n{translated_task}"
                    ),
                    system="You are a concise interpreter bridge. Rewrite only the operator reply. Keep it under 80 words.",
                    max_tokens=140,
                    use_web_search=False,
                    source=source,
                    workspace="bridge",
                )
                if external.get("text"):
                    external_reply = sanitize_operator_multiline(external["text"], operator_reply)
                    provider_chain.append(external.get("provider", "external"))
                    operator_reply = external_reply
            except Exception as exc:
                log.warning("Interpreter external refinement skipped: %s", exc)

        target_brain_data = find_brain(target_brain_id)
        event = {
            "id": new_id("interp"),
            "source": source,
            "target_brain_id": target_brain_id,
            "command_text": cleaned_command[:2500],
            "translated_task": translated_task[:2500],
            "operator_reply": operator_reply[:1200],
            "provider_chain_json": json.dumps(provider_chain, ensure_ascii=False),
            "used_external": 1 if len(provider_chain) > 1 else 0,
            "created_at": now_iso(),
        }
        db_exec(
            """
            INSERT INTO brain_interpreter_events(id,source,target_brain_id,command_text,translated_task,operator_reply,provider_chain_json,used_external,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                event["id"],
                event["source"],
                event["target_brain_id"],
                event["command_text"],
                event["translated_task"],
                event["operator_reply"],
                event["provider_chain_json"],
                event["used_external"],
                event["created_at"],
            ),
        )
        return {
            "id": event["id"],
            "source": source,
            "target_brain_id": target_brain_id,
            "target_brain_name": target_brain_data.get("name", target_brain_id) if target_brain_data else target_brain_id,
            "intent": sanitize_operator_line(str(translation.get("intent", "operator_instruction")), "operator_instruction"),
            "translated_task": translated_task,
            "operator_reply": operator_reply,
            "skill_name": skill_name,
            "mutation_signal": mutation_signal,
            "target_agent": target_agent_name,
            "response_style": sanitize_operator_line(str(translation.get("response_style", "calm_human")), "calm_human"),
            "escalation_needed": bool(translation.get("escalation_needed")),
            "confidence": max(0.0, min(1.0, float(translation.get("confidence", 0.62) or 0.62))),
            "provider_chain": provider_chain,
            "used_external": len(provider_chain) > 1,
            "external_reply": external_reply,
        }

    def ensure_ready_mutation(brain_id: str, skill_key: str, skill_name: str, summary: str, target_agent: str = "") -> Dict[str, Any]:
        existing = db_one(
            """
            SELECT id, status FROM brain_mutation_ledger
            WHERE brain_id=? AND trigger_skill_key=?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (brain_id, skill_key),
        )
        if existing:
            return {"status": existing.get("status", "ready"), "created": False}
        mutation_id = brain_identity(brain_id)["mutation_identity"]
        first_mutation = 0 if db_one("SELECT id FROM brain_mutation_ledger WHERE brain_id=? LIMIT 1", (brain_id,)) else 1
        rewrite_scope = ["child_agent_prompts", "next_agent_code", "reviewed_plugins", "workflow_modules"]
        db_exec(
            """
            INSERT INTO brain_mutation_ledger(id,brain_id,mutation_identity,trigger_skill_key,trigger_skill_name,target_agent,title,summary,rewrite_scope_json,status,first_mutation,proposal_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id("mut"),
                brain_id,
                mutation_id,
                skill_key,
                skill_name[:180],
                target_agent[:180],
                f"{skill_name[:90]} Mutation Blueprint",
                summary[:800] or f"{brain_id} learned {skill_name} and unlocked the next reviewed mutation lane.",
                json.dumps(rewrite_scope, ensure_ascii=False),
                "ready",
                first_mutation,
                "{}",
                now_iso(),
                now_iso(),
            ),
        )
        return {"status": "ready", "created": True}

    def status_payload() -> Dict[str, Any]:
        skills = db_one("SELECT COUNT(*) AS count FROM brain_skill_ledger")
        mutations = db_one("SELECT COUNT(*) AS count FROM brain_mutation_ledger")
        ready = db_one("SELECT COUNT(*) AS count FROM brain_mutation_ledger WHERE status IN ('ready','proposed')")
        last_event = db_one(
            """
            SELECT source, target_brain_id, created_at, provider_chain_json
            FROM brain_interpreter_events
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        ollama = ollama_status()
        return {
            "mode": "offline_primary_manual_external",
            "offline_model": ollama.get("active_model", ""),
            "offline_ready": bool(ollama.get("available")),
            "offline_warm_ready": bool(ollama.get("warm_ready")),
            "offline_warming": bool(ollama.get("warming")),
            "offline_provider": ollama.get("label", "ollama/local"),
            "external_provider": active_provider_label(get_state()),
            "external_manual_only": True,
            "skill_ledgers": int(skills.get("count", 0) if skills else 0),
            "mutations": int(mutations.get("count", 0) if mutations else 0),
            "ready_mutations": int(ready.get("count", 0) if ready else 0),
            "last_event": last_event or {},
            "bridge_note": "Operator commands route through the local interpreter first. External refinement is human-triggered only.",
        }

    @app.get("/api/interpreter/status")
    async def interpreter_status():
        return status_payload()

    @app.post("/api/interpreter/translate")
    async def interpreter_translate(req: InterpreterTranslateRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        command_text = sanitize_operator_multiline(req.command or req.message, "")
        if not command_text.strip():
            raise HTTPException(status_code=400, detail="A clear command is required")
        result = await translate_command(
            command_text,
            context=req.context,
            source=req.source or "manual",
            prefer_external=bool(req.prefer_external),
            target_brain=req.target_brain,
        )
        return result

    @app.get("/api/brain/skill-map")
    async def brain_skill_map():
        hierarchy = brain_hierarchy_payload()
        enrich = brain_enrichment_snapshot([brain.get("id") for brain in hierarchy.get("brains", []) if brain.get("id")])
        return {"summary": status_payload(), "brains": enrich}

    @app.get("/api/brain/nlp-map")
    async def brain_nlp_map():
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        return {
            "summary": {
                **status_payload(),
                "total_brains": len(brains),
                "nlp_brains": len([brain for brain in brains if brain.get("nlp_enabled")]),
                "nlp_modules": sum(int(brain.get("nlp_modules", 0) or 0) for brain in brains),
            },
            "brains": [
                {
                    "id": brain.get("id"),
                    "name": brain.get("name"),
                    "layer": brain.get("layer"),
                    "role_title": brain.get("role_title"),
                    "nlp_status": brain.get("nlp_status", "embedded"),
                    "nlp_operator_style": brain.get("nlp_operator_style", "calm, human, precise, brief"),
                    "nlp_modules": int(brain.get("nlp_modules", 0) or 0),
                    "nlp_capabilities": brain.get("nlp_capabilities", []),
                    "nlp_entities": brain.get("nlp_entities", []),
                    "nlp_workflows": brain.get("nlp_workflows", []),
                    "nlp_summary": brain.get("nlp_summary", ""),
                }
                for brain in brains
            ],
        }

    @app.get("/api/brain/mutation/status")
    async def brain_mutation_status():
        hierarchy = brain_hierarchy_payload()
        enrich = brain_enrichment_snapshot([brain.get("id") for brain in hierarchy.get("brains", []) if brain.get("id")])
        return {"summary": status_payload(), "mutations": enrich}

    @app.post("/api/brain/learn-skill")
    async def brain_learn_skill(req: BrainSkillLearnRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        if not can_control_brain(user, req.brain_id):
            raise HTTPException(status_code=403, detail="Only the master can teach this brain directly")
        brain = find_brain(req.brain_id)
        if not brain:
            raise HTTPException(status_code=404, detail="Brain not found")
        skill_name = sanitize_operator_line(req.skill_name, "")
        if not skill_name:
            raise HTTPException(status_code=400, detail="A clear skill name is required")
        summary = sanitize_operator_multiline(req.summary, f"{brain['name']} learned {skill_name}.")
        skill_key = slug(skill_name)
        existing = db_one(
            "SELECT id, learned_at FROM brain_skill_ledger WHERE brain_id=? AND skill_key=?",
            (req.brain_id, skill_key),
        )
        created = False
        learned_at = now_iso()
        if not existing:
            db_exec(
                """
                INSERT INTO brain_skill_ledger(id,brain_id,skill_key,skill_name,summary,source,proof,target_agent,learned_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_id("skill"),
                    req.brain_id,
                    skill_key,
                    skill_name[:180],
                    summary[:1000],
                    sanitize_operator_line(req.source, "manual"),
                    sanitize_operator_multiline(req.proof, "")[:1200],
                    sanitize_operator_line(req.target_agent, "")[:180],
                    learned_at,
                ),
            )
            created = True
        mutation = ensure_ready_mutation(req.brain_id, skill_key, skill_name, summary, req.target_agent)
        lesson = broadcast_brain_lesson(
            title=f"{brain['name']} learned {skill_name}",
            summary=summary[:240],
            content=(
                f"Brain: {brain['name']}\n"
                f"Skill learned: {skill_name}\n"
                f"Summary: {summary}\n"
                f"Target agent: {req.target_agent or 'general'}\n"
                "This skill can now be used by the wider hierarchy when relevant."
            ),
            source_type="brain_skill_lesson",
            source_url=f"brain-skill://{req.brain_id}/{skill_key}",
            keywords=[skill_key, brain.get("layer", "brain"), brain["name"].lower()],
            target_brains=[brain["id"]] if not created else None,
            relevance=0.9,
        )
        return {
            "brain": brain["name"],
            "skill_name": skill_name,
            "created": created,
            "mutation_ready": mutation["status"] == "ready",
            "mutation_created": mutation["created"],
            "lesson_targets": lesson["targets"],
            "summary": status_payload(),
        }

    @app.post("/api/brain/mutation/propose")
    async def brain_mutation_propose(req: BrainMutationProposeRequest, request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        if not can_control_brain(user, req.brain_id):
            raise HTTPException(status_code=403, detail="Only the master can mutate this brain")
        brain = find_brain(req.brain_id)
        if not brain:
            raise HTTPException(status_code=404, detail="Brain not found")
        pending = db_one(
            """
            SELECT id, mutation_identity, trigger_skill_key, trigger_skill_name, target_agent, title, summary, rewrite_scope_json, first_mutation
            FROM brain_mutation_ledger
            WHERE brain_id=? AND status='ready'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (req.brain_id,),
        )
        if not pending and req.skill_name:
            ensure_ready_mutation(req.brain_id, slug(req.skill_name), sanitize_operator_line(req.skill_name, ""), "", req.target_agent)
            pending = db_one(
                """
                SELECT id, mutation_identity, trigger_skill_key, trigger_skill_name, target_agent, title, summary, rewrite_scope_json, first_mutation
                FROM brain_mutation_ledger
                WHERE brain_id=? AND status='ready'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (req.brain_id,),
            )
        if not pending:
            raise HTTPException(status_code=400, detail="No ready mutation exists for this brain. Teach a new skill first.")

        target_agent = sanitize_operator_line(req.target_agent or pending.get("target_agent", ""), "")
        rewrite_scope = json.loads(pending.get("rewrite_scope_json", "[]") or "[]")
        system_prompt = (
            f"You are {AI_NAME} drafting a reviewed mutation blueprint for a specialized brain. "
            "Return strict JSON with keys: title, summary, rewrite_scope, child_agent_identity, safeguards, next_checks, operator_reply."
        )
        user_prompt = (
            f"Brain: {brain.get('name')}\n"
            f"Role: {brain.get('role_title', brain.get('layer', 'brain'))}\n"
            f"Mission: {brain.get('mission', brain.get('assigned_task', ''))}\n"
            f"Trigger skill: {pending.get('trigger_skill_name')}\n"
            f"Target agent: {target_agent or 'next child agent'}\n"
            f"Rewrite scope: {', '.join(rewrite_scope)}\n"
            "Create a safe reviewed mutation blueprint. No stealth, no self-hiding, no uncontrolled spread."
        )
        proposal = {}
        try:
            local = await call_local_llm(system=system_prompt, prompt=user_prompt, max_tokens=220)
            proposal = parse_json_blob(local.get("text", "")) or {}
        except Exception as exc:
            log.warning("Local mutation blueprint fallback: %s", exc)
        if not proposal:
            proposal = {
                "title": pending.get("title") or f"{pending.get('trigger_skill_name')} Mutation Blueprint",
                "summary": pending.get("summary") or f"{brain['name']} can now revise the next child agent around {pending.get('trigger_skill_name')}.",
                "rewrite_scope": rewrite_scope,
                "child_agent_identity": f"{brain_identity(req.brain_id)['rewrite_signature']}.{slug(target_agent or pending.get('trigger_skill_name', 'agent'))}",
                "safeguards": [
                    "Mutation is review-only until the mother brain approves it.",
                    "Changes apply only to future child agents or explicit reviewed modules.",
                    "Every mutation stays visible in the mutation ledger.",
                ],
                "next_checks": ["Review scope", "Validate tests", "Approve rollout"],
                "operator_reply": "The mutation blueprint is ready for review.",
            }
        provider_chain = ["ollama/local"]
        if (
            req.prefer_external
            and external_ai_allowed_for_source("manual")
            and any(provider_config().get(name, {}).get("configured") for name in ("openai", "anthropic", "gemini"))
        ):
            try:
                external = await generate_text(
                    f"Summarize this mutation blueprint into 3 short human lines:\n{json.dumps(proposal, ensure_ascii=False)}",
                    system="You are a concise mutation-review assistant.",
                    max_tokens=180,
                    use_web_search=False,
                    source="manual",
                    workspace="bridge",
                )
                if external.get("text"):
                    proposal["operator_reply"] = sanitize_operator_multiline(external["text"], proposal.get("operator_reply", "The mutation blueprint is ready for review."))
                    provider_chain.append(external.get("provider", "external"))
            except Exception as exc:
                log.warning("External mutation refinement skipped: %s", exc)

        db_exec(
            """
            UPDATE brain_mutation_ledger
            SET target_agent=?, title=?, summary=?, proposal_json=?, status='proposed', updated_at=?
            WHERE id=?
            """,
            (
                target_agent or pending.get("target_agent", ""),
                sanitize_operator_line(str(proposal.get("title", pending.get("title", ""))), pending.get("title", ""))[:180],
                sanitize_operator_multiline(str(proposal.get("summary", pending.get("summary", ""))), pending.get("summary", ""))[:1200],
                json.dumps({**proposal, "provider_chain": provider_chain}, ensure_ascii=False),
                now_iso(),
                pending["id"],
            ),
        )
        return {
            "brain": brain["name"],
            "mutation_identity": pending["mutation_identity"],
            "trigger_skill": pending["trigger_skill_name"],
            "proposal": proposal,
            "provider_chain": provider_chain,
            "summary": status_payload(),
        }

    return {
        "translate_command": translate_command,
        "status_payload": status_payload,
        "brain_enrichment_snapshot": brain_enrichment_snapshot,
    }
