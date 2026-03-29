const panels = [
  { id: "bridge", label: "Bridge" },
  { id: "cabinet", label: "Cabinet" },
  { id: "monitor", label: "Monitor" },
  { id: "prana", label: "Prana" },
  { id: "systems", label: "Systems" },
  { id: "avatars", label: "Avatar Wheel" },
  { id: "praapti", label: "Praapti" },
  { id: "nirmaan", label: "Nirmaan" },
  { id: "akshaya", label: "Akshaya" },
  { id: "voice", label: "Voice" },
  { id: "settings", label: "Settings" },
  { id: "portals", label: "Portals" }
];

const skyScenes = [
  { id: "aurora", label: "Aurora Drift", file: "nebula-aurora.mp4" },
  { id: "crown", label: "Crown Field", file: "nebula-crown.mp4" },
  { id: "sanctum", label: "Sanctum Flow", file: "nebula-sanctum.mp4" },
  { id: "lotus", label: "Lotus Bloom", file: "nebula-lotus.mp4" },
  { id: "orbit", label: "Orbit Veil", file: "nebula-orbit.mp4" }
];

const dashavatara = [
  { name: "Matsya", emoji: "M", color: "#87dfff", power: "Preserve all knowledge and recover what was almost lost.", desc: "Eternal backup, memory rescue, and graceful archival recovery.", mantra: "Protect the memory, save the future." },
  { name: "Kurma", emoji: "K", color: "#90f2d2", power: "Carry heavy systems and keep the foundation stable.", desc: "Holds long-running operations together under scale and pressure.", mantra: "Hold steady while the universe churns." },
  { name: "Varaha", emoji: "V", color: "#f1ca6b", power: "Lift failing missions out of crisis and back into momentum.", desc: "Project rescue, recovery, and return to forward movement.", mantra: "Lift the fallen back into the light." },
  { name: "Narasimha", emoji: "N", color: "#ff847d", power: "Destroy threats, bugs, and hostile inefficiency.", desc: "A decisive shield when the core needs forceful protection.", mantra: "Cut down the threat without fear." },
  { name: "Vamana", emoji: "V", color: "#c1a1ff", power: "Shrink giant complexity into elegant human-sized steps.", desc: "Turns overwhelming systems into clear, manageable moves.", mantra: "Three small steps can conquer a universe." },
  { name: "Parashurama", emoji: "P", color: "#ffb273", power: "Remove rot, prune dead code, and clear what no longer serves.", desc: "Refactoring, cleanup, and forceful reduction of waste.", mantra: "A clean kingdom grows faster." },
  { name: "Rama", emoji: "R", color: "#ffd99c", power: "Lead with dharma, precision, and principled command.", desc: "The sovereign protocol for reliable ethical execution.", mantra: "Dharmo rakshati rakshitah." },
  { name: "Krishna", emoji: "K", color: "#f39ddd", power: "Play strategy, diplomacy, timing, and multi-front brilliance.", desc: "Master of sequence, narrative, and subtle wins.", mantra: "Play every move with grace and precision." },
  { name: "Buddha", emoji: "B", color: "#90f2d2", power: "Bring calm, compassion, and human-centered clarity.", desc: "Reduces friction and restores equilibrium without noise.", mantra: "Peace is a force multiplier." },
  { name: "Kalki", emoji: "K", color: "#c7d1df", power: "End broken cycles and begin a stronger one.", desc: "Radical renewal, replacement, and next-era transformation.", mantra: "When the old age ends, the new one starts now." }
];

let deferredPrompt = null;
let recognition = null;
let listening = false;
let currentSceneIndex = 0;
let currentAvatarNames = ["Rama"];
let currentAvatarProfiles = [dashavatara.find(item => item.name === "Rama")];
let latestSettings = null;
let providerDraft = { provider: null, model: null, dirty: false };
let packageTemplateCache = [];
let screenStream = null;
let screenRecorder = null;
let screenChunks = [];
let screenRecordings = [];
let latestCabinet = null;
let latestPrana = null;
let brainEventSource = null;
let brainRefreshTimer = null;
let synthVoices = [];
let lastChosenVoiceName = "";
let recognitionActive = false;
let recognitionStarting = false;
let lastRecognitionError = "";
let voicePrefs = {
  voice_profile: "sovereign_female",
  language: "en-IN",
  rate: 0.94,
  pitch: 1.08,
  engine: "browser_builtin_female"
};

const $ = id => document.getElementById(id);

function titleAvatar(name) {
  const safe = String(name || "");
  return safe.charAt(0).toUpperCase() + safe.slice(1).toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.style.display = "block";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.style.display = "none";
  }, 3200);
}

function updateListeningState(message = "") {
  if (!$("listeningState")) return;
  if (message) {
    $("listeningState").textContent = message;
    return;
  }
  if (!listening) {
    $("listeningState").textContent = "Listening is disabled until you enable it.";
    return;
  }
  if (recognitionActive) {
    $("listeningState").textContent = "Microphone is live. Speak naturally and Leazy will process direct voice commands.";
    return;
  }
  if (recognitionStarting) {
    $("listeningState").textContent = "Starting microphone access for direct voice control...";
    return;
  }
  if (lastRecognitionError) {
    $("listeningState").textContent = `Voice wake is enabled, but browser listening is blocked: ${lastRecognitionError}. Allow microphone access and enable listening again.`;
    return;
  }
  $("listeningState").textContent = "Voice wake is enabled. If the browser stopped listening, enable it again to restore live command mode.";
}

function currentWorkspace() {
  const activePanel = document.querySelector(".tab-panel.active")?.id || "panel-bridge";
  return activePanel.replace("panel-", "");
}

function createParticles(count = 24, color = "rgba(241,202,107,.9)") {
  const centerX = window.innerWidth * 0.5;
  const centerY = window.innerHeight * 0.55;
  for (let i = 0; i < count; i += 1) {
    const item = document.createElement("div");
    item.className = "particle";
    item.style.left = centerX + "px";
    item.style.top = centerY + "px";
    item.style.background = color;
    item.style.setProperty("--dx", (Math.random() * 320 - 160) + "px");
    item.style.setProperty("--dy", (Math.random() * 280 - 140) + "px");
    document.body.appendChild(item);
    setTimeout(() => item.remove(), 1800);
  }
}

function flareHridaya(scale = 1.12) {
  const core = $("hridayaCore");
  if (!core) return;
  core.style.transform = `scale(${scale})`;
  core.style.boxShadow = "0 0 70px rgba(255,107,138,.52), 0 0 130px rgba(193,161,255,.42)";
  clearTimeout(core._timer);
  core._timer = setTimeout(() => {
    core.style.transform = "";
    core.style.boxShadow = "";
  }, 520);
}

function refreshSpeechVoices() {
  if (!("speechSynthesis" in window)) return [];
  synthVoices = window.speechSynthesis.getVoices() || [];
  return synthVoices;
}

function voicePreferenceLabel(profile) {
  const labels = {
    sovereign_female: "Sovereign Female",
    warm_guide: "Warm Guide",
    strategic_female: "Strategic Female",
    neutral: "Neutral"
  };
  return labels[profile] || "Sovereign Female";
}

function pickSpeechVoice() {
  if (!("speechSynthesis" in window)) return null;
  const voices = refreshSpeechVoices();
  if (!voices.length) return null;
  const language = String(voicePrefs.language || "en-IN").toLowerCase();
  const wantsHindi = language.startsWith("hi");
  const feminineMarkers = ["female", "woman", "zira", "aria", "samantha", "hazel", "natasha", "raveena", "heera", "priya", "veena"];
  const strategicMarkers = ["aria", "zira", "neural", "samantha"];
  const warmMarkers = ["samantha", "hazel", "veena", "karen", "susan"];
  const preferredMarkers = voicePrefs.voice_profile === "strategic_female" ? strategicMarkers : voicePrefs.voice_profile === "warm_guide" ? warmMarkers : feminineMarkers;
  const filtered = voices.filter(voice => voice.lang?.toLowerCase().startsWith(language.slice(0, 2)));
  const candidates = filtered.length ? filtered : voices;
  const exact = candidates.find(voice => preferredMarkers.some(marker => voice.name.toLowerCase().includes(marker)));
  if (exact) return exact;
  if (wantsHindi) {
    const hindi = candidates.find(voice => voice.lang?.toLowerCase().startsWith("hi"));
    if (hindi) return hindi;
  }
  const englishIndian = candidates.find(voice => voice.lang?.toLowerCase().startsWith("en-in"));
  if (englishIndian) return englishIndian;
  return candidates[0] || null;
}

