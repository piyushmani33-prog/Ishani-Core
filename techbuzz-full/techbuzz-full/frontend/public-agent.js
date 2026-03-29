const $ = id => document.getElementById(id);
let publicAgentAuth = null;
let publicAgentMessages = [];
let publicAgentListening = false;
let publicAgentRecognition = null;
let publicAgentVoiceName = "";
let publicAgentVoicePrefs = {
  provider: "built_in",
  model: "empire-fallback",
  api_key: "",
  language: "en-IN",
  voice_profile: "sovereign_female"
};
let lastAgentReply = "";

function toast(message) {
  const el = $("agentToast");
  el.textContent = message;
  el.style.display = "block";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.style.display = "none";
  }, 3200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
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
  if (!response.ok) {
    throw new Error(data.detail || data.message || (`Request failed: ${response.status}`));
  }
  return data;
}

function loadProviderDraft() {
  try {
    publicAgentVoicePrefs = {
      ...publicAgentVoicePrefs,
      ...JSON.parse(localStorage.getItem("techbuzz_public_agent_provider") || "{}")
    };
  } catch (error) {
    // ignore invalid saved state
  }
}

function saveProviderDraft() {
  publicAgentVoicePrefs.provider = $("providerSelect").value;
  publicAgentVoicePrefs.model = $("modelSelect").value;
  publicAgentVoicePrefs.api_key = $("providerKey").value.trim();
  publicAgentVoicePrefs.language = $("voiceLanguage").value;
  publicAgentVoicePrefs.voice_profile = $("voicePersona").value;
  localStorage.setItem("techbuzz_public_agent_provider", JSON.stringify(publicAgentVoicePrefs));
  renderProviderSummary();
  toast("Public agent provider draft saved in this browser.");
}

function clearProviderDraft() {
  publicAgentVoicePrefs = {
    provider: "built_in",
    model: "empire-fallback",
    api_key: "",
    language: $("voiceLanguage").value || "en-IN",
    voice_profile: $("voicePersona").value || "sovereign_female"
  };
  localStorage.removeItem("techbuzz_public_agent_provider");
  syncDraftToFields();
  renderProviderSummary();
  toast("Provider draft cleared.");
}

function syncDraftToFields() {
  $("providerSelect").value = publicAgentVoicePrefs.provider || "built_in";
  $("providerKey").value = publicAgentVoicePrefs.api_key || "";
  $("voiceLanguage").value = publicAgentVoicePrefs.language || "en-IN";
  $("voicePersona").value = publicAgentVoicePrefs.voice_profile || "sovereign_female";
}

function renderProviderSummary(extra = "") {
  const provider = publicAgentVoicePrefs.provider || "built_in";
  const model = publicAgentVoicePrefs.model || "empire-fallback";
  $("publicAgentProviderBadge").textContent = `${provider} / ${model}`;
  $("providerStatusBox").textContent = extra || (
    provider === "built_in"
      ? "Built-in TechBuzz AI is active. No external key is required."
      : `Provider ${provider} is selected with model ${model}. The pasted key remains only in this browser unless you clear it.`
  );
}

function loadMessageHistory() {
  try {
    publicAgentMessages = JSON.parse(localStorage.getItem("techbuzz_public_agent_messages") || "[]");
  } catch (error) {
    publicAgentMessages = [];
  }
  if (!publicAgentMessages.length) {
    publicAgentMessages = [
      {
        role: "ai",
        text: "TechBuzz AI is live. Ask about hiring, documents, automation, or how to work with Ishani.",
        provider: "built_in/public-agent"
      }
    ];
  }
}

function saveMessageHistory() {
  localStorage.setItem("techbuzz_public_agent_messages", JSON.stringify(publicAgentMessages.slice(-24)));
}

function renderChat() {
  $("publicAgentChatLog").innerHTML = publicAgentMessages.map(message => `
    <div class="bubble ${message.role}">
      ${escapeHtml(message.text)}
      ${message.provider ? `<span class="bubble-meta">${escapeHtml(message.provider)}</span>` : ""}
    </div>
  `).join("");
  $("publicAgentChatLog").scrollTop = $("publicAgentChatLog").scrollHeight;
}

