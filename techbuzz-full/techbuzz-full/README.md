# TechBuzz Full

TechBuzz Full is the live Ishani Core workspace for TechBuzz Systems Pvt Ltd. It combines the public company portal, the public AI agent, the protected Leazy mother-brain cockpit, ATS, Network, HQ owner portal, Media, Accounts, Carbon intelligence, and research/mutation tooling into one FastAPI application.

## Current Surfaces

- `GET /company/portal`
  Public TechBuzz HQ with branding, public AI concierge, plans, and gateway links.
- `GET /agent`
  Public AI agent page with bring-your-own-key flow and public voice/chat access.
- `GET /login`
  Unified access page for members and master access.
- `GET /agent/console`
  Member workspace with candidate pipeline, open roles, accounts, documents, hierarchy, and intelligence.
- `GET /leazy`
  Mother-brain cockpit for master access.
- `GET /hq`
  Owner command portal.
- `GET /network`
  Protected network operations surface.
- `GET /ats`
  Protected ATS surface.
- `GET /media`
  Protected media and creative relay surface.
- `GET /software-forge`
  Software Forge for toolchain, blueprint, scaffold, and build flows.
- `GET /preservation-lab`
  Preservation, mutation-review, and recovery lab.

## Project Layout

```text
techbuzz-full/
├── backend_python/
│   ├── app.py
│   ├── empire_merge_layer.py
│   ├── requirements.txt
│   ├── .env
│   └── data/
├── backend_go/
│   ├── main.go
│   └── go.mod
├── frontend/
│   ├── leazy.html
│   ├── agent.html
│   ├── public-agent.html
│   ├── empire-portals.html
│   ├── hq-owner.html
│   ├── network.html
│   ├── ats.html
│   ├── media.html
│   ├── login.html
│   ├── *.js / *.css
│   ├── art/
│   └── media/
└── START.bat
```

## Security Notes

- Configure the master login ID and hashed master password locally in `backend_python/.env`.
- Do not commit real provider keys or master credentials.
- The shipped config is neutralized for local setup and manual provider entry.
- Public/member/master access is split by the backend session layer, not just the frontend.

## Quick Start

### Windows

Run:

```bat
START.bat
```

The launcher checks `.venv`, `venv`, and system Python fallbacks.

### Manual Python Run

```bash
cd backend_python
pip install -r requirements.txt
python app.py
```

Then open:

- `http://localhost:8000/company/portal`
- `http://localhost:8000/agent`
- `http://localhost:8000/login`

## Provider Setup

No external AI key is bundled.

Use the in-app Settings flow:

1. Open Leazy or Public Agent settings.
2. Paste your provider key manually.
3. Fetch models.
4. Choose the model.
5. Save and apply.

If no external provider is configured, Ishani falls back to the built-in local brain.

## Master Access Setup

The master unlock flow uses:

- `MASTER_LOGIN_ID`
- `MASTER_PASSWORD_SALT`
- `MASTER_PASSWORD_HASH`

The browser asks for the master login ID and password, while the backend stores only the salted password hash.

## Important Backend Areas

- `app.py`
  Main FastAPI app, auth, session control, mother-brain routes, ATS/Network/HQ/Accounts/Voice/Media, and page serving.
- `empire_merge_layer.py`
  Carbon, ATS, Network, HQ, Intel, and Media merge routes that were brought into the live project from the richer March build.
- `data/`
  Local runtime state, database, documents, exports, proposals, and recovery files.

## Important Frontend Areas

- `leazy.*`
  Mother-brain cockpit.
- `agent.*`
  Member agent console.
- `public-agent.*`
  Public AI agent experience.
- `empire-portals.*`
  Public HQ shell and shared portal behavior.
- `hq-owner.html`
  Owner portal.
- `network.html`
  Network operations UI.
- `ats.html`
  ATS pipeline UI.
- `media.html`
  Media relay.

## Merge Notes

This project already includes the March 27 visual/portal merge into the current TechBuzz app. Duplicate legacy pieces were intentionally not wired if the current project already had a richer or safer implementation.

## Restart After Changes

After frontend or service worker updates:

1. Restart `START.bat`
2. Open the target page
3. Press `Ctrl+F5`
4. If an old shell still appears once, clear site data so the latest service worker cache can take over
