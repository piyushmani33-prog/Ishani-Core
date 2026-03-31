"""
Unified Brain Registry — single source of truth for all brains.

Merges:
- brain_prompt_registry.BRAIN_REGISTRY (prompt/doctrine definitions)
- role_router_layer.ROLE_BRAIN_MAP (role → brain mappings)
- Hard-coded hierarchy tiers from app.py brain_hierarchy_payload

Exposes: GET /api/platform/brains
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

try:
    from fastapi import HTTPException
except ImportError:  # allow import without fastapi installed (e.g. unit tests)
    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int = 500, detail: str = ""):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

# ---------------------------------------------------------------------------
# Brain tier definitions (mirrors app.py brain_hierarchy_payload)
# ---------------------------------------------------------------------------

_HIERARCHY_TIERS: List[Dict[str, Any]] = [
    {
        "tier": 1,
        "label": "Mother",
        "brains": ["mother_brain"],
    },
    {
        "tier": 2,
        "label": "Executive",
        "brains": ["exec_praapti", "cabinet_brain", "akshaya_brain", "interpreter_brain"],
    },
    {
        "tier": 3,
        "label": "Secretary",
        "brains": ["sec_nidhi", "recruitment_secretary", "operations_executive"],
    },
    {
        "tier": 4,
        "label": "Domain",
        "brains": [
            "tool_ats_kanban",
            "tool_accounts_automation",
            "tool_network_scanner",
            "tool_document_studio",
            "carbon_protocol",
            "public_agent",
            "world_brain",
        ],
    },
    {
        "tier": 5,
        "label": "Machine",
        "brains": ["local_ai_runtime", "orchestration_stack", "browser_automation"],
    },
    {
        "tier": 6,
        "label": "Tool",
        "brains": ["voice_runtime", "ats_kanban_tool", "resume_tool"],
    },
]

# tier lookup: brain_id → tier number
_BRAIN_TIER: Dict[str, int] = {}
for _t in _HIERARCHY_TIERS:
    for _b in _t["brains"]:
        _BRAIN_TIER[_b] = _t["tier"]


# ---------------------------------------------------------------------------
# Canonical brain catalogue
# Every entry must have at minimum: id, purpose, tier, layer_label
# ---------------------------------------------------------------------------

_BRAIN_CATALOGUE: List[Dict[str, Any]] = [
    {
        "id": "mother_brain",
        "purpose": "Sovereign strategic command across all brain layers",
        "tier": 1,
        "layer_label": "Mother",
        "input_types": ["query", "directive", "event"],
        "output_types": ["strategic_analysis", "cross_brain_directive", "risk_report", "decision_brief"],
        "allowed_tools": ["all"],
        "fallback_strategy": "none — mother is the last resort",
        "roles": ["founder_admin"],
    },
    {
        "id": "exec_praapti",
        "purpose": "Executive acquisition: clients, deals, and growth pipeline",
        "tier": 2,
        "layer_label": "Executive",
        "input_types": ["query", "deal_data", "pipeline_update"],
        "output_types": ["action_plan", "decision_brief", "delegation_note", "pipeline_update"],
        "allowed_tools": ["document_studio", "network_scanner", "ats_kanban"],
        "fallback_strategy": "route to mother_brain",
        "roles": ["founder_admin"],
    },
    {
        "id": "cabinet_brain",
        "purpose": "Cross-functional cabinet coordination and governance",
        "tier": 2,
        "layer_label": "Executive",
        "input_types": ["query", "policy_request"],
        "output_types": ["policy_directive", "coordination_note"],
        "allowed_tools": ["document_studio"],
        "fallback_strategy": "route to mother_brain",
        "roles": ["founder_admin"],
    },
    {
        "id": "akshaya_brain",
        "purpose": "Operations and resource continuity executive",
        "tier": 2,
        "layer_label": "Executive",
        "input_types": ["query", "ops_request"],
        "output_types": ["ops_plan", "resource_report"],
        "allowed_tools": ["document_studio", "accounts_automation"],
        "fallback_strategy": "route to mother_brain",
        "roles": ["founder_admin", "operator_research"],
    },
    {
        "id": "interpreter_brain",
        "purpose": "Code interpretation and technical analysis",
        "tier": 2,
        "layer_label": "Executive",
        "input_types": ["code", "query", "technical_request"],
        "output_types": ["code_output", "analysis_report"],
        "allowed_tools": ["code_interpreter"],
        "fallback_strategy": "surface error to user",
        "roles": ["founder_admin"],
    },
    {
        "id": "sec_nidhi",
        "purpose": "Finance compliance, ledger oversight, and regulatory risk tracking",
        "tier": 3,
        "layer_label": "Secretary",
        "input_types": ["financial_data", "query", "audit_request"],
        "output_types": ["risk_assessment", "compliance_flag", "audit_item", "financial_summary"],
        "allowed_tools": ["accounts_automation", "document_studio"],
        "fallback_strategy": "route to exec_praapti",
        "roles": ["founder_admin"],
    },
    {
        "id": "recruitment_secretary",
        "purpose": "End-to-end recruitment operations and candidate pipeline management",
        "tier": 3,
        "layer_label": "Secretary",
        "input_types": ["candidate_data", "job_description", "query"],
        "output_types": ["candidate_action", "pipeline_update", "outreach_draft"],
        "allowed_tools": ["ats_kanban", "document_studio", "network_scanner"],
        "fallback_strategy": "route to mother_brain",
        "roles": ["recruiter"],
    },
    {
        "id": "operations_executive",
        "purpose": "Operational research, workflow oversight, and task management",
        "tier": 3,
        "layer_label": "Secretary",
        "input_types": ["task_request", "research_query", "workflow_data"],
        "output_types": ["ops_report", "task_list", "research_brief"],
        "allowed_tools": ["browser_automation", "document_studio"],
        "fallback_strategy": "route to akshaya_brain",
        "roles": ["operator_research"],
    },
    {
        "id": "public_agent",
        "purpose": "Public-facing career assistant for candidates",
        "tier": 4,
        "layer_label": "Domain",
        "input_types": ["query", "resume_data", "job_listing"],
        "output_types": ["career_advice", "resume_feedback", "job_match"],
        "allowed_tools": ["resume_tool"],
        "fallback_strategy": "use mock_llm fallback",
        "roles": ["candidate"],
    },
    {
        "id": "tool_ats_kanban",
        "purpose": "Recruitment ATS pipeline: sourcing, screening, and placement tracking",
        "tier": 4,
        "layer_label": "Domain",
        "input_types": ["candidate_data", "pipeline_command"],
        "output_types": ["candidate_action", "screening_checklist", "pipeline_update"],
        "allowed_tools": ["ats_kanban"],
        "fallback_strategy": "surface error",
        "roles": ["recruiter", "founder_admin"],
    },
    {
        "id": "tool_accounts_automation",
        "purpose": "Accounting automation: invoices, ledgers, tax, and financial records",
        "tier": 4,
        "layer_label": "Domain",
        "input_types": ["financial_data", "invoice_request"],
        "output_types": ["invoice_summary", "ledger_entry", "tax_computation"],
        "allowed_tools": ["accounts_automation"],
        "fallback_strategy": "surface error",
        "roles": ["founder_admin"],
    },
    {
        "id": "tool_network_scanner",
        "purpose": "Network intelligence: competitive signals, market mapping, and relationship graphs",
        "tier": 4,
        "layer_label": "Domain",
        "input_types": ["search_query", "company_data"],
        "output_types": ["intel_brief", "signal_report", "competitor_update"],
        "allowed_tools": ["browser_automation"],
        "fallback_strategy": "surface error",
        "roles": ["founder_admin", "operator_research"],
    },
    {
        "id": "tool_document_studio",
        "purpose": "Document generation: reports, templates, exports, and structured content",
        "tier": 4,
        "layer_label": "Domain",
        "input_types": ["document_request", "template_data"],
        "output_types": ["document_draft", "template_output", "structured_report"],
        "allowed_tools": ["document_studio"],
        "fallback_strategy": "surface error",
        "roles": ["founder_admin", "operator_research", "recruiter"],
    },
    {
        "id": "carbon_protocol",
        "purpose": "Carbon tracking and sustainability reporting",
        "tier": 4,
        "layer_label": "Domain",
        "input_types": ["emissions_data", "query"],
        "output_types": ["sustainability_report", "carbon_summary"],
        "allowed_tools": ["document_studio"],
        "fallback_strategy": "surface error",
        "roles": ["founder_admin"],
    },
    {
        "id": "world_brain",
        "purpose": "Global recruitment market intelligence and world atlas management",
        "tier": 4,
        "layer_label": "Domain",
        "input_types": ["market_query", "geo_data"],
        "output_types": ["market_brief", "geo_intel", "atlas_update"],
        "allowed_tools": ["browser_automation", "network_scanner"],
        "fallback_strategy": "route to operations_executive",
        "roles": ["founder_admin", "operator_research"],
    },
    {
        "id": "local_ai_runtime",
        "purpose": "Local LLM (Ollama/ChromaDB/RAG) orchestration",
        "tier": 5,
        "layer_label": "Machine",
        "input_types": ["query", "embedding_request"],
        "output_types": ["llm_response", "rag_result"],
        "allowed_tools": ["ollama", "chromadb"],
        "fallback_strategy": "fallback to remote provider",
        "roles": [],
    },
    {
        "id": "orchestration_stack",
        "purpose": "LangChain/LangGraph/LlamaIndex workflow orchestration",
        "tier": 5,
        "layer_label": "Machine",
        "input_types": ["workflow_request", "graph_task"],
        "output_types": ["workflow_result", "graph_output"],
        "allowed_tools": ["langchain", "langgraph", "llamaindex"],
        "fallback_strategy": "degrade to direct LLM call",
        "roles": [],
    },
    {
        "id": "browser_automation",
        "purpose": "Web browser automation, scraping, and job-board integration",
        "tier": 5,
        "layer_label": "Machine",
        "input_types": ["url", "scrape_request", "automation_script"],
        "output_types": ["page_data", "scrape_result", "automation_log"],
        "allowed_tools": ["playwright", "selenium"],
        "fallback_strategy": "surface error — no fallback for live automation",
        "roles": [],
    },
    {
        "id": "voice_runtime",
        "purpose": "Voice I/O: speech-to-text, TTS, and voice command routing",
        "tier": 6,
        "layer_label": "Tool",
        "input_types": ["audio_input", "text_for_tts"],
        "output_types": ["transcript", "audio_output"],
        "allowed_tools": ["faster_whisper", "silero_vad", "pyttsx3", "melo_tts"],
        "fallback_strategy": "browser TTS fallback",
        "roles": [],
    },
    {
        "id": "resume_tool",
        "purpose": "Resume building, parsing, and job-match scoring",
        "tier": 6,
        "layer_label": "Tool",
        "input_types": ["resume_text", "job_description"],
        "output_types": ["parsed_resume", "match_score", "resume_draft"],
        "allowed_tools": ["document_studio"],
        "fallback_strategy": "surface error",
        "roles": ["candidate", "recruiter"],
    },
]

# Build a fast lookup map
_BRAIN_MAP: Dict[str, Dict[str, Any]] = {b["id"]: b for b in _BRAIN_CATALOGUE}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_brains() -> List[Dict[str, Any]]:
    """Return the full brain catalogue with runtime health placeholders."""
    return [_enrich(b) for b in _BRAIN_CATALOGUE]


def get_brain(brain_id: str) -> Optional[Dict[str, Any]]:
    """Return enriched details for a single brain, or None if unknown."""
    b = _BRAIN_MAP.get(brain_id)
    return _enrich(b) if b else None


def get_brains_by_tier(tier: int) -> List[Dict[str, Any]]:
    """Return all brains at the given tier level."""
    return [_enrich(b) for b in _BRAIN_CATALOGUE if b["tier"] == tier]


def get_hierarchy() -> List[Dict[str, Any]]:
    """Return tiers with their brain summaries."""
    result = []
    for t in _HIERARCHY_TIERS:
        brains_in_tier = [
            {"id": bid, "purpose": _BRAIN_MAP.get(bid, {}).get("purpose", ""), "enabled": True}
            for bid in t["brains"]
        ]
        result.append(
            {
                "tier": t["tier"],
                "label": t["label"],
                "brain_count": len(brains_in_tier),
                "brains": brains_in_tier,
            }
        )
    return result


def _enrich(brain: Dict[str, Any]) -> Dict[str, Any]:
    """Add runtime status fields to a brain record (non-destructive copy)."""
    return {
        **brain,
        "enabled": True,
        "health_status": "ok",
        "fallback_active": False,
        "last_error": None,
        "ready_for_user": True,
        "ready_for_automation": True,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# FastAPI route installer
# ---------------------------------------------------------------------------

def install_unified_brain_registry(app: Any, ctx: Dict[str, Any]) -> None:
    """Register /api/platform/brains and /api/platform/brains/hierarchy."""

    @app.get("/api/platform/brains")
    async def platform_brains():
        """List all registered brains with their metadata and runtime status."""
        brains = get_all_brains()
        return {
            "total": len(brains),
            "brains": brains,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    @app.get("/api/platform/brains/hierarchy")
    async def platform_brain_hierarchy():
        """Return the brain hierarchy tiers with brain membership."""
        return {
            "tiers": get_hierarchy(),
            "total_brains": len(_BRAIN_CATALOGUE),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    @app.get("/api/platform/brains/{brain_id}")
    async def platform_brain_detail(brain_id: str):
        """Return details for a single brain by ID."""
        brain = get_brain(brain_id)
        if brain is None:
            raise HTTPException(status_code=404, detail=f"Brain '{brain_id}' not found in registry.")
        return brain
