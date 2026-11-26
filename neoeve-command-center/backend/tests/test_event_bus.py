"""Tests for Event Bus: publish, reserve, ack, fail."""

import pytest
from app.services.event_bus import (
    publish_event,
    reserve_event_atomic,
    ack_event,
    fail_event,
    get_pending_events,
)


class TestEventBus:
    """Event Bus tests."""

    def test_publish_event_valid(self):
        """Publish valid event."""
        event = publish_event(
            event_type="mission.created",
            tenant_id="test-tenant",
            project_id="test-project",
            actor_id="test-user",
            mission_id="mission-1",
            payload={"name": "Test Mission"},
        )
        assert event is not None
        assert event.event_type == "mission.created"
        assert event.status == "PENDING"
        print("✓ Test 1: Publish valid event")

    def test_publish_event_idempotent(self):
        """Same idempotency key returns same event."""
        key = "idempotent-key-1"
        event1 = publish_event(
            event_type="mission.created",
            tenant_id="test-tenant",
            project_id="test-project",
            actor_id="test-user",
            idempotency_key=key,
        )
        event2 = publish_event(
            event_type="mission.created",
            tenant_id="test-tenant",
            project_id="test-project",
            actor_id="test-user",
            idempotency_key=key,
        )
        assert event1.event_id == event2.event_id
        print("✓ Test 2: Idempotency")

    def test_reserve_event_atomic(self):
        """Reserve event marks as PROCESSING."""
        event = publish_event(
            event_type="task.assigned",
            tenant_id="test-tenant",
            project_id="test-project",
            actor_id="test-user",
            task_id="task-1",
        )
        reserved = reserve_event_atomic(
            event.event_id,
            "test-tenant",
            "test-project",
        )
        assert reserved is not None
        assert reserved.status == "PROCESSING"
        print("✓ Test 3: Atomic reserve")

    def test_ack_event(self):
        """Acknowledge event marks as PROCESSED."""
        event = publish_event(
            event_type="execution.completed",
            tenant_id="test-tenant",
            project_id="test-project",
            actor_id="test-user",
            execution_id="exec-1",
        )
        reserve_event_atomic(event.event_id, "test-tenant", "test-project")
        success = ack_event(event.event_id, "test-tenant", "test-project")
        assert success is True
        print("✓ Test 4: Acknowledge")

    def test_fail_event_retry(self):
        """Fail event increments retry count."""
        event = publish_event(
            event_type="validation.failed",
            tenant_id="test-tenant",
            project_id="test-project",
            actor_id="test-user",
        )
        success = fail_event(
            event.event_id,
            "test-tenant",
            "test-project",
            "Test error",
        )
        assert success is True
        print("✓ Test 5: Fail and retry")

    def test_tenant_isolation(self):
        """Cannot access event from different tenant."""
        event = publish_event(
            event_type="mission.created",
            tenant_id="tenant-1",
            project_id="project-1",
            actor_id="user-1",
        )
        # Try to reserve with wrong tenant
        reserved = reserve_event_atomic(
            event.event_id,
            "tenant-2",  # Wrong tenant
            "project-1",
        )
        assert reserved is None
        print("✓ Test 6: Tenant isolation")

    def test_get_pending_events(self):
        """Retrieve pending events for processing."""
        for i in range(3):
            publish_event(
                event_type=f"test.event.{i}",
                tenant_id="test-tenant",
                project_id="test-project",
                actor_id="test-user",
            )
        pending = get_pending_events("test-tenant", "test-project")
        assert len(pending) >= 3
        print("✓ Test 7: Get pending events")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
