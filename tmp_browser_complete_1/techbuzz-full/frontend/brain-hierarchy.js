// ── Universal API shim — works in both leazy.js and agent.js contexts ──────────
const apiReq = (typeof api !== 'undefined') ? api : async function(url,opts){
  const r=await fetch(url,{credentials:'include',headers:{'Content-Type':'application/json'},...(opts||{})});
  if(r.status===401){window.location.href='/login';throw new Error('Auth');}
  const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Error');return d;
};
const showToast = (typeof showLeazyToast!=='undefined')?showLeazyToast:(typeof toast!=='undefined')?toast:function(m){
  let el=document.getElementById('empToast')||document.getElementById('toast')||document.getElementById('portalToast');
  if(el){el.textContent=m;el.style.display='block';clearTimeout(el._t);el._t=setTimeout(()=>el.style.display='none',2800);}
  else console.log('[Toast]',m);
};

// ═══════════════════════════════════════════════════════════════════════════════
//  BRAIN HIERARCHY — Living brain tree with permission relay and motivation
//  Injected into Leazy Jinn
// ═══════════════════════════════════════════════════════════════════════════════

const LAYER_NAMES = {0:"Mother Brain",1:"Executive Brains",2:"Secretary Brains",3:"Tool Brains",4:"Domain Brains",5:"Machine Brains",6:"Atom Brains"};
const LAYER_COLORS = {0:"#f1ca6b",1:"#87dfff",2:"#c1a1ff",3:"#90f2d2",4:"#f39ddd",5:"#87dfff",6:"#95a5c3"};
const KIND_EMOJI = {mother:"🌌",executive:"⚡",secretary:"🎯",tool:"🔧",domain:"🌐",machine:"⚙️",atom:"⚛️"};

async function renderBrainHierarchy() {
  const container = document.getElementById("brainHierarchyWrap");
  if (!container) return;
  try {
    const data = await apiReq("/api/brain/hierarchy");
    if (!data) return;
    const { brains, permission_relays, motivation_streams, layers, summary } = data;

    container.innerHTML = `
      <div class="bh-summary">
        <div class="bh-stat"><strong>${summary.total_brains}</strong><span>Total Brains</span></div>
        <div class="bh-stat"><strong>${summary.layers}</strong><span>Layers</span></div>
        <div class="bh-stat"><strong>${summary.alive}</strong><span>Alive</span></div>
        <div class="bh-stat"><strong>${summary.permission_relays}</strong><span>Relays</span></div>
        <div class="bh-stat"><strong>${summary.total_thoughts.toLocaleString()}</strong><span>Thoughts</span></div>
        <div class="bh-stat"><strong>${(summary.avg_learning_score*100).toFixed(1)}%</strong><span>Avg Learning</span></div>
      </div>

      <div class="bh-tabs">
        <button class="bh-tab on" onclick="showBHTab('tree',this)">🌌 Brain Tree</button>
        <button class="bh-tab" onclick="showBHTab('relay',this)">⚡ Permission Relay</button>
        <button class="bh-tab" onclick="showBHTab('motivation',this)">🔥 Motivation</button>
        <button class="bh-tab" onclick="showBHTab('atoms',this)">⚛️ Atom Level</button>
      </div>

      <div id="bh-tree" class="bh-content">
        ${Object.entries(layers).sort((a,b)=>+a[0]-+b[0]).map(([layer, info]) => `
          <div class="bh-layer">
            <div class="bh-layer-head" style="color:${LAYER_COLORS[+layer]||'#95a5c3'}">
              ${LAYER_NAMES[+layer]||'Layer '+layer} <span class="bh-layer-count">${info.count}</span>
            </div>
            <div class="bh-layer-cards">
              ${brains.filter(b=>b.layer===+layer).map(b => `
                <div class="bh-card" style="border-left-color:${LAYER_COLORS[+layer]||'#95a5c3'}">
                  <div class="bh-card-head">
                    <span class="bh-emoji">${b.emoji}</span>
                    <div class="bh-card-info">
                      <div class="bh-card-name">${b.name}</div>
                      <div class="bh-card-domain">${b.domain} · ${b.kind}</div>
                    </div>
                    <div class="bh-card-score">
                      <div class="bh-score-val" style="color:${b.load>80?'#ff847d':'#90f2d2'}">${b.load}%</div>
                      <div class="bh-score-lbl">load</div>
                    </div>
                  </div>
                  <div class="bh-card-thought">${b.last_thought||'Initializing...'}</div>
                  <div class="bh-card-task">${b.assigned_task.slice(0,80)}...</div>
                  <div class="bh-card-meta">
                    <span>Authority: ${b.authority}</span>
                    <span>Thoughts: ${b.thoughts_processed}</span>
                    <span>Learning: ${(b.learning_score*100).toFixed(0)}%</span>
                    ${b.autonomous_cycle_sec > 0 ? `<span class="bh-alive">● ALIVE (${b.autonomous_cycle_sec}s)</span>` : '<span>Manual</span>'}
                  </div>
                  ${b.layer <= 2 ? `<div class="bh-card-btns">
                    <button onclick="assignBrainTask('${b.id}','${b.name}')" class="bh-btn">Assign Task</button>
                    <button onclick="motivateBrain('${b.id}')" class="bh-btn bh-btn-m">Motivate</button>
                    <button onclick="thinkBrain('${b.id}')" class="bh-btn">Think Now</button>
                  </div>` : ''}
                </div>`).join('')}
            </div>
          </div>`).join('')}
      </div>

      <div id="bh-relay" class="bh-content" style="display:none">
        <div class="bh-relay-header">Permission flows from Mother Brain down through ${summary.permission_relays} relay channels</div>
        <div class="bh-relay-list">
          ${permission_relays.slice(0,30).map(r => `
            <div class="bh-relay-row" style="border-left-color:${LAYER_COLORS[r.layer]||'#95a5c3'}">
              <div class="bh-relay-from">${r.from}</div>
              <div class="bh-relay-arrow">→</div>
              <div class="bh-relay-to">${r.to}</div>
              <div class="bh-relay-perms">${r.permission.join(', ')}</div>
            </div>`).join('')}
        </div>
      </div>

      <div id="bh-motivation" class="bh-content" style="display:none">
        <button onclick="motivateAll()" class="bh-motivate-all">🔥 Motivate All Brains</button>
        <div id="bhMotivateResult"></div>
        <div class="bh-motivation-grid">
          ${motivation_streams.map(m => `
            <div class="bh-motivation-card">
              <div class="bh-m-emoji">${m.emoji}</div>
              <div class="bh-m-name">${m.brain}</div>
              <div class="bh-m-text">"${m.motivation}"</div>
            </div>`).join('')}
        </div>
      </div>

      <div id="bh-atoms" class="bh-content" style="display:none">
        <div class="bh-atom-note">⚛️ Atom brains are the smallest intelligent units. Each one performs a single precise function, working in parallel across the empire.</div>
        <div class="bh-atom-grid">
          ${brains.filter(b=>b.kind==='atom').map(b => `
            <div class="bh-atom-card">
              <div class="bh-atom-emoji">${b.emoji}</div>
              <div class="bh-atom-name">${b.name}</div>
              <div class="bh-atom-domain">${b.domain}</div>
              <div class="bh-atom-task">${b.assigned_task.slice(0,60)}</div>
              <div class="bh-atom-stat">Thoughts: ${b.thoughts_processed}</div>
            </div>`).join('')}
        </div>
      </div>

      <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
        <button onclick="renderBrainHierarchy()" style="padding:8px 14px;border-radius:999px;background:rgba(241,202,107,.1);border:1px solid rgba(241,202,107,.25);color:var(--gold);cursor:pointer;font-weight:700">↻ Refresh</button>
        <button onclick="assignBrainTask('all','All Brains')" style="padding:8px 14px;border-radius:999px;background:rgba(135,223,255,.08);border:1px solid rgba(135,223,255,.2);color:var(--blue);cursor:pointer;font-weight:700">⚡ Mass Task Deploy</button>
      </div>
    `;
  } catch(e) {
    if (container) container.innerHTML = `<div style="color:var(--muted);padding:18px">Brain hierarchy loading... ${e.message||''}</div>`;
  }
}

