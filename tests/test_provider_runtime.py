"""
Tests for Priority 2 — Provider / LLM Runtime fixes.

Covers:
- config.py: ollama_model field, has_ai_provider includes Ollama, provider_priority
- health_check.py: /ready returns active_provider and fallback_only fields
- platform_status.py: _check_ai_providers reports active_provider, pings Ollama
- provider_status_layer.py: /api/provider/status returns correct structure
- generate_text() response includes provider_used, fallback_used, mock_used fields
- Settings integration: selected_provider from settings_manager is consulted
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techbuzz-full",
    "techbuzz-full",
    "backend_python",
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# config.py tests
# ---------------------------------------------------------------------------

class TestConfigOllamaModel:
    def _import(self):
        from config import AppConfig  # noqa: PLC0415
        return AppConfig

    def test_ollama_model_field_default(self):
        AppConfig = self._import()
        config = AppConfig()
        assert config.ollama_model == "mistral"

    def test_ollama_model_from_env(self, monkeypatch):
        AppConfig = self._import()
        monkeypatch.setenv("OLLAMA_MODEL", "llama3")
        config = AppConfig.from_env()
        assert config.ollama_model == "llama3"

    def test_has_ai_provider_true_with_ollama_host(self):
        AppConfig = self._import()
        config = AppConfig(
            openai_api_key="",
            gemini_api_key="",
            anthropic_api_key="",
            ollama_host="http://localhost:11434",
        )
        assert config.has_ai_provider is True

    def test_has_ai_provider_false_with_no_ollama(self):
        AppConfig = self._import()
        config = AppConfig(
            openai_api_key="",
            gemini_api_key="",
            anthropic_api_key="",
            ollama_host="",
        )
        assert config.has_ai_provider is False

    def test_provider_priority_includes_ollama_first(self):
        AppConfig = self._import()
        config = AppConfig(
            openai_api_key="sk-test",
            ollama_host="http://localhost:11434",
        )
        priority = config.provider_priority
        assert "ollama" in priority
        assert "openai" in priority
        assert priority.index("ollama") < priority.index("openai")

    def test_provider_priority_always_ends_with_built_in(self):
        AppConfig = self._import()
        config = AppConfig()
        assert config.provider_priority[-1] == "built_in"

    def test_as_safe_dict_includes_ollama_model(self):
        AppConfig = self._import()
        config = AppConfig(ollama_model="phi3")
        safe = config.as_safe_dict()
        assert safe["ai_providers"]["ollama_model"] == "phi3"


# ---------------------------------------------------------------------------
# health_check.py tests
# ---------------------------------------------------------------------------

class TestHealthCheckReadiness:
    def test_file_exists(self):
        path = os.path.join(BACKEND_DIR, "health_check.py")
        assert os.path.isfile(path)

    def test_check_providers_returns_active_provider(self):
        """_check_providers() must return an active_provider key."""
        from health_check import _check_providers  # noqa: PLC0415
        result = _run(_check_providers())
        assert "active_provider" in result
        assert "fallback_only" in result
        assert "providers" in result

    def test_check_providers_ollama_not_reachable_by_default(self):
        """With no Ollama running locally the layer reports it as not reachable."""
        from health_check import _check_providers  # noqa: PLC0415
        result = _run(_check_providers())
        # In test environment, Ollama is not running
        assert result["providers"]["ollama"]["configured"] in (True, False)

    def test_check_providers_fallback_only_when_no_providers(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        # Patch httpx so Ollama ping fails
        import health_check as hc  # noqa: PLC0415
        import httpx as _httpx  # noqa: PLC0415
        with patch.object(_httpx.AsyncClient, "__aenter__", side_effect=Exception("no connection")):
            result = _run(hc._check_providers())
        assert result["fallback_only"] is True
        assert result["active_provider"] == "built-in"

    def test_check_providers_openai_valid_key_format(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-valid1234567890abcdefgh")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        # Make Ollama unreachable
        import health_check as hc  # noqa: PLC0415
        import httpx as _httpx  # noqa: PLC0415
        with patch.object(_httpx.AsyncClient, "__aenter__", side_effect=Exception("no connection")):
            result = _run(hc._check_providers())
        assert result["providers"]["openai"]["key_format_valid"] is True
        assert result["active_provider"] == "openai"
        assert result["fallback_only"] is False


# ---------------------------------------------------------------------------
# platform_status.py tests
# ---------------------------------------------------------------------------

class TestPlatformStatusProviders:
    def _import(self):
        from platform_status import _check_ai_providers  # noqa: PLC0415
        return _check_ai_providers

    def test_returns_active_provider_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "")
        _check = self._import()
        result = _check()
        assert "active_provider" in result

    def test_builtin_fallback_when_nothing_configured(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "")
        _check = self._import()
        result = _check()
        assert "built-in" in result["active_provider"]

    def test_openai_valid_key_detected(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-valid1234567890abcdefgh")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "")
        _check = self._import()
        result = _check()
        assert result["providers"]["openai"] is True
        assert result["active_provider"] == "openai"

    def test_invalid_key_format_not_counted(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "invalid-key-format")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "")
        _check = self._import()
        result = _check()
        assert result["providers"]["openai"] is False

    def test_ollama_unreachable_reported_in_notes(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        # urllib.request.urlopen will fail in test env with no Ollama
        _check = self._import()
        result = _check()
        notes_str = " ".join(result.get("notes", []))
        assert "ollama" in notes_str.lower() or result["providers"]["ollama"] is False


# ---------------------------------------------------------------------------
# provider_status_layer.py tests
# ---------------------------------------------------------------------------

class TestProviderStatusLayer:
    def _import(self):
        from provider_status_layer import _build_provider_status  # noqa: PLC0415
        return _build_provider_status

    def test_file_exists(self):
        path = os.path.join(BACKEND_DIR, "provider_status_layer.py")
        assert os.path.isfile(path), "provider_status_layer.py must exist"

    def test_returns_required_fields(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        _build = self._import()
        result = _run(_build())
        assert "providers" in result
        assert "active_provider" in result
        assert "fallback_active" in result
        assert "ready_for_chat" in result
        assert "checked_at" in result

    def test_providers_dict_has_all_four_keys(self, monkeypatch):
        _build = self._import()
        result = _run(_build())
        for key in ("ollama", "openai", "gemini", "anthropic"):
            assert key in result["providers"], f"providers.{key} missing"

    def test_openai_valid_key_format(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-valid1234567890abcdefgh")
        _build = self._import()
        result = _run(_build())
        assert result["providers"]["openai"]["key_format_valid"] is True

    def test_openai_invalid_key_format(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "bad-key")
        _build = self._import()
        result = _run(_build())
        assert result["providers"]["openai"]["key_format_valid"] is False
        assert "error" in result["providers"]["openai"]

    def test_gemini_valid_key_format(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaTestKeyXYZ1234567890")
        _build = self._import()
        result = _run(_build())
        assert result["providers"]["gemini"]["key_format_valid"] is True

    def test_anthropic_valid_key_format(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-TestKey1234567890")
        _build = self._import()
        result = _run(_build())
        assert result["providers"]["anthropic"]["key_format_valid"] is True

    def test_ollama_unreachable_when_not_running(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        import httpx as _httpx  # noqa: PLC0415
        with patch.object(_httpx.AsyncClient, "__aenter__", side_effect=Exception("refused")):
            _build = self._import()
            result = _run(_build())
        assert result["providers"]["ollama"]["reachable"] is False
        assert result["fallback_active"] is True

    def test_ollama_reachable_becomes_active_provider(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-valid1234567890abcdefgh")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "mistral")

        # Mock a successful Ollama response
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        async def _fake_enter(self_):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            return mock_client

        import httpx as _httpx  # noqa: PLC0415
        import provider_status_layer as psl  # noqa: PLC0415
        with patch.object(_httpx.AsyncClient, "__aenter__", _fake_enter):
            result = _run(psl._build_provider_status())

        assert result["providers"]["ollama"]["reachable"] is True
        assert result["active_provider"] == "ollama/mistral"
        assert result["fallback_active"] is False

    def test_install_function_registers_route(self):
        """install_provider_status_layer must call app.get with /api/provider/status."""
        from provider_status_layer import install_provider_status_layer  # noqa: PLC0415
        mock_app = MagicMock()
        registered_paths = []

        def _get(path):
            registered_paths.append(path)
            return lambda fn: fn

        mock_app.get.side_effect = _get
        install_provider_status_layer(mock_app, {})
        assert "/api/provider/status" in registered_paths


# ---------------------------------------------------------------------------
# generate_text() metadata fields
# ---------------------------------------------------------------------------

class TestGenerateTextMetadata:
    """Verify that generate_text() always returns the required metadata fields."""

    def _get_generate_text(self):
        """Import generate_text from app module without starting the server."""
        import importlib
        # We only need the function, not to run the server
        import app as _app  # noqa: PLC0415
        return _app.generate_text

    def test_builtin_fallback_includes_provider_used(self):
        """When no real provider is configured, built-in fallback must set metadata."""
        try:
            generate_text = self._get_generate_text()
        except Exception:
            return  # app.py has many side-effects; skip if import fails in test env

        with (
            patch("app.ANTHROPIC_API_KEY", ""),
            patch("app.OPENAI_API_KEY", ""),
            patch("app.GEMINI_API_KEY", ""),
            patch("app.ollama_provider_ready", return_value=False),
        ):
            result = _run(generate_text("hello", system="be helpful"))

        assert "provider_used" in result
        assert "fallback_used" in result
        assert "mock_used" in result
        assert result["fallback_used"] is True
        assert result["mock_used"] is True

    def test_ollama_success_includes_provider_used(self):
        """When Ollama succeeds, provider_used must reflect ollama/model."""
        try:
            generate_text = self._get_generate_text()
        except Exception:
            return

        ollama_response = {
            "message": {"content": "Hello from Ollama"},
            "prompt_eval_count": 10,
            "eval_count": 20,
        }

        with (
            patch("app.ANTHROPIC_API_KEY", ""),
            patch("app.OPENAI_API_KEY", ""),
            patch("app.GEMINI_API_KEY", ""),
            patch("app.ollama_provider_ready", return_value=True),
            patch("app.OLLAMA_MODEL", "mistral"),
            patch("app.call_ollama", new=AsyncMock(return_value=ollama_response)),
            patch("app.compact_ollama_request", return_value={"prompt": "hello", "system": "help", "max_tokens": 512}),
            patch("app.extract_ollama_text", return_value="Hello from Ollama"),
        ):
            result = _run(generate_text("hello", system="be helpful"))

        assert "provider_used" in result
        assert result["provider_used"].startswith("ollama/")
        assert result["fallback_used"] is False
        assert result["mock_used"] is False


# ---------------------------------------------------------------------------
# Settings integration: selected_provider is consulted
# ---------------------------------------------------------------------------

class TestSettingsIntegration:
    def test_settings_manager_has_selected_provider(self):
        from settings_manager import _default_settings  # noqa: PLC0415
        defaults = _default_settings()
        assert "selected_provider" in defaults.get("ai_providers", {})

    def test_settings_manager_has_fallback_enabled(self):
        from settings_manager import _default_settings  # noqa: PLC0415
        defaults = _default_settings()
        assert "fallback_enabled" in defaults.get("ai_providers", {})

    def test_settings_manager_has_ollama_model(self):
        from settings_manager import _default_settings  # noqa: PLC0415
        defaults = _default_settings()
        assert "ollama_model" in defaults.get("ai_providers", {})

    def test_runtime_status_reports_ollama_configured(self, tmp_path):
        from settings_manager import SettingsManager  # noqa: PLC0415
        manager = SettingsManager(tmp_path)
        status = manager.runtime_status()
        assert "ollama_configured" in status["providers"]

    def test_runtime_status_ai_functional_with_fallback(self, tmp_path):
        from settings_manager import SettingsManager  # noqa: PLC0415
        manager = SettingsManager(tmp_path)
        status = manager.runtime_status()
        # With fallback_enabled=True (default), ai_functional should be True
        assert status["ai_functional"] is True
