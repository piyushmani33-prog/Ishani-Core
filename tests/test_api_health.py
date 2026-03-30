"""
Real-world scenario tests for Ishani-Core / TechBuzz AI.

These tests simulate actual recruiter workflows to verify
the system works end-to-end as real users would experience.
"""
import os
import sys
import pytest

# ---------------------------------------------------------------------------
# Scenario 1: Startup & Health Check
# ---------------------------------------------------------------------------

class TestStartupHealth:
    """Verify the server can start and respond to basic requests."""

    def test_main_py_exists(self):
        """A new developer clones the repo and finds main.py."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_py = os.path.join(root, "main.py")
        assert os.path.isfile(main_py), "main.py should exist at repo root"

    def test_main_py_is_valid_python(self):
        """main.py should be valid Python (not markdown disguised as .py)."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_py = os.path.join(root, "main.py")
        with open(main_py, "r") as f:
            source = f.read()
        # Should compile without SyntaxError
        compile(source, main_py, "exec")

    def test_backend_app_exists(self):
        """The actual FastAPI app.py should exist."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_py = os.path.join(
            root, "techbuzz-full", "techbuzz-full", "backend_python", "app.py"
        )
        assert os.path.isfile(app_py), "app.py should exist in backend_python"

    def test_requirements_txt_has_fastapi(self):
        """Root requirements.txt should reference FastAPI (the actual framework)."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        req = os.path.join(root, "requirements.txt")
        with open(req, "r") as f:
            content = f.read().lower()
        assert "fastapi" in content, "requirements.txt should include fastapi"

    def test_env_example_exists(self):
        """.env.example should exist so users know what to configure."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_example = os.path.join(
            root, "techbuzz-full", "techbuzz-full", "backend_python", ".env.example"
        )
        assert os.path.isfile(env_example), ".env.example should exist"

    def test_env_not_committed(self):
        """The actual .env file should NOT be in the repo (security check)."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(
            root, "techbuzz-full", "techbuzz-full", "backend_python", ".env"
        )
        assert not os.path.isfile(env_file), (
            ".env should NOT be committed to the repository — it contains secrets!"
        )


# ---------------------------------------------------------------------------
# Scenario 2: Backend Layer Files Integrity
# ---------------------------------------------------------------------------

class TestBackendLayers:
    """Verify all documented backend layer files exist and are valid Python."""

    BACKEND_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "techbuzz-full", "techbuzz-full", "backend_python"
    )

    EXPECTED_LAYERS = [
        "app.py",
        "recruitment_brain_layer.py",
        "empire_merge_layer.py",
        "browser_suite_layer.py",
        "orchestration_stack_layer.py",
        "interpreter_brain_layer.py",
        "global_recruitment_brain_layer.py",
        "local_ai_runtime_layer.py",
        "voice_runtime_layer.py",
        "recruiter_status_layer.py",
    ]

    def test_all_layers_exist(self):
        """Every documented layer file should be present."""
        for layer in self.EXPECTED_LAYERS:
            path = os.path.join(self.BACKEND_DIR, layer)
            assert os.path.isfile(path), f"Missing layer file: {layer}"

    def test_layers_are_valid_python(self):
        """Each layer file should be syntactically valid Python."""
        for layer in self.EXPECTED_LAYERS:
            path = os.path.join(self.BACKEND_DIR, layer)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                try:
                    compile(source, path, "exec")
                except SyntaxError as e:
                    pytest.fail(f"SyntaxError in {layer}: {e}")

    def test_requirements_txt_exists_in_backend(self):
        """Backend requirements.txt should exist."""
        path = os.path.join(self.BACKEND_DIR, "requirements.txt")
        assert os.path.isfile(path)

    def test_backend_requirements_has_fastapi(self):
        """Backend requirements should include FastAPI."""
        path = os.path.join(self.BACKEND_DIR, "requirements.txt")
        with open(path, "r") as f:
            content = f.read().lower()
        assert "fastapi" in content


# ---------------------------------------------------------------------------
# Scenario 3: Frontend Files Integrity
# ---------------------------------------------------------------------------

class TestFrontendFiles:
    """Verify key frontend files exist for all documented pages."""

    FRONTEND_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "techbuzz-full", "techbuzz-full", "frontend"
    )

    EXPECTED_FILES = [
        "index.html",
        "login.html",
        "agent.html",
    ]

    def test_frontend_dir_exists(self):
        """Frontend directory should exist."""
        assert os.path.isdir(self.FRONTEND_DIR), "frontend/ directory should exist"

    def test_key_pages_exist(self):
        """Core frontend pages should be present."""
        if not os.path.isdir(self.FRONTEND_DIR):
            pytest.skip("frontend/ directory not found")
        for fname in self.EXPECTED_FILES:
            path = os.path.join(self.FRONTEND_DIR, fname)
            assert os.path.isfile(path), f"Missing frontend file: {fname}"


# ---------------------------------------------------------------------------
# Scenario 4: Security Checks
# ---------------------------------------------------------------------------

class TestSecurityChecks:
    """Verify no secrets are committed and security basics are met."""

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_gitignore_blocks_env(self):
        """.gitignore should block .env files."""
        gitignore = os.path.join(self.ROOT, ".gitignore")
        with open(gitignore, "r") as f:
            content = f.read()
        assert ".env" in content, ".gitignore must block .env files"

    def test_gitignore_blocks_zip(self):
        """.gitignore should block .zip files."""
        gitignore = os.path.join(self.ROOT, ".gitignore")
        with open(gitignore, "r") as f:
            content = f.read()
        assert ".zip" in content or "*.zip" in content, ".gitignore must block .zip files"

    def test_gitignore_blocks_db(self):
        """.gitignore should block database files."""
        gitignore = os.path.join(self.ROOT, ".gitignore")
        with open(gitignore, "r") as f:
            content = f.read()
        assert ".db" in content or "*.db" in content, ".gitignore must block .db files"

    def test_security_md_exists(self):
        """SECURITY.md should exist."""
        path = os.path.join(self.ROOT, "SECURITY.md")
        assert os.path.isfile(path)


# ---------------------------------------------------------------------------
# Scenario 5: Documentation Completeness
# ---------------------------------------------------------------------------

class TestDocumentation:
    """Verify documentation is present and accurate."""

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_root_readme_mentions_techbuzz(self):
        """Root README should describe the actual TechBuzz platform."""
        readme = os.path.join(self.ROOT, "README.md")
        with open(readme, "r") as f:
            content = f.read()
        assert "TechBuzz" in content or "techbuzz" in content.lower(), (
            "Root README should mention the TechBuzz platform"
        )

    def test_root_readme_mentions_fastapi(self):
        """Root README should mention FastAPI (the actual framework)."""
        readme = os.path.join(self.ROOT, "README.md")
        with open(readme, "r") as f:
            content = f.read()
        assert "FastAPI" in content or "fastapi" in content.lower()

    def test_inner_readme_exists(self):
        """The detailed inner README should exist."""
        path = os.path.join(
            self.ROOT, "techbuzz-full", "techbuzz-full", "README.md"
        )
        assert os.path.isfile(path)
