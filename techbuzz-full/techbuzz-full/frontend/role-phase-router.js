/**
 * role-phase-router.js
 * ====================
 * Client-side Role + Phase Router for Ishani Core / TechBuzz
 *
 * On page load, fetches /api/role/visibility to get the combined role+phase
 * data and exposes a global window.RolePhaseRouter with the following API:
 *
 *   isModuleVisible(moduleId)      → boolean
 *   isActionAllowed(actionId)      → boolean
 *   isDashboardVisible(dashboardId)→ boolean
 *   getCurrentRole()               → string
 *   getCurrentPhase()              → number
 *   getOwnerBrain()                → string
 *
 * Navigation items that carry data-module, data-action, or data-dashboard
 * attributes are automatically shown/hidden based on the current visibility
 * rules once the router is ready.
 *
 * Usage in HTML:
 *   <script src="/frontend-assets/role-phase-router.js"></script>
 *
 *   Navigation links:
 *     <a href="/neural" data-dashboard="neural">Neural</a>
 *     <a href="/agent/console" data-module="agent">Agent Console</a>
 */

(function (global) {
  "use strict";

  // -------------------------------------------------------------------------
  // Internal state
  // -------------------------------------------------------------------------

  var _data = null; // raw payload from /api/role/visibility
  var _ready = false;
  var _readyCallbacks = [];

  // -------------------------------------------------------------------------
  // Fetch visibility data
  // -------------------------------------------------------------------------

  function _fetchVisibility() {
    return fetch("/api/role/visibility", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        if (!res.ok) {
          throw new Error("role-phase-router: /api/role/visibility returned " + res.status);
        }
        return res.json();
      })
      .then(function (payload) {
        _data = payload;
        _ready = true;
        _applyVisibility();
        _updateBadges();
        _readyCallbacks.forEach(function (cb) {
          try { cb(_data); } catch (e) { /* ignore */ }
        });
      })
      .catch(function (err) {
        console.warn("role-phase-router: could not load visibility data —", err.message);
        // Install a permissive fallback so the UI is not broken
        _data = {
          ok: false,
          role: "operator_research",
          owner_brain: "operations_executive",
          label: "Operations Brain",
          authenticated: false,
          phase: { phase: 1, name: "Recruitment Launch", all_access: false,
                   visible_modules: [], visible_actions: [], visible_dashboards: [] },
        };
        _ready = true;
        _readyCallbacks.forEach(function (cb) {
          try { cb(_data); } catch (e) { /* ignore */ }
        });
      });
  }

  // -------------------------------------------------------------------------
  // Visibility helpers
  // -------------------------------------------------------------------------

  function _phaseData() {
    return (_data && _data.phase) ? _data.phase : { all_access: false, visible_modules: [], visible_actions: [], visible_dashboards: [] };
  }

  function _inList(list, value) {
    if (!Array.isArray(list)) return false;
    return list.indexOf("ALL") !== -1 || list.indexOf(value) !== -1;
  }

  // -------------------------------------------------------------------------
  // DOM: apply visibility to nav items
  // -------------------------------------------------------------------------

  function _applyVisibility() {
    if (!_data) return;
    var ph = _phaseData();

    // data-module attributes
    document.querySelectorAll("[data-module]").forEach(function (el) {
      var mod = el.getAttribute("data-module");
      _setVisible(el, _inList(ph.visible_modules, mod));
    });

    // data-action attributes
    document.querySelectorAll("[data-action]").forEach(function (el) {
      var action = el.getAttribute("data-action");
      _setVisible(el, _inList(ph.visible_actions, action));
    });

    // data-dashboard attributes
    document.querySelectorAll("[data-dashboard]").forEach(function (el) {
      var dash = el.getAttribute("data-dashboard");
      _setVisible(el, _inList(ph.visible_dashboards, dash));
    });

    // Role-gated elements: data-role-required
    document.querySelectorAll("[data-role-required]").forEach(function (el) {
      var required = el.getAttribute("data-role-required").split(",").map(function (r) { return r.trim(); });
      var currentRole = _data.role || "operator_research";
      _setVisible(el, required.indexOf(currentRole) !== -1 || required.indexOf("ALL") !== -1);
    });

    // Restricted-access overlays for dashboards not yet unlocked
    document.querySelectorAll("[data-restricted-dashboard]").forEach(function (el) {
      var dash = el.getAttribute("data-restricted-dashboard");
      var isVisible = _inList(ph.visible_dashboards, dash);
      if (!isVisible) {
        el.classList.add("rp-restricted");
        if (!el.querySelector(".rp-restricted-overlay")) {
          var overlay = document.createElement("div");
          overlay.className = "rp-restricted-overlay";

          var msg = document.createElement("div");
          msg.className = "rp-restricted-message";

          var lockIcon = document.createElement("span");
          lockIcon.className = "rp-lock-icon";
          lockIcon.textContent = "🔒";

          var title = document.createElement("strong");
          title.textContent = "Unlocks in a later phase";

          var desc = document.createElement("p");
          desc.textContent = "This feature is not yet available in Phase " + ph.phase + ".";

          msg.appendChild(lockIcon);
          msg.appendChild(title);
          msg.appendChild(desc);
          overlay.appendChild(msg);
          el.appendChild(overlay);
        }
      } else {
        el.classList.remove("rp-restricted");
        var existingOverlay = el.querySelector(".rp-restricted-overlay");
        if (existingOverlay) existingOverlay.remove();
      }
    });
  }

  function _setVisible(el, visible) {
    if (visible) {
      el.classList.remove("rp-hidden");
      el.removeAttribute("aria-hidden");
    } else {
      el.classList.add("rp-hidden");
      el.setAttribute("aria-hidden", "true");
    }
  }

  // -------------------------------------------------------------------------
  // DOM: update role/phase badges
  // -------------------------------------------------------------------------

  function _updateBadges() {
    if (!_data) return;
    var ph = _phaseData();

    // Role badge(s)
    document.querySelectorAll(".rp-role-badge").forEach(function (el) {
      el.textContent = _data.label || _data.role || "—";
      el.setAttribute("data-role", _data.role || "");
    });

    // Phase badge(s)
    document.querySelectorAll(".rp-phase-badge").forEach(function (el) {
      el.textContent = "Phase " + ph.phase + " — " + (ph.name || "");
      el.setAttribute("data-phase", ph.phase || "");
    });

    // Owner brain label(s)
    document.querySelectorAll(".rp-brain-label").forEach(function (el) {
      el.textContent = _data.label || "—";
    });
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  var RolePhaseRouter = {
    /**
     * Register a callback to be invoked once visibility data is loaded.
     * If data is already loaded, the callback fires immediately.
     */
    onReady: function (cb) {
      if (_ready) {
        try { cb(_data); } catch (e) { /* ignore */ }
      } else {
        _readyCallbacks.push(cb);
      }
    },

    /** Returns true if the given module is visible in the current phase. */
    isModuleVisible: function (moduleId) {
      if (!_ready) return true; // permissive before load
      return _inList(_phaseData().visible_modules, moduleId);
    },

    /** Returns true if the given action is allowed in the current phase. */
    isActionAllowed: function (actionId) {
      if (!_ready) return true;
      return _inList(_phaseData().visible_actions, actionId);
    },

    /** Returns true if the given dashboard is visible in the current phase. */
    isDashboardVisible: function (dashboardId) {
      if (!_ready) return true;
      return _inList(_phaseData().visible_dashboards, dashboardId);
    },

    /** Returns the current role string. */
    getCurrentRole: function () {
      return (_data && _data.role) ? _data.role : "operator_research";
    },

    /** Returns the current phase number. */
    getCurrentPhase: function () {
      return _phaseData().phase || 1;
    },

    /** Returns the owner brain id for the current role. */
    getOwnerBrain: function () {
      return (_data && _data.owner_brain) ? _data.owner_brain : "operations_executive";
    },

    /** Returns whether the user is authenticated. */
    isAuthenticated: function () {
      return !!((_data && _data.authenticated));
    },

    /** Re-apply visibility rules (useful after dynamic nav updates). */
    refresh: function () {
      _applyVisibility();
      _updateBadges();
    },

    /** Reload visibility data from the server then re-apply. */
    reload: function () {
      _ready = false;
      return _fetchVisibility();
    },
  };

  // -------------------------------------------------------------------------
  // Bootstrap
  // -------------------------------------------------------------------------

  function _init() {
    _fetchVisibility();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _init);
  } else {
    _init();
  }

  // Expose globally
  global.RolePhaseRouter = RolePhaseRouter;

})(window);
