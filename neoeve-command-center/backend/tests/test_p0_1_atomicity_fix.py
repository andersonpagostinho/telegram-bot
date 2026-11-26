"""
Tests for P0.1: Transactional Atomicity Fix

Validates that P0.1 implementation maintains ACID properties:
- Atomicity: All projections commit together or rollback together
- Idempotency: Same event processed twice = one record
- Multi-tenant: Tenant A events isolated from Tenant B
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from event_bus.event import Event, EventType, EventStatus
from database.models import AgentEvent, WebSocketEventLog, Mission, ProcessedEvent
from app.services.websocket_event_log_service import WebSocketEventLogService
from workers.projection_worker import ProjectionWorker


class TestAtomicityFix:
    """Test transactional atomicity of P0.1 implementation."""

    @pytest.fixture
    def test_mission(self, db_session):
        """Create test mission."""
        mission = Mission(
            mission_id="atomicity_test_mission",
            project_id="atomicity_test_project",
            tenant_id="atomicity_test_tenant",
            name="Atomicity Test Mission",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(mission)
        db_session.commit()
        return mission

    @pytest.fixture
    def test_event(self, test_mission):
        """Create test event."""
        return Event(
            event_id="evt_atomicity_001",
            event_type=EventType.MISSION_STARTED,
            schema_version=1,
            mission_id=test_mission.mission_id,
            tenant_id=test_mission.tenant_id,
            project_id=test_mission.project_id,
            actor_id="actor_test",
            agent_id="architect",
            agent_role="ARCHITECT",
            payload={"mission_id": test_mission.mission_id, "status": "RUNNING"},
            status=EventStatus.PENDING,
            timestamp=datetime.now(timezone.utc).isoformat(),
            idempotency_key="idem_atomicity_001",
        )

    # TEST A: Success Case — Both projections persist
    def test_atomicity_success_both_projections(self, db_session, test_event, test_mission):
        """
        GIVEN projection worker processes an event
        WHEN both AgentEvent and WebSocketEventLog are projected
        THEN both should be persisted in SAME transaction
        """
        from workers.projection_worker import ProjectionWorker
        from unittest.mock import Mock

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="atomicity_consumer",
        )

        # Verify counts before
        agent_count_before = db_session.query(AgentEvent).count()
        ws_count_before = db_session.query(WebSocketEventLog).count()

        # Project event
        result = worker._project_event(test_event)
        assert result is True

        # Verify both projections exist
        agent_event = db_session.query(AgentEvent).filter_by(
            event_id=test_event.event_id
        ).first()
        assert agent_event is not None

        ws_event = db_session.query(WebSocketEventLog).filter_by(
            event_id=test_event.event_id
        ).first()
        assert ws_event is not None

        # Verify counts increased by 1 each
        assert db_session.query(AgentEvent).count() == agent_count_before + 1
        assert db_session.query(WebSocketEventLog).count() == ws_count_before + 1

    # TEST B: Idempotency — No duplicates on reprocessing
    def test_atomicity_idempotent_no_duplicates(self, db_session, test_event, test_mission):
        """
        GIVEN event already processed
        WHEN same event is processed again
        THEN no duplicate records should be created
        """
        from workers.projection_worker import ProjectionWorker
        from unittest.mock import Mock

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="atomicity_consumer",
        )

        # First projection
        result1 = worker._project_event(test_event)
        assert result1 is True

        # Count records
        agent_count_1 = db_session.query(AgentEvent).filter_by(
            event_id=test_event.event_id
        ).count()
        ws_count_1 = db_session.query(WebSocketEventLog).filter_by(
            event_id=test_event.event_id
        ).count()

        assert agent_count_1 == 1
        assert ws_count_1 == 1

        # Second projection (idempotent retry)
        result2 = worker._project_event(test_event)
        assert result2 is True

        # Count should not increase
        agent_count_2 = db_session.query(AgentEvent).filter_by(
            event_id=test_event.event_id
        ).count()
        ws_count_2 = db_session.query(WebSocketEventLog).filter_by(
            event_id=test_event.event_id
        ).count()

        assert agent_count_2 == 1  # Still 1, not 2
        assert ws_count_2 == 1  # Still 1, not 2

    # TEST C: Failure during WebSocketEventLog — Rollback both
    def test_atomicity_failure_websocket_rollback_both(self, db_session, test_event, test_mission):
        """
        GIVEN projection worker encounters IntegrityError in WebSocketEventLog
        WHEN both projections are part of same transaction
        THEN entire transaction should be rolled back
        """
        from workers.projection_worker import ProjectionWorker
        from unittest.mock import Mock

        # Pre-create WebSocketEventLog with same event_id to cause UNIQUE violation
        ws_duplicate = WebSocketEventLog(
            event_id=test_event.event_id,
            event_type="DUMMY",
            tenant_id=test_mission.tenant_id,
            project_id=test_mission.project_id,
            payload={"dummy": True},
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(ws_duplicate)
        db_session.commit()

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="atomicity_consumer",
        )

        # Count before
        agent_count_before = db_session.query(AgentEvent).count()
        ws_count_before = db_session.query(WebSocketEventLog).count()

        # Attempt projection (should fail on WebSocketEventLog UNIQUE)
        with pytest.raises(IntegrityError):
            worker._project_event(test_event)

        # Rollback happened automatically due to exception
        db_session.rollback()

        # Verify AgentEvent was NOT created (transaction rolled back)
        agent_event = db_session.query(AgentEvent).filter_by(
            event_id=test_event.event_id
        ).first()
        assert agent_event is None

        # Verify no new records were added
        assert db_session.query(AgentEvent).count() == agent_count_before
        assert db_session.query(WebSocketEventLog).count() == ws_count_before

    # TEST D: Flush vs Commit — Transactional Control
    def test_transactional_flush_no_premature_commit(self, db_session, test_mission):
        """
        GIVEN WebSocketEventLogService.log_event() uses flush() not commit()
        WHEN multiple events are added to session
        THEN no commits should happen until outer transaction commits
        """
        ws_service = WebSocketEventLogService()

        # Add events without committing
        seq1 = ws_service.log_event(
            db=db_session,
            event_id="evt_flush_001",
            event_type="TEST_EVENT",
            tenant_id=test_mission.tenant_id,
            project_id=test_mission.project_id,
            payload={"test": 1},
        )
        assert seq1 is not None

        seq2 = ws_service.log_event(
            db=db_session,
            event_id="evt_flush_002",
            event_type="TEST_EVENT",
            tenant_id=test_mission.tenant_id,
            project_id=test_mission.project_id,
            payload={"test": 2},
        )
        assert seq2 is not None

        # Verify sequence numbers are auto-incremented
        assert seq2 > seq1

        # At this point, records are in session but not committed
        # Verify they exist in session
        in_session_1 = db_session.query(WebSocketEventLog).filter_by(
            event_id="evt_flush_001"
        ).first()
        assert in_session_1 is not None

        # Now commit
        db_session.commit()

        # After commit, verify persistence
        persisted_1 = db_session.query(WebSocketEventLog).filter_by(
            event_id="evt_flush_001"
        ).first()
        assert persisted_1 is not None

        persisted_2 = db_session.query(WebSocketEventLog).filter_by(
            event_id="evt_flush_002"
        ).first()
        assert persisted_2 is not None

    # TEST E: Multi-tenant Isolation Maintained
    def test_atomicity_multi_tenant_isolation(self, db_session):
        """
        GIVEN events from different tenants
        WHEN both are projected
        THEN isolation should be maintained (not mixed)
        """
        # Create missions for 2 tenants
        mission_a = Mission(
            mission_id="mission_tenant_a",
            project_id="project_a",
            tenant_id="tenant_a_isolated",
            name="Mission A",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        mission_b = Mission(
            mission_id="mission_tenant_b",
            project_id="project_b",
            tenant_id="tenant_b_isolated",
            name="Mission B",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(mission_a)
        db_session.add(mission_b)
        db_session.commit()

        from workers.projection_worker import ProjectionWorker
        from unittest.mock import Mock

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="atomicity_consumer",
        )

        # Create events for both tenants
        event_a = Event(
            event_id="evt_tenant_a",
            event_type=EventType.MISSION_STARTED,
            schema_version=1,
            mission_id=mission_a.mission_id,
            tenant_id="tenant_a_isolated",
            project_id="project_a",
            actor_id="actor_a",
            agent_id="architect",
            agent_role="ARCHITECT",
            payload={"mission_id": mission_a.mission_id},
            status=EventStatus.PENDING,
            timestamp=datetime.now(timezone.utc).isoformat(),
            idempotency_key="idem_a",
        )

        event_b = Event(
            event_id="evt_tenant_b",
            event_type=EventType.MISSION_STARTED,
            schema_version=1,
            mission_id=mission_b.mission_id,
            tenant_id="tenant_b_isolated",
            project_id="project_b",
            actor_id="actor_b",
            agent_id="architect",
            agent_role="ARCHITECT",
            payload={"mission_id": mission_b.mission_id},
            status=EventStatus.PENDING,
            timestamp=datetime.now(timezone.utc).isoformat(),
            idempotency_key="idem_b",
        )

        # Project both
        worker._project_event(event_a)
        worker._project_event(event_b)
        db_session.commit()

        # Verify isolation: Tenant A sees only A
        ws_events_a = db_session.query(WebSocketEventLog).filter_by(
            tenant_id="tenant_a_isolated"
        ).all()
        assert len(ws_events_a) == 1
        assert ws_events_a[0].event_id == "evt_tenant_a"

        # Verify isolation: Tenant B sees only B
        ws_events_b = db_session.query(WebSocketEventLog).filter_by(
            tenant_id="tenant_b_isolated"
        ).all()
        assert len(ws_events_b) == 1
        assert ws_events_b[0].event_id == "evt_tenant_b"
