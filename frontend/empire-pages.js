const modeConfigs = {
  hq: {
    title: "TechBuzz HQ",
    kicker: "Public TechBuzz command layer",
    heading: "TechBuzz Systems now has a public HQ powered by the same Ishani brain that runs the internal company stack.",
    copy: "Explore the company, use the free TechBuzz AI concierge, understand hiring and automation, and move into the protected workspaces only when you need deeper execution.",
    scene: "nebula-crown.mp4",
    panels: [
      { id: "dashboard", label: "Dashboard" },
      { id: "activity", label: "Activity Log" },
      { id: "reports", label: "Reports" },
      { id: "growth", label: "Growth Engine" },
      { id: "portals", label: "Portal Links" }
    ]
  },
  hqowner: {
    title: "TechBuzz HQ Owner",
    kicker: "Master strategy, revenue, and client command",
    heading: "Owner HQ is now a dedicated strategy surface for pipeline, revenue, team lanes, and carbon-bonded operating intelligence.",
    copy: "Use this page to govern TechBuzz as one live system: client pipeline, revenue movement, team lanes, strategy, activity, and the direct bridge into Leazy and the protected company stack.",
    scene: "nebula-crown.mp4",
    panels: [
      { id: "dashboard", label: "Dashboard" },
      { id: "pipeline", label: "Client Pipeline" },
      { id: "revenue", label: "Revenue" },
      { id: "team", label: "Team" },
      { id: "strategy", label: "Strategy" },
      { id: "activity", label: "Activity" }
    ]
  },
  network: {
    title: "TechBuzz Network",
    kicker: "Signal and relationship mesh",
    heading: "Network now opens as a live signal map instead of a separate old product.",
    copy: "Use this surface to inspect hunts, packages, clients, candidates, and ecosystem movement from one visual control layer.",
    scene: "nebula-orbit.mp4",
    panels: [
      { id: "overview", label: "Overview" },
      { id: "signals", label: "Signals" },
      { id: "relationships", label: "Relationships" },
      { id: "packages", label: "Packages" },
      { id: "activity", label: "Activity Log" }
    ]
  },
  ats: {
    title: "TechBuzz ATS",
    kicker: "Hiring operations powered by Leazy",
    heading: "ATS is now a working live dashboard tied to Leazy instead of a dead-end shell.",
    copy: "Candidates, jobs, resume intake, and reports run from the same empire state so you can actually move between workflows.",
    scene: "nebula-sanctum.mp4",
    panels: [
      { id: "dashboard", label: "Dashboard" },
      { id: "candidates", label: "Candidates" },
      { id: "jobs", label: "Jobs" },
      { id: "resume-upload", label: "Resume Upload" },
      { id: "reports", label: "Reports" }
    ]
  }
};

let currentMode = "hq";
let currentPanel = "dashboard";
let portalState = null;
let resumeDrafts = [];
let publicHqMessages = [];
let publicHqPopupOpen = false;

const $ = id => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function toast(message) {
  const el = $("portalToast");
  el.textContent = message;
  el.style.display = "block";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.style.display = "none";
  }, 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
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

function appendPortalGuideBubble(type, text) {
  const log = $("portalGuideLog");
  if (!log) return;
  const item = document.createElement("div");
  item.className = `workspace-bubble ${type}`;
  item.textContent = text;
  log.appendChild(item);
  log.scrollTop = log.scrollHeight;
}

function resolveMode() {
  const path = window.location.pathname;
  if (path.startsWith("/hq")) return "hqowner";
  if (path.startsWith("/network")) return "network";
  if (path.startsWith("/ats")) return "ats";
  return "hq";
}

function loadResumeDrafts() {
  try {
    resumeDrafts = JSON.parse(localStorage.getItem("leazy_resume_drafts") || "[]");
  } catch (error) {
    resumeDrafts = [];
  }
}

function saveResumeDrafts() {
  localStorage.setItem("leazy_resume_drafts", JSON.stringify(resumeDrafts));
}

function loadPublicHqMessages() {
  try {
    publicHqMessages = JSON.parse(localStorage.getItem("techbuzz_public_hq_messages") || "[]");
  } catch (error) {
    publicHqMessages = [];
  }
  if (!publicHqMessages.length) {
    publicHqMessages = [
      {
        role: "ai",
        text: "TechBuzz AI is live. Ask about hiring, automation, document tools, or how to start working with Ishani.",
        provider: "shared-hq-brain"
      }
    ];
  }
}

function savePublicHqMessages() {
  localStorage.setItem("techbuzz_public_hq_messages", JSON.stringify(publicHqMessages.slice(-20)));
}

function renderTopLinks() {
  const links = currentMode === "hq"
    ? [
        { href: "/company/portal", label: "HQ" },
        { href: "#hqConcierge", label: "Free AI" },
        { href: "/agent", label: "Agent" },
        { href: "/login?next=/leazy", label: "Core Access" },
        { href: "/login", label: "Login" }
      ]
    : currentMode === "hqowner"
    ? [
        { href: "/hq", label: "Owner HQ" },
        { href: "/leazy", label: "Leazy" },
        { href: "/agent/console", label: "Agent" },
        { href: "/company/portal", label: "Public HQ" },
        { href: "/network", label: "Network" },
        { href: "/ats", label: "ATS" }
      ]
    : [
        { href: "/leazy", label: "Leazy" },
        { href: "/agent/console", label: "Agent" },
        { href: "/company/portal", label: "HQ" },
        { href: "/network", label: "Network" },
        { href: "/ats", label: "ATS" },
        { href: "/login", label: "Login" },
        { href: "/leazy#settings", label: "Settings" }
      ];
  $("portalLinks").innerHTML = links.map(link => `<a href="${link.href}">${link.label}</a>`).join("");
}

function setModeVisibility() {
  const publicMode = currentMode === "hq";
  document.body.classList.toggle("public-hq-mode", publicMode);
  $("publicHqStage").hidden = !publicMode;
  $("hqAiFab").hidden = !publicMode;
  if (!publicMode) {
    $("hqAiPopup").hidden = true;
    publicHqPopupOpen = false;
  }
}

function appendPublicHqMessage(role, text, provider = "") {
  publicHqMessages.push({ role, text, provider });
  publicHqMessages = publicHqMessages.slice(-20);
  savePublicHqMessages();
  renderPublicHqMessages();
}

function renderPublicHqMessages() {
  const markup = publicHqMessages.map(message => `
    <div class="public-ai-bubble ${message.role}">
      ${escapeHtml(message.text)}
      ${message.provider ? `<span class="public-ai-meta">${escapeHtml(message.provider)}</span>` : ""}
    </div>
  `).join("");
  const panelLog = $("publicAiLog");
  const popupLog = $("hqAiPopupLog");
  if (panelLog) {
    panelLog.innerHTML = markup;
    panelLog.scrollTop = panelLog.scrollHeight;
  }
  if (popupLog) {
    popupLog.innerHTML = markup;
    popupLog.scrollTop = popupLog.scrollHeight;
  }
}

function focusPublicAi() {
  const target = $("hqConcierge");
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  toggleHqPopup(true);
}

function toggleHqPopup(force) {
  if (currentMode !== "hq") return;
  publicHqPopupOpen = typeof force === "boolean" ? force : !publicHqPopupOpen;
  $("hqAiPopup").hidden = !publicHqPopupOpen;
  if (publicHqPopupOpen) {
    renderPublicHqMessages();
    setTimeout(() => $("hqAiPopupInput")?.focus(), 60);
  }
}

function quickPublicPrompt(message) {
  const input = $("publicAiInput");
  if (input) input.value = message;
  focusPublicAi();
}

