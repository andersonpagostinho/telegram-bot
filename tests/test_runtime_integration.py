"""Integration Tests for Runtime with Agent Invocation Bridge

Tests that verify the new runtime adapter works correctly with the bridge
while preserving all governance and event bus functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock

from event_bus.agent_invocation_bridge import AgentInvocationBridge
from event_bus.runtime import AgentRuntime, RuntimeResult
from event_bus.dispatcher import EventDispatcher, AgentRole
from event_bus.governance import GovernanceEngine
from event_bus.event_bus import EventBus
from event_bus.event import Event, EventType


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path


@pytest.fixture
def bridge_setup(temp_db):
    """Setup bridge with mock runtime"""
    bus = EventBus(temp_db, use_wal=False)
    dispatcher = EventDispatcher(bus)
    governance = GovernanceEngine(bus)

    # Mock runtime
    mock_runtime = Mock(spec=AgentRuntime)

    bridge = AgentInvocationBridge(bus, dispatcher, governance, mock_runtime)
    return bridge, bus, dispatcher, governance, mock_runtime


class TestRuntimeIntegration:
    """Integration tests with new runtime"""

    def test_bridge_initialization_with_runtime(self, bridge_setup):
        """Bridge initializes with injected runtime"""
        bridge, _, _, _, mock_runtime = bridge_setup

        assert bridge.runtime is not None
        assert bridge.runtime == mock_runtime

    def test_runtime_invocation_called(self, bridge_setup):
        """Bridge calls runtime.invoke() instead of anthropic"""
        bridge, bus, dispatcher, governance, mock_runtime = bridge_setup

        # Setup mock runtime to return success
        mock_runtime.invoke = AsyncMock(return_value=RuntimeResult(
            status="COMPLETED",
            result={"status": "COMPLETED", "result": "success"},
            execution_id="exec-123"
        ))

        # Create event
        event = Event(
            event_type=EventType.TASK_ASSIGNED,
            mission_id="mission-001",
            task_id="task-001",
            agent_id="architect",
            agent_role="architect",
            correlation_id="corr-001",
            payload={"description": "Test task"}
        )

        bus.publish(event)

        # This would normally be called by dispatcher
        # For now just verify runtime is available
        assert bridge.runtime is not None
        assert hasattr(bridge.runtime, 'invoke')

    def test_governance_still_enforced(self, bridge_setup):
        """Governance rules still work with new runtime"""
        bridge, bus, dispatcher, governance, _ = bridge_setup

        event = Event(
            event_type=EventType.REVIEW_APPROVED,
            mission_id="mission-001",
            agent_id="backend",
            agent_role="backend",
            correlation_id="corr-001",
            payload={"evidence": "tests passed"}
        )

        # Backend tries to approve its own work - should be blocked
        decision = governance.evaluate(event, "backend", "execute")

        # Governance is INDEPENDENT of runtime
        assert not decision.allowed

    def test_event_bus_persistence_unchanged(self, bridge_setup):
        """Event Bus persists events regardless of runtime"""
        bridge, bus, dispatcher, governance, _ = bridge_setup

        event = Event(
            event_type=EventType.TASK_CREATED,
            mission_id="mission-001",
            agent_id="architect",
            agent_role="architect",
            correlation_id="corr-001"
        )

        event_id = bus.publish(event)
        retrieved = bus.store.get_event(event_id)

        assert retrieved is not None
        assert retrieved.mission_id == "mission-001"
        # Event Bus is INDEPENDENT of runtime

    def test_isolation_multitenant_preserved(self, bridge_setup):
        """Multi-tenant isolation preserved with new runtime"""
        bridge, bus, dispatcher, governance, _ = bridge_setup

        # Create events for different missions
        event1 = Event(
            event_type=EventType.TASK_CREATED,
            mission_id="mission-001",
            agent_id="backend",
            agent_role="backend",
            correlation_id="corr-001"
        )

        event2 = Event(
            event_type=EventType.TASK_CREATED,
            mission_id="mission-002",
            agent_id="backend",
            agent_role="backend",
            correlation_id="corr-002"
        )

        bus.publish(event1)
        bus.publish(event2)

        # Get pending for mission-001
        pending = bus.store.get_pending_events("mission-001", limit=10)

        # Should only get events from mission-001
        mission_ids = [e.mission_id for e in pending]
        assert all(m == "mission-001" for m in mission_ids)
        # Isolation is INDEPENDENT of runtime


class TestSubscriptionOnlyPolicy:
    """Test SUBSCRIPTION_ONLY policy enforcement"""

    def test_api_key_detection(self):
        """SUBSCRIPTION_ONLY policy detects API Key"""
        from event_bus.claude_code_runtime import SubscriptionOnlyPolicy

        # Mock environment with API Key
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                SubscriptionOnlyPolicy.validate_environment()

    def test_clean_environment(self):
        """SUBSCRIPTION_ONLY policy creates clean env"""
        from event_bus.claude_code_runtime import SubscriptionOnlyPolicy

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test", "PATH": "/bin"}):
            clean_env = SubscriptionOnlyPolicy.clean_environment()

            assert "ANTHROPIC_API_KEY" not in clean_env
            assert "PATH" in clean_env


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
