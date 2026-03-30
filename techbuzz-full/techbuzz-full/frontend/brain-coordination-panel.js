/**
 * brain-coordination-panel.js
 * Coordination dashboard panel for the Independent Brain Execution system.
 *
 * Shows: recent events • pending tasks • aggregation results
 *        action drafts awaiting approval • safety log / blocked items
 *
 * Uses the same apiReq / showToast patterns as brain-hierarchy.js.
 */

/* global apiReq, showToast */

"use strict";

// ---------------------------------------------------------------------------
// API helpers — fall back gracefully if the host page's helpers are missing
// ---------------------------------------------------------------------------

const _bcpApi = (typeof apiReq !== "undefined")
  ? apiReq
  : async function (url, opts) {
      const res = await fetch(url, {
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        ...(opts || {}),
      });
      if (res.status === 401) { window.location.href = "/login"; throw new Error("Auth"); }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Error");
      return data;
    };

const _bcpToast = (typeof showToast !== "undefined")
  ? showToast
  : (msg) => console.log("[BCP Toast]", msg);

// ---------------------------------------------------------------------------
// Panel state
// ---------------------------------------------------------------------------

const BrainCoordPanel = {
  _pollHandle: null,
  _pollInterval: 15000,          // 15 seconds
  _mountId: "brain-coord-panel", // default mount element id

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  /** Mount the panel into *container* (HTMLElement or element id string). */
  mount(container) {
    const el = (typeof container === "string")
      ? document.getElementById(container)
      : container;
    if (!el) { console.warn("[BCP] mount target not found:", container); return; }

    el.innerHTML = BrainCoordPanel._buildSkeleton();
    BrainCoordPanel._attachStyles();
    BrainCoordPanel.refresh();
    BrainCoordPanel._pollHandle = setInterval(BrainCoordPanel.refresh, BrainCoordPanel._pollInterval);
  },

  unmount() {
    if (BrainCoordPanel._pollHandle) {
      clearInterval(BrainCoordPanel._pollHandle);
      BrainCoordPanel._pollHandle = null;
    }
  },

  async refresh() {
    await Promise.allSettled([
      BrainCoordPanel._loadEvents(),
      BrainCoordPanel._loadTasks(),
      BrainCoordPanel._loadAggregation(),
      BrainCoordPanel._loadActions(),
      BrainCoordPanel._loadSafety(),
    ]);
  },

  // -----------------------------------------------------------------------
  // Sections
  // -----------------------------------------------------------------------

  async _loadEvents() {
    try {
      const data = await _bcpApi("/api/events/log?limit=20");
      const container = document.getElementById("bcp-events-list");
      if (!container) return;
      if (!data.events || data.events.length === 0) {
        container.innerHTML = "<p class='bcp-empty'>No events yet.</p>";
        return;
      }
      container.innerHTML = data.events.map(e => `
        <div class="bcp-card">
          <span class="bcp-badge bcp-badge-blue">${_esc(e.event_type)}</span>
          <span class="bcp-meta">source: ${_esc(e.source_brain)} &nbsp;|&nbsp; ${_esc(e.created_at)}</span>
          <span class="bcp-meta">subscribers: ${e.subscriber_count}</span>
          <pre class="bcp-json">${_esc(JSON.stringify(e.payload, null, 2))}</pre>
        </div>
      `).join("");
    } catch (err) {
      console.error("[BCP] events error:", err);
    }
  },

  async _loadTasks() {
    try {
      const data = await _bcpApi("/api/tasks?status=pending&limit=50");
      const container = document.getElementById("bcp-tasks-list");
      if (!container) return;
      if (!data.tasks || data.tasks.length === 0) {
        container.innerHTML = "<p class='bcp-empty'>No pending tasks.</p>";
        return;
      }
      container.innerHTML = data.tasks.map(t => `
        <div class="bcp-card">
          <span class="bcp-badge bcp-badge-yellow">${_esc(t.task_type)}</span>
          <span class="bcp-meta">brain: ${_esc(t.brain_id)} &nbsp;|&nbsp; priority: ${t.priority} &nbsp;|&nbsp; ${_esc(t.created_at)}</span>
          <p class="bcp-msg">${_esc(t.output_data && t.output_data.message ? t.output_data.message : JSON.stringify(t.output_data))}</p>
          <div class="bcp-actions">
            <button class="bcp-btn bcp-btn-green" onclick="BrainCoordPanel.approveTask('${_esc(t.id)}')">Approve</button>
            <button class="bcp-btn bcp-btn-red"   onclick="BrainCoordPanel.rejectTask('${_esc(t.id)}')">Reject</button>
          </div>
        </div>
      `).join("");
    } catch (err) {
      console.error("[BCP] tasks error:", err);
    }
  },

  async _loadAggregation() {
    try {
      // We auto-run aggregation each refresh so results are current
      await _bcpApi("/api/aggregator/auto", { method: "POST", body: JSON.stringify({}) });

      // Fetch recent aggregation results by querying tasks that have been aggregated
      const data = await _bcpApi("/api/tasks?status=aggregated&limit=20");
      const container = document.getElementById("bcp-aggregation-list");
      if (!container) return;
      if (!data.tasks || data.tasks.length === 0) {
        container.innerHTML = "<p class='bcp-empty'>No aggregated results yet.</p>";
        return;
      }
      container.innerHTML = data.tasks.map(t => `
        <div class="bcp-card">
          <span class="bcp-badge bcp-badge-purple">${_esc(t.task_type)}</span>
          <span class="bcp-meta">brain: ${_esc(t.brain_id)} &nbsp;|&nbsp; ${_esc(t.created_at)}</span>
          <p class="bcp-msg">${_esc(t.output_data && t.output_data.merged_message ? t.output_data.merged_message : (t.output_data && t.output_data.message ? t.output_data.message : JSON.stringify(t.output_data)))}</p>
        </div>
      `).join("");
    } catch (err) {
      console.error("[BCP] aggregation error:", err);
    }
  },

  async _loadActions() {
    try {
      const data = await _bcpApi("/api/actions?status=draft&limit=30");
      const container = document.getElementById("bcp-actions-list");
      if (!container) return;
      if (!data.actions || data.actions.length === 0) {
        container.innerHTML = "<p class='bcp-empty'>No action drafts awaiting approval.</p>";
        return;
      }
      container.innerHTML = data.actions.map(a => `
        <div class="bcp-card">
          <span class="bcp-badge bcp-badge-orange">${_esc(a.action_type)}</span>
          <span class="bcp-meta">task: ${_esc(a.task_id)} &nbsp;|&nbsp; ${_esc(a.created_at)}</span>
          <p class="bcp-msg">${_esc(a.content && a.content.message ? a.content.message : JSON.stringify(a.content))}</p>
          <div class="bcp-actions">
            <button class="bcp-btn bcp-btn-green" onclick="BrainCoordPanel.executeAction('${_esc(a.id)}')">Execute</button>
            <button class="bcp-btn bcp-btn-gray"  onclick="BrainCoordPanel.dismissAction('${_esc(a.id)}')">Dismiss</button>
          </div>
        </div>
      `).join("");
    } catch (err) {
      console.error("[BCP] actions error:", err);
    }
  },

  async _loadSafety() {
    try {
      const [logData, blockedData] = await Promise.all([
        _bcpApi("/api/safety/log?limit=10"),
        _bcpApi("/api/safety/blocked"),
      ]);
      const container = document.getElementById("bcp-safety-list");
      if (!container) return;

      let html = "";
      if (blockedData.blocked && blockedData.blocked.length > 0) {
        html += "<h4 class='bcp-subheading'>Blocked</h4>";
        html += blockedData.blocked.map(b => `
          <div class="bcp-card bcp-card-danger">
            <span class="bcp-badge bcp-badge-red">BLOCKED</span>
            <span class="bcp-meta">action: ${_esc(b.action_id)} &nbsp;|&nbsp; ${_esc(b.created_at)}</span>
            <p class="bcp-msg">${_esc(b.reason)}</p>
            <button class="bcp-btn bcp-btn-yellow" onclick="BrainCoordPanel.overrideSafety('${_esc(b.action_id)}')">Override</button>
          </div>
        `).join("");
      }

      if (logData.log && logData.log.length > 0) {
        html += "<h4 class='bcp-subheading'>Recent checks</h4>";
        html += logData.log.map(l => `
          <div class="bcp-card ${l.result === 'blocked' ? 'bcp-card-danger' : ''}">
            <span class="bcp-badge ${l.result === 'passed' ? 'bcp-badge-green' : 'bcp-badge-red'}">${_esc(l.result)}</span>
            <span class="bcp-meta">${_esc(l.check_type)} &nbsp;|&nbsp; action: ${_esc(l.action_id)} &nbsp;|&nbsp; ${_esc(l.created_at)}</span>
            ${l.reason ? `<p class="bcp-msg">${_esc(l.reason)}</p>` : ""}
          </div>
        `).join("");
      }

      container.innerHTML = html || "<p class='bcp-empty'>No safety events.</p>";
    } catch (err) {
      console.error("[BCP] safety error:", err);
    }
  },

  // -----------------------------------------------------------------------
  // Button handlers
  // -----------------------------------------------------------------------

  async approveTask(taskId) {
    try {
      await _bcpApi(`/api/tasks/${taskId}/approve`, { method: "POST", body: JSON.stringify({}) });
      _bcpToast("Task approved ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async rejectTask(taskId) {
    try {
      await _bcpApi(`/api/tasks/${taskId}/reject`, { method: "POST", body: JSON.stringify({}) });
      _bcpToast("Task rejected");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async executeAction(actionId) {
    try {
      await _bcpApi(`/api/actions/${actionId}/execute`, { method: "POST", body: JSON.stringify({}) });
      _bcpToast("Action executed ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async dismissAction(actionId) {
    try {
      await _bcpApi(`/api/actions/${actionId}/dismiss`, { method: "POST", body: JSON.stringify({}) });
      _bcpToast("Action dismissed");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async overrideSafety(actionId) {
    const reason = prompt("Override reason (master only):", "Manual master override");
    if (reason === null) return;
    try {
      await _bcpApi(`/api/safety/override/${actionId}`, { method: "POST", body: JSON.stringify({ reason }) });
      _bcpToast("Safety block overridden ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async publishEvent(eventType, sourceBrain, payload) {
    try {
      await _bcpApi("/api/events/publish", {
        method: "POST",
        body: JSON.stringify({ event_type: eventType, source_brain: sourceBrain, payload }),
      });
      _bcpToast(`Event '${eventType}' published`);
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  // -----------------------------------------------------------------------
  // HTML skeleton
  // -----------------------------------------------------------------------

  _buildSkeleton() {
    return `
      <div class="bcp-panel">
        <div class="bcp-header">
          <h2>🧠 Brain Coordination Dashboard</h2>
          <button class="bcp-btn bcp-btn-blue" onclick="BrainCoordPanel.refresh()">⟳ Refresh</button>
        </div>

        <div class="bcp-grid">
          <section class="bcp-section">
            <h3>📡 Recent Events</h3>
            <div id="bcp-events-list"><p class="bcp-empty">Loading…</p></div>
          </section>

          <section class="bcp-section">
            <h3>📋 Pending Tasks</h3>
            <div id="bcp-tasks-list"><p class="bcp-empty">Loading…</p></div>
          </section>

          <section class="bcp-section">
            <h3>🔀 Aggregation Results</h3>
            <div id="bcp-aggregation-list"><p class="bcp-empty">Loading…</p></div>
          </section>

          <section class="bcp-section">
            <h3>⚡ Action Drafts</h3>
            <div id="bcp-actions-list"><p class="bcp-empty">Loading…</p></div>
          </section>

          <section class="bcp-section bcp-section-wide">
            <h3>🛡 Safety Log</h3>
            <div id="bcp-safety-list"><p class="bcp-empty">Loading…</p></div>
          </section>
        </div>
      </div>
    `;
  },

  // -----------------------------------------------------------------------
  // Scoped styles (injected once)
  // -----------------------------------------------------------------------

  _stylesInjected: false,

  _attachStyles() {
    if (BrainCoordPanel._stylesInjected) return;
    BrainCoordPanel._stylesInjected = true;
    const style = document.createElement("style");
    style.textContent = `
      .bcp-panel { font-family: inherit; color: #e2e8f0; }
      .bcp-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
      .bcp-header h2 { margin: 0; font-size: 1.2rem; }
      .bcp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
      .bcp-section { background: #1e293b; border-radius: 8px; padding: 12px; }
      .bcp-section h3 { margin: 0 0 10px; font-size: 0.95rem; border-bottom: 1px solid #334155; padding-bottom: 6px; }
      .bcp-section-wide { grid-column: 1 / -1; }
      .bcp-subheading { margin: 10px 0 4px; font-size: 0.8rem; color: #94a3b8; }
      .bcp-card { background: #0f172a; border-radius: 6px; padding: 8px 10px; margin-bottom: 8px; }
      .bcp-card-danger { border-left: 3px solid #ef4444; }
      .bcp-badge { font-size: 0.7rem; font-weight: 700; padding: 2px 6px; border-radius: 99px; margin-right: 6px; }
      .bcp-badge-blue   { background: #1d4ed8; color: #fff; }
      .bcp-badge-yellow { background: #b45309; color: #fff; }
      .bcp-badge-purple { background: #7c3aed; color: #fff; }
      .bcp-badge-orange { background: #c2410c; color: #fff; }
      .bcp-badge-green  { background: #166534; color: #fff; }
      .bcp-badge-red    { background: #991b1b; color: #fff; }
      .bcp-meta { font-size: 0.7rem; color: #64748b; display: block; margin: 2px 0; }
      .bcp-msg  { font-size: 0.8rem; margin: 4px 0; }
      .bcp-json { font-size: 0.65rem; white-space: pre-wrap; word-break: break-all; color: #94a3b8; margin: 4px 0 0; max-height: 80px; overflow: auto; }
      .bcp-empty { color: #475569; font-size: 0.8rem; }
      .bcp-actions { display: flex; gap: 6px; margin-top: 6px; }
      .bcp-btn { font-size: 0.75rem; padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; }
      .bcp-btn-blue   { background: #2563eb; color: #fff; }
      .bcp-btn-green  { background: #16a34a; color: #fff; }
      .bcp-btn-red    { background: #dc2626; color: #fff; }
      .bcp-btn-gray   { background: #475569; color: #fff; }
      .bcp-btn-yellow { background: #d97706; color: #fff; }
    `;
    document.head.appendChild(style);
  },
};

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function _esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Auto-mount if a container element with the default id exists in DOM
document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById(BrainCoordPanel._mountId);
  if (el) BrainCoordPanel.mount(el);
});

// Export for module environments
if (typeof module !== "undefined" && module.exports) {
  module.exports = BrainCoordPanel;
}
