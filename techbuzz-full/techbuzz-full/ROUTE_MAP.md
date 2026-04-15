# TechBuzz Full — Route Map

Routes are defined in two files:

- **`backend_python/app.py`** — core routes (lines 7738–10244)
- **`backend_python/empire_merge_layer.py`** — empire routes inside `install_empire_merge_layer()` (function at line 163; route handlers at lines 510–1289)

Auth guards used:
- `session_user()` / `require_member()` — valid session cookie required
- `require_master()` — master password required (stricter)
- `verify_admin()` — X-Admin-Token header required

---

## Public Routes (no authentication required)

| Method | Path | Handler / Function | File | Notes |
|--------|------|--------------------|------|-------|
| GET | `/login` | serve `login.html` | app.py:7738 | Login page |
| GET | `/` | redirect to `/leazy` | app.py:7743 | Root redirect |
| GET | `/api` | redirect to `/docs` | app.py:7748 | API docs |
| GET | `/favicon.ico` | serve favicon | app.py:8472 | |
| GET | `/manifest.json` | PWA manifest JSON | app.py:8665 | |
| GET | `/service-worker.js` | serve `service-worker.js` | app.py:8683 | |
| POST | `/api/auth/register` | user registration | app.py:7790 | Creates user + session |
| POST | `/api/auth/login` | password login | app.py:7843 | Sets session cookie |
| POST | `/api/public/hq-chat` | HQ chatbot (unauthenticated) | app.py:8803 | Rate-limited by IP |
| POST | `/api/public/agent-chat` | Agent chatbot (unauthenticated) | app.py:8853 | Rate-limited by IP |
| POST | `/api/public/provider-models` | list available AI models | app.py:8840 | |
| GET | `/api/health` | basic health check | app.py:8695 | |
| GET | `/career` | serve `career.html` | app.py:8515 | Public career page |
| GET | `/jobs` | serve `jobs.html` | app.py:8520 | Public jobs listing |
| GET | `/jobs/{job_id}` | serve `jobs.html` | app.py:8525 | |
| GET | `/api/member-network/public-state` | public network state | empire_merge_layer.py:881 | |

---

## Member Routes (valid session cookie required)

### Authentication

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| POST | `/api/auth/logout` | clear session | app.py:7881 |
| GET | `/api/auth/me` | current session info | app.py:7891 |
| POST | `/api/auth/master-login` | elevate to master | app.py:7859 |

### Billing

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/billing/plans` | list subscription plans | app.py:7897 |
| POST | `/api/billing/checkout` | create checkout / order | app.py:7908 |
| GET | `/api/billing/orders` | list user orders | app.py:7934 |

### Accounts / Finance

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/accounts/status` | account status | app.py:8006 |
| GET | `/api/accounts/ledger` | list ledger entries | app.py:8014 |
| POST | `/api/accounts/ledger` | add ledger entry | app.py:8027 |
| POST | `/api/accounts/invoice` | generate invoice | app.py:8078 |
| POST | `/api/accounts/gst-calc` | GST breakdown | app.py:8134 |
| POST | `/api/accounts/tds-calc` | TDS obligation | app.py:8156 |
| GET | `/api/accounts/tax-calendar` | upcoming tax dates | app.py:8174 |
| POST | `/api/accounts/profile` | update account profile | app.py:8183 |
| POST | `/api/accounts/entry` | add account entry | app.py:8252 |
| POST | `/api/accounts/analyze` | AI-powered account analysis | app.py:8297 |

### Documents

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/documents/list` | list user documents | app.py:8366 |
| POST | `/api/documents/upload` | upload file | app.py:8383 |
| POST | `/api/documents/create-note` | create text note | app.py:8398 |
| POST | `/api/documents/extract` | extract text from doc | app.py:8408 |
| POST | `/api/documents/update-text` | update document text | app.py:8420 |
| POST | `/api/documents/merge-pdf` | merge PDFs | app.py:8442 |
| POST | `/api/documents/split-pdf` | split PDF | app.py:8451 |
| GET | `/api/documents/download/{document_id}` | download document | app.py:8460 |

### Navigator

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/navigator/status` | navigator status | app.py:7946 |
| POST | `/api/navigator/capture` | capture URL session | app.py:7954 |
| POST | `/api/navigator/open-launcher` | open Naukri launcher | app.py:7977 |

