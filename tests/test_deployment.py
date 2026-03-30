"""
Deployment readiness tests for Ishani-Core / TechBuzz AI.

Verifies:
- Dockerfile syntax and required directives
- docker-compose.yml has no hardcoded secrets
- .env.example has all required variables
- .env.production.example exists and is a valid template
- Deploy config files are present and readable
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY_DIR = os.path.join(ROOT, "techbuzz-full", "techbuzz-full", "deploy")
BACKEND_DIR = os.path.join(ROOT, "techbuzz-full", "techbuzz-full", "backend_python")


# ---------------------------------------------------------------------------
# Dockerfile tests
# ---------------------------------------------------------------------------

class TestDockerfile:
    """Verify the Dockerfile is present and contains required directives."""

    DOCKERFILE = os.path.join(DEPLOY_DIR, "Dockerfile")

    def test_dockerfile_exists(self):
        assert os.path.isfile(self.DOCKERFILE), "deploy/Dockerfile must exist"

    def test_dockerfile_has_from(self):
        with open(self.DOCKERFILE) as f:
            content = f.read()
        assert content.strip().startswith("FROM"), "Dockerfile must start with FROM"

    def test_dockerfile_uses_python_312(self):
        with open(self.DOCKERFILE) as f:
            content = f.read()
        assert "3.12" in content, "Dockerfile should use Python 3.12"

    def test_dockerfile_has_expose(self):
        with open(self.DOCKERFILE) as f:
            content = f.read()
        assert "EXPOSE" in content, "Dockerfile should EXPOSE a port"

    def test_dockerfile_has_healthcheck(self):
        with open(self.DOCKERFILE) as f:
            content = f.read()
        assert "HEALTHCHECK" in content, "Dockerfile should include a HEALTHCHECK"

    def test_dockerfile_has_cmd(self):
        with open(self.DOCKERFILE) as f:
            content = f.read()
        assert "CMD" in content, "Dockerfile should have a CMD instruction"

    def test_dockerfile_no_hardcoded_secrets(self):
        with open(self.DOCKERFILE) as f:
            content = f.read()
        # Check for patterns that look like committed secrets
        forbidden_patterns = [
            r"MASTER_KEY_SALT=\w{10,}",
            r"MASTER_KEY_HASH=\w{20,}",
            r"MASTER_EMAIL=\S+@\S+",
            r"piyushmani33@gmail\.com",
        ]
        for pattern in forbidden_patterns:
            assert not re.search(pattern, content), (
                f"Dockerfile appears to contain hardcoded secret matching: {pattern}"
            )


# ---------------------------------------------------------------------------
# docker-compose.yml tests
# ---------------------------------------------------------------------------

class TestDockerCompose:
    """Verify docker-compose.yml uses environment variable references only."""

    COMPOSE_FILE = os.path.join(DEPLOY_DIR, "docker-compose.yml")

    def test_compose_file_exists(self):
        assert os.path.isfile(self.COMPOSE_FILE), "deploy/docker-compose.yml must exist"

    def test_no_hardcoded_master_email(self):
        with open(self.COMPOSE_FILE) as f:
            content = f.read()
        # Must not contain a literal email address as a value (e.g. MASTER_EMAIL=foo@bar)
        assert not re.search(r"MASTER_EMAIL=\S+@\S+", content), (
            "docker-compose.yml must not contain a hardcoded MASTER_EMAIL value"
        )

    def test_no_hardcoded_salt(self):
        with open(self.COMPOSE_FILE) as f:
            content = f.read()
        # Salt patterns: long hex strings assigned directly
        assert not re.search(r"MASTER_KEY_SALT=[0-9a-f]{16,}", content), (
            "docker-compose.yml must not contain a hardcoded MASTER_KEY_SALT"
        )
        assert not re.search(r"MASTER_PASSWORD_SALT=[0-9a-f]{16,}", content), (
            "docker-compose.yml must not contain a hardcoded MASTER_PASSWORD_SALT"
        )

    def test_no_hardcoded_hash(self):
        with open(self.COMPOSE_FILE) as f:
            content = f.read()
        assert not re.search(r"MASTER_KEY_HASH=[0-9a-f]{32,}", content), (
            "docker-compose.yml must not contain a hardcoded MASTER_KEY_HASH"
        )
        assert not re.search(r"MASTER_PASSWORD_HASH=[0-9a-f]{32,}", content), (
            "docker-compose.yml must not contain a hardcoded MASTER_PASSWORD_HASH"
        )

    def test_no_wildcard_allowed_origins(self):
        with open(self.COMPOSE_FILE) as f:
            content = f.read()
        # ALLOWED_ORIGINS=* (literal asterisk, not inside a variable reference)
        assert not re.search(r"ALLOWED_ORIGINS=\*\s*$", content, re.MULTILINE), (
            "docker-compose.yml must not set ALLOWED_ORIGINS=* (use a variable reference)"
        )

    def test_secrets_use_variable_references(self):
        with open(self.COMPOSE_FILE) as f:
            content = f.read()
        # The critical secret vars should use ${...} references
        for var in ["MASTER_ACCOUNT_EMAIL", "MASTER_PASSWORD_SALT", "MASTER_PASSWORD_HASH", "SESSION_SECRET"]:
            assert f"${{{var}}}" in content or f"${var}" in content, (
                f"docker-compose.yml should reference {var} as a variable (${{{var}}})"
            )

    def test_has_healthcheck(self):
        with open(self.COMPOSE_FILE) as f:
            content = f.read()
        assert "healthcheck" in content.lower(), (
            "docker-compose.yml should include a healthcheck"
        )


# ---------------------------------------------------------------------------
# .env.example tests
# ---------------------------------------------------------------------------

class TestEnvExample:
    """Verify .env.example has all required variables and no local paths."""

    ENV_EXAMPLE = os.path.join(BACKEND_DIR, ".env.example")

    REQUIRED_VARS = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "MASTER_ACCOUNT_EMAIL",
        "MASTER_PASSWORD_SALT",
        "MASTER_PASSWORD_HASH",
        "SESSION_SECRET",
        "ALLOWED_ORIGINS",
        "PORT",
        "LOG_LEVEL",
        "RATE_LIMIT_PER_MINUTE",
        "DATABASE_URL",
        "DEMO_MODE",
        "ADMIN_ROUTES_ENABLED",
    ]

    def test_env_example_exists(self):
        assert os.path.isfile(self.ENV_EXAMPLE), ".env.example must exist"

    def test_has_required_variables(self):
        with open(self.ENV_EXAMPLE) as f:
            content = f.read()
        for var in self.REQUIRED_VARS:
            assert var in content, f".env.example must document {var}"

    def test_no_windows_local_paths(self):
        with open(self.ENV_EXAMPLE) as f:
            content = f.read()
        # Should not contain Windows-style local paths like C:\Users\...
        assert not re.search(r"[A-Z]:\\\\Users\\\\", content), (
            ".env.example must not contain Windows local paths (e.g. C:\\Users\\...)"
        )
        assert "C:\\Users" not in content and r"C:\Users" not in content, (
            ".env.example must not contain Windows local paths"
        )

    def test_no_naukri_launcher_path(self):
        with open(self.ENV_EXAMPLE) as f:
            content = f.read()
        assert "NAUKRI_LAUNCHER_PATH" not in content, (
            "NAUKRI_LAUNCHER_PATH (local Windows path) must be removed from .env.example"
        )

    def test_no_real_secrets_committed(self):
        with open(self.ENV_EXAMPLE) as f:
            content = f.read()
        # Values for secret vars should be empty or placeholder-only
        lines = {
            line.split("=")[0].strip(): line.split("=", 1)[1].strip()
            for line in content.splitlines()
            if "=" in line and not line.strip().startswith("#")
        }
        for secret_var in ["MASTER_PASSWORD_SALT", "MASTER_PASSWORD_HASH", "SESSION_SECRET"]:
            value = lines.get(secret_var, "")
            assert not re.fullmatch(r"[0-9a-f]{32,}", value), (
                f".env.example must not contain a real {secret_var} value"
            )


# ---------------------------------------------------------------------------
# .env.production.example tests
# ---------------------------------------------------------------------------

class TestEnvProductionExample:
    """Verify .env.production.example exists and is a valid production template."""

    ENV_PROD_EXAMPLE = os.path.join(DEPLOY_DIR, ".env.production.example")

    REQUIRED_VARS = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "MASTER_ACCOUNT_EMAIL",
        "MASTER_PASSWORD_SALT",
        "MASTER_PASSWORD_HASH",
        "SESSION_SECRET",
        "ALLOWED_ORIGINS",
        "DEMO_MODE",
        "ADMIN_ROUTES_ENABLED",
        "LOG_LEVEL",
        "RATE_LIMIT_PER_MINUTE",
        "PORT",
    ]

    def test_file_exists(self):
        assert os.path.isfile(self.ENV_PROD_EXAMPLE), (
            "deploy/.env.production.example must exist"
        )

    def test_has_required_variables(self):
        with open(self.ENV_PROD_EXAMPLE) as f:
            content = f.read()
        for var in self.REQUIRED_VARS:
            assert var in content, f".env.production.example must document {var}"

    def test_no_real_secrets(self):
        with open(self.ENV_PROD_EXAMPLE) as f:
            content = f.read()
        lines = {
            line.split("=")[0].strip(): line.split("=", 1)[1].strip()
            for line in content.splitlines()
            if "=" in line and not line.strip().startswith("#")
        }
        for secret_var in ["MASTER_PASSWORD_SALT", "MASTER_PASSWORD_HASH", "SESSION_SECRET"]:
            value = lines.get(secret_var, "")
            assert not re.fullmatch(r"[0-9a-f]{32,}", value), (
                f".env.production.example must not contain a real {secret_var}"
            )


# ---------------------------------------------------------------------------
# Deploy config files existence tests
# ---------------------------------------------------------------------------

class TestDeployConfigs:
    """Verify all documented deploy configuration files exist."""

    EXPECTED_FILES = [
        "Dockerfile",
        "docker-compose.yml",
        "DEPLOY.md",
        ".env.production.example",
    ]

    def test_deploy_dir_exists(self):
        assert os.path.isdir(DEPLOY_DIR), "deploy/ directory must exist"

    def test_all_deploy_files_exist(self):
        for fname in self.EXPECTED_FILES:
            path = os.path.join(DEPLOY_DIR, fname)
            assert os.path.isfile(path), f"deploy/{fname} must exist"

    def test_deploy_md_has_health_check_section(self):
        deploy_md = os.path.join(DEPLOY_DIR, "DEPLOY.md")
        with open(deploy_md) as f:
            content = f.read()
        assert "health" in content.lower(), "DEPLOY.md must document health check verification"

    def test_deploy_md_no_hardcoded_credentials(self):
        deploy_md = os.path.join(DEPLOY_DIR, "DEPLOY.md")
        with open(deploy_md) as f:
            content = f.read()
        forbidden = [
            "MASTER_KEY_SALT=7da6609f",
            "MASTER_KEY_HASH=13939481",
            "piyushmani33@gmail.com",
            "ICBAQ00538",
        ]
        for secret in forbidden:
            assert secret not in content, (
                f"DEPLOY.md must not contain hardcoded credentials: {secret!r}"
            )