function appendMessage(role, text, provider = "") {
  publicAgentMessages.push({ role, text, provider });
  publicAgentMessages = publicAgentMessages.slice(-24);
  saveMessageHistory();
  renderChat();
}

async function loadAuthState() {
  const data = await api("/api/auth/me");
  publicAgentAuth = data;
  if (data?.authenticated && data.user) {
    $("publicAgentAuthBadge").textContent = `Signed in as ${data.user.role}`;
  } else {
    $("publicAgentAuthBadge").textContent = "Public access";
  }
}

async function fetchProviderModels() {
  const provider = $("providerSelect").value;
  const apiKey = $("providerKey").value.trim();
  const data = await api("/api/public/provider-models", {
    method: "POST",
    body: JSON.stringify({ provider, api_key: apiKey })
  });
  const models = data.models || [];
  $("modelSelect").innerHTML = models.map(model => `<option value="${model}">${model}</option>`).join("");
  if (models.length) {
    $("modelSelect").value = data.current_model || models[0];
  }
  publicAgentVoicePrefs.provider = provider;
  publicAgentVoicePrefs.model = $("modelSelect").value;
  publicAgentVoicePrefs.api_key = apiKey;
  renderProviderSummary(`${provider} model list refreshed. Choose a model and start chatting.`);
}

function buildHistoryPayload() {
  return publicAgentMessages.slice(-8).map(item => ({
    role: item.role === "ai" ? "assistant" : "user",
    content: item.text
  }));
}

async function sendPublicAgentMessage() {
  const input = $("publicAgentInput");
  const message = input.value.trim();
  if (!message) return;
  appendMessage("user", message);
  input.value = "";
  publicAgentVoicePrefs.provider = $("providerSelect").value;
  publicAgentVoicePrefs.model = $("modelSelect").value;
  publicAgentVoicePrefs.api_key = $("providerKey").value.trim();
  publicAgentVoicePrefs.language = $("voiceLanguage").value;
  publicAgentVoicePrefs.voice_profile = $("voicePersona").value;
  try {
    const data = await api("/api/public/agent-chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        provider: publicAgentVoicePrefs.provider,
        api_key: publicAgentVoicePrefs.api_key,
        model: publicAgentVoicePrefs.model,
        history: buildHistoryPayload()
      })
    });
    lastAgentReply = data.reply || "";
    appendMessage("ai", data.reply || "No reply received.", data.provider || "built_in/public-agent");
    renderProviderSummary(data.error || `Reply delivered through ${data.provider || "built-in"}.`);
    speakText(lastAgentReply);
  } catch (error) {
    appendMessage("ai", error.message || "The public agent could not answer right now.", "error");
    toast(error.message || "Public agent failed");
  }
}

function seedPublicPrompt() {
  $("publicAgentInput").value = "I want a hiring strategy for a startup role and I want to know which TechBuzz surface I should use first.";
}

function renderPromptChips() {
  const prompts = [
    "Explain TechBuzz services",
    "Build a hiring plan for a new startup role",
    "What can your document tools do?",
    "Create an automation roadmap for my company",
    "How do I move from free AI to the protected console?"
  ];
  $("publicPromptChips").innerHTML = prompts.map(prompt => `<button class="prompt-chip" onclick="usePromptChip('${prompt.replace(/'/g, "\\'")}')">${prompt}</button>`).join("");
}

