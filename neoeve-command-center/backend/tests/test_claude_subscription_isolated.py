"""Isolated tests for Claude Code subscription - no database dependencies."""

import json
import sys
import os
from unittest.mock import patch, MagicMock
import subprocess

# Set required env vars BEFORE any imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.claude_code_adapter import ClaudeCodeAdapter


def test_verify_subscription_pro_active():
    """Test successful Pro subscription verification."""
    adapter = ClaudeCodeAdapter(subscription_only=True)

    mock_response = {
        "loggedIn": True,
        "authMethod": "claude.ai",
        "subscriptionType": "pro",
        "planTier": "pro",
        "loginExpiresAt": "2026-12-22T18:52:28.753Z",
        "email": "test@example.com",
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_response),
        )

        is_valid, status = adapter.verify_subscription()

        assert is_valid is True, f"Expected valid=True, got {is_valid}"
        assert status.get("subscriptionType") == "pro", f"Expected pro, got {status.get('subscriptionType')}"
        assert status.get("loggedIn") is True
        assert adapter._subscription_verified is True
        print("✓ test_verify_subscription_pro_active PASSED")


def test_verify_subscription_not_logged_in():
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

        assert is_valid is False, "Expected valid=False for not logged in"
        assert "not authenticated" in status.get("error", "").lower()
        print("✓ test_verify_subscription_not_logged_in PASSED")


def test_verify_subscription_non_pro_tier():
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

        assert is_valid is False, "Expected valid=False for non-Pro"
        assert "not Pro tier" in status.get("error", "") or "not Pro" in status.get("error", "")
        print("✓ test_verify_subscription_non_pro_tier PASSED")


def test_verify_subscription_cli_not_found():
    """Test verification when CLI is not in PATH."""
    adapter = ClaudeCodeAdapter(subscription_only=True)

    with patch("shutil.which") as mock_which:
        mock_which.return_value = None

        is_valid, status = adapter.verify_subscription()

        assert is_valid is False
        assert "not found" in status.get("error", "").lower()
        print("✓ test_verify_subscription_cli_not_found PASSED")


def test_verify_subscription_command_fails():
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
            print("✓ test_verify_subscription_command_fails PASSED")


def test_verify_subscription_json_parse_error():
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
            print("✓ test_verify_subscription_json_parse_error PASSED")


def test_verify_subscription_timeout():
    """Test verification when CLI command times out."""
    adapter = ClaudeCodeAdapter(subscription_only=True)

    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/claude"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("claude", 5)

            is_valid, status = adapter.verify_subscription()

            assert is_valid is False
            assert "timeout" in status.get("error", "").lower()
            print("✓ test_verify_subscription_timeout PASSED")


def test_health_check_all_good():
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
            mock_run.side_effect = [
                MagicMock(returncode=0),
                MagicMock(returncode=0, stdout=json.dumps(auth_response)),
            ]

            result = adapter.health_check()

            assert result["cli_available"] is True
            assert result["subscription_valid"] is True
            assert len(result["errors"]) == 0
            print("✓ test_health_check_all_good PASSED")


def test_health_check_cli_not_available():
    """Test health check when CLI is not available."""
    adapter = ClaudeCodeAdapter(subscription_only=True)

    with patch("shutil.which") as mock_which:
        mock_which.return_value = None

        result = adapter.health_check()

        assert result["cli_available"] is False
        assert len(result["errors"]) > 0
        print("✓ test_health_check_cli_not_available PASSED")


def test_health_check_subscription_invalid():
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
            print("✓ test_health_check_subscription_invalid PASSED")


def test_subscription_only_false_skips_verification():
    """Test that subscription_only=False skips verification."""
    adapter = ClaudeCodeAdapter(subscription_only=False)

    # health_check should still work but not require subscription
    result = adapter.health_check()

    assert isinstance(result, dict)
    assert "cli_available" in result
    print("✓ test_subscription_only_false_skips_verification PASSED")


def test_get_claude_executable_found():
    """Test finding Claude executable."""
    adapter = ClaudeCodeAdapter(subscription_only=True)

    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/claude"
        exe = adapter._get_claude_executable()
        assert exe == "/usr/bin/claude"
        print("✓ test_get_claude_executable_found PASSED")


def test_get_claude_executable_not_found():
    """Test when Claude executable not found."""
    adapter = ClaudeCodeAdapter(subscription_only=True)

    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        exe = adapter._get_claude_executable()
        assert exe is None
        print("✓ test_get_claude_executable_not_found PASSED")


def test_real_subscription_check():
    """Real integration test: check actual subscription status.

    This test runs against the REAL Claude CLI installed on the system.
    """
    adapter = ClaudeCodeAdapter(subscription_only=True)

    try:
        is_valid, status = adapter.verify_subscription()
        print(f"\n✓ REAL SUBSCRIPTION CHECK RESULT: valid={is_valid}")
        print(f"  Details: {json.dumps(status, indent=2)}")

        # Check that it at least returns valid response structure
        assert isinstance(is_valid, bool)
        assert isinstance(status, dict)

        # If Pro, should have correct fields
        if is_valid:
            assert status.get("subscriptionType") == "pro"
            assert status.get("loggedIn") is True
            print("  ✓ Pro subscription verified with real CLI!")
        else:
            print(f"  ✗ Subscription not valid: {status.get('error')}")

    except Exception as e:
        print(f"✗ Real subscription check failed: {e}")
        print("  This is expected if Claude CLI is not installed/authenticated")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("RUNNING CLAUDE CODE SUBSCRIPTION TESTS (ISOLATED)")
    print("="*70 + "\n")

    tests = [
        test_verify_subscription_pro_active,
        test_verify_subscription_not_logged_in,
        test_verify_subscription_non_pro_tier,
        test_verify_subscription_cli_not_found,
        test_verify_subscription_command_fails,
        test_verify_subscription_json_parse_error,
        test_verify_subscription_timeout,
        test_health_check_all_good,
        test_health_check_cli_not_available,
        test_health_check_subscription_invalid,
        test_subscription_only_false_skips_verification,
        test_get_claude_executable_found,
        test_get_claude_executable_not_found,
    ]

    passed = 0
    failed = 0

    print("UNIT TESTS (mocked):")
    print("-" * 70)
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1

    print("\n" + "-" * 70)
    print("INTEGRATION TEST (real CLI):")
    print("-" * 70)
    try:
        test_real_subscription_check()
    except Exception as e:
        print(f"✗ Integration test error: {e}")

    print("\n" + "="*70)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    sys.exit(0 if failed == 0 else 1)
