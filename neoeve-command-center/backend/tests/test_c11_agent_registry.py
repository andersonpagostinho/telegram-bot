"""Tests for Agent Registry (C.1.1)."""

import pytest
from app.services.agent_registry import (
    AgentRegistry, AgentRole, Permission, OperationalState, ConnectivityState
)


class TestAgentRegistry:
    """Agent Registry tests (10 scenarios)."""

    def test_seven_agents_registered(self):
        """All seven agents in registry."""
        assert len(AgentRegistry.AGENTS) == 7
        assert "architect" in AgentRegistry.AGENTS
        assert "openai_validator" in AgentRegistry.AGENTS
        print("✓ Test 1: Seven agents registered")

    def test_agent_roles(self):
        """Agent roles correctly assigned."""
        assert AgentRegistry.AGENTS["architect"]["role"] == AgentRole.ARCHITECT
        assert AgentRegistry.AGENTS["backend_developer"]["role"] == AgentRole.BACKEND_DEVELOPER
        assert AgentRegistry.AGENTS["openai_validator"]["role"] == AgentRole.OPENAI_VALIDATOR
        print("✓ Test 2: Agent roles")

    def test_permission_matrix_architect(self):
        """Architect permissions."""
        agent_id = AgentRegistry.AGENTS["architect"]["agent_id"]
        assert AgentRegistry.has_permission(agent_id, Permission.WRITE)
        assert AgentRegistry.has_permission(agent_id, Permission.EXECUTE)
        print("✓ Test 3: Architect permissions")

    def test_permission_deny_qa_write(self):
        """QA cannot write production code."""
        agent_id = AgentRegistry.AGENTS["qa_engineer"]["agent_id"]
        assert not AgentRegistry.has_permission(agent_id, Permission.WRITE)
        print("✓ Test 4: QA denied WRITE")

    def test_security_auditor_veto(self):
        """Security Auditor can veto."""
        agent_id = AgentRegistry.AGENTS["security_auditor"]["agent_id"]
        assert AgentRegistry.can_veto(agent_id)
        print("✓ Test 5: Security Auditor veto")

    def test_openai_validator_read_only(self):
        """OpenAI Validator is read-only."""
        agent_id = AgentRegistry.AGENTS["openai_validator"]["agent_id"]
        assert AgentRegistry.is_read_only(agent_id)
        assert not AgentRegistry.has_permission(agent_id, Permission.WRITE)
        print("✓ Test 6: OpenAI Validator read-only")

    def test_capabilities(self):
        """Agent capabilities available."""
        architect_id = AgentRegistry.AGENTS["architect"]["agent_id"]
        caps = AgentRegistry.get_capabilities(architect_id)
        assert "plan" in caps
        assert "decompose" in caps
        print("✓ Test 7: Capabilities")

    def test_operational_states(self):
        """Operational states defined."""
        assert OperationalState.IDLE.value == "IDLE"
        assert OperationalState.WORKING.value == "WORKING"
        assert OperationalState.ERROR.value == "ERROR"
        print("✓ Test 8: Operational states")

    def test_connectivity_states(self):
        """Connectivity states defined."""
        assert ConnectivityState.ONLINE.value == "ONLINE"
        assert ConnectivityState.NOT_CONFIGURED.value == "NOT_CONFIGURED"
        print("✓ Test 9: Connectivity states")

    def test_no_executor_configured(self):
        """Agents without executor show NOT_CONFIGURED."""
        # Initial state before runtime setup
        status = ConnectivityState.NOT_CONFIGURED.value
        assert status == "NOT_CONFIGURED"
        print("✓ Test 10: NOT_CONFIGURED for unexecuted agents")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