function usePromptChip(prompt) {
  $("publicAgentInput").value = prompt;
  $("publicAgentInput").focus();
}

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function pickPublicAgentVoice() {
  if (!("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices() || [];
  if (!voices.length) return null;
  const language = String($("voiceLanguage").value || "en-IN").toLowerCase();
  const persona = $("voicePersona").value || "sovereign_female";
  const feminineMarkers = ["female", "woman", "zira", "aria", "samantha", "hazel", "natasha", "priya", "veena", "heera"];
  const strategicMarkers = ["zira", "aria", "samantha", "neural"];
  const warmMarkers = ["hazel", "samantha", "veena", "karen", "susan"];
  const preferredMarkers = persona === "strategic_female" ? strategicMarkers : persona === "warm_guide" ? warmMarkers : feminineMarkers;
  const filtered = voices.filter(voice => voice.lang?.toLowerCase().startsWith(language.slice(0, 2)));
  const candidates = filtered.length ? filtered : voices;
  const exact = candidates.find(voice => preferredMarkers.some(marker => voice.name.toLowerCase().includes(marker)));
  if (exact) return exact;
  const englishIndian = candidates.find(voice => voice.lang?.toLowerCase().startsWith("en-in"));
  return englishIndian || candidates[0] || null;
}

function speakText(text) {
  if (!("speechSynthesis" in window) || !text) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = $("voiceLanguage").value || "en-IN";
  utter.rate = $("voicePersona").value === "strategic_female" ? 0.92 : 0.96;
  utter.pitch = $("voicePersona").value === "strategic_female" ? 1.0 : 1.08;
  const preferred = pickPublicAgentVoice();
  if (preferred) {
    utter.voice = preferred;
    utter.lang = preferred.lang || utter.lang;
    publicAgentVoiceName = `${preferred.name} (${preferred.lang})`;
  } else {
    publicAgentVoiceName = "Default browser voice";
  }
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
  renderVoiceSummary(`Spoken with ${publicAgentVoiceName}.`);
}

function speakLastReply() {
  if (!lastAgentReply) {
    toast("No reply is available to speak yet.");
    return;
  }
  speakText(lastAgentReply);
}

function renderVoiceSummary(extra = "") {
  $("publicAgentVoiceBadge").textContent = publicAgentListening ? "Voice listening" : "Voice standby";
  $("voiceStatusBox").textContent = extra || (
    publicAgentListening
      ? "Speech recognition is active. Speak naturally and the public agent will send your words."
      : "Browser voice is ready. Use Start Listening to capture speech if your browser supports it."
  );
  $("voiceToggleBtn").textContent = publicAgentListening ? "Stop Listening" : "Start Listening";
}

function toggleVoiceListening() {
  const Recognition = getSpeechRecognition();
  if (!Recognition) {
    renderVoiceSummary("Speech recognition is not supported in this browser. Text chat and spoken replies still work.");
    return;
  }
  if (publicAgentListening && publicAgentRecognition) {
    publicAgentRecognition.stop();
    publicAgentListening = false;
    renderVoiceSummary();
    return;
  }
  publicAgentRecognition = new Recognition();
  publicAgentRecognition.lang = $("voiceLanguage").value || "en-IN";
  publicAgentRecognition.interimResults = false;
  publicAgentRecognition.maxAlternatives = 1;
  publicAgentRecognition.onstart = () => {
    publicAgentListening = true;
    renderVoiceSummary("Listening now. Speak your request for TechBuzz AI.");
  };
  publicAgentRecognition.onend = () => {
    publicAgentListening = false;
    renderVoiceSummary();
  };
  publicAgentRecognition.onerror = event => {
    publicAgentListening = false;
    renderVoiceSummary(`Voice recognition error: ${event.error}`);
  };
  publicAgentRecognition.onresult = event => {
    const transcript = event.results?.[0]?.[0]?.transcript || "";
    $("publicAgentInput").value = transcript;
    sendPublicAgentMessage();
  };
  publicAgentRecognition.start();
}

function bindInputs() {
  $("publicAgentInput").addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      sendPublicAgentMessage();
    }
  });
  $("providerSelect").addEventListener("change", () => {
    if ($("providerSelect").value === "built_in") {
      $("modelSelect").innerHTML = `<option value="empire-fallback">empire-fallback</option>`;
      $("modelSelect").value = "empire-fallback";
      renderProviderSummary();
    }
  });
}

async function boot() {
  loadProviderDraft();
  loadMessageHistory();
  syncDraftToFields();
  renderPromptChips();
  renderChat();
  renderProviderSummary();
  renderVoiceSummary();
  if ("speechSynthesis" in window) {
    window.speechSynthesis.onvoiceschanged = () => {
      const voice = pickPublicAgentVoice();
      if (voice) {
        publicAgentVoiceName = `${voice.name} (${voice.lang})`;
        renderVoiceSummary(`Voice ready: ${publicAgentVoiceName}.`);
      }
    };
  }
  bindInputs();
  await loadAuthState();
}

boot().catch(error => {
  toast(error.message || "Unable to boot the public agent.");
});
