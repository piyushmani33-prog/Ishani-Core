// ═══════════════════════════════════════════════════════════════════════════════
//  INTELLIGENCE ENGINE UI — Web Mining · News · Brain Learning
//  Each brain learns from Google (DDG), RSS news, URLs, local files
// ═══════════════════════════════════════════════════════════════════════════════

// Universal API shim
const _intelApi = (typeof api !== 'undefined') ? api : async function(url,opts){
  const r=await fetch(url,{credentials:'include',headers:{'Content-Type':'application/json'},...(opts||{})});
  if(r.status===401){window.location.href='/login';throw new Error('Auth');}
  const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Error');return d;
};
const _intelToast=(m)=>{let el=document.getElementById('empToast')||document.getElementById('toast')||document.getElementById('portalToast');if(el){el.textContent=m;el.style.display='block';clearTimeout(el._t);el._t=setTimeout(()=>el.style.display='none',2800);}else console.log('[Intel]',m);};

async function renderIntelPanel() {
  const wrap = document.getElementById('intelPanelWrap');
  if (!wrap) return;
  try {
    const sources = await _intelApi('/api/intel/sources');
    const knowledge = await _intelApi('/api/intel/all-knowledge');
    const items = knowledge.knowledge || [];

    wrap.innerHTML = `
      <div class="intel-header">
        <div class="intel-brand">
          <span style="font-size:1.6rem">🌐</span>
          <div>
            <div style="font-weight:900;font-size:.95rem">Intelligence Engine</div>
            <div style="font-size:.7rem;color:var(--muted);letter-spacing:.1em;text-transform:uppercase">Web Mining · News · Learning · Graphene-Mind</div>
          </div>
        </div>
        <div style="font-size:.72rem;color:var(--teal);padding:5px 10px;border-radius:999px;border:1px solid rgba(144,242,210,.2);background:rgba(144,242,210,.07);font-weight:700">
          ${items.length} items learned
        </div>
      </div>

      <div class="intel-tabs">
        <button class="itab on" onclick="showIntelTab('search',this)">🔍 Web Search</button>
        <button class="itab" onclick="showIntelTab('news',this)">📰 News Feeds</button>
        <button class="itab" onclick="showIntelTab('url',this)">🔗 URL Fetch</button>
        <button class="itab" onclick="showIntelTab('mass',this)">🧠 Mass Learn</button>
        <button class="itab" onclick="showIntelTab('knowledge',this)">📚 Knowledge Base</button>
      </div>

      <!-- Web Search -->
      <div id="it-search" class="it-panel">
        <div style="margin-bottom:10px;font-size:.82rem;color:var(--muted)">
          Powered by DuckDuckGo — no API key required. Selected brain learns and stores results.
        </div>
        <div style="display:grid;grid-template-columns:1fr auto;gap:8px;margin-bottom:10px">
          <input class="fi" id="itQuery" placeholder="Search: AI hiring trends India, Python developer salary 2025..." onkeydown="if(event.key==='Enter')intelSearch()">
          <button class="abtn" onclick="intelSearch()" id="itSearchBtn">🔍 Search & Learn</button>
        </div>
        <div style="margin-bottom:10px">
          <label style="font-size:.68rem;font-weight:700;color:var(--muted);letter-spacing:.14em;text-transform:uppercase;display:block;margin-bottom:4px">Assign to Brain</label>
          <select class="fi" id="itBrainSel" style="max-width:300px">
            ${['sec_signals','sec_anveshan','sec_hunt','dom_network','exec_research','tool_researcher','sec_source']
              .map(id=>`<option value="${id}">${id.replace(/_/g,' ')}</option>`).join('')}
          </select>
        </div>
        <div id="itSearchResult" class="intel-result"></div>
      </div>

      <!-- News -->
      <div id="it-news" class="it-panel" style="display:none">
        <div style="margin-bottom:10px;font-size:.82rem;color:var(--muted)">
          RSS news feeds — free, no API key. Brains automatically learn from assigned feeds.
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:8px;margin-bottom:10px">
          <select class="fi" id="itCatSel">
            <option value="tech">Technology News</option>
            <option value="india_business">India Business</option>
            <option value="hiring">Jobs & Hiring</option>
            <option value="ai">AI Research</option>
          </select>
          <select class="fi" id="itNewsBrain">
            ${['exec_research','sec_anveshan','exec_praapti','sec_signals','exec_accounts','dom_network']
              .map(id=>`<option value="${id}">${id.replace(/_/g,' ')}</option>`).join('')}
          </select>
          <button class="abtn" onclick="intelNews()" id="itNewsBtn">📰 Fetch & Learn</button>
        </div>
        <div id="itNewsResult" class="intel-result"></div>
        
        <!-- Available feeds display -->
        <div style="margin-top:14px">
          <div style="font-size:.7rem;font-weight:800;color:var(--muted);letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px">Available RSS Feeds</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px">
            ${Object.entries(sources.news_feeds||{}).map(([cat,feeds])=>`
              <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:10px">
                <div style="font-weight:700;font-size:.82rem;margin-bottom:5px;color:var(--gold)">${cat}</div>
                ${feeds.map(f=>`<div style="font-size:.68rem;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${f}</div>`).join('')}
              </div>`).join('')}
          </div>
        </div>
      </div>

      <!-- URL Fetch -->
      <div id="it-url" class="it-panel" style="display:none">
        <div style="margin-bottom:10px;font-size:.82rem;color:var(--muted)">
          Fetch any URL — the brain extracts and stores the text content for learning.
        </div>
        <div style="display:grid;grid-template-columns:1fr;gap:8px;margin-bottom:10px">
          <input class="fi" id="itUrl" placeholder="https://techcrunch.com/article... or any URL">
          <div style="display:grid;grid-template-columns:1fr auto;gap:8px">
            <select class="fi" id="itUrlBrain">
              ${['tool_researcher','sec_anveshan','sec_signals','dom_network','sec_gst','sec_tds']
                .map(id=>`<option value="${id}">${id.replace(/_/g,' ')}</option>`).join('')}
            </select>
            <button class="abtn" onclick="intelFetchUrl()" id="itUrlBtn">🔗 Fetch & Learn</button>
          </div>
        </div>
        <div id="itUrlResult" class="intel-result"></div>
        <div style="margin-top:10px;padding:10px 14px;background:rgba(255,255,255,.03);border-radius:12px;font-size:.78rem;color:var(--muted)">
          <strong style="color:var(--gold)">Example URLs to try:</strong><br>
          https://economictimes.indiatimes.com<br>
          https://timesofindia.indiatimes.com<br>
          https://inc42.com (Indian startup news)<br>
          Any Wikipedia article, government portal, or business news site
        </div>
      </div>

      <!-- Mass Learn -->
      <div id="it-mass" class="it-panel" style="display:none">
        <div style="margin-bottom:14px;padding:14px;background:rgba(144,242,210,.05);border:1px solid rgba(144,242,210,.15);border-radius:14px">
          <div style="font-weight:700;margin-bottom:4px">🧠 Graphene-Mind Mass Learning</div>
          <div style="font-size:.82rem;color:var(--muted);line-height:1.65">
            All major brains learn simultaneously from the web. Hunt Secretary searches for talent sourcing techniques. 
            Signals Secretary scans hiring trends. Anveshan searches AI research. GST/TDS brains update tax knowledge.
            Runs across 8 brains in parallel.
          </div>
        </div>
        <button class="abtn" style="width:100%;justify-content:center;padding:14px" onclick="intelMassLearn()" id="itMassBtn">
          🌐 Launch Mass Learning — All Brains
        </button>
        <div id="itMassResult" class="intel-result" style="margin-top:10px"></div>
      </div>

      <!-- Knowledge Base -->
      <div id="it-knowledge" class="it-panel" style="display:none">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">
          <div style="font-weight:700">All Brain Knowledge (${items.length} items)</div>
          <div style="display:flex;gap:7px">
            <select class="fi" id="kbFilterBrain" style="max-width:180px" onchange="filterKnowledge(this.value)">
              <option value="">All Brains</option>
              ${[...new Set(items.map(i=>i.brain_id))].map(b=>`<option value="${b}">${b}</option>`).join('')}
            </select>
            <button class="gbtn" onclick="renderIntelPanel()">↻</button>
          </div>
        </div>
        <div id="kbList">${renderKnowledgeList(items)}</div>
      </div>
    `;
  } catch(e) {
    if(wrap) wrap.innerHTML = `<div class="empty">Intelligence Engine loading... ${e.message||''}</div>`;
  }
}

