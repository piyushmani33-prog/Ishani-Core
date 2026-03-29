const $ = id => document.getElementById(id);
let agentPortalState = null;
let selectedDocumentIds = new Set();
let agentEventSource = null;
let agentRefreshTimer = null;
let preparedActionUrl = "";
let recruiterVaultStatus = null;
let localVaultMirrorMeta = null;
let vaultMirrorDirty = false;
const RECRUITMENT_VAULT_DB = "techbuzz-recruitment-vault";
const RECRUITMENT_VAULT_STORE = "vault_snapshots";

async function api(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(path, {
    headers: isFormData ? {} : { "Content-Type": "application/json" },
    ...options
  });
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }
  if (response.status === 401) {
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname + window.location.hash)}`;
    throw new Error("Session expired. Redirecting to login.");
  }
  if (!response.ok) {
    throw new Error(data.detail || data.message || ("Request failed: " + response.status));
  }
  return data;
}

function appendAgentBubble(type, text) {
  const item = document.createElement("div");
  item.className = "bubble " + type;
  item.textContent = text;
  $("agentChatLog").appendChild(item);
  $("agentChatLog").scrollTop = $("agentChatLog").scrollHeight;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function copyTextToClipboard(text) {
  const value = String(text ?? "");
  if (!value) return false;
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch (error) {
    const area = document.createElement("textarea");
    area.value = value;
    area.style.position = "fixed";
    area.style.opacity = "0";
    area.style.top = "0";
    area.style.left = "0";
    area.readOnly = false;
    document.body.appendChild(area);
    area.focus();
    area.setSelectionRange(0, area.value.length);
    area.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (_) {
      copied = false;
    }
    document.body.removeChild(area);
    return copied;
  }
}

function openRecruitmentVaultDb() {
  return new Promise((resolve, reject) => {
    if (!("indexedDB" in window)) {
      resolve(null);
      return;
    }
    const request = window.indexedDB.open(RECRUITMENT_VAULT_DB, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(RECRUITMENT_VAULT_STORE)) {
        db.createObjectStore(RECRUITMENT_VAULT_STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Recruitment vault database could not be opened."));
  });
}

async function saveRecruitmentVaultSnapshot(snapshot) {
  const db = await openRecruitmentVaultDb();
  if (!db) return false;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(RECRUITMENT_VAULT_STORE, "readwrite");
    tx.objectStore(RECRUITMENT_VAULT_STORE).put(snapshot);
    tx.oncomplete = () => {
      db.close();
      resolve(true);
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error || new Error("Recruitment vault snapshot could not be saved."));
    };
  });
}

async function loadRecruitmentVaultSnapshot() {
  const db = await openRecruitmentVaultDb();
  if (!db) return null;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(RECRUITMENT_VAULT_STORE, "readonly");
    const request = tx.objectStore(RECRUITMENT_VAULT_STORE).get("active");
    request.onsuccess = () => {
      db.close();
      resolve(request.result || null);
    };
    request.onerror = () => {
      db.close();
      reject(request.error || new Error("Recruitment vault snapshot could not be loaded."));
    };
  });
}

async function clearRecruitmentVaultSnapshot() {
  const db = await openRecruitmentVaultDb();
  if (!db) return false;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(RECRUITMENT_VAULT_STORE, "readwrite");
    tx.objectStore(RECRUITMENT_VAULT_STORE).delete("active");
    tx.oncomplete = () => {
      db.close();
      resolve(true);
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error || new Error("Recruitment vault snapshot could not be cleared."));
    };
  });
}

function buildRecruitmentVaultSnapshot() {
  return {
    id: "active",
    saved_at: new Date().toISOString(),
    vault: recruiterVaultStatus || agentPortalState?.recruitment_vault || {},
    recruitment_tracker: agentPortalState?.recruitment_tracker || {},
    recruiter_reporting: agentPortalState?.recruiter_reporting || {},
    recruitment_ops: agentPortalState?.recruitment_ops || {},
    candidate_intelligence: agentPortalState?.candidate_intelligence || {},
  };
}

async function flushRecruitmentVaultMirror() {
  if (!vaultMirrorDirty || !agentPortalState) return;
  try {
    const snapshot = buildRecruitmentVaultSnapshot();
    await saveRecruitmentVaultSnapshot(snapshot);
    localVaultMirrorMeta = {
      saved_at: snapshot.saved_at,
      cache_key: (snapshot.vault || {}).local_cache_key || "",
    };
    vaultMirrorDirty = false;
    renderRecruitmentVault(recruiterVaultStatus || agentPortalState?.recruitment_vault || {});
  } catch (error) {
    console.error(error);
  }
}

function seedAgentPrompt() {
  $("agentJobDescription").value = "Hiring a senior AI engineer who can build productized automation systems, work across frontend and backend, and communicate clearly with founders.";
}

function syncFieldValue(id, value) {
  const field = $(id);
  if (!field) return;
  if (document.activeElement === field) return;
  if (!field.value || field.dataset.synced !== "manual") {
    field.value = value ?? "";
  }
}

function syncResumeFieldValue(id, value) {
  const field = $(id);
  if (!field) return;
  if (document.activeElement === field) return;
  if (!field.value || field.dataset.synced !== "manual") {
    field.value = value ?? "";
  }
}

function formatMoney(amount, currency = "INR") {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      maximumFractionDigits: 2,
    }).format(Number(amount || 0));
  } catch (error) {
    return `${currency || "INR"} ${Number(amount || 0).toFixed(2)}`;
  }
}

function describeRecruiterExportSummary(summary) {
  if (!summary) return "";
  if (typeof summary === "string") return summary;
  const totals = summary.totals || {};
  const dsr = summary.dsr || {};
  const hsr = summary.hsr || {};
  return [
    `Rows ${totals.rows || 0}`,
    `Submitted ${totals.submitted || 0}`,
    `Interested ${totals.interested || 0}`,
    `Drafts ${totals.drafts || 0}`,
    `DSR processed ${dsr.profiles_processed || 0}`,
    `HSR processed ${hsr.profiles_processed || 0}`,
  ].join(" | ");
}

function seedAccountsEntry() {
  $("accountsEntryType").value = "income";
  $("accountsEntryCategory").value = "retainer";
  $("accountsEntryAmount").value = "45000";
  $("accountsEntryTaxPercent").value = $("accountsTaxRate")?.value || "18";
  $("accountsCounterparty").value = "TechBuzz Growth Client";
  $("accountsEntryDescription").value = "Monthly retainer invoice for strategy, automation, and hiring support.";
  $("accountsOccurredOn").value = new Date().toISOString().slice(0, 10);
}

function clearDraftFlags(ids) {
  ids.forEach(id => {
    const field = $(id);
    if (field) delete field.dataset.synced;
  });
}

function currentCandidateFilters() {
  return {
    search: $("candidateSearch")?.value?.trim() || "",
    stage: $("candidateStageFilter")?.value || "",
    detail: $("candidateDetailLevel")?.value || "guided",
    allow_full_context: Boolean($("candidateAllowFull")?.checked),
  };
}

function currentRecruiterReportFilters() {
  return {
    date_from: $("reportDateFrom")?.value || "",
    date_to: $("reportDateTo")?.value || "",
    recruiter: $("reportRecruiterFilter")?.value?.trim() || "",
    candidate_name: $("reportCandidateFilter")?.value?.trim() || "",
    client_name: $("reportClientFilter")?.value?.trim() || "",
    position: $("reportPositionFilter")?.value?.trim() || "",
    mail_id: $("reportMailFilter")?.value?.trim() || "",
    contact_no: $("reportContactFilter")?.value?.trim() || "",
    notice_period: $("reportNoticeFilter")?.value?.trim() || "",
    row_id: $("reportRowIdFilter")?.value?.trim() || "",
    min_total_exp: $("reportMinExpFilter")?.value?.trim() || "",
    max_total_exp: $("reportMaxExpFilter")?.value?.trim() || "",
    min_ctc: $("reportMinCtcFilter")?.value?.trim() || "",
    max_ctc: $("reportMaxCtcFilter")?.value?.trim() || "",
    submission_state: $("reportSubmissionStateFilter")?.value?.trim() || "",
    response_status: $("reportResponseStatusFilter")?.value?.trim() || "",
  };
}

function currentAgentConsoleFilters() {
  return {
    ...currentCandidateFilters(),
    ...currentRecruiterReportFilters(),
  };
}

function queryStringFromObject(values) {
  const params = new URLSearchParams();
  Object.entries(values || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === false) return;
    params.set(key, String(value));
  });
  const query = params.toString();
  return query ? "?" + query : "";
}

function renderAgentStats(state) {
  const dashboard = state.dashboard || {};
  const brain = state.brain || {};
  const cabinet = state.cabinet || {};
  const primeMinister = cabinet.prime_minister || {};
  const metrics = dashboard.metrics || {};
  const stats = [
    ["Hunts Today", metrics.praapti_hunts_today || 0],
    ["Revenue", `${metrics.projected_revenue_inr || 0} Cr`],
    ["Protection", `${metrics.vishnu_protection || 0}%`],
    ["Brain Temp", brain.temperature || 0],
    ["Packages", metrics.packages_active || 0],
    ["Secretaries", primeMinister.active_secretaries || 0]
  ];
  $("agentStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  $("agentAvatarStrip").innerHTML = (dashboard.active_avatars || []).map(item => `<span class="avatar-pill">${item.name}</span>`).join("");
  $("agentGuardian").textContent = `Guardian ${dashboard.memory_guardian.status}. Seal ${dashboard.memory_guardian.seal}. Prime Minister ${primeMinister.enabled ? "loop live" : "paused"}.`;
  $("agentProviderBadge").textContent = dashboard.provider || state.settings?.active_provider || "built-in";
  $("agentModeBadge").textContent = `Mode ${brain.mode || "Bridge"}`;
  $("agentGuardianBadge").textContent = dashboard.memory_guardian?.seal || "Guardian";
  $("agentCabinetSummary").innerHTML = `
    <div class="stack-item">
      <strong>${primeMinister.name || "Prime Minister"}</strong>
      <div class="stack-meta">
        <span>${primeMinister.enabled ? "loop live" : "loop paused"}</span>
        <span>${primeMinister.active_secretaries || 0} secretaries</span>
      </div>
      <p>${primeMinister.objective || "No cabinet mandate set yet."}</p>
    </div>
  `;
}

function renderRelayBoard(state) {
  const brain = state.brain || {};
  const pillars = brain.pillars || [];
  const evolution = brain.evolution_cycle || [];
  const rows = [...pillars.slice(0, 2), ...evolution.slice(0, 2)];
  $("agentRelayBoard").innerHTML = rows.map(item => {
    const score = item.score || 0;
    return `
      <div class="relay-card">
        <span>${item.label}</span>
        <strong>${score}%</strong>
        <div class="meter"><div class="meter-fill" style="width:${score}%"></div></div>
        <p>${item.summary || item.status || ""}</p>
      </div>
    `;
  }).join("");
}

function renderRecentHunts(hunts) {
  const rows = hunts || [];
  $("recentHunts").innerHTML = rows.length ? rows.map(item => `
    <div class="stack-item">
      <strong>${item.client_company || "TechBuzz Systems"}</strong>
      <div class="stack-meta">
        <span>${(item.avatars || []).join(" + ") || "Rama"}</span>
        <span>${item.provider || "built-in"}</span>
      </div>
      <p>${(item.job_description || "").slice(0, 180)}</p>
    </div>
  `).join("") : `<div class="empty">No hunts yet. Run Praapti from this page and the results will appear here.</div>`;
}

function renderVaultItems(activity) {
  const rows = activity || [];
  $("agentVaultList").innerHTML = rows.length ? rows.slice(0, 5).map(item => `
    <div class="stack-item">
      <strong>${item.title}</strong>
      <div class="stack-meta">
        <span>${item.kind}</span>
        <span>${item.created_at}</span>
      </div>
      <p>${item.summary}</p>
    </div>
  `).join("") : `<div class="empty">The vault is empty for now.</div>`;
}

function renderReports(reports) {
  const rows = reports || [];
  const cabinetCycle = agentPortalState?.cabinet?.mission_log?.[0];
  const merged = cabinetCycle
    ? [{ title: "Prime Minister Cycle", summary: cabinetCycle.report || cabinetCycle.objective || "Cabinet cycle logged." }, ...rows]
    : rows;
  $("agentReportList").innerHTML = merged.length ? merged.slice(0, 4).map(item => `
    <div class="stack-item">
      <strong>${item.title}</strong>
      <p>${item.summary}</p>
    </div>
  `).join("") : `<div class="empty">No reports yet.</div>`;
}

function renderCandidates(candidates) {
  const rows = candidates || [];
  $("agentCandidateList").innerHTML = rows.length ? rows.map(candidate => `
    <div class="candidate">
      <strong>${candidate.name} - ${candidate.title}</strong>
      <div class="candidate-meta">
        <span>Fit ${candidate.fit_score}</span>
        <span>${candidate.experience} years</span>
        <span>${candidate.stage || "applied"}</span>
        <span>${candidate.client_company || "TechBuzz Systems"}</span>
      </div>
      <p>${candidate.summary || candidate.genesis_profile || "Candidate profile staged through the shared empire memory."}</p>
      ${(candidate.ai_strength || candidate.ai_concern) ? `<p>Strength: ${candidate.ai_strength || "n/a"}${candidate.ai_concern ? ` | Concern: ${candidate.ai_concern}` : ""}</p>` : ""}
      ${candidate.email ? `<p>Email: ${candidate.email}</p>` : ""}
    </div>
  `).join("") : `<div class="empty">No candidates yet. Run a Praapti hunt to build the pipeline.</div>`;
}

function renderRoles(jobs) {
  const rows = jobs || [];
  $("agentRoleList").innerHTML = rows.length ? rows.map(job => `
    <div class="stack-item">
      <strong>${job.title || job.client_company}</strong>
      <div class="stack-meta">
        <span>${job.department || "department not set"}</span>
        <span>${job.location || "location not set"}</span>
        <span>${job.urgency || "high"}</span>
        <span>${job.created_at || "now"}</span>
        <span>${job.candidate_count || 0} candidates</span>
      </div>
      <p>${job.summary}</p>
    </div>
  `).join("") : `<div class="empty">No open roles yet.</div>`;
}

function buildTrackerIssueChips(issueFlags = []) {
  return issueFlags.length
    ? issueFlags.map(flag => `<span class="avatar-pill">${flag.replace(/_/g, " ")}</span>`).join("")
    : `<span class="avatar-pill">clear</span>`;
}

async function updateTrackerRow(rowId, payload = {}) {
  try {
    const data = await api("/api/recruitment-tracker/update", {
      method: "POST",
      body: JSON.stringify({ row_id: rowId, ...payload })
    });
    $("trackerHeadline").textContent = data.message || "Recruitment tracker updated.";
    await refreshAgentConsole();
  } catch (error) {
    $("trackerHeadline").textContent = error.message || "Tracker update failed. Please try again.";
  }
}

async function prepareTrackerAcknowledgment(rowId) {
  try {
    const data = await api("/api/recruitment-tracker/prepare-ack", {
      method: "POST",
      body: JSON.stringify({ row_id: rowId })
    });
    preparedActionUrl = data.launch_url || "";
    $("actionCenterStatus").textContent =
      `${data.message || "Acknowledgment prepared."}\n\nPrepared: ${data.label}\n${data.summary}`;
    $("captureStatus").textContent =
      `${data.message || "Acknowledgment prepared."}\n\nSubject: ${data.subject || ""}\n\n${data.body || ""}`;
    await loadRecruitmentCore();
  } catch (error) {
    if ($("actionCenterStatus")) {
      $("actionCenterStatus").textContent = error.message || "Acknowledgment preparation failed. Please try again.";
    }
  }
}

function renderRecruitmentTracker(tracker) {
  const summary = tracker?.summary || {};
  const totals = summary.totals || {};
  const dsr = summary.dsr || {};
  const hsr = summary.hsr || {};
  const issueCounts = summary.issue_counts || {};
  const rows = tracker?.rows || [];
  if ($("trackerStats")) {
    const stats = [
      ["Rows", totals.rows || 0],
      ["Submitted", totals.submitted || 0],
      ["Drafts", totals.drafts || 0],
      ["Interested", totals.interested || 0],
      ["Ack Sent", totals.ack_sent || 0],
      ["Ack Confirmed", totals.ack_confirmed || 0],
      ["Follow Ups", totals.follow_ups_due || 0],
    ];
    $("trackerStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("trackerHeadline")) {
    $("trackerHeadline").textContent =
      `${summary.headline || "Tracker memory is loading."} ` +
      `Visible rows: ${rows.length}.`;
  }
  if ($("trackerRowList")) {
    $("trackerRowList").innerHTML = rows.length ? rows.map(row => `
      <div class="stack-item">
        <strong>${row.candidate_name} - ${row.position}</strong>
        <div class="stack-meta">
          <span>${row.process_stage || "sourced"}</span>
          <span>${row.response_status || "pending_review"}</span>
          <span>${row.submission_state || "draft"}</span>
          <span>${row.sourced_from || "manual"}</span>
          <span>${row.total_exp || 0} yrs</span>
          <span>${row.notice_period || "notice n/a"}</span>
        </div>
        <p>${row.summary || row.remarks || "Tracker row is ready for recruiter action."}</p>
        ${row.skill_snapshot ? `<p>Skills: ${escapeHtml(row.skill_snapshot)}</p>` : ""}
        ${row.resume_file_name ? `<p>Resume: ${escapeHtml(row.resume_file_name)}</p>` : ""}
        ${row.follow_up_due_at ? `<p>Follow up due: ${escapeHtml(row.follow_up_due_at)}</p>` : ""}
        <div class="avatar-strip">${buildTrackerIssueChips(row.issue_flags || [])}</div>
        <div class="button-row">
          <button class="agent-btn small" onclick="prepareTrackerAcknowledgment('${row.id}')">Prepare Ack</button>
          <button class="agent-btn small" onclick="updateTrackerRow('${row.id}', { ack_action: 'sent' })">Mark Ack Sent</button>
          <button class="agent-btn small" onclick="scheduleTrackerInterview('${row.id}', 'L1')">Schedule L1</button>
          <button class="agent-btn small" onclick="updateTrackerRow('${row.id}', { ack_action: 'confirmed' })">Mark Confirmed</button>
          <button class="agent-btn small" onclick="updateTrackerRow('${row.id}', { response_status: 'no_response', issue_flags: ['no_response'] })">No Response</button>
          <button class="agent-btn small" onclick="updateTrackerRow('${row.id}', { response_status: 'screen_rejected', issue_flags: ['screen_rejected'] })">Screen Reject</button>
          <button class="agent-btn small" onclick="updateTrackerRow('${row.id}', { response_status: 'not_interested', issue_flags: ['not_interested'] })">Not Interested</button>
        </div>
      </div>
    `).join("") : `<div class="empty">No tracker rows yet. Import ATS candidates or run Praapti first.</div>`;
  }
  if ($("trackerReportStats")) {
    const stats = [
      ["DSR Profiles", dsr.profiles_processed || 0],
      ["DSR Interested", dsr.interested || 0],
      ["DSR No Response", dsr.no_response || 0],
      ["HSR Profiles", hsr.profiles_processed || 0],
      ["HSR Submitted", hsr.submitted || 0],
      ["HSR Ack Sent", hsr.ack_sent || 0],
    ];
    $("trackerReportStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("trackerReportNarrative")) {
    $("trackerReportNarrative").textContent =
      `Daily summary: ${dsr.profiles_processed || 0} rows touched today, ${dsr.interested || 0} interested, ` +
      `${dsr.no_response || 0} no response, ${dsr.screen_rejected || 0} screen rejected.\n\n` +
      `Last 2 hours: ${hsr.profiles_processed || 0} rows touched, ${hsr.submitted || 0} submitted, ` +
      `${hsr.ack_sent || 0} acknowledgment mails marked sent, ${hsr.interested || 0} interested.`;
  }
  if ($("trackerIssueBoard")) {
    const issueRows = Object.entries(issueCounts)
      .filter(([, value]) => Number(value || 0) > 0)
      .sort((a, b) => Number(b[1]) - Number(a[1]));
    $("trackerIssueBoard").innerHTML = issueRows.length ? issueRows.map(([issue, count]) => `
      <div class="stack-item">
        <strong>${issue.replace(/_/g, " ")}</strong>
        <p>${count} tracker row(s) are carrying this issue right now.</p>
      </div>
    `).join("") : `<div class="empty">No active issue clusters right now.</div>`;
  }
}

function renderRecruitmentOps(ops) {
  const exports = ops?.exports || {};
  const journey = ops?.journey || {};
  const interviews = ops?.interviews || {};
  const defaults = ops?.capture_defaults || {};

  syncFieldValue("captureClientName", defaults.client_name || "TechBuzz Systems Pvt Ltd");
  syncFieldValue("captureRecruiter", defaults.recruiter || "");
  syncFieldValue("captureSource", defaults.source || "naukri");
  syncResumeFieldValue("resumeClientName", defaults.client_name || "TechBuzz Systems Pvt Ltd");
  syncResumeFieldValue("resumeRecruiter", defaults.recruiter || "");
  syncResumeFieldValue("resumeSource", defaults.source || "naukri");

  if ($("journeyStats")) {
    const stats = [
      ["Journey Events", (journey.events || []).length],
      ["Upcoming Interviews", interviews?.stats?.upcoming || 0],
      ["Pending Feedback", interviews?.stats?.pending_feedback || 0],
      ["Follow Ups", interviews?.stats?.follow_ups || 0],
      ["Tracker Rows", exports?.tracker?.row_count || 0],
      ["DSR Rows", exports?.dsr?.row_count || 0],
    ];
    $("journeyStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("journeyList")) {
    $("journeyList").innerHTML = (journey.events || []).length ? journey.events.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.candidate_name)} - ${escapeHtml(item.position)}</strong>
        <div class="stack-meta">
          <span>${escapeHtml((item.stage || "sourced").replace(/_/g, " "))}</span>
          <span>${escapeHtml(item.response_status || "pending")}</span>
          <span>${escapeHtml(item.created_at || "now")}</span>
        </div>
        <p>${escapeHtml(item.summary || "Journey update captured.")}</p>
      </div>
    `).join("") : `<div class="empty">No journey events captured yet.</div>`;
  }
  if ($("interviewDesk")) {
    $("interviewDesk").innerHTML = (interviews.upcoming || []).length ? interviews.upcoming.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.candidate_name)} - ${escapeHtml(item.interview_round || "L1")}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(item.position || "Open role")}</span>
          <span>${escapeHtml(item.scheduled_for || "schedule pending")}</span>
          <span>${escapeHtml(item.feedback_status || "pending")}</span>
        </div>
        <p>${escapeHtml(item.interviewer_name || "Interviewer not assigned yet")} | ${escapeHtml(item.mode || "virtual")}</p>
      </div>
    `).join("") : `<div class="empty">No interview events logged yet.</div>`;
  }
  if ($("followUpDesk")) {
    $("followUpDesk").innerHTML = (interviews.follow_ups || []).length ? interviews.follow_ups.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.candidate_name)} - ${escapeHtml(item.position)}</strong>
        <div class="stack-meta">
          <span>${escapeHtml((item.process_stage || "sourced").replace(/_/g, " "))}</span>
          <span>${escapeHtml(item.response_status || "pending")}</span>
          <span>${escapeHtml(item.submission_state || "draft")}</span>
        </div>
        <p>${escapeHtml(item.summary || "Follow-up pending.")}</p>
        ${item.follow_up_due_at ? `<p>${escapeHtml(`Follow up due ${item.follow_up_due_at}`)}</p>` : ""}
      </div>
    `).join("") : `<div class="empty">No follow-up queue right now.</div>`;
  }
  if ($("trackerExportBox")) {
    $("trackerExportBox").textContent = exports.tracker?.tsv || "Tracker export will appear here.";
  }
  if ($("resumeIntakeStatus")) {
    const trackerSummary = agentPortalState?.recruitment_tracker?.summary?.totals || {};
    if (!$("resumeIntakeStatus").dataset.manual) {
      $("resumeIntakeStatus").textContent =
        `Resume intake ready. Drafts ${trackerSummary.drafts || 0} | Confirmed ${trackerSummary.ack_confirmed || 0} | Follow ups due ${trackerSummary.follow_ups_due || 0}.\n\n` +
        `Upload the candidate resume after acknowledgment. If acknowledgment is still pending, the AI will keep the row in draft memory and prepare the mail flow instead of forcing a confirmed tracker.`;
    }
  }
}

