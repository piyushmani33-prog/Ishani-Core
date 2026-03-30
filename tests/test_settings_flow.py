"""
Tests for the Settings Manager module.

Verifies:
- Default settings structure
- Settings load/save/reset cycle
- Provider key validation
- Runtime status reporting
- Secret redaction in public output
"""

import json
import os
import sys

BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techbuzz-full",
    "techbuzz-full",
    "backend_python",
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _import_settings():
    from settings_manager import SettingsManager, validate_provider_key  # noqa: PLC0415
    return SettingsManager, validate_provider_key


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

class TestSettingsManagerFile:
    def test_file_exists(self):
        path = os.path.join(BACKEND_DIR, "settings_manager.py")
        assert os.path.isfile(path), "settings_manager.py must exist"

    def test_file_valid_python(self):
        path = os.path.join(BACKEND_DIR, "settings_manager.py")
        with open(path, "r") as fh:
            source = fh.read()
        compile(source, path, "exec")


# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------

class TestDefaultSettings:
    REQUIRED_SECTIONS = ["server", "ai_providers", "voice", "features", "security", "ui"]

    def test_load_returns_all_sections(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        settings = mgr.load()
        for section in self.REQUIRED_SECTIONS:
            assert section in settings, f"Settings section '{section}' missing"

    def test_server_has_port(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        settings = mgr.load()
        assert "port" in settings["server"]
        assert isinstance(settings["server"]["port"], int)

    def test_ai_providers_has_fallback(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        settings = mgr.load()
        assert "fallback_enabled" in settings["ai_providers"]

    def test_features_section_present(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        settings = mgr.load()
        features = settings["features"]
        assert "recruiter_mode" in features
        assert "ats_enabled" in features


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

class TestSettingsSaveLoad:
    def test_save_creates_file(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        result = mgr.save({"ui": {"theme": "light"}})
        assert result["saved"] is True
        assert (tmp_path / "settings.json").exists()

    def test_save_persists_value(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        mgr.save({"ui": {"theme": "light"}})
        settings = mgr.load()
        assert settings["ui"]["theme"] == "light"

    def test_save_merges_with_existing(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        mgr.save({"ui": {"theme": "light"}})
        mgr.save({"ui": {"language": "hi"}})
        settings = mgr.load()
        assert settings["ui"]["theme"] == "light"
        assert settings["ui"]["language"] == "hi"

    def test_reset_section(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        mgr.save({"ui": {"theme": "light"}})
        result = mgr.reset_section("ui")
        assert result["reset"] is True
        # After reset, theme should revert to default
        settings = mgr.load()
        assert settings["ui"]["theme"] == "dark"

    def test_reset_unknown_section(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        result = mgr.reset_section("nonexistent_section_xyz")
        assert result["reset"] is False

    def test_secrets_redacted_in_load(self, tmp_path):
        """load() should never return raw API keys."""
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        # Write a key directly to the settings file
        raw = {"ai_providers": {"openai_api_key": "sk-testkey123456789012345678901234"}}
        (tmp_path / "settings.json").write_text(json.dumps(raw))
        settings = mgr.load()
        key_val = settings["ai_providers"].get("openai_api_key", "")
        assert key_val == "***", "API keys must be redacted in public load()"


# ---------------------------------------------------------------------------
# Provider key validation
# ---------------------------------------------------------------------------

class TestProviderKeyValidation:
    def test_empty_key_invalid(self):
        _, validate = _import_settings()
        result = validate("openai_api_key", "")
        assert result["valid"] is False

    def test_valid_openai_key(self):
        _, validate = _import_settings()
        result = validate("openai_api_key", "sk-" + "a" * 40)
        assert result["valid"] is True

    def test_invalid_openai_key_format(self):
        _, validate = _import_settings()
        result = validate("openai_api_key", "not-an-openai-key")
        assert result["valid"] is False

    def test_valid_anthropic_key(self):
        _, validate = _import_settings()
        result = validate("anthropic_api_key", "sk-ant-" + "a" * 30)
        assert result["valid"] is True

    def test_unknown_key_type_accepted(self):
        _, validate = _import_settings()
        result = validate("some_unknown_key", "any_value")
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# Runtime status
# ---------------------------------------------------------------------------

class TestSettingsRuntimeStatus:
    REQUIRED_STATUS_KEYS = [
        "settings_file_exists",
        "providers",
        "features",
        "ai_functional",
        "warnings",
        "errors",
        "checked_at",
    ]

    def test_runtime_status_keys(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        status = mgr.runtime_status()
        for key in self.REQUIRED_STATUS_KEYS:
            assert key in status, f"Runtime status missing key '{key}'"

    def test_ai_functional_with_fallback(self, tmp_path):
        """With no real provider but fallback enabled, ai_functional should be True."""
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        mgr.save({"ai_providers": {"fallback_enabled": True}})
        status = mgr.runtime_status()
        assert status["ai_functional"] is True

    def test_settings_file_not_exists_initially(self, tmp_path):
        SettingsManager, _ = _import_settings()
        mgr = SettingsManager(tmp_path)
        status = mgr.runtime_status()
        assert status["settings_file_exists"] is False