function showIntelTab(tab, btn) {
  ['search','news','url','mass','knowledge'].forEach(t => {
    const el = document.getElementById('it-'+t);
    if(el) el.style.display = t===tab ? 'block' : 'none';
  });
  document.querySelectorAll('.itab').forEach(b => b.classList.remove('on'));
  if(btn) btn.classList.add('on');
}

function renderKnowledgeList(items) {
  if(!items.length) return '<div class="empty">No knowledge stored yet. Run Web Search or Mass Learn above.</div>';
  return items.map(k => `
    <div style="padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.04);margin-bottom:7px">
      <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:5px">
        <span style="font-size:.65rem;padding:2px 8px;border-radius:999px;background:rgba(144,242,210,.08);border:1px solid rgba(144,242,210,.15);color:var(--teal);font-weight:700;flex-shrink:0">${k.brain_id||''}</span>
        <div style="font-weight:700;font-size:.85rem;line-height:1.4;flex:1">${k.title||'Untitled'}</div>
        <span style="font-size:.65rem;color:var(--muted);flex-shrink:0">${(k.source_type||'web').replace('_',' ')}</span>
      </div>
      <div style="font-size:.78rem;color:var(--muted);line-height:1.6">${(k.summary||k.content||'').slice(0,180)}</div>
      <div style="font-size:.65rem;color:var(--dim,#3a4a64);margin-top:5px">${new Date(k.learned_at||Date.now()).toLocaleString('en-IN')}</div>
    </div>`).join('');
}

