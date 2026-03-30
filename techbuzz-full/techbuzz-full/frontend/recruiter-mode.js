/* Recruiter Product Mode — recruiter-mode.js */
"use strict";

// ── State ──────────────────────────────────────────────────────────────────
let rmMode   = "sheet";       // "sheet" | "summary"
let rmFmt    = "plain_text";  // "plain_text" | "tsv" | "csv"
let rmOutput = "";            // last generated output string
let rmFormVisible = true;

// ── API helper ──────────────────────────────────────────────────────────────
async function rmApi(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers    = isFormData ? {} : { "Content-Type": "application/json" };
  try {
    const res = await fetch(path, { ...options, headers: { ...headers, ...(options.headers || {}) } });
    if (res.status === 401) { window.location.href = "/login"; return null; }
    if (res.status === 403) { window.location.href = "/login"; return null; }
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) return await res.json();
    return await res.text();
  } catch (e) {
    console.error("rmApi error:", e);
    return null;
  }
}

// ── Toast ────────────────────────────────────────────────────────────────────
function rmToast(msg, duration = 2200) {
  const el = document.getElementById("rmToast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), duration);
}

// ── Clipboard helper (mirrors agent.js copyTextToClipboard pattern) ────────
function rmCopyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).catch(() => rmCopyFallback(text));
  }
  rmCopyFallback(text);
}

function rmCopyFallback(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.top  = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try { document.execCommand("copy"); } catch (e) { /* silent */ }
  document.body.removeChild(ta);
}

// ── Clipboard copy actions ──────────────────────────────────────────────────
async function rmCopy(target) {
  if (!rmOutput) { rmToast("⚠ No output to copy — generate first"); return; }

  if (target === "raw") {
    rmCopyText(rmOutput);
    rmToast("✓ Copied");
    return;
  }

  const data = await rmApi("/api/recruiter-status/format-for-share", {
    method: "POST",
    body: JSON.stringify({ output: rmOutput, target }),
  });

  if (!data) { rmToast("⚠ Could not format output"); return; }

  const text = data.formatted || rmOutput;
  rmCopyText(text);

  const labels = { teams: "✓ Copied for Teams", whatsapp: "✓ Copied for WhatsApp", email: "✓ Copied for Email" };
  rmToast(labels[target] || "✓ Copied");
}

// ── Native share ─────────────────────────────────────────────────────────────
async function rmShare() {
  if (!rmOutput) { rmToast("⚠ No output to share — generate first"); return; }

  if (navigator.share) {
    try {
      await navigator.share({ title: "Recruiter Status", text: rmOutput });
      return;
    } catch (e) {
      if (e.name !== "AbortError") console.warn("share error", e);
      return; // user cancelled
    }
  }
  // fallback → plain copy
  rmCopyText(rmOutput);
  rmToast("✓ Copied (Share not available in this browser)");
}

// ── Mode / format switching ─────────────────────────────────────────────────
function rmSetMode(mode, btn) {
  rmMode = mode;
  document.querySelectorAll(".rm-mode-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");

  // hide format row for summary mode
  const fmtRow = document.getElementById("rmFormatRow");
  if (fmtRow) fmtRow.style.display = mode === "summary" ? "none" : "";
}

function rmSetFmt(fmt, btn) {
  rmFmt = fmt;
  document.querySelectorAll(".rm-fmt-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
}

// ── Generate status ──────────────────────────────────────────────────────────
async function rmGenerate() {
  const btn = document.getElementById("rmGenerateBtn");
  const out = document.getElementById("rmOutput");

  btn.disabled = true;
  btn.innerHTML = '<span class="rm-spin"></span> Generating…';
  out.value = "";

  const data = await rmApi("/api/recruiter-status/generate", {
    method: "POST",
    body: JSON.stringify({ mode: rmMode, format: rmFmt }),
  });

  btn.disabled = false;
  btn.textContent = "Generate";

  if (!data) { out.value = "Error — please try again."; return; }

  rmOutput = data.output || "";
  out.value = rmOutput;
  if (!rmOutput) out.value = "No data found. Add some tracker rows first.";
}

// ── Quick stats ───────────────────────────────────────────────────────────────
async function rmLoadStats() {
  const data = await rmApi("/api/recruiter-status/quick-stats");
  if (!data) return;
  document.getElementById("statTotal").textContent      = data.total_rows       ?? "—";
  document.getElementById("statToday").textContent      = data.today_updated    ?? "—";
  document.getElementById("statInterviews").textContent = data.interviews_scheduled ?? "—";
  document.getElementById("statOffers").textContent     = data.offers           ?? "—";
  document.getElementById("statClosures").textContent   = data.closures         ?? "—";
}

// ── Tracker rows ──────────────────────────────────────────────────────────────
async function rmLoadTracker() {
  const list = document.getElementById("rmTrackerList");
  list.innerHTML = '<div class="rm-tracker-empty">Loading…</div>';

  const data = await rmApi("/api/recruitment-tracker/export?scope=tracker");
  if (!data) {
    list.innerHTML = '<div class="rm-tracker-empty">Could not load tracker.</div>';
    return;
  }

  const tsv = (typeof data === "string") ? data : (data.tsv || "");
  const lines = tsv.trim().split("\n").filter(Boolean);

  if (lines.length <= 1) {
    list.innerHTML = '<div class="rm-tracker-empty">No tracker rows yet. Add your first candidate above!</div>';
    return;
  }

  // Parse TSV — headers on line 0, data from line 1
  const headers = lines[0].split("\t").map(h => h.trim());
  const rows = lines.slice(1).map(line => {
    const cols = line.split("\t");
    const obj = {};
    headers.forEach((h, i) => { obj[h] = (cols[i] || "").trim(); });
    return obj;
  });

  if (!rows.length) {
    list.innerHTML = '<div class="rm-tracker-empty">No tracker rows yet.</div>';
    return;
  }

  list.innerHTML = rows.map((row, idx) => {
    const name     = row["Candidate Name"] || row["candidate_name"] || "—";
    const position = row["Position"]       || row["position"]       || "—";
    const stage    = (row["Stage"]         || row["process_stage"]  || "sourced").toLowerCase().replace(/\s+/g, "_");
    const status   = (row["Status"]        || row["response_status"]|| "pending_review").toLowerCase().replace(/\s+/g, "_");
    const stageLabel  = stage.charAt(0).toUpperCase()  + stage.slice(1).replace(/_/g, " ");
    const statusLabel = status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, " ");

    return `
      <div class="rm-tracker-row" data-idx="${idx}" data-name="${esc(name)}" data-pos="${esc(position)}" data-stage="${esc(stage)}" data-status="${esc(status)}">
        <div class="rm-tracker-name">${esc(name)}</div>
        <div class="rm-tracker-meta">
          <span>${esc(position)}</span>
        </div>
        <div class="rm-tracker-meta">
          <span class="rm-badge stage-${esc(stage)}">${esc(stageLabel)}</span>
          <span class="rm-badge status-${esc(status)}">${esc(statusLabel)}</span>
        </div>
        <div class="rm-tracker-actions">
          <button class="rm-btn small" onclick="rmEditRow(${idx})">✏ Edit</button>
          <button class="rm-btn small" onclick="rmQuickStatus(${idx})">🔄 Status</button>
        </div>
      </div>
    `;
  }).join("");
}

