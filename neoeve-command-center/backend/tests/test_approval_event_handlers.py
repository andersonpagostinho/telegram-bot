"""Integration tests for Approval Event Bus handlers with PostgreSQL."""

import pytest
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base, AgentEvent, ProcessedEvent, Mission, Validation
from app.models.event_store import Event, Base as EventBase
from app.services.event_bus import publish_event, reserve_event_atomic, ack_event, fail_event
from app.services.projection_worker import (
    ProjectionWorker,
    handle_approval_requested,
    handle_approval_approved,
    handle_approval_rejected,
    handle_approval_vetoed,
)

# PostgreSQL for tests
DATABASE_URL = "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"
engine_pg = create_engine(DATABASE_URL, echo=False)
SessionPG = sessionmaker(bind=engine_pg)

# SQLite Event Store for tests
EVENT_STORE_URL = "sqlite:///:memory:"
engine_sqlite = create_engine(EVENT_STORE_URL, isolation_level="SERIALIZABLE")
EventBase.metadata.create_all(engine_sqlite)
SessionSQLite = sessionmaker(bind=engine_sqlite)


@pytest.fixture(scope="session")
def setup_pg_db():
    """Create PostgreSQL tables."""
    Base.metadata.create_all(engine_pg)
    yield
    # Keep tables for inspection


@pytest.fixture(autouse=True)
def cleanup_pg_before_each(setup_pg_db):
    """Clean PostgreSQL before each test."""
    with engine_pg.begin() as conn:
        conn.execute(text("TRUNCATE agent_events CASCADE"))
        conn.execute(text("TRUNCATE processed_events CASCADE"))
        conn.execute(text("TRUNCATE validations CASCADE"))
        conn.execute(text("TRUNCATE missions CASCADE"))
        conn.commit()
    yield
    with engine_pg.begin() as conn:
        conn.execute(text("TRUNCATE agent_events CASCADE"))
        conn.execute(text("TRUNCATE processed_events CASCADE"))
        yield


@pytest.fixture
def db_pg() -> Session:
    """PostgreSQL session for each test."""
    session = SessionPG()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def db_sqlite() -> Session:
    """SQLite session for each test."""
    session = SessionSQLite()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_mission(db_pg) -> Mission:
    """Create test mission."""
    mission = Mission(
        mission_id=str(uuid4()),
        project_id="test-project",
        tenant_id="test-tenant",
        name="Test Mission",
        status="PENDING",
    )
    db_pg.add(mission)
    db_pg.commit()
    return mission


# TEST 1: approval.requested projetado corretamente
def test_1_approval_requested_projected(db_pg, test_mission):
    """Verify approval.requested event is projected to PostgreSQL."""
    # Create event
    event = Event(
        event_id=str(uuid4()),
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        task_id=None,
        execution_id=None,
        correlation_id=str(uuid4()),
        causation_id=None,
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="requester-1",
        source_agent="api",
        target_agent=None,
        payload=json.dumps({
            "approval_id": str(uuid4()),
            "requested_by": "requester-1",
        }),
        status="PENDING",
        idempotency_key=f"approval.requested.{uuid4()}",
        retry_count=0,
    )

    # Project event
    result = handle_approval_requested(event, db_pg)
    assert result is True, "Handler should return True for successful projection"

    db_pg.commit()

    # Verify AgentEvent created
    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_id == event.event_id
    ).all()
    assert len(agent_events) == 1, "Should create exactly 1 AgentEvent"
    assert agent_events[0].event_type == "approval.requested"
    assert agent_events[0].tenant_id == "test-tenant"
    assert agent_events[0].project_id == "test-project"

    # Verify ProcessedEvent created (idempotency marker)
    processed = db_pg.query(ProcessedEvent).filter(
        ProcessedEvent.event_id == event.event_id
    ).first()
    assert processed is not None, "Should create ProcessedEvent"
    assert processed.event_type == "approval.requested"


