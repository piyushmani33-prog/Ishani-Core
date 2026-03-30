"""
Health check endpoint for deployment monitoring.

Register in app.py:
    from health_check import register_health_routes
    register_health_routes(app)
"""

import datetime


def register_health_routes(app):
    """Register /health and /api/health endpoints."""

    @app.get("/health")
    @app.get("/api/health")
    async def health_check():
        return {
            "status": "ok",
            "service": "ishani-core",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
