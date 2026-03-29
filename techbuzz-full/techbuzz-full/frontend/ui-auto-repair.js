(() => {
  const BUTTONISH_SELECTOR = [
    "button",
    "[onclick]",
    "[role='button']",
    ".mini-btn",
    ".action-btn",
    ".ghost-btn",
    ".nav-btn",
    ".gbtn",
    ".abtn",
    ".kbtn",
    ".atab",
    ".co-nav-item",
    ".cmode",
    ".chip",
    ".hq-ai-fab",
    ".orb",
    ".orb-restore",
    ".conn-del",
    ".mclose",
    ".mb",
    ".del",
    ".launch-btn",
    ".price-btn",
    ".btn-primary",
    ".btn-outline",
    ".hero-btn-main",
    ".hero-btn-sec",
  ].join(",");

  const INPUT_SELECTOR = "input, textarea, select";

  function cleanLabel(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .replace(/[←→↑↓✓✕⚡📡📋💎📝💼💡🔗🔌🎯🔍🔒🔓🤖📊📈📉📞📬🧠🛠️⚙️]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function titleFromId(value) {
    return cleanLabel(
      String(value || "")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/[_-]+/g, " ")
    );
  }

  function deriveLabel(el) {
    const explicit = el.getAttribute("aria-label") || el.getAttribute("title");
    if (cleanLabel(explicit)) return cleanLabel(explicit);
    const text = cleanLabel(el.textContent);
    if (text) return text;
    const placeholder = cleanLabel(el.getAttribute("placeholder"));
    if (placeholder) return placeholder;
    const value = cleanLabel(el.getAttribute("value"));
    if (value) return value;
    const idGuess = titleFromId(el.id || el.name || "");
    if (idGuess) return idGuess;
    if (el.className) return titleFromId(String(el.className).split(/\s+/)[0] || "");
    return "";
  }

  function repairButtonLike(root = document) {
    let repaired = 0;
    root.querySelectorAll(BUTTONISH_SELECTOR).forEach(el => {
      const label = deriveLabel(el);
      if (!el.hasAttribute("aria-label") && label) {
        el.setAttribute("aria-label", label);
        repaired += 1;
      }
      if (
        el.tagName !== "BUTTON" &&
        !el.hasAttribute("role") &&
        (el.hasAttribute("onclick") || String(el.className || "").includes("btn") || el.classList.contains("chip"))
      ) {
        el.setAttribute("role", "button");
        repaired += 1;
      }
      if ((el.getAttribute("role") === "button" || el.hasAttribute("onclick")) && !el.hasAttribute("tabindex")) {
        el.setAttribute("tabindex", "0");
        repaired += 1;
      }
    });
    return repaired;
  }

  function repairInputs(root = document) {
    let repaired = 0;
    root.querySelectorAll(INPUT_SELECTOR).forEach(el => {
      const label = deriveLabel(el);
      if (!el.hasAttribute("aria-label") && !el.hasAttribute("aria-labelledby") && label) {
        el.setAttribute("aria-label", label);
        repaired += 1;
      }
    });
    return repaired;
  }

  function injectFocusStyle() {
    if (document.getElementById("tb-ui-repair-style")) return;
    const style = document.createElement("style");
    style.id = "tb-ui-repair-style";
    style.textContent = `
      [role="button"]:focus-visible,
      button:focus-visible,
      input:focus-visible,
      textarea:focus-visible,
      select:focus-visible,
      a:focus-visible {
        outline: 2px solid rgba(144,242,210,.95);
        outline-offset: 3px;
        box-shadow: 0 0 0 4px rgba(144,242,210,.12);
      }
    `;
    document.head.appendChild(style);
  }

  function applyAccessibilityRepair(root = document) {
    injectFocusStyle();
    const buttonRepairs = repairButtonLike(root);
    const inputRepairs = repairInputs(root);
    window.__TB_UI_REPAIR = {
      active: true,
      repairedButtons: buttonRepairs,
      repairedInputs: inputRepairs,
      repairedTotal: buttonRepairs + inputRepairs,
      updatedAt: new Date().toISOString(),
    };
    return window.__TB_UI_REPAIR;
  }

  document.addEventListener("keydown", event => {
    const target = event.target;
    if (!target) return;
    const isButtonRole = target.getAttribute && target.getAttribute("role") === "button";
    if (!isButtonRole) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      target.click();
    }
  });

  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach(node => {
        if (node.nodeType === 1) {
          applyAccessibilityRepair(node);
        }
      });
    }
  });

  function boot() {
    applyAccessibilityRepair(document);
    if (document.body) {
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

  window.TechBuzzUiAutoRepair = {
    apply: applyAccessibilityRepair,
    summary: () => window.__TB_UI_REPAIR || { active: false, repairedTotal: 0 },
  };
})();
