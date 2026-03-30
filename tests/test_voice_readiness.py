"""
Tests for voice pipeline readiness reporting.

Verifies that voice_runtime_layer.py honestly reports:
- Which components are available
- ready_for_user / ready_for_automation flags
- browser TTS fallback is always active as last resort
- The status payload contains all expected fields
"""

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


# ---------------------------------------------------------------------------
# File existence / syntax
# ---------------------------------------------------------------------------

class TestVoiceRuntimeFile:
    def test_file_exists(self):
        path = os.path.join(BACKEND_DIR, "voice_runtime_layer.py")
        assert os.path.isfile(path), "voice_runtime_layer.py must exist"

    def test_file_valid_python(self):
        path = os.path.join(BACKEND_DIR, "voice_runtime_layer.py")
        with open(path, "r") as fh:
            source = fh.read()
        compile(source, path, "exec")


# ---------------------------------------------------------------------------
# Honesty field tests (parse source, not import)
# ---------------------------------------------------------------------------

class TestVoiceReadinessFields:
    """
    Parse voice_runtime_layer.py source to confirm required fields appear
    in the status_payload return dict.  We cannot safely import the file
    because it imports FastAPI and heavy optional deps at module scope.
    """

    def _get_source(self):
        path = os.path.join(BACKEND_DIR, "voice_runtime_layer.py")
        with open(path, "r") as fh:
            return fh.read()

    def test_ready_for_user_in_source(self):
        source = self._get_source()
        assert "ready_for_user" in source, (
            "voice_runtime_layer.py must report 'ready_for_user' in status payload"
        )

    def test_ready_for_automation_in_source(self):
        source = self._get_source()
        assert "ready_for_automation" in source, (
            "voice_runtime_layer.py must report 'ready_for_automation' in status payload"
        )

    def test_degraded_in_source(self):
        source = self._get_source()
        assert "degraded" in source, (
            "voice_runtime_layer.py must report 'degraded' flag in status payload"
        )

    def test_browser_tts_fallback_in_source(self):
        source = self._get_source()
        assert "browser_tts_fallback_active" in source, (
            "voice_runtime_layer.py must report browser TTS fallback status"
        )

    def test_stt_available_in_source(self):
        source = self._get_source()
        assert "stt_available" in source

    def test_tts_available_in_source(self):
        source = self._get_source()
        assert "tts_available" in source

    def test_whisper_availability_check_in_source(self):
        """WhisperModel import must be wrapped in try/except (graceful absence)."""
        source = self._get_source()
        assert "WhisperModel = None" in source or "WhisperModel is None" in source, (
            "voice_runtime_layer.py must handle missing faster-whisper gracefully"
        )

    def test_pyttsx3_availability_check_in_source(self):
        source = self._get_source()
        assert "pyttsx3 = None" in source or "pyttsx3_available" in source


# ---------------------------------------------------------------------------
# platform_status voice sub-check
# ---------------------------------------------------------------------------

class TestPlatformStatusVoiceCheck:
    """Ensure platform_status._check_voice_pipeline returns expected structure."""

    def test_check_voice_pipeline_structure(self):
        from platform_status import _check_voice_pipeline  # noqa: PLC0415
        result = _check_voice_pipeline()
        required = [
            "enabled",
            "configured",
            "initialized",
            "healthy",
            "degraded",
            "fallback_active",
            "last_error",
            "ready_for_user",
            "ready_for_automation",
            "components",
            "notes",
        ]
        for field in required:
            assert field in result, f"voice check missing field '{field}'"

    def test_browser_tts_fallback_always_true(self):
        from platform_status import _check_voice_pipeline  # noqa: PLC0415
        result = _check_voice_pipeline()
        assert result["components"]["tts_browser_fallback"] is True

    def test_voice_not_ready_for_automation_without_whisper(self):
        """Without faster-whisper, voice cannot be ready_for_automation."""
        import importlib.util  # noqa: PLC0415
        from platform_status import _check_voice_pipeline  # noqa: PLC0415

        whisper_available = importlib.util.find_spec("faster_whisper") is not None
        result = _check_voice_pipeline()
        if not whisper_available:
            assert result["ready_for_automation"] is False, (
                "Without faster-whisper, ready_for_automation must be False"
            )
