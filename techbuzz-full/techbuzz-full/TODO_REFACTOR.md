# TechBuzz Full — Refactoring TODO

This file documents risky, oversized, or duplicated areas identified during the codebase
audit.  **No existing behavior should be changed** until each item is reviewed.
Items are ordered roughly by risk / impact.

---

## Backend — app.py (10,244 lines)

### HIGH — `brain_hierarchy_payload()` is a 547-line monolith
**Location:** `app.py` ~line 5254  
**Risk:** Massive single function that builds the entire brain hierarchy JSON payload.
Contains nested loops, multiple SQLite queries, string manipulation, and provider checks.
Hard to test or modify without unintended side-effects.  
**Action:** Extract into sub-functions per concern (brain role, NLP profile, auto-repair
status, doctrine lessons). Each sub-function already has a named counterpart
(`brain_role_profile`, `brain_nlp_profile`, `brain_auto_repair_profile`,
`brain_doctrine_lessons`) — wire them in.

---

### HIGH — `generate_text()` is a 113-line async function with silent fallbacks
**Location:** `app.py` ~line 3169  
**Risk:** Handles all AI provider routing, token trimming, and multi-step fallback in one
function. `except Exception` blocks swallow errors and silently try the next provider.
A broken provider will never surface an error to the caller.  
**Action:** Raise structured exceptions instead of silent swallows. Split provider
selection logic (`provider_order`) from the retry loop from the actual call dispatch.

---

### MEDIUM — `compact_ollama_request()` token overflow risk
**Location:** `app.py` ~line 3106 (63 lines)  
**Risk:** Trims prompt content to fit token limits using character-count heuristics, not
actual tokenisation. Can silently truncate mid-sentence or mid-JSON.  
**Action:** Replace character-count heuristic with tiktoken or a similar tokeniser, or
add an explicit warning log when truncation occurs.

---

### MEDIUM — `warm_ollama_background()` is a long-running thread with no shutdown signal
**Location:** `app.py` ~line 2415 (175 lines)  
**Risk:** Spawned as a daemon thread on startup. Contains a long polling loop with no
cooperative stop mechanism. On server shutdown the thread is killed abruptly, which may
leave Ollama in a bad state.  
**Action:** Add a `threading.Event` stop flag so the lifespan shutdown handler can signal
the thread to exit cleanly.

---

### MEDIUM — Duplicate `recruitment_seed_brief()` definition
**Location:** `app.py` lines 2691 and 2791  
**Risk:** The function is defined twice with different signatures. Python silently uses
the second definition, making the first unreachable dead code.  
**Action:** Remove the first definition (line 2691) after verifying no callers depend on
its signature.

---

### MEDIUM — `repair_operator_state_and_brain_memory()` does unchecked state mutation
**Location:** `app.py` line 1281  
**Risk:** Mutates the global state JSON directly without validation guards for all keys.
A missing key in `default_state()` causes a KeyError that halts repair silently.  
**Action:** Add explicit presence checks for each key before writing, and log what was
repaired vs. what was skipped.

---

### MEDIUM — No rate limiting on most authenticated API routes
**Location:** `app.py` — `check_rate_limit()` is defined (line 1975) but only applied
to the public chat endpoints.  
**Risk:** Authenticated users can flood expensive AI routes (`/api/chat`,
`/api/brain/think/{brain_id}`, `/api/swarm/mission`, etc.) without throttling.  
**Action:** Apply `check_rate_limit()` (or a per-user variant) to all AI-calling routes.

---

### LOW — `save_state_unlocked()` / `load_state_unlocked()` are not atomic
**Location:** `app.py` lines 1099–1113  
**Risk:** File is written by overwriting in place. A crash mid-write corrupts the state
file permanently. A file lock is used but does not protect against partial writes.  
**Action:** Write to a temp file, then `os.replace()` for atomic swap.

---

### LOW — SQLite connections are opened per-call with no connection pool
**Location:** `app.py` — `db_connect()` line 1184  
**Risk:** Under concurrent load, each request opens and closes a fresh connection.
SQLite allows multiple readers but only one writer; no WAL mode is explicitly set.  
**Action:** Enable WAL mode (`PRAGMA journal_mode=WAL`) in `db_connect()` and consider a
small connection pool via `threading.local()`.

---

## Backend — empire_merge_layer.py (1,289 lines)

