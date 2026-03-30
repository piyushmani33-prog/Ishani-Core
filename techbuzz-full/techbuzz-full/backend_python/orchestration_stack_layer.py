import logging
import hashlib
import json
import re
import time
import warnings
from importlib import metadata
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import HTTPException, Request
from pydantic import BaseModel

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)

try:
    import langchain  # noqa: F401
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnableLambda

    LANGCHAIN_AVAILABLE = True
except Exception:
    ChatPromptTemplate = None
    RunnableLambda = None
    LANGCHAIN_AVAILABLE = False

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except Exception:
    END = None
    StateGraph = None
    LANGGRAPH_AVAILABLE = False

try:
    from llama_index.core import Document, Settings
    from llama_index.core.indices.keyword_table import KeywordTableIndex

    LLAMAINDEX_AVAILABLE = True
except Exception:
    Document = None
    Settings = None
    KeywordTableIndex = None
    LLAMAINDEX_AVAILABLE = False


class OrchestrationAssistRequest(BaseModel):
    message: str
    target_brain: Optional[str] = None
    source: str = "manual"
    prefer_local: bool = True
    prefer_external: bool = False
    max_tokens: int = 500


class OrchestrationIndexQueryRequest(BaseModel):
    query: str
    target_brain: Optional[str] = None
    limit: int = 5


class OrchestrationState(TypedDict, total=False):
    message: str
    source: str
    target_brain: str
    normalized_message: str
    operator_brief: str
    keywords: List[str]
    retrieval: List[Dict[str, Any]]
    selected_brain: str
    retrieved_context: str
    workflow_steps: List[str]
    system: str
    prompt: str


