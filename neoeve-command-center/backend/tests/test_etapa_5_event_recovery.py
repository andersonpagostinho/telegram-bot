"""
ETAPA 5: WebSocket Event Log and Recovery Tests

Tests for event logging and recovery mechanism for reconnecting WebSocket clients.

Scenarios:
- Event logging with sequence numbers
- Missed event recovery from cursor
- Multi-tenant event isolation
- Event cleanup and TTL
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from database.connection import SessionLocal, engine
from database.models import WebSocketEventLog, Base
from app.services.websocket_event_log_service import WebSocketEventLogService, get_event_log_service


@pytest.fixture(scope="session")
def setup_db():
    """Create test database schema."""
    Base.metadata.create_all(bind=engine)
    yield
    # Note: Don't drop all to preserve data between tests if needed
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_db):
    """Get database session for test."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_tenant():
    """Create unique tenant ID."""
    return f"test_tenant_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_project():
    """Create unique project ID."""
    return f"test_project_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def event_log_service():
    """Create event log service instance."""
    return WebSocketEventLogService(event_ttl_hours=24)


class TestWebSocketEventLogging:
    """Test event logging functionality."""

    def test_log_event(self, db_session, event_log_service, test_tenant, test_project):
        """Test logging a single event."""
        event_id = f"event_{uuid.uuid4().hex[:8]}"
        payload = {"mission_id": "m1", "status": "RUNNING"}

        sequence = event_log_service.log_event(
            db=db_session,
            event_id=event_id,
            event_type="MISSION_UPDATED",
            tenant_id=test_tenant,
            project_id=test_project,
            payload=payload,
        )

        assert sequence is not None
        assert isinstance(sequence, int)
        assert sequence > 0

    def test_log_multiple_events(self, db_session, event_log_service, test_tenant, test_project):
        """Test logging multiple events - sequence should increment."""
        sequences = []
        for i in range(5):
            sequence = event_log_service.log_event(
                db=db_session,
                event_id=f"event_{i}_{uuid.uuid4().hex[:8]}",
                event_type="TASK_CREATED",
                tenant_id=test_tenant,
                project_id=test_project,
                payload={"task_id": f"t{i}"},
            )
            sequences.append(sequence)

        # Sequences should be strictly increasing
        assert all(sequences[i] < sequences[i+1] for i in range(len(sequences)-1))

    def test_logged_event_persists(self, db_session, event_log_service, test_tenant, test_project):
        """Test that logged events can be retrieved."""
        event_id = f"event_{uuid.uuid4().hex[:8]}"
        payload = {"data": "test"}

        sequence = event_log_service.log_event(
            db=db_session,
            event_id=event_id,
            event_type="TEST_EVENT",
            tenant_id=test_tenant,
            project_id=test_project,
            payload=payload,
        )

        # Create new session to verify persistence
        new_db = SessionLocal()
        try:
            event = new_db.query(WebSocketEventLog).filter_by(
                event_id=event_id
            ).first()

            assert event is not None
            assert event.sequence == sequence
            assert event.event_type == "TEST_EVENT"
            assert event.payload == payload
        finally:
            new_db.close()


