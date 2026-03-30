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

## Architecture

See [techbuzz-full/techbuzz-full/README.md](techbuzz-full/techbuzz-full/README.md) for the full architecture documentation, API reference, database schema, and deployment guide.

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
