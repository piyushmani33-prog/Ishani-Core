"""
Tests for the centralized AppConfig module.

Tests cover:
- Default values
- Loading from environment variables
- Validation warnings
- Demo mode flag
- AI provider detection
- Safe dictionary representation
"""
import os
import sys

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techbuzz-full", "techbuzz-full", "backend_python",
)


def _import_config():
    """Import AppConfig from backend_python/config.py."""
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    from config import AppConfig  # noqa: PLC0415
    return AppConfig


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConfigDefaults:
    """Test that default values are sane."""

    def test_default_port(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert config.port == 8000

    def test_default_host(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert config.host == "0.0.0.0"

    def test_default_demo_mode_is_false(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert config.demo_mode is False

    def test_default_admin_routes_enabled_is_true(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert config.admin_routes_enabled is True

    def test_default_rate_limit(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert config.rate_limit_per_minute == 60

    def test_default_allowed_origins_is_localhost(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert "http://localhost" in config.allowed_origins

    def test_default_database_url_is_sqlite(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert "sqlite" in config.database_url

    def test_default_no_ai_keys(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert config.openai_api_key == ""
        assert config.gemini_api_key == ""
        assert config.anthropic_api_key == ""


class TestConfigFromEnv:
    """Test loading configuration from environment variables."""

    def test_port_from_env(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("PORT", "9000")
        config = AppConfig.from_env()
        assert config.port == 9000

    def test_demo_mode_from_env(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("DEMO_MODE", "true")
        config = AppConfig.from_env()
        assert config.demo_mode is True

    def test_demo_mode_case_insensitive(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("DEMO_MODE", "TRUE")
        config = AppConfig.from_env()
        assert config.demo_mode is True

    def test_admin_routes_disabled_from_env(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("ADMIN_ROUTES_ENABLED", "false")
        config = AppConfig.from_env()
        assert config.admin_routes_enabled is False

    def test_log_level_uppercased(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("LOG_LEVEL", "debug")
        config = AppConfig.from_env()
        assert config.log_level == "DEBUG"

    def test_allowed_origins_parsed(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.com, https://b.com")
        config = AppConfig.from_env()
        # Check exact list membership (not substring matching)
        assert config.allowed_origins == ["https://a.com", "https://b.com"]

    def test_session_secret_from_env(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("SESSION_SECRET", "abc123")
        config = AppConfig.from_env()
        assert config.session_secret == "abc123"

    def test_openai_key_from_env(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        config = AppConfig.from_env()
        assert config.openai_api_key == "sk-test-key"

    def test_rate_limit_from_env(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "30")
        config = AppConfig.from_env()
        assert config.rate_limit_per_minute == 30


class TestConfigValidation:
    """Test the validate() method returns appropriate warnings."""

    def test_no_warnings_with_full_config(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("SESSION_SECRET", "a" * 64)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("DEBUG", "false")
        config = AppConfig.from_env()
        warnings = config.validate()
        # No critical warnings
        assert not any("SESSION_SECRET" in w for w in warnings)

    def test_warning_when_no_session_secret(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("SESSION_SECRET", "")
        config = AppConfig.from_env()
        warnings = config.validate()
        assert any("SESSION_SECRET" in w for w in warnings)

    def test_warning_when_no_ai_keys(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        config = AppConfig.from_env()
        warnings = config.validate()
        assert any("AI provider" in w or "fallback" in w.lower() for w in warnings)

    def test_warning_in_demo_mode(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("DEMO_MODE", "true")
        config = AppConfig.from_env()
        warnings = config.validate()
        assert any("demo" in w.lower() for w in warnings)

    def test_warning_when_debug_true(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("DEBUG", "true")
        config = AppConfig.from_env()
        warnings = config.validate()
        assert any("debug" in w.lower() for w in warnings)

    def test_warning_for_wildcard_origins(self, monkeypatch):
        AppConfig = _import_config()
        monkeypatch.setenv("ALLOWED_ORIGINS", "*")
        config = AppConfig.from_env()
        warnings = config.validate()
        assert any("*" in w or "wildcard" in w.lower() or "any origin" in w.lower() for w in warnings)


class TestConfigProperties:
    """Test computed properties."""

    def test_has_ai_provider_false_with_no_keys(self):
        AppConfig = _import_config()
        config = AppConfig()
        assert config.has_ai_provider is False

    def test_has_ai_provider_true_with_openai(self):
        AppConfig = _import_config()
        config = AppConfig(openai_api_key="sk-test")
        assert config.has_ai_provider is True

    def test_has_ai_provider_true_with_gemini(self):
        AppConfig = _import_config()
        config = AppConfig(gemini_api_key="AIza-test")
        assert config.has_ai_provider is True

    def test_effective_session_secret_uses_provided(self):
        AppConfig = _import_config()
        config = AppConfig(session_secret="mysecret")
        assert config.effective_session_secret == "mysecret"

    def test_effective_session_secret_generates_when_missing(self):
        AppConfig = _import_config()
        config = AppConfig(session_secret="")
        secret = config.effective_session_secret
        assert len(secret) == 64  # 32 bytes = 64 hex chars
        # Should be stable: same value on repeated access
        assert config.effective_session_secret == secret

    def test_as_safe_dict_redacts_api_keys(self):
        AppConfig = _import_config()
        config = AppConfig(openai_api_key="sk-real-key", session_secret="real-secret")
        safe = config.as_safe_dict()
        # The safe dict must not contain the actual key value
        assert "sk-real-key" not in str(safe)
        assert "real-secret" not in str(safe)
        # But it should indicate that a provider is configured
        assert safe["ai_providers"]["openai"] is True
        assert safe["session_secret_set"] is True

    def test_as_safe_dict_redacts_db_password(self):
        AppConfig = _import_config()
        config = AppConfig(database_url="postgresql://user:s3cr3t@host/db")
        safe = config.as_safe_dict()
        # Should not contain the full URL with password
        assert "s3cr3t" not in str(safe)
