"""Basic Event Bus Core Tests — PHASE 1"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from event_bus import Event, EventType, EventBus, InvalidEventException
import tempfile
import pytest


class TestEventSchema:
    """Test event schema and validation"""

    def test_valid_event(self):
        """Test creating valid event"""
        event = Event(
            event_type=EventType.TASK_CREATED,
            mission_id="mission-001",
            agent_id="agent-001",
            correlation_id="corr-001"
        )
        assert event.event_id
        assert event.mission_id == "mission-001"
        assert event.timestamp

    def test_invalid_missing_mission(self):
        """Test validation rejects missing mission_id"""
        with pytest.raises(InvalidEventException):
            Event(
                event_type=EventType.TASK_CREATED,
                agent_id="agent-001",
                correlation_id="corr-001"
            )

    def test_invalid_secret_in_payload(self):
        """Test validation rejects secrets in payload"""
        with pytest.raises(InvalidEventException):
            Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                agent_id="agent-001",
                correlation_id="corr-001",
                payload={"api_key": "sk-secret"}
            )


class TestEventStore:
    """Test SQLite persistence"""

    @pytest.fixture
    def bus(self):
        """Create event bus with temp database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus = EventBus(db_path)
            yield bus

    def test_store_and_retrieve(self, bus):
        """Test storing and retrieving events"""
        event = Event(
            event_type=EventType.MISSION_CREATED,
            mission_id="mission-001",
            agent_id="architect",
            correlation_id="corr-001"
        )

        event_id = bus.publish(event)
        retrieved = bus.store.get_event(event_id)

        assert retrieved is not None
        assert retrieved.mission_id == "mission-001"
        assert retrieved.event_type == EventType.MISSION_CREATED

    def test_get_pending_events(self, bus):
        """Test retrieving pending events"""
        for i in range(3):
            event = Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                agent_id=f"agent-{i}",
                correlation_id=f"corr-{i}"
            )
            bus.publish(event)

        pending = bus.store.get_pending_events("mission-001", limit=10)
        assert len(pending) == 3

    def test_update_event_status(self, bus):
        """Test updating event status"""
        event = Event(
            event_type=EventType.TASK_COMPLETED,
            mission_id="mission-001",
            agent_id="agent-001",
            correlation_id="corr-001"
        )

        event_id = bus.publish(event)
        bus.mark_completed(event_id, "agent-001")

        updated = bus.store.get_event(event_id)
        from event_bus import EventStatus
        assert updated.status == EventStatus.COMPLETED


class TestIdempotency:
    """Test duplicate prevention"""

    @pytest.fixture
    def bus(self):
        """Create event bus with temp database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus = EventBus(db_path)
            yield bus

    def test_duplicate_prevention(self, bus):
        """Test that duplicate events are prevented"""
        event = Event(
            event_type=EventType.MISSION_CREATED,
            mission_id="mission-001",
            agent_id="architect",
            correlation_id="corr-001"
        )

        # First publish
        event_id1 = bus.publish(event, idempotency_key="key-001")

        # Second publish with same key
        event_id2 = bus.publish(event, idempotency_key="key-001")

        assert event_id1 == event_id2


class TestAuditTrail:
    """Test JSONL audit logging"""

    def test_audit_log_created(self):
        """Test that audit log is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            audit_path = os.path.join(tmpdir, "audit.jsonl")

            bus = EventBus(db_path)
            bus.audit_logger.log_path = audit_path

            event = Event(
                event_type=EventType.MISSION_CREATED,
                mission_id="mission-001",
                agent_id="architect",
                correlation_id="corr-001"
            )

            bus.audit_logger.log_event(event, "PUBLISHED")

            assert os.path.exists(audit_path)
            with open(audit_path) as f:
                lines = f.readlines()
                assert len(lines) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