### Brain / AI Management

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/brain/hierarchy` | brain hierarchy payload | app.py:9085 |
| GET | `/api/brain/status` | brain status | app.py:9289 |
| GET | `/api/brain/stream` | SSE brain updates | app.py:9038 |
| GET | `/api/brain/training-map` | training map | app.py:9180 |
| GET | `/api/brain/auto-repair/status` | auto-repair status | app.py:9090 |
| POST | `/api/brain/auto-repair/run` | trigger auto-repair | app.py:9106 |
| POST | `/api/brain/assign-task` | assign task to brain | app.py:9185 |
| POST | `/api/brain/motivate` | motivate brain | app.py:9220 |
| POST | `/api/brain/think/{brain_id}` | generate brain thought | app.py:9255 |
| POST | `/api/brain/pulse` | send pulse | app.py:9562 |
| GET | `/api/uiux/audit` | UI/UX audit status | app.py:9098 |
| GET | `/api/prana-nadi/pulse` | prana-nadi pulse | app.py:9075 |
| GET | `/api/nervous-system/status` | nervous system status | app.py:9080 |
| GET | `/api/mother/monitor` | mother brain monitor | app.py:9070 |

### Cabinet / Operations

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/cabinet/status` | cabinet status | app.py:9385 |
| POST | `/api/cabinet/prime-minister` | PM command | app.py:9390 |
| POST | `/api/cabinet/toggle` | toggle cabinet feature | app.py:9412 |
| GET | `/api/ops/domains` | operational domains | app.py:9279 |

### Packages / Portal

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/packages/templates` | list package templates | app.py:9437 |
| POST | `/api/packages/launch` | launch package | app.py:9442 |
| GET | `/api/portal/state` | portal state payload | app.py:9509 |
| GET | `/api/portal/stream` | SSE portal updates | app.py:9052 |
| GET | `/api/empire/dashboard` | empire dashboard data | app.py:9033 |

### Memory / Settings

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/memory/audit` | memory audit | app.py:9284 |
| GET | `/api/akshaya/vault` | memory vault | app.py:9836 |
| GET | `/api/settings/status` | settings status | app.py:9294 |
| POST | `/api/settings/update` | update settings | app.py:9299 |

### AI / Chat / Search

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| POST | `/api/chat` | main chat endpoint | app.py:8756 |
| POST | `/api/leazy/chat` | Leazy Jinn chat | app.py:8880 |
| POST | `/api/search` | search | app.py:9014 |
| POST | `/api/providers/configure` | configure AI provider | app.py:9336 |
| POST | `/api/providers/catalog` | list provider models | app.py:9370 |

### Recruitment / ATS / Network

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| POST | `/api/praapti/hunt` | start recruitment hunt | app.py:9609 |
| GET | `/api/praapti/hunts` | list hunts | app.py:9695 |
| POST | `/api/ats/import-latest` | import latest ATS data | app.py:9539 |
| POST | `/api/network/scan` | network scan | app.py:9514 |

### Missions / Proposals

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| POST | `/api/swarm/mission` | launch swarm mission | app.py:9702 |
| GET | `/api/nirmaan/proposals` | list proposals | app.py:9764 |
| POST | `/api/nirmaan/develop` | develop proposal | app.py:9772 |
| POST | `/api/nirmaan/approve` | approve proposal | app.py:9789 |

### Voice / Vishnu

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/voice/status` | voice status | app.py:9853 |
| POST | `/api/voice/settings` | update voice settings | app.py:9858 |
| POST | `/api/voice/wake` | voice wake trigger | app.py:9976 |
| GET | `/api/vishnu/status` | vishnu system status | app.py:9981 |
| POST | `/api/vishnu/channel` | vishnu channel | app.py:9994 |
| GET | `/api/voice/profile` | voice profile | empire_merge_layer.py:1166 |

### Member Network (empire_merge_layer.py)

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/member-network/state` | member network state | empire_merge_layer.py:885 |
| POST | `/api/member-network/connect` | create connection | empire_merge_layer.py:890 |
| DELETE | `/api/member-network/connections/{connection_id}` | remove connection | empire_merge_layer.py:903 |
| POST | `/api/member-network/post` | create post | empire_merge_layer.py:909 |
| POST | `/api/member-network/posts/{post_id}/like` | like a post | empire_merge_layer.py:934 |

### Media (empire_merge_layer.py)

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| POST | `/api/media/save` | save media item | empire_merge_layer.py:1266 |
| GET | `/api/media/library` | list media library | empire_merge_layer.py:1279 |
| PUT | `/api/media/play/{media_id}` | mark media as played | empire_merge_layer.py:1285 |

---

## Master Routes (master password required)

### Admin (app.py)

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| POST | `/api/admin/login` | admin authentication | app.py:8736 |
| POST | `/api/admin/edit` | edit system data | app.py:8975 |
| GET | `/api/stats` | system statistics | app.py:10035 |
| GET | `/api/health/full` | full health report | app.py:8712 |

