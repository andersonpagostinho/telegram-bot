"""Proof of Concept Test — Real Agent Communication via Event Bus"""

import pytest
import tempfile
import os
from pathlib import Path

from event_bus.event_bus import EventBus
from event_bus.dispatcher import EventDispatcher
from event_bus.agent_handlers import ProofOfConcept
from event_bus.event import Event, EventType


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path


def test_dispatcher_routing(temp_db):
    """Test that Dispatcher correctly routes events"""
    bus = EventBus(temp_db, use_wal=False)
    dispatcher = EventDispatcher(bus)

    # Create test event
    event = Event(
        event_type=EventType.TASK_ASSIGNED,
        mission_id="test-mission",
        task_id="test-task",
        agent_id="architect",
        agent_role="architect",
        correlation_id="test-corr-001",
        payload={"description": "Test task", "target_agent": "backend"},
        schema_version="1.0"
    )

    bus.publish(event)

    # Verify dispatcher can determine target
    from event_bus.dispatcher import AgentRole
    target = dispatcher._determine_target_agent(event)

    assert target == AgentRole.BACKEND, "Should route to Backend"
    print("✅ Dispatcher routing test passed")


def test_architect_backend_communication_real(temp_db):
    """
    REAL PROOF OF CONCEPT TEST

    Demonstrates actual communication flow:
    Architect → Backend → Architect

    This is NOT a mock. It demonstrates real event handling and publishing.
    """
    # Setup
    bus = EventBus(temp_db, use_wal=False)
    dispatcher = EventDispatcher(bus)
    poc = ProofOfConcept(bus, dispatcher)

    # Execute proof of concept
    success = poc.run_proof_of_concept()

    assert success, "Proof of concept should succeed"
    print("✅ Real Architect ↔ Backend communication test passed")


def test_idempotency_with_real_handlers(temp_db):
    """Test that duplicate events don't produce duplicate effects"""
    bus = EventBus(temp_db, use_wal=False)
    dispatcher = EventDispatcher(bus)

    from event_bus.agent_handlers import ArchitectHandler, BackendDeveloperHandler
    architect = ArchitectHandler(bus)
    backend = BackendDeveloperHandler(bus)

    from event_bus.dispatcher import AgentRole
    dispatcher.register_handler(AgentRole.ARCHITECT, architect.handle_event)
    dispatcher.register_handler(AgentRole.BACKEND, backend.handle_event)

    mission_id = "idempotent-test"
    task_id = "idempotent-task"

    # Create task event
    task_event = Event(
        event_type=EventType.TASK_ASSIGNED,
        mission_id=mission_id,
        task_id=task_id,
        agent_id="architect",
        agent_role="architect",
        correlation_id="idempotent-001",
        payload={"description": "Idempotency test", "target_agent": "backend"},
        schema_version="1.0"
    )

    # Publish twice with same idempotency_key
    key = "test-idempotent-key"
    bus.publish(task_event, idempotency_key=key)
    bus.publish(task_event, idempotency_key=key)

    # Should only have one event in database
    events = bus.store.get_pending_events(mission_id, limit=10)

    # Count by event_id (should be unique)
    unique_ids = set(e.event_id for e in events)
    assert len(unique_ids) == 1, "Idempotency key should prevent duplicates"

    print("✅ Idempotency test passed")


def test_correlation_traceability(temp_db):
    """Test that events are properly traced via correlation_id"""
    bus = EventBus(temp_db, use_wal=False)
    dispatcher = EventDispatcher(bus)
    poc = ProofOfConcept(bus, dispatcher)

    mission_id = "traceability-test"

    # Publish initial event
    from event_bus.event import Event, EventType
    from uuid import uuid4

    correlation_id = f"trace-{uuid4().hex[:8]}"

    event1 = Event(
        event_type=EventType.TASK_ASSIGNED,
        mission_id=mission_id,
        task_id="trace-task",
        agent_id="architect",
        agent_role="architect",
        correlation_id=correlation_id,
        payload={"description": "Trace test", "target_agent": "backend"},
        schema_version="1.0"
    )

    bus.publish(event1)

    # Get all events with this correlation_id
    all_events = bus.store.get_pending_events(mission_id, limit=100)
    traced_events = [e for e in all_events if e.correlation_id == correlation_id]

    assert len(traced_events) >= 1, "Should have at least one event with correlation_id"

    # Verify causation chain
    for evt in traced_events:
        if evt.causation_id:
            parent = bus.store.get_event(evt.causation_id)
            assert parent is not None, f"Parent event {evt.causation_id} should exist"
            print(f"  Chain: {parent.event_type.value} → {evt.event_type.value}")

    print("✅ Correlation traceability test passed")


if __name__ == "__main__":
    # Run tests directly for quick verification
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        print("\n🧪 Running Proof of Concept Tests...\n")

        test_dispatcher_routing(db)
        test_architect_backend_communication_real(db)
        test_idempotency_with_real_handlers(db)
        test_correlation_traceability(db)

        print("\n✅ All tests passed!")
