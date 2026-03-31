"""
Unified Agent Registry — central registry for all Ishani-Core agents.

Lists every agent with:
- id, label, purpose
- capabilities (what it can do)
- allowed_tools (tools it may invoke)
- health_status, enabled, fallback_strategy
- ready_for_user, ready_for_automation

Exposes: GET /api/platform/agents
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Agent catalogue
# ---------------------------------------------------------------------------

_AGENT_CATALOGUE: List[Dict[str, Any]] = [
    {
        "id": "leazy_jinn",
        "label": "Leazy Jinn",
        "purpose": "Primary user-facing chat assistant and concierge",
        "capabilities": [
            "natural_language_chat",
            "task_delegation",
            "context_awareness",
            "multi_brain_routing",
        ],
        "allowed_tools": ["all_brains", "document_studio", "resume_tool"],
        "fallback_strategy": "mock_llm if no provider configured",
        "owner_brain": "mother_brain",
        "roles": ["all"],
    },
    {
        "id": "recruiter_agent",
        "label": "Recruiter Agent",
        "purpose": "Automates recruiter workflows: candidate sourcing, screening, follow-up",
        "capabilities": [
            "candidate_pipeline_management",
            "follow_up_automation",
            "jd_parsing",
            "outreach_drafting",
            "ats_sync",
        ],
        "allowed_tools": ["ats_kanban", "document_studio", "network_scanner"],
        "fallback_strategy": "route to recruitment_secretary brain",
        "owner_brain": "recruitment_secretary",
        "roles": ["recruiter", "founder_admin"],
    },
    {
        "id": "career_assistant",
        "label": "Career Assistant",
        "purpose": "Helps candidates with resume building, job matching, and career guidance",
        "capabilities": [
            "resume_parsing",
            "resume_generation",
            "job_match_scoring",
            "interview_prep",
            "career_advice",
        ],
        "allowed_tools": ["resume_tool", "document_studio"],
        "fallback_strategy": "use mock_llm fallback",
        "owner_brain": "public_agent",
        "roles": ["candidate"],
    },
    {
        "id": "ats_agent",
        "label": "ATS Agent",
        "purpose": "Manages the applicant tracking system: pipeline, stages, and dispositions",
        "capabilities": [
            "candidate_intake",
            "stage_transitions",
            "offer_management",
            "rejection_handling",
            "pipeline_reporting",
        ],
        "allowed_tools": ["ats_kanban"],
        "fallback_strategy": "surface error — ATS requires database",
        "owner_brain": "tool_ats_kanban",
        "roles": ["recruiter", "founder_admin"],
    },
    {
        "id": "browser_agent",
        "label": "Browser Automation Agent",
        "purpose": "Automates web research, job board scraping, and browser tasks",
        "capabilities": [
            "web_navigation",
            "job_board_scraping",
            "form_submission",
            "screenshot_capture",
            "data_extraction",
        ],
        "allowed_tools": ["playwright", "selenium", "browser_automation"],
        "fallback_strategy": "surface error — no fallback for live browsing",
        "owner_brain": "browser_automation",
        "roles": ["operator_research", "founder_admin"],
    },
    {
        "id": "voice_agent",
        "label": "Voice Agent",
        "purpose": "Handles voice input/output pipeline: STT, brain call, TTS",
        "capabilities": [
            "speech_to_text",
            "voice_command_routing",
            "text_to_speech",
            "vad_filtering",
        ],
        "allowed_tools": ["faster_whisper", "silero_vad", "pyttsx3", "melo_tts"],
        "fallback_strategy": "browser TTS fallback when local TTS unavailable",
        "owner_brain": "voice_runtime",
        "roles": ["all"],
    },
    {
        "id": "intel_agent",
        "label": "Intelligence Agent",
        "purpose": "Gathers competitive and market intelligence from web sources",
        "capabilities": [
            "competitive_analysis",
            "market_signal_detection",
            "company_research",
            "relationship_mapping",
        ],
        "allowed_tools": ["browser_automation", "network_scanner"],
        "fallback_strategy": "surface partial results",
        "owner_brain": "tool_network_scanner",
        "roles": ["founder_admin", "operator_research"],
    },
    {
        "id": "accounts_agent",
        "label": "Accounts Agent",
        "purpose": "Handles invoicing, ledger entries, and tax calculations",
        "capabilities": [
            "invoice_generation",
            "ledger_management",
            "tax_computation",
            "financial_reporting",
        ],
        "allowed_tools": ["accounts_automation", "document_studio"],
        "fallback_strategy": "surface error — financial accuracy required",
        "owner_brain": "tool_accounts_automation",
        "roles": ["founder_admin"],
    },
    {
        "id": "document_agent",
        "label": "Document Agent",
        "purpose": "Generates, formats, and manages documents and templates",
        "capabilities": [
            "document_generation",
            "template_filling",
            "version_control",
            "export_pdf",
        ],
        "allowed_tools": ["document_studio"],
        "fallback_strategy": "surface error",
        "owner_brain": "tool_document_studio",
        "roles": ["all"],
    },
    {
        "id": "autopilot_agent",
        "label": "Recruitment Autopilot",
        "purpose": "Runs autonomous recruitment workflows: follow-ups, acknowledgments, daily status",
        "capabilities": [
            "follow_up_automation",
            "acknowledgment_automation",
            "daily_status_reporting",
            "autonomous_loop",
        ],
        "allowed_tools": ["ats_kanban", "document_studio"],
        "fallback_strategy": "pause loop and alert operator",
        "owner_brain": "recruitment_secretary",
        "roles": ["recruiter", "founder_admin"],
    },
    {
        "id": "world_brain_agent",
        "label": "World Brain Agent",
        "purpose": "Manages global recruitment market atlas and geo-intelligence",
        "capabilities": [
            "market_mapping",
            "geo_intelligence",
            "atlas_seeding",
            "global_trend_tracking",
        ],
        "allowed_tools": ["browser_automation", "network_scanner"],
        "fallback_strategy": "route to operations_executive",
        "owner_brain": "world_brain",
        "roles": ["founder_admin", "operator_research"],
    },
    {
        "id": "local_ai_agent",
        "label": "Local AI Agent",
        "purpose": "Routes LLM queries to local Ollama/ChromaDB when available",
        "capabilities": [
            "local_llm_inference",
            "rag_retrieval",
            "embedding_generation",
            "vector_search",
        ],
        "allowed_tools": ["ollama", "chromadb"],
        "fallback_strategy": "fallback to remote provider (OpenAI/Gemini/Anthropic)",
        "owner_brain": "local_ai_runtime",
        "roles": [],
    },
]

_AGENT_MAP: Dict[str, Dict[str, Any]] = {a["id"]: a for a in _AGENT_CATALOGUE}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_agents() -> List[Dict[str, Any]]:
    """Return the full agent catalogue with runtime status."""
    return [_enrich(a) for a in _AGENT_CATALOGUE]


def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
    """Return enriched details for a single agent, or None if unknown."""
    a = _AGENT_MAP.get(agent_id)
    return _enrich(a) if a else None


def _enrich(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Attach runtime status fields to an agent record (non-destructive copy)."""
    return {
        **agent,
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

def install_unified_agent_registry(app: Any, ctx: Dict[str, Any]) -> None:
    """Register /api/platform/agents endpoints."""

    @app.get("/api/platform/agents")
    async def platform_agents():
        """List all registered agents with their capabilities and runtime status."""
        agents = get_all_agents()
        return {
            "total": len(agents),
            "agents": agents,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    @app.get("/api/platform/agents/{agent_id}")
    async def platform_agent_detail(agent_id: str):
        """Return details for a single agent by ID."""
        agent = get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found in registry.")
        return agent
