/* brain-reputation.js — Dashboard logic for the Brain Reputation & Scheduling page */
/* Uses fetch() to call the backend API endpoints.  No auto-send of external comms. */

(function () {
  "use strict";

  // ── Helpers ──────────────────────────────────────────────────────────────

  function fmt(val) {
    if (val === null || val === undefined) return "—";
    return val;
  }

  function pct(score) {
    return Math.round((score || 0) * 100) + "%";
  }

  function scoreClass(score) {
    if (score >= 0.6) return "high";
    if (score >= 0.35) return "medium";
    return "low";
  }

  function barWidth(score) {
    return Math.min(Math.round((score || 0) * 100), 100) + "%";
  }

  function statusPill(status) {
    const s = (status || "").toLowerCase();
    return `<span class="br-pill ${s}">${s}</span>`;
  }

  function relTime(isoStr) {
    if (!isoStr) return "—";
    try {
      const d = new Date(isoStr);
      const diff = Date.now() - d.getTime();
      if (diff < 60000) return "just now";
      if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
      if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
      return d.toLocaleDateString();
    } catch (_) {
      return isoStr;
    }
  }

  function escHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── Trust Scores Panel ───────────────────────────────────────────────────

  async function loadTrustScores() {
    const panel = document.getElementById("trustPanel");
    try {
      const res = await fetch("/api/reputation/leaderboard");
      const data = await res.json();
      const list = data.leaderboard || [];
      if (list.length === 0) {
        panel.innerHTML = '<div class="br-empty">No reputation data yet.</div>';
        return;
      }
      panel.innerHTML = list
        .map(
          (r) => `
        <div class="br-brain-row">
          <div class="br-brain-row-header">
            <span class="br-brain-id">${escHtml(r.brain_id)}</span>
            <span class="br-trust-badge ${scoreClass(r.trust_score)}">
              Trust ${pct(r.trust_score)}
            </span>
          </div>
          <div class="br-bar-row">
            <span class="br-bar-label">Reliability</span>
            <div class="br-bar-track">
              <div class="br-bar-fill reliability" style="width:${barWidth(r.reliability_score)}"></div>
            </div>
            <span class="br-bar-val">${pct(r.reliability_score)}</span>
          </div>
          <div class="br-bar-row">
            <span class="br-bar-label">Usefulness</span>
            <div class="br-bar-track">
              <div class="br-bar-fill usefulness" style="width:${barWidth(r.usefulness_score)}"></div>
            </div>
            <span class="br-bar-val">${pct(r.usefulness_score)}</span>
          </div>
          <div class="br-bar-row">
            <span class="br-bar-label">Trust</span>
            <div class="br-bar-track">
              <div class="br-bar-fill trust ${scoreClass(r.trust_score) === "low" ? "low" : ""}"
                   style="width:${barWidth(r.trust_score)}"></div>
            </div>
            <span class="br-bar-val">${pct(r.trust_score)}</span>
          </div>
        </div>`
        )
        .join("");
    } catch (err) {
      panel.innerHTML = `<div class="br-empty">Error loading trust scores: ${escHtml(err.message)}</div>`;
    }
  }

  // ── Scheduler Status ─────────────────────────────────────────────────────

  async function loadSchedulerStatus() {
    try {
      const res = await fetch("/api/schedules/status");
      const data = await res.json();
      const running = data.running === true;
      const dot = document.getElementById("schedDot");
      const label = document.getElementById("schedStatusLabel");
      dot.className = "br-sched-dot" + (running ? " running" : "");
      label.textContent = running
        ? `Scheduler running — ticks every ${data.tick_interval_seconds}s`
        : "Scheduler stopped";
    } catch (_) {
      document.getElementById("schedStatusLabel").textContent = "Status unavailable";
    }
  }

  // ── Schedules Table ───────────────────────────────────────────────────────

  async function loadSchedules() {
    const tbody = document.getElementById("schedulesBody");
    try {
      const res = await fetch("/api/schedules");
      const data = await res.json();
      const list = data.schedules || [];
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="br-empty">No schedules defined.</td></tr>';
        return;
      }
      tbody.innerHTML = list
        .map(
          (s) => `<tr>
          <td>${escHtml(s.brain_id)}</td>
          <td>${escHtml(s.task_type)}</td>
          <td>${s.interval_seconds}s</td>
          <td>${s.max_runs_per_hour}</td>
          <td>${escHtml(s.purpose || "—")}</td>
          <td>${relTime(s.next_run_at)}</td>
          <td>${s.active ? '<span class="br-pill active">active</span>' : '<span class="br-pill skipped">paused</span>'}</td>
        </tr>`
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="br-empty">Error: ${escHtml(err.message)}</td></tr>`;
    }
  }

  // ── Recent Runs ───────────────────────────────────────────────────────────

  async function loadRecentRuns() {
    const tbody = document.getElementById("runsBody");
    // Pull runs for all brains by fetching schedules first, then per-brain runs
    try {
      const schedRes = await fetch("/api/schedules");
      const schedData = await schedRes.json();
      const brainIds = [
        ...new Set((schedData.schedules || []).map((s) => s.brain_id)),
      ];

      if (brainIds.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="br-empty">No runs recorded yet.</td></tr>';
        return;
      }

      const allRuns = [];
      await Promise.all(
        brainIds.map(async (bid) => {
          try {
            const r = await fetch(`/api/schedules/${encodeURIComponent(bid)}/runs`);
            const d = await r.json();
            (d.runs || []).forEach((run) => allRuns.push(run));
          } catch (fetchErr) {
            console.warn(`brain-reputation: failed to load runs for brain '${bid}':`, fetchErr);
          }
        })
      );

      allRuns.sort((a, b) => (b.ran_at || "").localeCompare(a.ran_at || ""));
      const recent = allRuns.slice(0, 50);

      if (recent.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="br-empty">No runs recorded yet.</td></tr>';
        return;
      }

      tbody.innerHTML = recent
        .map(
          (run) => `<tr>
          <td>${escHtml(run.brain_id)}</td>
          <td>${escHtml(run.task_type)}</td>
          <td>${statusPill(run.status)}</td>
          <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
              title="${escHtml(run.detail)}">${escHtml(run.detail || "—")}</td>
          <td>${relTime(run.ran_at)}</td>
        </tr>`
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" class="br-empty">Error: ${escHtml(err.message)}</td></tr>`;
    }
  }

  // ── Weak Brains ───────────────────────────────────────────────────────────

  async function loadWeakBrains() {
    const panel = document.getElementById("weakPanel");
    try {
      const res = await fetch("/api/reputation/weak-brains");
      const data = await res.json();
      const list = data.weak_brains || [];
      if (list.length === 0) {
        panel.innerHTML = '<div class="br-empty">All brains are performing well ✓</div>';
        return;
      }
      panel.innerHTML = list
        .map(
          (r) => `
        <div class="br-weak-card">
          <div class="br-weak-name">${escHtml(r.brain_id)}</div>
          <div style="font-size:.78rem;color:var(--br-muted);margin-top:2px;">
            Trust: ${pct(r.trust_score)} &nbsp;·&nbsp;
            Reliability: ${pct(r.reliability_score)} &nbsp;·&nbsp;
            Usefulness: ${pct(r.usefulness_score)}
          </div>
          <div class="br-weak-rec">💡 ${escHtml(r.recommendation || "")}</div>
        </div>`
        )
        .join("");
    } catch (err) {
      panel.innerHTML = `<div class="br-empty">Error: ${escHtml(err.message)}</div>`;
    }
  }

  // ── Routing Decisions ─────────────────────────────────────────────────────

  async function loadRoutingDecisions() {
    const panel = document.getElementById("routingPanel");
    try {
      const res = await fetch("/api/routing/decisions");
      const data = await res.json();
      const list = data.decisions || [];
      if (list.length === 0) {
        panel.innerHTML = '<div class="br-empty">No routing decisions recorded yet.</div>';
        return;
      }
      panel.innerHTML = list
        .slice(0, 30)
        .map(
          (d) => `
        <div class="br-routing-row">
          <span class="br-routing-chosen">${escHtml(d.chosen_brain)}</span>
          <span class="br-routing-type">${escHtml(d.task_type)}</span>
          <span class="br-routing-reason">${escHtml(d.reasoning)}</span>
          <span class="br-routing-ts">${relTime(d.decided_at)}</span>
        </div>`
        )
        .join("");
    } catch (err) {
      panel.innerHTML = `<div class="br-empty">Error: ${escHtml(err.message)}</div>`;
    }
  }

  // ── Scheduler controls ────────────────────────────────────────────────────

  document.getElementById("btnStartSched").addEventListener("click", async () => {
    try {
      await fetch("/api/schedules/start", { method: "POST" });
      await loadSchedulerStatus();
    } catch (err) {
      alert("Could not start scheduler: " + err.message);
    }
  });

  document.getElementById("btnStopSched").addEventListener("click", async () => {
    try {
      await fetch("/api/schedules/stop", { method: "POST" });
      await loadSchedulerStatus();
    } catch (err) {
      alert("Could not stop scheduler: " + err.message);
    }
  });

  // ── Refresh ───────────────────────────────────────────────────────────────

  async function refreshAll() {
    await Promise.all([
      loadTrustScores(),
      loadSchedulerStatus(),
      loadSchedules(),
      loadRecentRuns(),
      loadWeakBrains(),
      loadRoutingDecisions(),
    ]);
  }

  document.getElementById("btnRefresh").addEventListener("click", refreshAll);

  // ── Initial load ──────────────────────────────────────────────────────────

  refreshAll();
})();
