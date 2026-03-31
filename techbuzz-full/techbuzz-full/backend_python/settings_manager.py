"""
Settings Manager — unified settings persistence and runtime binding.

Provides:
- GET  /api/settings           — current settings (runtime + saved)
- POST /api/settings           — save settings patch, validate provider keys
- GET  /api/settings/status    — actual runtime state vs saved state
- POST /api/settings/reset     — reset a section to defaults

Settings are loaded in priority order:
  1. .env file (base)
  2. data/settings.json (runtime overrides, persisted across restarts)
  3. In-memory session overrides (not persisted)
"""

from __future__ import annotations

import datetime
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    from fastapi import HTTPException, Request
except ImportError:  # allow import without fastapi installed (e.g. unit tests)
    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int = 500, detail: str = ""):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

    class Request:  # type: ignore[no-redef]  # noqa: E303
        pass

# ---------------------------------------------------------------------------
# Default settings schema
# ---------------------------------------------------------------------------

def _default_settings() -> Dict[str, Any]:
    return {
        "server": {
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", "8000")),
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "demo_mode": os.getenv("DEMO_MODE", "false").lower() == "true",
        },
        "ai_providers": {
            "selected_provider": os.getenv("AI_PROVIDER", "fallback"),
            "openai_api_key": "",
            "gemini_api_key": "",
            "anthropic_api_key": "",
            "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "mistral"),
            "fallback_enabled": True,
            "fallback_provider": "mock_llm",
        },
        "voice": {
            "enabled": True,
            "stt_engine": "faster_whisper",
            "whisper_model": os.getenv("TECHBUZZ_WHISPER_MODEL", "base"),
            "vad_engine": "silero_vad",
            "use_vad": True,
            "tts_engine": "pyttsx3_local",
            "language": "en-IN",
        },
        "features": {
            "recruiter_mode": True,
            "ats_enabled": True,
            "brain_hierarchy_enabled": True,
            "autonomous_loop_enabled": False,
            "local_ai_enabled": False,
            "browser_automation_enabled": False,
            "carbon_protocol_enabled": True,
            "world_brain_enabled": True,
        },
        "security": {
            "rate_limit_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            "allowed_origins": os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost,http://127.0.0.1",
            ).split(","),
        },
        "ui": {
            "theme": "dark",
            "language": "en",
            "timezone": "Asia/Kolkata",
        },
    }


# ---------------------------------------------------------------------------
# Provider key validation
# ---------------------------------------------------------------------------

_KEY_PATTERNS: Dict[str, re.Pattern] = {
    "openai_api_key": re.compile(r"^sk-[A-Za-z0-9\-_]{20,}$"),
    "gemini_api_key": re.compile(r"^[A-Za-z0-9\-_]{20,}$"),
    "anthropic_api_key": re.compile(r"^sk-ant-[A-Za-z0-9\-_]{20,}$"),
}


def validate_provider_key(key_name: str, value: str) -> Dict[str, Any]:
    """
    Validate a provider API key format.

    Returns {"valid": bool, "message": str}.
    Does NOT make network calls — format validation only.
    """
    if not value or not value.strip():
        return {"valid": False, "message": "Key is empty."}
    pattern = _KEY_PATTERNS.get(key_name)
    if pattern is None:
        return {"valid": True, "message": "No format rule for this key — accepted as-is."}
    if pattern.match(value.strip()):
        return {"valid": True, "message": "Key format looks valid."}
    return {"valid": False, "message": f"Key format does not match expected pattern for {key_name}."}


