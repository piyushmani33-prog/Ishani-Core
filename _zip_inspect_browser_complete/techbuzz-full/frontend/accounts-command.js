// ── Accounts API with cookie auth ────────────────────────────────────────────
async function api(path, opts={}) {
  const isFD = opts.body instanceof FormData;
  const r = await fetch(path, {
    credentials: 'include',
    headers: isFD ? {} : {'Content-Type':'application/json'},
    ...opts
  });
  if(r.status===401){window.location.href='/login?next=/agent';throw new Error('Session expired');}
  const d = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(d.detail||d.message||'Error '+r.status);
  return d;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  ACCOUNTS COMMAND — Indian GST/TDS/ITR automation
//  Learns from regional tax system, manages accounts automatically
// ═══════════════════════════════════════════════════════════════════════════════

async function renderAccountsCommand() {
  const el = document.getElementById("accountsCommandWrap");
  if (!el) return;
  try {
    const status = await api("/api/accounts/status");
    const fin = status.financials || {};
    const regional = status.regional_tax || {};

    el.innerHTML = `
      <div class="acc-header">
        <div class="acc-brand">
          <span class="acc-emoji">📊</span>
          <div>
            <div class="acc-title">Accounts Command</div>
            <div class="acc-sub">${regional.state||'Uttar Pradesh'} · GST/TDS Automated</div>
          </div>
        </div>
        <div class="acc-brain-badge">⚡ Accounts Executive Brain Active</div>
      </div>

      <div class="acc-metrics">
        <div class="acc-metric"><strong style="color:var(--teal)">₹${(fin.income||0).toLocaleString('en-IN')}</strong><span>Income</span></div>
        <div class="acc-metric"><strong style="color:var(--danger)">₹${(fin.expenses||0).toLocaleString('en-IN')}</strong><span>Expenses</span></div>
        <div class="acc-metric"><strong style="color:${fin.net>=0?'var(--teal)':'var(--danger)'}">₹${(fin.net||0).toLocaleString('en-IN')}</strong><span>Net P&L</span></div>
        <div class="acc-metric"><strong style="color:var(--gold)">₹${(fin.gst_liability||0).toLocaleString('en-IN')}</strong><span>GST Collected</span></div>
        <div class="acc-metric"><strong style="color:var(--violet)">₹${(fin.tds_deducted||0).toLocaleString('en-IN')}</strong><span>TDS Deducted</span></div>
        <div class="acc-metric"><strong style="color:var(--rose)">${status.pending_invoices||0}</strong><span>Pending Inv</span></div>
      </div>

      <div class="acc-tabs">
        <button class="acc-tab on" onclick="showAccTab('add',this)">➕ Add Entry</button>
        <button class="acc-tab" onclick="showAccTab('invoice',this)">🧾 Invoice</button>
        <button class="acc-tab" onclick="showAccTab('gst',this)">🏛️ GST Calc</button>
        <button class="acc-tab" onclick="showAccTab('tds',this)">📝 TDS Calc</button>
        <button class="acc-tab" onclick="showAccTab('analyze',this)">🧠 AI Analysis</button>
        <button class="acc-tab" onclick="showAccTab('calendar',this)">📅 Tax Calendar</button>
        <button class="acc-tab" onclick="showAccTab('ledger',this)">📚 Ledger</button>
      </div>

      <!-- Add Entry -->
      <div id="acc-add" class="acc-panel">
        <div class="acc-form">
          <div class="acc-row2">
            <div class="acc-fg"><label>Date</label><input type="date" id="aDate" class="acc-fi" value="${new Date().toISOString().slice(0,10)}"></div>
            <div class="acc-fg"><label>Type</label>
              <select id="aType" class="acc-fi">
                <option value="receipt">💰 Receipt / Income</option>
                <option value="payment">💸 Payment / Expense</option>
                <option value="sales">🛒 Sales</option>
                <option value="purchase">📦 Purchase</option>
              </select>
            </div>
          </div>
          <div class="acc-row2">
            <div class="acc-fg"><label>Amount (₹)</label><input type="number" id="aAmt" class="acc-fi" placeholder="50000"></div>
            <div class="acc-fg"><label>Party Name</label><input id="aParty" class="acc-fi" placeholder="Client / Vendor name"></div>
          </div>
          <div class="acc-fg"><label>Description (AI auto-detects GST & TDS)</label>
            <input id="aDesc" class="acc-fi" placeholder="Recruitment consultancy fee for Infosys placement..."></div>
          <button onclick="addLedgerEntry()" class="acc-btn">+ Add Entry (AI auto-calculates tax)</button>
          <div id="aResult" class="acc-result"></div>
        </div>
      </div>

      <!-- Invoice -->
      <div id="acc-invoice" class="acc-panel" style="display:none">
        <div class="acc-form">
          <div class="acc-row2">
            <div class="acc-fg"><label>Client Name</label><input id="iClient" class="acc-fi" placeholder="Infosys Ltd"></div>
            <div class="acc-fg"><label>Client GSTIN (optional)</label><input id="iGstin" class="acc-fi" placeholder="27XXXXX..."></div>
          </div>
          <div class="acc-fg"><label>Service Description</label>
            <input id="iDesc" class="acc-fi" placeholder="Recruitment consultancy fee — Senior Python Engineer placement"></div>
          <div class="acc-row2">
            <div class="acc-fg"><label>Amount (₹) before GST</label><input type="number" id="iAmt" class="acc-fi" placeholder="150000"></div>
            <div class="acc-fg"><label>Payment Due (days)</label><input type="number" id="iDue" class="acc-fi" value="30"></div>
          </div>
          <button onclick="createInvoice()" class="acc-btn">🧾 Generate Invoice (GST auto-applied)</button>
          <div id="iResult" class="acc-result"></div>
        </div>
      </div>

      <!-- GST Calculator -->
      <div id="acc-gst" class="acc-panel" style="display:none">
        <div class="acc-form">
          <div class="acc-row2">
            <div class="acc-fg"><label>Base Amount (₹)</label><input type="number" id="gAmt" class="acc-fi" placeholder="100000"></div>
            <div class="acc-fg"><label>Supply Type</label>
              <select id="gSupply" class="acc-fi">
                <option value="intra">Intra-state (CGST + SGST)</option>
                <option value="inter">Inter-state (IGST)</option>
              </select>
            </div>
          </div>
          <div class="acc-fg"><label>Service Category</label>
            <select id="gCat" class="acc-fi">
              <option value="recruitment_fee">Recruitment Consultancy (SAC 998511) — 18%</option>
              <option value="training">Training Services — 18%</option>
              <option value="software">Software/IT Services — 18%</option>
              <option value="goods">General Goods — 12%</option>
            </select>
          </div>
          <button onclick="calcGST()" class="acc-btn">Calculate GST</button>
          <div id="gResult" class="acc-result"></div>
        </div>
        <div class="acc-info-box">
          <strong>UP GST Notes:</strong> Recruitment consultancy (SAC 998511) attracts 18% GST. 
          If supplier and recipient are in same state → CGST 9% + SGST 9%. 
          If different states → IGST 18%. Input Tax Credit available for registered businesses.
        </div>
      </div>

      <!-- TDS Calculator -->
      <div id="acc-tds" class="acc-panel" style="display:none">
        <div class="acc-form">
          <div class="acc-row2">
            <div class="acc-fg"><label>Payment Amount (₹)</label><input type="number" id="tAmt" class="acc-fi" placeholder="50000"></div>
            <div class="acc-fg"><label>TDS Section</label>
              <select id="tSection" class="acc-fi">
                <option value="194J">194J — Professional/Technical Services (10%)</option>
                <option value="194C">194C — Contractor Payment (1% individual, 2% company)</option>
                <option value="194H">194H — Commission/Brokerage (5%)</option>
                <option value="194I">194I — Rent — Plant/Machinery (10%)</option>
              </select>
            </div>
          </div>
          <div class="acc-row2">
            <div class="acc-fg"><label>Party Name</label><input id="tParty" class="acc-fi" placeholder="Vendor name"></div>
            <div class="acc-fg"><label>PAN</label><input id="tPan" class="acc-fi" placeholder="ABCDE1234F"></div>
          </div>
          <button onclick="calcTDS()" class="acc-btn">Calculate TDS</button>
          <div id="tResult" class="acc-result"></div>
        </div>
        <div class="acc-info-box">
          <strong>TDS Reminders:</strong> Deposit TDS by 7th of following month. 
          File quarterly return (Form 26Q) by 15th of month following quarter end. 
          Issue Form 16A within 15 days of filing return.
        </div>
      </div>

      <!-- AI Analysis -->
      <div id="acc-analyze" class="acc-panel" style="display:none">
        <div class="acc-form">
          <div class="acc-fg"><label>Question for Accounts Brain</label>
            <textarea id="anQuestion" class="acc-fi" style="min-height:80px;resize:vertical" 
              placeholder="Am I GST compliant? What taxes are due this month? How can I save more tax? Show me my P&L. When should I file GSTR-3B?"></textarea>
          </div>
          <button onclick="runAccountsAnalysis()" class="acc-btn">🧠 Diamond-Mind Analysis</button>
          <div id="anResult" class="acc-result" style="min-height:120px"></div>
        </div>
      </div>

      <!-- Tax Calendar -->
      <div id="acc-calendar" class="acc-panel" style="display:none">
        <div id="calResult"></div>
        <button onclick="loadTaxCalendar()" class="acc-btn">📅 Load Tax Deadlines</button>
      </div>

      <!-- Ledger -->
      <div id="acc-ledger" class="acc-panel" style="display:none">
        <button onclick="loadLedger()" class="acc-btn" style="margin-bottom:10px">📚 Load Ledger</button>
        <div id="ledResult"></div>
      </div>
    `;
  } catch(e) {
    if (el) el.innerHTML = `<div class="empty">Set up your accounts profile first. <button onclick="setupAccountsProfile()" style="color:var(--gold);background:none;border:none;cursor:pointer;font-weight:700">Setup →</button></div>`;
  }
}

function showAccTab(tab, btn) {
  document.querySelectorAll('.acc-panel').forEach(p => p.style.display = 'none');
  const el = document.getElementById('acc-'+tab);
  if (el) el.style.display = 'block';
  document.querySelectorAll('.acc-tab').forEach(b => b.classList.remove('on'));
  if (btn) btn.classList.add('on');
  if (tab === 'calendar') loadTaxCalendar();
  if (tab === 'ledger') loadLedger();
}

async function addLedgerEntry() {
  const amt = parseFloat(document.getElementById('aAmt')?.value);
  const desc = document.getElementById('aDesc')?.value.trim();
  if (!amt || !desc) { showAccountsToast('Fill amount and description'); return; }
  const btn = event.target; btn.disabled=true; btn.textContent='AI calculating...';
  try {
    const d = await api('/api/accounts/ledger', {method:'POST',body:JSON.stringify({
      date:document.getElementById('aDate').value,
      entry_type:document.getElementById('aType').value,
      amount:amt,description:desc,
      party_name:document.getElementById('aParty').value,
    })});
    document.getElementById('aResult').innerHTML = `
      <div class="acc-success">
        ✅ Entry recorded<br>
        ${d.gst?.cgst>0?`GST: CGST ₹${d.gst.cgst} + SGST ₹${d.gst.sgst}`:''}
        ${d.tds?.applicable?`<br>TDS ${d.tds.section}: ₹${d.tds.amount} deducted`:''}
      </div>`;
    showAccountsToast('Ledger entry added!');
    renderAccountsCommand();
  } catch(e) { document.getElementById('aResult').innerHTML=`<div style="color:var(--danger)">${e.message}</div>`; }
  btn.disabled=false; btn.textContent='+ Add Entry (AI auto-calculates tax)';
}

async function createInvoice() {
  const amt = parseFloat(document.getElementById('iAmt')?.value);
  const client = document.getElementById('iClient')?.value.trim();
  if (!amt || !client) { showAccountsToast('Fill client and amount'); return; }
  const btn = event.target; btn.disabled=true; btn.textContent='Generating...';
  try {
    const d = await api('/api/accounts/invoice',{method:'POST',body:JSON.stringify({
      client_name:client,client_gstin:document.getElementById('iGstin').value,
      description:document.getElementById('iDesc').value,
      amount:amt,due_days:parseInt(document.getElementById('iDue').value)||30
    })});
    document.getElementById('iResult').innerHTML = `
      <div class="acc-success">
        <strong>Invoice ${d.invoice_no}</strong><br>
        Base: ₹${amt.toLocaleString('en-IN')}<br>
        CGST (9%): ₹${d.gst?.cgst||0}<br>
        SGST (9%): ₹${d.gst?.sgst||0}<br>
        ${d.gst?.igst>0?`IGST (18%): ₹${d.gst.igst}<br>`:''}
        <strong>Total: ₹${(d.total||0).toLocaleString('en-IN')}</strong><br>
        Due: ${d.due_date}
      </div>`;
    showAccountsToast('Invoice created!');
  } catch(e) { document.getElementById('iResult').innerHTML=`<div style="color:var(--danger)">${e.message}</div>`; }
  btn.disabled=false; btn.textContent='🧾 Generate Invoice';
}

async function calcGST() {
  const amt = parseFloat(document.getElementById('gAmt')?.value);
  if (!amt) { showAccountsToast('Enter amount'); return; }
  const d = await api('/api/accounts/gst-calc',{method:'POST',body:JSON.stringify({
    amount:amt,supply_type:document.getElementById('gSupply').value,
    category:document.getElementById('gCat').value
  })});
  document.getElementById('gResult').innerHTML = `
    <div class="acc-success">
      Base Amount: ₹${amt.toLocaleString('en-IN')}<br>
      Rate: ${d.rate_applied}% GST (SAC: Recruitment Consultancy)<br>
      ${d.cgst>0?`CGST (${d.rate_applied/2}%): ₹${d.cgst.toLocaleString('en-IN')}<br>SGST (${d.rate_applied/2}%): ₹${d.sgst.toLocaleString('en-IN')}`:`IGST (${d.rate_applied}%): ₹${d.igst.toLocaleString('en-IN')}`}<br>
      <strong>Invoice Total: ₹${d.invoice_total.toLocaleString('en-IN')}</strong><br>
      <small style="color:var(--muted)">${d.notes||''}</small>
    </div>`;
}

async function calcTDS() {
  const amt = parseFloat(document.getElementById('tAmt')?.value);
  if (!amt) { showAccountsToast('Enter amount'); return; }
  const d = await api('/api/accounts/tds-calc',{method:'POST',body:JSON.stringify({
    section:document.getElementById('tSection').value,
    amount:amt,party_name:document.getElementById('tParty').value,
    party_pan:document.getElementById('tPan').value
  })});
  document.getElementById('tResult').innerHTML = `
    <div class="acc-success">
      Payment: ₹${amt.toLocaleString('en-IN')}<br>
      Section: ${d.section} (${d.rate||10}%)<br>
      ${d.applicable?`TDS Deductible: ₹${(d.tds_amount||0).toLocaleString('en-IN')}<br>
      Net Payable to Party: ₹${(d.net_payable||0).toLocaleString('en-IN')}<br>
      <strong>Deposit TDS by 7th of next month</strong>`
      :`<span style="color:var(--teal)">TDS NOT applicable — ${d.reason}</span>`}
    </div>`;
}

async function runAccountsAnalysis() {
  const q = document.getElementById('anQuestion')?.value.trim();
  const res = document.getElementById('anResult');
  if (res) res.innerHTML = '<div style="color:var(--muted)">Diamond-Mind analyzing...</div>';
  try {
    const d = await api('/api/accounts/analyze',{method:'POST',body:JSON.stringify({question:q||''})});
    if (res) res.innerHTML = `<div style="white-space:pre-wrap;line-height:1.75;font-size:.88rem">${d.analysis||''}</div>`;
  } catch(e) { if(res) res.innerHTML=`<div style="color:var(--danger)">${e.message}</div>`; }
}

async function loadTaxCalendar() {
  try {
    const d = await api('/api/accounts/tax-calendar');
    const el = document.getElementById('calResult');
    if (!el) return;
    const today = new Date().toISOString().slice(0,10);
    el.innerHTML = `<div class="acc-calendar">${(d.calendar||[]).map(item => {
      const isPast = item.deadline < today;
      const isUrgent = !isPast && item.deadline <= new Date(Date.now()+7*86400000).toISOString().slice(0,10);
      return `<div class="acc-cal-item ${isPast?'acc-past':isUrgent?'acc-urgent':''}">
        <div class="acc-cal-date">${item.deadline}</div>
        <div class="acc-cal-task">${item.task}</div>
        <div class="acc-cal-auth">${item.authority} · ${item.penalty}</div>
      </div>`;
    }).join('')}</div>`;
  } catch(e) {}
}

async function loadLedger() {
  try {
    const d = await api('/api/accounts/ledger');
    const el = document.getElementById('ledResult');
    if (!el) return;
    el.innerHTML = (d.ledger||[]).map(e => `
      <div class="acc-led-row">
        <div class="acc-led-dot" style="background:${e.entry_type==='receipt'||e.entry_type==='income'?'var(--teal)':'var(--danger)'}"></div>
        <div class="acc-led-main">
          <div class="acc-led-desc">${e.description}</div>
          <div class="acc-led-meta">${e.date} · ${e.party_name||''} ${e.gst_applicable?'· GST':''} ${e.tds_applicable?'· TDS':''}</div>
        </div>
        <div class="acc-led-amt" style="color:${e.entry_type==='receipt'||e.entry_type==='income'?'var(--teal)':'var(--danger)'}">
          ₹${(e.amount||0).toLocaleString('en-IN')}
        </div>
      </div>`).join('') || '<div class="empty">No ledger entries yet.</div>';
  } catch(e) {}
}

async function setupAccountsProfile() {
  const name = prompt('Business Name:', 'TechBuzz Systems Pvt Ltd');
  if (!name) return;
  const gstin = prompt('GSTIN (optional):', '09XXXXX...');
  const pan = prompt('PAN:', 'XXXXX1234X');
  try {
    await api('/api/accounts/profile',{method:'POST',body:JSON.stringify({business_name:name,gstin:gstin||'',pan:pan||'',state_code:'09',city:'Lucknow',regional_profile:'UP_STANDARD'})});
    showAccountsToast('Profile saved!');
    renderAccountsCommand();
  } catch(e) { showAccountsToast('Error: '+e.message); }
}

function showAccountsToast(msg) {
  const t = document.getElementById('toast');
  if (t) { t.textContent=msg; t.style.display='block'; setTimeout(()=>t.style.display='none',2600); }
}