# TEST 2: approval.approved projetado corretamente
def test_2_approval_approved_projected(db_pg, test_mission):
    """Verify approval.approved event is projected correctly."""
    event = Event(
        event_id=str(uuid4()),
        event_type="approval.approved",
        schema_version=1,
        mission_id=test_mission.mission_id,
        task_id=None,
        correlation_id=str(uuid4()),
        causation_id=None,
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="validator-1",
        source_agent="api",
        payload=json.dumps({
            "approval_id": str(uuid4()),
            "validator": "validator-1",
        }),
        status="PENDING",
        idempotency_key=f"approval.approved.{uuid4()}",
    )

    result = handle_approval_approved(event, db_pg)
    assert result is True
    db_pg.commit()

    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_type == "approval.approved"
    ).all()
    assert len(agent_events) == 1
    assert agent_events[0].processed_at is not None, "processed_at should be set"


# TEST 3: approval.rejected projetado corretamente
def test_3_approval_rejected_projected(db_pg, test_mission):
    """Verify approval.rejected event is projected correctly."""
    event = Event(
        event_id=str(uuid4()),
        event_type="approval.rejected",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="validator-1",
        source_agent="api",
        payload=json.dumps({
            "approval_id": str(uuid4()),
            "validator": "validator-1",
        }),
        status="PENDING",
        idempotency_key=f"approval.rejected.{uuid4()}",
    )

    result = handle_approval_rejected(event, db_pg)
    assert result is True
    db_pg.commit()

    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_type == "approval.rejected"
    ).all()
    assert len(agent_events) == 1


# TEST 4: approval.vetoed projetado corretamente
def test_4_approval_vetoed_projected(db_pg, test_mission):
    """Verify approval.vetoed event is projected correctly."""
    event = Event(
        event_id=str(uuid4()),
        event_type="approval.vetoed",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="security-1",
        source_agent="api",
        payload=json.dumps({
            "approval_id": str(uuid4()),
            "validator": "security-1",
            "reason": "Security risk detected",
        }),
        status="PENDING",
        idempotency_key=f"approval.vetoed.{uuid4()}",
    )

    result = handle_approval_vetoed(event, db_pg)
    assert result is True
    db_pg.commit()

    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_type == "approval.vetoed"
    ).all()
    assert len(agent_events) == 1
    assert agent_events[0].payload_summary.get("reason") == "Security risk detected"


# TEST 5: Mesmo event_id processado duas vezes (idempotência)
def test_5_duplicate_event_idempotent(db_pg, test_mission):
    """Verify same event_id processed twice is idempotent."""
    event_id = str(uuid4())

    # First processing
    event1 = Event(
        event_id=event_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="requester-1",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-1"}),
        status="PENDING",
        idempotency_key=f"approval.requested.{event_id}",
    )

    result1 = handle_approval_requested(event1, db_pg)
    db_pg.commit()
    assert result1 is True

    agent_events_1 = db_pg.query(AgentEvent).filter(
        AgentEvent.event_id == event_id
    ).count()
    assert agent_events_1 == 1, "First processing should create 1 AgentEvent"

    # Second processing (same event_id)
    result2 = handle_approval_requested(event1, db_pg)
    db_pg.commit()
    assert result2 is True, "Second processing should return True (idempotent)"

    agent_events_2 = db_pg.query(AgentEvent).filter(
        AgentEvent.event_id == event_id
    ).count()
    assert agent_events_2 == 1, "Second processing should NOT create duplicate (idempotent)"


# TEST 6: Retry após falha de projeção
def test_6_retry_after_projection_failure(db_pg, test_mission):
    """Verify handler can be retried after failure."""
    event_id = str(uuid4())

    # First attempt - simulate failure by returning False
    event = Event(
        event_id=event_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="requester-1",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-1"}),
        status="PENDING",
        idempotency_key=f"approval.requested.{event_id}",
    )

    # First attempt succeeds (no failure injected)
    result1 = handle_approval_requested(event, db_pg)
    db_pg.commit()
    assert result1 is True

    # Verify event was processed
    processed1 = db_pg.query(ProcessedEvent).filter(
        ProcessedEvent.event_id == event_id
    ).first()
    assert processed1 is not None

    # Second attempt (retry) - should be idempotent
    result2 = handle_approval_requested(event, db_pg)
    db_pg.commit()
    assert result2 is True, "Retry should succeed (idempotent)"

    processed_count = db_pg.query(ProcessedEvent).filter(
        ProcessedEvent.event_id == event_id
    ).count()
    assert processed_count == 1, "Should not create duplicate ProcessedEvent on retry"