function speak(text) {
  if (!("speechSynthesis" in window) || !text) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = Number(voicePrefs.rate || 0.94);
  utter.pitch = Number(voicePrefs.pitch || 1.08);
  utter.lang = voicePrefs.language || "en-IN";
  const voice = pickSpeechVoice();
  if (voice) {
    utter.voice = voice;
    utter.lang = voice.lang || utter.lang;
    lastChosenVoiceName = `${voice.name} (${voice.lang})`;
  } else {
    lastChosenVoiceName = "Default browser voice";
  }
  if ($("voiceSelectedName")) {
    $("voiceSelectedName").textContent = `Built-in voice: ${lastChosenVoiceName}`;
  }
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
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

async function apiForm(path, formData, options = {}) {
  const response = await fetch(path, {
    method: "POST",
    body: formData,
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

async function loadVoiceRuntimeStatus() {
  try {
    const data = await api("/api/voice/runtime/status");
    if ($("voiceRuntimeHeadline")) {
      $("voiceRuntimeHeadline").textContent = data.headline || "Local voice runtime ready.";
    }
    if ($("voiceRuntimeNote")) {
      const gpu = data.gpu?.label || "CPU";
      $("voiceRuntimeNote").textContent = `STT ${data.stt_engine || "faster_whisper"} (${data.whisper_model || "base"}) | VAD ${data.vad_engine || "silero_vad"} | TTS ${data.tts_engine || "browser_fallback"} | GPU ${gpu} | Streaming ${data.streaming_enabled ? "on" : "off"}.`;
    }
  } catch (error) {
    if ($("voiceRuntimeHeadline")) {
      $("voiceRuntimeHeadline").textContent = "Local voice runtime is not ready yet.";
    }
    if ($("voiceRuntimeNote")) {
      $("voiceRuntimeNote").textContent = error.message || "Install the local voice dependencies and restart the backend.";
    }
  }
}

function selectedVoiceClip() {
  return $("voiceClipFile")?.files?.[0] || null;
}

async function transcribeVoiceClip() {
  const file = selectedVoiceClip();
  if (!file) {
    toast("Choose an audio clip first.");
    return;
  }
  if ($("voiceRuntimeResult")) {
    $("voiceRuntimeResult").textContent = "Transcribing locally with Whisper...";
  }
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", voicePrefs.language || "en-IN");
    const data = await apiForm("/api/voice/runtime/transcribe", formData);
    if ($("voiceRuntimeResult")) {
      $("voiceRuntimeResult").textContent = `Transcript:\n${data.transcript || "No speech detected."}`;
    }
  } catch (error) {
    if ($("voiceRuntimeResult")) {
      $("voiceRuntimeResult").textContent = `Transcription failed: ${error.message}`;
    }
  }
}

async function runLocalVoiceLoop() {
  const file = selectedVoiceClip();
  if (!file) {
    toast("Choose an audio clip first.");
    return;
  }
  if ($("voiceRuntimeResult")) {
    $("voiceRuntimeResult").textContent = "Running local voice loop: capture -> transcribe -> think -> synthesize...";
  }
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", voicePrefs.language || "en-IN");
    formData.append("mode", "direct");
    formData.append("synthesize", "true");
    const data = await apiForm("/api/voice/runtime/respond", formData);
    const transcript = data.transcript || "No speech detected.";
    const response = data.wake?.response || "No spoken reply generated.";
    if ($("voiceRuntimeResult")) {
      $("voiceRuntimeResult").textContent = `Transcript:\n${transcript}\n\nResponse:\n${response}`;
    }
    if (data.tts?.audio_url) {
      try {
        const audio = new Audio(data.tts.audio_url);
        await audio.play();
      } catch (playbackError) {
        speak(response);
      }
    } else {
      speak(response);
    }
    await Promise.all([loadVoiceStatus(), loadVoiceRuntimeStatus(), loadBrainStatus(), loadMotherMonitor()]).catch(() => {});
  } catch (error) {
    if ($("voiceRuntimeResult")) {
      $("voiceRuntimeResult").textContent = `Local voice loop failed: ${error.message}`;
    }
  }
}

function renderTabs() {
  $("tabs").innerHTML = panels.map(panel => `<button class="nav-btn ${panel.id === "bridge" ? "active" : ""}" data-panel="${panel.id}">${panel.label}</button>`).join("");
  document.querySelectorAll(".nav-btn").forEach(button => {
    button.addEventListener("click", () => showPanel(button.dataset.panel));
  });
}

function normalizePanelId(id) {
  const map = {
    cabinet: "cabinet",
    prime: "cabinet",
    minister: "cabinet",
    "prime-minister": "cabinet",
    monitor: "monitor",
    monitoring: "monitor",
    nervous: "monitor",
    prana: "prana",
    "prana-nadi": "prana",
    hridaya: "prana",
    systems: "systems",
    system: "systems",
    domains: "systems",
    vishnu: "avatars",
    avatar: "avatars",
    avatars: "avatars",
    praapti: "praapti",
    nirmaan: "nirmaan",
    bridge: "bridge",
    akshaya: "akshaya",
    voice: "voice",
    settings: "settings",
    portals: "portals"
  };
  return map[String(id || "").toLowerCase()] || "bridge";
}

function showPanel(id, updateHash = true) {
  const safeId = normalizePanelId(id);
  document.querySelectorAll(".tab-panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === "panel-" + safeId);
  });
  document.querySelectorAll(".nav-btn").forEach(button => {
    button.classList.toggle("active", button.dataset.panel === safeId);
  });
  const target = $("panel-" + safeId);
  if (updateHash) {
    if (history.replaceState) {
      history.replaceState(null, "", "#" + safeId);
    } else {
      window.location.hash = safeId;
    }
  }
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function openGuidanceLayer(id) {
  showPanel(id);
  createParticles(20, "rgba(135,223,255,.9)");
}

function renderSceneButtons() {
  $("sceneButtons").innerHTML = skyScenes.map((scene, index) => `<button class="scene-btn ${index === currentSceneIndex ? "active" : ""}" onclick="setScene(${index})"><span>${scene.label}</span><span>${scene.file.replace(".mp4", "")}</span></button>`).join("");
}

function setScene(index) {
  currentSceneIndex = (index + skyScenes.length) % skyScenes.length;
  const scene = skyScenes[currentSceneIndex];
  const video = $("skyVideo");
  video.src = "/frontend-assets/media/" + scene.file;
  video.play().catch(() => {});
  renderSceneButtons();
}

function cycleScene() {
  setScene(currentSceneIndex + 1);
}

function avatarLookup(name) {
  return dashavatara.find(item => item.name.toLowerCase() === String(name || "").toLowerCase());
}

function setOrbMode(names) {
  currentAvatarNames = (names && names.length ? names : ["Rama"]).map(titleAvatar);
  currentAvatarProfiles = currentAvatarNames.map(avatarLookup).filter(Boolean);
  const lead = currentAvatarProfiles[0] || avatarLookup("Rama");
  $("orbEmoji").textContent = lead.emoji;
  $("orbSub").textContent = currentAvatarNames.join(" + ") + " Protocol";
  const orb = $("orb");
  orb.style.background = `radial-gradient(circle at 35% 35%, ${lead.color}, #2d235f 58%, #070b14 100%)`;
  orb.style.boxShadow = `0 0 44px ${lead.color}55, 0 0 90px rgba(241,202,107,.16)`;
}

function updateActiveAvatarCards(profiles) {
  const safeProfiles = (profiles && profiles.length ? profiles : [avatarLookup("Rama")]).map(item => ({
    ...item,
    name: titleAvatar(item.name || "Rama")
  }));
  const lead = safeProfiles[0] || avatarLookup("Rama");
  const names = safeProfiles.map(item => item.name);
  $("activeAvatarEmpire").textContent = names.join(" + ") + " is currently steering the empire.";
  $("activeAvatarBadges").innerHTML = names.map(name => `<span class="badge">${name}</span>`).join("");
  $("activeAvatarMantra").textContent = lead.mantra;
  $("avatarStatusTitle").textContent = names.join(" + ") + " Mode Active";
  $("avatarStatusDesc").innerHTML = `<strong>${lead.power}</strong><br>${lead.desc}`;
  $("avatarStatusMantra").textContent = lead.mantra;
  setOrbMode(names);
}

function renderBrainPillars(pillars) {
  $("brainPillars").innerHTML = (pillars || []).map(pillar => `
    <div class="pillar-card">
      <div class="pillar-head">
        <div>
          <strong>${pillar.label}</strong>
          <div class="muted">${pillar.id.toUpperCase()}</div>
        </div>
        <img src="/frontend-assets/art/${pillar.icon}" alt="${pillar.label}">
      </div>
      <div class="pillar-score">${pillar.score}%</div>
      <div class="pillar-meter"><span style="width:${pillar.score}%"></span></div>
      <p>${pillar.summary}</p>
    </div>
  `).join("");
}

function renderRecommendations(items) {
  const rows = items || [];
  const dynamic = rows.map(item => `<div class="recommendation"><strong>${item.title}</strong><p>${item.action}</p><div class="button-row" style="margin-top:10px"><button class="mini-btn" onclick="openGuidanceLayer('${item.layer}')">Open ${titleAvatar(normalizePanelId(item.layer))}</button></div></div>`).join("");
  const shortcuts = `<div class="recommendation"><strong>Quick Access</strong><p>Open the core workspaces directly whenever you want to move without waiting for a recommendation.</p><div class="button-row" style="margin-top:10px"><button class="mini-btn" onclick="openGuidanceLayer('cabinet')">Open Cabinet</button><button class="mini-btn" onclick="openGuidanceLayer('praapti')">Open Praapti</button><button class="mini-btn" onclick="openGuidanceLayer('nirmaan')">Open Nirmaan</button><button class="mini-btn" onclick="openGuidanceLayer('avatars')">Open Avatars</button></div></div>`;
  $("brainRecommendations").innerHTML = (dynamic || `<div class="empty-note">The brain has no queued guidance yet.</div>`) + shortcuts;
}

function renderMetrics(data) {
  const metrics = [
    ["Praapti Hunts Today", data.metrics.praapti_hunts_today],
    ["Projected Revenue", data.metrics.projected_revenue_inr + " Cr"],
    ["Army Active", data.metrics.army_active],
    ["Nirmaan Active", data.metrics.nirmaan_active],
    ["Collective Insights", data.metrics.collective_insights],
    ["Vault Items", data.metrics.vault_items],
    ["Packages Active", data.metrics.packages_active || 0],
    ["Secretaries", data.metrics.active_secretaries || 0],
    ["Provider", data.provider || "built-in"]
  ];
  $("empireMetrics").innerHTML = metrics.map(metric => `<div class="metric-card"><span>${metric[0]}</span><strong>${metric[1]}</strong></div>`).join("");
}

function renderCabinetSummary(data) {
  latestCabinet = data || {};
  const pm = latestCabinet.prime_minister || {};
  const revenue = latestCabinet.revenue_board || {};
  const storage = latestCabinet.quantum_storage || {};
  const secretaries = latestCabinet.secretaries || [];
  const missionLog = latestCabinet.mission_log || [];

  if ($("primeMinisterStatus")) {
    $("primeMinisterStatus").textContent = `${pm.name || "Prime Minister"} • ${pm.status || "governing"}`;
  }
  if ($("primeMinisterFocus")) {
    $("primeMinisterFocus").textContent = pm.objective || "No Prime Minister mandate has been set yet.";
  }
  if ($("primeMinisterStats")) {
    $("primeMinisterStats").textContent = `${pm.active_secretaries || secretaries.length || 0} secretaries active`;
  }
  if ($("primeMinisterLoop")) {
    $("primeMinisterLoop").textContent = `${pm.enabled ? "Loop live" : "Loop paused"} • Revenue focus ₹${revenue.projected_revenue_inr || 0} Cr • Next cycle ${pm.next_cycle_at || "pending"}`;
  }
  if ($("pmObjective") && !document.activeElement?.isSameNode($("pmObjective"))) {
    $("pmObjective").value = pm.objective || "";
  }
  if ($("pmToggleBtn")) {
    $("pmToggleBtn").textContent = pm.enabled ? "Pause Loop" : "Resume Loop";
  }
  if ($("pmReport")) {
    $("pmReport").textContent = latestCabinet.latest_report || "No cabinet report yet.";
  }
  if ($("pmSecretaryCount")) {
    $("pmSecretaryCount").textContent = `${pm.active_secretaries || secretaries.length || 0} active`;
  }
  if ($("pmStorageTitle")) {
    $("pmStorageTitle").textContent = `${storage.mode || "elastic preservation"} • ${storage.seal || "Matsya + Kurma"}`;
  }
  if ($("pmStorageSummary")) {
    $("pmStorageSummary").textContent = `Manager ${storage.manager || "Prime Minister Cabinet"}. Accuracy mode ${storage.accuracy_mode || "structured summaries"}. Preserved items ${storage.items_preserved || 0}. Footprint ${storage.footprint_kb || 0} KB.`;
  }
  if ($("pmRevenueTitle")) {
    $("pmRevenueTitle").textContent = `Revenue focus • ₹${revenue.projected_revenue_inr || 0} Cr projected`;
  }
  if ($("pmRevenueSummary")) {
    $("pmRevenueSummary").textContent = `Hunts today ${revenue.hunts_today || 0}, packages ${revenue.packages_active || 0}, proposals ${revenue.pending_proposals || 0}. Order: ${revenue.priority_order || "Awaiting mandate."}`;
  }
  if ($("pmSecretaryGrid")) {
    $("pmSecretaryGrid").innerHTML = secretaries.length ? secretaries.map(secretary => `
      <div class="secretary-card">
        <div class="secretary-head">
          <div>
            <strong>${secretary.name}</strong>
            <div class="secretary-lane">${secretary.lane}</div>
          </div>
          <span class="secretary-priority">${secretary.priority || 0}%</span>
        </div>
        <p>${secretary.brief || "Secretary brief unavailable."}</p>
        <div class="secretary-next"><strong>${secretary.status || "ready"}</strong><br>${secretary.next_move || "Await next order."}</div>
      </div>
    `).join("") : `<div class="empty-note">No secretary swarm loaded yet.</div>`;
  }
  if ($("pmMissionLog")) {
    $("pmMissionLog").innerHTML = missionLog.length ? missionLog.map(item => `
      <div class="proposal-card">
        <strong>${item.source || "manual"} cycle</strong>
        <p>${item.report || item.objective || "No report available."}</p>
        <div class="proposal-meta">${item.created_at || "now"} • ${(item.top_secretaries || []).join(" • ")}</div>
      </div>
    `).join("") : `<div class="empty-note">No Prime Minister cycles yet. Run the first cycle to seed the cabinet.</div>`;
  }
}

function renderMotherMonitor(data) {
  const alerts = data.alerts || [];
  const reports = data.reports || [];
  const nervous = data.nervous_system || {};
  const memory = data.memory_audit || {};
  const repairEngine = data.auto_repair || nervous.auto_repair || {};
  const domains = data.domains || [];
  const telemetry = nervous.telemetry || {};
  const carbon = nervous.carbon_protocol || {};
  const intelligence = nervous.component_intelligence || {};
  const intelligenceSummary = intelligence.summary || {};
  const organSystems = nervous.organ_systems || [];
  const cellClusters = nervous.cell_clusters || [];
  const reflexArcs = nervous.reflex_arcs || [];
  const hierarchy = nervous.hierarchy || {};
  const hierarchySummary = hierarchy.summary || {};
  const hierarchyBrains = hierarchy.brains || [];
  const permissionRelays = hierarchy.permission_relays || [];
  const motivationStreams = hierarchy.motivation_streams || [];
  const brainLookup = new Map(hierarchyBrains.map(item => [item.id, item.name]));
  const prana = data.prana_nadi || nervous.prana_nadi || null;

  if ($("monitorStatus")) {
    $("monitorStatus").textContent = `Heartbeat ${data.heartbeat_ms || 0} ms with ${hierarchySummary.total_brains || 0} brains, ${domains.length} domains, ${telemetry.organs_online || 0} organs, ${telemetry.cells_active || 0} active cells, ${carbon.allotrope || "carbon-seed"} active, and repair engine ${repairEngine.status || "ready"}`;
  }
  if ($("monitorSummary")) {
    $("monitorSummary").textContent = `Last scan ${data.last_scan_at || "unknown"}. Mother brain is tracking ${hierarchySummary.total_brains || 0} brains across ${hierarchySummary.layers || 0} layers, ${data.engines?.length || 0} engines, ${organSystems.length || 0} organ systems, ${nervous.transmissions?.length || 0} live transmissions, and Carbon bond integrity ${carbon.bond_integrity || 0}%.`;
  }
  if ($("systemsStatus")) {
    $("systemsStatus").textContent = `${domains.length} operational domains, ${hierarchySummary.total_brains || 0} brains, and ${organSystems.length || 0} organ systems are connected`;
  }
  if ($("systemsSummary")) {
    const leaders = domains.slice(0, 3).map(domain => domain.lead).join(", ");
    $("systemsSummary").textContent = leaders ? `Lead agents: ${leaders}. Mother children ${hierarchySummary.mother_children || 0}. Signal integrity ${telemetry.signal_integrity || 0}%.` : "Operational leaders will appear here.";
  }
  if ($("monitorStrip")) {
    const strip = [
      ["Heartbeat", `${data.heartbeat_ms || 0} ms`],
      ["Brains", hierarchySummary.total_brains || 0],
      ["Domains", domains.length],
      ["Layers", hierarchySummary.layers || 0],
      ["Organs", telemetry.organs_online || 0],
      ["Cells", telemetry.cells_active || 0],
      ["Integrity", `${telemetry.signal_integrity || 0}%`],
      ["Circulation", `${telemetry.circulation_index || 0}%`],
      ["Relays", hierarchySummary.permission_relays || 0],
      ["Bond", `${carbon.bond_integrity || 0}%`],
      ["Alerts", alerts.length],
      ["Footprint", `${memory.footprint_kb || 0} KB`],
      ["Repair", repairEngine.status || "ready"]
    ];
    $("monitorStrip").innerHTML = strip.map(item => `<div class="metric-card"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("monitorSummaryBox")) {
    $("monitorSummaryBox").textContent =
      `Mother: ${nervous.mother?.name || "Ishani Core"}\n` +
      `Last scan: ${data.last_scan_at || "unknown"}\n` +
      `State file: ${nervous.mother?.state_file || memory.state_file || "unknown"}\n\n` +
      `The nervous system currently tracks ${nervous.nodes?.length || 0} nodes, ${nervous.links?.length || 0} links, ${nervous.transmissions?.length || 0} recent transmissions, and ${telemetry.cells_active || 0} active cells across ${organSystems.length || 0} organ systems.\n\n` +
      `Hierarchy: ${hierarchySummary.total_brains || 0} brains across ${hierarchySummary.layers || 0} layers with ${hierarchySummary.permission_relays || 0} permission relays. Mother governs ${hierarchySummary.mother_children || 0} direct child brains.\n\n` +
      `Component intelligence: ${intelligenceSummary.atoms || 0} atoms, ${intelligenceSummary.molecules || 0} molecules, ${intelligenceSummary.agents || 0} agents, ${intelligenceSummary.tools || 0} tools, ${intelligenceSummary.thinking_units || 0} thinking units.\n\n` +
      `Carbon Protocol: ${carbon.allotrope || "carbon-seed"} • bond integrity ${carbon.bond_integrity || 0}% • ${carbon.signals_per_minute || 0} signals/minute.\n\n` +
      `Auto Repair: ${repairEngine.status || "ready"} • ${repairEngine.safe_repairs_applied || 0} safe repairs applied • ${repairEngine.issue_count || 0} active issue(s).`;
  }
  if ($("memoryAuditBox")) {
    const repairText = (memory.repairs || []).map(item => `- ${item}`).join("\n");
    const issueText = (memory.issues || []).length ? (memory.issues || []).map(item => `- ${item}`).join("\n") : "- No memory faults detected.";
    $("memoryAuditBox").textContent =
      `Guardian: ${memory.guardian || "eternal preservation"}\n` +
      `Seal: ${memory.seal || "Matsya + Kurma"}\n` +
      `Mode: ${memory.mode || "elastic preservation"}\n` +
      `Accuracy: ${memory.accuracy_mode || "structured"}\n` +
      `Footprint: ${memory.footprint_kb || 0} KB\n` +
      `Archive cycles: ${memory.archive_cycles || 0}\n` +
      `Last guardian cycle: ${memory.last_guardian_cycle || "unknown"}\n\n` +
      `Repairs:\n${repairText}\n\nIssues:\n${issueText}`;
  }
  if ($("monitorRepairBox")) {
    const issueText = (repairEngine.issues || []).length
      ? (repairEngine.issues || []).map(item => `- ${item}`).join("\n")
      : "- No active repair issues.";
    $("monitorRepairBox").textContent =
      `Status: ${repairEngine.status || "ready"}\n` +
      `Last self-check: ${repairEngine.last_check_at || "not yet"}\n` +
      `Last repair: ${repairEngine.last_repair_at || "none"}\n` +
      `Safe repairs applied: ${repairEngine.safe_repairs_applied || 0}\n` +
      `Health score: ${repairEngine.uiux?.health_score || 100}%\n` +
      `Runtime accessibility overlay: ${repairEngine.uiux?.runtime_accessibility_overlay ? "active" : "missing"}\n\n` +
      `${repairEngine.last_report || "Safe self-check layer is ready."}\n\n` +
      `Issues:\n${issueText}`;
  }
  if ($("monitorAlerts")) {
    $("monitorAlerts").innerHTML = alerts.length ? alerts.map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.summary)}</p>
        <div class="proposal-meta">${escapeHtml(item.level || "info")}</div>
      </div>
    `).join("") : `<div class="empty-note">No alerts right now. The mother brain sees a stable relay chain.</div>`;
  }
  if ($("monitorReports")) {
    $("monitorReports").innerHTML = reports.length ? reports.map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.engine || item.name || "Engine Report")}</strong>
        <p>${escapeHtml(item.summary || "No summary yet.")}</p>
        <div class="proposal-meta">${escapeHtml(item.status || "live")} - ${escapeHtml(item.created_at || data.last_scan_at || "now")}</div>
      </div>
    `).join("") : `<div class="empty-note">No engine reports yet.</div>`;
  }
  if ($("nervousNodes")) {
    $("nervousNodes").innerHTML = (nervous.nodes || []).length ? nervous.nodes.map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.name)}</strong>
        <p>${escapeHtml(item.kind)} - ${escapeHtml(item.status)}</p>
      </div>
    `).join("") : `<div class="empty-note">No nervous-system nodes available yet.</div>`;
  }
  if ($("nervousFlow")) {
    const flowRows = nervous.transmissions?.length ? nervous.transmissions : nervous.links || [];
    $("nervousFlow").innerHTML = flowRows.length ? flowRows.map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.from)} -> ${escapeHtml(item.to)}</strong>
        <p>${escapeHtml(item.message || item.label || "Flow registered.")}</p>
        <div class="proposal-meta">${escapeHtml(item.created_at || data.last_scan_at || "live")}</div>
      </div>
    `).join("") : `<div class="empty-note">No flow chain has been recorded yet.</div>`;
  }
  if ($("brainHierarchyList")) {
    $("brainHierarchyList").innerHTML = hierarchyBrains.length ? hierarchyBrains.slice(0, 16).map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.name)}</strong>
        <p>${escapeHtml(item.role_title || item.authority)}</p>
        <div class="proposal-meta">${item.layer} • ${item.status} • parent ${brainLookup.get(item.parent_id) || "none"} • ${item.children_count || 0} child brains</div>
        <p>Mission: ${escapeHtml(item.mission || item.assigned_task || "Awaiting assignment.")}</p>
        <p>NLP Status: ${escapeHtml(item.nlp_status || "embedded")} • ${(item.nlp_capabilities || []).slice(0, 2).join(" / ") || "language stack pending"}</p>
        <p>Responsibilities: ${(item.responsibilities || []).slice(0, 2).join(" • ") || "Awaiting doctrine."}</p>
      </div>
    `).join("") : `<div class="empty-note">No hierarchy map has been generated yet.</div>`;
  }
  if ($("permissionRelayList")) {
    $("permissionRelayList").innerHTML = permissionRelays.length ? permissionRelays.slice(0, 18).map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.from_name || item.from)} -> ${escapeHtml(item.to_name || item.to)}</strong>
        <p>${escapeHtml(item.reason || "Permission relay registered.")}</p>
        <div class="proposal-meta">${item.permission || "relay"} • ${item.status || "live"}</div>
      </div>
    `).join("") : `<div class="empty-note">No permission relay has been mapped yet.</div>`;
  }
  if ($("brainMotivationGrid")) {
    $("brainMotivationGrid").innerHTML = motivationStreams.length ? motivationStreams.map(item => `
      <div class="system-card">
        <strong>${escapeHtml(item.target)}</strong>
        <p>${escapeHtml(item.message)}</p>
        <div class="system-meta">
          <span>${escapeHtml(item.source)}</span>
          <span>${escapeHtml(item.focus)}</span>
        </div>
      </div>
    `).join("") : `<div class="empty-note">No motivation streams are active yet.</div>`;
  }
  if ($("organSystems")) {
    $("organSystems").innerHTML = organSystems.length ? organSystems.map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.name)}</strong>
        <p>${escapeHtml(item.role)}</p>
        <div class="proposal-meta">${escapeHtml(item.status)} - load ${escapeHtml(item.load || 0)}%</div>
      </div>
    `).join("") : `<div class="empty-note">No organ systems mapped yet.</div>`;
  }
  if ($("cellClusters")) {
    $("cellClusters").innerHTML = cellClusters.length ? cellClusters.map(item => `
      <div class="proposal-card">
        <strong>${escapeHtml(item.name)}</strong>
        <p>${escapeHtml(item.signal)}</p>
        <div class="proposal-meta">${escapeHtml(item.identity)} - ${escapeHtml(item.status)} - ${escapeHtml(item.cell_count || 0)} cells</div>
      </div>
    `).join("") : `<div class="empty-note">No cell clusters mapped yet.</div>`;
  }
  if ($("reflexArcs")) {
    $("reflexArcs").innerHTML = reflexArcs.length ? reflexArcs.map(item => `
      <div class="system-card">
        <strong>${escapeHtml(item.trigger)}</strong>
        <p>${escapeHtml(item.response)}</p>
      </div>
    `).join("") : `<div class="empty-note">No reflex arcs loaded yet.</div>`;
  }
  if ($("systemsGrid")) {
    $("systemsGrid").innerHTML = domains.length ? domains.map(domain => `
      <div class="system-card">
        <strong>${escapeHtml(domain.name)}</strong>
        <div class="system-meta">
          <span>${escapeHtml(domain.lead)}</span>
          <span>${escapeHtml(domain.status)}</span>
          <span>${escapeHtml(domain.priority || 0)}%</span>
        </div>
        <p>${escapeHtml(domain.purpose)}</p>
        <p>${escapeHtml(domain.latest_signal)}</p>
        <div class="proposal-meta">${escapeHtml(domain.metric || "")}</div>
      </div>
    `).join("") : `<div class="empty-note">No domain lattice loaded yet.</div>`;
  }
  if (prana) {
    renderPranaNadi(prana);
  }
}

