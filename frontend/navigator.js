const $ = id => document.getElementById(id);
let navigatorState = null;
let currentSiteId = "";

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    window.location.href = `/login?next=${encodeURIComponent("/navigator")}`;
    throw new Error("Login required. Redirecting to access.");
  }
  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed: ${response.status}`);
  }
  return data;
}

function escapeHtml(text) {
  return String(text || "").replace(/[&<>\"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[ch]));
}

function normalizeUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  if (raw.startsWith("/")) return raw;
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(raw)) return raw;
  return `https://${raw}`;
}

function findQuickSiteById(id) {
  return (navigatorState?.quick_sites || []).find(item => item.id === id) || null;
}

function findQuickSiteByUrl(url) {
  return (navigatorState?.quick_sites || []).find(item => normalizeUrl(item.url) === url) || null;
}

function isInternalWorkspaceUrl(url, site) {
  if (site?.embed_recommended) return true;
  try {
    const target = new URL(url, window.location.origin);
    return target.origin === window.location.origin;
  } catch (error) {
    return false;
  }
}

function setFrameStatus(message) {
  $("frameStatus").textContent = message;
}

function hideWorkspaceGuide() {
  $("workspaceGuide").hidden = true;
}

function showWorkspaceGuide(site, url, copy) {
  $("workspaceGuide").hidden = false;
  $("workspaceGuideTitle").textContent = `${site?.label || "External Site"} Workspace Guide`;
  $("workspaceGuideCopy").textContent =
    copy ||
    `${site?.label || "This site"} works best through the visible external handoff. Preserve only the approved learning you want the brain mesh to keep.`;
  $("workspaceGuidePath").textContent =
    site?.best_path === "workspace" ? "Internal Workspace Frame" : "Open External";
  $("workspaceGuideFocus").textContent =
    site?.learning_focus || "Capture only the role, candidate, or market signal that matters.";
  setFrameStatus(
    site?.best_path === "workspace"
      ? `Workspace frame ready for ${url}.`
      : `${site?.label || url} opened through the safer external path. Keep the learning capture panel here for approved notes only.`
  );
}

function renderQuickSites() {
  const rows = navigatorState?.quick_sites || [];
  $("quickSites").innerHTML = rows.map(site => `
    <button class="quick-site" onclick="chooseSite('${site.id}')">
      <strong>${escapeHtml(site.label)}</strong>
      <span>${escapeHtml(site.best_path === "workspace" ? "Best in workspace frame" : "Best in external browser")}</span>
      <span>${escapeHtml(site.learning_focus || site.workspace_tip || "")}</span>
    </button>
  `).join("");
}

function renderStats() {
  const learning = navigatorState?.learning || {};
  const stats = [
    ["Saved Captures", learning.captures_for_user ?? 0],
    ["Brain Lessons", learning.brain_lessons_total ?? 0],
    ["Mode", learning.mode || "operator_approved_only"],
  ];
  $("navigatorStats").innerHTML = stats.map(item => `
    <div class="stat"><strong>${escapeHtml(item[1])}</strong><span>${escapeHtml(item[0])}</span></div>
  `).join("");
}

function renderRecentSessions() {
  const rows = navigatorState?.recent_sessions || [];
  $("recentSessions").innerHTML = rows.length ? rows.map(item => `
    <div class="session">
      <strong>${escapeHtml(item.title)}</strong>
      <div class="meta">
        <span>${escapeHtml(item.mode || "learning")}</span>
        <span>${escapeHtml(item.created_at || "")}</span>
      </div>
      <div class="muted">${escapeHtml((item.notes || "").slice(0, 220) || item.target_url || "No notes captured.")}</div>
      <div class="chips">${(item.tags || []).map(tag => `<span class="chip">${escapeHtml(tag)}</span>`).join("")}</div>
    </div>
  `).join("") : `<div class="muted">No navigator captures yet. Open a site and save the exact learning you want the brain mesh to retain.</div>`;
}

function renderLauncher() {
  const launcher = navigatorState?.launcher || {};
  $("launcherStatus").textContent = launcher.message || "Launcher status unavailable.";
  $("openLauncherBtn").disabled = !launcher.available;
}

function renderHeadline() {
  $("navigatorHeadline").textContent = navigatorState?.headline || "Navigator status unavailable.";
}

function applyStatus() {
  renderQuickSites();
  renderStats();
  renderRecentSessions();
  renderLauncher();
  renderHeadline();
}