def _validate_provider_section(ai_providers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return a list of validation errors/warnings for the ai_providers block."""
    issues: List[Dict[str, Any]] = []
    for key in ("openai_api_key", "gemini_api_key", "anthropic_api_key"):
        value = ai_providers.get(key, "")
        if value:
            result = validate_provider_key(key, value)
            if not result["valid"]:
                issues.append({"field": key, "severity": "error", "message": result["message"]})
    selected = ai_providers.get("selected_provider", "fallback")
    key_map = {
        "openai": "openai_api_key",
        "gemini": "gemini_api_key",
        "anthropic": "anthropic_api_key",
    }
    if selected in key_map:
        key_field = key_map[selected]
        if not ai_providers.get(key_field, "").strip():
            issues.append(
                {
                    "field": key_field,
                    "severity": "warning",
                    "message": (
                        f"Selected provider is '{selected}' but {key_field} is empty. "
                        "Fallback LLM will be used."
                    ),
                }
            )
    return issues


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

class SettingsManager:
    """
    Manages loading, merging, and persisting settings.

    Keeps settings.json in DATA_DIR for runtime overrides.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._settings_file = data_dir / "settings.json"
        self._runtime_overrides: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self) -> Dict[str, Any]:
        """Return merged settings: defaults + persisted file + runtime overrides."""
        base = _default_settings()
        file_data = self._load_file()
        merged = _deep_merge(base, file_data)
        merged = _deep_merge(merged, self._runtime_overrides)
        # Strip secrets from returned payload
        return _strip_secrets(merged)

    def load_raw(self) -> Dict[str, Any]:
        """Return merged settings including actual key values (master use only)."""
        base = _default_settings()
        file_data = self._load_file()
        return _deep_merge(base, file_data)

    def _load_file(self) -> Dict[str, Any]:
        if not self._settings_file.exists():
            return {}
        try:
            with open(self._settings_file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a patch dict to the persisted settings file.
        Returns {"saved": ..., "warnings": [...], "errors": [...]}.
        """
        current = self._load_file()
        updated = _deep_merge(current, patch)

        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        if "ai_providers" in patch:
            issues = _validate_provider_section(updated.get("ai_providers", {}))
            for issue in issues:
                (errors if issue["severity"] == "error" else warnings).append(issue)

        if errors:
            return {
                "saved": False,
                "errors": errors,
                "warnings": warnings,
                "message": "Settings NOT saved — validation errors found.",
            }

        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._settings_file, "w", encoding="utf-8") as fh:
            json.dump(updated, fh, indent=2)

        return {
            "saved": True,
            "errors": [],
            "warnings": warnings,
            "message": "Settings saved.",
            "settings": _strip_secrets(updated),
        }

    def reset_section(self, section: str) -> Dict[str, Any]:
        """Reset a settings section to its default values."""
        defaults = _default_settings()
        if section not in defaults:
            return {"reset": False, "message": f"Unknown settings section: {section}"}
        current = self._load_file()
        current.pop(section, None)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._settings_file, "w", encoding="utf-8") as fh:
            json.dump(current, fh, indent=2)
        return {"reset": True, "section": section, "message": f"Section '{section}' reset to defaults."}

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def runtime_status(self) -> Dict[str, Any]:
        """
        Report actual runtime state vs saved state.

        Checks provider keys for truthfulness, feature flag coherence, etc.
        """
        raw = self.load_raw()
        ai = raw.get("ai_providers", {})
        provider_issues = _validate_provider_section(ai)

        providers_status = {
            "selected": ai.get("selected_provider", "fallback"),
            "openai_configured": bool(ai.get("openai_api_key", "").strip()),
            "gemini_configured": bool(ai.get("gemini_api_key", "").strip()),
            "anthropic_configured": bool(ai.get("anthropic_api_key", "").strip()),
            "ollama_configured": bool(ai.get("ollama_host", "").strip()),
            "fallback_enabled": bool(ai.get("fallback_enabled", True)),
            "issues": provider_issues,
        }

        features = raw.get("features", {})
        feature_status = {k: bool(v) for k, v in features.items()}

        any_real_provider = any(
            [
                ai.get("openai_api_key", "").strip(),
                ai.get("gemini_api_key", "").strip(),
                ai.get("anthropic_api_key", "").strip(),
            ]
        )

        return {
            "settings_file_exists": self._settings_file.exists(),
            "providers": providers_status,
            "features": feature_status,
            "ai_functional": any_real_provider or ai.get("fallback_enabled", True),
            "warnings": [i["message"] for i in provider_issues if i["severity"] == "warning"],
            "errors": [i["message"] for i in provider_issues if i["severity"] == "error"],
            "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override into base (non-destructive to base)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


_SECRET_FIELDS = frozenset(
    ["openai_api_key", "gemini_api_key", "anthropic_api_key", "session_secret"]
)


def _strip_secrets(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of settings with secret values redacted."""
    result: Dict[str, Any] = {}
    for k, v in settings.items():
        if isinstance(v, dict):
            result[k] = _strip_secrets(v)
        elif k in _SECRET_FIELDS and isinstance(v, str) and v:
            result[k] = "***"
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# FastAPI route installer
# ---------------------------------------------------------------------------

def install_settings_manager(app: Any, ctx: Dict[str, Any]) -> None:
    """Register /api/settings endpoints."""
    data_dir = Path(ctx.get("DATA_DIR", "data"))
    manager = SettingsManager(data_dir)
    session_user = ctx["session_user"]

    @app.get("/api/settings")
    async def get_settings(request: Request):
        """Return current settings (secrets redacted)."""
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        return {
            "settings": manager.load(),
            "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    @app.post("/api/settings")
    async def save_settings(request: Request):
        """Save a settings patch. Master only."""
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        if viewer.get("role") != "master":
            raise HTTPException(status_code=403, detail="Only the platform owner can update settings.")
        patch = await request.json()
        if not isinstance(patch, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object.")
        return manager.save(patch)

    @app.get("/api/settings/status")
    async def settings_runtime_status(request: Request):
        """Report actual runtime state vs saved state."""
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        return manager.runtime_status()

    @app.post("/api/settings/reset/{section}")
    async def reset_settings_section(section: str, request: Request):
        """Reset a settings section to its defaults. Master only."""
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required.")
        if viewer.get("role") != "master":
            raise HTTPException(status_code=403, detail="Only the platform owner can reset settings.")
        return manager.reset_section(section)