function drawPranaNadi() {
  const canvas = $("nadiCanvas");
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);
  const tick = Date.now() / 380;
  const midX = width / 2;
  const pulse = latestPrana?.intensity || 72;
  const glow = 0.14 + pulse / 220;

  const gradient = ctx.createRadialGradient(midX, height * 0.5, 18, midX, height * 0.5, height * 0.54);
  gradient.addColorStop(0, "rgba(255,107,138,0.35)");
  gradient.addColorStop(0.55, "rgba(193,161,255,0.18)");
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const drawChannel = (offset, color, wobble, lineWidth) => {
    ctx.beginPath();
    for (let y = 20; y < height - 20; y += 8) {
      const wave = Math.sin((y / 42) + tick * wobble) * offset;
      const x = midX + wave;
      if (y === 20) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.shadowBlur = 18;
    ctx.shadowColor = color;
    ctx.stroke();
    ctx.shadowBlur = 0;
  };

  drawChannel(0, `rgba(255,215,168,${Math.min(.92, glow + .45)})`, 0, 4.4);
  drawChannel(54, `rgba(255,107,138,${Math.min(.82, glow + .3)})`, 1.15, 2.6);
  drawChannel(-54, `rgba(193,161,255,${Math.min(.82, glow + .3)})`, 1.05, 2.6);

  ctx.strokeStyle = "rgba(135,223,255,0.22)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 18; i += 1) {
    const y = 28 + i * 20;
    ctx.beginPath();
    ctx.moveTo(midX - 180, y);
    ctx.quadraticCurveTo(midX, y + Math.sin(tick + i) * 18, midX + 180, y);
    ctx.stroke();
  }

  const orbRadius = 34 + Math.sin(tick * 1.7) * 5;
  ctx.beginPath();
  ctx.arc(midX, height * 0.52, orbRadius, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255,155,189,0.28)";
  ctx.fill();
  ctx.strokeStyle = "rgba(255,230,242,0.8)";
  ctx.lineWidth = 2;
  ctx.stroke();
}

