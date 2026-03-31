# Ishani-Core / TechBuzz AI

> **AI-powered recruitment platform** — post jobs, screen candidates with AI, track pipelines, and share instant status updates.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

TechBuzz / Ishani-Core is a full-stack AI recruitment platform built with **FastAPI** (Python) on the backend and **vanilla HTML/CSS/JS** on the frontend. It includes:

- 🤖 **Leazy Jinn** — Conversational AI agent workspace
- 📊 **Recruitment Tracker** — Full pipeline: sourced → screening → interview → offer → hired → closed
- ⚡ **Recruiter Mode** — Mobile-first fast-update page (update + generate status + share in <10 seconds)
- 📋 **ATS** — Applicant tracking with AI screening
- 🌐 **Navigator** — Browser automation & web research
- 💼 **Company Portal** — HQ dashboard, billing, team management
- 🎙️ **Voice Runtime** — Wake-word voice command support
- 💻 **Code Interpreter** — In-browser code execution
- 📄 **Resume Builder** — AI-assisted resume creation
- 🏢 **Public Job Board** — Jobs listing and career AI

## Quick Start

### Prerequisites
- Python 3.10+ (tested with 3.12)
- pip

### Run

```bash
# Clone the repository
git clone https://github.com/piyushmani33-prog/Ishani-Core.git
cd Ishani-Core

# Option 1: Use the launcher
python main.py

# Option 2: Manual start
cd techbuzz-full/techbuzz-full/backend_python
cp .env.example .env        # Edit .env and add your API keys
pip install -r requirements.txt
python app.py
```

The server starts at **http://localhost:8000**.

### Windows
```bat
cd techbuzz-full\techbuzz-full
START.bat
```

## Environment Variables

Copy `.env.example` to `.env` in `techbuzz-full/techbuzz-full/backend_python/`:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Optional | OpenAI GPT provider |
| `GEMINI_API_KEY` | Optional | Google Gemini provider |
| `ANTHROPIC_API_KEY` | Optional | Claude AI provider |
| `OLLAMA_HOST` | Optional | Local Ollama endpoint (default `http://localhost:11434`) |
| `SESSION_SECRET` | Recommended | Secret key for session cookies |

> If no AI key is configured, the built-in fallback brain is used automatically.

## Unified Platform Architecture

### Platform Status Endpoint
`GET /api/platform/status` — Single honest readiness check covering all subsystems.

Each subsystem reports: `enabled`, `configured`, `initialized`, `healthy`, `degraded`,
`fallback_active`, `last_error`, `ready_for_user`, `ready_for_automation`.

Subsystems covered: database · ai_providers · brain_hierarchy · agent_registry ·
voice_pipeline · local_ai · settings · recruiter_module · ats · middleware.

### Brain Hierarchy
`GET /api/platform/brains` · `GET /api/platform/brains/hierarchy`

7-tier brain hierarchy (mother → executive → secretary → domain → machine → tool → atom):

| Tier | Label | Key Brains |
|------|-------|-----------|
| 1 | Mother | `mother_brain` |
| 2 | Executive | `exec_praapti`, `cabinet_brain`, `akshaya_brain`, `interpreter_brain` |
| 3 | Secretary | `sec_nidhi`, `recruitment_secretary`, `operations_executive` |
| 4 | Domain | `tool_ats_kanban`, `tool_network_scanner`, `public_agent`, `world_brain` |
| 5 | Machine | `local_ai_runtime`, `orchestration_stack`, `browser_automation` |
| 6 | Tool | `voice_runtime`, `resume_tool` |

### Agent Registry
`GET /api/platform/agents`

12 registered agents: `leazy_jinn` · `recruiter_agent` · `career_assistant` ·
`ats_agent` · `browser_agent` · `voice_agent` · `intel_agent` · `accounts_agent` ·
`document_agent` · `autopilot_agent` · `world_brain_agent` · `local_ai_agent`.

### Settings Manager
`GET /api/settings` · `POST /api/settings` · `GET /api/settings/status`

- Loads from `.env` + `data/settings.json` (runtime overrides)
- Validates provider keys on save (format check, not network)
- Redacts secrets in GET responses
- Reports actual runtime state vs saved state

### Voice Readiness
`GET /api/voice/runtime/status` reports honest readiness:
- `ready_for_user`: true when STT is available OR browser TTS fallback covers output
- `ready_for_automation`: true only when both STT and local TTS are present
- `degraded`: true when any component is missing
- `browser_tts_fallback_active`: always available as last resort

## Requirements

| File | Purpose |
|------|---------|
| `requirements.txt` | Root dev/test deps (fastapi, pytest, etc.) |
| `requirements-dev.txt` | Additional developer tools (ruff, mypy) |
| `techbuzz-full/techbuzz-full/backend_python/requirements.txt` | Full production deps |
| `techbuzz-full/techbuzz-full/backend_python/requirements-lite.txt` | Lite deps (no heavy ML) |

## Key Pages

| URL | Description |
|-----|-------------|
| `/` | Landing page |
| `/login` | Authentication |
| `/agent/console` | Full recruiter agent console |
| `/recruiter-mode` | ⚡ Mobile-first Recruiter Mode |
| `/ats` | Applicant Tracking System |
| `/leazy` | Leazy Jinn AI interface |
| `/jobs` | Public job board |
| `/ide` | Code interpreter |
| `/api/platform/status` | 🔍 Unified platform health check |
| `/api/platform/brains` | 🧠 Brain registry |
| `/api/platform/agents` | 🤖 Agent registry |
| `/api/settings` | ⚙️ Settings (auth required) |

## Local Validation Checklist

```
[ ] python main.py — server starts on :8000
[ ] GET /health — returns {"status":"ok"}
[ ] GET /api/platform/status — all subsystems visible
[ ] GET /api/platform/brains — 20+ brains listed
[ ] GET /api/platform/agents — 12 agents listed
[ ] GET /api/voice/runtime/status — ready_for_user is present
[ ] POST /api/settings (master login) — settings saved
[ ] pytest tests/ — all tests pass
```

## Architecture

See [techbuzz-full/techbuzz-full/README.md](techbuzz-full/techbuzz-full/README.md) for the full architecture documentation, API reference, database schema, and deployment guide.

## Contributing

1. Do **not** modify existing layer files directly
2. Add new features as new layer files or routes appended to `app.py`
3. All SQL must use **parameterised queries** scoped to `user_id`
4. No new pip dependencies without updating `requirements.txt`
5. Frontend is vanilla HTML/CSS/JS — no framework required

## Security

⚠️ **Never commit `.env` files.** See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

*TechBuzz AI — Hire Smarter. Grow Faster.*
