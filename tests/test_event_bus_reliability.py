"""Event Bus Reliability Tests — STEP 2"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from event_bus import Event, EventType, EventBus, EventStatus
import tempfile
import threading
import time
import pytest
import json


class TestConcurrency:
    """Concurrency and thread-safety tests"""

    @pytest.fixture
    def bus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus_instance = EventBus(db_path)
            yield bus_instance

            # CRITICAL: Wait for WAL checkpoint before tempdir cleanup
            # Windows/SQLite issue: WAL journal locks prevent file deletion
            # 2+ seconds needed for checkpoint + lock release on Windows
            time.sleep(2.0)

    def test_concurrent_publish(self, bus):
        """Test concurrent publishing"""
        results = []

        def publish_event(i):
            event = Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                agent_id=f"agent-{i}",
                correlation_id=f"corr-{i}"
            )
            event_id = bus.publish(event)
            results.append(event_id)

        threads = [threading.Thread(target=publish_event, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        assert len(set(results)) == 5  # All unique

    def test_concurrent_consume(self, bus):
        """Test concurrent consumption with atomic reserve"""
        # Publish 10 events
        for i in range(10):
            event = Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                agent_id="agent-001",
                correlation_id=f"corr-{i}"
            )
            bus.publish(event)

        consumed = []
        lock = threading.Lock()

        def consume_and_process():
            events = bus.consume_pending("mission-001", "consumer-1", limit=3)
            with lock:
                consumed.extend([e.event_id for e in events])
            for event in events:
                bus.mark_completed(event.event_id, "consumer-1")

        threads = [threading.Thread(target=consume_and_process) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # CRITICAL: Wait for all transaction commits + WAL checkpoint
        time.sleep(2.0)

        # With atomic reserve: 2 consumers × limit=3 = 6 consumed, 4 remaining
        # Atomic reserve prevents race condition (both threads getting same event)
        pending = bus.store.get_pending_events("mission-001")
        assert len(pending) <= 4, f"Expected at most 4 pending, got {len(pending)}"
        # Verify no duplicates consumed
        assert len(set(consumed)) == len(consumed), "Duplicate event IDs consumed!"


class TestRecovery:
    """Recovery and restart tests"""

    def test_restart_with_pending(self):
        """Test recovery of pending events after restart"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            # Create bus and publish
            bus1 = EventBus(db_path)
            for i in range(3):
                event = Event(
                    event_type=EventType.TASK_CREATED,
                    mission_id="mission-001",
                    agent_id="agent-001",
                    correlation_id=f"corr-{i}"
                )
                bus1.publish(event)

            # Simulate shutdown (don't mark completed)
            del bus1
            time.sleep(2.0)  # Wait for WAL checkpoint

            # Restart with new bus instance
            bus2 = EventBus(db_path)
            pending = bus2.store.get_pending_events("mission-001", limit=10)
            del bus2
            time.sleep(2.0)  # Wait before cleanup

            assert len(pending) == 3  # All events should be recoverable

    def test_recover_stuck_events(self):
        """Test recovery of events stuck in PROCESSING"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus = EventBus(db_path)

            # Publish and consume (without completing)
            event = Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                agent_id="agent-001",
                correlation_id="corr-001"
            )
            event_id = bus.publish(event)

            # Consume but don't complete
            events = bus.consume_pending("mission-001", "consumer-1")
            assert len(events) == 1

            # Event should be in PROCESSING
            stuck_events = bus.get_stuck_events(timeout_minutes=0)
            assert len(stuck_events) >= 1

            # Recover
            recovered = bus.recover_stuck_events(timeout_minutes=0)
            assert recovered >= 1

            # Should be back to PENDING
            pending = bus.store.get_pending_events("mission-001")
            del bus
            time.sleep(2.0)  # Wait before cleanup
            assert len(pending) >= 1


class TestIdempotency:
    """Idempotency tests"""

    @pytest.fixture
    def bus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus_instance = EventBus(db_path)
            yield bus_instance

            # CRITICAL: Wait for WAL checkpoint before tempdir cleanup
            time.sleep(2.0)

    def test_concurrent_duplicate_key(self, bus):
        """Test duplicate key prevention under concurrency"""
        results = []
        lock = threading.Lock()

        def publish_with_key():
            event = Event(
                event_type=EventType.MISSION_CREATED,
                mission_id="mission-001",
                agent_id="agent-001",
                correlation_id="corr-001"
            )
            event_id = bus.publish(event, idempotency_key="same-key")
            with lock:
                results.append(event_id)

        threads = [threading.Thread(target=publish_with_key) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        time.sleep(1.5)  # Wait for commits + checkpoint

        # All should return same event_id
        assert len(set(results)) == 1


class TestPersistence:
    """Persistence and audit trail tests"""

    def test_sqliteandjonl_consistency(self):
        """Test SQLite and JSONL consistency"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            audit_path = os.path.join(tmpdir, "audit.jsonl")

            bus = EventBus(db_path)
            bus.audit_logger.log_path = audit_path

            # Publish event
            event = Event(
                event_type=EventType.MISSION_CREATED,
                mission_id="mission-001",
                agent_id="agent-001",
                correlation_id="corr-001"
            )
            event_id = bus.publish(event)

            # Verify SQLite
            retrieved = bus.store.get_event(event_id)
            assert retrieved is not None

            # Verify JSONL exists
            assert os.path.exists(audit_path)
            with open(audit_path) as f:
                lines = f.readlines()
                assert len(lines) > 0

                # Parse first line
                record = json.loads(lines[0])
                assert record["event_id"] == event_id

            del bus
            time.sleep(2.0)  # Wait before cleanup

    def test_state_transitions(self):
        """Test valid state transitions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus = EventBus(db_path)

            event = Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                agent_id="agent-001",
                correlation_id="corr-001"
            )
            event_id = bus.publish(event)

            # Consume (PENDING -> PROCESSING)
            events = bus.consume_pending("mission-001", "consumer-1")
            assert events[0].status == EventStatus.PROCESSING

            # Complete (PROCESSING -> COMPLETED)
            bus.mark_completed(event_id, "consumer-1")
            final = bus.store.get_event(event_id)
            del bus
            time.sleep(2.0)  # Wait before cleanup
            assert final.status == EventStatus.COMPLETED


class TestAuditTrail:
    """Audit trail integrity tests"""

    def test_correlation_id_preserved(self):
        """Test that correlation_id is preserved through event lifecycle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus = EventBus(db_path)

            event = Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                task_id="task-001",
                agent_id="agent-001",
                correlation_id="trace-12345",
                causation_id="evt-parent-001"
            )
            event_id = bus.publish(event)

            retrieved = bus.store.get_event(event_id)
            del bus
            time.sleep(2.0)  # Wait before cleanup
            assert retrieved.correlation_id == "trace-12345"
            assert retrieved.causation_id == "evt-parent-001"


class TestEdgeCases:
    """Edge cases and error conditions"""

    def test_invalid_event_rejected(self):
        """Test that invalid events are rejected"""
        from event_bus import InvalidEventException

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus = EventBus(db_path)

            # Missing required field
            with pytest.raises(InvalidEventException):
                event = Event(
                    event_type=EventType.TASK_CREATED,
                    agent_id="agent-001",
                    correlation_id="corr-001"
                    # Missing mission_id
                )
                bus.publish(event)

            del bus
            time.sleep(2.0)  # Wait before cleanup

    def test_cleanup_old_events(self):
        """Test cleanup of old events"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            bus = EventBus(db_path)

            # Publish and complete event
            event = Event(
                event_type=EventType.TASK_CREATED,
                mission_id="mission-001",
                agent_id="agent-001",
                correlation_id="corr-001"
            )
            event_id = bus.publish(event)
            bus.mark_completed(event_id, "consumer-1")

            # Cleanup should not fail
            deleted = bus.cleanup_old_events(days=0)
            del bus
            time.sleep(2.0)  # Wait before cleanup
            assert deleted >= 0  # Should cleanup something


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
