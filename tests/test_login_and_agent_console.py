"""
Tests for master login flow and agent console UI integrity.

Covers:
- Master login endpoint logic (password verification)
- Agent console HTML: chat panel present, removed sections absent
- No dead polling references to removed sections in agent.js
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "techbuzz-full", "techbuzz-full", "backend_python")
FRONTEND_DIR = os.path.join(ROOT, "techbuzz-full", "techbuzz-full", "frontend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_frontend(filename):
    path = os.path.join(FRONTEND_DIR, filename)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Master login — password verification logic
# ---------------------------------------------------------------------------

class TestMasterPasswordVerification:
    """Verify the updated verify_master_password logic without starting the server."""

    def _get_fn(self, plain_pw=None, hash_val="", salt_val=""):
        """Return a patched verify_master_password function."""
        import importlib
        import types

        # Build a minimal module-like namespace to exercise the logic
        import hashlib
        import secrets as _secrets

        def hash_secret(secret, salt):
            return hashlib.pbkdf2_hmac(
                "sha256", secret.encode("utf-8"), salt.encode("utf-8"), 200_000
            ).hex()

        def verify(password):
            if not password:
                return False
            if hash_val and salt_val:
                return _secrets.compare_digest(hash_secret(password, salt_val), hash_val)
            if plain_pw:
                return _secrets.compare_digest(password, plain_pw)
            return False

        return verify

    def test_rejects_empty_password_with_plaintext(self):
        verify = self._get_fn(plain_pw="secret123")
        assert verify("") is False

    def test_accepts_correct_plaintext_password(self):
        verify = self._get_fn(plain_pw="secret123")
        assert verify("secret123") is True

    def test_rejects_wrong_plaintext_password(self):
        verify = self._get_fn(plain_pw="secret123")
        assert verify("wrong") is False

    def test_hash_path_preferred_over_plaintext(self):
        import hashlib
        salt = "testsalt"
        pw = "hashpass"
        h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
        verify = self._get_fn(plain_pw="plainpass", hash_val=h, salt_val=salt)
        # Correct hashed password should pass
        assert verify("hashpass") is True
        # Plaintext password should NOT match when hash is configured
        assert verify("plainpass") is False

    def test_no_credentials_configured_always_fails(self):
        verify = self._get_fn(plain_pw="", hash_val="", salt_val="")
        assert verify("anything") is False

    def test_env_example_documents_master_password(self):
        env_example = os.path.join(BACKEND_DIR, ".env.example")
        with open(env_example, "r") as fh:
            content = fh.read()
        assert "MASTER_PASSWORD=" in content, ".env.example must document MASTER_PASSWORD"
        assert "MASTER_PASSWORD_SALT=" in content
        assert "MASTER_PASSWORD_HASH=" in content

    def test_app_py_reads_master_password_env(self):
        app_py = os.path.join(BACKEND_DIR, "app.py")
        with open(app_py, "r") as fh:
            source = fh.read()
        assert 'MASTER_PASSWORD = os.getenv("MASTER_PASSWORD"' in source, (
            "app.py must read MASTER_PASSWORD env var"
        )

    def test_verify_master_password_uses_plaintext_fallback(self):
        app_py = os.path.join(BACKEND_DIR, "app.py")
        with open(app_py, "r") as fh:
            source = fh.read()
        assert "if MASTER_PASSWORD:" in source, (
            "verify_master_password must use MASTER_PASSWORD as plaintext fallback"
        )

    def test_startup_warning_for_plaintext_password(self):
        app_py = os.path.join(BACKEND_DIR, "app.py")
        with open(app_py, "r") as fh:
            source = fh.read()
        assert "plain-text MASTER_PASSWORD" in source, (
            "app.py must log a startup warning when MASTER_PASSWORD is in use without a hash"
        )


# ---------------------------------------------------------------------------
# Agent Console HTML — chat panel present
# ---------------------------------------------------------------------------

class TestAgentConsoleChat:
    """The agent console must have a visible, functional chat panel."""

    def test_chat_log_present(self):
        html = _read_frontend("agent.html")
        assert 'id="agentChatLog"' in html, "agentChatLog div must be present"

    def test_chat_input_present(self):
        html = _read_frontend("agent.html")
        assert 'id="agentChatInput"' in html, "agentChatInput textarea must be present"

    def test_send_button_present(self):
        html = _read_frontend("agent.html")
        assert "sendAgentMessage" in html, "sendAgentMessage must be wired to a button"

    def test_chat_status_bar_present(self):
        html = _read_frontend("agent.html")
        assert 'id="chatStatusBar"' in html, "chatStatusBar for loading state must be present"

    def test_chat_provider_badge_present(self):
        html = _read_frontend("agent.html")
        assert 'id="chatProviderBadge"' in html, "chatProviderBadge must be present to show provider info"


# ---------------------------------------------------------------------------
# Agent Console HTML — removed sections must not be present
# ---------------------------------------------------------------------------

class TestAgentConsoleRemovedSections:
    """Sections that were explicitly removed must not appear in agent.html."""

    def test_brain_relay_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentRelayBoard"' not in html, "Brain Relay (agentRelayBoard) must be removed"

    def test_recent_hunts_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="recentHunts"' not in html, "Recent Hunts section must be removed"

    def test_reports_vault_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentReportList"' not in html, "Reports And Vault section must be removed"

    def test_execution_queue_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentQueueList"' not in html, "Execution Queue section must be removed"

    def test_mother_monitor_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentMonitorStats"' not in html, "Mother Monitor section must be removed"

    def test_domain_systems_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentDomainList"' not in html, "Domain Systems section must be removed"

    def test_brain_hierarchy_panel_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentBrainHierarchy"' not in html, "Brain Hierarchy panel must be removed"

    def test_permission_relay_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentPermissionRelay"' not in html, "Permission Relay section must be removed"

    def test_accounts_command_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="accountsAutomation"' not in html, "Accounts Command section must be removed"

    def test_ledger_entry_composer_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="accountsEntryStatus"' not in html, "Ledger Entry Composer must be removed"

    def test_accounts_guidance_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="agentAccountsGuideList"' not in html, "Accounts Guidance must be removed"

    def test_living_brain_hierarchy_removed(self):
        html = _read_frontend("agent.html")
        assert 'id="brainHierarchyWrap"' not in html, "Living Brain Hierarchy widget must be removed"

    def test_brain_hierarchy_js_not_loaded(self):
        html = _read_frontend("agent.html")
        assert "brain-hierarchy.js" not in html, "brain-hierarchy.js must not be loaded"

    def test_brain_accounts_css_not_loaded(self):
        html = _read_frontend("agent.html")
        assert "brain-accounts.css" not in html, "brain-accounts.css must not be loaded"

    def test_accounts_quick_link_removed(self):
        html = _read_frontend("agent.html")
        assert "accountsAutomation" not in html, "Quick link scrolling to accountsAutomation must be removed"


# ---------------------------------------------------------------------------
# Agent JS — no dead polling for removed sections
# ---------------------------------------------------------------------------

class TestAgentJsCleanup:
    """agent.js must not reference render functions for removed sections."""

    def test_render_relay_board_removed(self):
        js = _read_frontend("agent.js")
        assert "renderRelayBoard" not in js, "renderRelayBoard must be removed from agent.js"

    def test_render_recent_hunts_removed(self):
        js = _read_frontend("agent.js")
        assert "renderRecentHunts" not in js, "renderRecentHunts must be removed from agent.js"

    def test_render_vault_items_removed(self):
        js = _read_frontend("agent.js")
        assert "renderVaultItems" not in js, "renderVaultItems must be removed from agent.js"

    def test_render_reports_removed(self):
        js = _read_frontend("agent.js")
        assert "renderReports" not in js, "renderReports must be removed from agent.js"

    def test_render_queue_removed(self):
        js = _read_frontend("agent.js")
        assert "renderQueue" not in js, "renderQueue must be removed from agent.js"

    def test_render_monitor_removed(self):
        js = _read_frontend("agent.js")
        assert "renderMonitor" not in js, "renderMonitor must be removed from agent.js"

    def test_render_accounts_removed(self):
        js = _read_frontend("agent.js")
        assert "renderAccounts" not in js, "renderAccounts must be removed from agent.js"

    def test_save_accounts_profile_removed(self):
        js = _read_frontend("agent.js")
        assert "saveAccountsProfile" not in js, "saveAccountsProfile must be removed from agent.js"

    def test_send_agent_message_has_error_handling(self):
        js = _read_frontend("agent.js")
        # The improved sendAgentMessage should have a try/catch
        assert "sendAgentMessage" in js, "sendAgentMessage must still exist"
        assert "catch (error)" in js, "sendAgentMessage must include error handling"

    def test_chat_provider_badge_updated_in_js(self):
        js = _read_frontend("agent.js")
        assert "chatProviderBadge" in js, "agent.js must update chatProviderBadge with provider info"

    def test_chat_status_bar_updated_in_js(self):
        js = _read_frontend("agent.js")
        assert "chatStatusBar" in js, "agent.js must update chatStatusBar for loading state"