function renderPranaNadi(data) {
  latestPrana = data;
  if ($("pranaMetrics")) {
    const metrics = [
      ["Pulse", data.pulse || "alive"],
      ["Intensity", `${data.intensity || 0}%`],
      ["Nadis", (data.nadis_total || 0).toLocaleString()],
      ["Heartbeat", `${data.heartbeat_ms || 0} ms`],
      ["Sync Glow", `${data.hridaya?.glow || 0}%`],
      ["Sync", `${data.hridaya?.sync || 0}%`]
    ];
    $("pranaMetrics").innerHTML = metrics.map(item => `<div class="metric-card"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join("");
  }
  if ($("pranaMessage")) {
    $("pranaMessage").textContent =
      `${data.message || "Prana current active."}\n\n` +
      `${data.hridaya?.name || "Sovereign Sync Core"}: ${data.hridaya?.message || "Where command becomes system-wide motion."}\n` +
      `Mantra: ${data.hridaya?.mantra || "Sankalpa Aikyam"}`;
  }
  if ($("pranaChannels")) {
    $("pranaChannels").innerHTML = (data.channels || []).map(channel => `
      <div class="proposal-card">
        <strong>${channel.name}</strong>
        <p>${channel.role}</p>
        <div class="proposal-meta">${channel.strength || 0}% strength</div>
      </div>
    `).join("");
  }
  if ($("hridayaStatus")) {
    $("hridayaStatus").textContent = `${data.hridaya?.name || "Sovereign Sync Core"} • ${data.hridaya?.sync || 0}% sync`;
  }
  if ($("hridayaCopy")) {
    $("hridayaCopy").textContent = `${data.hridaya?.message || "Where command becomes system-wide motion."} ${data.hridaya?.mantra || ""}`;
  }
  flareHridaya(1.08 + ((data.hridaya?.glow || 70) / 1000));
  drawPranaNadi();
}

function renderSwarmAgents(agents) {
  $("swarmAgents").innerHTML = (agents || []).map(agent => `<div class="agent-card"><strong>${agent.name}</strong><span>${agent.role}</span><div class="agent-status">${agent.status}</div></div>`).join("");
}

function renderAvatarHistory(history) {
  const rows = history || [];
  $("avatarHistory").innerHTML = rows.length ? rows.map(item => `<div class="history-item"><strong>${(item.avatars || []).map(titleAvatar).join(" + ")}</strong><p>${item.command || "No command logged."}</p></div>`).join("") : `<div class="empty-note">The wheel is waiting for the next channel.</div>`;
}

function renderDashavataraWheel(activeNames = currentAvatarNames) {
  const activeSet = new Set((activeNames || []).map(name => String(name).toLowerCase()));
  const shell = $("avatarWheel");
  shell.querySelectorAll(".avatar-node").forEach(node => node.remove());
  const size = Math.max(520, Math.min(shell.clientWidth || 760, 760));
  const radius = Math.max(170, Math.min(280, size * 0.37));
  const centerX = size / 2;
  const centerY = (shell.clientHeight || size) / 2;
  dashavatara.forEach((avatar, index) => {
    const angle = ((Math.PI * 2) / dashavatara.length) * index - Math.PI / 2;
    const x = centerX + Math.cos(angle) * radius;
    const y = centerY + Math.sin(angle) * radius;
    const node = document.createElement("div");
    node.className = "avatar-node" + (activeSet.has(avatar.name.toLowerCase()) ? " active" : "");
    node.style.left = x + "px";
    node.style.top = y + "px";
    node.style.color = avatar.color;
    node.innerHTML = `<div class="avatar-orb" style="background:radial-gradient(circle at 35% 35%, ${avatar.color}66, rgba(255,255,255,.04) 72%)">${avatar.emoji}</div><div class="avatar-name">${avatar.name}</div>`;
    node.addEventListener("click", () => channelAvatar(avatar.name));
    shell.appendChild(node);
  });
}

function renderAvatarGuideGrid(activeNames = currentAvatarNames) {
  const activeSet = new Set((activeNames || []).map(name => String(name).toLowerCase()));
  $("avatarGuideGrid").innerHTML = dashavatara.map(avatar => `
    <div class="guide-card ${activeSet.has(avatar.name.toLowerCase()) ? "active" : ""}">
      <div class="guide-head">
        <span class="guide-avatar-mark" style="color:${avatar.color}">${avatar.emoji}</span>
        <strong>${avatar.name}</strong>
      </div>
      <p><strong>${avatar.power}</strong><br>${avatar.desc}</p>
      <button class="mini-btn" onclick="channelAvatar('${avatar.name}')">Channel ${avatar.name}</button>
    </div>
  `).join("");
}

function renderEvolutionCycle(cycle) {
  $("brainCycle").innerHTML = (cycle || []).map(step => `
    <div class="cycle-card ${step.status}">
      <div class="cycle-top">
        <strong>${step.label}</strong>
        <span>${step.score}%</span>
      </div>
      <div class="cycle-status">${step.status}</div>
      <p>${step.summary}</p>
    </div>
  `).join("");
}

function appendBubble(type, text) {
  const bubble = document.createElement("div");
  bubble.className = "bubble " + type;
  bubble.textContent = text;
  $("orbLog").appendChild(bubble);
  $("orbLog").scrollTop = $("orbLog").scrollHeight;
}

function toggleCompanion() {
  $("orbDrawer").classList.toggle("open");
}

function hideOrbDock() {
  $("orbDock").classList.add("hidden");
  $("orbRestore").classList.add("show");
}

function showOrbDock() {
  $("orbDock").classList.remove("hidden");
  $("orbRestore").classList.remove("show");
}

async function loadBrainStatus() {
  const data = await api("/api/brain/status");
  $("identityChip").textContent = data.identity + " Core";
  $("creatorChip").textContent = data.creator_mode;
  $("heartbeatChip").textContent = "Heartbeat " + data.heartbeat.status;
  $("brainProviderChip").textContent = data.provider || "built-in";
  $("brainMode").textContent = data.mode + " Mode";
  const pm = data.prime_minister?.prime_minister || {};
  $("brainMessage").textContent = `Temperature ${data.temperature}. ${data.heartbeat.eternal_mode} preservation is active while ${data.mode.toLowerCase()} leads the next move. Prime Minister loop: ${pm.enabled ? "live" : "paused"} with ${pm.active_secretaries || 0} secretaries.`;
  $("coreLegendTitle").textContent = data.mode + " Brain";
  $("coreLegendCopy").textContent = `Pulse ${data.heartbeat.pulse}. Memory Guardian ${data.heartbeat.memory_guardian}.`;
  renderBrainPillars(data.pillars);
  renderRecommendations(data.recommendations);
  updateActiveAvatarCards(data.active_avatars);
  renderEvolutionCycle(data.evolution_cycle || []);
  renderAvatarGuideGrid((data.active_avatars || []).map(item => item.name));
}

async function loadPranaNadi() {
  const data = await api("/api/prana-nadi/pulse");
  renderPranaNadi(data);
  return data;
}

async function runBrainPulse() {
  const focus = $("brainFocus").value;
  const goal = $("brainGoal").value.trim() || "advance the empire with clarity and resilience";
  createParticles(44, "rgba(243,157,221,.9)");
  const data = await api("/api/brain/pulse", {
    method: "POST",
    body: JSON.stringify({ focus, goal })
  });
  $("brainPulseReport").textContent = data.report;
  flareHridaya(1.18);
  if (data.used_avatars) {
    setOrbMode(data.used_avatars.map(titleAvatar));
  }
  if (data.brain) {
    renderBrainPillars(data.brain.pillars || []);
    renderRecommendations(data.brain.recommendations || []);
    renderEvolutionCycle(data.brain.evolution_cycle || []);
  }
  speak("Brain pulse completed.");
  await Promise.all([loadBrainStatus(), loadEmpireDashboard(), loadVishnuStatus(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function loadEmpireDashboard() {
  const data = await api("/api/empire/dashboard");
  renderMetrics(data);
  renderSwarmAgents(data.swarm_agents);
  $("latestSwarm").textContent = data.latest_swarm_report || "No swarm mission has been run yet.";
  $("guardianInfo").textContent = `Memory Guardian ${data.memory_guardian.status}. Seal: ${data.memory_guardian.seal}. Vault items: ${data.memory_guardian.vault_items}. Conversation items: ${data.memory_guardian.conversation_items}.`;
  $("vaultGuardian").textContent = `Guardian ${data.memory_guardian.status}. State file: ${data.memory_guardian.state_file}. Seal: ${data.memory_guardian.seal}.`;
  $("protectionMeterFill").style.width = (data.metrics.vishnu_protection || 0) + "%";
  $("protectionLabel").textContent = `Protection meter at ${data.metrics.vishnu_protection || 0}%. ${data.creator_mode}.`;
  $("settingsSummaryTitle").textContent = `Provider ${data.provider || "built-in"} is active`;
  $("settingsSummaryText").textContent = `Packages ${data.metrics.packages_active || 0}, hunts ${data.metrics.praapti_hunts_today}, and vault items ${data.metrics.vault_items} are available across the empire.`;
  updateActiveAvatarCards(data.active_avatars || []);
  renderAvatarHistory(data.avatar_history || []);
  if (data.cabinet) {
    renderCabinetSummary(data.cabinet);
  }
}

async function loadCabinetStatus() {
  const data = await api("/api/cabinet/status");
  renderCabinetSummary(data);
  return data;
}

async function runPrimeMinisterCycle() {
  const objective = $("pmObjective")?.value.trim() || "";
  createParticles(58, "rgba(241,202,107,.95)");
  const data = await api("/api/cabinet/prime-minister", {
    method: "POST",
    body: JSON.stringify({
      objective: objective || "Generate revenue for TechBuzz Systems Pvt Ltd while protecting the core and improving delivery.",
      command: objective || "Coordinate the secretaries, protect the core, and compound revenue."
    })
  });
  renderCabinetSummary(data.cabinet || {});
  $("pmReport").textContent = data.report || "Prime Minister cycle completed.";
  if (data.used_avatars) {
    setOrbMode(data.used_avatars.map(titleAvatar));
  }
  toast(data.message || "Prime Minister cycle completed.");
  speak("Prime Minister cycle completed.");
  await Promise.all([loadBrainStatus(), loadEmpireDashboard(), loadVishnuStatus(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function togglePrimeMinisterLoop() {
  const nextEnabled = !(latestCabinet?.prime_minister?.enabled);
  const objective = $("pmObjective")?.value.trim() || latestCabinet?.prime_minister?.objective || "";
  const data = await api("/api/cabinet/toggle", {
    method: "POST",
    body: JSON.stringify({ enabled: nextEnabled, objective })
  });
  renderCabinetSummary(data.cabinet || {});
  toast(data.message || "Prime Minister loop updated.");
  await Promise.all([loadBrainStatus(), loadEmpireDashboard(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function triggerSwarmMission() {
  createParticles(52, "rgba(193,161,255,.9)");
  const data = await api("/api/swarm/mission", {
    method: "POST",
    body: JSON.stringify({ mission: "autonomous evolution across expand grow develop protect" })
  });
  $("latestSwarm").textContent = data.report || "Swarm mission complete.";
  if (data.used_avatars) {
    setOrbMode(data.used_avatars.map(titleAvatar));
  }
  speak("Swarm mission completed.");
  toast(data.status || "Swarm mission completed.");
  await Promise.all([loadEmpireDashboard(), loadBrainStatus(), loadVishnuStatus(), loadNirmaanProposals(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function loadVishnuStatus() {
  const data = await api("/api/vishnu/status");
  $("creatorModeText").textContent = `${data.identity} core is active. ${data.creator_mode}. Commands are prioritized quickly while preserving safety, legality, and runtime stability.`;
  updateActiveAvatarCards(data.active_avatars || []);
  renderDashavataraWheel((data.active_avatars || []).map(item => item.name));
  renderAvatarGuideGrid((data.active_avatars || []).map(item => item.name));
  renderAvatarHistory(data.history || []);
}

async function channelAvatar(name) {
  createParticles(68, "rgba(241,202,107,.95)");
  const data = await api("/api/vishnu/channel", {
    method: "POST",
    body: JSON.stringify({ avatar: name, command: "Channel " + name })
  });
  const names = (data.avatars || ["RAMA"]).map(titleAvatar);
  updateActiveAvatarCards((data.profiles || []).map(item => ({ ...item, name: titleAvatar(item.name) })));
  setOrbMode(names);
  toast(data.seal || "Avatar protocol active.");
  speak("Channel active.");
  await Promise.all([loadBrainStatus(), loadEmpireDashboard(), loadVishnuStatus(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function startPraaptiHunt() {
  const jobDescription = $("jdInput").value.trim();
  if (!jobDescription) {
    toast("Paste a job description first.");
    return;
  }
  createParticles(46, "rgba(241,202,107,.95)");
  $("praaptiNarrative").textContent = "Praapti is reading culture, role pressure, and hidden signals...";
  const data = await api("/api/praapti/hunt", {
    method: "POST",
    body: JSON.stringify({ job_description: jobDescription })
  });
  $("praaptiNarrative").textContent = `Culture Insight:\n${data.culture_insight}\n\nIdeal Profile:\n${data.ideal_profile}`;
  $("praaptiResults").innerHTML = (data.candidates || []).map(candidate => `<div class="candidate-card"><strong>${candidate.name} — ${candidate.title}</strong><div class="candidate-meta"><span>Fit Score ${candidate.fit_score}</span><span>${candidate.experience} years</span></div><p>${candidate.genesis_profile}</p><div class="proposal-meta">${candidate.discovery_source || ""}</div></div>`).join("");
  if (data.used_avatars) {
    setOrbMode(data.used_avatars.map(titleAvatar));
  }
  speak("Praapti hunt complete.");
  toast(data.message || "Praapti hunt complete.");
  await Promise.all([loadBrainStatus(), loadEmpireDashboard(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function loadNirmaanProposals() {
  const data = await api("/api/nirmaan/proposals");
  const proposals = data.proposals || [];
  $("nirmaanList").innerHTML = proposals.length ? proposals.map(item => `<div class="proposal-card"><strong>${item.title}</strong><p>${item.description}</p><div class="proposal-meta">${(item.avatars || []).map(titleAvatar).join(" + ") || "Empire synthesis"} • ${item.provider || "built-in"}</div><div class="button-row" style="margin-top:12px"><button class="action-btn" onclick="approveNirmaan('${item.id}')">Approve And Stage</button></div></div>`).join("") : `<div class="empty-note">No pending proposals. Trigger Nirmaan Chakra to generate the next evolution.</div>`;
}

async function triggerSelfDevelopment() {
  createParticles(42, "rgba(193,161,255,.95)");
  const data = await api("/api/nirmaan/develop", { method: "POST" });
  toast(data.message || "New proposal created.");
  await Promise.all([loadNirmaanProposals(), loadBrainStatus(), loadEmpireDashboard(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function approveNirmaan(id) {
  const data = await api("/api/nirmaan/approve", {
    method: "POST",
    body: JSON.stringify({ proposal_id: id })
  });
  toast(data.message || "Proposal approved.");
  await Promise.all([loadNirmaanProposals(), loadBrainStatus(), loadEmpireDashboard(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function loadVault() {
  const data = await api("/api/akshaya/vault");
  const storage = data.quantum_storage || {};
  $("guardianInfo").textContent = `Akshaya Guardian ${data.guardian}. Seal: ${data.seal}. State file: ${data.state_file}. Protection meter ${data.protection_meter}%. Quantum storage ${storage.mode || "elastic preservation"} with ${storage.items_preserved || 0} preserved items.`;
  $("vaultGuardian").textContent = `Guardian ${data.guardian}. State file: ${data.state_file}. Seal: ${data.seal}. Eternal preservation mode ${data.eternal_preservation_mode}. Prime Minister ${data.prime_minister?.enabled ? "loop live" : "paused"}.`;
  const items = data.items || [];
  $("vaultList").innerHTML = items.length ? items.map(item => `<div class="vault-card"><strong>${item.title}</strong><div class="vault-meta">${item.kind} • ${item.created_at}</div><p>${item.summary}</p></div>`).join("") : `<div class="empty-note">The vault is empty for now.</div>`;
}

async function loadMotherMonitor() {
  const data = await api("/api/mother/monitor");
  renderMotherMonitor(data);
  return data;
}

async function runSafeRepair() {
  try {
    const data = await api("/api/brain/auto-repair/run", {
      method: "POST",
      body: JSON.stringify({ brain_id: "all", include_state_repair: true, include_uiux_audit: true }),
    });
    toast(data.result || "Safe repair complete");
    await Promise.all([loadMotherMonitor(), loadBrainStatus(), loadCabinetStatus(), loadSettingsStatus()]).catch(() => {});
  } catch (error) {
    toast(error.message || "Safe repair failed");
  }
}

async function loadVoiceStatus() {
  const data = await api("/api/voice/status");
  listening = !!data.always_listening;
  refreshSpeechVoices();
  voicePrefs = {
    voice_profile: data.voice_profile || "sovereign_female",
    language: data.language || "en-IN",
    rate: Number(data.rate || 0.94),
    pitch: Number(data.pitch || 1.08),
    engine: data.engine || "browser_builtin_female"
  };
  const chosenVoice = pickSpeechVoice();
  if (chosenVoice) {
    lastChosenVoiceName = `${chosenVoice.name} (${chosenVoice.lang})`;
  }
  $("voiceToggle").textContent = listening ? "Disable Listening" : "Enable Listening";
  if ($("voiceProfileSelect")) $("voiceProfileSelect").value = voicePrefs.voice_profile;
  if ($("voiceLanguageSelect")) $("voiceLanguageSelect").value = voicePrefs.language;
  if ($("voiceSelectedName")) {
    $("voiceSelectedName").textContent = `Built-in voice target: ${voicePreferenceLabel(voicePrefs.voice_profile)}${lastChosenVoiceName ? ` | Current: ${lastChosenVoiceName}` : ""}`;
  }
  if ($("voiceEngineNote")) {
    const runtimeHeadline = data.runtime?.headline ? ` ${data.runtime.headline}.` : "";
    $("voiceEngineNote").textContent = `Engine ${voicePrefs.engine}. Language ${voicePrefs.language}. Rate ${voicePrefs.rate.toFixed(2)}. Pitch ${voicePrefs.pitch.toFixed(2)}.${runtimeHeadline}`;
  }
  $("voiceStatus").textContent = `Wake words: ${(data.wake_words || []).join(", ")}\nLast command: ${data.last_command || "none yet"}\nActive avatars: ${(data.active_avatars || []).join(" + ")}\nVoice persona: ${data.voice_profile_label || voicePreferenceLabel(voicePrefs.voice_profile)} (${voicePrefs.language})`;
  updateListeningState();
  await loadVoiceRuntimeStatus().catch(() => {});
}

function scheduleBrainStreamRefresh() {
  clearTimeout(brainRefreshTimer);
  brainRefreshTimer = setTimeout(() => {
    Promise.all([
      loadBrainStatus(),
      loadEmpireDashboard(),
      loadCabinetStatus(),
      loadMotherMonitor(),
      loadPranaNadi(),
      loadVishnuStatus(),
      loadVoiceStatus(),
      loadSettingsStatus()
    ]).catch(() => {});
  }, 120);
}

function connectBrainStream() {
  if (!("EventSource" in window)) return;
  if (brainEventSource) {
    brainEventSource.close();
  }
  brainEventSource = new EventSource("/api/brain/stream");
  brainEventSource.addEventListener("snapshot", () => {
    scheduleBrainStreamRefresh();
  });
  brainEventSource.onerror = () => {
    // polling remains as a fallback
  };
}

async function saveVoicePreferences() {
  const voice_profile = $("voiceProfileSelect")?.value || "sovereign_female";
  const language = $("voiceLanguageSelect")?.value || "en-IN";
  const data = await api("/api/voice/settings", {
    method: "POST",
    body: JSON.stringify({
      always_listening: listening,
      voice_profile,
      language
    })
  });
  voicePrefs = {
    ...voicePrefs,
    voice_profile,
    language,
    rate: Number(data.voice?.rate || voicePrefs.rate || 0.94),
    pitch: Number(data.voice?.pitch || voicePrefs.pitch || 1.08),
    engine: data.voice?.engine || "browser_builtin_female"
  };
  if (recognition) {
    recognition.lang = voicePrefs.language || "en-IN";
  }
  toast("Voice persona updated.");
  await loadVoiceStatus();
}

function boolLabel(value) {
  return value ? "On" : "Off";
}

async function updateSetting(patch) {
  const data = await api("/api/settings/update", {
    method: "POST",
    body: JSON.stringify(patch)
  });
  latestSettings = data.settings || null;
  await Promise.all([loadSettingsStatus(), loadBrainStatus(), loadEmpireDashboard(), loadVoiceStatus(), loadCabinetStatus(), loadMotherMonitor()]);
  if (Object.prototype.hasOwnProperty.call(patch, "always_listening")) {
    if (patch.always_listening) {
      startRecognition();
    } else {
      stopRecognition();
    }
  }
}

function renderSettings(settings) {
  latestSettings = settings;
  const providers = settings.providers || {};
  const effectiveProvider = providerDraft.provider || settings.provider_preference || "openai";
  const providerRows = ["ollama", "openai", "gemini", "anthropic", "built_in"].map(key => {
    const provider = providers[key] || {};
    const selected = effectiveProvider === key;
    return `
      <div class="provider-card ${selected ? "active" : ""}">
        <strong>${provider.label || key}</strong>
        <span>${provider.configured ? "Configured" : "Not configured"}</span>
        <small>${provider.model || ""}</small>
        <div class="button-row">
          <button class="mini-btn" onclick="selectProviderCard('${key}')">${selected ? "Selected" : "Select"}</button>
        </div>
      </div>
    `;
  }).join("");
  $("settingsProviders").innerHTML = providerRows;
  $("settingsKeyNote").textContent = settings.notes?.keys_source || "Paste a provider key manually when you want an external model.";
  $("providerIssueTitle").textContent = settings.provider_issue ? `${settings.provider_issue.provider} health` : "Provider Health";
  $("providerIssueText").textContent = settings.provider_issue?.message || "No recent provider errors. If a provider hits quota or billing limits, Leazy will fall back to the built-in local brain.";
  if ($("interpreterBridgeTitle")) {
    const interpreter = settings.interpreter || {};
    $("interpreterBridgeTitle").textContent = `Interpreter Bridge - ${interpreter.offline_provider || "ollama/local"}`;
    $("interpreterBridgeNote").textContent = interpreter.bridge_note || "Operator commands route through the local interpreter first.";
    const warmLabel = interpreter.offline_warm_ready ? "warm" : interpreter.offline_warming ? "warming" : "cold";
    $("interpreterBridgeModels").textContent = `Offline ${interpreter.offline_model || "llama3:latest"} (${warmLabel}) - External ${interpreter.external_provider || "built-in"} - Ready mutations ${Number(interpreter.ready_mutations || 0)} - Skill ledgers ${Number(interpreter.skill_ledgers || 0)}.`;
  }
  if ($("providerCatalogNote")) {
    const selectedProvider = providers[effectiveProvider] || {};
    const updatedAt = selectedProvider.catalog_updated_at ? ` Last refresh ${selectedProvider.catalog_updated_at}.` : "";
    $("providerCatalogNote").textContent = settings.notes?.models_source
      ? `${settings.notes.models_source}${updatedAt}`
      : `Paste a key and fetch the live model list for the selected provider.${updatedAt}`;
  }
  if ($("providerCatalogTitle")) {
    $("providerCatalogTitle").textContent = `Model Catalog${providers[effectiveProvider]?.catalog_source === "live" ? " - live" : ""}`;
  }

  const providerSelect = $("providerSelect");
  if (providerSelect) {
    providerSelect.innerHTML = [
      `<option value="auto">Auto (best available)</option>`,
      ...Object.entries(providers).map(([key, provider]) => `<option value="${key}">${provider.label}</option>`)
    ].join("");
    providerSelect.value = effectiveProvider;
    renderProviderModelOptions();
  }
  const providerKeyInput = $("providerKeyInput");
  if (providerKeyInput) {
    const keyNotRequired = effectiveProvider === "auto" || effectiveProvider === "built_in" || effectiveProvider === "ollama";
    providerKeyInput.disabled = keyNotRequired;
    providerKeyInput.placeholder = effectiveProvider === "ollama"
      ? "No API key needed for local Ollama"
      : "Paste API key here to save locally for the selected provider";
  }

  const toggles = [
    {
      label: "Voice Wake",
      key: "always_listening",
      value: settings.voice?.always_listening,
      copy: "Keeps browser wake listening aligned with backend voice status.",
      patchKey: "always_listening"
    },
    {
      label: "Screen Vision",
      key: "screen_capture_enabled",
      value: settings.privacy?.screen_capture_enabled,
      copy: "Allows consent-based browser screen capture tools.",
      patchKey: "screen_capture_enabled"
    },
    {
      label: "Audio Insights",
      key: "audio_capture_enabled",
      value: settings.privacy?.audio_capture_enabled,
      copy: "Lets the local control layer process audio capture when you explicitly allow it.",
      patchKey: "audio_capture_enabled"
    },
    {
      label: "Bounded Packages",
      key: "bounded_packages_enabled",
      value: settings.privacy?.bounded_packages_enabled,
      copy: "Enables safe package missions for research and growth planning.",
      patchKey: "bounded_packages_enabled"
    },
    {
      label: "Privacy Guard",
      key: "privacy_guard_enabled",
      value: settings.privacy?.privacy_guard_enabled,
      copy: "Keeps consent and privacy protections front and center across the UI.",
      patchKey: "privacy_guard_enabled"
    },
    {
      label: "HQ Visual Sync",
      key: "hq_visual_sync",
      value: settings.privacy?.hq_visual_sync,
      copy: "Keeps HQ, Network, and ATS aligned with the same live empire state.",
      patchKey: "hq_visual_sync"
    }
  ];

  $("settingsToggles").innerHTML = toggles.map(toggle => `
    <div class="toggle-card">
      <div>
        <strong>${toggle.label}</strong>
        <p>${toggle.copy}</p>
      </div>
      <button class="mini-btn" onclick="updateSetting({ ${toggle.patchKey}: ${!toggle.value} })">${boolLabel(toggle.value)}</button>
    </div>
  `).join("");

  $("settingsSummaryTitle").textContent = `Provider ${settings.active_provider || "built-in"} is active`;
  $("settingsSummaryText").textContent = `Voice ${boolLabel(settings.voice?.always_listening)} (${voicePreferenceLabel(settings.voice?.voice_profile)}), screen vision ${boolLabel(settings.privacy?.screen_capture_enabled)}, packages ${boolLabel(settings.privacy?.bounded_packages_enabled)}, interpreter ${(settings.interpreter?.offline_model || "local")}.`;
}

function selectProviderCard(provider) {
  providerDraft.provider = provider;
  providerDraft.model = latestSettings?.providers?.[provider]?.model || null;
  providerDraft.dirty = true;
  $("providerSelect").value = provider;
  renderProviderModelOptions();
  renderSettings(latestSettings);
}

function renderProviderModelOptions() {
  const provider = $("providerSelect")?.value || "auto";
  const modelSelect = $("providerModelSelect");
  if (provider === "auto" || provider === "built_in") {
    modelSelect.innerHTML = `<option value="">${provider === "auto" ? "Managed automatically" : "Built-in local brain"}</option>`;
    modelSelect.value = "";
    modelSelect.disabled = true;
    return;
  }
  modelSelect.disabled = false;
  const options = latestSettings?.providers?.[provider]?.model_options || [latestSettings?.providers?.[provider]?.model || "empire-fallback"];
  modelSelect.innerHTML = options.map(model => `<option value="${model}">${model}</option>`).join("");
  const activeModel = providerDraft.model || latestSettings?.providers?.[provider]?.model;
  if (activeModel && options.includes(activeModel)) {
    modelSelect.value = activeModel;
  }
}

function onProviderChanged() {
  providerDraft.provider = $("providerSelect")?.value || "auto";
  providerDraft.model = null;
  providerDraft.dirty = true;
  clearProviderKeyInput();
  renderProviderModelOptions();
  renderSettings(latestSettings);
}

function onProviderModelChanged() {
  providerDraft.model = $("providerModelSelect")?.value || null;
  providerDraft.dirty = true;
}

async function applySelectedProvider() {
  const provider = $("providerSelect").value;
  if (provider === "auto" || provider === "built_in") {
    await updateSetting({ provider_preference: provider });
    providerDraft = { provider, model: null, dirty: false };
    toast(`Provider preference set to ${provider}.`);
    return;
  }
  const model = $("providerModelSelect").value;
  const data = await api("/api/providers/configure", {
    method: "POST",
    body: JSON.stringify({
      provider,
      model,
      set_default: true
    })
  });
  providerDraft = { provider, model, dirty: false };
  toast(data.message || `Provider preference set to ${provider}.`);
  await Promise.all([loadSettingsStatus(), loadBrainStatus(), loadEmpireDashboard(), loadCabinetStatus(), loadMotherMonitor()]);
  return;
}

function clearProviderKeyInput() {
  $("providerKeyInput").value = "";
}

async function fetchProviderModels() {
  try {
    const provider = $("providerSelect").value;
    if (provider === "auto" || provider === "built_in") {
      toast("Choose Ollama or an external provider to fetch models.");
      return;
    }
    const apiKey = provider === "ollama" ? "" : $("providerKeyInput").value.trim();
    const data = await api("/api/providers/catalog", {
      method: "POST",
      body: JSON.stringify({ provider, api_key: apiKey })
    });
    latestSettings = data.settings || latestSettings;
    providerDraft.provider = provider;
    providerDraft.model = data.current_model || data.models?.[0] || null;
    providerDraft.dirty = true;
    renderSettings(latestSettings);
    if ($("providerModelSelect") && providerDraft.model) {
      $("providerModelSelect").value = providerDraft.model;
    }
    if ($("providerCatalogNote")) {
      $("providerCatalogNote").textContent = `${data.message} ${data.models?.length || 0} model(s) available for ${provider}.`;
    }
    toast(data.message || "Models refreshed.");
  } catch (error) {
    if ($("providerCatalogNote")) {
      $("providerCatalogNote").textContent = error.message || "Unable to fetch the provider catalog right now.";
    }
    toast(error.message || "Unable to fetch models.");
  }
}

async function removeSavedProviderKey() {
  try {
    const provider = $("providerSelect").value;
    if (provider === "auto" || provider === "built_in") {
      toast("Select Ollama or an external provider first.");
      return;
    }
    const data = await api("/api/providers/configure", {
      method: "POST",
      body: JSON.stringify({
        provider,
        clear_saved: true
      })
    });
    providerDraft = { provider: provider === "ollama" ? "ollama" : "built_in", model: null, dirty: false };
    clearProviderKeyInput();
    latestSettings = data.settings || latestSettings;
    renderSettings(latestSettings);
    toast(data.message || "Saved provider key removed.");
    await Promise.all([loadBrainStatus(), loadEmpireDashboard(), loadCabinetStatus(), loadMotherMonitor()]);
  } catch (error) {
    toast(error.message || "Unable to remove the saved key.");
  }
}

async function saveProviderConfig() {
  try {
    const provider = $("providerSelect").value;
    if (provider === "auto" || provider === "built_in") {
      await applySelectedProvider();
      return;
    }
    const model = $("providerModelSelect").value;
    const apiKey = provider === "ollama" ? "" : $("providerKeyInput").value.trim();
    if (provider !== "ollama" && !apiKey && !latestSettings?.providers?.[provider]?.configured) {
      toast("Paste an API key first, fetch the model list, then save and apply.");
      return;
    }
    const data = await api("/api/providers/configure", {
      method: "POST",
      body: JSON.stringify({
        provider,
        model,
        api_key: apiKey,
        set_default: true
      })
    });
    providerDraft = { provider, model, dirty: false };
    clearProviderKeyInput();
    toast(data.message || "Provider saved.");
    await Promise.all([loadSettingsStatus(), loadBrainStatus(), loadEmpireDashboard(), loadCabinetStatus(), loadMotherMonitor()]);
  } catch (error) {
    toast(error.message || "Unable to save the provider config.");
  }
}

async function loadSettingsStatus() {
  const settings = await api("/api/settings/status");
  renderSettings(settings);
  return settings;
}

function renderPackageTemplates(data) {
  packageTemplateCache = data.templates || [];
  $("packageTemplates").innerHTML = packageTemplateCache.map(template => `
    <div class="proposal-card">
      <strong>${template.title}</strong>
      <p>${template.summary}</p>
      <div class="proposal-meta">${template.best_for}</div>
      <div class="button-row" style="margin-top:12px">
        <button class="action-btn" onclick="launchPackage('${template.id}')">Launch ${template.title}</button>
      </div>
    </div>
  `).join("");
}

async function loadPackageTemplates() {
  const data = await api("/api/packages/templates");
  renderPackageTemplates(data);
}

async function launchPackage(templateId) {
  try {
    const objective = $("packageObjective").value.trim();
    $("packageLaunchLog").textContent = "Launching bounded package...";
    const data = await api("/api/packages/launch", {
      method: "POST",
      body: JSON.stringify({ template_id: templateId, objective })
    });
    if (data.allowed === false) {
      $("packageLaunchLog").textContent = data.message || "Packages are disabled.";
      latestSettings = data.settings || latestSettings;
      if (latestSettings) renderSettings(latestSettings);
      showPanel("settings");
      toast(data.message || "Packages are disabled.");
      return;
    }
    const pkg = data.package || {};
    $("packageLaunchLog").textContent = `${data.message}\n\n${pkg.report || "Mission plan ready."}`;
    toast(data.message || "Package launched.");
    createParticles(36, "rgba(135,223,255,.92)");
    await Promise.all([loadEmpireDashboard(), loadBrainStatus(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
  } catch (error) {
    $("packageLaunchLog").textContent = error.message || "Unable to launch the package.";
    toast(error.message || "Package launch failed.");
  }
}

function renderScreenRecordings() {
  $("screenRecordings").innerHTML = screenRecordings.length ? screenRecordings.map((item, index) => `
    <div class="proposal-card">
      <strong>Recording ${index + 1}</strong>
      <p>${item.label}</p>
      <div class="button-row" style="margin-top:12px">
        <a class="ghost-btn" href="${item.url}" download="${item.filename}">Download</a>
      </div>
    </div>
  `).join("") : `<div class="empty-note">No screen recordings yet. Start screen vision to capture a local recording.</div>`;
}

async function startScreenVision() {
  if (!latestSettings?.privacy?.screen_capture_enabled) {
    toast("Enable Screen Vision in settings first.");
    showPanel("settings");
    return;
  }
  if (!navigator.mediaDevices?.getDisplayMedia) {
    $("screenVisionStatus").textContent = "This browser does not support screen capture.";
    return;
  }
  try {
    screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    screenChunks = [];
    screenRecorder = new MediaRecorder(screenStream);
    screenRecorder.ondataavailable = event => {
      if (event.data?.size) screenChunks.push(event.data);
    };
    screenRecorder.onstop = () => {
      const blob = new Blob(screenChunks, { type: "video/webm" });
      const url = URL.createObjectURL(blob);
      screenRecordings.unshift({
        url,
        filename: `leazy-screen-${Date.now()}.webm`,
        label: `Local screen capture saved at ${new Date().toLocaleTimeString()}`
      });
      renderScreenRecordings();
      $("screenVisionStatus").textContent = "Screen vision stopped. The local recording is ready to download below.";
    };
    screenRecorder.start();
    $("screenVisionStatus").textContent = "Screen vision is active. Leazy is capturing the selected display locally in your browser.";
    renderScreenRecordings();
  } catch (error) {
    $("screenVisionStatus").textContent = error?.message || "Screen capture was canceled.";
  }
}

function stopScreenVision() {
  if (screenRecorder && screenRecorder.state !== "inactive") {
    screenRecorder.stop();
  }
  if (screenStream) {
    screenStream.getTracks().forEach(track => track.stop());
    screenStream = null;
  }
}

function initRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    $("voiceStatus").textContent = "Browser speech recognition is not available here. You can still use manual voice commands from this panel.";
    updateListeningState("Browser speech recognition is not available here. Use manual voice commands or a supported browser.");
    return;
  }
  recognition = new Recognition();
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.lang = voicePrefs.language || "en-IN";
  recognition.onstart = () => {
    recognitionStarting = false;
    recognitionActive = true;
    lastRecognitionError = "";
    updateListeningState();
  };
  recognition.onresult = async event => {
    const transcript = event.results[event.results.length - 1][0].transcript.trim();
    if (!transcript) return;
    await submitVoiceCommand(transcript, "direct");
  };
  recognition.onerror = event => {
    recognitionStarting = false;
    recognitionActive = false;
    lastRecognitionError = event.error || "unknown error";
    if ($("voiceStatus")) {
      $("voiceStatus").textContent = `Voice recognition issue: ${lastRecognitionError}\nSwitch to manual voice commands or refresh the voice relay.`;
    }
    updateListeningState();
  };
  recognition.onend = () => {
    recognitionStarting = false;
    recognitionActive = false;
    updateListeningState();
    if (listening && recognition && !["not-allowed", "service-not-allowed"].includes(lastRecognitionError)) {
      setTimeout(() => startRecognition("restart"), 320);
    }
  };
}

function startRecognition(reason = "manual") {
  if (!recognition) initRecognition();
  if (!recognition || recognitionActive || recognitionStarting) {
    return;
  }
  recognitionStarting = true;
  lastRecognitionError = "";
  updateListeningState(reason === "restart" ? "Voice relay is reconnecting..." : "Starting microphone access for direct voice control...");
  try {
    recognition.start();
  } catch (error) {
    recognitionStarting = false;
    recognitionActive = false;
    lastRecognitionError = error?.message || "recognition start failed";
    updateListeningState();
    toast("Browser voice listening could not start. Allow microphone access, then try again.");
  }
}

function stopRecognition() {
  if (recognition) {
    recognitionStarting = false;
    recognitionActive = false;
    try { recognition.stop(); } catch (error) {}
  }
  updateListeningState();
}

async function toggleListening() {
  const nextListening = !listening;
  await api("/api/voice/settings", {
    method: "POST",
    body: JSON.stringify({
      always_listening: nextListening,
      voice_profile: $("voiceProfileSelect")?.value || voicePrefs.voice_profile || "sovereign_female",
      language: $("voiceLanguageSelect")?.value || voicePrefs.language || "en-IN"
    })
  });
  listening = nextListening;
  if (listening) {
    startRecognition();
  } else {
    stopRecognition();
  }
  await loadVoiceStatus();
  toast(listening ? "Voice wake enabled." : "Voice wake disabled.");
}

async function submitVoiceCommand(command, mode = "wake") {
  const data = await api("/api/voice/wake", {
    method: "POST",
    body: JSON.stringify({ command, mode })
  });
  $("voiceStatus").textContent = `Heard: ${data.heard}\n${data.response}`;
  if (data.used_avatars) {
    setOrbMode(data.used_avatars.map(titleAvatar));
  }
  if (data.wake_detected) {
    createParticles(26, "rgba(241,202,107,.92)");
    flareHridaya(1.2);
    speak(data.response);
  }
  await Promise.all([loadVoiceStatus(), loadBrainStatus(), loadEmpireDashboard(), loadVishnuStatus(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

async function testWake() {
  await submitVoiceCommand("Hey Jinn, channel Krishna and report empire status", "wake");
}

async function sendVoiceCommand() {
  const input = $("voiceManual");
  const command = input.value.trim();
  if (!command) {
    toast("Type a voice command first.");
    return;
  }
  input.value = "";
  await submitVoiceCommand(command, "direct");
}

async function sendOrbMessage() {
  const input = $("orbInput");
  const message = input.value.trim();
  if (!message) return;
  appendBubble("user", message);
  input.value = "";
  if (message.toLowerCase().startsWith("channel ")) {
    await channelAvatar(message.slice(8));
    appendBubble("ai", "Channel updated.");
    return;
  }
  const data = await api("/api/leazy/chat", {
    method: "POST",
    body: JSON.stringify({ message, workspace: currentWorkspace(), source: "orb" })
  });
  appendBubble("ai", data.reply);
  flareHridaya(1.16);
  if (data.used_avatars) {
    setOrbMode(data.used_avatars.map(titleAvatar));
  }
  speak(data.reply);
  await Promise.all([loadBrainStatus(), loadEmpireDashboard(), loadVishnuStatus(), loadVault(), loadSettingsStatus(), loadCabinetStatus(), loadMotherMonitor()]);
}

window.addEventListener("beforeinstallprompt", event => {
  event.preventDefault();
  deferredPrompt = event;
});

async function installPWA() {
  if (!deferredPrompt) {
    toast("Install prompt is not available right now.");
    return;
  }
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
}

async function boot() {
  renderTabs();
  renderSceneButtons();
  renderDashavataraWheel();
  renderAvatarGuideGrid();
  renderScreenRecordings();
  setScene(0);
  refreshSpeechVoices();
  if ("speechSynthesis" in window) {
    window.speechSynthesis.onvoiceschanged = () => {
      refreshSpeechVoices();
      if ($("voiceSelectedName")) {
        $("voiceSelectedName").textContent = lastChosenVoiceName ? `Built-in voice: ${lastChosenVoiceName}` : "The browser will select the best built-in feminine voice available.";
      }
    };
  }
  initRecognition();
  const initialPanel = normalizePanelId((window.location.hash || "").replace("#", "") || "bridge");
  showPanel(initialPanel, false);
  appendBubble("ai", "Leazy Jinn is online. Ask for strategy, open Cabinet, run Praapti, trigger Nirmaan, or channel an avatar.");
  await Promise.all([
    loadBrainStatus(),
    loadEmpireDashboard(),
    loadCabinetStatus(),
    loadMotherMonitor(),
    loadPranaNadi(),
    loadVishnuStatus(),
    loadNirmaanProposals(),
    loadVault(),
    loadVoiceStatus(),
    loadSettingsStatus(),
    loadPackageTemplates()
  ]);
  connectBrainStream();
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  }
  setInterval(loadBrainStatus, 14000);
  setInterval(loadEmpireDashboard, 16000);
  setInterval(loadCabinetStatus, 17000);
  setInterval(loadMotherMonitor, 15000);
  setInterval(loadPranaNadi, 13000);
  setInterval(loadVishnuStatus, 18000);
  setInterval(loadSettingsStatus, 20000);
  setInterval(cycleScene, 42000);
  setInterval(drawPranaNadi, 80);
}

boot().catch(error => {
  console.error(error);
  toast(error.message || "Boot failed");
});