function renderRecruiterReporting(reporting) {
  const payload = reporting || {};
  const allowed = payload.allowed !== false;
  const stats = payload.stats || {};
  const trail = payload.discussion_trail?.items || [];
  const snapshots = payload.snapshots?.items || [];
  const latestExport = payload.latest_export || {};
  const sourceMode = payload.source_mode || latestExport.source_mode || "live";
  const archive = payload.archive || latestExport.archive || {};
  const activeFilters = Object.entries(payload.filters || {})
    .filter(([, value]) => value !== "" && value !== null && value !== undefined && value !== false)
    .map(([key, value]) => `${key.replace(/_/g, " ")}: ${value}`);

  if ($("reportDeskStats")) {
    const items = allowed
      ? [
          ["Trail Events", stats.discussion_events || 0],
          ["Snapshots", stats.report_snapshots || 0],
          ["Filtered Rows", stats.filtered_rows || 0],
          ["Latest Export", latestExport.row_count || 0],
        ]
      : [
          ["Trail Events", 0],
          ["Snapshots", 0],
          ["Filtered Rows", 0],
          ["Latest Export", 0],
        ];
    $("reportDeskStats").innerHTML = items
      .map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`)
      .join("");
  }

  if ($("reportDeskStatus")) {
    if (!allowed) {
      $("reportDeskStatus").textContent =
        payload.headline || "Recruiter reporting is available only inside the recruiter workspace.";
    } else {
      $("reportDeskStatus").textContent =
        `${payload.headline || "Recruiter memory desk is ready."}\n\n` +
        `${sourceMode === "archive" ? "Source: sealed server archive recall (read-only)." : "Source: live recruiter operational lane."}` +
        `${archive.archive_name ? `\nArchive: ${archive.archive_name}` : ""}\n\n` +
        `${latestExport.headline || "Filtered export is ready."}\n` +
        `${describeRecruiterExportSummary(latestExport.summary) || ""}`.trim() +
        `${activeFilters.length ? `\n\nActive filters:\n- ${activeFilters.join("\n- ")}` : "\n\nActive filters: none"}`;
    }
  }

  if ($("discussionTrailList")) {
    $("discussionTrailList").innerHTML = allowed && trail.length
      ? trail.map(item => `
        <div class="stack-item">
          <strong>${escapeHtml(item.candidate_name)} - ${escapeHtml(item.position)}</strong>
          <div class="stack-meta">
            <span>${escapeHtml((item.event_type || "conversation").replace(/_/g, " "))}</span>
            <span>${escapeHtml(item.recruiter || "recruiter n/a")}</span>
            <span>${escapeHtml(item.created_at || "now")}</span>
          </div>
          <p>${escapeHtml(item.summary || "No summary captured.")}</p>
        </div>
      `).join("")
      : `<div class="empty">${allowed ? "No discussion trail found for the current filters." : "Recruiter trail is hidden for non-recruiter users."}</div>`;
  }

  if ($("reportHistoryList")) {
    $("reportHistoryList").innerHTML = allowed && snapshots.length
      ? snapshots.map(item => `
        <div class="stack-item">
          <strong>${escapeHtml((item.kind || "tracker").toUpperCase())} - ${escapeHtml(item.window_label || item.window_key || "latest")}</strong>
          <div class="stack-meta">
            <span>${escapeHtml(item.row_count || 0)} rows</span>
            <span>${escapeHtml(item.updated_at || "now")}</span>
          </div>
          <p>${escapeHtml(item.summary || item.headline || "Snapshot ready.")}</p>
        </div>
      `).join("")
      : `<div class="empty">${allowed ? "No stored DSR/HSR snapshots yet." : "Recruiter snapshots are hidden for non-recruiter users."}</div>`;
  }

  if ($("reportDeskExportBox")) {
    $("reportDeskExportBox").textContent = allowed
      ? (latestExport.tsv || "Filtered tracker or report export will appear here for copy-paste into Excel or chat.")
      : "Recruiter reporting is available only inside the recruiter workspace.";
  }
}

function renderRecruitmentVault(vault) {
  const payload = vault || {};
  recruiterVaultStatus = payload;
  const counts = payload.counts || {};
  const archives = payload.archives || [];
  const latestArchive = payload.latest_archive || {};

  if ($("vaultStats")) {
    const items = [
      ["Local Gen", payload.local_generation || 0],
      ["Server Gen", payload.server_generation || 0],
      ["Records", payload.local_record_count || 0],
      ["Docs", payload.local_document_count || 0],
      ["Archives", archives.length],
      ["Archive Recall", payload.archive_recall_ready ? "ready" : "idle"],
      ["Local Mirror", localVaultMirrorMeta?.saved_at ? "ready" : "idle"],
    ];
    $("vaultStats").innerHTML = items.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }

  if ($("vaultStatus")) {
    const tableCounts = Object.entries(counts.tables || {})
      .map(([key, value]) => `${key.replace(/_/g, " ")} ${value}`)
      .join(" | ");
    $("vaultStatus").textContent =
      `${payload.headline || "Recruitment vault is loading."}\n\n` +
      `Status: ${payload.operational_status || "active"}\n` +
      `Fingerprint: ${payload.fingerprint || "pending"}\n` +
      `Last local sync: ${payload.last_local_sync_at || localVaultMirrorMeta?.saved_at || "not synced yet"}\n` +
      `Last server archive: ${payload.last_server_sync_at || "not archived yet"}\n` +
      `Last import: ${payload.last_imported_at || "never"}\n` +
      `Last local clear: ${payload.local_cache_cleared_at || "never"}\n` +
      `Archive recall: ${payload.archive_recall_ready ? "ready" : "not ready"}${latestArchive.archive_name ? ` (${latestArchive.archive_name})` : ""}\n` +
      `Local cache key: ${payload.local_cache_key || localVaultMirrorMeta?.cache_key || "pending"}\n\n` +
      `Counts: ${tableCounts || "no recruiter records yet"}\n\n` +
      `${payload.last_archive_summary || "No sealed server archive has been created yet."}`;
  }

  if ($("vaultArchiveList")) {
    $("vaultArchiveList").innerHTML = archives.length ? archives.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.archive_kind || "archive")} - ${escapeHtml(item.archive_name || "vault.zip")}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(item.record_count || 0)} records</span>
          <span>${escapeHtml(item.document_count || 0)} docs</span>
          <span>${escapeHtml(item.created_at || "now")}</span>
        </div>
        <p>${escapeHtml(item.summary || "Server archive is ready.")}</p>
      </div>
    `).join("") : `<div class="empty">No server archive has been written yet.</div>`;
  }
}