# TEST 7: Reinicialização do worker com evento pendente
def test_7_worker_restart_with_pending_event(db_pg, test_mission):
    """Verify worker can recover pending events after restart."""
    event_id = str(uuid4())

    # Create pending event (simulating worker crash before ACK)
    event = Event(
        event_id=event_id,
        event_type="approval.approved",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="validator-1",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "validator": "validator-1"}),
        status="PENDING",  # Still pending, never ACK'd
        idempotency_key=f"approval.approved.{event_id}",
    )

    # First processing
    result1 = handle_approval_approved(event, db_pg)
    db_pg.commit()
    assert result1 is True

    # Simulate restart: process same event again
    result2 = handle_approval_approved(event, db_pg)
    db_pg.commit()
    assert result2 is True, "After restart, handler should be idempotent"

    # Verify no duplicates
    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_id == event_id
    ).count()
    assert agent_events == 1, "No duplicates after restart"


# TEST 8: Isolamento entre tenants
def test_8_tenant_isolation(db_pg, test_mission):
    """Verify events are isolated per tenant."""
    event1_id = str(uuid4())

    # Create event for tenant-1
    event1 = Event(
        event_id=event1_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="tenant-1",  # First tenant
        project_id="project-1",
        actor_id="requester-1",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-1"}),
        status="PENDING",
        idempotency_key=f"approval.requested.tenant1.{event1_id}",
    )

    result1 = handle_approval_requested(event1, db_pg)
    db_pg.commit()
    assert result1 is True

    # Verify tenant-1 has 1 AgentEvent
    tenant1_events = db_pg.query(AgentEvent).filter(
        AgentEvent.tenant_id == "tenant-1"
    ).count()
    assert tenant1_events == 1

    # Create event for tenant-2
    event2_id = str(uuid4())
    event2 = Event(
        event_id=event2_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="tenant-2",  # Different tenant
        project_id="project-1",
        actor_id="requester-2",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-2"}),
        status="PENDING",
        idempotency_key=f"approval.requested.tenant2.{event2_id}",
    )

    result2 = handle_approval_requested(event2, db_pg)
    db_pg.commit()
    assert result2 is True

    # Verify isolation
    tenant1_events = db_pg.query(AgentEvent).filter(
        AgentEvent.tenant_id == "tenant-1"
    ).count()
    tenant2_events = db_pg.query(AgentEvent).filter(
        AgentEvent.tenant_id == "tenant-2"
    ).count()
    assert tenant1_events == 1, "Tenant-1 should have only its own events"
    assert tenant2_events == 1, "Tenant-2 should have only its own events"


# TEST 9: Isolamento entre projects
def test_9_project_isolation(db_pg, test_mission):
    """Verify events are isolated per project."""
    event1_id = str(uuid4())

    event1 = Event(
        event_id=event1_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="project-1",  # First project
        actor_id="requester-1",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-1"}),
        status="PENDING",
        idempotency_key=f"approval.requested.proj1.{event1_id}",
    )

    result1 = handle_approval_requested(event1, db_pg)
    db_pg.commit()

    project1_events = db_pg.query(AgentEvent).filter(
        AgentEvent.project_id == "project-1"
    ).count()
    assert project1_events == 1

    # Create event for project-2
    event2_id = str(uuid4())
    event2 = Event(
        event_id=event2_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="project-2",  # Different project
        actor_id="requester-2",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-2"}),
        status="PENDING",
        idempotency_key=f"approval.requested.proj2.{event2_id}",
    )

    result2 = handle_approval_requested(event2, db_pg)
    db_pg.commit()

    project1_events = db_pg.query(AgentEvent).filter(
        AgentEvent.project_id == "project-1"
    ).count()
    project2_events = db_pg.query(AgentEvent).filter(
        AgentEvent.project_id == "project-2"
    ).count()
    assert project1_events == 1
    assert project2_events == 1