### Carbon / Empire System (empire_merge_layer.py)

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/carbon/status` | carbon system status | empire_merge_layer.py:518 |
| POST | `/api/carbon/bond` | create carbon bond | empire_merge_layer.py:532 |
| POST | `/api/carbon/think` | carbon AI thinking | empire_merge_layer.py:562 |
| GET | `/api/carbon/stream` | SSE carbon stream | empire_merge_layer.py:582 |

### ATS (empire_merge_layer.py — master-only)

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/ats/state` | full ATS state | empire_merge_layer.py:612 |
| POST | `/api/ats/jobs` | create job | empire_merge_layer.py:626 |
| POST | `/api/ats/candidates` | create candidate | empire_merge_layer.py:652 |
| PUT | `/api/ats/candidates/{candidate_id}/move` | move candidate stage | empire_merge_layer.py:701 |
| DELETE | `/api/ats/candidates/{candidate_id}` | delete candidate | empire_merge_layer.py:708 |
| POST | `/api/ats/import-praapti` | import from Praapti | empire_merge_layer.py:714 |
| POST | `/api/ats/ai-score-all` | AI-score all candidates | empire_merge_layer.py:759 |

### Network / HQ (empire_merge_layer.py — master-only)

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| GET | `/api/network/state` | full network state | empire_merge_layer.py:940 |
| POST | `/api/network/connect` | add network connection | empire_merge_layer.py:948 |
| DELETE | `/api/network/connections/{connection_id}` | remove connection | empire_merge_layer.py:962 |
| POST | `/api/network/post` | create network post | empire_merge_layer.py:968 |
| POST | `/api/network/signal` | signal search | empire_merge_layer.py:993 |
| POST | `/api/network/posts/{post_id}/like` | like post | empire_merge_layer.py:1034 |
| GET | `/api/hq/state` | HQ full state | empire_merge_layer.py:1040 |
| POST | `/api/hq/clients` | create client | empire_merge_layer.py:1080 |
| PUT | `/api/hq/clients/{client_id}/stage` | move client stage | empire_merge_layer.py:1094 |
| DELETE | `/api/hq/clients/{client_id}` | delete client | empire_merge_layer.py:1101 |
| POST | `/api/hq/revenue` | add revenue entry | empire_merge_layer.py:1107 |
| POST | `/api/hq/team` | add team member | empire_merge_layer.py:1121 |
| DELETE | `/api/hq/team/{team_id}` | remove team member | empire_merge_layer.py:1134 |
| POST | `/api/hq/strategy` | set HQ strategy | empire_merge_layer.py:1140 |

### Intel (empire_merge_layer.py — master-only)

| Method | Path | Handler / Function | File |
|--------|------|--------------------|------|
| POST | `/api/intel/search` | web search | empire_merge_layer.py:1180 |
| POST | `/api/intel/news` | RSS news feed | empire_merge_layer.py:1191 |
| POST | `/api/intel/fetch-url` | scrape URL | empire_merge_layer.py:1204 |
| GET | `/api/intel/knowledge/{brain_id}` | brain knowledge | empire_merge_layer.py:1212 |
| GET | `/api/intel/all-knowledge` | all brain knowledge | empire_merge_layer.py:1218 |
| POST | `/api/intel/mass-learn` | mass knowledge ingestion | empire_merge_layer.py:1224 |
| GET | `/api/intel/sources` | knowledge sources | empire_merge_layer.py:1256 |

---

## Frontend Page Routes (HTML file serving)

All served from `frontend/` directory by app.py.

| Path | HTML File | Access | app.py line |
|------|-----------|--------|-------------|
| `/leazy` | `leazy.html` | member | 8480 |
| `/agent` | `agent.html` | member | 8495 |
| `/agent/console` | `agent.html` | member | 8500 |
| `/navigator` | `navigator.html` | member | 8505 |
| `/browser` | `browser.html` | member | 8510 |
| `/ide` | `ide.html` | member | 8530 |
| `/mission` | `mission.html` | member | 8535 |
| `/neural` | `neural.html` | member | 8540 |
| `/photon` | `photon.html` | member | 8545 |
| `/research` | `research.html` | member | 8550 |
| `/spread` | `spread.html` | member | 8555 |
| `/hq` | `hq.html` | member | 8620 |
| `/network` | `network.html` | member | 8630 |
| `/network/intel` | `network-intel.html` | member | 8635 |
| `/ats` | `ats.html` | member | 8645 |
| `/company/portal` | `company-portal.html` | member | 8485 |
| `/media` | `media.html` | master | empire_merge_layer.py:510 |
| `/career` | `career.html` | public | 8515 |
| `/jobs` | `jobs.html` | public | 8520 |

Alias redirects (not in schema, forward to canonical path):
`/company/portal.html`, `/company-portal`, `/company/workspace`, `/office`, `/index.html`,
`/company-register`, `/pricing`, `/about`, `/contact`, `/blog`, `/privacy`, `/terms`,
`/api-docs`, `/company/owner`, `/company/network.html`, `/company/ats.html`, `/company/hq.html`