function renderPublicHqStage() {
  if (!portalState || currentMode !== "hq") return;
  const dashboard = portalState.dashboard || {};
  const metrics = dashboard.metrics || {};
  const cabinet = portalState.cabinet || {};
  const plans = portalState.plans || [];
  const domains = portalState.domains || [];
  const activeAvatars = (dashboard.active_avatars || []).map(item => item.name).join(" + ") || "Rama";
  const authUser = portalState.auth?.user;

  $("publicHeroEyebrow").textContent = "TechBuzz Systems Pvt Ltd • Free Public HQ";
  $("publicHeroTitle").textContent = "TechBuzz HQ is now a public AI front door, powered by the same Ishani core that runs the internal company engine.";
  $("publicHeroText").textContent = "Use the free concierge to ask about hiring, automation, document handling, AI workflows, and how TechBuzz can help. When you need deeper execution, the same brain continues behind login.";
  $("publicBrainBadge").textContent = dashboard.identity || "Ishani Core";
  $("publicBrainCopy").textContent = `Provider ${portalState.settings?.active_provider || "built-in"} • Active avatars ${activeAvatars} • Creator mode ${dashboard.creator_mode || "enabled"}.`;
  $("publicHeroActions").innerHTML = `
    <button class="launch-btn" onclick="focusPublicAi()">Launch Free TechBuzz AI</button>
    <button class="mini-btn" onclick="window.location.href='/login?next=/agent/console'">Open Agent Workspace</button>
    <button class="mini-btn" onclick="window.location.href='/login?next=/leazy'">Open Protected Core</button>
    ${authUser?.role === "master" ? `<button class="mini-btn" onclick="window.location.href='/hq'">Open Owner HQ</button>` : ""}
  `;
  $("publicPromptChips").innerHTML = [
    "Show TechBuzz services",
    "Help me hire for a startup role",
    "What can your document studio do?",
    "Suggest an automation plan for my company",
    "How do I start with the free AI?"
  ].map(prompt => `<button class="public-chip" onclick="quickPublicPrompt('${prompt.replace(/'/g, "\\'")}')">${prompt}</button>`).join("");
  $("publicStatGrid").innerHTML = [
    ["Free AI", "Live", "Public concierge available right now"],
    ["Revenue Stack", `INR ${metrics.projected_revenue_inr} Cr`, "Shared growth engine across TechBuzz surfaces"],
    ["Hunts Today", metrics.praapti_hunts_today, "Praapti and ATS stay connected to the same state"],
    ["Vault", metrics.vault_items, "Akshaya memory keeps the company context preserved"]
  ].map(item => `
    <div class="public-stat-card">
      <span>${item[0]}</span>
      <strong>${item[1]}</strong>
      <p>${item[2]}</p>
    </div>
  `).join("");
  $("publicTrustBand").innerHTML = [
    ["Same Brain Everywhere", "The HQ site, popup concierge, Agent workspace, ATS, and Network all draw from one mother-brain state."],
    ["Free Entry Point", "Visitors can use the TechBuzz concierge without logging in."],
    ["Protected Deep Work", "Internal execution surfaces stay behind login so the public site stays safe and useful."],
    ["TechBuzz Branding First", "The public website now behaves like a real product front door, not an old detached page."]
  ].map(item => `
    <div class="public-band-item">
      <span>TechBuzz</span>
      <strong>${item[0]}</strong>
      <p>${item[1]}</p>
    </div>
  `).join("");
  $("publicCapabilityCards").innerHTML = [
    ["Public AI Concierge", "Guide visitors, answer company questions, and route them to the right TechBuzz service."],
    ["Hiring And Praapti", "Turn a job description into a sourcing, shortlist, and interview direction path."],
    ["Document Studio", "Read, summarize, merge, split, and prepare working documents from the same platform."],
    ["Automation Architecture", "Help operators plan workflows, AI usage, delivery systems, and growth sequences."]
  ].map(item => `
    <div class="public-feature-card">
      <strong>${item[0]}</strong>
      <p>${item[1]}</p>
    </div>
  `).join("");
  $("publicBrainFlow").innerHTML = `
    <div class="public-flow-grid">
      <div class="public-flow-card"><strong>Mother Brain</strong><p>${dashboard.identity || "Ishani"} keeps HQ, Agent, Network, and ATS aligned.</p></div>
      <div class="public-flow-card"><strong>Prime Minister</strong><p>${cabinet.prime_minister?.active_secretaries || 0} secretary lanes are feeding revenue and delivery visibility back into the core.</p></div>
      <div class="public-flow-card"><strong>Nervous System</strong><p>${(portalState.nervous_system?.transmissions || []).length} recent transmissions are moving between domains, reports, vault, and operators.</p></div>
      <div class="public-flow-card"><strong>Operational Domains</strong><p>${domains.slice(0, 4).map(item => item.name).join(", ")} are active right now.</p></div>
    </div>
  `;
  $("publicPlanCards").innerHTML = plans.map(plan => `
    <div class="public-plan-card">
      <strong>${plan.name}</strong>
      <p>${plan.tagline}</p>
      <span class="price">INR ${plan.price_inr}</span>
      <ul>${(plan.services || []).slice(0, 4).map(service => `<li>${service}</li>`).join("")}</ul>
    </div>
  `).join("");
  $("publicSurfaceCards").innerHTML = [
    { name: "Free TechBuzz AI", note: "Available right on this public HQ page.", href: "#hqConcierge", action: "Use Free AI" },
    { name: "Agent Workspace", note: "Member workspace for documents, chats, and operator tasks.", href: "/login?next=/agent/console", action: "Open Agent" },
    { name: "Protected Core", note: "Owner-grade Leazy bridge, cabinet, prana, and monitoring surfaces.", href: "/login?next=/leazy", action: "Open Core" },
    { name: "ATS And Hiring", note: "Connected hiring operations backed by the same shared state.", href: "/login?next=/ats", action: "Open ATS" },
    ...(authUser?.role === "master" ? [{ name: "Owner HQ", note: "Dedicated master view for client pipeline, revenue, team, and strategy.", href: "/hq", action: "Open Owner HQ" }] : [])
  ].map(item => `
    <div class="public-surface-card">
      <span>Surface</span>
      <strong>${item.name}</strong>
      <p>${item.note}</p>
      <a class="mini-btn" href="${item.href}">${item.action}</a>
    </div>
  `).join("");
  const ownerShell = $("publicOwnerShell");
  if (authUser?.role === "master") {
    const owner = portalState.hq_owner || {};
    ownerShell.hidden = false;
    $("publicOwnerSummary").innerHTML = `
      <div class="public-flow-grid">
        <div class="public-flow-card"><strong>Owner</strong><p>${escapeHtml(authUser.name)} • ${escapeHtml(authUser.email)}</p></div>
        <div class="public-flow-card"><strong>Architecture</strong><p>${escapeHtml(owner.architecture_note || "Carbon Protocol is stabilizing the operating surfaces.")}</p></div>
        <div class="public-flow-card"><strong>Protected Surfaces</strong><p>Leazy, ATS, Network, and Agent Console are now operating on one shared state layer.</p></div>
      </div>
    `;
    $("publicOwnerClients").innerHTML = (owner.client_pipeline || []).length ? (owner.client_pipeline || []).map(item => `
      <div class="public-feature-card">
        <strong>${escapeHtml(item.client)}</strong>
        <p>${item.open_roles} open role(s) • Pipeline value INR ${item.pipeline_value} Cr • ${item.status}</p>
      </div>
    `).join("") : `<div class="empty-note">No client pipeline has formed yet.</div>`;
    $("publicOwnerRevenue").innerHTML = `
      <div class="public-flow-grid">
        <div class="public-flow-card"><strong>Projected Revenue</strong><p>INR ${owner.revenue_tracker?.projected_revenue_inr || 0} Cr</p></div>
        <div class="public-flow-card"><strong>Packages</strong><p>${owner.revenue_tracker?.active_packages || 0} active package(s)</p></div>
        <div class="public-flow-card"><strong>Secretaries</strong><p>${owner.revenue_tracker?.active_secretaries || 0} active lane(s)</p></div>
        <div class="public-flow-card"><strong>Insights</strong><p>${owner.revenue_tracker?.collective_insights || 0} preserved intelligence points</p></div>
      </div>
    `;
    $("publicOwnerTeam").innerHTML = (owner.team || []).length ? (owner.team || []).map(item => `
      <div class="public-feature-card">
        <strong>${escapeHtml(item.name)}</strong>
        <p>${escapeHtml(item.lane)} • ${escapeHtml(item.status)} • Priority ${item.priority || 0}%</p>
      </div>
    `).join("") : `<div class="empty-note">No team lanes are visible yet.</div>`;
    $("publicOwnerStrategy").innerHTML = (owner.strategy || []).length ? (owner.strategy || []).map(item => `
      <div class="public-feature-card">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.action)} • Layer ${escapeHtml(item.layer)}</p>
      </div>
    `).join("") : `<div class="empty-note">No strategy cards are queued yet.</div>`;
  } else {
    ownerShell.hidden = true;
  }
  renderPublicHqMessages();
}