function showBHTab(tab, btn) {
  ['tree','relay','motivation','atoms'].forEach(t => {
    const el = document.getElementById('bh-'+t);
    if (el) el.style.display = t===tab ? 'block' : 'none';
  });
  document.querySelectorAll('.bh-tab').forEach(b => b.classList.remove('on'));
  if (btn) btn.classList.add('on');
}

async function assignBrainTask(brainId, brainName) {
  const task = prompt(`Assign task to ${brainName}:`, `Analyze your domain and report top 3 insights`);
  if (!task) return;
  try {
    const d = await apiReq('/api/brain/assign-task', { method:'POST', body:JSON.stringify({brain_id:brainId,task,context:'Master assigned directly'}) });
    showToast(`${brainName} executed: ${(d?.result||'').slice(0,60)}...`);
    renderBrainHierarchy();
  } catch(e) { showToast('Error: '+e.message); }
}

async function motivateBrain(brainId) {
  try {
    const d = await apiReq('/api/brain/motivate', { method:'POST', body:JSON.stringify({brain_id:brainId}) });
    showToast((d?.results?.[0]?.message||'Motivated!').slice(0,80));
    renderBrainHierarchy();
  } catch(e) { showToast('Error'); }
}

async function motivateAll() {
  const el = document.getElementById('bhMotivateResult');
  if (el) el.innerHTML = '<div style="color:var(--muted)">Motivating all brains...</div>';
  try {
    const d = await apiReq('/api/brain/motivate', { method:'POST', body:JSON.stringify({brain_id:'all'}) });
    showToast(`Motivated ${d?.motivated||0} brains!`);
    if (el) el.innerHTML = `<div style="color:var(--teal);padding:10px">✅ ${d?.motivated||0} brains energized</div>`;
    renderBrainHierarchy();
  } catch(e) { showToast('Error'); }
}

async function thinkBrain(brainId) {
  try {
    const d = await apiReq(`/api/brain/think/${brainId}`, { method:'POST', body:JSON.stringify({context:'Manual think trigger from master'}) });
    showToast(`${d?.brain}: ${(d?.thought||'').slice(0,60)}`);
    renderBrainHierarchy();
  } catch(e) { showToast('Error'); }
}

// Auto-refresh hierarchy every 30s when panel is visible
let _bhRefreshInterval = null;
function startBHAutoRefresh() {
  if (_bhRefreshInterval) clearInterval(_bhRefreshInterval);
  _bhRefreshInterval = setInterval(() => {
    const panel = document.getElementById('panel-monitor');
    const wrap = document.getElementById('brainHierarchyWrap');
    if (panel && panel.classList.contains('active') && wrap) renderBrainHierarchy();
  }, 30000);
}
startBHAutoRefresh();
