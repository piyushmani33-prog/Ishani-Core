# TechBuzz Full — Frontend Inventory

All frontend files live in `techbuzz-full/techbuzz-full/frontend/`.

---

## HTML Pages (23 active + 1 stub)

| File | Lines | Route(s) | Access | Purpose |
|------|-------|----------|--------|---------|
| `browser.html` | 872 | `/browser` | member | Playwright-controlled browser interface |
| `spread.html` | 709 | `/spread` | member | Spreading / distribution interface |
| `leazy.html` | 701 | `/leazy` | member | Leazy Jinn AI assistant (primary chat UI) |
| `agent.html` | 633 | `/agent`, `/agent/console` | member | AI Agent console |
| `photon.html` | 589 | `/photon` | member | Analytics / photon data |
| `neural.html` | 577 | `/neural` | member | Neural interface |
| `media.html` | 548 | `/media` | master | Media management center |
| `index.html` | 463 | (`/index.html` alias) | public | Public landing page |
| `network.html` | 432 | `/network` | member | Network management |
| `research.html` | 423 | `/research` | member | Research tools |
| `hq.html` | 413 | `/hq` | member | Member HQ dashboard |
| `hq-owner.html` | 413 | `/company/owner` | master | Owner HQ dashboard |
| `company-portal.html` | 370 | `/company/portal` | member | Company portal |
| `jobs.html` | 359 | `/jobs`, `/jobs/{id}` | public | Job listings |
| `network-intel.html` | 345 | `/network/intel` | member | Network intelligence panel |
| `mission.html` | 340 | `/mission` | member | Swarm mission launch |
| `ats.html` | 295 | `/ats` | member | ATS (applicant tracking) |
| `ide.html` | 243 | `/ide` | member | IDE / code interpreter |
| `career.html` | 242 | `/career` | public | Career / jobs landing |
| `empire-portals.html` | 224 | (no direct route) | — | Empire portal hub (linked internally) |
| `navigator.html` | 191 | `/navigator` | member | Naukri navigator launcher |
| `public-agent.html` | 152 | (no direct route) | public | Public-facing agent widget |
| `login.html` | 103 | `/login` | public | Login / register page |
| `techbuzz-systems.html` | 18 | (no direct route) | — | Minimal system info stub |

---

## JavaScript Files

| File | Lines | Loaded by | Purpose |
|------|-------|-----------|---------|
| `agent.js` | 1,980 | `agent.html` | Agent console UI, API calls, streaming |
| `leazy.js` | 1,855 | `leazy.html` | Leazy Jinn chat UI, resume drafts, provider switching |
| `empire-pages.js` | 1,536 | Most member pages | Empire UI state manager — tabs, panels, API wiring |
| `public-agent.js` | 365 | `public-agent.html` | Public agent widget logic |
| `brain-hierarchy.js` | 350 | Several member pages | Brain hierarchy tree rendering |
| `accounts-command.js` | 347 | Accounts/HQ pages | Accounts ledger and command UI |
| `intel-panel.js` | 317 | `network-intel.html` | Intel search / news feed UI |
| `navigator.js` | 255 | `navigator.html` | Navigator session capture logic |
| `login.js` | 177 | `login.html` | Login / register form handling |
| `ui-auto-repair.js` | 172 | Injected globally | UI self-repair / health checks |
| `service-worker.js` | 124 | `manifest.json` (PWA) | PWA offline caching |

---

## CSS Files

| File | Lines | Loaded by | Purpose |
|------|-------|-----------|---------|
| `leazy.css` | 587 | `leazy.html` | Leazy Jinn interface styles |
| `empire-pages.css` | 551 | Most member pages | Empire panel / tab layout |
| `agent.css` | 271 | `agent.html` | Agent console styles |
| `core.css` | 198 | All pages | Base / reset styles (shared) |
| `brain-accounts.css` | 101 | Accounts pages | Accounts UI styles |
| `public-agent.css` | 64 | `public-agent.html` | Public agent widget styles |
| `login.css` | 52 | `login.html` | Login page styles |

---

## Other Assets

| Path | Purpose |
|------|---------|
| `manifest.json` | PWA app manifest |
| `leazy-icon.svg` | Leazy Jinn icon |
| `art/` | Additional artwork / background images |
| `media/` | Stored media (uploads / thumbnails) |
| `visuals/` | Visual asset directory |

---

## Duplicated Logic

### 1. `async function api()` — defined in 7 JS files

Every JS file re-implements its own HTTP helper instead of sharing a module.

| File | Function signature |
|------|--------------------|
| `agent.js` | `async function api(path, options = {})` |
| `leazy.js` | `async function api(path, options = {})` |
| `empire-pages.js` | `async function api(path, options = {})` |
| `accounts-command.js` | `async function api(path, opts = {})` |
| `navigator.js` | `async function api(path, options = {})` |
| `login.js` | `async function api(path, options = {})` |
| `public-agent.js` | `async function api(path, options = {})` |

**Risk:** Each copy may diverge (e.g., `accounts-command.js` uses `opts` instead of `options`).
Any change to error handling, auth headers, or base-URL must be applied seven times.

`leazy.js` additionally defines a separate `async function apiForm()` for `multipart/form-data`.

### 2. Duplicate `hq.html` / `hq-owner.html`

Both files are 413 lines and share near-identical structure.
The only meaningful difference is the owner view shows revenue and team panels.
Maintaining two copies doubles the effort when updating shared HQ sections.

### 3. Repeated localStorage keys across files

| Key | Used in |
|-----|---------|
| `techbuzz_public_agent_messages` | `public-agent.js` |
| `techbuzz_public_agent_provider` | `public-agent.js` |
| `techbuzz_public_hq_messages` | `index.html` inline script |
| `leazy_resume_drafts` | `leazy.js` |

No shared constants file — key names are string literals scattered across files.

### 4. Inline `<script>` blocks in HTML

Several HTML pages contain significant JavaScript inline in `<script>` tags rather than in
separate `.js` files. This makes it harder to search, test, or reuse the logic:

- `index.html` — public HQ chat logic (inline)
- `company-portal.html` — company registration flow (inline)
- `jobs.html` — job listing fetch (inline)
- `career.html` — career page logic (inline)

### 5. Shared CSS patterns not extracted to `core.css`

`agent.css` and `leazy.css` share:
- Chat bubble / message list styles
- Input bar / send button patterns
- Sidebar / panel layout

These are independently maintained copies of the same visual patterns.
`core.css` (198 lines) only covers global reset and typography, not component patterns.
