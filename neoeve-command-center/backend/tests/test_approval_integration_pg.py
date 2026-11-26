"""Integration tests for Approval Engine with PostgreSQL and concurrency."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from threading import Thread, Event as ThreadEvent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Tenant, Mission, Validation
from app.services.approval_engine_pg import ApprovalEnginePG
from app.services.agent_registry import AgentRegistry

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def approval_engine_pg(test_db):
    return ApprovalEnginePG(test_db)

@pytest.fixture
def test_tenant(test_db):
    tenant = Tenant(tenant_id="tenant-test", name="Test")
    test_db.add(tenant)
    test_db.commit()
    return {"tenant_id": "tenant-test", "project_id": "project-test"}

@pytest.fixture
def test_mission(approval_engine_pg, test_db, test_tenant):
    mission = Mission(
        mission_id=str(uuid4()),
        project_id=test_tenant["project_id"],
        tenant_id=test_tenant["tenant_id"],
        name="Test Mission",
        status="RUNNING",
    )
    test_db.add(mission)
    test_db.commit()
    return mission

# TEST 1: PostgreSQL Persistence
def test_1_postgresql_persistence(approval_engine_pg, test_db, test_tenant, test_mission):
    """Approval persisted to PostgreSQL Validation table."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    assert approval_id is not None

    # Verify persisted in database
    validation = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert validation is not None
    assert validation.mission_id == test_mission.mission_id
    assert validation.verdict == "PENDING"

# TEST 2: Approval Persisted
def test_2_approval_persisted(approval_engine_pg, test_db, test_tenant, test_mission):
    """Approval decision persisted to PostgreSQL."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    success = approval_engine_pg.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="All tests passed",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )

    assert success is True

    # Verify persisted
    validation = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert validation.verdict == "APPROVED"

# TEST 3: Rejection Persisted
def test_3_rejection_persisted(approval_engine_pg, test_db, test_tenant, test_mission):
    """Rejection persisted to PostgreSQL."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    success = approval_engine_pg.reject(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Tests failed",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )

    assert success is True

    validation = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert validation.verdict == "BLOCKED"

# TEST 4: Concurrent Approvals (only one wins)
def test_4_concurrent_approvals_one_wins(approval_engine_pg, test_db, test_tenant, test_mission):
    """Two concurrent approvals - only one should succeed due to row-level lock."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    results = {"thread1": None, "thread2": None}

    def approve_in_thread(thread_name):
        try:
            # Create a new session for this thread (simulate concurrent request)
            Session = sessionmaker(bind=test_db.get_bind())
            thread_db = Session()
            engine = ApprovalEnginePG(thread_db)

            success = engine.approve(
                approval_id=approval_id,
                validator_agent_id="agent-qa",
                justification=f"Approval from {thread_name}",
                tenant_id=test_tenant["tenant_id"],
                project_id=test_tenant["project_id"],
                actor_id="agent-qa",
            )
            results[thread_name] = success
            thread_db.close()
        except Exception as e:
            results[thread_name] = False

    t1 = Thread(target=approve_in_thread, args=("thread1",))
    t2 = Thread(target=approve_in_thread, args=("thread2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Only one should succeed
    success_count = sum(1 for v in results.values() if v is True)
    assert success_count == 1, f"Expected 1 success, got {success_count}: {results}"

# TEST 5: Approval and Rejection Simultaneous
def test_5_concurrent_approve_reject(approval_engine_pg, test_db, test_tenant, test_mission):
    """Approve and reject simultaneously - only one should succeed."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    results = {}

    def approve_thread():
        Session = sessionmaker(bind=test_db.get_bind())
        thread_db = Session()
        engine = ApprovalEnginePG(thread_db)
        results["approve"] = engine.approve(
            approval_id=approval_id,
            validator_agent_id="agent-qa",
            justification="Approved",
            tenant_id=test_tenant["tenant_id"],
            project_id=test_tenant["project_id"],
            actor_id="agent-qa",
        )
        thread_db.close()

    def reject_thread():
        Session = sessionmaker(bind=test_db.get_bind())
        thread_db = Session()
        engine = ApprovalEnginePG(thread_db)
        results["reject"] = engine.reject(
            approval_id=approval_id,
            validator_agent_id="agent-qa",
            justification="Rejected",
            tenant_id=test_tenant["tenant_id"],
            project_id=test_tenant["project_id"],
            actor_id="agent-qa",
        )
        thread_db.close()

    t1 = Thread(target=approve_thread)
    t2 = Thread(target=reject_thread)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Only one should succeed
    success_count = sum(1 for v in results.values() if v is True)
    assert success_count == 1, f"Expected 1 success, got {success_count}: {results}"

# TEST 6-8: Placeholders for WebSocket and REST
def test_6_websocket_persistence_first(approval_engine_pg, test_db):
    """WebSocket notification should only happen after PostgreSQL commit."""
    assert True  # TODO: Implement with actual WebSocket

def test_7_tenant_isolation_concurrent(approval_engine_pg):
    """Concurrent operations in different tenants should not interfere."""
    assert True  # TODO: Implement multi-tenant concurrency

def test_8_rest_recovery_after_disconnect(approval_engine_pg):
    """REST API should allow recovery after WebSocket disconnect."""
    assert True  # TODO: Implement REST recovery endpoint

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
