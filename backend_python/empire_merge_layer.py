"""
empire_merge_layer.py — Empire integration orchestration layer.

This module is the thin glue that:
  1. Defines the shared CARBON_MODES and NEWS_FEEDS constants.
  2. Creates and wires the shared carbon_events list and emit_carbon helper.
  3. Initialises all empire-domain database tables.
  4. Mounts focused sub-routers (ATS, Network, HQ, Carbon, Intel, Media, Voice).

Route paths are not changed – all /api/* and page paths remain identical.
"""
import json
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Shared constants – consumed by sub-routers via ctx
# ---------------------------------------------------------------------------

CARBON_MODES: Dict[str, Dict[str, str]] = {
    "graphene": {
        "name": "Graphene-Mind",
        "desc": "Mass parallel signal mesh across the empire.",
        "use": "Network signals, broad intelligence, multi-lane scanning.",
        "color": "#90f2d2",
    },
    "diamond": {
        "name": "Diamond-Mind",
        "desc": "Deep single-focus analysis with hard precision.",
        "use": "Scoring, strategy, difficult planning, critical review.",
        "color": "#87dfff",
    },
    "nanotube": {
        "name": "Nanotube-Mind",
        "desc": "Zero-loss relay between connected systems and stages.",
        "use": "Pipelines, imports, logistics, controlled flow.",
        "color": "#c1a1ff",
    },
}

NEWS_FEEDS: Dict[str, List[str]] = {
    "tech": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "india_business": [
        "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "https://www.thehindubusinessline.com/feeder/default.rss",
    ],
    "hiring": [
        "https://www.linkedin.com/news/rss/",
        "https://blog.indeed.com/feed/",
    ],
    "ai": [
        "https://www.marktechpost.com/feed/",
        "https://openai.com/news/rss.xml",
    ],
}


# ---------------------------------------------------------------------------
# Main installer
# ---------------------------------------------------------------------------

def install_empire_merge_layer(app, ctx: Dict[str, Any]) -> None:
    """
    Register all empire-domain routes on *app* using the shared context *ctx*.

    ctx keys expected (provided by app.py):
      db_exec, db_all, new_id, now_iso, session_user, generate_text,
      get_state, FRONTEND_DIR, AI_NAME, COMPANY_NAME, CORE_IDENTITY, log
    """
    db_exec = ctx["db_exec"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    log = ctx["log"]

    # ------------------------------------------------------------------
    # Shared in-memory carbon event bus (capped at 120 entries)
    # ------------------------------------------------------------------
    carbon_events: List[Dict[str, Any]] = []

    def emit_carbon(kind: str, payload: Dict[str, Any], mode: str = "graphene") -> None:
        """Append a carbon event to the in-memory bus and persist to DB."""
        event = {
            "id": new_id("carbon"),
            "kind": kind,
            "payload": payload,
            "mode": mode,
            "at": now_iso(),
        }
        carbon_events.append(event)
        if len(carbon_events) > 120:
            del carbon_events[:-120]
        try:
            db_exec(
                """
                INSERT INTO carbon_events(id,event_type,payload,carbon_mode,created_at)
                VALUES(?,?,?,?,?)
                """,
                (
                    event["id"],
                    kind,
                    json.dumps(payload, ensure_ascii=False)[:4000],
                    mode,
                    event["at"],
                ),
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Initialise empire-domain database tables
    # ------------------------------------------------------------------
    _init_tables(db_exec)

    # ------------------------------------------------------------------
    # Build the extended context for sub-routers
    # ------------------------------------------------------------------
    router_ctx: Dict[str, Any] = {
        **ctx,
        "carbon_events": carbon_events,
        "emit_carbon": emit_carbon,
        "CARBON_MODES": CARBON_MODES,
        "NEWS_FEEDS": NEWS_FEEDS,
    }

    # ------------------------------------------------------------------
    # Mount focused sub-routers
    # ------------------------------------------------------------------
    from routers.carbon_router import make_carbon_router
    from routers.ats_router import make_ats_router
    from routers.network_router import make_network_router
    from routers.hq_router import make_hq_router
    from routers.intel_router import make_intel_router
    from routers.media_router import make_media_router
    from routers.voice_profile_router import make_voice_profile_router

    app.include_router(make_carbon_router(router_ctx))
    app.include_router(make_ats_router(router_ctx))
    app.include_router(make_network_router(router_ctx))
    app.include_router(make_hq_router(router_ctx))
    app.include_router(make_intel_router(router_ctx))
    app.include_router(make_media_router(router_ctx))
    app.include_router(make_voice_profile_router(router_ctx))

    log.info("Empire merge layer: %d sub-routers mounted.", 7)


# ---------------------------------------------------------------------------
# DB table initialisation (kept here so it runs once at startup)
# ---------------------------------------------------------------------------

def _init_tables(db_exec) -> None:
    """Create all empire-domain tables if they do not already exist."""
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS ats_jobs(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT NOT NULL,
            department TEXT,
            location TEXT,
            description TEXT,
            urgency TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'open',
            ai_profile TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS ats_candidates(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            job_id TEXT,
            name TEXT NOT NULL,
            email TEXT,
            role TEXT,
            experience INTEGER DEFAULT 0,
            fit_score INTEGER DEFAULT 70,
            status TEXT DEFAULT 'applied',
            ai_strength TEXT,
            ai_concern TEXT,
            source TEXT DEFAULT 'manual',
            resume_text TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS network_connections(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT NOT NULL,
            title TEXT,
            company TEXT,
            linkedin TEXT,
            notes TEXT,
            created_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS network_posts(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            content TEXT NOT NULL,
            enhanced TEXT,
            kind TEXT DEFAULT 'post',
            likes INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS network_signals(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            query TEXT,
            analysis TEXT,
            carbon_mode TEXT DEFAULT 'graphene',
            created_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS hq_clients(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT NOT NULL,
            industry TEXT,
            value REAL DEFAULT 0,
            stage TEXT DEFAULT 'prospect',
            contact TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS hq_revenue(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            type TEXT DEFAULT 'revenue',
            amount REAL NOT NULL,
            source TEXT,
            category TEXT,
            created_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS hq_team(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT NOT NULL,
            role TEXT,
            email TEXT,
            department TEXT,
            created_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS carbon_bonds(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            bond_type TEXT,
            source_system TEXT,
            target_system TEXT,
            protocol_mode TEXT DEFAULT 'graphene',
            signal TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS carbon_events(
            id TEXT PRIMARY KEY,
            event_type TEXT,
            payload TEXT,
            carbon_mode TEXT,
            created_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS brain_knowledge(
            id TEXT PRIMARY KEY,
            brain_id TEXT NOT NULL,
            source_type TEXT,
            source_url TEXT,
            title TEXT,
            content TEXT,
            summary TEXT,
            keywords TEXT,
            relevance_score REAL DEFAULT 0.7,
            learned_at TEXT
        )
        """
    )
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS media_library(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            media_type TEXT,
            url TEXT,
            thumbnail TEXT,
            duration TEXT,
            source TEXT,
            added_at TEXT,
            play_count INTEGER DEFAULT 0,
            last_played TEXT
        )
        """
    )
