const $ = id => document.getElementById(id);
let selectedPlanId = "starter";
let authMe = null;

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.style.display = "block";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.style.display = "none";
  }, 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }
  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed: ${response.status}`);
  }
  return data;
}

function nextPath() {
  const params = new URLSearchParams(window.location.search);
  return params.get("next") || "/agent/console";
}

function showTab(id) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.authTab === id));
  document.querySelectorAll(".auth-panel").forEach(panel => panel.classList.toggle("active", panel.id === `auth-${id}`));
}

function bindTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => showTab(btn.dataset.authTab));
  });
}

function renderPlans(plans) {
  $("plansGrid").innerHTML = (plans || []).map(plan => `
    <div class="plan-card ${selectedPlanId === plan.id ? "active" : ""}">
      <strong>${plan.name}</strong>
      <div class="price">${plan.price_inr ? `Rs ${plan.price_inr}` : "Free"}</div>
      <div class="muted">${plan.billing_period}</div>
      <p>${plan.tagline}</p>
      <ul>${(plan.services || []).map(item => `<li>${item}</li>`).join("")}</ul>
      <button class="mini-btn" onclick="selectPlan('${plan.id}','${plan.name.replace(/'/g, "\\'")}')">${selectedPlanId === plan.id ? "Selected" : "Choose Plan"}</button>
    </div>
  `).join("");
}

function selectPlan(planId, planName) {
  selectedPlanId = planId;
  $("selectedPlanName").value = planName;
  loadPlans();
}

async function loadPlans() {
  const data = await api("/api/billing/plans");
  renderPlans(data.plans || []);
  if (!$("selectedPlanName").value) {
    const first = (data.plans || [])[0];
    if (first) selectPlan(first.id, first.name);
  }
}

function updateAuthBanner(auth) {
  authMe = auth;
  if (auth?.authenticated && auth.user) {
    const identity = auth.user.login_id || auth.user.email || "active session";
    $("authStateTitle").textContent = `Connected as ${auth.user.name}`;
    $("authStateText").textContent = `${identity} • ${auth.user.role} • ${auth.user.plan?.name || auth.user.plan_id}`;
    $("continueBtn").style.display = "inline-flex";
    $("logoutBtn").style.display = "inline-flex";
  } else {
    $("authStateTitle").textContent = "No active session";
    $("authStateText").textContent = "Sign in, register, or use master unlock to enter the protected Ishani surfaces.";
    $("continueBtn").style.display = "none";
    $("logoutBtn").style.display = "none";
  }
}

async function loadAuthState() {
  const data = await api("/api/auth/me");
  updateAuthBanner(data);
}

async function loginUser() {
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("loginEmail").value.trim(),
        password: $("loginPassword").value,
      }),
    });
    $("authStatus").textContent = data.message;
    updateAuthBanner(data.auth);
    toast("Login successful.");
    continueSession();
  } catch (error) {
    $("authStatus").textContent = error.message;
    toast(error.message);
  }
}

async function registerUser() {
  try {
    const data = await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: $("registerName").value.trim(),
        email: $("registerEmail").value.trim(),
        password: $("registerPassword").value,
        plan_id: selectedPlanId,
      }),
    });
    const orderLine = data.order ? `\nOrder: ${data.order.plan_id} • ${data.order.status}` : "";
    $("authStatus").textContent = `${data.message}${orderLine}`;
    updateAuthBanner(data.auth);
    toast("Account created.");
    continueSession();
  } catch (error) {
    $("authStatus").textContent = error.message;
    toast(error.message);
  }
}

async function masterLogin() {
  try {
    const data = await api("/api/auth/master-login", {
      method: "POST",
      body: JSON.stringify({
        identifier: $("masterIdentifier").value.trim(),
        password: $("masterPassword").value,
      }),
    });
    $("authStatus").textContent = data.message;
    updateAuthBanner(data.auth);
    toast("Master access granted.");
    continueSession();
  } catch (error) {
    $("authStatus").textContent = error.message;
    toast(error.message);
  }
}

async function logoutSession() {
  await api("/api/auth/logout", { method: "POST" });
  updateAuthBanner({ authenticated: false, user: null });
  $("authStatus").textContent = "Logged out from Ishani Core.";
  toast("Logged out.");
}

function continueSession() {
  const path = nextPath();
  const destination = authMe?.user?.role === "master" ? path : "/agent/console";
  window.location.href = destination;
}

async function boot() {
  bindTabs();
  await Promise.all([loadPlans(), loadAuthState()]);
}

boot().catch(error => {
  $("authStatus").textContent = error.message || "Unable to load access state.";
});
