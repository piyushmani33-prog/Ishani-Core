# QA Report — Recruiter Workflow (TechBuzz / Ishani-Core)

**Audit date:** 2026-03-29  
**Auditor:** Copilot (automated code-review QA pass)  
**Scope:** Recruiter workflow — login → tracker CRUD → status generation → copy/share → mobile UX → error handling  

---

## Tested Scenarios

| # | Scenario | Method |
|---|----------|--------|
| 1 | Valid/invalid login, session persistence | Code review + existing audit script |
| 2 | Protected recruiter endpoints require auth | Existing audit script |
| 3 | Tracker CRUD (create/update/list) | Code review + existing audit script |
| 4 | User data isolation (cross-user access) | Code review + new audit checks |
| 5 | Tracker export — TSV format integrity | Code review + new audit checks |
| 6 | Tracker export — CSV format | Code review + new audit checks |
| 7 | Tracker capture — empty transcript rejection | Code review + new audit checks |
| 8 | Copy-to-clipboard on mobile (iOS Safari) | Code review (copyTextToClipboard fallback) |
| 9 | Mobile viewport — layout, tap targets | Code review (agent.css) |
| 10 | AI/Ollama failure — deterministic fallback | Code review (upsert_conversation_capture) |
| 11 | processRecruiterCapture — API error display | Code review |
| 12 | updateTrackerRow — API error display | Code review |
| 13 | Recruiter history, vault sync, archive recall | Existing audit script |

---

## Issues Found

### FIXED — Backend

#### 1. TSV export: newlines in free-text fields break row structure
**File:** `backend_python/recruitment_brain_layer.py` — `tracker_export_lines()`  
**Severity:** Medium  
**Detail:** Fields such as `skill_snapshot`, `role_scope`, and `remarks` had tab characters stripped but newline characters (`\n`, `\r`) were not removed. Any multi-line value in these fields would split a single tracker row across multiple lines, producing malformed TSV that Excel or spreadsheet tools cannot parse.  
**Fix:** Introduced a `_tsv_cell()` helper that strips all `\r`, `\n`, and `\t` characters from every cell value before joining with tabs. Applied consistently to all 25 columns.

---

#### 2. CSV export key missing from tracker_export_payload
**File:** `backend_python/recruitment_brain_layer.py` — `tracker_export_payload()`  
**Severity:** Low  
**Detail:** The export payload only provided a `tsv` key. The problem statement calls for CSV format alongside TSV.  
**Fix:** Added `tracker_export_csv_lines()` function that produces RFC 4180-compliant CSV (comma-separated, values containing commas or quotes are double-quote–wrapped with internal quotes doubled). The `csv` key is now included in all `tracker_export_payload` responses.

---

### FIXED — Frontend (agent.js)

#### 3. processRecruiterCapture — missing try/catch on API call
**File:** `frontend/agent.js` — `processRecruiterCapture()`  
**Severity:** Medium  
**Detail:** The `api()` call was not wrapped in a try/catch block. On any server error (400, 500, network failure) the exception would propagate silently to the browser console with no visible feedback to the recruiter.  
**Fix:** Wrapped the API call in try/catch and display `error.message` in `captureStatus` on failure.

---

#### 4. updateTrackerRow — missing try/catch on API call
**File:** `frontend/agent.js` — `updateTrackerRow()`  
**Severity:** Medium  
**Detail:** Same pattern: no error handling, so status update failures (e.g. clicking "Mark Ack Sent" on an invalid row) leave the UI frozen with no feedback.  
**Fix:** Wrapped in try/catch with error text shown in `trackerHeadline`.

---

#### 5. prepareTrackerAcknowledgment — missing try/catch on API call
**File:** `frontend/agent.js` — `prepareTrackerAcknowledgment()`  
**Severity:** Low  
**Detail:** Same pattern as above.  
**Fix:** Wrapped in try/catch with error text shown in `actionCenterStatus`.

---

#### 6. copyTextToClipboard iOS Safari fallback broken
**File:** `frontend/agent.js` — `copyTextToClipboard()`  
**Severity:** Low–Medium  
**Detail:** The `document.execCommand("copy")` fallback did not call `area.focus()` before `area.select()`. On iOS Safari, `textarea.select()` does not function without an explicit `focus()` call first, and additionally requires `setSelectionRange(0, length)`. The entire text would fail to be selected, making the copy silently fail.  
**Fix:** Added `area.focus()` and `area.setSelectionRange(0, area.value.length)` before `execCommand`. Added explicit try/catch around `execCommand` for robustness.

---

### FIXED — Frontend (agent.css)

#### 7. Button tap targets too small for mobile
**File:** `frontend/agent.css` — `.agent-btn`  
**Severity:** Low  
**Detail:** `.agent-btn` had `padding: 12px 18px` but no minimum height. Apple Human Interface Guidelines and Google Material Design both specify 44×44 px as the minimum touch target for interactive elements.  
**Fix:** Added `min-height: 44px` to `.agent-btn`.

---

## Issues Not Fixed (out of scope / low risk / by design)

| Issue | Reason not fixed |
|-------|-----------------|
| AI/Ollama unavailable — deterministic fallback already works (`upsert_conversation_capture` falls back to regex parsing when `generate_text` fails) | No fix needed; verified by code review |
| Login.css has no `min-height` for inputs on mobile | Inputs have `padding: 14px 16px` which meets the 44 px threshold implicitly; no change needed |
| `copyTextToClipboard` on iOS 12 (very old) will still fail since `navigator.clipboard` is unavailable and `execCommand` is unreliable; the output textarea is always visible as a manual-copy fallback | Acceptable; the fallback textarea is shown for manual selection |
| No CSV download button in the UI (only TSV copy exists) | CSV key now present in API response; UI wiring deferred as a UX enhancement |

---

## Regression Check

All changes are additive or narrowly targeted:
- `_tsv_cell()` and `tracker_export_csv_lines()` are new helper functions with no impact on existing code paths.
- The `csv` key is appended to the existing export payload; no existing callers are broken.
- `processRecruiterCapture`, `updateTrackerRow`, `prepareTrackerAcknowledgment`: try/catch wrappers preserve the original happy-path behavior; errors are now surfaced instead of silently thrown.
- `copyTextToClipboard`: the `navigator.clipboard.writeText` primary path is unchanged; only the fallback branch is improved.
- `min-height: 44px` on `.agent-btn` is a layout addition that cannot break existing functionality.

---

## Updated Test Coverage (recruitment_scenario_audit.py)

New checks added to the existing audit script:

1. **CSV key present** — `tracker_export.get("csv")` is truthy and contains "Candidate Name".
2. **TSV and CSV row parity** — Both formats produce the same number of rows.
3. **TSV column count** — Each data row has exactly 25 tab-separated columns (detects newline contamination regression).
4. **Empty transcript → 400** — POST `/api/recruitment-tracker/capture` with empty or whitespace-only transcript returns HTTP 400.
5. **User data isolation** — A second registered member querying the tracker export returns 0 rows for the first member's candidates.