async function sendPublicHqMessage(source = "panel") {
  try {
    const input = source === "popup" ? $("hqAiPopupInput") : $("publicAiInput");
    const text = input?.value.trim();
    if (!text) return;
    appendPublicHqMessage("user", text);
    input.value = "";
    const data = await api("/api/public/hq-chat", {
      method: "POST",
      body: JSON.stringify({ message: text, context: "TechBuzz HQ public website" })
    });
    appendPublicHqMessage("ai", data.reply, data.provider);
  } catch (error) {
    console.error(error);
    toast(error.message || "TechBuzz AI is unavailable right now.");
  }
}

function renderTopShell() {
  const mode = modeConfigs[currentMode];
  renderTopLinks();
  setModeVisibility();
  $("portalKicker").textContent = mode.kicker;
  $("portalTitle").textContent = mode.title;
  $("railModeHeading").textContent = mode.title;
  $("railModeCopy").textContent = mode.copy;
  $("portalHeroEyebrow").textContent = "TechBuzz Systems Pvt Ltd";
  $("portalHeroTitle").textContent = mode.heading;
  $("portalHeroText").textContent = mode.copy;
  $("portalSkyVideo").src = "/frontend-assets/media/" + mode.scene;
  $("portalSkyVideo").play().catch(() => {});
  $("portalHeroActions").innerHTML = `
    <button class="launch-btn" onclick="window.location.href='/leazy#bridge'">Open Leazy Bridge</button>
    <button class="mini-btn" onclick="window.location.href='/leazy#cabinet'">Open Cabinet</button>
    <button class="mini-btn" onclick="window.location.href='/agent/console'">Open Agent</button>
    <button class="mini-btn" onclick="window.location.href='/leazy#settings'">Open Settings</button>
  `;
}

function renderNav() {
  const mode = modeConfigs[currentMode];
  $("portalNav").innerHTML = mode.panels.map(panel => `
    <button class="${panel.id === currentPanel ? "active" : ""}" onclick="showPortalPanel('${panel.id}')">${panel.label}</button>
  `).join("");
}

function portalHashPanel() {
  const hash = (window.location.hash || "").replace("#", "");
  const valid = new Set(modeConfigs[currentMode].panels.map(item => item.id));
  return valid.has(hash) ? hash : modeConfigs[currentMode].panels[0].id;
}

function showPortalPanel(panelId, updateHash = true) {
  const valid = new Set(modeConfigs[currentMode].panels.map(item => item.id));
  currentPanel = valid.has(panelId) ? panelId : modeConfigs[currentMode].panels[0].id;
  renderNav();
  renderPortalContent();
  if (updateHash) {
    if (history.replaceState) {
      history.replaceState(null, "", "#" + currentPanel);
    } else {
      window.location.hash = currentPanel;
    }
  }
}

function jumpToActivity() {
  const valid = new Set(modeConfigs[currentMode].panels.map(item => item.id));
  if (valid.has("activity")) {
    showPortalPanel("activity");
    return;
  }
  showPortalPanel("reports");
}

function renderMetricRow() {
  const metrics = portalState.dashboard.metrics || {};
  const items = [
    ["Revenue", `${metrics.projected_revenue_inr} Cr`],
    ["Hunts Today", metrics.praapti_hunts_today],
    ["Army Active", metrics.army_active],
    ["Nirmaan", metrics.nirmaan_active],
    ["Vault", metrics.vault_items],
    ["Protection", `${metrics.vishnu_protection}%`]
  ];
  $("portalHeroMetrics").innerHTML = items.map(item => `
    <div class="metric-pill">
      <span>${item[0]}</span>
      <strong>${item[1]}</strong>
    </div>
  `).join("");
}

function renderBrainBody() {
  const brain = portalState.brain || {};
  const settings = portalState.settings || {};
  const cabinet = portalState.cabinet || {};
  const primeMinister = cabinet.prime_minister || {};
  $("portalProvider").textContent = `Provider: ${settings.active_provider || "built-in"}`;
  $("portalGuardian").textContent = `Guardian: ${portalState.dashboard.memory_guardian.status} | ${portalState.dashboard.memory_guardian.seal}`;
  $("portalProtection").textContent = `Protection: ${portalState.dashboard.metrics.vishnu_protection}%`;
  $("portalBrainBody").innerHTML = `
    <div class="brain-grid">
      ${(brain.evolution_cycle || []).map(step => `
        <div class="brain-step">
          <div class="brain-step-top">
            <strong>${step.label}</strong>
            <span>${step.score}%</span>
          </div>
          <div class="brain-status">${step.status}</div>
          <p>${step.summary}</p>
        </div>
      `).join("")}
      <div class="panel-note">Mode ${brain.mode || "Bridge"} | Active avatars: ${(brain.active_avatars || []).map(item => item.name).join(" + ") || "Rama"}.</div>
      <div class="panel-note">Prime Minister: ${primeMinister.name || "Prime Minister"} | ${primeMinister.enabled ? "Loop live" : "Loop paused"} | ${primeMinister.active_secretaries || 0} secretaries.</div>
    </div>
  `;
}