### HIGH — XML parsing vulnerable to XXE (RSS feeds)
**Location:** `empire_merge_layer.py` — `parse_news_feed()` ~line 288  
**Risk:** Uses `xml.etree.ElementTree.fromstring()` on RSS XML fetched from arbitrary
URLs. ElementTree resolves external entities in some Python versions; a malicious feed
can cause SSRF or file disclosure.  
**Action:** Use `defusedxml` instead of the stdlib `xml.etree.ElementTree`, or
explicitly set `resolve_entities=False` with lxml.

---

### HIGH — Regex-based HTML cleanup is not robust
**Location:** `empire_merge_layer.py` — `cleanup_text()` ~line 240  
**Risk:**
```python
re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", value, flags=re.I)
re.sub(r"<[^>]+>", " ", text)
```
Regex HTML parsing misses malformed tags, nested structures, and HTML entities.
Scraped content can contain XSS payloads that survive the cleanup.  
**Action:** Replace with `html.parser` (`HTMLParser`) or `BeautifulSoup` with
`html.parser` backend (already available via requirements).

---

### HIGH — `ddg_search()` and `scrape_url()` have no timeout or validation
**Location:** `empire_merge_layer.py` ~lines 245–275  
**Risk:** HTTP requests to DuckDuckGo and arbitrary URLs use `httpx.AsyncClient` with
no explicit timeout. A slow or hung remote host will block the worker indefinitely.
Scraped URLs are not validated — an internal IP (`127.0.0.1`, `169.254.x.x`) is
reachable (SSRF risk).  
**Action:** Add `timeout=10` to all `httpx` calls. Validate that URLs start with
`https://` and do not resolve to private IP ranges.

---

### MEDIUM — `emit_carbon()` silently swallows all exceptions
**Location:** `empire_merge_layer.py` ~line 223  
**Risk:** Any database write failure inside `emit_carbon()` is caught and discarded.
Carbon events may be lost without any log entry, making debugging very difficult.  
**Action:** At minimum, log the exception (`logger.warning(...)`) before suppressing it.

---

### MEDIUM — `install_empire_merge_layer()` is a 1,126-line single function
**Location:** `empire_merge_layer.py` line 163–end  
**Risk:** All route handlers are defined as closures inside one giant function.
This makes the file hard to navigate, test individually, or split into sub-routers.  
**Action:** Group related handlers (ATS, Network, HQ, Carbon, Intel, Media) into
FastAPI `APIRouter` instances and `include_router()` them from the install function.

---

### LOW — No input length cap on `NetworkSignalReq.query`
**Location:** `empire_merge_layer.py` — `NetworkSignalReq` model  
**Risk:** The `query` field is passed directly to DuckDuckGo search. An unbounded query
string can generate excessively long URLs or hit search engine limits silently.  
**Action:** Add `max_length=500` to the Pydantic field.

---

## Frontend

### HIGH — `async function api()` duplicated in 7 JS files
**Files:** `agent.js`, `leazy.js`, `empire-pages.js`, `accounts-command.js`,
`navigator.js`, `login.js`, `public-agent.js`  
**Risk:** Each copy may diverge. Bug fixes and auth-header changes must be applied
separately to every file.  
**Action:** Extract to a single `api-client.js` (or `api.js`) module, import via
`<script type="module">` or a shared include in all HTML pages.

---

### MEDIUM — `hq.html` and `hq-owner.html` are near-identical (413 lines each)
**Risk:** Any change to the HQ layout must be made twice.  
**Action:** Merge into a single `hq.html` and show/hide owner-only sections based on a
server-provided `is_owner` flag in the page payload.

---

### MEDIUM — Significant JS logic in inline `<script>` blocks
**Files:** `index.html`, `company-portal.html`, `jobs.html`, `career.html`  
**Risk:** Inline scripts cannot be linted, bundled, or cached separately.  
**Action:** Extract inline scripts to dedicated `.js` files.

---

### LOW — `localStorage` key names are hard-coded string literals
**Risk:** A typo in any file silently creates a separate key. No shared constants.  
**Action:** Define a `STORAGE_KEYS` constants object in a shared JS file.

---

### LOW — `core.css` does not cover shared component patterns
**Risk:** Chat bubble, input bar, and panel layout styles are duplicated between
`agent.css` and `leazy.css`.  
**Action:** Move shared component styles to `core.css` (or a new `components.css`).