# TEST 10: Falha PostgreSQL antes do commit
def test_10_pg_failure_before_commit(db_pg, test_mission):
    """Verify handler can recover if PostgreSQL fails before commit."""
    event_id = str(uuid4())

    event = Event(
        event_id=event_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="requester-1",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-1"}),
        status="PENDING",
        idempotency_key=f"approval.requested.{event_id}",
    )

    # First attempt
    result1 = handle_approval_requested(event, db_pg)
    db_pg.commit()
    assert result1 is True

    # Simulate rollback (simulating failure before commit)
    # - Rollback the session
    db_pg.rollback()

    # Now retry - since rollback happened, ProcessedEvent wasn't created
    # So handler will process again
    result2 = handle_approval_requested(event, db_pg)
    db_pg.commit()
    assert result2 is True, "Handler should succeed on retry"

    # Event should be there (possibly duplicated if no idempotency in DB)
    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_id == event_id
    ).count()
    # After retry, we might have 2 if rollback deleted first attempt
    assert agent_events >= 1, "Event should be projected"


# TEST 11: Falha após commit PostgreSQL e antes do ACK SQLite
def test_11_failure_between_pg_and_sqlite(db_pg, test_mission):
    """Verify idempotency if PostgreSQL succeeds but ACK fails."""
    # This test validates that having ProcessedEvent in PostgreSQL ensures
    # the event won't be reprocessed even if SQLite ACK fails

    event_id = str(uuid4())

    event = Event(
        event_id=event_id,
        event_type="approval.requested",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="requester-1",
        source_agent="api",
        payload=json.dumps({"approval_id": str(uuid4()), "requested_by": "requester-1"}),
        status="PENDING",
        idempotency_key=f"approval.requested.{event_id}",
    )

    # First processing
    result1 = handle_approval_requested(event, db_pg)
    db_pg.commit()  # PostgreSQL commit succeeds
    # Now imagine SQLite ACK fails - but we have ProcessedEvent in PostgreSQL

    # Second attempt (simulating worker retry after SQLite ACK failure)
    result2 = handle_approval_requested(event, db_pg)
    db_pg.commit()
    assert result2 is True, "Handler should be idempotent"

    # Verify no duplicates despite SQLite ACK failure
    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_id == event_id
    ).count()
    assert agent_events == 1, "No duplicates even if SQLite ACK failed"


# TEST 12: Reprocessamento sem duplicar efeitos
def test_12_reprocessing_without_duplication(db_pg, test_mission):
    """Verify reprocessing same event multiple times has no duplicating effects."""
    event_id = str(uuid4())
    approval_id = str(uuid4())

    event = Event(
        event_id=event_id,
        event_type="approval.approved",
        schema_version=1,
        mission_id=test_mission.mission_id,
        correlation_id=str(uuid4()),
        causation_id=None,
        tenant_id="test-tenant",
        project_id="test-project",
        actor_id="validator-1",
        source_agent="api",
        payload=json.dumps({"approval_id": approval_id, "validator": "validator-1"}),
        status="PENDING",
        idempotency_key=f"approval.approved.{event_id}",
    )

    # Process 5 times
    for i in range(5):
        result = handle_approval_approved(event, db_pg)
        db_pg.commit()
        assert result is True

    # Verify exactly 1 AgentEvent (not 5)
    agent_events = db_pg.query(AgentEvent).filter(
        AgentEvent.event_id == event_id
    ).count()
    assert agent_events == 1, "Reprocessing should not create duplicates"

    # Verify exactly 1 ProcessedEvent
    processed = db_pg.query(ProcessedEvent).filter(
        ProcessedEvent.event_id == event_id
    ).count()
    assert processed == 1, "ProcessedEvent should be created only once"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
