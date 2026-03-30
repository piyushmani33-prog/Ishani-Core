/* brain-messages.js — Inter-Brain Communication & Handoff Protocol UI
 * Injects a "Messages" tab into the Brain Hierarchy panel.
 */

(function () {
  "use strict";

  // ── Shared helpers (mirrors brain-hierarchy.js) ───────────────────────────

  const _apiReq =
    typeof apiReq !== "undefined"
      ? apiReq
      : async function (url, opts) {
          const res = await fetch(url, {
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            ...(opts || {}),
          });
          if (res.status === 401) {
            window.location.href = "/login";
            throw new Error("Auth");
          }
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(data.detail || "Error");
          return data;
        };

  const _toast =
    typeof showToast !== "undefined"
      ? showToast
      : typeof showLeazyToast !== "undefined"
      ? showLeazyToast
      : function (msg) {
          console.log("[BrainMessages]", msg);
        };

  const _esc =
    typeof escapeHtml !== "undefined"
      ? escapeHtml
      : function (v) {
          return String(v ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
        };

  const _LAYER_COLORS =
    typeof BRAIN_LAYER_COLORS !== "undefined"
      ? BRAIN_LAYER_COLORS
      : {
          mother: "#f1ca6b",
          executive: "#87dfff",
          secretary: "#c1a1ff",
          domain: "#f39ddd",
          machine: "#7ce6d1",
          tool: "#9fb5ff",
          atom: "#95a5c3",
        };

  // ── Message-type badge colours ────────────────────────────────────────────

  const MSG_TYPE_COLORS = {
    request_help: "#4a90e2",
    handoff_task: "#e67e22",
    escalate: "#e74c3c",
    attach_evidence: "#27ae60",
    request_decision: "#8e44ad",
    return_result: "#16a085",
    broadcast_signal: "#f1c40f",
  };

  const MSG_TYPE_LABELS = {
    request_help: "Help",
    handoff_task: "Handoff",
    escalate: "Escalate",
    attach_evidence: "Evidence",
    request_decision: "Decision",
    return_result: "Result",
    broadcast_signal: "Broadcast",
  };

  const PRIORITY_COLORS = {
    critical: "#e74c3c",
    high: "#e67e22",
    normal: "#3498db",
    low: "#95a5a6",
  };

  // ── CSS injection ─────────────────────────────────────────────────────────

  function injectStyles() {
    if (document.getElementById("bm-styles")) return;
    const style = document.createElement("style");
    style.id = "bm-styles";
    style.textContent = `
      #bmPanel { padding: 12px 0; }
      .bm-tabs { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
      .bm-tab {
        padding: 5px 14px; border-radius: 20px; cursor: pointer;
        background: #1e2535; color: #8a9ab5; border: 1px solid #2a3347; font-size: 12px;
        transition: all .2s;
      }
      .bm-tab.active { background: #2d3f66; color: #fff; border-color: #4a6aa0; }
      .bm-tab-pane { display: none; }
      .bm-tab-pane.active { display: block; }
      .bm-filter-row { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; align-items: center; }
      .bm-filter-row select, .bm-filter-row input {
        background: #1e2535; border: 1px solid #2a3347; color: #c8d3e8;
        border-radius: 6px; padding: 4px 8px; font-size: 12px;
      }
      .bm-btn {
        padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;
        background: #2d3f66; color: #fff; border: none; transition: background .2s;
      }
      .bm-btn:hover { background: #3a5080; }
      .bm-card {
        background: #161c2b; border: 1px solid #2a3347; border-radius: 8px;
        margin-bottom: 8px; padding: 10px 12px;
      }
      .bm-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 4px; }
      .bm-badge {
        display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;
      }
      .bm-priority { font-size: 11px; font-weight: 600; }
      .bm-arrow { color: #4a6aa0; margin: 0 4px; }
      .bm-brain { font-weight: 600; font-size: 12px; }
      .bm-status { font-size: 11px; color: #8a9ab5; }
      .bm-ts { font-size: 11px; color: #5a6a85; }
      .bm-stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-bottom: 12px; }
      .bm-stat-box { background: #1e2535; border: 1px solid #2a3347; border-radius: 8px; padding: 10px; text-align: center; }
      .bm-stat-box strong { display: block; font-size: 20px; color: #87dfff; }
      .bm-stat-box span { font-size: 11px; color: #8a9ab5; }
      .bm-section-title { font-size: 12px; color: #8a9ab5; margin: 10px 0 6px; text-transform: uppercase; letter-spacing: .05em; }
      .bm-violation { border-left: 3px solid #e74c3c; }
      .bm-type-row { display: flex; justify-content: space-between; align-items: center;
        padding: 4px 0; border-bottom: 1px solid #1e2535; font-size: 12px; }
      .bm-empty { color: #5a6a85; font-size: 13px; text-align: center; padding: 24px 0; }
      .bm-payload { font-size: 11px; color: #7a8a9f; background: #1a2033; border-radius: 4px;
        padding: 4px 8px; margin-top: 4px; word-break: break-all; white-space: pre-wrap; max-height: 80px; overflow: auto; }
    `;
    document.head.appendChild(style);
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  function msgTypeBadge(type) {
    const color = MSG_TYPE_COLORS[type] || "#666";
    const label = MSG_TYPE_LABELS[type] || type;
    return `<span class="bm-badge" style="background:${color}22;color:${color};border:1px solid ${color}55">${_esc(label)}</span>`;
  }

  function priorityBadge(priority) {
    const color = PRIORITY_COLORS[priority] || "#666";
    return `<span class="bm-priority" style="color:${color}">▲ ${_esc(priority)}</span>`;
  }

  function statusColor(status) {
    const map = {
      pending: "#e67e22",
      in_progress: "#3498db",
      resolved: "#27ae60",
      completed: "#27ae60",
      failed: "#e74c3c",
      rejected: "#c0392b",
    };
    return map[status] || "#8a9ab5";
  }

  function relTime(iso) {
    if (!iso) return "";
    try {
      const diff = Date.now() - new Date(iso).getTime();
      if (diff < 60000) return "just now";
      if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
      if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
      return Math.floor(diff / 86400000) + "d ago";
    } catch {
      return iso;
    }
  }

  function renderMessageCard(m) {
    const payloadStr =
      m.payload && typeof m.payload === "object" && Object.keys(m.payload).length
        ? JSON.stringify(m.payload, null, 2)
        : "";
    return `
      <div class="bm-card">
        <div class="bm-card-head">
          <span>
            ${msgTypeBadge(m.message_type)}
            ${priorityBadge(m.priority)}
          </span>
          <span class="bm-ts">${_esc(relTime(m.created_at))}</span>
        </div>
        <div style="font-size:12px;margin-bottom:4px">
          <span class="bm-brain">${_esc(m.from_brain_name || m.from_brain)}</span>
          <span class="bm-arrow">→</span>
          <span class="bm-brain">${_esc(m.to_brain_name || m.to_brain)}</span>
        </div>
        <div style="display:flex;gap:12px;align-items:center">
          <span class="bm-status" style="color:${statusColor(m.status)}">${_esc(m.status)}</span>
          ${m.task_id ? `<span class="bm-ts">task: ${_esc(m.task_id)}</span>` : ""}
        </div>
        ${payloadStr ? `<div class="bm-payload">${_esc(payloadStr)}</div>` : ""}
      </div>`;
  }

  // ── Tab: Feed ─────────────────────────────────────────────────────────────

  async function loadFeed(container) {
    const statusFilter = container.querySelector("#bmFeedStatus")?.value || "";
    const typeFilter = container.querySelector("#bmFeedType")?.value || "";
    const list = container.querySelector("#bmFeedList");
    if (!list) return;
    list.innerHTML = '<div class="bm-empty">Loading…</div>';

    const params = new URLSearchParams({ limit: 50 });
    if (statusFilter) params.set("status", statusFilter);
    if (typeFilter) params.set("message_type", typeFilter);

    try {
      const data = await _apiReq(`/api/brain/messages?${params}`);
      const messages = data.messages || [];
      if (!messages.length) {
        list.innerHTML = '<div class="bm-empty">No messages found</div>';
        return;
      }
      list.innerHTML = messages.map(renderMessageCard).join("");
    } catch (e) {
      list.innerHTML = `<div class="bm-empty">Error: ${_esc(e.message)}</div>`;
    }
  }

  function buildFeedPane() {
    const div = document.createElement("div");
    div.id = "bmPaneFeed";
    div.className = "bm-tab-pane";
    div.innerHTML = `
      <div class="bm-filter-row">
        <select id="bmFeedStatus">
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select id="bmFeedType">
          <option value="">All types</option>
          <option value="request_help">request_help</option>
          <option value="handoff_task">handoff_task</option>
          <option value="escalate">escalate</option>
          <option value="attach_evidence">attach_evidence</option>
          <option value="request_decision">request_decision</option>
          <option value="return_result">return_result</option>
          <option value="broadcast_signal">broadcast_signal</option>
        </select>
        <button class="bm-btn" id="bmFeedRefresh">Refresh</button>
      </div>
      <div id="bmFeedList"><div class="bm-empty">Loading…</div></div>`;
    return div;
  }

  // ── Tab: Handoffs ─────────────────────────────────────────────────────────

  async function loadHandoffs(container) {
    const list = container.querySelector("#bmHandoffList");
    if (!list) return;
    list.innerHTML = '<div class="bm-empty">Loading…</div>';
    try {
      const data = await _apiReq("/api/brain/messages/handoffs?limit=30");
      const messages = data.messages || [];
      if (!messages.length) {
        list.innerHTML = '<div class="bm-empty">No handoffs yet</div>';
        return;
      }
      list.innerHTML = messages.map(renderMessageCard).join("");
    } catch (e) {
      list.innerHTML = `<div class="bm-empty">Error: ${_esc(e.message)}</div>`;
    }
  }

  function buildHandoffsPane() {
    const div = document.createElement("div");
    div.id = "bmPaneHandoffs";
    div.className = "bm-tab-pane";
    div.innerHTML = `
      <div class="bm-filter-row">
        <button class="bm-btn" id="bmHandoffRefresh">Refresh</button>
      </div>
      <div id="bmHandoffList"><div class="bm-empty">Loading…</div></div>`;
    return div;
  }

  // ── Tab: Escalations ──────────────────────────────────────────────────────

  async function loadEscalations(container) {
    const list = container.querySelector("#bmEscList");
    if (!list) return;
    list.innerHTML = '<div class="bm-empty">Loading…</div>';
    try {
      const data = await _apiReq("/api/brain/messages/escalations?limit=30");
      const messages = data.messages || [];
      if (!messages.length) {
        list.innerHTML = '<div class="bm-empty">No escalations yet</div>';
        return;
      }
      list.innerHTML = messages.map(renderMessageCard).join("");
    } catch (e) {
      list.innerHTML = `<div class="bm-empty">Error: ${_esc(e.message)}</div>`;
    }
  }

  function buildEscalationsPane() {
    const div = document.createElement("div");
    div.id = "bmPaneEsc";
    div.className = "bm-tab-pane";
    div.innerHTML = `
      <div class="bm-filter-row">
        <button class="bm-btn" id="bmEscRefresh">Refresh</button>
      </div>
      <div id="bmEscList"><div class="bm-empty">Loading…</div></div>`;
    return div;
  }

  // ── Tab: Stats ────────────────────────────────────────────────────────────

  async function loadStats(container) {
    const root = container.querySelector("#bmStatsRoot");
    if (!root) return;
    root.innerHTML = '<div class="bm-empty">Loading…</div>';
    try {
      const d = await _apiReq("/api/brain/messages/stats");
      const byType = d.by_type || {};
      const byBrain = d.by_brain || {};

      const typeRows = Object.entries(byType)
        .sort((a, b) => b[1] - a[1])
        .map(
          ([t, c]) =>
            `<div class="bm-type-row">
              ${msgTypeBadge(t)}
              <span style="color:#c8d3e8;font-weight:600">${c}</span>
            </div>`
        )
        .join("") || '<div class="bm-empty">No data</div>';

      const brainRows = Object.entries(byBrain)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(
          ([b, c]) =>
            `<div class="bm-type-row">
              <span style="color:#c8d3e8">${_esc(b)}</span>
              <span style="color:#87dfff;font-weight:600">${c}</span>
            </div>`
        )
        .join("") || '<div class="bm-empty">No data</div>';

      root.innerHTML = `
        <div class="bm-stats-grid">
          <div class="bm-stat-box"><strong>${d.total || 0}</strong><span>Total</span></div>
          <div class="bm-stat-box"><strong>${d.pending || 0}</strong><span>Pending</span></div>
          <div class="bm-stat-box"><strong>${d.resolved || 0}</strong><span>Resolved</span></div>
          <div class="bm-stat-box"><strong>${d.violations || 0}</strong><span>Violations</span></div>
        </div>
        <div class="bm-section-title">By Message Type</div>
        <div>${typeRows}</div>
        <div class="bm-section-title" style="margin-top:12px">Top Senders</div>
        <div>${brainRows}</div>`;
    } catch (e) {
      root.innerHTML = `<div class="bm-empty">Error: ${_esc(e.message)}</div>`;
    }
  }

  function buildStatsPane() {
    const div = document.createElement("div");
    div.id = "bmPaneStats";
    div.className = "bm-tab-pane";
    div.innerHTML = `
      <div class="bm-filter-row">
        <button class="bm-btn" id="bmStatsRefresh">Refresh</button>
      </div>
      <div id="bmStatsRoot"><div class="bm-empty">Loading…</div></div>`;
    return div;
  }

  // ── Tab: Violations ───────────────────────────────────────────────────────

  async function loadViolations(container) {
    const list = container.querySelector("#bmViolList");
    if (!list) return;
    list.innerHTML = '<div class="bm-empty">Loading…</div>';
    try {
      const data = await _apiReq("/api/brain/messages/violations?limit=40");
      const violations = data.violations || [];
      if (!violations.length) {
        list.innerHTML = '<div class="bm-empty">No violations — all contracts respected ✓</div>';
        return;
      }
      list.innerHTML = violations
        .map(
          (v) => `
          <div class="bm-card bm-violation">
            <div class="bm-card-head">
              <span>${msgTypeBadge(v.message_type)}</span>
              <span class="bm-ts">${_esc(relTime(v.created_at))}</span>
            </div>
            <div style="font-size:12px;margin-bottom:4px">
              <span class="bm-brain">${_esc(v.from_brain_name || v.from_brain)}</span>
              <span class="bm-arrow">→</span>
              <span class="bm-brain">${_esc(v.to_brain_name || v.to_brain)}</span>
            </div>
            <div style="font-size:12px;color:#e74c3c">${_esc(v.violation_reason || v.reason || "")}</div>
          </div>`
        )
        .join("");
    } catch (e) {
      list.innerHTML = `<div class="bm-empty">Error: ${_esc(e.message)}</div>`;
    }
  }

  function buildViolationsPane() {
    const div = document.createElement("div");
    div.id = "bmPaneViol";
    div.className = "bm-tab-pane";
    div.innerHTML = `
      <div class="bm-filter-row">
        <button class="bm-btn" id="bmViolRefresh">Refresh</button>
      </div>
      <div id="bmViolList"><div class="bm-empty">Loading…</div></div>`;
    return div;
  }

  // ── Main panel builder ────────────────────────────────────────────────────

  function buildPanel() {
    const panel = document.createElement("div");
    panel.id = "bmPanel";

    const tabs = document.createElement("div");
    tabs.className = "bm-tabs";
    const tabDefs = [
      { id: "feed", label: "📨 Feed" },
      { id: "handoffs", label: "🔄 Handoffs" },
      { id: "escalations", label: "🚨 Escalations" },
      { id: "stats", label: "📊 Stats" },
      { id: "violations", label: "⚠️ Violations" },
    ];
    tabDefs.forEach(({ id, label }) => {
      const btn = document.createElement("button");
      btn.className = "bm-tab";
      btn.dataset.bmTab = id;
      btn.textContent = label;
      tabs.appendChild(btn);
    });
    panel.appendChild(tabs);

    const feedPane = buildFeedPane();
    const handoffsPane = buildHandoffsPane();
    const escPane = buildEscalationsPane();
    const statsPane = buildStatsPane();
    const violPane = buildViolationsPane();

    panel.appendChild(feedPane);
    panel.appendChild(handoffsPane);
    panel.appendChild(escPane);
    panel.appendChild(statsPane);
    panel.appendChild(violPane);

    // Tab switching
    function switchTab(id) {
      tabs.querySelectorAll(".bm-tab").forEach((b) => b.classList.remove("active"));
      panel.querySelectorAll(".bm-tab-pane").forEach((p) => p.classList.remove("active"));
      const btn = tabs.querySelector(`[data-bm-tab="${id}"]`);
      if (btn) btn.classList.add("active");
      const paneMap = {
        feed: feedPane,
        handoffs: handoffsPane,
        escalations: escPane,
        stats: statsPane,
        violations: violPane,
      };
      if (paneMap[id]) {
        paneMap[id].classList.add("active");
        // Lazy-load on first show
        if (id === "feed") loadFeed(feedPane);
        else if (id === "handoffs") loadHandoffs(handoffsPane);
        else if (id === "escalations") loadEscalations(escPane);
        else if (id === "stats") loadStats(statsPane);
        else if (id === "violations") loadViolations(violPane);
      }
    }

    tabs.addEventListener("click", (e) => {
      const tab = e.target.closest("[data-bm-tab]");
      if (tab) switchTab(tab.dataset.bmTab);
    });

    // Wire refresh buttons
    feedPane.querySelector("#bmFeedRefresh").addEventListener("click", () => loadFeed(feedPane));
    feedPane.querySelector("#bmFeedStatus").addEventListener("change", () => loadFeed(feedPane));
    feedPane.querySelector("#bmFeedType").addEventListener("change", () => loadFeed(feedPane));
    handoffsPane.querySelector("#bmHandoffRefresh").addEventListener("click", () => loadHandoffs(handoffsPane));
    escPane.querySelector("#bmEscRefresh").addEventListener("click", () => loadEscalations(escPane));
    statsPane.querySelector("#bmStatsRefresh").addEventListener("click", () => loadStats(statsPane));
    violPane.querySelector("#bmViolRefresh").addEventListener("click", () => loadViolations(violPane));

    // Default active tab
    switchTab("feed");

    return panel;
  }

  // ── Injection ─────────────────────────────────────────────────────────────

  function injectMessagesSection() {
    if (document.getElementById("bmPanel")) return; // already injected

    // Try to inject into the brain hierarchy wrapper
    const targets = [
      document.getElementById("brainHierarchyWrap"),
      document.querySelector(".brain-hierarchy-section"),
      document.querySelector("[data-section='brain-hierarchy']"),
      document.querySelector(".proposal-list"),
    ];

    let host = null;
    for (const t of targets) {
      if (t) {
        host = t;
        break;
      }
    }

    if (!host) return; // not rendered yet

    injectStyles();

    // Create a wrapper section
    const wrapper = document.createElement("div");
    wrapper.style.cssText =
      "margin-top:20px;background:#111824;border:1px solid #2a3347;border-radius:10px;padding:14px 16px;";

    const heading = document.createElement("div");
    heading.style.cssText =
      "font-size:13px;font-weight:700;color:#87dfff;margin-bottom:10px;letter-spacing:.04em;";
    heading.textContent = "🧠 Inter-Brain Messages";
    wrapper.appendChild(heading);
    wrapper.appendChild(buildPanel());

    host.appendChild(wrapper);
  }

  // ── Observe DOM for the brain hierarchy panel ─────────────────────────────

  function tryInject() {
    injectMessagesSection();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryInject);
  } else {
    tryInject();
  }

  const _observer = new MutationObserver(() => {
    if (!document.getElementById("bmPanel")) tryInject();
  });
  _observer.observe(document.body, { childList: true, subtree: true });
})();
