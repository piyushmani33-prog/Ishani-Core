"""
Tests for production middleware (RateLimitMiddleware, SecurityHeadersMiddleware,
DemoModeMiddleware, ErrorSanitizationMiddleware, RequestLoggingMiddleware).

Each middleware is tested in isolation using a minimal ASGI test app.
"""
import sys
import os

import pytest

BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techbuzz-full", "techbuzz-full", "backend_python",
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ---------------------------------------------------------------------------
# Try to import Starlette for middleware tests
# ---------------------------------------------------------------------------
try:
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient
    STARLETTE_AVAILABLE = True
except ImportError:
    STARLETTE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not STARLETTE_AVAILABLE,
    reason="starlette not installed — skipping middleware tests",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(middleware_class, middleware_kwargs=None, raise_in_handler=False):
    """Create a minimal Starlette app with the given middleware applied."""
    middleware_kwargs = middleware_kwargs or {}

    async def homepage(request: Request):
        if raise_in_handler:
            raise RuntimeError("intentional test error")
        return PlainTextResponse("ok")

    async def write_endpoint(request: Request):
        return JSONResponse({"written": True})

    app = Starlette(
        routes=[
            Route("/", homepage),
            Route("/write", write_endpoint, methods=["POST"]),
            Route("/health", homepage),
        ]
    )
    app.add_middleware(middleware_class, **middleware_kwargs)
    return app


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware:
    """Test the in-memory sliding-window rate limiter."""

    def test_allows_requests_under_limit(self):
        from middleware import RateLimitMiddleware, _rate_buckets
        _rate_buckets.clear()

        app = _make_app(RateLimitMiddleware, {"requests_per_minute": 10})
        client = TestClient(app, raise_server_exceptions=False)

        for _ in range(5):
            resp = client.get("/")
            assert resp.status_code == 200

    def test_blocks_requests_over_limit(self):
        from middleware import RateLimitMiddleware, _rate_buckets
        _rate_buckets.clear()

        app = _make_app(RateLimitMiddleware, {"requests_per_minute": 3})
        client = TestClient(app, raise_server_exceptions=False)

        for _ in range(3):
            client.get("/")

        resp = client.get("/")
        assert resp.status_code == 429

    def test_rate_limit_response_has_retry_after(self):
        from middleware import RateLimitMiddleware, _rate_buckets
        _rate_buckets.clear()

        app = _make_app(RateLimitMiddleware, {"requests_per_minute": 1})
        client = TestClient(app, raise_server_exceptions=False)

        client.get("/")
        resp = client.get("/")
        assert resp.status_code == 429
        assert "retry_after_seconds" in resp.json()

    def test_disabled_rate_limit_allows_all(self):
        from middleware import RateLimitMiddleware, _rate_buckets
        _rate_buckets.clear()

        app = _make_app(RateLimitMiddleware, {"requests_per_minute": 0})
        client = TestClient(app, raise_server_exceptions=False)

        for _ in range(20):
            resp = client.get("/")
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------

class TestSecurityHeadersMiddleware:
    """Test that security headers are added to all responses."""

    def test_x_content_type_options_header(self):
        from middleware import SecurityHeadersMiddleware
        app = _make_app(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_header(self):
        from middleware import SecurityHeadersMiddleware
        app = _make_app(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"

    def test_x_xss_protection_header(self):
        from middleware import SecurityHeadersMiddleware
        app = _make_app(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/")
        assert "x-xss-protection" in resp.headers

    def test_referrer_policy_header(self):
        from middleware import SecurityHeadersMiddleware
        app = _make_app(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/")
        assert "referrer-policy" in resp.headers


# ---------------------------------------------------------------------------
# DemoModeMiddleware
# ---------------------------------------------------------------------------

class TestDemoModeMiddleware:
    """Test that write operations are blocked in demo mode."""

    def test_get_allowed_in_demo_mode(self):
        from middleware import DemoModeMiddleware
        app = _make_app(DemoModeMiddleware, {"demo_mode": True})
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/")
        assert resp.status_code == 200

    def test_post_blocked_in_demo_mode(self):
        from middleware import DemoModeMiddleware
        app = _make_app(DemoModeMiddleware, {"demo_mode": True})
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/write")
        assert resp.status_code == 403
        assert resp.json()["error"] == "demo_mode"

    def test_post_allowed_when_demo_mode_disabled(self):
        from middleware import DemoModeMiddleware
        app = _make_app(DemoModeMiddleware, {"demo_mode": False})
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/write")
        assert resp.status_code == 200

    def test_health_endpoint_allowed_in_demo_mode(self):
        from middleware import DemoModeMiddleware
        app = _make_app(DemoModeMiddleware, {"demo_mode": True})
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# ErrorSanitizationMiddleware
# ---------------------------------------------------------------------------

class TestErrorSanitizationMiddleware:
    """Test that unhandled exceptions return safe error JSON."""

    def test_sanitizes_error_in_production_mode(self):
        from middleware import ErrorSanitizationMiddleware

        async def crashing_handler(request: Request):
            raise RuntimeError("super secret internal error detail")

        from starlette.applications import Starlette
        from starlette.routing import Route
        app = Starlette(routes=[Route("/crash", crashing_handler)])
        app.add_middleware(ErrorSanitizationMiddleware, debug=False)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/crash")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] == "internal_server_error"
        # Stack trace / internal detail must NOT be in the response
        assert "super secret internal error detail" not in resp.text

    def test_debug_mode_includes_detail(self):
        from middleware import ErrorSanitizationMiddleware

        async def crashing_handler(request: Request):
            raise ValueError("debug detail visible")

        from starlette.applications import Starlette
        from starlette.routing import Route
        app = Starlette(routes=[Route("/crash", crashing_handler)])
        app.add_middleware(ErrorSanitizationMiddleware, debug=True)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/crash")
        assert resp.status_code == 500
        body = resp.json()
        assert "detail" in body
        assert "debug detail visible" in body["detail"]

    def test_normal_request_not_affected(self):
        from middleware import ErrorSanitizationMiddleware
        app = _make_app(ErrorSanitizationMiddleware, {"debug": False})
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/")
        assert resp.status_code == 200
