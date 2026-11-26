"""
Tests for P0.1: Activity Stream Integration

Validates that events are projected to both AgentEvent and WebSocketEventLog.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy.orm import Session
from event_bus.event import Event, EventType, EventStatus
from database.models import AgentEvent, WebSocketEventLog, Mission
from app.services.websocket_event_log_service import WebSocketEventLogService


class TestActivityStreamIntegration:
    """Test Activity Stream (WebSocketEventLog) integration with ProjectionWorker."""

    @pytest.fixture
    def test_mission(self, db_session):
        """Create test mission."""
        mission = Mission(
            mission_id="test_mission_001",
            project_id="test_project_001",
            tenant_id="test_tenant_001",
            name="Test Mission",
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
            event_id="evt_001",
            event_type=EventType.MISSION_STARTED,
            schema_version=1,
            mission_id=test_mission.mission_id,
            task_id=None,
            execution_id=None,
            correlation_id="corr_001",
            causation_id="caus_001",
            tenant_id=test_mission.tenant_id,
            project_id=test_mission.project_id,
            actor_id="actor_001",
            agent_id="architect",
            agent_role="ARCHITECT",
            payload={"mission_id": test_mission.mission_id, "status": "RUNNING"},
            status=EventStatus.PENDING,
            timestamp=datetime.now(timezone.utc).isoformat(),
            idempotency_key="idem_001",
        )

    def test_event_projected_to_agent_event(self, db_session, test_event, test_mission):
        """
        GIVEN an event from Event Bus
        WHEN ProjectionWorker projects it
        THEN event should be in AgentEvent table
        """
        from workers.projection_worker import ProjectionWorker

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="test_consumer",
        )

        # Act
        result = worker._project_event(test_event)

        # Assert
        assert result is True

        agent_event = db_session.query(AgentEvent).filter_by(
            event_id=test_event.event_id
        ).first()
        assert agent_event is not None
        assert agent_event.event_type == "MISSION_STARTED"
        assert agent_event.tenant_id == test_mission.tenant_id
        assert agent_event.project_id == test_mission.project_id

    def test_event_projected_to_websocket_log(self, db_session, test_event, test_mission):
        """
        GIVEN an event from Event Bus
        WHEN ProjectionWorker projects it
        THEN event should ALSO be in WebSocketEventLog table
        """
        from workers.projection_worker import ProjectionWorker

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="test_consumer",
        )

        # Act
        result = worker._project_event(test_event)

        # Assert
        assert result is True

        ws_event = db_session.query(WebSocketEventLog).filter_by(
            event_id=test_event.event_id
        ).first()
        assert ws_event is not None
        assert ws_event.event_type == "MISSION_STARTED"
        assert ws_event.tenant_id == test_mission.tenant_id
        assert ws_event.project_id == test_mission.project_id
        assert ws_event.payload is not None

    def test_event_projected_idempotent(self, db_session, test_event, test_mission):
        """
        GIVEN an event already projected
        WHEN ProjectionWorker projects it again
        THEN WebSocketEventLog should NOT have duplicates
        """
        from workers.projection_worker import ProjectionWorker

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="test_consumer",
        )

        # First projection
        result1 = worker._project_event(test_event)
        assert result1 is True

        ws_count_1 = db_session.query(WebSocketEventLog).filter_by(
            event_id=test_event.event_id
        ).count()
        assert ws_count_1 == 1

        # Second projection (simulating retry)
        result2 = worker._project_event(test_event)
        assert result2 is True

        ws_count_2 = db_session.query(WebSocketEventLog).filter_by(
            event_id=test_event.event_id
        ).count()
        assert ws_count_2 == 1  # Still 1, not duplicated

    def test_websocket_log_multi_tenant_isolation(self, db_session):
        """
        GIVEN events from different tenants
        WHEN both are projected
        THEN each tenant should see only their own events
        """
        from workers.projection_worker import ProjectionWorker

        # Create missions for 2 tenants
        mission_a = Mission(
            mission_id="mission_a",
            project_id="project_a",
            tenant_id="tenant_a",
            name="Mission A",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        mission_b = Mission(
            mission_id="mission_b",
            project_id="project_b",
            tenant_id="tenant_b",
            name="Mission B",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(mission_a)
        db_session.add(mission_b)
        db_session.commit()

        # Create events
        event_a = Event(
            event_id="evt_a",
            event_type=EventType.MISSION_STARTED,
            schema_version=1,
            mission_id=mission_a.mission_id,
            tenant_id="tenant_a",
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
            event_id="evt_b",
            event_type=EventType.MISSION_STARTED,
            schema_version=1,
            mission_id=mission_b.mission_id,
            tenant_id="tenant_b",
            project_id="project_b",
            actor_id="actor_b",
            agent_id="architect",
            agent_role="ARCHITECT",
            payload={"mission_id": mission_b.mission_id},
            status=EventStatus.PENDING,
            timestamp=datetime.now(timezone.utc).isoformat(),
            idempotency_key="idem_b",
        )

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="test_consumer",
        )

        # Project both events
        worker._project_event(event_a)
        worker._project_event(event_b)

        # Verify isolation
        ws_events_a = db_session.query(WebSocketEventLog).filter_by(
            tenant_id="tenant_a"
        ).all()
        assert len(ws_events_a) == 1
        assert ws_events_a[0].event_id == "evt_a"

        ws_events_b = db_session.query(WebSocketEventLog).filter_by(
            tenant_id="tenant_b"
        ).all()
        assert len(ws_events_b) == 1
        assert ws_events_b[0].event_id == "evt_b"

    def test_websocket_log_failure_does_not_break_projection(
        self, db_session, test_event, test_mission
    ):
        """
        GIVEN WebSocketEventLogService.log_event() fails
        WHEN ProjectionWorker projects an event
        THEN AgentEvent should still be successfully projected
        """
        from workers.projection_worker import ProjectionWorker

        worker = ProjectionWorker(
            event_store=Mock(),
            db_session=db_session,
            consumer_id="test_consumer",
        )

        # Mock log_event to fail
        with patch.object(
            WebSocketEventLogService, "log_event", side_effect=Exception("DB error")
        ):
            # Act
            result = worker._project_event(test_event)

            # Assert: _project_event should return True despite Activity Stream failure
            assert result is True

            # AgentEvent should still be projected
            agent_event = db_session.query(AgentEvent).filter_by(
                event_id=test_event.event_id
            ).first()
            assert agent_event is not None


class TestActivityStreamAPI:
    """Test Activity Stream API endpoint returns events."""

    def test_get_events_returns_websocket_log_events(self, db_session, client, auth_headers):
        """
        GIVEN events in WebSocketEventLog
        WHEN calling GET /events
        THEN response should include the events
        """
        # Create test mission
        mission = Mission(
            mission_id="test_mission",
            project_id="test_project",
            tenant_id="test_tenant",
            name="Test",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(mission)
        db_session.commit()

        # Create event in WebSocketEventLog
        ws_event = WebSocketEventLog(
            event_id="evt_test",
            event_type="mission.created",
            tenant_id="test_tenant",
            project_id="test_project",
            payload={"mission_id": "test_mission", "name": "Test"},
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(ws_event)
        db_session.commit()

        # Act
        response = client.get("/api/v1/events", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert any(e["event_id"] == "evt_test" for e in data["events"])


class TestActivityStreamIntegrationWithProjectionWorker:
    """Integration tests with full ProjectionWorker."""

    def test_projection_worker_full_cycle(self, db_session, test_mission):
        """
        GIVEN Event Bus with pending events
        WHEN ProjectionWorker consumes and projects
        THEN both AgentEvent and WebSocketEventLog should be populated
        """
        # This test requires full Event Bus setup
        # Marked as integration test
        pytest.skip("Requires full Event Bus mock setup")
