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
    BrainCoordPanel._attachDelegation(el);
    BrainCoordPanel.refresh();
    BrainCoordPanel._pollHandle = setInterval(BrainCoordPanel.refresh, BrainCoordPanel._pollInterval);
  },

  /** Event delegation — handles all data-action buttons to avoid XSS-prone inline handlers. */
  _attachDelegation(rootEl) {
    rootEl.addEventListener("click", async (evt) => {
      const btn = evt.target.closest("[data-action]");
      if (!btn) return;
      const action = btn.dataset.action;
      const id = btn.dataset.id || "";
      switch (action) {
        case "approve-task":   await BrainCoordPanel.approveTask(id); break;
        case "reject-task":    await BrainCoordPanel.rejectTask(id); break;
        case "execute-action": await BrainCoordPanel.executeAction(id); break;
        case "dismiss-action": await BrainCoordPanel.dismissAction(id); break;
        case "override-safety": await BrainCoordPanel.overrideSafety(id); break;
        case "accept-insight":  await BrainCoordPanel.acceptInsight(id); break;
        case "reject-insight":  await BrainCoordPanel.rejectInsight(id); break;
        case "accept-proposal": await BrainCoordPanel.acceptProposal(id); break;
        case "reject-proposal": await BrainCoordPanel.rejectProposal(id); break;
        case "trigger-followup": await BrainCoordPanel.triggerFollowUp(); break;
        case "trigger-ack":      await BrainCoordPanel.triggerAck(); break;
        case "trigger-status":   await BrainCoordPanel.triggerStatus(); break;
        case "autopilot-approve": await BrainCoordPanel.autopilotAction(btn.dataset.runId, id, "approve"); break;
        case "autopilot-reject":  await BrainCoordPanel.autopilotAction(btn.dataset.runId, id, "reject"); break;
        case "autopilot-copy":    await BrainCoordPanel.autopilotAction(btn.dataset.runId, id, "copy"); break;
        case "refresh": await BrainCoordPanel.refresh(); break;
        default: break;
      }
    });
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
      BrainCoordPanel._loadLearning(),
      BrainCoordPanel._loadEvolution(),
      BrainCoordPanel._loadAutopilot(),
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
            <button class="bcp-btn bcp-btn-green" data-action="approve-task" data-id="${_esc(t.id)}">Approve</button>
            <button class="bcp-btn bcp-btn-red"   data-action="reject-task"  data-id="${_esc(t.id)}">Reject</button>
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
            <button class="bcp-btn bcp-btn-green" data-action="execute-action" data-id="${_esc(a.id)}">Execute</button>
            <button class="bcp-btn bcp-btn-gray"  data-action="dismiss-action" data-id="${_esc(a.id)}">Dismiss</button>
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
            <button class="bcp-btn bcp-btn-yellow" data-action="override-safety" data-id="${_esc(b.action_id)}">Override</button>
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

  async _loadLearning() {
    try {
      const [statsData, signalsData, insightsData] = await Promise.all([
        _bcpApi("/api/learning/stats"),
        _bcpApi("/api/learning/signals?limit=10"),
        _bcpApi("/api/learning/insights?status=proposed&limit=10"),
      ]);
      const container = document.getElementById("bcp-learning-list");
      if (!container) return;
      let html = "";

      if (statsData.stats) {
        const s = statsData.stats;
        html += `<div class="bcp-card"><span class="bcp-meta">Signals: ${s.total_signals} &nbsp;|&nbsp; Insights: ${s.total_insights}</span></div>`;
      }

      if (insightsData.insights && insightsData.insights.length > 0) {
        html += "<h4 class='bcp-subheading'>Proposed Insights</h4>";
        html += insightsData.insights.map(i => `
          <div class="bcp-card">
            <span class="bcp-badge bcp-badge-purple">${_esc(i.category)}</span>
            <span class="bcp-meta">brain: ${_esc(i.source_brain)} &nbsp;|&nbsp; ${_esc(i.created_at)}</span>
            <p class="bcp-msg">${_esc(i.summary)}</p>
            <div class="bcp-actions">
              <button class="bcp-btn bcp-btn-green" data-action="accept-insight" data-id="${_esc(i.id)}">Accept</button>
              <button class="bcp-btn bcp-btn-red"   data-action="reject-insight" data-id="${_esc(i.id)}">Reject</button>
            </div>
          </div>
        `).join("");
      }

      if (signalsData.signals && signalsData.signals.length > 0) {
        html += "<h4 class='bcp-subheading'>Recent Signals</h4>";
        html += signalsData.signals.map(s => `
          <div class="bcp-card">
            <span class="bcp-badge bcp-badge-blue">${_esc(s.signal_type)}</span>
            <span class="bcp-meta">${_esc(s.entity_type)}/${_esc(s.entity_id)} &nbsp;|&nbsp; ${_esc(s.created_at)}</span>
          </div>
        `).join("");
      }

      container.innerHTML = html || "<p class='bcp-empty'>No learning data yet.</p>";
    } catch (err) {
      console.error("[BCP] learning error:", err);
    }
  },

  async _loadEvolution() {
    try {
      const data = await _bcpApi("/api/evolution/proposals?status=proposed&limit=10");
      const container = document.getElementById("bcp-evolution-list");
      if (!container) return;
      if (!data.proposals || data.proposals.length === 0) {
        container.innerHTML = "<p class='bcp-empty'>No pending evolution proposals.</p>";
        return;
      }
      container.innerHTML = data.proposals.map(p => `
        <div class="bcp-card">
          <span class="bcp-badge bcp-badge-orange">${_esc(p.category)}</span>
          <span class="bcp-meta">brain: ${_esc(p.source_brain)} &nbsp;|&nbsp; priority: ${p.priority} &nbsp;|&nbsp; ${_esc(p.created_at)}</span>
          <p class="bcp-msg"><strong>${_esc(p.title)}</strong></p>
          <p class="bcp-msg">${_esc(p.description)}</p>
          <div class="bcp-actions">
            <button class="bcp-btn bcp-btn-green" data-action="accept-proposal" data-id="${_esc(p.id)}">Accept</button>
            <button class="bcp-btn bcp-btn-red"   data-action="reject-proposal" data-id="${_esc(p.id)}">Reject</button>
          </div>
        </div>
      `).join("");
    } catch (err) {
      console.error("[BCP] evolution error:", err);
    }
  },

  async _loadAutopilot() {
    try {
      const data = await _bcpApi("/api/recruitment/autopilot/runs?limit=10");
      const container = document.getElementById("bcp-autopilot-list");
      if (!container) return;
      if (!data.runs || data.runs.length === 0) {
        container.innerHTML = "<p class='bcp-empty'>No autopilot runs yet. Use the buttons above to trigger a workflow.</p>";
        return;
      }
      let html = "";
      for (const run of data.runs) {
        const workflowBadge = {
          follow_up: "bcp-badge-yellow",
          acknowledgment: "bcp-badge-blue",
          daily_status: "bcp-badge-purple",
        }[run.workflow] || "bcp-badge-blue";

        const statusBadge = run.status === "completed" ? "bcp-badge-green"
          : run.status === "awaiting_approval" ? "bcp-badge-orange"
          : "bcp-badge-gray";

        html += `<div class="bcp-card">
          <span class="bcp-badge ${workflowBadge}">${_esc(run.workflow)}</span>
          <span class="bcp-badge ${statusBadge}">${_esc(run.status)}</span>
          <span class="bcp-meta">event: ${_esc(run.event_id)} &nbsp;|&nbsp; ${_esc(run.created_at)}</span>`;

        // Show action IDs with approve/reject buttons for pending runs
        const actionIds = (run.summary && run.summary.action_ids) || [];
        if (run.status === "awaiting_approval" && actionIds.length > 0) {
          for (const aid of actionIds) {
            html += `<div class="bcp-actions" style="margin-top:4px;">
              <span class="bcp-meta" style="flex:1">${_esc(aid)}</span>
              <button class="bcp-btn bcp-btn-green" data-action="autopilot-approve" data-id="${_esc(aid)}" data-run-id="${_esc(run.id)}">✓ Approve</button>
              <button class="bcp-btn bcp-btn-red"   data-action="autopilot-reject"  data-id="${_esc(aid)}" data-run-id="${_esc(run.id)}">✗ Reject</button>
              <button class="bcp-btn bcp-btn-blue"  data-action="autopilot-copy"    data-id="${_esc(aid)}" data-run-id="${_esc(run.id)}">📋 Copy</button>
            </div>`;
          }
        }
        html += `</div>`;
      }
      container.innerHTML = html;
    } catch (err) {
      console.error("[BCP] autopilot error:", err);
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
    // Use confirm() for a simpler, non-blocking-prompt approach.
    // This avoids multi-step modal infrastructure while remaining explicit.
    if (!confirm(`Override safety block for action "${actionId}"?\n\nThis is a master-only operation. Confirm to proceed.`)) return;
    const reason = "Manual master override";
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

  async acceptInsight(insightId) {
    try {
      await _bcpApi(`/api/learning/insights/${insightId}/accept`, { method: "POST", body: JSON.stringify({}) });
      _bcpToast("Insight accepted ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async rejectInsight(insightId) {
    try {
      await _bcpApi(`/api/learning/insights/${insightId}/reject`, { method: "POST", body: JSON.stringify({}) });
      _bcpToast("Insight rejected");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async acceptProposal(proposalId) {
    try {
      await _bcpApi(`/api/evolution/proposals/${proposalId}/review`, {
        method: "POST",
        body: JSON.stringify({ decision: "accepted", review_notes: "Approved from dashboard" }),
      });
      _bcpToast("Proposal accepted ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async rejectProposal(proposalId) {
    try {
      await _bcpApi(`/api/evolution/proposals/${proposalId}/review`, {
        method: "POST",
        body: JSON.stringify({ decision: "rejected", review_notes: "Rejected from dashboard" }),
      });
      _bcpToast("Proposal rejected");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async triggerFollowUp() {
    const name = prompt("Candidate name for follow-up:", "");
    if (!name) return;
    const position = prompt("Position:", "Open Role");
    try {
      await _bcpApi("/api/recruitment/autopilot/follow-up", {
        method: "POST",
        body: JSON.stringify({ candidate_name: name, position: position || "" }),
      });
      _bcpToast("Follow-up loop triggered ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async triggerAck() {
    const name = prompt("Candidate name for acknowledgment:", "");
    if (!name) return;
    const position = prompt("Position:", "Open Role");
    try {
      await _bcpApi("/api/recruitment/autopilot/acknowledgment", {
        method: "POST",
        body: JSON.stringify({ candidate_name: name, position: position || "" }),
      });
      _bcpToast("Acknowledgment loop triggered ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async triggerStatus() {
    try {
      await _bcpApi("/api/recruitment/autopilot/status", {
        method: "POST",
        body: JSON.stringify({ scope: "daily", format: "both" }),
      });
      _bcpToast("Status loop triggered ✓");
      BrainCoordPanel.refresh();
    } catch (err) { _bcpToast("Error: " + err.message); }
  },

  async autopilotAction(runId, actionId, action) {
    try {
      await _bcpApi(`/api/recruitment/autopilot/runs/${runId}/actions/${actionId}`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      const pastTense = { approve: "approved", reject: "rejected", copy: "copied", edit: "edited" }[action] || action;
      _bcpToast(`Action ${pastTense} ✓`);
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
          <button class="bcp-btn bcp-btn-blue" data-action="refresh">⟳ Refresh</button>
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

          <section class="bcp-section">
            <h3>📚 Learning Engine</h3>
            <div id="bcp-learning-list"><p class="bcp-empty">Loading…</p></div>
          </section>

          <section class="bcp-section">
            <h3>🧬 Evolution Proposals</h3>
            <div id="bcp-evolution-list"><p class="bcp-empty">Loading…</p></div>
          </section>

          <section class="bcp-section bcp-section-wide">
            <h3>🚀 Recruitment Autopilot</h3>
            <div class="bcp-actions" style="margin-bottom:8px;">
              <button class="bcp-btn bcp-btn-yellow" data-action="trigger-followup">📩 Follow-Up Loop</button>
              <button class="bcp-btn bcp-btn-blue"   data-action="trigger-ack">✉️ Acknowledgment Loop</button>
              <button class="bcp-btn bcp-btn-green"  data-action="trigger-status">📊 Daily Status Loop</button>
            </div>
            <div id="bcp-autopilot-list"><p class="bcp-empty">Loading…</p></div>
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
