/* Brain Contract Dashboard — brain-contracts.js
 * Adds a Contracts tab to the brain hierarchy panel.
 * Depends on apiReq, showToast, escapeHtml, BRAIN_LAYER_COLORS defined in brain-hierarchy.js
 */

(function () {
  // ------------------------------------------------------------------
  // Utility shims (safe if already defined by brain-hierarchy.js)
  // ------------------------------------------------------------------
  const _apiReq =
    typeof apiReq !== "undefined"
      ? apiReq
      : async function (url, opts) {
          const res = await fetch(url, {
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            ...(opts || {}),
          });
          if (res.status === 401) { window.location.href = "/login"; throw new Error("Auth"); }
          const d = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(d.detail || "Error");
          return d;
        };

  const _toast =
    typeof showToast !== "undefined"
      ? showToast
      : function (msg) { console.log("[Toast]", msg); };

  function _esc(v) {
    return String(v ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

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

  const _LAYER_ORDER = ["mother", "executive", "secretary", "domain", "machine", "tool", "atom"];
  const _DISCLOSURE_LABELS = { full: "Full", guided: "Guided", minimal: "Minimal" };
  const _DISCLOSURE_COLORS = { full: "#87dfff", guided: "#f1ca6b", minimal: "#95a5c3" };

  // ------------------------------------------------------------------
  // Health colour helper
  // ------------------------------------------------------------------
  function healthColor(score) {
    if (score >= 0.75) return "#7ce6d1";   // green
    if (score >= 0.45) return "#f1ca6b";   // yellow
    return "#ff8080";                       // red
  }

  function healthLabel(score) {
    if (score >= 0.75) return "Healthy";
    if (score >= 0.45) return "Degraded";
    return "Critical";
  }

  function healthBar(score) {
    const pct = Math.round(score * 100);
    const color = healthColor(score);
    return `<div style="background:rgba(255,255,255,0.06);border-radius:4px;height:6px;width:100%;margin-top:4px">
      <div style="background:${color};width:${pct}%;height:6px;border-radius:4px;transition:width .4s"></div>
    </div>`;
  }

  // ------------------------------------------------------------------
  // Render helpers
  // ------------------------------------------------------------------
  function renderTagList(items, color) {
    if (!Array.isArray(items) || items.length === 0) return '<span style="color:var(--muted,#888)">—</span>';
    return items
      .map(
        (t) =>
          `<span style="display:inline-block;padding:1px 7px;border-radius:99px;background:${color}22;border:1px solid ${color}44;color:${color};font-size:11px;margin:2px 2px 0 0">${_esc(t)}</span>`
      )
      .join("");
  }

  function renderContractCard(contract, health) {
    const layer = contract.layer || "tool";
    const color = _LAYER_COLORS[layer] || "#9fb5ff";
    const hs = health ? health.health_score : null;
    const ls = health ? health.learning_score : null;
    const hColor = hs !== null ? healthColor(hs) : "#95a5c3";
    const dlColor = _DISCLOSURE_COLORS[contract.disclosure_level] || "#95a5c3";
    const dlLabel = _DISCLOSURE_LABELS[contract.disclosure_level] || contract.disclosure_level || "guided";

    return `
      <div class="bc-card" data-brain-id="${_esc(contract.brain_id)}" style="
        background: rgba(255,255,255,0.03);
        border: 1px solid ${color}44;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
      ">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
          <div>
            <span style="font-weight:700;color:${color};font-size:14px">${_esc(contract.name || contract.brain_id)}</span>
            <span style="margin-left:8px;font-size:11px;color:var(--muted,#888);background:${color}18;border:1px solid ${color}33;border-radius:99px;padding:1px 8px">${_esc(layer)}</span>
            <span style="margin-left:6px;font-size:11px;color:${dlColor};background:${dlColor}18;border:1px solid ${dlColor}33;border-radius:99px;padding:1px 8px">🔓 ${_esc(dlLabel)}</span>
          </div>
          ${hs !== null ? `<div style="text-align:right;min-width:80px">
            <div style="font-size:11px;color:${hColor};font-weight:700">${healthLabel(hs)} ${Math.round(hs * 100)}%</div>
            ${healthBar(hs)}
          </div>` : ""}
        </div>

        <div style="margin-top:8px;font-size:12px;color:var(--muted,#888)"><strong style="color:var(--text,#ddd)">Role:</strong> ${_esc(contract.role)}</div>
        <div style="margin-top:4px;font-size:12px;color:var(--muted,#888)"><strong style="color:var(--text,#ddd)">Mission:</strong> ${_esc(contract.mission)}</div>

        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin-top:10px">
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--muted,#888);margin-bottom:3px">Allowed Events</div>
            ${renderTagList(contract.allowed_events, "#87dfff")}
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--muted,#888);margin-bottom:3px">Allowed Tools</div>
            ${renderTagList(contract.allowed_tools, "#f1ca6b")}
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--muted,#888);margin-bottom:3px">Memory Namespaces</div>
            ${renderTagList(contract.allowed_memory_namespaces, "#c1a1ff")}
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--muted,#888);margin-bottom:3px">Can Create Tasks</div>
            ${renderTagList(contract.task_types_can_create, "#7ce6d1")}
          </div>
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--muted,#888);margin-bottom:3px">Can Resolve Tasks</div>
            ${renderTagList(contract.task_types_can_resolve, "#9fb5ff")}
          </div>
          ${
            Array.isArray(contract.learning_targets) && contract.learning_targets.length
              ? `<div>
              <div style="font-size:11px;font-weight:700;color:var(--muted,#888);margin-bottom:3px">Learning Targets</div>
              ${renderTagList(contract.learning_targets, "#f39ddd")}
            </div>`
              : ""
          }
        </div>

        ${contract.evolution_scope ? `<div style="margin-top:8px;font-size:11px;color:var(--muted,#888);border-top:1px solid rgba(255,255,255,0.05);padding-top:6px">⚡ <em>${_esc(contract.evolution_scope)}</em></div>` : ""}

        ${
          health
            ? `<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;font-size:11px;color:var(--muted,#888);border-top:1px solid rgba(255,255,255,0.05);padding-top:6px">
          <span>📋 Created <strong style="color:var(--text,#ddd)">${health.tasks_created}</strong></span>
          <span>✅ Resolved <strong style="color:var(--text,#ddd)">${health.tasks_resolved}</strong></span>
          <span>👍 Approved <strong style="color:var(--text,#ddd)">${health.actions_approved}</strong></span>
          <span>🚫 Rejected <strong style="color:var(--text,#ddd)">${health.actions_rejected}</strong></span>
          <span>⚠️ Conflicts <strong style="color:var(--text,#ddd)">${health.conflicts_generated}</strong></span>
          <span>🎓 Learning <strong style="color:${hColor}">${Math.round((ls || 0) * 100)}%</strong></span>
        </div>`
            : ""
        }
      </div>`;
  }

  function renderViolationRow(v) {
    const actionColors = {
      event: "#87dfff",
      task_create: "#7ce6d1",
      task_resolve: "#9fb5ff",
      tool: "#f1ca6b",
    };
    const color = actionColors[v.action_type] || "#95a5c3";
    return `
      <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:baseline;padding:7px 10px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px">
        <span style="color:${color};font-weight:700;min-width:88px">${_esc(v.action_type)}</span>
        <span style="color:var(--muted,#888);min-width:160px">${_esc(v.brain_id)}</span>
        <span style="flex:1;color:var(--text,#ddd)">${_esc(v.action_detail)}</span>
        <span style="color:#ff8080;font-size:11px">${_esc(v.blocked_reason)}</span>
        <span style="color:var(--muted,#888);font-size:10px;white-space:nowrap">${_esc(v.created_at)}</span>
      </div>`;
  }

  // ------------------------------------------------------------------
  // Main render function
  // ------------------------------------------------------------------
  async function renderBrainContracts() {
    const container = document.getElementById("bcContractsWrap");
    const violationsContainer = document.getElementById("bcViolationsWrap");
    if (!container && !violationsContainer) return;

    // Fetch contracts and health in parallel
    let contractsData = { contracts: [] };
    let healthData = { health: [] };
    let violationsData = { violations: [] };

    try {
      [contractsData, healthData, violationsData] = await Promise.all([
        _apiReq("/api/brain/contracts"),
        _apiReq("/api/brain/health"),
        _apiReq("/api/brain/contracts/violations?limit=30"),
      ]);
    } catch (err) {
      if (container) container.innerHTML = `<div style="color:var(--muted,#888);padding:18px">Failed to load contracts: ${_esc(err.message || "")}</div>`;
      return;
    }

    const contracts = Array.isArray(contractsData.contracts) ? contractsData.contracts : [];
    const healthMap = {};
    (Array.isArray(healthData.health) ? healthData.health : []).forEach((h) => {
      healthMap[h.brain_id] = h;
    });
    const violations = Array.isArray(violationsData.violations) ? violationsData.violations : [];

    if (container) {
      // Group contracts by layer
      const grouped = {};
      _LAYER_ORDER.forEach((l) => { grouped[l] = []; });
      contracts.forEach((c) => {
        const l = c.layer || "tool";
        if (!grouped[l]) grouped[l] = [];
        grouped[l].push(c);
      });

      let html = `
        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px">
          <div style="font-size:13px;color:var(--muted,#888)">${contracts.length} brain contracts</div>
          <button onclick="renderBrainContracts()" style="padding:5px 14px;border-radius:999px;background:rgba(135,223,255,.08);border:1px solid rgba(135,223,255,.2);color:#87dfff;cursor:pointer;font-size:12px">↻ Refresh</button>
        </div>`;

      _LAYER_ORDER.forEach((layer) => {
        const group = grouped[layer] || [];
        if (!group.length) return;
        const color = _LAYER_COLORS[layer] || "#9fb5ff";
        html += `<div style="margin-bottom:6px;font-size:12px;font-weight:700;color:${color};letter-spacing:.04em;text-transform:uppercase">${_esc(layer)} Layer (${group.length})</div>`;
        group.forEach((c) => {
          html += renderContractCard(c, healthMap[c.brain_id] || null);
        });
      });

      container.innerHTML = html;
    }

    if (violationsContainer) {
      if (!violations.length) {
        violationsContainer.innerHTML = '<div style="color:var(--muted,#888);padding:12px;font-size:13px">No violations recorded.</div>';
      } else {
        violationsContainer.innerHTML = `
          <div style="font-size:12px;color:var(--muted,#888);margin-bottom:8px">${violations.length} recent violation(s)</div>
          <div style="background:rgba(255,0,0,0.04);border:1px solid rgba(255,128,128,0.15);border-radius:8px;overflow:hidden">
            ${violations.map(renderViolationRow).join("")}
          </div>`;
      }
    }
  }

  // ------------------------------------------------------------------
  // Tab injection — injects a "Contracts" tab into the brain hierarchy
  // panel when it is rendered (or immediately if it already exists).
  // ------------------------------------------------------------------
  function injectContractsTab() {
    // Try to find the tab bar used in brain-hierarchy.js
    const tabBar = document.querySelector(".bh-tabs");
    if (!tabBar) return false;

    // Avoid double injection
    if (document.getElementById("bh-contracts-tab")) return true;

    // Add the tab button
    const btn = document.createElement("button");
    btn.id = "bh-contracts-tab";
    btn.className = "bh-tab";
    btn.textContent = "Contracts";
    btn.onclick = function () {
      showBCTab("contracts", btn);
    };
    tabBar.appendChild(btn);

    // Find the panel container (parent of one of the existing bh-* panels)
    const treePanel = document.getElementById("bh-tree");
    const panelParent = treePanel ? treePanel.parentNode : null;
    if (!panelParent) return false;

    // Add contracts panel
    const contractsSection = document.createElement("div");
    contractsSection.id = "bh-contracts";
    contractsSection.style.display = "none";
    contractsSection.innerHTML = `
      <div style="margin-bottom:12px">
        <div style="font-size:13px;font-weight:700;color:var(--text,#ddd);margin-bottom:8px">Brain Contract Dashboard</div>
        <div id="bcContractsWrap" style="max-height:580px;overflow-y:auto;padding-right:4px">
          <div style="color:var(--muted,#888);padding:14px">Loading contracts…</div>
        </div>
      </div>
      <div style="margin-top:18px">
        <div style="font-size:13px;font-weight:700;color:#ff8080;margin-bottom:8px">⚠️ Contract Violations Log</div>
        <div id="bcViolationsWrap">
          <div style="color:var(--muted,#888);padding:14px">Loading violations…</div>
        </div>
      </div>`;
    panelParent.appendChild(contractsSection);
    return true;
  }

  function showBCTab(tab, btn) {
    ["tree", "relay", "motivation", "training", "contracts"].forEach(function (name) {
      const el = document.getElementById("bh-" + name);
      if (el) el.style.display = name === tab ? "block" : "none";
    });
    document.querySelectorAll(".bh-tab").forEach(function (b) { b.classList.remove("on"); });
    if (btn) btn.classList.add("on");

    if (tab === "contracts") {
      renderBrainContracts();
    }
  }

  // Expose globally for onclick and external callers
  window.renderBrainContracts = renderBrainContracts;
  window.showBCTab = showBCTab;

  // ------------------------------------------------------------------
  // Observe DOM for brain hierarchy panel becoming available
  // ------------------------------------------------------------------
  function tryInject() {
    if (injectContractsTab()) return;
    // Panel not yet rendered — wait for it
    const observer = new MutationObserver(function () {
      if (injectContractsTab()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryInject);
  } else {
    tryInject();
  }
})();
