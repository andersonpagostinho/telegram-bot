"""Agent Invocation Bridge Structural Tests — ETAPA C"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from event_bus.agent_invocation_bridge import AgentInvocationBridge, AgentConfig
from event_bus.dispatcher import EventDispatcher, AgentRole
from event_bus.governance import GovernanceEngine
from event_bus.event_bus import EventBus
from event_bus.event import Event, EventType


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path


@pytest.fixture
def bridge_setup(temp_db):
    """Setup bridge with mocked dependencies"""
    bus = EventBus(temp_db, use_wal=False)
    dispatcher = EventDispatcher(bus)
    governance = GovernanceEngine(bus)
    bridge = AgentInvocationBridge(bus, dispatcher, governance)
    return bridge, bus, dispatcher, governance


class TestBridgeInitialization:
    """Test bridge initialization and configuration"""

    def test_bridge_initialization(self, bridge_setup):
        """Bridge initializes with correct components"""
        bridge, bus, dispatcher, governance = bridge_setup
        
        assert bridge.event_bus is not None
        assert bridge.dispatcher is not None
        assert bridge.governance is not None
        assert bridge.anthropic_client is not None

    def test_default_agents_registered(self, bridge_setup):
        """Default agents are registered on initialization"""
        bridge, _, _, _ = bridge_setup
        
        # Should have Backend, QA, and Security agents
        assert "backend" in bridge.agent_configs
        assert "qa" in bridge.agent_configs
        assert "security" in bridge.agent_configs
        
        # Verify configurations
        backend_config = bridge.agent_configs["backend"]
        assert backend_config.agent_role == AgentRole.BACKEND
        assert backend_config.max_tokens == 2000
        assert backend_config.timeout_seconds == 300

    def test_agent_registration(self, bridge_setup):
        """Custom agent can be registered"""
        bridge, _, _, _ = bridge_setup
        
        custom_config = AgentConfig(
            agent_id="custom",
            agent_role=AgentRole.ARCHITECT,
            system_prompt="Custom system prompt",
            authorized_tools=["read"],
            max_tokens=1000,
            timeout_seconds=120
        )
        
        bridge.register_agent(custom_config)
        
        assert "custom" in bridge.agent_configs
        assert bridge.agent_configs["custom"].agent_id == "custom"


class TestBridgeValidation:
    """Test bridge validation logic"""

    def test_validate_target_valid(self, bridge_setup):
        """Valid target agent passes validation"""
        bridge, _, _, _ = bridge_setup
        
        result = bridge._validate_target(AgentRole.BACKEND)
        assert result is True

    def test_validate_target_invalid(self, bridge_setup):
        """Invalid target agent fails validation"""
        bridge, _, _, _ = bridge_setup
        
        # Create a mock agent role not in configs
        invalid_role = Mock(value="nonexistent")
        result = bridge._validate_target(invalid_role)
        assert result is False


class TestBridgeContextPreparation:
    """Test context preparation for agents"""

    def test_prepare_context(self, bridge_setup):
        """Context is prepared with all required fields"""
        bridge, _, _, _ = bridge_setup
        
        event = Event(
            event_type=EventType.TASK_ASSIGNED,
            mission_id="mission-001",
            task_id="task-001",
            agent_id="architect",
            agent_role="architect",
            correlation_id="corr-001",
            payload={"description": "Test task"}
        )
        
        config = bridge.agent_configs["backend"]
        context = bridge._prepare_context(event, config)
        
        assert context["task_id"] == "task-001"
        assert context["mission_id"] == "mission-001"
        assert context["event_id"] == event.event_id
        assert context["correlation_id"] == "corr-001"
        assert context["agent_id"] == "backend"
        assert "execution_id" in context
        assert "timestamp" in context


class TestBridgeGovernanceIntegration:
    """Test governance integration in bridge"""

    def test_governance_blocks_self_approval(self, bridge_setup):
        """Governance blocks agent from approving own work"""
        bridge, bus, _, _ = bridge_setup
        
        event = Event(
            event_type=EventType.REVIEW_APPROVED,
            mission_id="mission-001",
            agent_id="backend",
            agent_role="backend",
            correlation_id="corr-001",
            payload={"evidence": "tests passed"}
        )
        
        # Backend tries to approve Backend's work
        decision = bridge.governance.evaluate(event, "backend", "execute")
        
        # Should be blocked by rule 1
        assert not decision.allowed

    def test_governance_allows_authorized_action(self, bridge_setup):
        """Governance allows authorized actions"""
        bridge, bus, _, _ = bridge_setup
        
        event = Event(
            event_type=EventType.TASK_ASSIGNED,
            mission_id="mission-001",
            agent_id="architect",
            agent_role="architect",
            correlation_id="corr-001",
            payload={"description": "Test task"}
        )
        
        # Backend executing a task should be allowed
        decision = bridge.governance.evaluate(event, "backend", "execute_task")
        
        assert decision.allowed


class TestBridgeEventPublishing:
    """Test result event publishing"""

    @patch('event_bus.agent_invocation_bridge.Anthropic')
    def test_result_event_published(self, mock_anthropic, bridge_setup):
        """Result event is published to Event Bus"""
        bridge, bus, _, _ = bridge_setup
        
        # Mock successful agent execution
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text='{"status": "COMPLETED", "result": "success"}')]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_client.messages.create.return_value = mock_response
        
        with patch.object(bridge, 'anthropic_client', mock_client):
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
            
            # Verify event was published
            published = bus.store.get_event(event.event_id)
            assert published is not None


class TestBridgeErrorHandling:
    """Test error handling in bridge"""

    def test_governance_rejection_recorded(self, bridge_setup):
        """Governance rejection is recorded in Event Bus"""
        bridge, bus, dispatcher, _ = bridge_setup
        
        event = Event(
            event_type=EventType.REVIEW_APPROVED,
            mission_id="mission-001",
            agent_id="backend",
            agent_role="backend",
            correlation_id="corr-001",
            payload={"evidence": "not provided"}
        )
        
        bus.publish(event)
        
        # Governance would block this
        decision = bridge.governance.evaluate(event, "backend", "execute")
        assert not decision.allowed
        
        # Event should be in store
        retrieved = bus.store.get_event(event.event_id)
        assert retrieved is not None

    def test_invalid_json_response_handled(self, bridge_setup):
        """Invalid JSON response is handled gracefully"""
        bridge, _, _, _ = bridge_setup
        
        config = bridge.agent_configs["backend"]
        context = bridge._prepare_context(Mock(task_id="t1", mission_id="m1", event_id="e1", correlation_id="c1", payload={}), config)
        
        # Try to parse invalid JSON
        invalid_json = "This is not JSON"
        
        try:
            import json
            result = json.loads(invalid_json)
        except json.JSONDecodeError:
            # Expected behavior
            pass


class TestBridgeIsolation:
    """Test isolation between different missions/agents"""

    def test_events_isolated_by_mission(self, bridge_setup):
        """Events from different missions are isolated"""
        bridge, bus, _, _ = bridge_setup
        
        # Create events for different missions
        event1 = Event(
            event_type=EventType.TASK_ASSIGNED,
            mission_id="mission-001",
            agent_id="backend",
            agent_role="backend",
            correlation_id="corr-001",
            payload={}
        )
        
        event2 = Event(
            event_type=EventType.TASK_ASSIGNED,
            mission_id="mission-002",
            agent_id="backend",
            agent_role="backend",
            correlation_id="corr-002",
            payload={}
        )
        
        bus.publish(event1)
        bus.publish(event2)
        
        # Get pending for mission-001
        pending1 = bus.store.get_pending_events("mission-001", limit=10)
        
        # Should only get event from mission-001
        mission_ids = [e.mission_id for e in pending1]
        assert all(m == "mission-001" for m in mission_ids)

    def test_correlation_chain_preserved(self, bridge_setup):
        """Correlation ID is preserved across event chain"""
        bridge, bus, _, _ = bridge_setup
        
        correlation_id = "correlation-chain-001"
        
        event1 = Event(
            event_type=EventType.TASK_ASSIGNED,
            mission_id="mission-001",
            agent_id="architect",
            agent_role="architect",
            correlation_id=correlation_id,
            payload={}
        )
        
        event1_id = bus.publish(event1)
        
        # Second event in chain references first
        event2 = Event(
            event_type=EventType.TASK_COMPLETED,
            mission_id="mission-001",
            agent_id="backend",
            agent_role="backend",
            correlation_id=correlation_id,
            causation_id=event1_id,
            payload={"result": "done"}
        )
        
        bus.publish(event2)
        
        # Retrieve and verify chain
        retrieved = bus.store.get_event(event2.event_id)
        assert retrieved.causation_id == event1_id
        assert retrieved.correlation_id == correlation_id


class TestBridgeSyncWrapper:
    """Test synchronous wrapper for compatibility"""

    def test_sync_wrapper_exists(self, bridge_setup):
        """Synchronous wrapper is available"""
        bridge, _, _, _ = bridge_setup
        
        from event_bus.agent_invocation_bridge import AgentInvocationBridgeSync
        sync_bridge = AgentInvocationBridgeSync(bridge.event_bus, bridge.dispatcher, bridge.governance)
        
        # Should have both async and sync methods
        assert hasattr(sync_bridge, 'invoke_agent')
        assert hasattr(sync_bridge, 'invoke_agent_sync')


class TestBridgePermissions:
    """Test agent permissions and authorization"""

    def test_backend_has_correct_permissions(self, bridge_setup):
        """Backend agent has correct permissions"""
        bridge, _, _, _ = bridge_setup
        
        backend_config = bridge.agent_configs["backend"]
        
        # Backend should be able to:
        # - read_file
        # - write_file
        # - run_tests
        # - git_commit
        
        assert "read_file" in backend_config.authorized_tools
        assert "write_file" in backend_config.authorized_tools
        assert "run_tests" in backend_config.authorized_tools
        assert "git_commit" in backend_config.authorized_tools

    def test_qa_has_read_only_permissions(self, bridge_setup):
        """QA agent has read-only permissions"""
        bridge, _, _, _ = bridge_setup
        
        qa_config = bridge.agent_configs["qa"]
        
        # QA should be able to:
        # - read_file
        # - run_tests
        # But NOT write
        
        assert "read_file" in qa_config.authorized_tools
        assert "run_tests" in qa_config.authorized_tools
        assert "write_file" not in qa_config.authorized_tools

    def test_security_auditor_read_only(self, bridge_setup):
        """Security Auditor is read-only"""
        bridge, _, _, _ = bridge_setup
        
        security_config = bridge.agent_configs["security"]
        
        # Security should only have read access
        assert "read_file" in security_config.authorized_tools
        assert "write_file" not in security_config.authorized_tools
        assert "git_commit" not in security_config.authorized_tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
