const apiReq = (typeof api !== "undefined")
  ? api
  : async function(url, opts) {
      const response = await fetch(url, {
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        ...(opts || {}),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Auth");
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Error");
      return data;
    };

const showToast = (typeof showLeazyToast !== "undefined")
  ? showLeazyToast
  : (typeof toast !== "undefined")
    ? toast
    : function(message) {
        const el =
          document.getElementById("empToast") ||
          document.getElementById("toast") ||
          document.getElementById("portalToast");
        if (el) {
          el.textContent = message;
          el.style.display = "block";
          clearTimeout(el._t);
          el._t = setTimeout(() => {
            el.style.display = "none";
          }, 2800);
        } else {
          console.log("[Toast]", message);
        }
      };

const BRAIN_LAYER_ORDER = ["mother", "executive", "secretary", "domain", "machine", "tool", "atom"];
const BRAIN_LAYER_NAMES = {
  mother: "Mother Brain",
  executive: "Executive Brains",
  secretary: "Secretary Brains",
  domain: "Domain Brains",
  machine: "Machine Brains",
  tool: "Tool Brains",
  atom: "Atom Brains",
};
const BRAIN_LAYER_COLORS = {
  mother: "#f1ca6b",
  executive: "#87dfff",
  secretary: "#c1a1ff",
  domain: "#f39ddd",
  machine: "#7ce6d1",
  tool: "#9fb5ff",
  atom: "#95a5c3",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderBulletList(items, maxItems) {
  return (items || [])
    .slice(0, maxItems)
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function groupBrainsByLayer(brains) {
  return BRAIN_LAYER_ORDER
    .map(layer => ({ layer, brains: brains.filter(brain => brain.layer === layer) }))
    .filter(group => group.brains.length);
}

async function renderBrainHierarchy() {
  const container = document.getElementById("brainHierarchyWrap");
  if (!container) return;
  try {
    const data = await apiReq("/api/brain/hierarchy");
    const brains = Array.isArray(data.brains) ? data.brains : [];
    const summary = data.summary || {};
    const permissionRelays = Array.isArray(data.permission_relays) ? data.permission_relays : [];
    const motivationStreams = Array.isArray(data.motivation_streams) ? data.motivation_streams : [];
    const repairEngine = data.auto_repair || {};
    const groups = groupBrainsByLayer(brains);

    container.innerHTML = `
      <div class="bh-summary">
        <div class="bh-stat"><strong>${summary.total_brains || 0}</strong><span>Total Brains</span></div>
        <div class="bh-stat"><strong>${summary.layers || 0}</strong><span>Layers</span></div>
        <div class="bh-stat"><strong>${summary.alive || 0}</strong><span>Live</span></div>
        <div class="bh-stat"><strong>${summary.permission_relays || 0}</strong><span>Relays</span></div>
        <div class="bh-stat"><strong>${Number(summary.total_thoughts || 0).toLocaleString()}</strong><span>Thoughts</span></div>
        <div class="bh-stat"><strong>${((summary.avg_learning_score || 0) * 100).toFixed(1)}%</strong><span>Avg Learning</span></div>
        <div class="bh-stat"><strong>${summary.doctrine_modules || 0}</strong><span>Doctrine Packs</span></div>
        <div class="bh-stat"><strong>${summary.nlp_modules || 0}</strong><span>NLP Modules</span></div>
        <div class="bh-stat"><strong>${summary.auto_repair_brains || 0}</strong><span>Repair Ready</span></div>
        <div class="bh-stat"><strong>${summary.auto_repair_issues || 0}</strong><span>Repair Issues</span></div>
      </div>

      <div class="bh-tabs">
        <button class="bh-tab on" onclick="showBHTab('tree',this)">Brain Tree</button>
        <button class="bh-tab" onclick="showBHTab('relay',this)">Permission Relay</button>
        <button class="bh-tab" onclick="showBHTab('motivation',this)">Motivation</button>
        <button class="bh-tab" onclick="showBHTab('training',this)">Doctrine</button>
      </div>

      <div id="bh-tree" class="bh-content">
        ${groups.map(group => `
          <div class="bh-layer">
            <div class="bh-layer-head" style="color:${BRAIN_LAYER_COLORS[group.layer] || "#95a5c3"}">
              ${BRAIN_LAYER_NAMES[group.layer] || group.layer}
              <span class="bh-layer-count">${group.brains.length}</span>
            </div>
            <div class="bh-layer-cards">
              ${group.brains.map(brain => `
                <div class="bh-card" style="border-left-color:${BRAIN_LAYER_COLORS[group.layer] || "#95a5c3"}">
                  <div class="bh-card-head">
                    <span class="bh-emoji">${escapeHtml(brain.emoji || "🧩")}</span>
                    <div class="bh-card-info">
                      <div class="bh-card-name">${escapeHtml(brain.name)}</div>
                      <div class="bh-card-domain">${escapeHtml(brain.role_title || brain.identity || brain.layer)}</div>
                    </div>
                    <div class="bh-card-score">
                      <div class="bh-score-val" style="color:${Number(brain.load || 0) > 80 ? "#ff847d" : "#90f2d2"}">${Number(brain.load || 0)}%</div>
                      <div class="bh-score-lbl">load</div>
                    </div>
                  </div>
                  <div class="bh-card-thought">${escapeHtml(brain.last_thought || "Initializing...")}</div>
                  <div class="bh-card-task">${escapeHtml(brain.assigned_task || "Awaiting assignment.")}</div>
                  <div class="bh-card-meta">
                    <span>Status: ${escapeHtml(brain.status || "ready")}</span>
                    <span>Parent: ${escapeHtml(brain.parent_name || "none")}</span>
                    <span>Children: ${Number(brain.children_count || 0)}</span>
                    <span>Knowledge: ${Number(brain.knowledge_count || 0)}</span>
                  </div>
                  <div class="bh-card-meta">
                    <span>Thoughts: ${Number(brain.thoughts_processed || 0)}</span>
                    <span>Learning: ${((brain.learning_score || 0) * 100).toFixed(0)}%</span>
                    <span>${Number(brain.autonomous_cycle_sec || 0) > 0 ? `Cycle ${Number(brain.autonomous_cycle_sec)}s` : "Manual"}</span>
                  </div>
                  <div class="bh-card-meta">
                    <span>Mutation: ${escapeHtml(brain.mutation_state || "dormant")}</span>
                    <span>Skills: ${Number(brain.skill_count || 0)}</span>
                    <span>${brain.can_rewrite_descendants ? "Descendant rewrites unlocked" : "Rewrite lock active"}</span>
                  </div>
                  <div class="bh-card-meta">
                    <span>NLP: ${escapeHtml(brain.nlp_status || "embedded")}</span>
                    <span>Pipelines: ${Number(brain.nlp_modules || 0)}</span>
                    <span>Style: ${escapeHtml(brain.nlp_operator_style || "calm, human, precise, brief")}</span>
                  </div>
                  <div class="bh-card-meta">
                    <span>Auto Repair: ${escapeHtml(brain.auto_repair_status || "ready")}</span>
                    <span>Focus: ${escapeHtml((brain.auto_repair_focus || [])[0] || "system health")}</span>
                    <span>Last Check: ${escapeHtml(brain.last_self_check_at || "not yet")}</span>
                  </div>
                  <div style="margin-top:8px;color:var(--muted);font-size:12px">Identity: ${escapeHtml(brain.mutation_identity || brain.identity || brain.id)}</div>
                  <div style="margin-top:10px;color:var(--muted);font-size:12px">NLP Stack</div>
                  <ul style="margin:8px 0 0 18px;padding:0;color:var(--text);font-size:13px;line-height:1.5">
                    ${renderBulletList(brain.nlp_capabilities, 4)}
                  </ul>
                  <div style="margin-top:10px;color:var(--muted);font-size:12px">Auto Repair Focus</div>
                  <ul style="margin:8px 0 0 18px;padding:0;color:var(--text);font-size:13px;line-height:1.5">
                    ${renderBulletList(brain.auto_repair_focus, 3)}
                  </ul>
                  <div style="margin-top:10px;color:var(--muted);font-size:12px">Responsibilities</div>
                  <ul style="margin:8px 0 0 18px;padding:0;color:var(--text);font-size:13px;line-height:1.5">
                    ${renderBulletList(brain.responsibilities, 3)}
                  </ul>
                  <div style="margin-top:10px;color:var(--muted);font-size:12px">Growth Targets</div>
                  <ul style="margin:8px 0 0 18px;padding:0;color:var(--text);font-size:13px;line-height:1.5">
                    ${renderBulletList(brain.growth_targets, 2)}
                  </ul>
                  ${(group.layer === "mother" || group.layer === "executive" || group.layer === "secretary") ? `
                    <div class="bh-card-btns">
                      <button onclick="assignBrainTask('${brain.id}','${escapeHtml(brain.name)}')" class="bh-btn">Assign Task</button>
                      <button onclick="motivateBrain('${brain.id}')" class="bh-btn bh-btn-m">Motivate</button>
                      <button onclick="thinkBrain('${brain.id}')" class="bh-btn">Think Now</button>
                      <button onclick="runBrainAutoRepair('${brain.id}')" class="bh-btn">Self-Check</button>
                    </div>
                  ` : `
                    <div class="bh-card-btns">
                      <button onclick="runBrainAutoRepair('${brain.id}')" class="bh-btn">Self-Check</button>
                    </div>
                  `}
                </div>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </div>

      <div id="bh-relay" class="bh-content" style="display:none">
        <div class="bh-relay-header">Permission flows through ${summary.permission_relays || 0} live relay channels</div>
        <div class="bh-relay-list">
          ${permissionRelays.slice(0, 40).map(relay => {
            const toBrain = brains.find(brain => brain.id === relay.to);
            return `
              <div class="bh-relay-row" style="border-left-color:${BRAIN_LAYER_COLORS[(toBrain && toBrain.layer) || "tool"] || "#95a5c3"}">
                <div class="bh-relay-from">${escapeHtml(relay.from_name || relay.from)}</div>
                <div class="bh-relay-arrow">→</div>
                <div class="bh-relay-to">${escapeHtml(relay.to_name || relay.to)}</div>
                <div class="bh-relay-perms">${Array.isArray(relay.permission) ? relay.permission.join(", ") : escapeHtml(relay.permission || "relay")}</div>
              </div>
            `;
          }).join("")}
        </div>
      </div>

      <div id="bh-motivation" class="bh-content" style="display:none">
        <button onclick="motivateAll()" class="bh-motivate-all">Motivate All Brains</button>
        <div id="bhMotivateResult"></div>
        <div class="bh-motivation-grid">
          ${motivationStreams.map(stream => `
            <div class="bh-motivation-card">
              <div class="bh-m-name">${escapeHtml(stream.target || "Stream")}</div>
              <div class="bh-m-text">"${escapeHtml(stream.message || "")}"</div>
              <div style="margin-top:8px;color:var(--muted);font-size:12px">${escapeHtml(stream.source || "")} • ${escapeHtml(stream.focus || "")}</div>
            </div>
          `).join("")}
        </div>
      </div>

      <div id="bh-training" class="bh-content" style="display:none">
        <div class="bh-atom-note">Every brain now carries separate doctrine packs for role, operating rhythm, growth, and NLP. This is the live training map for the mother-brain hierarchy.</div>
        <div class="bh-atom-grid">
          ${brains.map(brain => `
            <div class="bh-atom-card">
              <div class="bh-atom-emoji">${escapeHtml(brain.emoji || "🧩")}</div>
              <div class="bh-atom-name">${escapeHtml(brain.name)}</div>
              <div class="bh-atom-domain">${escapeHtml(brain.role_title || brain.layer)}</div>
              <div class="bh-atom-task">${escapeHtml(brain.mission || brain.assigned_task || "")}</div>
              <div class="bh-atom-stat">Doctrine Modules: ${Number(brain.training_modules || 0)}</div>
              <div class="bh-atom-stat">NLP Modules: ${Number(brain.nlp_modules || 0)}</div>
              <div class="bh-atom-stat">Deliverables: ${Number((brain.deliverables || []).length)}</div>
              <div class="bh-atom-stat">Skills: ${Number(brain.skill_count || 0)}</div>
              <div class="bh-atom-stat">Mutation: ${escapeHtml(brain.mutation_state || "dormant")}</div>
              <div class="bh-atom-task">${escapeHtml(brain.nlp_summary || "")}</div>
            </div>
          `).join("")}
        </div>
      </div>

      <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
        <button onclick="renderBrainHierarchy()" style="padding:8px 14px;border-radius:999px;background:rgba(241,202,107,.1);border:1px solid rgba(241,202,107,.25);color:var(--gold);cursor:pointer;font-weight:700">Refresh</button>
        <button onclick="assignBrainTask('all','All Brains')" style="padding:8px 14px;border-radius:999px;background:rgba(135,223,255,.08);border:1px solid rgba(135,223,255,.2);color:var(--blue);cursor:pointer;font-weight:700">Mass Task Deploy</button>
        <button onclick="runBrainAutoRepair('all')" style="padding:8px 14px;border-radius:999px;background:rgba(144,242,210,.08);border:1px solid rgba(144,242,210,.25);color:var(--teal);cursor:pointer;font-weight:700">Run Safe Repair</button>
      </div>
      <div style="margin-top:12px;color:var(--muted);font-size:12px">Repair Engine: ${escapeHtml(repairEngine.status || "ready")} • ${Number(repairEngine.safe_repairs_applied || 0)} safe repairs applied • ${Number(repairEngine.issue_count || 0)} active issue(s).</div>
    `;
  } catch (error) {
    container.innerHTML = `<div style="color:var(--muted);padding:18px">Brain hierarchy loading... ${escapeHtml(error.message || "")}</div>`;
  }
}

function showBHTab(tab, btn) {
  ["tree", "relay", "motivation", "training"].forEach(name => {
    const el = document.getElementById(`bh-${name}`);
    if (el) el.style.display = name === tab ? "block" : "none";
  });
  document.querySelectorAll(".bh-tab").forEach(button => button.classList.remove("on"));
  if (btn) btn.classList.add("on");
}

async function assignBrainTask(brainId, brainName) {
  const task = prompt(`Assign task to ${brainName}:`, "Analyze your domain and report the top 3 actionable insights");
  if (!task) return;
  try {
    const data = await apiReq("/api/brain/assign-task", {
      method: "POST",
      body: JSON.stringify({ brain_id: brainId, task, context: "Operator assigned directly from hierarchy" }),
    });
    showToast((data.result || "Task assigned").slice(0, 120));
    renderBrainHierarchy();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  }
}

async function motivateBrain(brainId) {
  try {
    const data = await apiReq("/api/brain/motivate", {
      method: "POST",
      body: JSON.stringify({ brain_id: brainId }),
    });
    showToast((data?.results?.[0]?.message || "Motivated").slice(0, 120));
    renderBrainHierarchy();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  }
}

async function motivateAll() {
  const el = document.getElementById("bhMotivateResult");
  if (el) el.innerHTML = '<div style="color:var(--muted)">Motivating all brains...</div>';
  try {
    const data = await apiReq("/api/brain/motivate", {
      method: "POST",
      body: JSON.stringify({ brain_id: "all" }),
    });
    if (el) el.innerHTML = `<div style="color:var(--teal);padding:10px">OK ${data.motivated || 0} brains energized</div>`;
    showToast(`Motivated ${data.motivated || 0} brains`);
    renderBrainHierarchy();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  }
}

async function thinkBrain(brainId) {
  try {
    const data = await apiReq(`/api/brain/think/${brainId}`, {
      method: "POST",
      body: JSON.stringify({ context: "Manual think trigger from hierarchy console" }),
    });
    showToast(`${data.brain || "Brain"}: ${(data.thought || "").slice(0, 120)}`);
    renderBrainHierarchy();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  }
}

async function runBrainAutoRepair(brainId = "all") {
  try {
    const data = await apiReq("/api/brain/auto-repair/run", {
      method: "POST",
      body: JSON.stringify({ brain_id: brainId, include_state_repair: true, include_uiux_audit: true }),
    });
    showToast((data.result || "Safe repair completed").slice(0, 120));
    renderBrainHierarchy();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  }
}

let _brainHierarchyRefresh = null;
function startBHAutoRefresh() {
  if (_brainHierarchyRefresh) clearInterval(_brainHierarchyRefresh);
  _brainHierarchyRefresh = setInterval(() => {
    const wrap = document.getElementById("brainHierarchyWrap");
    if (wrap) renderBrainHierarchy();
  }, 30000);
}

startBHAutoRefresh();