function renderActivityPreview() {
  const items = (portalState.activity || []).slice(0, 6);
  $("portalActivityBody").innerHTML = items.length ? `
    <div class="activity-stack">
      ${items.map(item => `
        <div class="activity-card">
          <strong>${item.title}</strong>
          <span>${item.kind || "event"} • ${item.created_at || ""}</span>
          <p>${item.summary || ""}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No activity recorded yet.</div>`;
}

function avatarChipRow(limit = 4) {
  const avatars = portalState.dashboard?.active_avatars || [];
  return avatars.length ? `
    <div class="chip-row">
      ${avatars.slice(0, limit).map(item => `<span class="chip">${item.name}</span>`).join("")}
    </div>
  ` : `<div class="empty-note">No active avatars yet.</div>`;
}

function pillarMeterBoard() {
  const pillars = portalState.brain?.pillars || [];
  return pillars.length ? `
    <div class="ops-grid">
      ${pillars.map(pillar => `
        <div class="ops-card">
          <span>${pillar.label}</span>
          <strong>${pillar.score}%</strong>
          <div class="meter"><div class="meter-fill" style="width:${pillar.score}%"></div></div>
          <p>${pillar.summary}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No brain pillars yet.</div>`;
}

function recommendationBoard(limit = 4) {
  const rows = (portalState.brain?.recommendations || []).slice(0, limit);
  return rows.length ? `
    <div class="queue-list">
      ${rows.map(item => `
        <div class="queue-card">
          <span>${item.layer || "bridge"}</span>
          <strong>${item.title}</strong>
          <p>${item.action}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No recommendations right now.</div>`;
}

function cabinetBoard(limit = 4) {
  const cabinet = portalState.cabinet || {};
  const primeMinister = cabinet.prime_minister || {};
  const missionLog = (cabinet.mission_log || []).slice(0, limit);
  return `
    <div class="queue-list">
      <div class="queue-card">
        <span>${primeMinister.enabled ? "loop live" : "loop paused"}</span>
        <strong>${primeMinister.name || "Prime Minister"}</strong>
        <p>${primeMinister.objective || "No mandate set yet."}</p>
      </div>
      ${missionLog.map(item => `
        <div class="queue-card">
          <span>${item.source || "manual"}</span>
          <strong>${item.objective || "Cabinet cycle"}</strong>
          <p>${(item.top_secretaries || []).join(" • ") || item.report || "No secretary brief saved yet."}</p>
        </div>
      `).join("")}
    </div>
  `;
}

function candidateBoard(limit = 6) {
  const rows = (portalState.candidates || []).slice(0, limit);
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(candidate => `
        <div class="list-card">
          <strong>${candidate.name} - ${candidate.title}</strong>
          <span>${candidate.client_company} • Fit ${candidate.fit_score}</span>
          <p>${candidate.experience} years experience.</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No candidate profiles yet.</div>`;
}

function clientBoard(limit = 8) {
  const rows = (portalState.clients || []).slice(0, limit);
  return rows.length ? `
    <div class="lane-grid">
      ${rows.map(client => `
        <div class="lane-card">
          <span>Client Lane</span>
          <strong>${client}</strong>
          <p>Connected through live hunts, packages, and workspace memory.</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No client lanes yet.</div>`;
}

function packageBoard(limit = 6) {
  const rows = (portalState.packages || []).slice(0, limit);
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(pkg => `
        <div class="list-card">
          <strong>${pkg.title}</strong>
          <span>${(pkg.avatars || []).join(" + ")} • ${pkg.provider || "built-in"}</span>
          <p>${pkg.objective || "No objective saved."}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No packages launched yet.</div>`;
}

function domainBoard(limit = 8) {
  const rows = (portalState.domains || []).slice(0, limit);
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(domain => `
        <div class="list-card">
          <strong>${domain.name}</strong>
          <span>${domain.lead} - ${domain.status} - ${domain.priority || 0}%</span>
          <p>${domain.latest_signal || domain.purpose}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No operational domains loaded yet.</div>`;
}

function monitorBoard(limit = 6) {
  const rows = (portalState.monitor?.alerts || []).slice(0, limit);
  return rows.length ? `
    <div class="queue-list">
      ${rows.map(item => `
        <div class="queue-card">
          <span>${item.level || "info"}</span>
          <strong>${item.title}</strong>
          <p>${item.summary}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">Mother monitor sees no current alerts.</div>`;
}

function nervousBoard(limit = 8) {
  const transmissions = (portalState.nervous_system?.transmissions || []).slice(0, limit);
  return transmissions.length ? `
    <div class="stack-list">
      ${transmissions.map(item => `
        <div class="list-card">
          <strong>${item.from} -> ${item.to}</strong>
          <span>${item.created_at || "live"}</span>
          <p>${item.message || "Flow event captured."}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No nervous-system transmissions recorded yet.</div>`;
}

function jobBoard(limit = 6) {
  const rows = (portalState.jobs || []).slice(0, limit);
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(job => `
        <div class="list-card">
          <strong>${job.client_company}</strong>
          <span>${job.urgency} • ${job.created_at || "now"}</span>
          <p>${job.summary}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No active jobs yet.</div>`;
}

function reportBoard(limit = 6) {
  const rows = (portalState.reports || []).slice(0, limit);
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(report => `
        <div class="list-card">
          <strong>${report.title}</strong>
          <p>${report.summary}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No reports yet.</div>`;
}

function latestHuntBoard(limit = 6) {
  const rows = (portalState.hunts || []).slice(0, limit);
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(hunt => `
        <div class="list-card">
          <strong>${hunt.client_company || "TechBuzz Systems"}</strong>
          <span>${hunt.urgency || "high"} • ${hunt.provider || "built-in"}</span>
          <p>${(hunt.job_description || "").slice(0, 180)}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No Praapti hunts yet.</div>`;
}

function atsKanbanBoard() {
  const columns = portalState.ats_surface?.columns || [];
  return columns.length ? `
    <div class="lane-grid">
      ${columns.map(column => `
        <div class="lane-card">
          <span>${column.label}</span>
          <strong>${column.items.length} candidate(s)</strong>
          <div class="stack-list" style="margin-top:12px">
            ${column.items.slice(0, 4).map(item => `
              <div class="list-card">
                <strong>${item.name}</strong>
                <span>${item.title} • AI score ${item.ai_score}</span>
                <p>${item.client_company}</p>
              </div>
            `).join("") || `<div class="empty-note">No candidates in this stage.</div>`}
          </div>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">The ATS kanban board is empty until Praapti imports candidates.</div>`;
}

function networkConnectionsBoard() {
  const rows = portalState.network_surface?.connections || [];
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(item => `
        <div class="list-card">
          <strong>${item.name}</strong>
          <span>${item.kind} • strength ${item.strength}%</span>
          <p>${item.summary}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No live connections yet.</div>`;
}

function networkPostsBoard() {
  const rows = portalState.network_surface?.posts || [];
  return rows.length ? `
    <div class="stack-list">
      ${rows.map(item => `
        <div class="list-card">
          <strong>${item.title}</strong>
          <span>${item.kind} • ${item.created_at || "live"}</span>
          <p>${item.summary}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No network posts recorded yet.</div>`;
}

function quickActionGrid() {
  return `
    <div class="action-grid">
      <a class="action-card panel-link" href="/leazy"><strong>Main Site</strong><p>Open the living Leazy bridge.</p></a>
      <a class="action-card panel-link" href="/leazy#cabinet"><strong>Cabinet</strong><p>Open the Prime Minister control room.</p></a>
      <a class="action-card panel-link" href="/agent/console"><strong>Agent</strong><p>Open the strategist console.</p></a>
      <a class="action-card panel-link" href="/network"><strong>Network</strong><p>Open relationship and signal view.</p></a>
      <a class="action-card panel-link" href="/ats"><strong>ATS</strong><p>Open hiring operations.</p></a>
      <button class="action-card panel-link" onclick="showPortalPanel('dashboard')"><strong>Dashboard</strong><p>Return to the live overview.</p></button>
      <button class="action-card panel-link" onclick="showPortalPanel('activity')"><strong>Activity Log</strong><p>Open the latest vault and mission events.</p></button>
      <button class="action-card panel-link" onclick="window.location.href='/ats#candidates'"><strong>Candidates</strong><p>Jump to candidate view in ATS.</p></button>
      <button class="action-card panel-link" onclick="window.location.href='/ats#jobs'"><strong>Jobs</strong><p>Jump to active jobs in ATS.</p></button>
    </div>
  `;
}

async function atsImportLatestHunt() {
  try {
    const data = await api("/api/ats/import-latest", { method: "POST" });
    toast(data.message || "Latest Praapti hunt imported.");
    await refreshPortal();
  } catch (error) {
    console.error(error);
    toast(error.message || "ATS import failed");
  }
}

async function scanNetworkSignals() {
  try {
    const input = $("networkScannerInput");
    const query = input?.value.trim();
    if (!query) {
      toast("Enter a market or connection query first.");
      return;
    }
    const data = await api("/api/network/scan", {
      method: "POST",
      body: JSON.stringify({ query })
    });
    $("networkScannerReport").textContent = data.report || "No report returned.";
    toast(data.message || "Network scan complete.");
    await refreshPortal();
  } catch (error) {
    console.error(error);
    toast(error.message || "Network scan failed");
  }
}

function renderHqPanel() {
  const hunts = portalState.hunts || [];
  const clients = portalState.clients || [];
  const reports = portalState.reports || [];
  const packages = portalState.packages || [];

  if (currentPanel === "dashboard") {
    $("portalPrimaryTitle").textContent = "Company Dashboard";
    $("portalPrimaryBody").innerHTML = `
      <div class="data-grid">
        <div class="data-card"><span>Identity</span><strong>${portalState.dashboard.identity}</strong></div>
        <div class="data-card"><span>Creator Mode</span><strong>${portalState.dashboard.creator_mode}</strong></div>
        <div class="data-card"><span>Clients</span><strong>${clients.length}</strong></div>
        <div class="data-card"><span>Packages</span><strong>${packages.length}</strong></div>
      </div>
      <div class="panel-note">TechBuzz HQ is now directly powered by Leazy's shared brain instead of the old separate website.</div>
      ${quickActionGrid()}
    `;
    $("portalSecondaryTitle").textContent = "Client And Hunt Feed";
    $("portalSecondaryBody").innerHTML = hunts.length ? `
      <div class="stack-list">
        ${hunts.slice(0, 8).map(hunt => `
          <div class="list-card">
            <strong>${hunt.client_company || "TechBuzz Systems"}</strong>
            <span>${(hunt.avatars || []).join(" + ")} • ${hunt.provider || "built-in"}</span>
            <p>${(hunt.job_description || "").slice(0, 180)}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No Praapti hunts have been run yet.</div>`;
    $("portalTertiaryTitle").textContent = "Operational Domains";
    $("portalTertiaryBody").innerHTML = domainBoard(8);
    $("portalQueueTitle").textContent = "Mother Monitor";
    $("portalQueueBody").innerHTML = monitorBoard(5);
    return;
  }

  if (currentPanel === "activity") {
    $("portalPrimaryTitle").textContent = "Activity Log";
    $("portalPrimaryBody").innerHTML = $("portalActivityBody").innerHTML;
    $("portalSecondaryTitle").textContent = "Recent Reports";
    $("portalSecondaryBody").innerHTML = reports.length ? `
      <div class="stack-list">
        ${reports.map(report => `
          <div class="list-card">
            <strong>${report.title}</strong>
            <p>${report.summary}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No reports generated yet.</div>`;
    $("portalTertiaryTitle").textContent = "Client Lanes";
    $("portalTertiaryBody").innerHTML = clientBoard(8);
    $("portalQueueTitle").textContent = "Flow Chain";
    $("portalQueueBody").innerHTML = nervousBoard(6);
    return;
  }

  if (currentPanel === "reports") {
    $("portalPrimaryTitle").textContent = "Reports";
    $("portalPrimaryBody").innerHTML = reports.length ? `
      <div class="stack-list">
        ${reports.map(report => `
          <div class="list-card">
            <strong>${report.title}</strong>
            <p>${report.summary}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No reports yet.</div>`;
    $("portalSecondaryTitle").textContent = "Suggested Moves";
    $("portalSecondaryBody").innerHTML = `
      <div class="panel-note">Use Leazy Brain Pulse for executive direction, Praapti for hiring reports, and bounded packages for revenue research.</div>
    `;
    $("portalTertiaryTitle").textContent = "Revenue And Delivery";
    $("portalTertiaryBody").innerHTML = `
      <div class="ops-grid">
        <div class="ops-card"><span>Projected Revenue</span><strong>₹${portalState.dashboard.metrics.projected_revenue_inr} Cr</strong><p>Current revenue projection built from hunts, packages, and brain activity.</p></div>
        <div class="ops-card"><span>Collective Insights</span><strong>${portalState.dashboard.metrics.collective_insights}</strong><p>Signals already saved into the shared memory of the company system.</p></div>
      </div>
    `;
    $("portalQueueTitle").textContent = "Delivery Queue";
    $("portalQueueBody").innerHTML = packageBoard(6);
    return;
  }

  if (currentPanel === "growth") {
    $("portalPrimaryTitle").textContent = "Growth Engine";
    $("portalPrimaryBody").innerHTML = `
      <div class="launch-form">
        <input id="portalObjectiveInput" placeholder="Optional objective, for example: build a revenue pipeline for TechBuzz in fintech">
        <div class="stack-list">
          ${(portalState.package_templates || []).map(template => `
            <div class="list-card">
              <strong>${template.title}</strong>
              <span>${template.best_for}</span>
              <p>${template.summary}</p>
              <button class="launch-btn" onclick="launchPortalPackage('${template.id}')">Launch ${template.title}</button>
            </div>
          `).join("")}
        </div>
      </div>
      <div class="panel-note" id="portalPackageLog">Packages are safe bounded missions. They do not self-propagate or bypass consent.</div>
    `;
    $("portalSecondaryTitle").textContent = "Recent Packages";
    $("portalSecondaryBody").innerHTML = packages.length ? `
      <div class="stack-list">
        ${packages.map(pkg => `
          <div class="list-card">
            <strong>${pkg.title}</strong>
            <span>${(pkg.avatars || []).join(" + ")} • ${pkg.provider || "built-in"}</span>
            <p>${pkg.objective}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No bounded packages launched yet.</div>`;
    $("portalTertiaryTitle").textContent = "Growth Pressure Map";
    $("portalTertiaryBody").innerHTML = pillarMeterBoard();
    $("portalQueueTitle").textContent = "Next Revenue Moves";
    $("portalQueueBody").innerHTML = recommendationBoard(4);
    return;
  }

  $("portalPrimaryTitle").textContent = "Portal Links";
  $("portalPrimaryBody").innerHTML = quickActionGrid();
  $("portalSecondaryTitle").textContent = "Company Access";
  $("portalSecondaryBody").innerHTML = `
    <div class="panel-note">This portal now routes into the live Leazy stack with absolute paths, so Main Site, Agent, Network, and ATS all open correctly.</div>
  `;
  $("portalTertiaryTitle").textContent = "Company Mesh";
  $("portalTertiaryBody").innerHTML = domainBoard(8);
  $("portalQueueTitle").textContent = "Command Queue";
  $("portalQueueBody").innerHTML = nervousBoard(6);
}

function renderOwnerHqPanel() {
  const owner = portalState.hq_owner || {};
  const pipeline = owner.client_pipeline || [];
  const revenue = owner.revenue_tracker || {};
  const team = owner.team || [];
  const strategy = owner.strategy || [];
  const reports = portalState.reports || [];

  if (currentPanel === "dashboard") {
    $("portalPrimaryTitle").textContent = "Owner Dashboard";
    $("portalPrimaryBody").innerHTML = `
      <div class="data-grid">
        <div class="data-card"><span>Projected Revenue</span><strong>INR ${revenue.projected_revenue_inr || 0} Cr</strong></div>
        <div class="data-card"><span>Active Secretaries</span><strong>${revenue.active_secretaries || 0}</strong></div>
        <div class="data-card"><span>Active Packages</span><strong>${revenue.active_packages || 0}</strong></div>
        <div class="data-card"><span>Collective Insights</span><strong>${revenue.collective_insights || 0}</strong></div>
      </div>
      <div class="panel-note">${owner.architecture_note || "Carbon Protocol is stabilizing the company layers."}</div>
      ${quickActionGrid()}
    `;
    $("portalSecondaryTitle").textContent = "Client Pipeline Snapshot";
    $("portalSecondaryBody").innerHTML = pipeline.length ? `
      <div class="lane-grid">
        ${pipeline.map(item => `
          <div class="lane-card">
            <span>${item.status}</span>
            <strong>${item.client}</strong>
            <p>${item.open_roles} open role(s) • Pipeline value INR ${item.pipeline_value} Cr</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No client pipeline is active yet.</div>`;
    $("portalTertiaryTitle").textContent = "Team Lanes";
    $("portalTertiaryBody").innerHTML = team.length ? `
      <div class="stack-list">
        ${team.map(item => `
          <div class="list-card">
            <strong>${item.name}</strong>
            <span>${item.lane} • ${item.status} • Priority ${item.priority || 0}%</span>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No active team lanes yet.</div>`;
    $("portalQueueTitle").textContent = "Strategy Queue";
    $("portalQueueBody").innerHTML = strategy.length ? `
      <div class="queue-list">
        ${strategy.map(item => `
          <div class="queue-card">
            <span>${item.layer || "hq"}</span>
            <strong>${item.title}</strong>
            <p>${item.action}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No strategy moves are queued yet.</div>`;
    return;
  }

  if (currentPanel === "pipeline") {
    $("portalPrimaryTitle").textContent = "Client Pipeline";
    $("portalPrimaryBody").innerHTML = pipeline.length ? `
      <div class="lane-grid">
        ${pipeline.map(item => `
          <div class="lane-card">
            <span>${item.status}</span>
            <strong>${item.client}</strong>
            <p>${item.open_roles} open role(s)</p>
            <div class="meter"><div class="meter-fill" style="width:${Math.min(100, Math.round((item.pipeline_value || 0) * 20))}%"></div></div>
            <p>Pipeline value INR ${item.pipeline_value} Cr</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No client pipeline yet.</div>`;
    $("portalSecondaryTitle").textContent = "Live ATS";
    $("portalSecondaryBody").innerHTML = atsKanbanBoard();
    $("portalTertiaryTitle").textContent = "Open Jobs";
    $("portalTertiaryBody").innerHTML = jobBoard(10);
    $("portalQueueTitle").textContent = "Carbon Bond Notes";
    $("portalQueueBody").innerHTML = nervousBoard(8);
    return;
  }

  if (currentPanel === "revenue") {
    $("portalPrimaryTitle").textContent = "Revenue Tracker";
    $("portalPrimaryBody").innerHTML = `
      <div class="ops-grid">
        <div class="ops-card"><span>Projected Revenue</span><strong>INR ${revenue.projected_revenue_inr || 0} Cr</strong><p>Shared forecast across hunts, packages, and cabinet activity.</p></div>
        <div class="ops-card"><span>Packages</span><strong>${revenue.active_packages || 0}</strong><p>Bounded execution missions currently feeding growth.</p></div>
        <div class="ops-card"><span>Secretaries</span><strong>${revenue.active_secretaries || 0}</strong><p>Prime Minister secretary lanes driving execution and delivery.</p></div>
        <div class="ops-card"><span>Insights</span><strong>${revenue.collective_insights || 0}</strong><p>Preserved intelligence points available to the whole system.</p></div>
      </div>
    `;
    $("portalSecondaryTitle").textContent = "Growth Recommendations";
    $("portalSecondaryBody").innerHTML = recommendationBoard(6);
    $("portalTertiaryTitle").textContent = "Package Flow";
    $("portalTertiaryBody").innerHTML = packageBoard(8);
    $("portalQueueTitle").textContent = "Revenue Reports";
    $("portalQueueBody").innerHTML = reportBoard(6);
    return;
  }

  if (currentPanel === "team") {
    $("portalPrimaryTitle").textContent = "Team And Secretary Mesh";
    $("portalPrimaryBody").innerHTML = team.length ? `
      <div class="stack-list">
        ${team.map(item => `
          <div class="list-card">
            <strong>${item.name}</strong>
            <span>${item.lane} • ${item.status} • Priority ${item.priority || 0}%</span>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No team lanes available yet.</div>`;
    $("portalSecondaryTitle").textContent = "Operational Domains";
    $("portalSecondaryBody").innerHTML = domainBoard(12);
    $("portalTertiaryTitle").textContent = "Monitor";
    $("portalTertiaryBody").innerHTML = monitorBoard(8);
    $("portalQueueTitle").textContent = "Cabinet";
    $("portalQueueBody").innerHTML = cabinetBoard(6);
    return;
  }

  if (currentPanel === "strategy") {
    $("portalPrimaryTitle").textContent = "Strategy Layer";
    $("portalPrimaryBody").innerHTML = strategy.length ? `
      <div class="queue-list">
        ${strategy.map(item => `
          <div class="queue-card">
            <span>${item.layer || "hq"}</span>
            <strong>${item.title}</strong>
            <p>${item.action}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No strategy cards queued.</div>`;
    $("portalSecondaryTitle").textContent = "Brain Pillars";
    $("portalSecondaryBody").innerHTML = pillarMeterBoard();
    $("portalTertiaryTitle").textContent = "Carbon Bond Layer";
    $("portalTertiaryBody").innerHTML = `
      <div class="panel-note">
        ${(portalState.nervous_system?.carbon_protocol?.allotrope || "carbon-seed")} is active.
        Bond integrity ${(portalState.nervous_system?.carbon_protocol?.bond_integrity || 0)}%.
        Signals per minute ${(portalState.nervous_system?.carbon_protocol?.signals_per_minute || 0)}.
      </div>
      ${nervousBoard(8)}
    `;
    $("portalQueueTitle").textContent = "Owner Reports";
    $("portalQueueBody").innerHTML = reportBoard(8);
    return;
  }

  $("portalPrimaryTitle").textContent = "Owner Activity";
  $("portalPrimaryBody").innerHTML = $("portalActivityBody").innerHTML;
  $("portalSecondaryTitle").textContent = "Reports";
  $("portalSecondaryBody").innerHTML = reportBoard(8);
  $("portalTertiaryTitle").textContent = "Flow Chain";
  $("portalTertiaryBody").innerHTML = nervousBoard(10);
  $("portalQueueTitle").textContent = "Client Lanes";
  $("portalQueueBody").innerHTML = clientBoard(10);
}

function renderNetworkPanel() {
  const candidates = portalState.candidates || [];
  const clients = portalState.clients || [];
  const hunts = portalState.hunts || [];
  const packages = portalState.packages || [];
  const networkSurface = portalState.network_surface || {};

  if (currentPanel === "overview") {
    $("portalPrimaryTitle").textContent = "Network Overview";
    $("portalPrimaryBody").innerHTML = `
      <div class="data-grid">
        <div class="data-card"><span>Clients</span><strong>${clients.length}</strong></div>
        <div class="data-card"><span>Candidates</span><strong>${candidates.length}</strong></div>
        <div class="data-card"><span>Signals</span><strong>${hunts.length}</strong></div>
        <div class="data-card"><span>Packages</span><strong>${packages.length}</strong></div>
      </div>
      <div class="panel-note">This network view now acts like a real relationship surface: live connections, posts, and a Carbon Signal Scanner all work from the same empire state.</div>
      <div class="launch-form">
        <input id="networkScannerInput" placeholder="Scan a market or ecosystem, for example: product hiring demand in Bangalore AI startups">
        <div class="button-row">
          <button class="launch-btn" onclick="scanNetworkSignals()">Run Carbon Signal Scanner</button>
        </div>
        <div class="panel-note" id="networkScannerReport">The signal scanner report will appear here.</div>
      </div>
    `;
    $("portalSecondaryTitle").textContent = "Connection Mesh";
    $("portalSecondaryBody").innerHTML = networkConnectionsBoard();
    $("portalTertiaryTitle").textContent = "Recent Posts";
    $("portalTertiaryBody").innerHTML = networkPostsBoard();
    $("portalQueueTitle").textContent = "Signal Feed";
    $("portalQueueBody").innerHTML = (networkSurface.signals || []).length ? `
      <div class="stack-list">
        ${(networkSurface.signals || []).map(item => `
          <div class="list-card">
            <strong>${item.title}</strong>
            <span>${item.source} • ${item.created_at || "live"}</span>
            <p>${item.summary}</p>
          </div>
        `).join("")}
      </div>
    ` : nervousBoard(6);
    return;
  }

  if (currentPanel === "signals") {
    $("portalPrimaryTitle").textContent = "Signal Feed";
    $("portalPrimaryBody").innerHTML = hunts.length ? `
      <div class="stack-list">
        ${hunts.map(hunt => `
          <div class="list-card">
            <strong>${hunt.client_company || "TechBuzz Systems"}</strong>
            <span>${hunt.urgency || "high"} • ${hunt.provider || "built-in"}</span>
            <p>${(hunt.job_description || "").slice(0, 180)}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No network signals yet.</div>`;
    $("portalSecondaryTitle").textContent = "Scanner";
    $("portalSecondaryBody").innerHTML = `
      <div class="launch-form">
        <input id="networkScannerInput" placeholder="Scan a market or connection question">
        <button class="launch-btn" onclick="scanNetworkSignals()">Run Carbon Signal Scanner</button>
        <div class="panel-note" id="networkScannerReport">Signals, risks, opportunities, and next move will appear here.</div>
      </div>
    `;
    $("portalTertiaryTitle").textContent = "Recent Posts";
    $("portalTertiaryBody").innerHTML = networkPostsBoard();
    $("portalQueueTitle").textContent = "Signal Queue";
    $("portalQueueBody").innerHTML = (networkSurface.signals || []).length ? `
      <div class="stack-list">
        ${(networkSurface.signals || []).map(item => `
          <div class="list-card">
            <strong>${item.title}</strong>
            <span>${item.source}</span>
            <p>${item.summary}</p>
          </div>
        `).join("")}
      </div>
    ` : monitorBoard(5);
    return;
  }

  if (currentPanel === "relationships") {
    $("portalPrimaryTitle").textContent = "Candidate Relationships";
    $("portalPrimaryBody").innerHTML = candidates.length ? `
      <div class="stack-list">
        ${candidates.map(candidate => `
          <div class="list-card">
            <strong>${candidate.name} — ${candidate.title}</strong>
            <span>${candidate.client_company} • Fit ${candidate.fit_score}</span>
            <p>${candidate.experience} years experience.</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No candidate relationships yet.</div>`;
    $("portalSecondaryTitle").textContent = "Connection Mesh";
    $("portalSecondaryBody").innerHTML = networkConnectionsBoard();
    $("portalTertiaryTitle").textContent = "Avatar Coverage";
    $("portalTertiaryBody").innerHTML = avatarChipRow();
    $("portalQueueTitle").textContent = "Relationship Queue";
    $("portalQueueBody").innerHTML = domainBoard(6);
    return;
  }

  if (currentPanel === "packages") {
    $("portalPrimaryTitle").textContent = "Network Packages";
    $("portalPrimaryBody").innerHTML = `
      <div class="launch-form">
        <input id="portalObjectiveInput" placeholder="Optional objective, for example: map hiring signals across product-led startups">
        <div class="stack-list">
          ${(portalState.package_templates || []).map(template => `
            <div class="list-card">
              <strong>${template.title}</strong>
              <p>${template.summary}</p>
              <button class="launch-btn" onclick="launchPortalPackage('${template.id}')">Launch ${template.title}</button>
            </div>
          `).join("")}
        </div>
      </div>
      <div class="panel-note" id="portalPackageLog">Bounded packages let Network create safe missions without unsafe propagation.</div>
    `;
    $("portalSecondaryTitle").textContent = "Launched Packages";
    $("portalSecondaryBody").innerHTML = packages.length ? `
      <div class="stack-list">
        ${packages.map(pkg => `<div class="list-card"><strong>${pkg.title}</strong><p>${pkg.objective}</p></div>`).join("")}
      </div>
    ` : `<div class="empty-note">No packages launched yet.</div>`;
    $("portalTertiaryTitle").textContent = "Opportunity Lanes";
    $("portalTertiaryBody").innerHTML = latestHuntBoard(6);
    $("portalQueueTitle").textContent = "Package Queue";
    $("portalQueueBody").innerHTML = nervousBoard(6);
    return;
  }

  $("portalPrimaryTitle").textContent = "Activity Log";
  $("portalPrimaryBody").innerHTML = $("portalActivityBody").innerHTML;
  $("portalSecondaryTitle").textContent = "Network Posts";
  $("portalSecondaryBody").innerHTML = networkPostsBoard();
  $("portalTertiaryTitle").textContent = "Network Reports";
  $("portalTertiaryBody").innerHTML = reportBoard(6);
  $("portalQueueTitle").textContent = "Operations Queue";
  $("portalQueueBody").innerHTML = networkConnectionsBoard();
}

function renderAtsPanel() {
  const candidates = portalState.candidates || [];
  const jobs = portalState.jobs || [];
  const reports = portalState.reports || [];
  const atsSurface = portalState.ats_surface || {};

  if (currentPanel === "dashboard") {
    $("portalPrimaryTitle").textContent = "ATS Dashboard";
    $("portalPrimaryBody").innerHTML = `
      <div class="data-grid">
        <div class="data-card"><span>Candidates</span><strong>${candidates.length}</strong></div>
        <div class="data-card"><span>Jobs</span><strong>${jobs.length}</strong></div>
        <div class="data-card"><span>Reports</span><strong>${reports.length}</strong></div>
        <div class="data-card"><span>Hunts Today</span><strong>${portalState.dashboard.metrics.praapti_hunts_today}</strong></div>
      </div>
      <div class="panel-note">ATS now shares the same Leazy brain, so candidate and job views stay in sync with real hunts. The kanban board below is AI-scored directly from the shared state.</div>
      ${atsKanbanBoard()}
    `;
    $("portalSecondaryTitle").textContent = "Quick Operations";
    $("portalSecondaryBody").innerHTML = `
      <div class="action-grid">
        <button class="action-card panel-link" onclick="showPortalPanel('candidates')"><strong>Candidates</strong><p>Open live candidate list.</p></button>
        <button class="action-card panel-link" onclick="showPortalPanel('jobs')"><strong>Jobs</strong><p>Open the active jobs list.</p></button>
        <button class="action-card panel-link" onclick="showPortalPanel('resume-upload')"><strong>Resume Upload</strong><p>Open the intake workspace.</p></button>
        <button class="action-card panel-link" onclick="showPortalPanel('reports')"><strong>Reports</strong><p>Open hiring and swarm reports.</p></button>
        <button class="action-card panel-link" onclick="atsImportLatestHunt()"><strong>Praapti Import</strong><p>Pull the latest hunt into the ATS pipeline.</p></button>
      </div>
    `;
    $("portalTertiaryTitle").textContent = "AI Candidate Scoring";
    $("portalTertiaryBody").innerHTML = `
      <div class="ops-grid">
        <div class="ops-card"><span>Average Fit</span><strong>${atsSurface.score_summary?.average_fit || 0}</strong><p>Average AI candidate fit score across the current ATS pipeline.</p></div>
        <div class="ops-card"><span>Best Fit</span><strong>${atsSurface.score_summary?.best_fit || 0}</strong><p>Strongest candidate signal currently mapped from Praapti and the shared brain.</p></div>
      </div>
    `;
    $("portalQueueTitle").textContent = "Hiring Cabinet";
    $("portalQueueBody").innerHTML = cabinetBoard(4);
    return;
  }

  if (currentPanel === "candidates") {
    $("portalPrimaryTitle").textContent = "Candidates";
    $("portalPrimaryBody").innerHTML = atsKanbanBoard();
    $("portalSecondaryTitle").textContent = "Candidate Actions";
    $("portalSecondaryBody").innerHTML = `
      <div class="panel-note">Use Praapti hunts to populate this list, then use AI scoring to move candidates across sourced, screening, interview, and offer stages.</div>
    `;
    $("portalTertiaryTitle").textContent = "Open Roles";
    $("portalTertiaryBody").innerHTML = jobBoard(8);
    $("portalQueueTitle").textContent = "Shortlist Queue";
    $("portalQueueBody").innerHTML = monitorBoard(5);
    return;
  }

  if (currentPanel === "jobs") {
    $("portalPrimaryTitle").textContent = "Jobs";
    $("portalPrimaryBody").innerHTML = jobs.length ? `
      <div class="stack-list">
        ${jobs.map(job => `
          <div class="list-card">
            <strong>${job.client_company}</strong>
            <span>${job.urgency} • ${job.created_at}</span>
            <p>${job.summary}</p>
          </div>
        `).join("")}
      </div>
    ` : `<div class="empty-note">No jobs yet. Run a Praapti hunt to seed the ATS job board.</div>`;
    $("portalSecondaryTitle").textContent = "Navigation";
    $("portalSecondaryBody").innerHTML = quickActionGrid();
    $("portalTertiaryTitle").textContent = "Candidate Snapshot";
    $("portalTertiaryBody").innerHTML = `
      <div class="ops-grid">
        <div class="ops-card"><span>Candidate Count</span><strong>${atsSurface.score_summary?.candidate_count || 0}</strong><p>Total candidates currently staged in ATS.</p></div>
        <div class="ops-card"><span>Import Ready</span><strong>${atsSurface.import_ready ? "Yes" : "No"}</strong><p>Praapti can be imported directly into ATS whenever a live hunt exists.</p></div>
      </div>
    `;
    $("portalQueueTitle").textContent = "Job Queue";
    $("portalQueueBody").innerHTML = domainBoard(6);
    return;
  }

  if (currentPanel === "resume-upload") {
    $("portalPrimaryTitle").textContent = "Resume Upload";
    $("portalPrimaryBody").innerHTML = `
      <div class="resume-drop">
        <strong>Resume Intake</strong>
        <p>Select one or more files to stage local intake drafts in this browser. You can also import the latest Praapti hunt to seed the ATS board instantly.</p>
        <input type="file" id="resumeUploadInput" multiple accept=".pdf,.doc,.docx,.txt" onchange="captureResumeDrafts(event)">
        <div class="button-row" style="margin-top:12px">
          <button class="launch-btn" onclick="atsImportLatestHunt()">Import Latest Praapti Hunt</button>
        </div>
      </div>
      <div class="stack-list" style="margin-top:16px" id="resumeDraftList"></div>
    `;
    $("portalSecondaryTitle").textContent = "Usage";
    $("portalSecondaryBody").innerHTML = `
      <div class="panel-note">These resume drafts are stored locally in your browser for now. If you want, we can add server-side resume storage next.</div>
    `;
    $("portalTertiaryTitle").textContent = "Current Job Intake";
    $("portalTertiaryBody").innerHTML = jobBoard(6);
    $("portalQueueTitle").textContent = "Recruitment Queue";
    $("portalQueueBody").innerHTML = nervousBoard(6);
    renderResumeDrafts();
    return;
  }

  $("portalPrimaryTitle").textContent = "Reports";
  $("portalPrimaryBody").innerHTML = reports.length ? `
    <div class="stack-list">
      ${reports.map(report => `
        <div class="list-card">
          <strong>${report.title}</strong>
          <p>${report.summary}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty-note">No reports yet.</div>`;
  $("portalSecondaryTitle").textContent = "Activity";
  $("portalSecondaryBody").innerHTML = $("portalActivityBody").innerHTML;
  $("portalTertiaryTitle").textContent = "Candidates And Jobs";
  $("portalTertiaryBody").innerHTML = `
    <div class="ops-grid">
      <div class="ops-card"><span>Candidates</span><strong>${candidates.length}</strong><p>Profiles discovered from the latest hunts and network signals.</p></div>
      <div class="ops-card"><span>Jobs</span><strong>${jobs.length}</strong><p>Role demand currently reflected in the ATS workspace.</p></div>
    </div>
  `;
  $("portalQueueTitle").textContent = "Reporting Queue";
  $("portalQueueBody").innerHTML = monitorBoard(5);
}

function renderPortalContent() {
  renderMetricRow();
  renderBrainBody();
  renderActivityPreview();
  if (currentMode === "hq") {
    renderHqPanel();
    return;
  }
  if (currentMode === "hqowner") {
    renderOwnerHqPanel();
    return;
  }
  if (currentMode === "network") {
    renderNetworkPanel();
    return;
  }
  renderAtsPanel();
}

let portalEventSource = null;
let portalRefreshTimer = null;

function schedulePortalStreamRefresh() {
  clearTimeout(portalRefreshTimer);
  portalRefreshTimer = setTimeout(() => {
    refreshPortal().catch(error => console.error(error));
  }, 140);
}

function connectPortalStream() {
  if (!("EventSource" in window)) return;
  if (portalEventSource) {
    portalEventSource.close();
  }
  portalEventSource = new EventSource("/api/portal/stream");
  portalEventSource.addEventListener("snapshot", () => {
    schedulePortalStreamRefresh();
  });
  portalEventSource.onerror = () => {
    // polling remains as a fallback
  };
}

function renderResumeDrafts() {
  const container = $("resumeDraftList");
  if (!container) return;
  container.innerHTML = resumeDrafts.length ? resumeDrafts.map(item => `
    <div class="list-card">
      <strong>${item.name}</strong>
      <span>${item.size} KB • ${item.created_at}</span>
      <p>Staged locally for ATS intake.</p>
    </div>
  `).join("") : `<div class="empty-note">No resume files selected yet.</div>`;
}

function captureResumeDrafts(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;
  files.forEach(file => {
    resumeDrafts.unshift({
      name: file.name,
      size: Math.max(1, Math.round(file.size / 1024)),
      created_at: new Date().toLocaleString()
    });
  });
  resumeDrafts = resumeDrafts.slice(0, 20);
  saveResumeDrafts();
  renderResumeDrafts();
  toast("Resume drafts staged locally.");
}

async function launchPortalPackage(templateId) {
  const objectiveInput = $("portalObjectiveInput");
  const objective = objectiveInput ? objectiveInput.value.trim() : "";
  const data = await api("/api/packages/launch", {
    method: "POST",
    body: JSON.stringify({ template_id: templateId, objective })
  });
  const log = $("portalPackageLog");
  if (log) {
    log.textContent = `${data.message}\n\n${data.package?.report || "Mission ready."}`;
  }
  toast(data.message || "Package launched.");
  await refreshPortal();
}

async function refreshPortal() {
  portalState = await api("/api/portal/state");
  if (currentMode === "hq") {
    renderPublicHqStage();
  }
  renderPortalContent();
}

async function sendPortalGuide() {
  try {
    const input = $("portalGuideInput");
    const message = input.value.trim();
    if (!message) return;
    appendPortalGuideBubble("user", message);
    input.value = "";
    const data = await api("/api/leazy/chat", {
      method: "POST",
      body: JSON.stringify({ message, workspace: currentMode, source: "portal" })
    });
    appendPortalGuideBubble("ai", data.reply);
    await refreshPortal();
  } catch (error) {
    console.error(error);
    toast(error.message || "Workspace guide failed");
  }
}

async function boot() {
  loadResumeDrafts();
  loadPublicHqMessages();
  currentMode = resolveMode();
  renderTopShell();
  currentPanel = portalHashPanel();
  renderNav();
  $("portalGuideInput")?.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendPortalGuide();
    }
  });
  $("publicAiInput")?.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      sendPublicHqMessage("panel");
    }
  });
  $("hqAiPopupInput")?.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendPublicHqMessage("popup");
    }
  });
  appendPortalGuideBubble("ai", `Workspace guide is live for ${modeConfigs[currentMode].title}. Ask about dashboard status, hiring, reports, candidates, jobs, or next actions.`);
  await refreshPortal();
  connectPortalStream();
  setInterval(refreshPortal, 16000);
}

boot().catch(error => {
  console.error(error);
  toast(error.message || "Portal boot failed");
});