function renderCandidateIntelligence(intelligence) {
  const stats = intelligence?.stats || {};
  const rows = intelligence?.candidates || [];
  const policy = intelligence?.policy || [];

  if ($("candidateIntelStats")) {
    const items = [
      ["Tracked", stats.tracked_candidates || 0],
      ["Active Move", stats.active_job_change || 0],
      ["Pending Feedback", stats.pending_feedback || 0],
      ["Offers Live", stats.offers_live || 0],
      ["Strong Fit", stats.strong_fit || 0],
    ];
    $("candidateIntelStats").innerHTML = items.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }

  if ($("candidateIntelSummary")) {
    $("candidateIntelSummary").textContent =
      `${intelligence?.headline || "Candidate market intelligence is loading."}\n\n` +
      `${rows.length ? `Visible candidates: ${rows.length}` : "No candidate intelligence captured yet."}`;
  }

  if ($("candidateIntelPolicy")) {
    $("candidateIntelPolicy").textContent =
      `Recruiter guidance:\n${policy.map(item => `- ${item}`).join("\n") || "- No guidance loaded yet."}`;
  }

  if ($("candidateIntelList")) {
    $("candidateIntelList").innerHTML = rows.length ? rows.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.candidate_name)} - ${escapeHtml(item.target_role || "Talent Pool")}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(item.job_change_intent || "unknown")}</span>
          <span>${escapeHtml(item.process_stage || "sourced")}</span>
          <span>fit ${escapeHtml(item.fit_score || 0)} (${escapeHtml(item.fit_label || "unknown")})</span>
        </div>
        <p>${escapeHtml(`Companies ${item.applications_count || 0} | Interviews ${item.interviews_count || 0} | Offers ${item.offers_count || 0} | Notice ${item.notice_period || "n/a"}`)}</p>
        <p>${escapeHtml(item.latest_signal || "No latest signal.")}</p>
      </div>
    `).join("") : `<div class="empty">No candidate intelligence captured yet. Network intent and recruiter conversations will start filling this automatically.</div>`;
  }

  if ($("candidateIntelWatchList")) {
    $("candidateIntelWatchList").innerHTML = rows.length ? rows.slice(0, 8).map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.candidate_name)}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(item.current_company || "company n/a")}</span>
          <span>${escapeHtml(item.current_location || item.preferred_location || "location n/a")}</span>
        </div>
        <p>${escapeHtml(item.next_move || "No next move yet.")}</p>
      </div>
    `).join("") : `<div class="empty">No recruiter next-move desk yet.</div>`;
  }
}

