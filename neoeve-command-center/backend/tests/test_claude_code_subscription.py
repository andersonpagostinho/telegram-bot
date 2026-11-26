"""Tests for Claude Code subscription verification via native CLI."""

import json
import pytest
import subprocess
from unittest.mock import patch, MagicMock, Mock
from app.services.claude_code_adapter import ClaudeCodeAdapter


class TestClaudeCodeSubscriptionVerification:
    """Test suite for subscription verification."""

    def test_verify_subscription_pro_active(self):
        """Test successful Pro subscription verification."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        # Mock successful auth status response
        mock_response = {
            "loggedIn": True,
            "authMethod": "claude.ai",
            "subscriptionType": "pro",
            "planTier": "pro",
            "loginExpiresAt": "2026-12-22T18:52:28.753Z",
            "email": "andersonpagostinho@gmail.com",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_response),
            )

            is_valid, status = adapter.verify_subscription()

            assert is_valid is True
            assert status.get("subscriptionType") == "pro"
            assert status.get("loggedIn") is True
            assert adapter._subscription_verified is True

    def test_verify_subscription_not_logged_in(self):
        """Test subscription check when CLI is not logged in."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        mock_response = {
            "loggedIn": False,
            "authMethod": None,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_response),
            )

            is_valid, status = adapter.verify_subscription()

            assert is_valid is False
            assert "not authenticated" in status.get("error", "").lower()

    def test_verify_subscription_non_pro_tier(self):
        """Test subscription check with non-Pro tier."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        mock_response = {
            "loggedIn": True,
            "subscriptionType": "free",
            "planTier": "free",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_response),
            )

            is_valid, status = adapter.verify_subscription()

            assert is_valid is False
            assert "not Pro tier" in status.get("error", "")

    def test_verify_subscription_cli_not_found(self):
        """Test verification when CLI is not in PATH."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            is_valid, status = adapter.verify_subscription()

            assert is_valid is False
            assert "not found" in status.get("error", "").lower()

    def test_verify_subscription_command_fails(self):
        """Test verification when auth status command fails."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/claude"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stderr="Unauthorized",
                )

                is_valid, status = adapter.verify_subscription()

                assert is_valid is False
                assert "failed" in status.get("error", "").lower()

    def test_verify_subscription_json_parse_error(self):
        """Test verification with invalid JSON response."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/claude"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="invalid json {",
                )

                is_valid, status = adapter.verify_subscription()

                assert is_valid is False
                assert "JSON" in status.get("error", "")

    def test_verify_subscription_timeout(self):
        """Test verification when CLI command times out."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/claude"

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("claude", 5)

                is_valid, status = adapter.verify_subscription()

                assert is_valid is False
                assert "timeout" in status.get("error", "").lower()

    def test_health_check_all_good(self):
        """Test health check with all systems working."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        auth_response = {
            "loggedIn": True,
            "subscriptionType": "pro",
            "planTier": "pro",
        }

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/claude"

            with patch("subprocess.run") as mock_run:
                # First call: --version, second call: auth status
                mock_run.side_effect = [
                    MagicMock(returncode=0),
                    MagicMock(returncode=0, stdout=json.dumps(auth_response)),
                ]

                result = adapter.health_check()

                assert result["cli_available"] is True
                assert result["subscription_valid"] is True
                assert len(result["errors"]) == 0

    def test_health_check_cli_not_available(self):
        """Test health check when CLI is not available."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = adapter.health_check()

            assert result["cli_available"] is False
            assert len(result["errors"]) > 0

    def test_health_check_subscription_invalid(self):
        """Test health check with invalid subscription."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        auth_response = {
            "loggedIn": False,
        }

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/claude"

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(returncode=0),
                    MagicMock(returncode=0, stdout=json.dumps(auth_response)),
                ]

                result = adapter.health_check()

                assert result["cli_available"] is True
                assert result["subscription_valid"] is False
                assert len(result["errors"]) > 0

    def test_execute_with_subscription_verified(self):
        """Test execute when subscription is already verified."""
        adapter = ClaudeCodeAdapter(subscription_only=True)
        adapter._subscription_verified = True  # Already verified

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock a simple command
            with patch("subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                exit_code, stdout, stderr = adapter.execute(
                    execution_id="test-exec-1",
                    task_description="echo hello",
                    workspace_path=tmpdir,
                    timeout_seconds=5,
                )

                assert exit_code == 0
                assert stdout == "output"

    def test_execute_subscription_verification_fails(self):
        """Test execute when subscription verification fails."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        auth_response = {
            "loggedIn": False,
        }

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/bin/claude"

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0,
                        stdout=json.dumps(auth_response),
                    )

                    exit_code, stdout, stderr = adapter.execute(
                        execution_id="test-exec-2",
                        task_description="echo hello",
                        workspace_path=tmpdir,
                        timeout_seconds=5,
                    )

                    assert exit_code == 1
                    assert "verification failed" in stderr.lower()

    def test_subscription_only_false_skips_verification(self):
        """Test that subscription_only=False skips verification."""
        adapter = ClaudeCodeAdapter(subscription_only=False)

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                # Should execute without subscription check
                exit_code, stdout, stderr = adapter.execute(
                    execution_id="test-exec-3",
                    task_description="echo hello",
                    workspace_path=tmpdir,
                    timeout_seconds=5,
                )

                # Execution proceeds (no subscription error)
                assert exit_code == 0

    def test_get_claude_executable_found(self):
        """Test finding Claude executable."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/claude"
            exe = adapter._get_claude_executable()
            assert exe == "/usr/bin/claude"

    def test_get_claude_executable_not_found(self):
        """Test when Claude executable not found."""
        adapter = ClaudeCodeAdapter(subscription_only=True)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            exe = adapter._get_claude_executable()
            assert exe is None


class TestClaudeCodeIntegration:
    """Integration tests with real CLI (skipped in CI)."""

    @pytest.mark.integration
    def test_real_subscription_check(self):
        """Integration test: check real subscription status.

        This test requires Claude Code CLI to be installed and authenticated.
        Run locally with: pytest -m integration
        """
        adapter = ClaudeCodeAdapter(subscription_only=True)

        # This will call the real CLI
        is_valid, status = adapter.verify_subscription()

        # Log results for inspection
        print(f"\nReal subscription check result: {status}")

        # At minimum, check should not crash
        assert isinstance(is_valid, bool)
        assert isinstance(status, dict)

    @pytest.mark.integration
    def test_real_health_check(self):
        """Integration test: run real health check.

        This test requires Claude Code CLI to be installed.
        """
        adapter = ClaudeCodeAdapter(subscription_only=True)

        result = adapter.health_check()

        print(f"\nReal health check result: {result}")

        assert isinstance(result, dict)
        assert "cli_available" in result
        assert "subscription_valid" in result
        assert "errors" in result