function seedCapture() {
  const site = findQuickSiteById(currentSiteId) || findQuickSiteByUrl(normalizeUrl($("navigatorUrl").value));
  $("captureTitle").value = site ? `${site.label} Research Session` : "Senior React Recruiter Market Signal";
  $("captureTags").value = site
    ? `${site.kind || "research"}, ${site.id}, approved_learning`
    : "market_signal, react, recruiter, delhi";
  $("captureNotes").value = site
    ? `Learning focus: ${site.learning_focus || site.workspace_tip || "Capture only the approved market or candidate signal."}\nObserved signal: `
    : "Observed a stronger response pattern for recruiter profiles that mention startup hiring, stakeholder management, and offer closure. Salary expectations appear tighter for Delhi NCR than Bangalore for the same experience range.";
}

function chooseSite(id) {
  const site = findQuickSiteById(id);
  if (!site) return;
  currentSiteId = site.id;
  $("navigatorUrl").value = site.url || "";
  $("captureTitle").value = `${site.label} Research Session`;
  $("captureTags").value = `${site.kind || "research"}, ${site.id}, approved_learning`;
  if (site.best_path === "workspace") {
    openEmbedded();
    return;
  }
  showWorkspaceGuide(
    site,
    site.url,
    `${site.label} usually blocks secure framing, so Navigator opens it in a normal browser tab and keeps this panel ready for operator-approved learning.`
  );
  openExternal({ auto: true });
}

function openEmbedded(force = false) {
  const url = normalizeUrl($("navigatorUrl").value);
  const site = findQuickSiteById(currentSiteId) || findQuickSiteByUrl(url);
  if (!url) {
    setFrameStatus("Enter a URL or choose a quick site first.");
    return;
  }
  $("navigatorUrl").value = url;
  if (!force && !isInternalWorkspaceUrl(url, site)) {
    showWorkspaceGuide(
      site,
      url,
      `${site?.label || "This site"} works better in a visible external browser window. Navigator will keep the learning workspace here so you can save only the exact sourcing, hiring, or market notes you approve.`
    );
    openExternal({ auto: true, silentGuide: true });
    return;
  }
  hideWorkspaceGuide();
  $("navigatorFrame").src = url;
  setFrameStatus(`Workspace opened ${url}. Internal TechBuzz pages work best here.`);
}

function forceEmbeddedOpen() {
  const url = normalizeUrl($("navigatorUrl").value);
  if (!url) {
    setFrameStatus("Choose a quick site or enter a URL first.");
    return;
  }
  $("navigatorFrame").src = url;
  showWorkspaceGuide(
    findQuickSiteById(currentSiteId) || findQuickSiteByUrl(url),
    url,
    "Frame attempt started. If the site blocks embedding, keep working through the external browser path and use this workspace only for approved learning capture."
  );
}

function openExternal(options = {}) {
  const url = normalizeUrl($("navigatorUrl").value);
  if (!url) {
    setFrameStatus("Enter a URL or choose a quick site first.");
    return;
  }
  $("navigatorUrl").value = url;
  window.open(url, "_blank", "noopener,noreferrer");
  if (!options.silentGuide) {
    setFrameStatus(`Opened ${url} in a normal browser tab. Use Save Learning when you want to preserve only the approved notes.`);
  }
}

async function saveCapture() {
  const title = $("captureTitle").value.trim();
  if (!title) {
    $("captureStatus").textContent = "Add a capture title first.";
    return;
  }
  const payload = {
    title,
    url: $("navigatorUrl").value.trim(),
    notes: $("captureNotes").value.trim(),
    mode: $("captureMode").value,
    tags: $("captureTags").value.split(",").map(item => item.trim()).filter(Boolean),
  };
  try {
    const data = await api("/api/navigator/capture", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("captureStatus").textContent = data.message || "Navigator learning saved.";
    navigatorState = data.status || navigatorState;
    applyStatus();
  } catch (error) {
    $("captureStatus").textContent = error.message || "Unable to save navigator learning.";
  }
}

async function openLocalLauncher() {
  try {
    const data = await api("/api/navigator/open-launcher", { method: "POST" });
    $("captureStatus").textContent = data.message || "Launcher opened.";
    navigatorState = data.status || navigatorState;
    applyStatus();
  } catch (error) {
    $("captureStatus").textContent = error.message || "Unable to open the launcher.";
  }
}

async function loadNavigator() {
  navigatorState = await api("/api/navigator/status");
  applyStatus();
}

loadNavigator().catch(error => {
  $("navigatorHeadline").textContent = error.message || "Unable to load navigator status.";
});
