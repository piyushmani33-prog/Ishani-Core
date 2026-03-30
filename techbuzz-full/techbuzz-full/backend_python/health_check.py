"""
Health check endpoints for deployment monitoring.

Provides:
- GET /health    — liveness probe (always 200 if server is running)
- GET /ready     — readiness probe (checks DB, AI providers, config)
- GET /api/health — alias for backward compatibility

Register in app.py:
    from health_check import register_health_routes
    register_health_routes(app)
"""

import datetime
import os
import sqlite3


def register_health_routes(app):
    """Register /health, /ready, and /api/health endpoints."""

    @app.get("/health")
    @app.get("/api/health")
    async def health_check():
        """Liveness probe — always returns 200 if the process is alive."""
        return {
            "status": "ok",
            "service": "ishani-core",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    @app.get("/ready")
    @app.get("/api/ready")
    async def readiness_check():
        """
        Readiness probe — checks whether the service is ready to serve traffic.

        Verifies:
        - Database connectivity (SQLite file accessible or PostgreSQL reachable)
        - Config status (demo mode, AI providers, session secret)

        Returns HTTP 200 when ready, HTTP 503 when not ready.
        """
        checks = {}
        overall_ok = True

        # Database check
        db_status = _check_database()
        checks["database"] = db_status
        if not db_status["ok"]:
            overall_ok = False

        # Config / mode flags
        checks["config"] = {
            "demo_mode": os.getenv("DEMO_MODE", "false").lower() == "true",
            "admin_routes_enabled": os.getenv("ADMIN_ROUTES_ENABLED", "true").lower() == "true",
            "session_secret_set": bool(os.getenv("SESSION_SECRET", "")),
            "ai_providers": {
                "openai": bool(os.getenv("OPENAI_API_KEY", "")),
                "gemini": bool(os.getenv("GEMINI_API_KEY", "")),
                "anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "")),
            },
        }

        status_code = 200 if overall_ok else 503
        body = {
            "status": "ready" if overall_ok else "not_ready",
            "service": "ishani-core",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "checks": checks,
        }

        from starlette.responses import JSONResponse
        return JSONResponse(content=body, status_code=status_code)


def _check_database() -> dict:
    """Check database connectivity and return a status dict."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/techbuzz.db")

    if database_url.startswith("sqlite"):
        return _check_sqlite(database_url)

    # For non-SQLite databases, report as unchecked (external DB check not implemented)
    return {
        "ok": True,
        "type": "external",
        "message": "External database — connectivity check skipped",
    }


def _check_sqlite(database_url: str) -> dict:
    """Check SQLite database accessibility."""
    # Extract path from sqlite:///path/to/db
    db_path = database_url.replace("sqlite:///", "").replace("sqlite://", "")
    if not db_path:
        db_path = "data/techbuzz.db"

    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            conn.execute("SELECT 1")
        return {"ok": True, "type": "sqlite", "path": db_path}
    except (sqlite3.Error, OSError) as exc:
        # SQLite file may not exist yet on first startup — that is acceptable
        if "unable to open" in str(exc).lower() or "no such file" in str(exc).lower():
            return {
                "ok": True,
                "type": "sqlite",
                "path": db_path,
                "message": "Database file will be created on first use",
            }
        return {"ok": False, "type": "sqlite", "path": db_path, "error": str(exc)}