function filterKnowledge(brainId) {
  _intelApi('/api/intel/knowledge/'+(brainId||'all')+(!brainId?'':'')).then(d=>{
    const el = document.getElementById('kbList');
    if(el) el.innerHTML = renderKnowledgeList(d.knowledge||[]);
  }).catch(()=>{});
}

async function intelSearch() {
  const q = document.getElementById('itQuery')?.value.trim();
  const brain = document.getElementById('itBrainSel')?.value || 'sec_signals';
  if(!q) { _intelToast('Enter a search query'); return; }
  const btn = document.getElementById('itSearchBtn');
  btn.disabled=true; btn.innerHTML='<span class="spin"></span> Searching...';
  const res = document.getElementById('itSearchResult');
  if(res) res.innerHTML = '<div style="color:var(--muted)">🔍 Searching DuckDuckGo and learning...</div>';
  try {
    const d = await _intelApi('/api/intel/search', {method:'POST',body:JSON.stringify({query:q,brain_id:brain,engine:'web'})});
    _intelToast(`Brain learned ${d.stored||0} items about: ${q.slice(0,40)}`);
    if(res) res.innerHTML = `
      <div style="color:var(--teal);margin-bottom:10px;font-size:.82rem">✅ ${d.stored||0} items stored in ${brain}</div>
      ${(d.results||[]).map(r=>`<div style="padding:8px;border-radius:10px;border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.04);margin-bottom:6px">
        <div style="font-weight:700;font-size:.82rem">${r.title||''}</div>
        <div style="font-size:.75rem;color:var(--muted);margin-top:3px">${r.summary||''}</div>
      </div>`).join('')}`;
  } catch(e) { if(res) res.innerHTML=`<div style="color:var(--danger)">${e.message}</div>`; }
  btn.disabled=false; btn.textContent='🔍 Search & Learn';
}

