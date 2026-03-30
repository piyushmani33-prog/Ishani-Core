/**
 * role-phase-router.js
 *
 * Role-Aware Phase Router for TechBuzz / Ishani Core.
 *
 * On page load this module fetches /api/role/visibility to get the combined
 * role + phase data, then controls navigation visibility based on the rules
 * returned by the server.  All advanced modules remain in the DOM but are
 * hidden until the active phase exposes them.
 *
 * Usage
 * -----
 *   <script src="role-phase-router.js"></script>
 *
 * After the script loads, a global window.RolePhaseRouter object is available:
 *
 *   RolePhaseRouter.isModuleVisible(moduleId)   → boolean
 *   RolePhaseRouter.isActionAllowed(actionId)   → boolean
 *   RolePhaseRouter.isDashboardVisible(dashId)  → boolean
 *   RolePhaseRouter.getCurrentRole()            → string
 *   RolePhaseRouter.getCurrentPhase()           → number
 *   RolePhaseRouter.getOwnerBrain()             → string
 */

(function () {
  "use strict";

  // -------------------------------------------------------------------------
  // Internal state
  // -------------------------------------------------------------------------

  var _state = {
    role: null,
    phase: null,
    phaseName: null,
    ownerBrain: null,
    label: null,
    visibleModules: [],
    visibleActions: [],
    visibleDashboards: [],
    hiddenAdvanced: [],
    loaded: false,
  };

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  function isModuleVisible(moduleId) {
    if (!_state.loaded) return true; // fail-open before data arrives
    if (_state.visibleModules.indexOf("*") !== -1) return true;
    return _state.visibleModules.indexOf(moduleId) !== -1;
  }

  function isActionAllowed(actionId) {
    if (!_state.loaded) return true;
    if (_state.visibleActions.indexOf("*") !== -1) return true;
    return _state.visibleActions.indexOf(actionId) !== -1;
  }

  function isDashboardVisible(dashboardId) {
    if (!_state.loaded) return true;
    if (_state.visibleDashboards.indexOf("*") !== -1) return true;
    return _state.visibleDashboards.indexOf(dashboardId) !== -1;
  }

  function getCurrentRole() {
    return _state.role;
  }

  function getCurrentPhase() {
    return _state.phase;
  }

  function getOwnerBrain() {
    return _state.ownerBrain;
  }

  // -------------------------------------------------------------------------
  // DOM helpers
  // -------------------------------------------------------------------------

  function _applyVisibility() {
    // Nav items with data-module attribute
    document.querySelectorAll("[data-module]").forEach(function (el) {
      var mod = el.getAttribute("data-module");
      if (!isModuleVisible(mod)) {
        el.classList.add("rpr-hidden");
      } else {
        el.classList.remove("rpr-hidden");
      }
    });

    // Nav items with data-dashboard attribute
    document.querySelectorAll("[data-dashboard]").forEach(function (el) {
      var dash = el.getAttribute("data-dashboard");
      if (!isDashboardVisible(dash)) {
        el.classList.add("rpr-hidden");
      } else {
        el.classList.remove("rpr-hidden");
      }
    });

    // Nav items with data-action attribute
    document.querySelectorAll("[data-action]").forEach(function (el) {
      var action = el.getAttribute("data-action");
      if (!isActionAllowed(action)) {
        el.classList.add("rpr-hidden");
      } else {
        el.classList.remove("rpr-hidden");
      }
    });

    // Restricted overlay on sections with data-requires-dashboard
    document.querySelectorAll("[data-requires-dashboard]").forEach(function (el) {
      var dash = el.getAttribute("data-requires-dashboard");
      if (!isDashboardVisible(dash)) {
        el.classList.add("rpr-locked");
      } else {
        el.classList.remove("rpr-locked");
      }
    });

    _updateBadges();
  }

  function _updateBadges() {
    // Role badge
    document.querySelectorAll(".rpr-role-badge").forEach(function (el) {
      el.textContent = _state.label || _state.role || "—";
      el.setAttribute("data-role", _state.role || "");
    });

    // Phase badge
    document.querySelectorAll(".rpr-phase-badge").forEach(function (el) {
      if (_state.phase !== null) {
        el.textContent = "Phase " + _state.phase + " — " + (_state.phaseName || "");
        el.setAttribute("data-phase", _state.phase);
      }
    });
  }

  // -------------------------------------------------------------------------
  // Bootstrap
  // -------------------------------------------------------------------------

  function _load() {
    fetch("/api/role/visibility", { credentials: "same-origin" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        _state.role = data.role || null;
        _state.phase = data.phase !== undefined ? data.phase : null;
        _state.phaseName = data.phase_name || null;
        _state.ownerBrain = data.owner_brain || null;
        _state.label = data.label || null;
        _state.visibleModules = data.visible_modules || [];
        _state.visibleActions = data.visible_actions || [];
        _state.visibleDashboards = data.visible_dashboards || [];
        _state.hiddenAdvanced = data.hidden_advanced || [];
        _state.loaded = true;
        _applyVisibility();

        // Dispatch a custom event so other scripts can react
        document.dispatchEvent(
          new CustomEvent("rolePhaseRouterReady", { detail: _state })
        );
      })
      .catch(function (err) {
        console.warn("[RolePhaseRouter] Could not load visibility data:", err);
        // Fail-open: mark as loaded so the UI shows everything
        _state.loaded = true;
      });
  }

  // -------------------------------------------------------------------------
  // Expose global
  // -------------------------------------------------------------------------

  window.RolePhaseRouter = {
    isModuleVisible: isModuleVisible,
    isActionAllowed: isActionAllowed,
    isDashboardVisible: isDashboardVisible,
    getCurrentRole: getCurrentRole,
    getCurrentPhase: getCurrentPhase,
    getOwnerBrain: getOwnerBrain,
  };

  // Kick off on DOMContentLoaded (or immediately if already ready)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _load);
  } else {
    _load();
  }
})();