// HTML escape helper
function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Edit a tracker row (pre-fill form) ───────────────────────────────────────
function rmEditRow(idx) {
  const row = document.querySelector(`.rm-tracker-row[data-idx="${idx}"]`);
  if (!row) return;

  document.getElementById("rmCandidateName").value = row.dataset.name   || "";
  document.getElementById("rmPosition").value      = row.dataset.pos    || "";
  document.getElementById("rmStage").value         = row.dataset.stage  || "sourced";
  document.getElementById("rmStatus").value        = row.dataset.status || "pending_review";
  document.getElementById("rmRowId").value         = "";  // TSV doesn't carry row IDs

  if (!rmFormVisible) rmToggleForm();
  document.getElementById("rmCandidateName").focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
  rmToast("ℹ Row loaded for editing — update and Save");
}

// ── Quick stage cycle ────────────────────────────────────────────────────────
function rmQuickStatus(idx) {
  const row = document.querySelector(`.rm-tracker-row[data-idx="${idx}"]`);
  if (!row) return;

  const stages = ["sourced", "screening", "interview", "offer", "hired", "closed"];
  const cur    = row.dataset.stage || "sourced";
  const next   = stages[(stages.indexOf(cur) + 1) % stages.length];

  // Pre-fill form with updated stage, let user confirm/save
  document.getElementById("rmCandidateName").value = row.dataset.name   || "";
  document.getElementById("rmPosition").value      = row.dataset.pos    || "";
  document.getElementById("rmStage").value         = next;
  document.getElementById("rmStatus").value        = row.dataset.status || "pending_review";
  document.getElementById("rmRowId").value         = "";

  if (!rmFormVisible) rmToggleForm();
  window.scrollTo({ top: 0, behavior: "smooth" });
  rmToast(`ℹ Stage → ${next} — review and Save`);
}

// ── Form save ────────────────────────────────────────────────────────────────
async function rmSaveRow(e) {
  e.preventDefault();

  const name   = document.getElementById("rmCandidateName").value.trim();
  const pos    = document.getElementById("rmPosition").value.trim();
  const stage  = document.getElementById("rmStage").value;
  const status = document.getElementById("rmStatus").value;
  const notes  = document.getElementById("rmRemarks").value.trim();
  const rowId  = document.getElementById("rmRowId").value.trim();

  if (!name) { rmToast("⚠ Candidate name is required"); return; }

  const btn = document.getElementById("rmSaveBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="rm-spin"></span> Saving…';

  const payload = {
    candidate_name: name,
    position: pos,
    process_stage: stage,
    response_status: status,
    remarks: notes,
    row_id: rowId,
  };

  const data = await rmApi("/api/recruiter-status/tracker-add", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  btn.disabled = false;
  btn.textContent = "Save to Tracker";

  if (!data || !data.ok) {
    rmToast("⚠ Save failed — please try again");
    return;
  }

  rmToast(data.action === "updated" ? "✓ Row updated" : "✓ Candidate added");
  rmClearForm();
  rmRefreshAll();
}

// ── Form helpers ─────────────────────────────────────────────────────────────
function rmClearForm() {
  document.getElementById("rmTrackerForm").reset();
  document.getElementById("rmRowId").value = "";
  document.getElementById("rmFormStatus").textContent = "";
}

function rmToggleForm() {
  rmFormVisible = !rmFormVisible;
  const body    = document.getElementById("rmFormBody");
  const toggle  = document.getElementById("rmFormToggle");
  if (body)   body.style.display   = rmFormVisible ? "" : "none";
  if (toggle) toggle.classList.toggle("collapsed", !rmFormVisible);
}

// ── Refresh all data ──────────────────────────────────────────────────────────
async function rmRefreshAll() {
  await Promise.all([rmLoadStats(), rmLoadTracker()]);
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  rmRefreshAll();
});