async function intelNews() {
  const cat = document.getElementById('itCatSel')?.value || 'tech';
  const brain = document.getElementById('itNewsBrain')?.value || 'exec_research';
  const btn = document.getElementById('itNewsBtn');
  btn.disabled=true; btn.innerHTML='<span class="spin"></span> Fetching news...';
  const res = document.getElementById('itNewsResult');
  if(res) res.innerHTML='<div style="color:var(--muted)">📰 Fetching RSS feeds...</div>';
  try {
    const d = await _intelApi('/api/intel/news', {method:'POST',body:JSON.stringify({category:cat,brain_id:brain})});
    _intelToast(`${brain} learned ${d.stored||0} news items`);
    if(res) res.innerHTML = `
      <div style="color:var(--teal);margin-bottom:10px;font-size:.82rem">✅ ${d.stored||0} news items stored</div>
      ${(d.results||[]).map(r=>`<div style="padding:8px;border-radius:10px;border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.04);margin-bottom:6px">
        <div style="font-weight:700;font-size:.82rem">${r.title||''}</div>
        <div style="font-size:.75rem;color:var(--muted);margin-top:3px">${r.summary||''}</div>
      </div>`).join('')}`;
  } catch(e) { if(res) res.innerHTML=`<div style="color:var(--danger)">${e.message}</div>`; }
  btn.disabled=false; btn.textContent='📰 Fetch & Learn';
}

async function intelFetchUrl() {
  const url = document.getElementById('itUrl')?.value.trim();
  const brain = document.getElementById('itUrlBrain')?.value || 'tool_researcher';
  if(!url) { _intelToast('Enter a URL'); return; }
  const btn = document.getElementById('itUrlBtn');
  btn.disabled=true; btn.innerHTML='<span class="spin"></span>';
  const res = document.getElementById('itUrlResult');
  if(res) res.innerHTML='<div style="color:var(--muted)">🔗 Fetching URL content...</div>';
  try {
    const d = await _intelApi('/api/intel/fetch-url', {method:'POST',body:JSON.stringify({url,brain_id:brain})});
    _intelToast(`${brain} learned from ${url.slice(0,40)}`);
    if(res) res.innerHTML = `
      <div style="color:var(--teal);margin-bottom:8px;font-size:.82rem">✅ Content stored (${d.content_length||0} chars)</div>
      <div style="font-size:.78rem;color:var(--muted);line-height:1.65;background:rgba(255,255,255,.04);border-radius:10px;padding:10px">${d.preview||''}</div>`;
  } catch(e) { if(res) res.innerHTML=`<div style="color:var(--danger)">${e.message}</div>`; }
  btn.disabled=false; btn.textContent='🔗 Fetch & Learn';
}

async function intelMassLearn() {
  const btn = document.getElementById('itMassBtn');
  const res = document.getElementById('itMassResult');
  btn.disabled=true; btn.innerHTML='<span class="spin"></span> All brains learning from web...';
  if(res) res.innerHTML='<div style="color:var(--muted)">🌐 Graphene-Mind activating — 8 brains learning in parallel...</div>';
  try {
    const d = await _intelApi('/api/intel/mass-learn', {method:'POST',body:JSON.stringify({})});
    _intelToast(`Mass learning complete! ${d.total_learned||0} total items`);
    if(res) res.innerHTML = `
      <div style="color:var(--teal);font-size:.88rem;margin-bottom:10px">✅ ${d.total_learned||0} items learned across ${Object.keys(d.results||{}).length} brains</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px">
        ${Object.entries(d.results||{}).map(([bid,count])=>`
          <div style="padding:10px;border-radius:12px;background:rgba(144,242,210,.06);border:1px solid rgba(144,242,210,.12)">
            <div style="font-size:.72rem;font-weight:800;color:var(--teal)">${bid.replace(/_/g,' ')}</div>
            <div style="font-family:var(--mono,'monospace');font-size:1.2rem;font-weight:900;margin-top:4px">${count} items</div>
          </div>`).join('')}
      </div>`;
    renderIntelPanel(); // Refresh knowledge count
  } catch(e) { if(res) res.innerHTML=`<div style="color:var(--danger)">${e.message}</div>`; }
  btn.disabled=false; btn.textContent='🌐 Launch Mass Learning — All Brains';
}

