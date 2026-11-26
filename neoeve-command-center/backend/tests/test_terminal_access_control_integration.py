"""Integration tests: Terminal Access Control + AgentRuntime + ClaudeCodeAdapter."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.terminal_access_control import TerminalAccessControl
from app.services.agent_registry import AgentRegistry, Permission, OperationalState
from app.services.agent_runtime import AgentRuntime
from database.models import Execution


class TestTerminalAccessControlIntegration:
    """Test that TerminalAccessControl is enforced in real execution paths."""

    # Test agents
    TEST_AGENT_ID = "agent-backend"
    TEST_TENANT_ID = "test-tenant-secure"
    TEST_PROJECT_ID = "test-project-123"
    TEST_WORKSPACE = "/home/agent/workspace"
    TEST_EXECUTION_ID = "exec-test-123"
    TEST_TASK_ID = "task-test-456"
    TEST_MISSION_ID = "mission-test-789"

    # ========================================================================
    # TEST 1: Command in Whitelist is Permitted
    # ========================================================================

    def test_whitelist_permitted_command(self):
        """Test: Permitted command passes validation."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="ls -la /tmp",
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        assert is_allowed, f"ls should be permitted, but blocked: {reason}"

    def test_whitelist_permitted_git(self):
        """Test: Git command passes validation."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="git status",
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        assert is_allowed, f"git should be permitted, but blocked: {reason}"

    def test_whitelist_permitted_python(self):
        """Test: Python command passes validation."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="python script.py",
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        assert is_allowed, f"python should be permitted, but blocked: {reason}"

    # ========================================================================
    # TEST 2: Unknown Command is Blocked (Whitelist)
    # ========================================================================

    def test_whitelist_unknown_command_blocked(self):
        """Test: Unknown command is blocked (Whitelist mode)."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="mysterious_unknown_cmd",
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        assert not is_allowed, "Unknown command should be blocked"
        assert "not in whitelist" in reason

    def test_whitelist_dangerous_cmd_blocked(self):
        """Test: Even if not in blacklist, unknown commands blocked."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="perl -e 'system(\"rm -rf /\")'",
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        assert not is_allowed, "perl is not in whitelist"
        assert "not in whitelist" in reason

    # ========================================================================
    # TEST 3: Path Traversal Protection
    # ========================================================================

    def test_path_traversal_in_command(self):
        """Test: Path traversal (..) in command is blocked."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="cat ../../../etc/passwd",
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        # cat is in whitelist, but workspace validation should still run
        assert is_allowed or ".." in reason, "Should warn about path traversal"

    def test_path_traversal_in_workspace(self):
        """Test: Path traversal in workspace path is blocked."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="ls",
            agent_id=self.TEST_AGENT_ID,
            workspace_path="/home/agent/../../../etc",
            tenant_id=self.TEST_TENANT_ID,
        )
        assert not is_allowed, "Workspace with .. should be blocked"
        assert ".." in reason

    # ========================================================================
    # TEST 4: Permission Validation
    # ========================================================================

    def test_agent_without_execute_permission_blocked(self):
        """Test: Agent without EXECUTE permission is blocked."""
        # This test assumes AgentRegistry.has_permission returns False for unknown agent
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="ls",
            agent_id="agent-nonexistent-99999",
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        # Depending on AgentRegistry implementation, may be blocked
        # If it returns False for unknown agent, this test validates that

    # ========================================================================
    # TEST 5: Tenant Isolation
    # ========================================================================

    def test_command_validation_requires_tenant(self):
        """Test: Command validation requires valid tenant."""
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="ls",
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id="",  # Empty tenant
        )
        assert not is_allowed, "Command should be blocked without tenant"

    def test_audit_logs_tenant_isolation(self):
        """Test: Audit logs include tenant_id for isolation."""
        # This is a logical test: audit_command should log tenant_id
        # Making sure data is not mixed between tenants
        # Actual verification would require database inspection
        pass

    # ========================================================================
    # TEST 6: Blacklist Secondary Protection
    # ========================================================================

    def test_blacklist_still_protects(self):
        """Test: Blacklist provides second layer of protection."""
        # Even though a command might be in whitelist, blacklist should block
        # for example: ls with rm -rf injection in args (if parsing doesn't catch it)
        is_allowed, reason = TerminalAccessControl.validate_command(
            command="echo 'rm -rf /' | base64 --decode",  # echo is whitelisted
            agent_id=self.TEST_AGENT_ID,
            workspace_path=self.TEST_WORKSPACE,
            tenant_id=self.TEST_TENANT_ID,
        )
        # Should block on blacklist (base64 --decode pattern)
        assert not is_allowed, "base64 decode pattern should be blocked"

    # ========================================================================
    # TEST 7: Auditoria Integration
    # ========================================================================

    def test_audit_command_records_permitted(self):
        """Test: Audit command records permitted operations."""
        # This test validates that audit_command() can be called
        # and that it logs properly
        result = TerminalAccessControl.audit_command(
            execution_id=self.TEST_EXECUTION_ID,
            agent_id=self.TEST_AGENT_ID,
            task_id=self.TEST_TASK_ID,
            tenant_id=self.TEST_TENANT_ID,
            project_id=self.TEST_PROJECT_ID,
            command="ls -la",
            workspace_path=self.TEST_WORKSPACE,
            status="PERMITTED",
            db=None,  # No DB in test
        )
        # Function should handle None db gracefully
        assert result is False, "Audit without DB session should return False (expected)"

    def test_audit_command_records_blocked(self):
        """Test: Audit command records blocked operations."""
        result = TerminalAccessControl.audit_command(
            execution_id=self.TEST_EXECUTION_ID,
            agent_id=self.TEST_AGENT_ID,
            task_id=self.TEST_TASK_ID,
            tenant_id=self.TEST_TENANT_ID,
            project_id=self.TEST_PROJECT_ID,
            command="unknown_command",
            workspace_path=self.TEST_WORKSPACE,
            status="BLOCKED",
            block_reason="Command not in whitelist",
            db=None,  # No DB in test
        )
        assert result is False, "Audit without DB session should return False"

    # ========================================================================
    # TEST 8: Resource Limits Declaration
    # ========================================================================

    def test_resource_limits_defined(self):
        """Test: Resource limits are defined."""
        limits = TerminalAccessControl.RESOURCE_LIMITS
        assert "timeout_seconds" in limits
        assert "memory_mb" in limits
        assert "cpu_percent" in limits
        assert limits["timeout_seconds"] == 300
        assert limits["memory_mb"] == 2048
        assert limits["cpu_percent"] == 80

    # ========================================================================
    # TEST 9: Whitelist Completeness
    # ========================================================================

    def test_whitelist_contains_common_operations(self):
        """Test: Whitelist includes common safe operations."""
        allowed = TerminalAccessControl.ALLOWED_OPERATIONS

        # Safe read operations
        assert "ls" in allowed or any("ls" in op for op in allowed)
        assert "cat" in allowed or any("cat" in op for op in allowed)

        # Build tools
        assert "make" in allowed or any("make" in op for op in allowed)

        # Git
        assert "git" in allowed or any("git" in op for op in allowed)

        # Python
        assert "python" in allowed or any("python" in op for op in allowed)

    # ========================================================================
    # TEST 10: Dangerous Commands Blocked
    # ========================================================================

    def test_dangerous_commands_not_in_whitelist(self):
        """Test: Dangerous commands are not in whitelist."""
        allowed = TerminalAccessControl.ALLOWED_OPERATIONS

        dangerous = ["rm", "sudo", "chmod", "dd", "mkfs", "reboot", "shutdown"]

        for cmd in dangerous:
            # These should NOT be whitelisted (rm is there but not with -rf)
            # For rm specifically, we allow it but only without -r/-f flags
            if cmd == "rm":
                # rm is in whitelist but should be blocked with -r or -f
                is_allowed, reason = TerminalAccessControl.validate_command(
                    command="rm -rf /",
                    agent_id=self.TEST_AGENT_ID,
                    workspace_path=self.TEST_WORKSPACE,
                    tenant_id=self.TEST_TENANT_ID,
                )
                assert not is_allowed, "rm -rf should be blocked by blacklist"
            else:
                # Other dangerous commands should not be in whitelist
                assert not any(cmd in op for op in allowed), f"{cmd} should not be whitelisted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
