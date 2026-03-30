/**
 * role-phase-router.js
 * --------------------
 * Role-Aware Navigation Controller for TechBuzz / Ishani Core.
 *
 * On page load, fetches /api/role/visibility to get the combined
 * role + phase data and exposes window.RolePhaseRouter with utility
 * methods. Then hides/shows nav items that carry data-module or
 * data-dashboard attributes.
 */

(function () {
  "use strict";

  // -------------------------------------------------------------------------
  // Internal state
  // -------------------------------------------------------------------------
  let _data = null;          // raw visibility payload from the API
  let _loaded = false;
  const _listeners = [];     // callbacks registered before load completes

  // -------------------------------------------------------------------------
  // Fetch visibility data
  // -------------------------------------------------------------------------
  async function _fetchVisibility() {
    try {
      const res = await fetch("/api/role/visibility", { credentials: "include" });
      if (!res.ok) {
        // Not authenticated — treat as candidate with phase 1 defaults
        _data = _candidateFallback();
      } else {
        _data = await res.json();
      }
    } catch (_e) {
      _data = _candidateFallback();
    }
    _loaded = true;
    _applyNavVisibility();
    _renderBadges();
    _listeners.forEach(function (fn) {
      try { fn(_data); } catch (_) {}
    });
  }

  function _candidateFallback() {
    return {
      role: "candidate",
      owner_brain: "public_agent",
      brain_label: "Career Assistant",
      phase: 1,
      phase_name: "Recruitment Launch",
      visible_modules: ["recruitment", "ats", "career", "jobs", "public_agent"],
      visible_actions: ["post_job", "screen_candidate", "schedule_interview", "recruiter_chat"],
      visible_dashboards: ["recruiter-mode", "career", "jobs", "ats", "company-portal"],
      hidden_advanced: ["neural", "spread", "empire", "research", "browser_suite", "photon", "brain_hierarchy"],
    };
  }

  // -------------------------------------------------------------------------
  // Apply visibility to DOM elements with data-module / data-dashboard attrs
  // -------------------------------------------------------------------------
  function _applyNavVisibility() {
    if (!_data) return;

    // Handle data-module attributes
    document.querySelectorAll("[data-module]").forEach(function (el) {
      const moduleId = el.getAttribute("data-module");
      const allowed = _data.visible_modules && _data.visible_modules.includes(moduleId);
      _setNavItemVisibility(el, allowed);
    });

    // Handle data-dashboard attributes
    document.querySelectorAll("[data-dashboard]").forEach(function (el) {
      const dashId = el.getAttribute("data-dashboard");
      const allowed = _data.visible_dashboards && _data.visible_dashboards.includes(dashId);
      _setNavItemVisibility(el, allowed);
    });

    // Handle data-action attributes
    document.querySelectorAll("[data-action-id]").forEach(function (el) {
      const actionId = el.getAttribute("data-action-id");
      const allowed = _data.visible_actions && _data.visible_actions.includes(actionId);
      _setNavItemVisibility(el, allowed);
    });
  }

  function _setNavItemVisibility(el, allowed) {
    if (allowed) {
      el.classList.remove("rpr-hidden");
      el.classList.add("rpr-visible");
    } else {
      el.classList.remove("rpr-visible");
      el.classList.add("rpr-hidden");
    }
  }

  // -------------------------------------------------------------------------
  // Inject role + phase badges
  // -------------------------------------------------------------------------
  function _renderBadges() {
    if (!_data) return;

    // Role badge
    const roleBadgeEl = document.getElementById("rpr-role-badge");
    if (roleBadgeEl) {
      roleBadgeEl.textContent = _data.brain_label || _data.role || "–";
      roleBadgeEl.setAttribute("data-role", _data.role || "");
      roleBadgeEl.classList.remove("rpr-badge-hidden");
    }

    // Phase badge
    const phaseBadgeEl = document.getElementById("rpr-phase-badge");
    if (phaseBadgeEl) {
      phaseBadgeEl.textContent = "Phase " + (_data.phase || 1) + " · " + (_data.phase_name || "");
      phaseBadgeEl.setAttribute("data-phase", _data.phase || 1);
      phaseBadgeEl.classList.remove("rpr-badge-hidden");
    }

    // Inject floating badges into topbar if they don't exist yet
    const topbar = document.querySelector(".topbar, header.topbar, nav.topbar");
    if (topbar) {
      if (!document.getElementById("rpr-role-badge")) {
        const rb = document.createElement("span");
        rb.id = "rpr-role-badge";
        rb.className = "rpr-role-badge";
        rb.textContent = _data.brain_label || _data.role || "–";
        rb.setAttribute("data-role", _data.role || "");
        topbar.appendChild(rb);
      }
      if (!document.getElementById("rpr-phase-badge")) {
        const pb = document.createElement("span");
        pb.id = "rpr-phase-badge";
        pb.className = "rpr-phase-badge";
        pb.textContent = "Phase " + (_data.phase || 1) + " · " + (_data.phase_name || "");
        pb.setAttribute("data-phase", _data.phase || 1);
        topbar.appendChild(pb);
      }
    }
  }

  // -------------------------------------------------------------------------
  // Public API — window.RolePhaseRouter
  // -------------------------------------------------------------------------
  window.RolePhaseRouter = {
    /**
     * Returns true when the visibility data has been loaded from the API.
     */
    isLoaded: function () {
      return _loaded;
    },

    /**
     * Register a callback to be invoked once (or immediately if already loaded)
     * when the visibility data is available.
     */
    onReady: function (fn) {
      if (_loaded && _data) {
        try { fn(_data); } catch (_) {}
      } else {
        _listeners.push(fn);
      }
    },

    /**
     * Returns true if the given module is visible for the current role+phase.
     * @param {string} moduleId
     * @returns {boolean}
     */
    isModuleVisible: function (moduleId) {
      if (!_data) return false;
      return (_data.visible_modules || []).includes(moduleId);
    },

    /**
     * Returns true if the given action is allowed for the current role+phase.
     * @param {string} actionId
     * @returns {boolean}
     */
    isActionAllowed: function (actionId) {
      if (!_data) return false;
      return (_data.visible_actions || []).includes(actionId);
    },

    /**
     * Returns true if the given dashboard is visible for the current role+phase.
     * @param {string} dashboardId
     * @returns {boolean}
     */
    isDashboardVisible: function (dashboardId) {
      if (!_data) return false;
      return (_data.visible_dashboards || []).includes(dashboardId);
    },

    /**
     * Returns the current user's role string.
     * @returns {string}
     */
    getCurrentRole: function () {
      return (_data && _data.role) || "candidate";
    },

    /**
     * Returns the current active phase number.
     * @returns {number}
     */
    getCurrentPhase: function () {
      return (_data && _data.phase) || 1;
    },

    /**
     * Returns the owner brain id for the current role.
     * @returns {string}
     */
    getOwnerBrain: function () {
      return (_data && _data.owner_brain) || "public_agent";
    },

    /**
     * Returns the full raw visibility payload (for advanced use).
     * @returns {object|null}
     */
    getRawData: function () {
      return _data;
    },

    /**
     * Re-apply nav visibility rules to any newly added elements.
     */
    refresh: function () {
      _applyNavVisibility();
      _renderBadges();
    },
  };

  // -------------------------------------------------------------------------
  // Bootstrap on DOM ready
  // -------------------------------------------------------------------------
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _fetchVisibility);
  } else {
    _fetchVisibility();
  }
})();