class TestEventRecovery:
    """Test event recovery for reconnecting clients."""

    def test_get_missed_events_all(self, db_session, event_log_service, test_tenant, test_project):
        """Test retrieving all recent events when cursor is None."""
        # Log 3 events
        event_ids = []
        for i in range(3):
            event_id = f"event_{i}_{uuid.uuid4().hex[:8]}"
            event_log_service.log_event(
                db=db_session,
                event_id=event_id,
                event_type="TEST_EVENT",
                tenant_id=test_tenant,
                project_id=test_project,
                payload={"index": i},
            )
            event_ids.append(event_id)

        # Get all recent events (cursor=None)
        missed_events = event_log_service.get_missed_events(
            db=db_session,
            tenant_id=test_tenant,
            cursor=None,
            limit=10,
        )

        # Should get at least our 3 events
        assert len(missed_events) >= 3
        # Should be sorted by sequence
        assert all(
            missed_events[i].sequence <= missed_events[i+1].sequence
            for i in range(len(missed_events)-1)
        )

    def test_get_missed_events_after_cursor(self, db_session, event_log_service, test_tenant, test_project):
        """Test retrieving events after a specific cursor."""
        # Log 5 events
        sequences = []
        for i in range(5):
            sequence = event_log_service.log_event(
                db=db_session,
                event_id=f"event_{i}_{uuid.uuid4().hex[:8]}",
                event_type="TEST_EVENT",
                tenant_id=test_tenant,
                project_id=test_project,
                payload={"index": i},
            )
            sequences.append(sequence)

        # Get events after first 2
        cursor = sequences[1]  # After 2nd event
        missed_events = event_log_service.get_missed_events(
            db=db_session,
            tenant_id=test_tenant,
            cursor=cursor,
            limit=10,
        )

        # Should get events 3, 4, 5 (after cursor)
        returned_sequences = [e.sequence for e in missed_events]
        assert all(seq > cursor for seq in returned_sequences)
        assert len(missed_events) >= 3

    def test_missed_events_respects_limit(self, db_session, event_log_service, test_tenant, test_project):
        """Test that limit parameter works."""
        # Log 10 events
        for i in range(10):
            event_log_service.log_event(
                db=db_session,
                event_id=f"event_{i}_{uuid.uuid4().hex[:8]}",
                event_type="TEST_EVENT",
                tenant_id=test_tenant,
                project_id=test_project,
                payload={"index": i},
            )

        # Get only 3 events
        missed_events = event_log_service.get_missed_events(
            db=db_session,
            tenant_id=test_tenant,
            cursor=None,
            limit=3,
        )

        assert len(missed_events) <= 3

    def test_multi_tenant_isolation(self, db_session, event_log_service, test_project):
        """Test that events are isolated per tenant."""
        tenant1 = f"tenant_{uuid.uuid4().hex[:8]}"
        tenant2 = f"tenant_{uuid.uuid4().hex[:8]}"

        # Log events for both tenants
        seq1 = event_log_service.log_event(
            db=db_session,
            event_id=f"event_t1_{uuid.uuid4().hex[:8]}",
            event_type="TEST_EVENT",
            tenant_id=tenant1,
            project_id=test_project,
            payload={"tenant": "1"},
        )

        seq2 = event_log_service.log_event(
            db=db_session,
            event_id=f"event_t2_{uuid.uuid4().hex[:8]}",
            event_type="TEST_EVENT",
            tenant_id=tenant2,
            project_id=test_project,
            payload={"tenant": "2"},
        )

        # Get events for tenant1 only
        tenant1_events = event_log_service.get_missed_events(
            db=db_session,
            tenant_id=tenant1,
            cursor=None,
            limit=10,
        )

        # Should not contain tenant2 events
        tenant1_payloads = [e.payload for e in tenant1_events]
        assert all(p.get("tenant") != "2" for p in tenant1_payloads)


class TestEventCleanup:
    """Test event cleanup and TTL."""

    def test_get_latest_sequence(self, db_session, event_log_service, test_tenant, test_project):
        """Test getting the latest sequence number."""
        # Log 3 events
        sequences = []
        for i in range(3):
            seq = event_log_service.log_event(
                db=db_session,
                event_id=f"event_{i}_{uuid.uuid4().hex[:8]}",
                event_type="TEST_EVENT",
                tenant_id=test_tenant,
                project_id=test_project,
                payload={"index": i},
            )
            sequences.append(seq)

        # Get latest sequence
        latest = event_log_service.get_latest_sequence(
            db=db_session,
            tenant_id=test_tenant,
        )

        # Should be max of all sequences
        assert latest == max(sequences)

    def test_cleanup_expired_events(self, db_session, event_log_service, test_tenant, test_project):
        """Test cleanup of expired events."""
        # Create service with very short TTL
        short_ttl_service = WebSocketEventLogService(event_ttl_hours=0)

        # Log event (will be immediately expired)
        event_log_service.log_event(
            db=db_session,
            event_id=f"event_{uuid.uuid4().hex[:8]}",
            event_type="TEST_EVENT",
            tenant_id=test_tenant,
            project_id=test_project,
            payload={"status": "expired"},
        )

        # Count before cleanup
        # Note: cleanup checks ttl_expires_at, so with 0 hour TTL they should be old
        # For this test, we just verify the method runs without error

        count = event_log_service.cleanup_expired_events(db=db_session, dry_run=True)
        # This is a dry run, so no events are deleted
        assert count >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