function renderRecruitmentTools(tools) {
  const searchTool = tools?.intelligent_search || {};
  const crm = tools?.talent_crm || {};
  const risk = tools?.fraud_and_compliance || {};
  const workforce = tools?.workforce_planning || {};
  const market = tools?.vendor_landscape || {};

  if ($("searchToolStats")) {
    const stats = [
      ["Query Terms", searchTool?.stats?.query_terms || 0],
      ["Matched Candidates", searchTool?.stats?.matched_candidates || 0],
      ["Matched Roles", searchTool?.stats?.matched_roles || 0],
      ["Tracker Rows", searchTool?.stats?.tracker_rows || 0],
    ];
    $("searchToolStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("searchToolSummary")) {
    $("searchToolSummary").textContent =
      `${searchTool?.headline || "Search intelligence is loading."}\n\n` +
      `Search: ${searchTool?.search || "none"}\n` +
      `Stage: ${searchTool?.stage || "all"}`;
  }
  if ($("searchSuggestionList")) {
    const items = (searchTool?.suggestions || []).map(item => ({
      title: item,
      body: "Suggested search refinement",
    }));
    $("searchSuggestionList").innerHTML = items.length ? items.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.body)}</p>
      </div>
    `).join("") : `<div class="empty">No extra search suggestions right now.</div>`;
  }

  if ($("crmStats")) {
    const stats = [
      ["Hot", crm?.stats?.hot || 0],
      ["Warm", crm?.stats?.warm || 0],
      ["Watch", crm?.stats?.watch || 0],
      ["Submitted", crm?.stats?.submitted || 0],
    ];
    $("crmStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("crmPoolList")) {
    const items = [
      ...(crm?.hot_pool || []).slice(0, 2).map(item => ({ lane: "Hot", ...item })),
      ...(crm?.warm_pool || []).slice(0, 2).map(item => ({ lane: "Warm", ...item })),
      ...(crm?.watch_pool || []).slice(0, 2).map(item => ({ lane: "Watch", ...item })),
    ];
    $("crmPoolList").innerHTML = items.length ? items.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.candidate_name)} - ${escapeHtml(item.position)}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(item.lane)}</span>
          <span>${escapeHtml((item.process_stage || "sourced").replace(/_/g, " "))}</span>
          <span>${escapeHtml(item.response_status || "pending")}</span>
        </div>
        <p>${escapeHtml(item.summary || "CRM lane ready.")}</p>
      </div>
    `).join("") : `<div class="empty">Talent CRM pools are still empty.</div>`;
  }

  if ($("riskToolStats")) {
    const stats = [
      ["Fraud Watch", risk?.stats?.fraud_watch || 0],
      ["Missing Info", risk?.stats?.missing_info || 0],
      ["Ack Pending", risk?.stats?.ack_pending || 0],
      ["Pending Feedback", risk?.stats?.pending_feedback || 0],
    ];
    $("riskToolStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("riskToolSummary")) {
    $("riskToolSummary").textContent =
      `${risk?.headline || "Fraud and compliance intelligence is loading."}\n\n` +
      `${(risk?.policy || []).map(item => `- ${item}`).join("\n") || "- No policy loaded."}`;
  }
  if ($("riskToolList")) {
    const items = [
      ...(risk?.fraud_watch || []).slice(0, 3).map(item => ({ type: "Fraud Watch", title: `${item.candidate_name} - ${item.position}`, body: (item.signals || []).join(", ") })),
      ...(risk?.missing_info || []).slice(0, 2).map(item => ({ type: "Missing Info", title: `${item.candidate_name} - ${item.position}`, body: (item.missing || []).join(", ") })),
      ...(risk?.ack_pending || []).slice(0, 2).map(item => ({ type: "Ack Pending", title: `${item.candidate_name} - ${item.position}`, body: "Candidate is interested/shared but ack mail is not prepared or sent yet." })),
    ];
    $("riskToolList").innerHTML = items.length ? items.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.type)} - ${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.body)}</p>
      </div>
    `).join("") : `<div class="empty">No fraud or compliance alerts right now.</div>`;
  }

  if ($("workforceStats")) {
    const stats = [
      ["Open Roles", workforce?.stats?.open_roles || 0],
      ["Risk Roles", workforce?.stats?.risk_roles || 0],
      ["Covered Roles", workforce?.stats?.covered_roles || 0],
    ];
    $("workforceStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("workforceSummary")) {
    $("workforceSummary").textContent =
      `${workforce?.headline || "Workforce planning is loading."}\n\n` +
      `${(workforce?.priority_actions || []).map(item => `- ${item}`).join("\n") || "- No actions loaded."}`;
  }
  if ($("workforceRoleList")) {
    $("workforceRoleList").innerHTML = (workforce?.roles || []).length ? workforce.roles.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.title)}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(item.location || "location n/a")}</span>
          <span>${escapeHtml(item.urgency || "normal")}</span>
          <span>${escapeHtml(item.risk || "covered")}</span>
        </div>
        <p>${escapeHtml(`Linked ${item.linked_candidates || 0} | Hot ${item.hot_candidates || 0} | Interviews ${item.interviews || 0}`)}</p>
      </div>
    `).join("") : `<div class="empty">No workforce planning roles available yet.</div>`;
  }

  if ($("vendorToolStats")) {
    const stats = [
      ["Vendors", market?.stats?.vendors || 0],
      ["Categories", market?.stats?.categories || 0],
      ["Staffing Fit", market?.stats?.staffing_focused || 0],
      ["Enterprise Fit", market?.stats?.enterprise_focused || 0],
    ];
    $("vendorToolStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("vendorToolSummary")) {
    $("vendorToolSummary").textContent =
      `${market?.headline || "Recruiting software market intelligence is loading."}\n\n` +
      `${(market?.positioning || []).map(item => `- ${item}`).join("\n") || "- No positioning guidance loaded."}`;
  }
  if ($("vendorToolList")) {
    $("vendorToolList").innerHTML = (market?.categories || []).length ? market.categories.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.category || "Category")}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(((item.vendors || []).slice(0, 4)).join(", ") || "No vendors")}</span>
          <span>${escapeHtml(`${(item.vendors || []).length} tools`)}</span>
        </div>
        <p>${escapeHtml(item.focus || "Category focus is loading.")}</p>
      </div>
    `).join("") : `<div class="empty">No market categories loaded yet.</div>`;
  }
  if ($("vendorBenchmarkSummary")) {
    $("vendorBenchmarkSummary").textContent =
      "Use this market map as a benchmark, not as a copying guide. TechBuzz should absorb the best workflow patterns from ATS, sourcing, scheduling, and staffing platforms while staying stronger in recruiter memory, tracker automation, and delivery control.";
  }
  if ($("vendorBenchmarkList")) {
    $("vendorBenchmarkList").innerHTML = (market?.benchmark || []).length ? market.benchmark.map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.name || "Benchmark")}</strong>
        <p>${escapeHtml(item.reason || "Benchmark guidance is loading.")}</p>
      </div>
    `).join("") : `<div class="empty">No benchmark shortlist loaded yet.</div>`;
  }
}

