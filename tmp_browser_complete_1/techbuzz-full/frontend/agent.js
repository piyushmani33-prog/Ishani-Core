const $ = id => document.getElementById(id);
let agentPortalState = null;
let selectedDocumentIds = new Set();

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

function seedAgentPrompt() {
  $("agentJobDescription").value = "Hiring a senior AI engineer who can build productized automation systems, work across frontend and backend, and communicate clearly with founders.";
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
        <span>${candidate.client_company || "TechBuzz Systems"}</span>
      </div>
      <p>${candidate.genesis_profile || "Candidate profile staged through the shared empire memory."}</p>
    </div>
  `).join("") : `<div class="empty">No candidates yet. Run a Praapti hunt to build the pipeline.</div>`;
}

function renderRoles(jobs) {
  const rows = jobs || [];
  $("agentRoleList").innerHTML = rows.length ? rows.map(job => `
    <div class="stack-item">
      <strong>${job.client_company}</strong>
      <div class="stack-meta">
        <span>${job.urgency || "high"}</span>
        <span>${job.created_at || "now"}</span>
      </div>
      <p>${job.summary}</p>
    </div>
  `).join("") : `<div class="empty">No open roles yet.</div>`;
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
  const stats = [
    ["Heartbeat", `${monitor?.heartbeat_ms || 0} ms`],
    ["Alerts", alerts.length],
    ["Domains", domains.length],
    ["Reports", (monitor?.reports || []).length],
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
      <strong>${item.name}</strong>
      <div class="stack-meta">
        <span>${item.lead}</span>
        <span>${item.status}</span>
        <span>${item.priority || 0}%</span>
      </div>
      <p>${item.latest_signal}</p>
    </div>
  `).join("") : `<div class="empty">No domain systems loaded yet.</div>`;
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

async function refreshAgentConsole() {
  agentPortalState = await api("/api/portal/state");
  renderAgentStats(agentPortalState);
  renderRelayBoard(agentPortalState);
  renderRecentHunts(agentPortalState.hunts || []);
  renderVaultItems(agentPortalState.activity || []);
  renderReports(agentPortalState.reports || []);
  renderCandidates(agentPortalState.candidates || []);
  renderRoles(agentPortalState.jobs || []);
  renderQueue(agentPortalState.brain || {});
  renderMonitor(agentPortalState.monitor || {});
  renderDocuments(agentPortalState.documents || []);
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
  const data = await api("/api/leazy/chat", {
    method: "POST",
    body: JSON.stringify({ message, workspace: "agent", source: "agent_console" })
  });
  appendAgentBubble("ai", data.reply);
  await refreshAgentConsole();
}

async function bootAgent() {
  $("agentChatInput")?.addEventListener("keydown", event => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      sendAgentMessage().catch(error => appendAgentBubble("ai", error.message || "Send failed."));
    }
  });
  appendAgentBubble("ai", "Agent Console is online. Ask for sourcing plans, candidate ranking, hiring strategy, Prime Minister directives, role summaries, or the next move for TechBuzz.");
  await refreshAgentConsole();
  setInterval(refreshAgentConsole, 15000);
}

bootAgent().catch(error => {
  console.error(error);
  appendAgentBubble("ai", error.message || "Agent Console failed to load.");
});
