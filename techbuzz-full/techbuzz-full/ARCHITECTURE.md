# TechBuzz Full — Architecture Overview

## Project Layout

```
techbuzz-full/techbuzz-full/
├── backend_python/                        # Primary Python/FastAPI backend (all active API logic)
│   ├── app.py                             # 10,244 lines — main FastAPI app, core routes, state, auth, AI
│   ├── empire_merge_layer.py              #  1,289 lines — ATS, Network, HQ, Carbon, Intel, Media routes
│   ├── recruitment_brain_layer.py         #  6,780 lines — recruitment AI, seed packs, candidate matching
│   ├── browser_suite_layer.py             #  2,874 lines — Playwright-based browser automation
│   ├── orchestration_stack_layer.py       #    700 lines — task orchestration
│   ├── interpreter_brain_layer.py         #    715 lines — code interpretation / sandboxed execution
│   ├── local_ai_runtime_layer.py          #    811 lines — Ollama / local model runtime
│   ├── global_recruitment_brain_layer.py  #    513 lines — cross-workspace recruitment coordination
│   ├── recruitment_scenario_audit.py      #    619 lines — audit helpers for recruitment scenarios
│   ├── voice_runtime_layer.py             #    368 lines — voice command handling
│   ├── requirements.txt
│   └── data/                              # Runtime data (state, DB, uploads)
│       ├── empire_state.json        # Flat-JSON global state (single writer via file lock)
│       ├── ishani_core.db           # SQLite — users, sessions, orders, docs, accounts, etc.
│       ├── documents/               # User-uploaded files
│       ├── document_exports/        # Processed output files
│       ├── nirmaan/                 # Proposal JSON files
│       ├── recruitment_vaults/      # Per-workspace recruitment data
│       ├── voice_runtime/           # Voice session data
│       └── voice_commands/          # Stored voice commands
├── backend_go/              # Secondary Go backend (supplemental, not primary path)
├── frontend/                # 25 HTML pages + 11 JS files + 8 CSS files (see FRONTEND_INVENTORY.md)
├── deploy/                  # Deployment configs
├── START.sh / START.bat     # Launch scripts (starts uvicorn on port 8000)
└── README.md
```

## Runtime Architecture

```
Browser  ──HTTP/SSE──►  FastAPI (app.py, port 8000)
                               │
               ┌───────────────┼──────────────────────────────┐
               │               │                              │
        empire_merge_layer  recruitment_brain_layer    browser_suite_layer
        (ATS/Network/HQ)    (AI hiring flows)          (Playwright automation)
               │
        orchestration_stack_layer / interpreter_brain_layer
        local_ai_runtime_layer / voice_runtime_layer
               │
         ┌─────┴──────┐
   empire_state.json   ishani_core.db (SQLite)
   (global state)      (users, sessions, accounts, docs)
```

## Backend — app.py Responsibilities

`app.py` is the monolithic entry point. It contains:

| Concern | Location |
|---------|----------|
| FastAPI app creation + lifespan | Lines 1–93 |
| Global state file (empire_state.json) load/save/mutate | Lines 1099–1183 |
| SQLite helpers (`db_connect`, `db_exec`, `db_one`, `db_all`) | Lines 1184–1217 |
| DB schema initialisation (`init_core_db`) | Lines 1526–1699 |
| Authentication (hash, session, cookie, master auth) | Lines 1465–1970 |
| AI provider dispatch (`generate_text`, `call_*`) | Lines 1995–3165 |
| Brain hierarchy & payload builders | Lines 3166–3929 |
| Document handling (upload, extract, merge/split PDF) | Lines 3929–4047 |
| Accounts / finance (ledger, GST, TDS, tax calendar) | Lines 4048–4200+ |
| All HTTP route handlers | Lines 7738–10244 |

## Backend — Layer Registration Order

Layers are registered at the bottom of `app.py` (lines 10051–10244) in this order:

1. `install_empire_merge_layer` — ATS, Network, HQ, Carbon, Intel, Media
2. `install_global_recruitment_brain_layer` — global hunt coordination
3. `install_recruitment_brain_layer` — per-workspace recruitment AI
4. `install_browser_suite_layer` — browser automation
5. `install_interpreter_brain_layer` — code interpreter
6. `install_orchestration_stack_layer` — task orchestration
7. `install_local_ai_runtime_layer` — Ollama / local LLM management
8. `install_voice_runtime_layer` — voice wake/command

## AI Provider Support

| Provider | Helper function | Key |
|----------|----------------|-----|
| Anthropic Claude | `call_anthropic()` | env/state `anthropic_key` |
| OpenAI | `call_openai()` | env/state `openai_key` |
| Google Gemini | `call_gemini()` | env/state `gemini_key` |
| Ollama (local) | `call_ollama()` / `call_local_llm()` | `OLLAMA_BASE_URL` |

Provider preference order is resolved by `provider_order()` based on state.

## Data Storage Summary

| Store | Type | Purpose |
|-------|------|---------|
| `data/empire_state.json` | JSON file (file-locked) | Global app state, brain configs, provider settings |
| `data/ishani_core.db` | SQLite | Users, sessions, billing orders, documents, accounts, carbon events, media |
| `data/documents/` | Files | Raw uploaded documents |
| `data/document_exports/` | Files | Processed/exported documents |
| `data/nirmaan/` | JSON files | Proposal data |
| `data/recruitment_vaults/` | JSON/files | Per-workspace recruitment data |
| `data/voice_runtime/` | Files | Voice session state |

## Authentication Model

Three access levels are enforced:

| Level | How enforced | Where |
|-------|-------------|-------|
| **Public** | No auth required | Open routes (see ROUTE_MAP.md) |
| **Member** | `session_user()` / `require_member()` — session cookie | Most API routes |
| **Master** | `verify_master_password()` / `require_master()` — shared master password | Admin/empire routes |

Session tokens are stored as SHA-256 hashed cookies (`techbuzz_session`).  
Master identity is checked via `verify_master_password()` (app.py line 1484).
