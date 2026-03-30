"""
Smoke tests — startup, core routes, and key module availability.

These tests verify the critical path without a running server:
- main.py is importable / valid
- Key backend layer files exist and are valid Python
- Core configuration loads without errors
- All new unified modules are importable
- Requirements files are consistent
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "techbuzz-full", "techbuzz-full", "backend_python")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# Core file presence
# ---------------------------------------------------------------------------

class TestCoreFilesExist:
    """All critical backend files must exist."""

    CRITICAL_FILES = [
        "app.py",
        "config.py",
        "health_check.py",
        "middleware.py",
        "voice_runtime_layer.py",
        "platform_status.py",
        "unified_brain_registry.py",
        "unified_agent_registry.py",
        "settings_manager.py",
    ]

    def test_critical_files_present(self):
        for filename in self.CRITICAL_FILES:
            path = os.path.join(BACKEND_DIR, filename)
            assert os.path.isfile(path), f"Critical file missing: {filename}"

    def test_main_py_at_root(self):
        assert os.path.isfile(os.path.join(ROOT, "main.py"))


# ---------------------------------------------------------------------------
# Python syntax validity
# ---------------------------------------------------------------------------

class TestPythonSyntaxValidity:
    """All new unified modules must compile without syntax errors."""

    NEW_MODULES = [
        "platform_status.py",
        "unified_brain_registry.py",
        "unified_agent_registry.py",
        "settings_manager.py",
    ]

    def test_new_modules_valid_python(self):
        for filename in self.NEW_MODULES:
            path = os.path.join(BACKEND_DIR, filename)
            with open(path, "r") as fh:
                source = fh.read()
            try:
                compile(source, path, "exec")
            except SyntaxError as exc:
                assert False, f"Syntax error in {filename}: {exc}"

    def test_main_py_valid_python(self):
        path = os.path.join(ROOT, "main.py")
        with open(path, "r") as fh:
            source = fh.read()
        compile(source, path, "exec")


# ---------------------------------------------------------------------------
# Config smoke
# ---------------------------------------------------------------------------

class TestConfigSmoke:
    """AppConfig must load and validate without exceptions."""

    def test_config_loads(self):
        from config import AppConfig  # noqa: PLC0415
        cfg = AppConfig.from_env()
        assert cfg is not None

    def test_config_has_port(self):
        from config import AppConfig  # noqa: PLC0415
        cfg = AppConfig.from_env()
        assert cfg.port > 0

    def test_config_validate_returns_list(self):
        from config import AppConfig  # noqa: PLC0415
        cfg = AppConfig.from_env()
        warnings = cfg.validate()
        assert isinstance(warnings, list)


# ---------------------------------------------------------------------------
# Unified module imports
# ---------------------------------------------------------------------------

class TestUnifiedModuleImports:
    """Unified registry modules must import cleanly."""

    def test_unified_brain_registry_imports(self):
        import unified_brain_registry  # noqa: PLC0415, F401
        assert hasattr(unified_brain_registry, "get_all_brains")
        assert hasattr(unified_brain_registry, "get_hierarchy")

    def test_unified_agent_registry_imports(self):
        import unified_agent_registry  # noqa: PLC0415, F401
        assert hasattr(unified_agent_registry, "get_all_agents")
        assert hasattr(unified_agent_registry, "get_agent")

    def test_settings_manager_imports(self):
        from settings_manager import SettingsManager  # noqa: PLC0415
        assert SettingsManager is not None

    def test_platform_status_imports(self):
        from platform_status import build_platform_status  # noqa: PLC0415
        assert callable(build_platform_status)


# ---------------------------------------------------------------------------
# Requirements files
# ---------------------------------------------------------------------------

class TestRequirementsFiles:
    """Requirements files must be present and well-formed."""

    def test_root_requirements_exists(self):
        path = os.path.join(ROOT, "requirements.txt")
        assert os.path.isfile(path)

    def test_root_requirements_has_fastapi(self):
        path = os.path.join(ROOT, "requirements.txt")
        with open(path) as fh:
            content = fh.read().lower()
        assert "fastapi" in content

    def test_root_requirements_has_pytest(self):
        path = os.path.join(ROOT, "requirements.txt")
        with open(path) as fh:
            content = fh.read().lower()
        assert "pytest" in content

    def test_backend_requirements_exists(self):
        path = os.path.join(BACKEND_DIR, "requirements.txt")
        assert os.path.isfile(path)

    def test_requirements_dev_exists(self):
        path = os.path.join(ROOT, "requirements-dev.txt")
        assert os.path.isfile(path), (
            "requirements-dev.txt must exist at repo root for developer tooling"
        )


# ---------------------------------------------------------------------------
# Dead artifact cleanup
# ---------------------------------------------------------------------------

class TestDeadArtifactsRemoved:
    """Verify dead directories are no longer committed (tracked by git)."""

    def test_zip_inspect_not_tracked(self):
        """_zip_inspect_browser_complete must not be a committed directory."""
        # Check git tracking via the .git index
        import subprocess  # noqa: PLC0415
        result = subprocess.run(
            ["git", "ls-files", "_zip_inspect_browser_complete/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", (
            "_zip_inspect_browser_complete/ must not be tracked by git"
        )

    def test_tmp_browser_not_tracked(self):
        import subprocess  # noqa: PLC0415
        result = subprocess.run(
            ["git", "ls-files", "tmp_browser_complete_1/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", (
            "tmp_browser_complete_1/ must not be tracked by git"
        )

    def test_zip_not_tracked(self):
        import subprocess  # noqa: PLC0415
        result = subprocess.run(
            ["git", "ls-files", "techbuzz-full-final.zip"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", (
            "techbuzz-full-final.zip must not be tracked by git"
        )
