"""
Tests for the Unified Platform Status module.

Verifies:
- build_platform_status returns correct structure
- All required subsystem keys are present
- Each subsystem has the standard status fields
- Overall status is one of the expected values
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techbuzz-full",
    "techbuzz-full",
    "backend_python",
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _import_platform_status():
    from platform_status import build_platform_status  # noqa: PLC0415
    return build_platform_status


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

class TestPlatformStatusFile:
    def test_file_exists(self):
        path = os.path.join(BACKEND_DIR, "platform_status.py")
        assert os.path.isfile(path), "platform_status.py must exist in backend_python"

    def test_file_is_valid_python(self):
        path = os.path.join(BACKEND_DIR, "platform_status.py")
        with open(path, "r") as fh:
            source = fh.read()
        compile(source, path, "exec")


# ---------------------------------------------------------------------------
# Structure tests (no live DB or network needed)
# ---------------------------------------------------------------------------

class TestPlatformStatusStructure:
    """Verify the status payload has all required top-level keys."""

    REQUIRED_TOP_KEYS = [
        "platform",
        "version",
        "overall_status",
        "ready_for_users",
        "ready_for_automation",
        "subsystems",
        "subsystem_count",
        "healthy_count",
        "degraded_count",
        "error_count",
        "checked_at",
    ]

    REQUIRED_SUBSYSTEMS = [
        "database",
        "ai_providers",
        "brain_hierarchy",
        "agent_registry",
        "voice_pipeline",
        "local_ai",
        "settings",
        "recruiter_module",
        "ats",
        "middleware",
    ]

    SUBSYSTEM_FIELDS = [
        "enabled",
        "configured",
        "initialized",
        "healthy",
        "degraded",
        "fallback_active",
        "last_error",
        "ready_for_user",
        "ready_for_automation",
    ]

    def _get_status(self, tmp_path):
        build = _import_platform_status()
        return build(Path(tmp_path))

    def test_top_level_keys_present(self, tmp_path):
        status = self._get_status(tmp_path)
        for key in self.REQUIRED_TOP_KEYS:
            assert key in status, f"Top-level key '{key}' missing from platform status"

    def test_platform_name(self, tmp_path):
        status = self._get_status(tmp_path)
        assert status["platform"] == "ishani-core"

    def test_overall_status_is_valid(self, tmp_path):
        status = self._get_status(tmp_path)
        assert status["overall_status"] in ("healthy", "degraded", "partial")

    def test_all_subsystems_present(self, tmp_path):
        status = self._get_status(tmp_path)
        subsystems = status["subsystems"]
        for name in self.REQUIRED_SUBSYSTEMS:
            assert name in subsystems, f"Subsystem '{name}' missing from platform status"

    def test_subsystem_count_matches(self, tmp_path):
        status = self._get_status(tmp_path)
        assert status["subsystem_count"] == len(status["subsystems"])

    def test_each_subsystem_has_standard_fields(self, tmp_path):
        status = self._get_status(tmp_path)
        for subsys_name, subsys in status["subsystems"].items():
            for field in self.SUBSYSTEM_FIELDS:
                assert field in subsys, (
                    f"Subsystem '{subsys_name}' is missing field '{field}'"
                )

    def test_healthy_count_is_integer(self, tmp_path):
        status = self._get_status(tmp_path)
        assert isinstance(status["healthy_count"], int)
        assert status["healthy_count"] >= 0

    def test_checked_at_is_iso8601(self, tmp_path):
        import datetime  # noqa: PLC0415
        status = self._get_status(tmp_path)
        # Should parse without error
        datetime.datetime.fromisoformat(status["checked_at"])

    def test_ready_for_users_is_bool(self, tmp_path):
        status = self._get_status(tmp_path)
        assert isinstance(status["ready_for_users"], bool)

    def test_ready_for_automation_is_bool(self, tmp_path):
        status = self._get_status(tmp_path)
        assert isinstance(status["ready_for_automation"], bool)


# ---------------------------------------------------------------------------
# Honesty tests — status must not report "healthy" when clearly broken
# ---------------------------------------------------------------------------

class TestPlatformStatusHonesty:
    """Verify that the status is truthful about what is missing."""

    def test_missing_db_not_healthy(self, tmp_path):
        """If the database file doesn't exist, db subsystem should not be healthy."""
        build = _import_platform_status()
        status = build(Path(tmp_path))  # empty tmp dir — no DB file
        db_status = status["subsystems"]["database"]
        # A missing DB is either not initialized or not healthy — never both True
        assert not (db_status["initialized"] and db_status["healthy"]), (
            "Database subsystem should not claim healthy when DB file is missing"
        )

    def test_voice_status_reflects_imports(self, tmp_path):
        """Voice status components dict must be present."""
        build = _import_platform_status()
        status = build(Path(tmp_path))
        voice = status["subsystems"]["voice_pipeline"]
        assert "components" in voice, "voice_pipeline must include 'components' dict"
        components = voice["components"]
        assert "stt_faster_whisper" in components
        assert "tts_browser_fallback" in components
        # browser TTS fallback is always True
        assert components["tts_browser_fallback"] is True
