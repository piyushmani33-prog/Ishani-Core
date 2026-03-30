"""
Centralized configuration management for TechBuzz AI / Ishani-Core.

Usage:
    from config import AppConfig
    config = AppConfig.from_env()
    warnings = config.validate()
    for w in warnings:
        print(f"[CONFIG WARNING] {w}")
"""

import os
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """Application configuration loaded from environment variables."""

    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Mode flags
    demo_mode: bool = False
    admin_routes_enabled: bool = True

    # Security
    session_secret: str = ""
    rate_limit_per_minute: int = 60
    allowed_origins: list = field(
        default_factory=lambda: ["http://localhost", "http://127.0.0.1"]
    )

    # AI Providers (all optional — built-in fallback used when none configured)
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_host: str = "http://localhost:11434"

    # Database
    database_url: str = "sqlite:///data/techbuzz.db"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create an AppConfig instance from environment variables."""
        return cls(
            port=int(os.getenv("PORT", "8000")),
            host=os.getenv("HOST", "0.0.0.0"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            demo_mode=os.getenv("DEMO_MODE", "false").lower() == "true",
            admin_routes_enabled=os.getenv("ADMIN_ROUTES_ENABLED", "true").lower() == "true",
            session_secret=os.getenv("SESSION_SECRET", ""),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            allowed_origins=[
                o.strip()
                for o in os.getenv(
                    "ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1"
                ).split(",")
                if o.strip()
            ],
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///data/techbuzz.db"),
        )

    def validate(self) -> list:
        """
        Validate configuration and return a list of warning strings.

        Returns an empty list if everything looks good.
        Warnings are non-fatal — the app can still start.
        """
        warnings = []

        if not self.session_secret:
            warnings.append(
                "SESSION_SECRET not set — sessions will not persist across restarts. "
                "Set SESSION_SECRET to a random 32-byte hex string."
            )

        if self.demo_mode:
            warnings.append(
                "DEMO_MODE=true — write and delete operations are disabled. "
                "Set DEMO_MODE=false for full functionality."
            )

        if not self.has_ai_provider:
            warnings.append(
                "No AI provider API keys configured "
                "(OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY). "
                "Using built-in fallback brain only."
            )

        if self.debug:
            warnings.append(
                "DEBUG=true — never enable debug mode in production. "
                "Stack traces will be visible in API responses."
            )

        if "*" in self.allowed_origins:
            warnings.append(
                "ALLOWED_ORIGINS contains '*' — this allows requests from any origin. "
                "Set explicit origins for production deployments."
            )

        if self.rate_limit_per_minute <= 0:
            warnings.append(
                "RATE_LIMIT_PER_MINUTE is 0 or negative — rate limiting is effectively disabled."
            )

        return warnings

    @property
    def has_ai_provider(self) -> bool:
        """Return True if at least one external AI provider API key is configured."""
        return bool(self.openai_api_key or self.gemini_api_key or self.anthropic_api_key)

    @property
    def effective_session_secret(self) -> str:
        """
        Return the session secret, generating a random one if not configured.

        NOTE: A generated secret is created once at class instantiation time
        and is stable for the lifetime of this config object. However, since
        it is not persisted, sessions will not survive an application restart.
        Set SESSION_SECRET in your environment for persistent sessions.
        """
        if self.session_secret:
            return self.session_secret
        # Use a stable random value per config instance (not per property access)
        if not hasattr(self, "_generated_secret"):
            object.__setattr__(self, "_generated_secret", os.urandom(32).hex())
        return self._generated_secret  # type: ignore[attr-defined]

    def as_safe_dict(self) -> dict:
        """
        Return a dictionary representation with secrets redacted.
        Safe to log or include in health check responses.
        """
        return {
            "port": self.port,
            "host": self.host,
            "debug": self.debug,
            "log_level": self.log_level,
            "demo_mode": self.demo_mode,
            "admin_routes_enabled": self.admin_routes_enabled,
            "session_secret_set": bool(self.session_secret),
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "allowed_origins": self.allowed_origins,
            "has_ai_provider": self.has_ai_provider,
            "ai_providers": {
                "openai": bool(self.openai_api_key),
                "gemini": bool(self.gemini_api_key),
                "anthropic": bool(self.anthropic_api_key),
                "ollama_host": self.ollama_host,
            },
            "database_url": (
                self.database_url.split("@")[-1]
                if "@" in self.database_url
                else self.database_url
            ),
        }
