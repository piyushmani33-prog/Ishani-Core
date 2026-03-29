# TechBuzz / Ishani Core

> **AI-powered recruitment platform** — post jobs, screen candidates with AI, track pipelines, and share instant status updates.

Contact: **+91-8588866632** | **piyushmani33@gmail.com**

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Getting Started](#getting-started)
5. [Environment Variables](#environment-variables)
6. [Pages & Routes](#pages--routes)
7. [API Reference](#api-reference)
8. [Recruiter Product Mode](#recruiter-product-mode)
9. [Database Schema Highlights](#database-schema-highlights)
10. [Deployment](#deployment)
11. [Contributing](#contributing)

---

## Overview

TechBuzz is a full-stack AI recruitment platform built with **FastAPI** (Python) on the backend and **vanilla HTML/CSS/JS** on the frontend. It bundles:

- A living AI agent workspace (**Leazy Jinn**)
- Recruitment tracker & ATS
- Browser/navigator automation
- Company portal & billing
- Voice I/O runtime
- Code interpreter
- Global recruitment brain

Everything runs from a single Python process. No separate worker or message broker is required.

---

## Features

| Feature | Description |
|---------|-------------|
| **Leazy Jinn Agent** | Conversational AI workspace with Praapti hunt, Akshaya memory, and Swarm missions |
| **Recruitment Tracker** | Full pipeline tracking: sourced → screening → interview → offer → hired → closed |
| **⚡ Recruiter Mode** | Mobile-first fast-update page — update tracker, generate status, share in under 10 seconds |
| **ATS** | Applicant tracking system with AI screening |
| **Navigator** | Browser automation & web research |
| **Company Portal** | HQ dashboard, billing, and team management |
| **Voice Runtime** | Wake-word voice command support |
| **Code Interpreter** | In-browser code execution |
| **Resume Builder** | AI-assisted resume creation |
| **Public Job Board** | Jobs listing and career AI |

---

## Architecture

```
techbuzz-full/techbuzz-full/
├── backend_python/
│   ├── app.py                        # Main FastAPI entry point (DO NOT rewrite)
│   ├── recruitment_brain_layer.py    # Tracker, vault, AI chat, DSR/HSR
│   ├── empire_merge_layer.py         # ATS, carbon protocol, company portals
│   ├── browser_suite_layer.py        # Browser, career, SaaS, job board
│   ├── orchestration_stack_layer.py  # Brain hierarchy
│   ├── interpreter_brain_layer.py    # Code interpreter
│   ├── global_recruitment_brain_layer.py
│   ├── local_ai_runtime_layer.py     # Local AI / Ollama runtime
│   ├── voice_runtime_layer.py        # Voice I/O
│   ├── recruiter_status_layer.py     # ⚡ Recruiter Mode endpoints (new)
│   ├── routes/
│   │   └── resume_router.py          # Resume builder API
│   ├── data/                         # SQLite DB + state files
│   ├── requirements.txt
│   └── .env / .env.example
├── frontend/
│   ├── agent.html / agent.js / agent.css   # Main agent console
│   ├── recruiter-mode.html/css/js           # ⚡ Recruiter Mode page (new)
│   ├── login.html / login.js / login.css    # Auth page
│   ├── index.html                           # Landing page
│   ├── core.css                             # Shared styles
│   ├── leazy.html / leazy.js / leazy.css    # Leazy Jinn interface
│   ├── ats.html                             # ATS page
│   ├── browser.html                         # Browser automation
│   ├── ide.html                             # Code interpreter
│   ├── research.html                        # Research intelligence
│   ├── hq.html / hq-owner.html             # Company HQ
│   └── …
├── START.bat                         # Windows startup
├── START.sh                          # Linux/macOS startup
└── deploy/                           # Docker, Railway, Render configs
```

### Layer Registration Pattern

Each feature layer exports an `install_*` function called at the bottom of `app.py`:

```python
RECRUITMENT_LAYER = install_recruitment_brain_layer(app, { ...helpers... })
# Lightweight layers use register_* pattern:
register_recruiter_status_routes(app, db_all=db_all, ...)
```

---

## Getting Started

### Prerequisites

- Python 3.10+ (tested with 3.12/3.14)
- pip

### Install & Run

**Windows:**
```bat
START.bat
```

**Linux / macOS:**
```sh
chmod +x START.sh
./START.sh
```

**Manual:**
```sh
cd techbuzz-full/techbuzz-full/backend_python
pip install -r requirements.txt
python app.py
```

The server starts at **http://localhost:8000**.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional | Claude AI provider |
| `OPENAI_API_KEY` | Optional | OpenAI GPT provider |
| `GEMINI_API_KEY` | Optional | Google Gemini provider |
| `OLLAMA_HOST` | Optional | Local Ollama endpoint (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | Optional | Ollama model name (default `llama3`) |
| `SESSION_SECRET` | Recommended | Secret key for session cookies |
| `ADMIN_EMAIL` | Optional | Master admin email |
| `ADMIN_PASSWORD` | Optional | Master admin password |

> If no AI key is configured the built-in fallback brain is used automatically.

---

## Pages & Routes

| URL | Auth | Description |
|-----|------|-------------|
| `/` | Public | Landing page |
| `/login` | Public | Authentication |
| `/leazy` | Public | Leazy Jinn AI interface |
| `/agent/console` | Member | Full recruiter agent console |
| `/recruiter-mode` | Member | ⚡ Mobile-first Recruiter Mode |
| `/ats` | Member | Applicant Tracking System |
| `/navigator` | Member | Browser automation |
| `/browser` | Member | Web browser |
| `/ide` | Public | Code interpreter |
| `/research` | Public | Research intelligence |
| `/company/portal` | Public | Company HQ dashboard |
| `/hq` | Owner | HQ owner dashboard |
| `/jobs` | Public | Job board |
| `/career` | Public | Career AI assistant |
| `/media` | Member | Media library |
| `/network/intel` | Public | Network intelligence |

---

## API Reference

### Authentication

Session-based auth via cookies. All `/api/recruiter-status/*` and `/api/agent/console/*` endpoints require a valid session.

### Recruitment Tracker

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recruitment-tracker/export?scope=tracker` | Export tracker as TSV |
| POST | `/api/recruitment-tracker/update` | Update a tracker row |
| POST | `/api/recruitment-tracker/capture` | Capture from conversation |
| POST | `/api/recruitment-tracker/submit-resume` | Submit resume |

### ⚡ Recruiter Status (new)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recruiter-status/quick-stats` | Dashboard counts |
| POST | `/api/recruiter-status/generate` | Generate status output |
| POST | `/api/recruiter-status/format-for-share` | Reformat for Teams/WhatsApp |
| POST | `/api/recruiter-status/tracker-add` | Quick add/update a row |

#### GET `/api/recruiter-status/quick-stats`

```json
{
  "total_rows": 12,
  "today_updated": 5,
  "interviews_scheduled": 2,
  "offers": 1,
  "closures": 0
}
```

#### POST `/api/recruiter-status/generate`

Request body:
```json
{
  "mode": "sheet",
  "format": "plain_text",
  "date_from": "",
  "date_to": ""
}
```

- `mode`: `"sheet"` (SQL aggregation, no AI) | `"summary"` (AI-generated)
- `format`: `"plain_text"` | `"tsv"` | `"csv"`

Response:
```json
{
  "output": "📊 Recruiter Status — 29 Mar 2026\n\nRole: Sr Developer\n  Sourced: 5 | ...",
  "format": "plain_text",
  "mode": "sheet",
  "row_count": 8,
  "generated_at": "2026-03-29T17:55:30Z"
}
```

#### POST `/api/recruiter-status/format-for-share`

Request body:
```json
{ "output": "...", "target": "teams" }
```

- `target`: `"teams"` | `"whatsapp"` | `"email"` | `"plain"`

#### POST `/api/recruiter-status/tracker-add`

Request body:
```json
{
  "candidate_name": "Rahul Sharma",
  "position": "Sr Developer",
  "process_stage": "interview",
  "response_status": "interested",
  "remarks": "L2 scheduled for Friday",
  "row_id": ""
}
```

Set `row_id` to update an existing row (ownership-verified).

---

## Recruiter Product Mode

The **Recruiter Mode** page (`/recruiter-mode`) is a simplified, mobile-first workspace designed for speed.

### Goal

Allow a recruiter to:
1. Open the page → update tracker → generate status → copy/share — **in under 10 seconds on mobile**.

### Features

- **Quick stats bar** — total candidates, today's updates, interviews, offers, closures
- **Quick Add / Update form** — always-visible collapsible form with large touch targets (≥ 48 px)
- **Tracker list** — all rows with stage/status badges and Edit / Status cycle buttons
- **Status generation** — two modes:
  - 📊 **Sheet** (instant, no AI) — aggregates by Role with columns: Sourced, Shortlisted, Interviews, Offers, Closures, Notes
  - 🤖 **Summary** (AI-based) — manager-ready paragraph summary
- **Format options** — Plain Text / TSV (Excel paste) / CSV
- **Copy & Share buttons**:
  - 📋 **Copy** — raw output to clipboard
  - 📱 **Copy for Teams** — Markdown table format
  - 💬 **Copy for WhatsApp** — emoji-rich format
  - 📤 **Share** — native `navigator.share()` API (mobile) with clipboard fallback

### Output Formats

**Plain Text (chat):**
```
📊 Recruiter Status — 29 Mar 2026

Role: Sr Developer
  Sourced: 5 | Shortlisted: 3 | Interviews: 2 | Offers: 1 | Closures: 0 | Notes: L2 scheduled
```

**TSV (Excel paste):**
```
Role	Profiles Sourced	Shortlisted	Interviews Scheduled	Offers	Closures	Notes
Sr Developer	5	3	2	1	0	L2 scheduled
```

**Teams Markdown:**
```
**📊 Recruiter Status Update**

| Role | Sourced | Shortlisted | Interviews | Offers | Closures |
|------|---------|-------------|------------|--------|----------|
| Sr Developer | 5 | 3 | 2 | 1 | 0 |
```

**WhatsApp:**
```
📊 *Recruiter Status Update*

🔹 *Sr Developer*
✅ Sourced: 5 | Shortlisted: 3
📞 Interviews: 2 | 🎯 Offers: 1
📝 Notes: L2 scheduled
```

---

## Database Schema Highlights

All data is stored in `backend_python/data/ishani_core.db` (SQLite).

### `recruitment_tracker_rows`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | Unique row ID |
| `user_id` | TEXT | Owner user (all queries scoped) |
| `candidate_name` | TEXT | |
| `position` | TEXT | Role / job title |
| `process_stage` | TEXT | `sourced` \| `screening` \| `interview` \| `offer` \| `hired` \| `closed` |
| `response_status` | TEXT | `pending_review` \| `interested` \| `no_response` \| `not_interested` \| `screen_rejected` |
| `submission_state` | TEXT | `draft` \| `ack_prepared` \| `submitted` \| `confirmed` |
| `remarks` | TEXT | Free-text notes |
| `created_at` | TEXT | ISO 8601 |
| `updated_at` | TEXT | ISO 8601 |

### `users`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | |
| `email` | TEXT | Login email |
| `role` | TEXT | `member` \| `master` |
| `session_token` | TEXT | Current session |

---

## Deployment

### Docker

```sh
docker build -f deploy/Dockerfile -t techbuzz .
docker run -p 8000:8000 --env-file .env techbuzz
```

### Railway / Render

Configuration files are in `deploy/`:
- `railway.json` — Railway deployment
- `render.yaml` — Render deployment
- `Procfile` — Heroku-style
- `nixpacks.toml` — Nixpacks build

### Environment

Set all required environment variables on your hosting platform. The SQLite database is file-based — mount a persistent volume at `backend_python/data/` for production.

---

## Contributing

1. Do **not** modify existing layer files (`recruitment_brain_layer.py`, `empire_merge_layer.py`, etc.)
2. Add new features as new layer files or new routes appended to `app.py`
3. Do **not** change auth/session logic or `START.bat` / `START.sh`
4. All SQL must use **parameterised queries** and be **scoped to `user_id`**
5. No new pip dependencies without updating `requirements.txt`
6. Frontend is vanilla HTML/CSS/JS — no framework required

---

*TechBuzz AI — Hire Smarter. Grow Faster.*