function renderSeedPack(seedPack, learningHealth) {
  const coverage = seedPack?.coverage || {};
  const stats = [
    ["Seeded Entries", seedPack?.seeded_entries || 0],
    ["Seeded Brains", (seedPack?.seeded_brains || []).length],
    ["Knowledge Entries", learningHealth?.knowledge_entries || 0],
    ["Coverage", `${learningHealth?.coverage_percent || 0}%`],
    ["Learning Loops", (learningHealth?.loops || []).length],
    ["Healthy Brains", (learningHealth?.brains || []).filter(item => item.status === "healthy").length],
  ];
  if ($("agentSeedStats")) {
    $("agentSeedStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("agentSeedSummary")) {
    $("agentSeedSummary").textContent =
      `${seedPack?.headline || "Recruitment core is loading."}\n\n` +
      `Learning loops:\n${(learningHealth?.loops || []).map(item => `- ${item}`).join("\n") || "- No loops loaded yet."}`;
  }
  if ($("agentSeedList")) {
    $("agentSeedList").innerHTML = (seedPack?.packs || []).length ? seedPack.packs.slice(0, 8).map(pack => `
      <div class="stack-item">
        <strong>${pack.title}</strong>
        <div class="stack-meta">
          <span>${(pack.brains || []).length} brains</span>
          <span>${(pack.workspace || []).join(", ")}</span>
        </div>
        <p>${pack.summary}</p>
        <p>Coverage: ${(pack.brains || []).map(brain => `${brain} (${coverage[brain] || 0})`).join(" | ")}</p>
      </div>
    `).join("") : `<div class="empty">Recruitment seed packs are not available yet.</div>`;
  }
}

function renderWorldAtlas(world) {
  const metrics = world?.metrics || {};
  const stats = [
    ["Atlas Atoms", metrics.seeded_atoms || 0],
    ["Country Nodes", metrics.country_nodes || 0],
    ["Location Nodes", metrics.subdivision_nodes || 0],
    ["Domains", metrics.domains || 0],
    ["Role Families", metrics.role_families || 0],
    ["Thought Space", metrics.possible_thoughts || 0],
  ];
  if ($("agentWorldStats")) {
    $("agentWorldStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("agentWorldSummary")) {
    $("agentWorldSummary").textContent =
      `${world?.headline || "Global atlas is loading."}\n\n` +
      `Mode: ${world?.atlas_mode || "unknown"}\n` +
      `Policy:\n${(world?.policy || []).map(item => `- ${item}`).join("\n") || "- No atlas policy loaded yet."}`;
  }
  if ($("agentWorldSourceList")) {
    $("agentWorldSourceList").innerHTML = (world?.sources || []).length ? world.sources.map(item => `
      <div class="stack-item">
        <strong>${item.title}</strong>
        <div class="stack-meta">
          <span>${item.authority}</span>
        </div>
        <p>${item.scope}</p>
      </div>
    `).join("") : `<div class="empty">No live source packs loaded yet.</div>`;
  }
}

function renderAtsConsoleMeta(meta) {
  const stats = meta?.stats || {};
  if ($("candidateDisclosureStatus")) {
    $("candidateDisclosureStatus").textContent =
      `${meta?.disclosure_note || "Candidate disclosure mode is loading."} ` +
      `Visible candidates: ${stats.visible_candidates || 0} / ${stats.ats_candidates || 0}. ` +
      `Tracker rows: ${stats.tracker_rows || 0}.`;
  }
  if ($("agentRoleSummary")) {
    $("agentRoleSummary").textContent =
      `Visible roles: ${stats.visible_roles || 0} / ${stats.open_roles || 0} open roles. ` +
      `${(meta?.suggestions || []).length} Praapti suggestions are waiting outside ATS until you import them. ` +
      `${stats.tracker_duplicates || 0} tracker duplicate(s) are flagged. ` +
      `${stats.intelligence_candidates || 0} candidate intelligence profile(s) are live.`;
  }
}

function renderActionCenterStatus(data) {
  if ($("actionCenterKind")) {
    const current = $("actionCenterKind").value || "gmail";
    $("actionCenterKind").innerHTML = (data?.actions || []).map(action => `<option value="${action.id}">${action.label}</option>`).join("");
    $("actionCenterKind").value = current && (data?.actions || []).some(action => action.id === current) ? current : "gmail";
  }
  if ($("actionCenterStatus")) {
    $("actionCenterStatus").textContent =
      `${data?.headline || "Action Center ready."}\n\n` +
      `${(data?.policy || []).map(item => `- ${item}`).join("\n") || "- No policy loaded yet."}`;
  }
}

function renderActionCenterRecent(events) {
  if (!$("actionCenterRecent")) return;
  $("actionCenterRecent").innerHTML = (events || []).length ? events.map(event => `
    <div class="stack-item">
      <strong>${event.action_kind}</strong>
      <div class="stack-meta">
        <span>${event.target || "direct url"}</span>
        <span>${event.created_at || "now"}</span>
      </div>
      <p>${event.subject || event.body || event.launch_url}</p>
    </div>
  `).join("") : `<div class="empty">No prepared actions yet.</div>`;
}

function renderQueue(brain) {
  const rows = agentPortalState?.cabinet?.secretaries?.slice(0, 6) || [];
  if (rows.length) {
    $("agentQueueList").innerHTML = rows.map(item => `
      <div class="stack-item">
        <strong>${item.name}</strong>
        <div class="stack-meta">
          <span>${item.lane || "lane"}</span>
          <span>${item.priority || 0}%</span>
        </div>
        <p>${item.next_move || item.brief || "Awaiting next move."}</p>
      </div>
    `).join("");
    return;
  }
  const fallbackRows = brain?.recommendations || [];
  $("agentQueueList").innerHTML = fallbackRows.length ? fallbackRows.map(item => `
    <div class="stack-item">
      <strong>${item.title}</strong>
      <div class="stack-meta">
        <span>${item.layer || "bridge"}</span>
      </div>
      <p>${item.action}</p>
    </div>
  `).join("") : `<div class="empty">No execution queue yet.</div>`;
}

function renderMonitor(monitor) {
  const alerts = monitor?.alerts || [];
  const domains = monitor?.domains || [];
  const carbon = monitor?.nervous_system?.carbon_protocol || {};
  const intelligence = monitor?.nervous_system?.component_intelligence?.summary || {};
  const hierarchy = monitor?.nervous_system?.hierarchy || {};
  const hierarchySummary = hierarchy.summary || {};
  const brains = hierarchy.brains || [];
  const relays = hierarchy.permission_relays || [];
  const brainLookup = new Map(brains.map(item => [item.id, item.name]));
  const stats = [
    ["Heartbeat", `${monitor?.heartbeat_ms || 0} ms`],
    ["Alerts", alerts.length],
    ["Domains", domains.length],
    ["Reports", (monitor?.reports || []).length],
    ["Brains", hierarchySummary.total_brains || 0],
    ["Layers", hierarchySummary.layers || 0],
    ["Carbon", carbon.allotrope || "carbon-seed"],
    ["Thinking Units", intelligence.thinking_units || 0],
    ["Molecules", intelligence.molecules || 0],
    ["Vault", monitor?.memory_audit?.counts?.vault || 0],
    ["Footprint", `${monitor?.memory_audit?.footprint_kb || 0} KB`]
  ];
  $("agentMonitorStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  $("agentMonitorAlerts").innerHTML = alerts.length ? alerts.map(item => `
    <div class="stack-item">
      <strong>${item.title}</strong>
      <div class="stack-meta">
        <span>${item.level || "info"}</span>
      </div>
      <p>${item.summary}</p>
    </div>
  `).join("") : `<div class="empty">No monitor alerts right now.</div>`;
  $("agentDomainList").innerHTML = domains.length ? domains.slice(0, 10).map(item => `
    <div class="stack-item">
      <strong>${escapeHtml(item.name)}</strong>
      <div class="stack-meta">
        <span>${escapeHtml(item.lead)}</span>
        <span>${escapeHtml(item.status)}</span>
        <span>${escapeHtml(item.priority || 0)}%</span>
      </div>
      <p>${escapeHtml(item.latest_signal)}</p>
    </div>
  `).join("") : `<div class="empty">No domain systems loaded yet.</div>`;
  if ($("agentBrainHierarchy")) {
    $("agentBrainHierarchy").innerHTML = brains.length ? brains.slice(0, 14).map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.name)}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(item.layer)}</span>
          <span>${escapeHtml(item.status)}</span>
          <span>${escapeHtml(item.children_count || 0)} children</span>
        </div>
        <p>${escapeHtml(item.assigned_task || "Awaiting assignment.")}</p>
        <p>Reports to ${escapeHtml(brainLookup.get(item.parent_id) || "mother root")}.</p>
      </div>
    `).join("") : `<div class="empty">No brain hierarchy mapped yet.</div>`;
  }
  if ($("agentPermissionRelay")) {
    $("agentPermissionRelay").innerHTML = relays.length ? relays.slice(0, 16).map(item => `
      <div class="stack-item">
        <strong>${escapeHtml(item.from_name || item.from)} -> ${escapeHtml(item.to_name || item.to)}</strong>
        <div class="stack-meta">
          <span>${escapeHtml(Array.isArray(item.permission) ? item.permission.join(", ") : (item.permission || "relay"))}</span>
          <span>${escapeHtml(item.status || "live")}</span>
        </div>
        <p>${escapeHtml(item.reason || "Relay active.")}</p>
      </div>
    `).join("") : `<div class="empty">No permission relay is active yet.</div>`;
  }
}

function renderAccounts(accounts) {
  const profile = accounts?.profile || {};
  const metrics = accounts?.metrics || {};
  const guidance = accounts?.guidance || [];
  const reports = accounts?.reports || [];
  const entries = accounts?.entries || [];
  const automation = accounts?.automation || {};
  const regions = accounts?.regions || [];
  const entryTypes = accounts?.entry_types || [];

  if ($("agentAccountsStats")) {
    const stats = [
      ["Income", formatMoney(metrics.income_total, profile.currency)],
      ["Expense", formatMoney(metrics.expense_total, profile.currency)],
      ["Cashflow", formatMoney(metrics.net_cashflow, profile.currency)],
      ["Tax Reserve", formatMoney(metrics.estimated_tax_payable, profile.currency)],
      ["Entries", metrics.entries_count || 0],
      ["Reports", metrics.reports_count || 0]
    ];
    $("agentAccountsStats").innerHTML = stats.map(item => `<div class="stat"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }

  if ($("accountsRegionSelect")) {
    $("accountsRegionSelect").innerHTML = regions.map(region => `<option value="${region.code}">${region.label}</option>`).join("");
    syncFieldValue("accountsRegionSelect", profile.region_code || "IN");
  }
  if ($("accountsEntryType")) {
    const selectedType = $("accountsEntryType").value || "income";
    $("accountsEntryType").innerHTML = entryTypes.map(type => `<option value="${type.id}">${type.label}</option>`).join("");
    syncFieldValue("accountsEntryType", selectedType);
  }

  syncFieldValue("accountsBusinessName", profile.business_name || "");
  syncFieldValue("accountsBusinessType", profile.business_type || "");
  syncFieldValue("accountsCurrency", profile.currency || "INR");
  syncFieldValue("accountsTaxName", profile.tax_name || "Tax");
  syncFieldValue("accountsTaxRate", profile.default_tax_rate ?? "");
  syncFieldValue("accountsFilingCycle", profile.filing_cycle || "");
  syncFieldValue("accountsRegistration", profile.tax_registration || "");
  syncFieldValue("accountsProfileNotes", profile.notes || "");
  if ($("accountsOccurredOn") && !$("accountsOccurredOn").value) {
    $("accountsOccurredOn").value = new Date().toISOString().slice(0, 10);
  }
  if ($("accountsEntryTaxPercent") && !$("accountsEntryTaxPercent").value) {
    $("accountsEntryTaxPercent").value = profile.default_tax_rate ?? 0;
  }

  if ($("accountsProfileStatus")) {
    $("accountsProfileStatus").textContent =
      `${automation.headline || "Accounts automation ready."}\n\n` +
      `Tax lane: ${profile.tax_name || "Tax"} • Filing cycle: ${profile.filing_cycle || "custom"} • Registration: ${profile.tax_registration || "not added yet"}\n\n` +
      `${automation.notes || "Add region and ledger details to let Ishani guide accounts with more context."}`;
  }

  if ($("agentAccountsGuideList")) {
    $("agentAccountsGuideList").innerHTML = guidance.length ? guidance.map(item => `
      <div class="stack-item">
        <strong>${item.title}</strong>
        <p>${item.summary}</p>
      </div>
    `).join("") : `<div class="empty">No accounts guidance yet.</div>`;
  }

  if ($("agentAccountsReportList")) {
    $("agentAccountsReportList").innerHTML = reports.length ? reports.map(item => `
      <div class="stack-item">
        <strong>${item.title}</strong>
        <div class="stack-meta">
          <span>${item.created_at || "now"}</span>
        </div>
        <p>${item.summary}</p>
      </div>
    `).join("") : `<div class="empty">No account reports yet. Run an analysis after adding profile or ledger entries.</div>`;
  }

  if ($("agentAccountsEntryList")) {
    $("agentAccountsEntryList").innerHTML = entries.length ? entries.slice(0, 8).map(item => `
      <div class="stack-item">
        <strong>${item.category} • ${item.entry_type}</strong>
        <div class="stack-meta">
          <span>${formatMoney(item.amount, item.currency)}</span>
          <span>${item.tax_percent || 0}% ${profile.tax_name || "tax"}</span>
          <span>${item.occurred_on || item.created_at || "now"}</span>
        </div>
        <p>${item.counterparty || "No counterparty"} • ${item.description || "Ledger entry saved to the accounts relay."}</p>
      </div>
    `).join("") : `<div class="empty">No ledger entries yet. Add income, expenses, salary, or tax payments to wake the accounts relay.</div>`;
  }
}

function toggleDocumentSelection(documentId, enabled) {
  if (enabled) selectedDocumentIds.add(documentId);
  else selectedDocumentIds.delete(documentId);
}

function renderDocuments(documents) {
  const rows = documents || [];
  $("agentDocumentList").innerHTML = rows.length ? rows.map(item => `
    <div class="stack-item">
      <strong>${item.original_name}</strong>
      <div class="stack-meta">
        <span>${item.extension}</span>
        <span>${Math.max(1, Math.round((item.size_bytes || 0) / 1024))} KB</span>
        <span>${item.kind}</span>
      </div>
      <p>${item.summary || "No summary available."}</p>
      <div class="button-row">
        ${item.extension === ".pdf" ? `<label class="agent-check"><input type="checkbox" onchange="toggleDocumentSelection('${item.id}', this.checked)"> Select</label>` : ""}
        <button class="agent-btn small" onclick="extractDocument('${item.id}')">Read</button>
        ${item.extension === ".pdf" ? `<button class="agent-btn small" onclick="splitDocument('${item.id}')">Split</button>` : ""}
        <a class="agent-btn small" href="/api/documents/download/${item.id}" target="_blank">Download</a>
      </div>
    </div>
  `).join("") : `<div class="empty">No documents yet. Upload files to activate the document studio.</div>`;
}

async function extractDocument(documentId) {
  const data = await api("/api/documents/extract", {
    method: "POST",
    body: JSON.stringify({ document_id: documentId })
  });
  $("agentDocumentPreview").textContent = data.text || "No extracted text available for this document.";
}

async function uploadAgentDocuments() {
  const files = $("agentDocumentFiles").files;
  if (!files || !files.length) {
    $("agentDocumentStatus").textContent = "Choose one or more files first.";
    return;
  }
  const form = new FormData();
  Array.from(files).slice(0, 10).forEach(file => form.append("files", file));
  $("agentDocumentStatus").textContent = "Uploading documents into Ishani Core...";
  const data = await api("/api/documents/upload", {
    method: "POST",
    body: form
  });
  $("agentDocumentStatus").textContent = data.message || "Documents uploaded.";
  $("agentDocumentFiles").value = "";
  await refreshAgentConsole();
}

async function createAgentNote(format) {
  const title = $("agentNoteTitle").value.trim() || "Ishani Note";
  const content = $("agentNoteContent").value.trim();
  if (!content) {
    $("agentDocumentStatus").textContent = "Write the document content first.";
    return;
  }
  const form = new FormData();
  form.append("title", title);
  form.append("content", content);
  form.append("format", format);
  const data = await api("/api/documents/create-note", {
    method: "POST",
    body: form
  });
  $("agentDocumentStatus").textContent = data.message || "Document created.";
  $("agentDocumentPreview").textContent = content;
  $("agentNoteContent").value = "";
  await refreshAgentConsole();
}

async function mergeSelectedDocuments() {
  if (selectedDocumentIds.size < 2) {
    $("agentDocumentStatus").textContent = "Select at least two PDF files to merge.";
    return;
  }
  const data = await api("/api/documents/merge-pdf", {
    method: "POST",
    body: JSON.stringify({ document_ids: Array.from(selectedDocumentIds) })
  });
  selectedDocumentIds = new Set();
  $("agentDocumentStatus").textContent = data.message || "PDFs merged.";
  await refreshAgentConsole();
}

async function splitDocument(documentId) {
  const start = window.prompt("Start page number", "1");
  if (start === null) return;
  const end = window.prompt("End page number", start);
  const data = await api("/api/documents/split-pdf", {
    method: "POST",
    body: JSON.stringify({
      document_id: documentId,
      start_page: Number(start || 1),
      end_page: Number(end || start || 1)
    })
  });
  $("agentDocumentStatus").textContent = data.message || "PDF split complete.";
  await refreshAgentConsole();
}

async function saveAccountsProfile() {
  const data = await api("/api/accounts/profile", {
    method: "POST",
    body: JSON.stringify({
      region_code: $("accountsRegionSelect").value,
      business_name: $("accountsBusinessName").value,
      business_type: $("accountsBusinessType").value,
      currency: $("accountsCurrency").value,
      tax_name: $("accountsTaxName").value,
      default_tax_rate: Number($("accountsTaxRate").value || 0),
      filing_cycle: $("accountsFilingCycle").value,
      tax_registration: $("accountsRegistration").value,
      notes: $("accountsProfileNotes").value,
    })
  });
  $("accountsProfileStatus").textContent = data.message || "Accounts profile saved.";
  clearDraftFlags([
    "accountsRegionSelect",
    "accountsBusinessName",
    "accountsBusinessType",
    "accountsCurrency",
    "accountsTaxName",
    "accountsTaxRate",
    "accountsFilingCycle",
    "accountsRegistration",
    "accountsProfileNotes"
  ]);
  await refreshAgentConsole();
}

async function addAccountsEntry() {
  const amount = Number($("accountsEntryAmount").value || 0);
  if (!(amount > 0)) {
    $("accountsEntryStatus").textContent = "Enter a positive amount before posting to the ledger.";
    return;
  }
  const data = await api("/api/accounts/entry", {
    method: "POST",
    body: JSON.stringify({
      entry_type: $("accountsEntryType").value,
      category: $("accountsEntryCategory").value,
      amount,
      tax_percent: Number($("accountsEntryTaxPercent").value || 0),
      currency: $("accountsCurrency").value,
      counterparty: $("accountsCounterparty").value,
      description: $("accountsEntryDescription").value,
      occurred_on: $("accountsOccurredOn").value,
      source: "agent_console",
    })
  });
  $("accountsEntryStatus").textContent = data.message || "Ledger entry saved.";
  $("accountsEntryAmount").value = "";
  $("accountsCounterparty").value = "";
  $("accountsEntryDescription").value = "";
  clearDraftFlags([
    "accountsEntryType",
    "accountsEntryCategory",
    "accountsEntryAmount",
    "accountsEntryTaxPercent",
    "accountsCounterparty",
    "accountsEntryDescription",
    "accountsOccurredOn"
  ]);
  await refreshAgentConsole();
}

async function runAccountsAnalysis() {
  const data = await api("/api/accounts/analyze", {
    method: "POST",
    body: JSON.stringify({ focus: "local_tax_and_cashflow" })
  });
  $("accountsProfileStatus").textContent = data.message || "Accounts analysis complete.";
  await refreshAgentConsole();
}

async function loadRecruitmentCore() {
  const [seedPack, learningHealth, actionStatus, actionRecent, worldAtlas] = await Promise.all([
    api("/api/agent/seed-pack"),
    api("/api/agent/learning-health"),
    api("/api/action-center/status"),
    api("/api/action-center/recent"),
    api("/api/world-brain/status")
  ]);
  renderSeedPack(seedPack, learningHealth);
  renderWorldAtlas(worldAtlas);
  renderActionCenterStatus(actionStatus);
  renderActionCenterRecent(actionRecent.events || []);
}

async function prepareActionCenter() {
  const body = {
    kind: $("actionCenterKind")?.value || "gmail",
    target: $("actionCenterTarget")?.value || "",
    subject: $("actionCenterSubject")?.value || "",
    body: $("actionCenterBody")?.value || "",
    url: $("actionCenterUrl")?.value || "",
    require_confirmation: true,
  };
  const data = await api("/api/action-center/prepare", {
    method: "POST",
    body: JSON.stringify(body)
  });
  preparedActionUrl = data.launch_url || "";
  $("actionCenterStatus").textContent =
    `${data.message || "Action prepared."}\n\n` +
    `Prepared: ${data.label}\n` +
    `${data.summary}\n\n` +
    `${preparedActionUrl || "No launch url returned."}`;
  await loadRecruitmentCore();
}

function openPreparedAction() {
  if (!preparedActionUrl) {
    $("actionCenterStatus").textContent = "Prepare an action first, then open it.";
    return;
  }
  if (preparedActionUrl.startsWith("tel:") || preparedActionUrl.startsWith("sms:") || preparedActionUrl.startsWith("mailto:")) {
    window.location.href = preparedActionUrl;
    return;
  }
  window.open(preparedActionUrl, "_blank", "noopener");
}

async function copyTrackerExport(scope = "tracker") {
  try {
    const data = await api("/api/recruitment-tracker/export" + queryStringFromObject({
      scope,
      search: $("candidateSearch")?.value?.trim() || "",
      stage: $("candidateStageFilter")?.value || "",
    }));
    $("trackerExportBox").textContent = data.tsv || "";
    const copied = await copyTextToClipboard(data.tsv || "");
    $("captureStatus").textContent =
      `${data.headline || "Tracker export ready."}\n\n` +
      `${copied ? "Copied to clipboard." : "Clipboard access was blocked, so the export is shown below for manual copy."}`;
  } catch (error) {
    $("captureStatus").textContent = error.message || "Tracker export failed.";
  }
}

async function loadRecruiterMemoryDesk() {
  if ($("reportDeskStatus")) {
    $("reportDeskStatus").textContent = "Loading recruiter discussion trail and stored reports...";
  }
  try {
    const data = await api("/api/recruitment-tracker/history" + queryStringFromObject(currentRecruiterReportFilters()));
    if (agentPortalState) {
      agentPortalState.recruiter_reporting = data;
    }
    renderRecruiterReporting(data);
  } catch (error) {
    try {
      const data = await api("/api/recruitment-vault/archive-history" + queryStringFromObject(currentRecruiterReportFilters()));
      if (agentPortalState) {
        agentPortalState.recruiter_reporting = data;
      }
      renderRecruiterReporting(data);
    } catch (archiveError) {
      if ($("reportDeskStatus")) {
        $("reportDeskStatus").textContent = archiveError.message || error.message || "Recruiter memory desk failed to load.";
      }
    }
  }
}

async function syncRecruitmentVaultToServer() {
  if ($("vaultStatus")) {
    $("vaultStatus").textContent = "Refreshing the sealed server archive from the operational recruiter lane...";
  }
  const data = await api("/api/recruitment-vault/server-sync", {
    method: "POST",
    body: JSON.stringify({})
  });
  renderRecruitmentVault(data.vault || {});
}

function downloadRecruitmentVault() {
  window.open("/api/recruitment-vault/export", "_blank", "noopener");
}

function triggerRecruitmentVaultImport() {
  $("vaultImportFile")?.click();
}

async function importRecruitmentVault() {
  const fileInput = $("vaultImportFile");
  const file = fileInput?.files?.[0];
  if (!file) return;
  if ($("vaultStatus")) {
    $("vaultStatus").textContent = "Restoring the uploaded recruiter vault into the operational lane...";
  }
  const formData = new FormData();
  formData.append("file", file);
  const data = await api("/api/recruitment-vault/import", {
    method: "POST",
    body: formData,
  });
  if (fileInput) fileInput.value = "";
  vaultMirrorDirty = true;
  renderRecruitmentVault(data.vault || {});
  await refreshAgentConsole();
}

async function clearRecruitmentLocalVault() {
  const confirmed = window.confirm(
    "This will clear the operational recruiter lane for this account from the live workspace. The sealed server archive will stay with the mother brain. Continue?"
  );
  if (!confirmed) return;
  if ($("vaultStatus")) {
    $("vaultStatus").textContent = "Clearing the operational recruiter lane and sealing a server archive first...";
  }
  const data = await api("/api/recruitment-vault/clear-local", {
    method: "POST",
    body: JSON.stringify({})
  });
  await clearRecruitmentVaultSnapshot();
  localVaultMirrorMeta = null;
  renderRecruitmentVault(data.vault || {});
  await refreshAgentConsole();
}

async function loadRecruitmentArchiveRecall() {
  if ($("vaultStatus")) {
    $("vaultStatus").textContent = "Loading recruiter recall from the sealed server archive...";
  }
  const data = await api("/api/recruitment-vault/archive-history" + queryStringFromObject(currentRecruiterReportFilters()));
  if (agentPortalState) {
    agentPortalState.recruiter_reporting = data;
  }
  renderRecruiterReporting(data);
  if ($("vaultStatus")) {
    const archive = data.archive || {};
    $("vaultStatus").textContent =
      `Read-only archive recall loaded.\n\n` +
      `${archive.archive_name ? `Archive: ${archive.archive_name}\n` : ""}` +
      `${archive.summary || "The sealed server archive is now feeding the recruiter memory desk without restoring the live operational lane."}`;
  }
}

async function copyArchiveRecall(scope = "tracker") {
  const data = await api("/api/recruitment-vault/archive-export" + queryStringFromObject({
    scope,
    ...currentCandidateFilters(),
    ...currentRecruiterReportFilters(),
  }));
  $("reportDeskExportBox").textContent = data.tsv || "";
  const copied = await copyTextToClipboard(data.tsv || "");
  $("reportDeskStatus").textContent =
    `${data.headline || "Archive export ready."}\n\n` +
    `${describeRecruiterExportSummary(data.summary)}\n\n` +
    `${copied ? "Copied to clipboard." : "Clipboard access was blocked, so the archive export is shown here for manual copy."}`;
  if (agentPortalState) {
    agentPortalState.recruiter_reporting = {
      ...(agentPortalState.recruiter_reporting || {}),
      latest_export: data,
      filters: currentRecruiterReportFilters(),
      allowed: true,
      source_mode: "archive",
      archive: data.archive || {},
    };
  }
}

async function copyHistoricalTracker(scope = "tracker") {
  try {
    const data = await api("/api/recruitment-tracker/export" + queryStringFromObject({
      scope,
      ...currentCandidateFilters(),
      ...currentRecruiterReportFilters(),
    }));
    $("reportDeskExportBox").textContent = data.tsv || "";
    const copied = await copyTextToClipboard(data.tsv || "");
    $("reportDeskStatus").textContent =
      `${data.headline || "Filtered export ready."}\n\n` +
      `${describeRecruiterExportSummary(data.summary)}\n\n` +
      `${copied ? "Copied to clipboard." : "Clipboard access was blocked, so the export is shown here for manual copy."}`;
    if (agentPortalState) {
      agentPortalState.recruiter_reporting = {
        ...(agentPortalState.recruiter_reporting || {}),
        latest_export: data,
        filters: currentRecruiterReportFilters(),
        allowed: true,
      };
    }
  } catch (error) {
    try {
      await copyArchiveRecall(scope);
    } catch (archiveError) {
      $("reportDeskStatus").textContent = archiveError.message || error.message || "Filtered export failed.";
    }
  }
}

async function processRecruiterCapture() {
  const transcript = $("captureTranscript")?.value?.trim() || "";
  if (!transcript) {
    $("captureStatus").textContent = "Paste the recruiter-candidate conversation or call notes first.";
    return;
  }
  const body = {
    transcript,
    candidate_name: $("captureCandidateName")?.value || "",
    position: $("capturePosition")?.value || "",
    client_name: $("captureClientName")?.value || "",
    recruiter: $("captureRecruiter")?.value || "",
    sourced_from: $("captureSource")?.value || "",
    auto_prepare_ack: true,
  };
  try {
    const data = await api("/api/recruitment-tracker/capture", {
      method: "POST",
      body: JSON.stringify(body)
    });
    if (data.acknowledgment?.launch_url) {
      preparedActionUrl = data.acknowledgment.launch_url;
    }
    $("captureStatus").textContent =
      `${data.message || "Conversation captured."}\n\n` +
      `${data.summary || ""}\n\n` +
      `${data.acknowledgment ? "Acknowledgment draft prepared in Action Center." : "Draft tracker memory saved. Final tracker waits for acknowledgment confirmation."}`;
    $("trackerExportBox").textContent = data.tracker_export?.tsv || "";
    $("captureTranscript").value = "";
    await refreshAgentConsole();
  } catch (error) {
    $("captureStatus").textContent = error.message || "Capture failed. Please try again.";
  }
}

function prepareResumeAckDraft() {
  const select = $("resumeAckStatus");
  const confirmed = $("resumeCandidateConfirmed");
  if (select) select.value = "prepared";
  if (confirmed) confirmed.checked = false;
  if ($("resumeIntakeStatus")) {
    $("resumeIntakeStatus").dataset.manual = "true";
    $("resumeIntakeStatus").textContent =
      "Ack draft mode selected. Upload the resume and the system will hold the tracker in draft memory until the candidate confirms on mail.";
  }
}

async function submitRecruiterResume() {
  const fileInput = $("resumeUploadFile");
  const file = fileInput?.files?.[0];
  if (!file) {
    if ($("resumeIntakeStatus")) {
      $("resumeIntakeStatus").dataset.manual = "true";
      $("resumeIntakeStatus").textContent = "Choose the candidate resume file first.";
    }
    return;
  }
  if ($("resumeIntakeStatus")) {
    $("resumeIntakeStatus").dataset.manual = "true";
    $("resumeIntakeStatus").textContent = "Uploading resume into the recruiter memory lane...";
  }
  const uploadData = new FormData();
  uploadData.append("files", file);
  const uploadResponse = await api("/api/documents/upload", {
    method: "POST",
    body: uploadData,
  });
  const document = uploadResponse.documents?.[0];
  if (!document?.id) {
    throw new Error("Resume upload completed but no document id was returned.");
  }
  const ackStatus = $("resumeAckStatus")?.value || "pending";
  const candidateConfirmed = Boolean($("resumeCandidateConfirmed")?.checked) || ackStatus === "confirmed";
  const payload = {
    document_id: document.id,
    candidate_name: $("resumeCandidateName")?.value || "",
    position: $("resumePosition")?.value || "",
    client_name: $("resumeClientName")?.value || "",
    recruiter: $("resumeRecruiter")?.value || "",
    sourced_from: $("resumeSource")?.value || "",
    mail_id: $("resumeMailId")?.value || "",
    contact_no: $("resumeContactNo")?.value || "",
    current_ctc: parseFloat(($("resumeCurrentCtc")?.value || "0").replace(/[^0-9.]/g, "")) || 0,
    expected_ctc: parseFloat(($("resumeExpectedCtc")?.value || "0").replace(/[^0-9.]/g, "")) || 0,
    notice_period: $("resumeNoticePeriod")?.value || "",
    transcript: $("resumeIntakeNotes")?.value || "",
    remarks: $("resumeIntakeNotes")?.value || "",
    ack_status: ackStatus,
    candidate_confirmed: candidateConfirmed,
  };
  const data = await api("/api/recruitment-tracker/submit-resume", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (data.acknowledgment?.launch_url) {
    preparedActionUrl = data.acknowledgment.launch_url;
  }
  const row = data.row || {};
  syncResumeFieldValue("resumeCandidateName", row.candidate_name || "");
  syncResumeFieldValue("resumeMailId", row.mail_id || "");
  syncResumeFieldValue("resumeContactNo", row.contact_no || "");
  syncResumeFieldValue("resumeNoticePeriod", row.notice_period || "");
  syncFieldValue("captureCandidateName", row.candidate_name || "");
  syncFieldValue("capturePosition", row.position || "");
  syncFieldValue("captureClientName", row.client_name || "");
  syncFieldValue("captureRecruiter", row.recruiter || "");
  if ($("resumeIntakeStatus")) {
    $("resumeIntakeStatus").dataset.manual = "true";
    $("resumeIntakeStatus").textContent =
      `${data.message || "Resume intake completed."}\n\n` +
      `${data.summary || ""}\n\n` +
      `${data.acknowledgment ? "Acknowledgment draft is ready in Action Center." : "Tracker is already confirmed or no mail draft was needed."}`;
  }
  $("trackerExportBox").textContent = data.tracker_export?.tsv || $("trackerExportBox").textContent;
  if ($("resumeIntakeNotes")) $("resumeIntakeNotes").value = "";
  if (fileInput) fileInput.value = "";
  await refreshAgentConsole();
}

async function scheduleTrackerInterview(rowId, round = "L1") {
  const scheduledFor = window.prompt(`${round} interview date/time (example: 2026-03-29 15:00)`, "");
  if (scheduledFor === null) return;
  const interviewerName = window.prompt("Interviewer name", "");
  if (interviewerName === null) return;
  const interviewerEmail = window.prompt("Interviewer email", "");
  if (interviewerEmail === null) return;
  const mode = window.prompt("Mode (virtual / office / telephonic)", "virtual");
  const data = await api("/api/recruitment-tracker/interview", {
    method: "POST",
    body: JSON.stringify({
      row_id: rowId,
      interview_round: round,
      scheduled_for: scheduledFor || "",
      interviewer_name: interviewerName || "",
      interviewer_email: interviewerEmail || "",
      mode: mode || "virtual",
      feedback_status: "requested"
    })
  });
  $("captureStatus").textContent = data.message || `${round} interview updated.`;
  await refreshAgentConsole();
}

async function importLatestHuntCandidates() {
  const data = await api("/api/ats/import-praapti", {
    method: "POST",
    body: JSON.stringify({})
  });
  $("candidateDisclosureStatus").textContent =
    `Imported ${data.imported || 0} candidate(s) from the latest Praapti hunt into ATS.`;
  await refreshAgentConsole();
}

async function refreshAgentConsole() {
  const filters = currentAgentConsoleFilters();
  agentPortalState = await api("/api/agent/console/state" + queryStringFromObject(filters));
  renderAgentStats(agentPortalState);
  renderRelayBoard(agentPortalState);
  renderRecentHunts(agentPortalState.hunts || []);
  renderVaultItems(agentPortalState.activity || []);
  renderReports(agentPortalState.reports || []);
  renderCandidates(agentPortalState.candidates || []);
  renderRoles(agentPortalState.jobs || []);
  renderRecruitmentTracker(agentPortalState.recruitment_tracker || {});
  renderRecruitmentOps(agentPortalState.recruitment_ops || {});
  renderRecruitmentVault(agentPortalState.recruitment_vault || {});
  renderRecruiterReporting(agentPortalState.recruiter_reporting || {});
  renderCandidateIntelligence((agentPortalState.recruitment_ops || {}).tools?.candidate_intelligence || agentPortalState.candidate_intelligence || {});
  renderRecruitmentTools((agentPortalState.recruitment_ops || {}).tools || {});
  renderAtsConsoleMeta(agentPortalState.ats_console || {});
  renderQueue(agentPortalState.brain || {});
  renderMonitor(agentPortalState.monitor || {});
  renderAccounts(agentPortalState.accounts || {});
  renderDocuments(agentPortalState.documents || []);
  vaultMirrorDirty = true;
  await loadRecruitmentCore();
  if (typeof renderBrainHierarchy === "function") {
    renderBrainHierarchy();
  }
  if (typeof renderIntelPanel === "function") {
    renderIntelPanel();
  }
}

function scheduleAgentStreamRefresh() {
  clearTimeout(agentRefreshTimer);
  agentRefreshTimer = setTimeout(() => {
    refreshAgentConsole().catch(error => console.error(error));
  }, 140);
}

function connectAgentStream() {
  if (!("EventSource" in window)) return;
  if (agentEventSource) {
    agentEventSource.close();
  }
  agentEventSource = new EventSource("/api/portal/stream");
  agentEventSource.addEventListener("snapshot", () => {
    scheduleAgentStreamRefresh();
  });
  agentEventSource.onerror = () => {
    // interval refresh remains as a fallback
  };
}

async function startAgentHunt() {
  const jobDescription = $("agentJobDescription").value.trim();
  if (!jobDescription) {
    $("agentHuntNarrative").textContent = "Paste a job description first.";
    return;
  }
  $("agentHuntNarrative").textContent = "Praapti is scanning the role and reading the company signal...";
  const data = await api("/api/praapti/hunt", {
    method: "POST",
    body: JSON.stringify({ job_description: jobDescription, client_company: "TechBuzz Systems Pvt Ltd" })
  });
  $("agentHuntNarrative").textContent = `Culture Insight:\n${data.culture_insight}\n\nIdeal Profile:\n${data.ideal_profile}`;
  renderCandidates(data.candidates || []);
  await refreshAgentConsole();
}

async function sendAgentMessage() {
  const input = $("agentChatInput");
  const message = input.value.trim();
  if (!message) return;
  appendAgentBubble("user", message);
  input.value = "";
  const data = await api("/api/agent/console/chat", {
    method: "POST",
    body: JSON.stringify({ message, ...currentAgentConsoleFilters() })
  });
  appendAgentBubble("ai", data.reply);
  await refreshAgentConsole();
}

async function bootAgent() {
  try {
    const snapshot = await loadRecruitmentVaultSnapshot();
    if (snapshot?.saved_at) {
      localVaultMirrorMeta = {
        saved_at: snapshot.saved_at,
        cache_key: snapshot?.vault?.local_cache_key || "",
      };
    }
  } catch (error) {
    console.error(error);
  }
  [
    "accountsRegionSelect",
    "accountsBusinessName",
    "accountsBusinessType",
    "accountsCurrency",
    "accountsTaxName",
    "accountsTaxRate",
    "accountsFilingCycle",
    "accountsRegistration",
    "accountsProfileNotes",
    "accountsEntryType",
    "accountsEntryCategory",
    "accountsEntryAmount",
    "accountsEntryTaxPercent",
    "accountsCounterparty",
    "accountsEntryDescription",
    "accountsOccurredOn",
    "candidateSearch",
    "candidateStageFilter",
    "candidateDetailLevel",
    "candidateAllowFull",
    "captureCandidateName",
    "capturePosition",
    "captureClientName",
    "captureRecruiter",
    "captureSource",
    "captureTranscript",
    "resumeCandidateName",
    "resumePosition",
    "resumeClientName",
    "resumeRecruiter",
    "resumeSource",
    "resumeAckStatus",
    "resumeMailId",
    "resumeContactNo",
    "resumeCurrentCtc",
    "resumeExpectedCtc",
    "resumeNoticePeriod",
    "resumeCandidateConfirmed",
    "resumeIntakeNotes",
    "reportDateFrom",
    "reportDateTo",
    "reportRecruiterFilter",
    "reportCandidateFilter",
    "reportClientFilter",
    "reportPositionFilter",
    "reportMailFilter",
    "reportContactFilter",
    "reportNoticeFilter",
    "reportRowIdFilter",
    "reportMinExpFilter",
    "reportMaxExpFilter",
    "reportMinCtcFilter",
    "reportMaxCtcFilter",
    "reportSubmissionStateFilter",
    "reportResponseStatusFilter",
    "actionCenterKind",
    "actionCenterTarget",
    "actionCenterSubject",
    "actionCenterBody",
    "actionCenterUrl"
  ].forEach(id => {
    const field = $(id);
    if (!field) return;
    const eventName = field.type === "checkbox" || field.tagName === "SELECT" ? "change" : "input";
    field.addEventListener(eventName, () => {
      field.dataset.synced = "manual";
    });
  });
  $("candidateSearch")?.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      refreshAgentConsole().catch(error => console.error(error));
    }
  });
  $("agentChatInput")?.addEventListener("keydown", event => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      sendAgentMessage().catch(error => appendAgentBubble("ai", error.message || "Send failed."));
    }
  });
  appendAgentBubble("ai", "Agent Console is online. I can now turn recruiter conversation notes into draft tracker memory, move confirmed resumes into finalized tracker rows after acknowledgment, keep the journey and interview desk updated, and prepare copy-ready DSR or HSR output.");
  await refreshAgentConsole();
  connectAgentStream();
  setInterval(refreshAgentConsole, 15000);
  setInterval(() => {
    flushRecruitmentVaultMirror().catch(error => console.error(error));
  }, 1000);
}

bootAgent().catch(error => {
  console.error(error);
  appendAgentBubble("ai", error.message || "Agent Console failed to load.");
});