def install_orchestration_stack_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    can_control_brain = ctx["can_control_brain"]
    find_brain = ctx["find_brain"]
    brain_hierarchy_payload = ctx["brain_hierarchy_payload"]
    sanitize_operator_line = ctx["sanitize_operator_line"]
    sanitize_operator_multiline = ctx["sanitize_operator_multiline"]
    call_local_llm = ctx["call_local_llm"]
    generate_text = ctx["generate_text"]
    provider_config = ctx["provider_config"]
    active_provider_label = ctx["active_provider_label"]
    ollama_status = ctx["ollama_status"]
    build_brain_context = ctx.get("build_brain_context")
    brain_aware_generate = ctx.get("brain_aware_generate")
    brain_aware_local_llm = ctx.get("brain_aware_local_llm")
    compute_confidence = ctx.get("compute_confidence")
    record_override = ctx.get("record_override")
    AI_NAME = ctx["AI_NAME"]
    CORE_IDENTITY = ctx["CORE_IDENTITY"]
    log = ctx["log"]
    logging.getLogger("llama_index").setLevel(logging.WARNING)
    logging.getLogger("llama_index.core").setLevel(logging.WARNING)

    index_cache: Dict[str, Any] = {
        "fingerprint": "",
        "built_at": "",
        "documents": 0,
        "brains": 0,
        "index": None,
        "documents_payload": [],
    }
    graph_cache: Dict[str, Any] = {"app": None, "nodes": ["normalize", "retrieve", "route", "prompt"]}

    def package_version(name: str) -> str:
        try:
            return metadata.version(name)
        except Exception:
            return ""

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS orchestration_runs(
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual',
                target_brain TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                normalized_message TEXT NOT NULL DEFAULT '',
                selected_brain TEXT NOT NULL DEFAULT '',
                stack_json TEXT NOT NULL DEFAULT '{}',
                retrieved_json TEXT NOT NULL DEFAULT '[]',
                response_text TEXT NOT NULL DEFAULT '',
                provider_label TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    def require_user(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        return user

    def safe_split(text: str) -> List[str]:
        return [part.strip() for part in re.split(r"[\n\r]+", text or "") if part.strip()]

    def keyword_list(text: str, *, limit: int = 12) -> List[str]:
        tokens: List[str] = []
        seen = set()
        for token in re.findall(r"[a-zA-Z0-9_+#/.:-]{3,}", text or ""):
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            tokens.append(lowered)
            if len(tokens) >= limit:
                break
        return tokens

    def brain_doc(brain: Dict[str, Any]) -> Dict[str, Any]:
        capabilities = ", ".join(brain.get("nlp_capabilities", [])[:6])
        workflows = ", ".join(brain.get("nlp_workflows", [])[:6])
        responsibilities = brain.get("responsibilities", [])[:6]
        learning_targets = brain.get("learning_targets", [])[:6]
        growth_targets = brain.get("growth_targets", [])[:6]
        lines = [
            f"Brain: {brain.get('name', '')}",
            f"Brain ID: {brain.get('id', '')}",
            f"Layer: {brain.get('layer', '')}",
            f"Domain: {brain.get('domain', '')}",
            f"Role Title: {brain.get('role_title', '')}",
            f"Mission: {brain.get('mission', '')}",
            f"Scope: {brain.get('real_world_scope', '')}",
            f"Assigned Task: {brain.get('assigned_task', '')}",
            f"Motivation: {brain.get('motivation', '')}",
            f"NLP Summary: {brain.get('nlp_summary', '')}",
            f"NLP Capabilities: {capabilities}",
            f"NLP Workflows: {workflows}",
            f"Responsibilities: {', '.join(str(item) for item in responsibilities)}",
            f"Learning Targets: {', '.join(str(item) for item in learning_targets)}",
            f"Growth Targets: {', '.join(str(item) for item in growth_targets)}",
        ]
        text = "\n".join(line for line in lines if line.rstrip(": ").strip())
        return {
            "brain_id": brain.get("id", ""),
            "name": brain.get("name", ""),
            "layer": brain.get("layer", ""),
            "role_title": brain.get("role_title", ""),
            "domain": brain.get("domain", ""),
            "text": text,
        }

    def hierarchy_documents() -> List[Dict[str, Any]]:
        hierarchy = brain_hierarchy_payload()
        return [brain_doc(brain) for brain in hierarchy.get("brains", []) if brain.get("id")]

    def hierarchy_fingerprint(docs: List[Dict[str, Any]]) -> str:
        material = "\n".join(f"{item['brain_id']}|{item['text']}" for item in docs)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def ensure_index(force: bool = False) -> Dict[str, Any]:
        docs = hierarchy_documents()
        fingerprint = hierarchy_fingerprint(docs)
        if (
            not force
            and index_cache.get("index") is not None
            and index_cache.get("fingerprint") == fingerprint
        ):
            return index_cache
        if not LLAMAINDEX_AVAILABLE:
            index_cache.update(
                {
                    "fingerprint": fingerprint,
                    "built_at": now_iso(),
                    "documents": len(docs),
                    "brains": len(docs),
                    "index": None,
                    "documents_payload": docs,
                }
            )
            return index_cache
        Settings.llm = None
        index_documents = [
            Document(
                text=item["text"],
                metadata={
                    "brain_id": item["brain_id"],
                    "name": item["name"],
                    "layer": item["layer"],
                    "role_title": item["role_title"],
                    "domain": item["domain"],
                },
            )
            for item in docs
        ]
        index_cache.update(
            {
                "fingerprint": fingerprint,
                "built_at": now_iso(),
                "documents": len(index_documents),
                "brains": len(docs),
                "index": KeywordTableIndex.from_documents(index_documents),
                "documents_payload": docs,
            }
        )
        return index_cache

    def ranked_retrieval(query: str, target_brain: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        state = ensure_index()
        docs = state.get("documents_payload", [])
        candidate_rows: List[Dict[str, Any]] = []
        query_tokens = set(keyword_list(query, limit=24))

        if LLAMAINDEX_AVAILABLE and state.get("index") is not None:
            try:
                retriever = state["index"].as_retriever()
                retrieval = retriever.retrieve(query)
                for item in retrieval:
                    node = getattr(item, "node", None)
                    text = getattr(node, "text", "") if node else ""
                    metadata = getattr(node, "metadata", {}) if node else {}
                    candidate_rows.append(
                        {
                            "brain_id": metadata.get("brain_id", ""),
                            "name": metadata.get("name", ""),
                            "layer": metadata.get("layer", ""),
                            "role_title": metadata.get("role_title", ""),
                            "domain": metadata.get("domain", ""),
                            "text": text,
                        }
                    )
            except Exception as exc:
                log.warning("LlamaIndex retrieval fallback activated: %s", exc)

        if not candidate_rows:
            candidate_rows = docs

        ranked: List[Dict[str, Any]] = []
        seen = set()
        for row in candidate_rows:
            brain_id = row.get("brain_id", "")
            if not brain_id or brain_id in seen:
                continue
            text = row.get("text", "")
            text_tokens = set(keyword_list(text, limit=48))
            lexical = len(query_tokens & text_tokens)
            score = lexical
            if target_brain and brain_id == target_brain:
                score += 100
            if any(token in (row.get("domain", "") or "").lower() for token in query_tokens):
                score += 8
            if any(token in (row.get("role_title", "") or "").lower() for token in query_tokens):
                score += 6
            ranked.append(
                {
                    "brain_id": brain_id,
                    "name": row.get("name", ""),
                    "layer": row.get("layer", ""),
                    "role_title": row.get("role_title", ""),
                    "domain": row.get("domain", ""),
                    "score": score,
                    "snippet": " ".join(safe_split(text)[:5])[:280],
                }
            )
            seen.add(brain_id)
        ranked.sort(key=lambda item: (item["score"], item["brain_id"]), reverse=True)
        return ranked[: max(1, min(limit, 8))]

    def langchain_packet(message: str, target_brain: str = "") -> Dict[str, Any]:
        normalized = sanitize_operator_multiline(message or "")
        if not LANGCHAIN_AVAILABLE or ChatPromptTemplate is None or RunnableLambda is None:
            return {
                "normalized_message": normalized,
                "operator_brief": sanitize_operator_line(normalized[:180]),
                "keywords": keyword_list(normalized),
            }
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You normalize operator requests for a living AI system. Keep the request direct, structured, and execution-ready.",
                ),
                (
                    "human",
                    "Target brain: {target_brain}\nOperator message: {message}\nReturn a compact dispatch packet.",
                ),
            ]
        )
        chain = prompt | RunnableLambda(
            lambda prompt_value: {
                "dispatch_text": "\n".join(message.content for message in prompt_value.to_messages()),
            }
        )
        payload = chain.invoke({"target_brain": target_brain or "auto", "message": normalized})
        dispatch_text = sanitize_operator_multiline(payload.get("dispatch_text", normalized))
        return {
            "normalized_message": normalized,
            "operator_brief": sanitize_operator_line(dispatch_text.replace("Operator message:", "").strip()[:220]),
            "keywords": keyword_list(dispatch_text),
        }

    def route_brain(target_brain: str, retrieval: List[Dict[str, Any]], message: str) -> str:
        if target_brain and find_brain(target_brain):
            return target_brain
        heuristics = {
            "tool_ats_kanban": {"candidate", "recruit", "resume", "ats", "interview", "tracker", "ack", "screening", "sourcing"},
            "tool_accounts_automation": {"invoice", "tax", "ledger", "account", "gst", "tds", "payment"},
            "tool_network_scanner": {"network", "signal", "competitor", "market", "client", "intel", "relationship"},
            "tool_document_studio": {"document", "pdf", "docx", "excel", "sheet", "tracker", "export"},
            "tool_provider_router": {"provider", "model", "ollama", "openai", "gemini", "anthropic"},
            "machine_voice_mesh": {"voice", "listen", "speech", "mic", "call"},
            "interpreter_brain": {"translate", "interpreter", "explain", "respond"},
            "domain_development": {"code", "develop", "debug", "deploy", "rollout", "implementation"},
            "domain_lab": {"research", "experiment", "mutation", "learning", "knowledge"},
        }
        tokens = set(keyword_list(message, limit=18))
        best_id = ""
        best_score = -1
        for brain_id, token_bank in heuristics.items():
            score = len(tokens & token_bank)
            if score > best_score and find_brain(brain_id):
                best_score = score
                best_id = brain_id
        if best_score > 0:
            return best_id
        if retrieval:
            return retrieval[0].get("brain_id", "") or "interpreter_brain"
        return "interpreter_brain"

    def build_prompt_payload(state: OrchestrationState) -> Dict[str, str]:
        target_brain = find_brain(state.get("selected_brain", "")) or {}
        selected_brain_id = state.get("selected_brain", "")
        retrieval_text = "\n".join(
            f"- {item.get('name', item.get('brain_id', ''))}: {item.get('snippet', '')}"
            for item in state.get("retrieval", [])[:4]
        )
        workflow_steps = "\n".join(f"- {step}" for step in state.get("workflow_steps", []))
        _default_workflow = "- Understand the request.\n- Answer directly.\n- Keep the system aligned."

        if build_brain_context and selected_brain_id:
            brain_ctx = build_brain_context(selected_brain_id)
            system = sanitize_operator_multiline(brain_ctx["system_prompt"]).strip()
        else:
            system = sanitize_operator_multiline(
                f"""
You are {AI_NAME}, the living operating intelligence of {CORE_IDENTITY}.
Respond like a sharp human operator, not a ceremonial narrator.
Speak clearly, directly, and only as long as needed.
Primary execution brain: {target_brain.get('name', state.get('selected_brain', 'Interpreter Bridge Brain'))}
Brain role: {target_brain.get('role_title', '')}
Brain mission: {target_brain.get('mission', '')}
"""
            ).strip()

        prompt = sanitize_operator_multiline(
            f"""
Operator request:
{state.get('normalized_message', '')}

Interpreter brief:
{state.get('operator_brief', '')}

Retrieved brain context:
{retrieval_text or '- No retrieved context available.'}

Suggested workflow:
{workflow_steps or _default_workflow}

Deliver:
- a precise answer
- next action if needed
- no filler
"""
        ).strip()
        return {"system": system, "prompt": prompt}

    def compile_graph():
        if graph_cache.get("app") is not None or not LANGGRAPH_AVAILABLE or StateGraph is None:
            return graph_cache.get("app")

        def normalize_node(state: OrchestrationState) -> OrchestrationState:
            packet = langchain_packet(state.get("message", ""), state.get("target_brain", ""))
            return {
                "normalized_message": packet.get("normalized_message", ""),
                "operator_brief": packet.get("operator_brief", ""),
                "keywords": packet.get("keywords", []),
            }

        def retrieve_node(state: OrchestrationState) -> OrchestrationState:
            retrieval = ranked_retrieval(
                state.get("normalized_message", state.get("message", "")),
                target_brain=state.get("target_brain", ""),
                limit=5,
            )
            return {
                "retrieval": retrieval,
                "retrieved_context": "\n".join(item.get("snippet", "") for item in retrieval[:4]),
            }

        def route_node(state: OrchestrationState) -> OrchestrationState:
            selected = route_brain(
                state.get("target_brain", ""),
                state.get("retrieval", []),
                state.get("normalized_message", state.get("message", "")),
            )
            workflows = [
                "Interpret the request in operational language.",
                "Pull only the most relevant brain context.",
                "Respond briefly with action-ready guidance.",
            ]
            if selected.startswith("tool_ats") or "candidate" in state.get("normalized_message", "").lower():
                workflows.append("Keep recruiter-facing output precise and tracker-safe.")
            return {"selected_brain": selected, "workflow_steps": workflows}

        def prompt_node(state: OrchestrationState) -> OrchestrationState:
            return build_prompt_payload(state)

        graph = StateGraph(OrchestrationState)
        graph.add_node("normalize", normalize_node)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("route", route_node)
        graph.add_node("prompt", prompt_node)
        graph.set_entry_point("normalize")
        graph.add_edge("normalize", "retrieve")
        graph.add_edge("retrieve", "route")
        graph.add_edge("route", "prompt")
        graph.add_edge("prompt", END)
        graph_cache["app"] = graph.compile()
        return graph_cache["app"]

    def recent_runs(limit: int = 12) -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT user_id, source, target_brain, selected_brain, message, normalized_message, provider_label, created_at
            FROM orchestration_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "user_id": row.get("user_id", ""),
                "source": row.get("source", "manual"),
                "target_brain": row.get("target_brain", ""),
                "selected_brain": row.get("selected_brain", ""),
                "message": row.get("message", "")[:180],
                "normalized_message": row.get("normalized_message", "")[:180],
                "provider": row.get("provider_label", ""),
                "created_at": row.get("created_at", ""),
            }
            for row in rows
        ]

    def status_payload() -> Dict[str, Any]:
        index_state = ensure_index()
        providers = provider_config()
        return {
            "installed": {
                "langchain": {
                    "available": LANGCHAIN_AVAILABLE,
                    "version": package_version("langchain"),
                    "role": "Prompt normalization and orchestration packets.",
                },
                "langgraph": {
                    "available": LANGGRAPH_AVAILABLE,
                    "version": package_version("langgraph"),
                    "role": "Live state routing across execution stages.",
                },
                "llamaindex": {
                    "available": LLAMAINDEX_AVAILABLE,
                    "version": package_version("llama-index"),
                    "role": "Offline-safe retrieval index across brain knowledge.",
                },
            },
            "graph": {
                "ready": LANGGRAPH_AVAILABLE,
                "nodes": graph_cache.get("nodes", []),
            },
            "index": {
                "ready": LLAMAINDEX_AVAILABLE,
                "documents": int(index_state.get("documents", 0) or 0),
                "brains": int(index_state.get("brains", 0) or 0),
                "built_at": index_state.get("built_at", ""),
                "fingerprint": index_state.get("fingerprint", "")[:12],
            },
            "active_provider": active_provider_label(),
            "local_lane": ollama_status(),
            "provider_modes": {
                "ollama": providers.get("ollama", {}),
                "openai": providers.get("openai", {}),
                "gemini": providers.get("gemini", {}),
                "anthropic": providers.get("anthropic", {}),
            },
            "recent_runs": recent_runs(),
        }

    async def generate_orchestrated_reply(
        user: Dict[str, Any],
        req: OrchestrationAssistRequest,
    ) -> Dict[str, Any]:
        start_time = time.time()
        target_brain = (req.target_brain or "").strip()
        if target_brain and not can_control_brain(user, target_brain):
            target_brain = "interpreter_brain"
        initial_state: OrchestrationState = {
            "message": sanitize_operator_multiline(req.message or ""),
            "source": (req.source or "manual").strip().lower() or "manual",
            "target_brain": target_brain,
        }
        if LANGGRAPH_AVAILABLE:
            graph = compile_graph()
            state = graph.invoke(initial_state)
        else:
            packet = langchain_packet(initial_state["message"], target_brain)
            retrieval = ranked_retrieval(packet["normalized_message"], target_brain=target_brain, limit=5)
            selected = route_brain(target_brain, retrieval, packet["normalized_message"])
            built = build_prompt_payload(
                {
                    **initial_state,
                    **packet,
                    "retrieval": retrieval,
                    "selected_brain": selected,
                    "workflow_steps": [
                        "Interpret the request in operational language.",
                        "Pull the most relevant brain context.",
                        "Respond with concise action-ready guidance.",
                    ],
                }
            )
            state = {
                **initial_state,
                **packet,
                "retrieval": retrieval,
                "selected_brain": selected,
                **built,
            }

        # Ensure a non-empty brain ID for registry lookup; fall back to interpreter_brain
        selected_brain_id = state.get("selected_brain", "") or "interpreter_brain"
        max_tok = max(200, min(req.max_tokens, 900))

        generated: Dict[str, Any]
        if req.prefer_local:
            try:
                if brain_aware_local_llm:
                    local = await brain_aware_local_llm(
                        state.get("prompt", ""),
                        brain_id=selected_brain_id,
                        max_tokens=max_tok,
                    )
                    generated = {
                        "text": local.get("text", ""),
                        "provider": local.get("provider", f"ollama/{local.get('model', '')}".strip("/")),
                        "usage": local.get("usage", {}),
                    }
                else:
                    local = await call_local_llm(
                        system=state.get("system", ""),
                        prompt=state.get("prompt", ""),
                        max_tokens=max_tok,
                    )
                    generated = {
                        "text": local.get("text", ""),
                        "provider": f"ollama/{local.get('model', '')}".strip("/"),
                        "usage": local.get("usage", {}),
                    }
            except HTTPException:
                if brain_aware_generate:
                    generated = await brain_aware_generate(
                        state.get("prompt", ""),
                        brain_id=selected_brain_id,
                        max_tokens=max_tok,
                        use_web_search=False,
                        source=req.source or "manual",
                        workspace="orchestration",
                    )
                else:
                    generated = await generate_text(
                        state.get("prompt", ""),
                        system=state.get("system", ""),
                        max_tokens=max_tok,
                        use_web_search=False,
                        source=req.source or "manual",
                        workspace="orchestration",
                    )
        else:
            if brain_aware_generate:
                generated = await brain_aware_generate(
                    state.get("prompt", ""),
                    brain_id=selected_brain_id,
                    max_tokens=max_tok,
                    use_web_search=False,
                    source=req.source or "manual",
                    workspace="orchestration",
                )
            else:
                generated = await generate_text(
                    state.get("prompt", ""),
                    system=state.get("system", ""),
                    max_tokens=max_tok,
                    use_web_search=False,
                    source=req.source or "manual",
                    workspace="orchestration",
                )

        response_text = sanitize_operator_multiline(generated.get("text", "")).strip()
        resilience_meta: Dict[str, Any] = {}
        if compute_confidence:
            resilience_meta = compute_confidence(
                brain_id=state.get("selected_brain", ""),
                source_action="orchestration_assist",
                input_text=state.get("message", ""),
                output_text=response_text,
                provider=generated.get("provider", ""),
                fallback_used="fallback" in generated.get("provider", "").lower(),
                provider_chain=[generated.get("provider", "")],
                latency_ms=int((time.time() - start_time) * 1000),
            )
        db_exec(
            """
            INSERT INTO orchestration_runs(
                id, user_id, source, target_brain, message, normalized_message, selected_brain,
                stack_json, retrieved_json, response_text, provider_label, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id("orc"),
                user.get("id", ""),
                state.get("source", "manual"),
                state.get("target_brain", ""),
                state.get("message", ""),
                state.get("normalized_message", ""),
                state.get("selected_brain", ""),
                json.dumps(
                    {
                        "langchain": LANGCHAIN_AVAILABLE,
                        "langgraph": LANGGRAPH_AVAILABLE,
                        "llamaindex": LLAMAINDEX_AVAILABLE,
                    }
                ),
                json.dumps(state.get("retrieval", [])),
                response_text,
                generated.get("provider", "built-in"),
                now_iso(),
            ),
        )
        return {
            "message": response_text,
            "provider": generated.get("provider", "built-in"),
            "selected_brain": state.get("selected_brain", ""),
            "target_brain": state.get("target_brain", ""),
            "normalized_message": state.get("normalized_message", ""),
            "operator_brief": state.get("operator_brief", ""),
            "retrieval": state.get("retrieval", []),
            "workflow_steps": state.get("workflow_steps", []),
            "stack": {
                "langchain": LANGCHAIN_AVAILABLE,
                "langgraph": LANGGRAPH_AVAILABLE,
                "llamaindex": LLAMAINDEX_AVAILABLE,
            },
            "resilience": resilience_meta,
        }

    @app.get("/api/orchestration/status")
    async def orchestration_status(request: Request):
        require_user(request)
        return status_payload()

    @app.post("/api/orchestration/assist")
    async def orchestration_assist(req: OrchestrationAssistRequest, request: Request):
        user = require_user(request)
        return await generate_orchestrated_reply(user, req)

    @app.post("/api/orchestration/index/query")
    async def orchestration_index_query(req: OrchestrationIndexQueryRequest, request: Request):
        user = require_user(request)
        target_brain = (req.target_brain or "").strip()
        if target_brain and not can_control_brain(user, target_brain):
            target_brain = "interpreter_brain"
        results = ranked_retrieval(req.query, target_brain=target_brain, limit=req.limit)
        return {
            "query": sanitize_operator_line(req.query),
            "target_brain": target_brain,
            "results": results,
            "index": {
                "documents": ensure_index().get("documents", 0),
                "built_at": ensure_index().get("built_at", ""),
            },
        }

    @app.post("/api/orchestration/index/rebuild")
    async def orchestration_index_rebuild(request: Request):
        user = require_user(request)
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master access required")
        state = ensure_index(force=True)
        return {
            "message": "Orchestration index rebuilt.",
            "documents": state.get("documents", 0),
            "brains": state.get("brains", 0),
            "built_at": state.get("built_at", ""),
        }

    ensure_index(force=True)
    compile_graph()
    log.info(
        "Orchestration stack layer loaded: LangChain=%s LangGraph=%s LlamaIndex=%s",
        LANGCHAIN_AVAILABLE,
        LANGGRAPH_AVAILABLE,
        LLAMAINDEX_AVAILABLE,
    )
    return {
        "status": "loaded",
        "status_payload": status_payload,
    }