// Add Intel panel to agent page sections
function addIntelToAgent() {
  const main = document.querySelector('.agent-shell main, .agent-shell');
  if(!main || document.getElementById('intelPanelWrap')) return;
  const section = document.createElement('section');
  section.className='agent-grid pipeline';
  section.style.marginTop='16px';
  section.innerHTML=`
    <article class="agent-card" style="grid-column:1/-1">
      <div class="card-head">
        <h2>🌐 Intelligence Engine</h2>
        <button class="agent-btn small" onclick="renderIntelPanel()">Refresh</button>
      </div>
      <div id="intelPanelWrap"><div class="muted">Loading intelligence engine...</div></div>
    </article>`;
  main.appendChild(section);
  renderIntelPanel();
}

// CSS for intel panel (injected)
const _intelStyle=document.createElement('style');
_intelStyle.textContent=`
.intel-header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px;padding:12px 14px;background:rgba(144,242,210,.04);border:1px solid rgba(144,242,210,.12);border-radius:14px}
.intel-brand{display:flex;align-items:center;gap:10px}
.intel-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;border-bottom:1px solid rgba(255,255,255,.07);padding-bottom:10px}
.itab{padding:6px 12px;border-radius:10px;border:1px solid transparent;background:transparent;color:#95a5c3;cursor:pointer;font-weight:700;font-size:.8rem;transition:all .15s}
.itab.on{background:rgba(144,242,210,.08);border-color:rgba(144,242,210,.22);color:#90f2d2}
.it-panel{animation:itFade .2s ease}
@keyframes itFade{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:none}}
.intel-result{margin-top:10px}
.fi{width:100%;padding:9px 13px;border-radius:12px;border:1px solid rgba(255,255,255,.09);background:rgba(255,255,255,.05);color:#edf2ff;font:inherit;outline:none;transition:border-color .15s}
.fi:focus{border-color:rgba(144,242,210,.35)}
.abtn{display:inline-flex;align-items:center;justify-content:center;gap:5px;padding:8px 15px;border-radius:999px;background:linear-gradient(135deg,#f1ca6b,#ff9c63);color:#0b0f17;border:none;font-weight:900;cursor:pointer;font-size:.83rem;white-space:nowrap;transition:all .15s}
.abtn:hover{filter:brightness(1.1)}.abtn:disabled{opacity:.4;cursor:not-allowed}
.gbtn{display:inline-flex;align-items:center;gap:5px;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.05);color:#edf2ff;border:1px solid rgba(255,255,255,.09);font-weight:700;cursor:pointer;font-size:.8rem;transition:all .15s}
.gbtn:hover{border-color:rgba(144,242,210,.3);color:#90f2d2}
.spin{display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.2);border-top-color:currentColor;border-radius:50%;animation:_ispn .7s linear infinite}
@keyframes _ispn{to{transform:rotate(360deg)}}
.empty{text-align:center;padding:20px;color:#95a5c3;border:1px dashed rgba(255,255,255,.09);border-radius:14px;font-size:.85rem}
`;
if(!document.getElementById('intelCSS')){_intelStyle.id='intelCSS';document.head.appendChild(_intelStyle);}

// Auto-add to page if agent
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if(document.querySelector('.agent-shell') && !document.getElementById('intelPanelWrap')) {
      addIntelToAgent();
    }
  }, 2000);
});
