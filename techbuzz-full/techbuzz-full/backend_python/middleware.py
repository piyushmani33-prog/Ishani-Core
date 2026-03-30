"""
Production middleware for TechBuzz AI / Ishani-Core.

Provides:
- RateLimitMiddleware    — simple in-memory token bucket per IP
- SecurityHeadersMiddleware — adds standard security headers
- DemoModeMiddleware     — blocks write/delete endpoints in demo mode
- ErrorSanitizationMiddleware — catches unhandled exceptions, returns safe JSON
- RequestLoggingMiddleware   — structured request/response logging (sanitized)

Usage (in app.py, before any route registration):
    from middleware import apply_middleware
    apply_middleware(app, config)
"""

import json
import logging
import threading
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger("ishani.middleware")

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

# Simple in-memory store: {ip: [timestamp, ...]}
# Protected by _rate_lock for thread safety across concurrent requests.
_rate_buckets: dict = defaultdict(list)
_rate_lock = threading.Lock()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding-window rate limiter (in-memory, per IP address).

    Blocks IPs that exceed `requests_per_minute` within a 60-second window.
    Returns HTTP 429 with a JSON error body when the limit is exceeded.
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self.requests_per_minute <= 0:
            return await call_next(request)

        ip = self._get_client_ip(request)
        now = time.monotonic()
        window_start = now - 60.0

        with _rate_lock:
            timestamps = _rate_buckets[ip]
            # Prune timestamps outside the current window
            timestamps[:] = [t for t in timestamps if t > window_start]

            if len(timestamps) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests. Please wait before retrying.",
                        "retry_after_seconds": 60,
                    },
                    headers={"Retry-After": "60"},
                )

            timestamps.append(now)

        return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract the real client IP, respecting common proxy headers."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client:
            return request.client.host
        return "unknown"


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


# ---------------------------------------------------------------------------
# Demo Mode Guard
# ---------------------------------------------------------------------------

# HTTP methods that modify state and should be blocked in demo mode
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Prefixes that are always allowed even in demo mode (health checks, GET reads)
_DEMO_ALLOWED_PREFIXES = (
    "/health",
    "/ready",
    "/api/health",
    "/api/ready",
    "/static",
    "/frontend",
)


class DemoModeMiddleware(BaseHTTPMiddleware):
    """
    Blocks write/delete operations when DEMO_MODE is enabled.

    In demo mode:
    - All GET/HEAD/OPTIONS requests are allowed.
    - POST/PUT/PATCH/DELETE requests to non-excluded paths return HTTP 403.
    """

    def __init__(self, app: ASGIApp, demo_mode: bool = False) -> None:
        super().__init__(app)
        self.demo_mode = demo_mode

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.demo_mode:
            return await call_next(request)

        if request.method in _UNSAFE_METHODS:
            path = request.url.path
            # Allow safe prefixes through even in demo mode
            if not any(path.startswith(p) for p in _DEMO_ALLOWED_PREFIXES):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "demo_mode",
                        "message": (
                            "This instance is running in demo mode. "
                            "Write and delete operations are disabled."
                        ),
                    },
                )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Error Sanitization
# ---------------------------------------------------------------------------

class ErrorSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled exceptions and returns a safe JSON error response.

    In non-debug mode, stack traces and internal details are hidden.
    All unhandled errors are logged server-side for debugging.
    """

    def __init__(self, app: ASGIApp, debug: bool = False) -> None:
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception(
                "Unhandled exception on %s %s", request.method, request.url.path
            )
            body: dict = {
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please try again.",
            }
            if self.debug:
                body["detail"] = str(exc)
                body["type"] = type(exc).__name__
            return JSONResponse(status_code=500, content=body)


# ---------------------------------------------------------------------------
# Request Logging
# ---------------------------------------------------------------------------

# Headers that must never appear in logs
_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-ishani-session",
    "set-cookie",
    "x-api-key",
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured request/response logging middleware.

    Logs method, path, status code, and duration.
    Sensitive headers are redacted from logs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        logger.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


# ---------------------------------------------------------------------------
# Convenience: apply all middleware at once
# ---------------------------------------------------------------------------

def apply_middleware(app: ASGIApp, config) -> None:
    """
    Apply all production middleware to the given ASGI app in the correct order.

    The `config` argument should be an AppConfig instance (or any object with
    the same attributes: demo_mode, debug, rate_limit_per_minute).

    Call this before registering any routes.

    Example:
        from config import AppConfig
        from middleware import apply_middleware

        config = AppConfig.from_env()
        apply_middleware(app, config)
    """
    # Applied in reverse order (last added = outermost wrapper = first to run)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorSanitizationMiddleware, debug=config.debug)
    app.add_middleware(DemoModeMiddleware, demo_mode=config.demo_mode)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware, requests_per_minute=config.rate_limit_per_minute
    )
