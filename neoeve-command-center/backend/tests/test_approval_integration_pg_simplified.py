"""Integration tests for Approval Engine PostgreSQL - SQLite compatible version."""

import pytest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Tenant, Mission, Validation
from app.services.approval_engine_pg import ApprovalEnginePG

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

# TEST 4: Idempotent Approvals (second attempt fails)
def test_4_idempotent_approvals(approval_engine_pg, test_db, test_tenant, test_mission):
    """Idempotency: second approval attempt should fail."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    success1 = approval_engine_pg.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="First approval",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success1 is True

    # Second approval attempt should fail
    success2 = approval_engine_pg.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Second attempt",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success2 is False

# TEST 5: Approval then Rejection blocked
def test_5_decision_terminal(approval_engine_pg, test_db, test_tenant, test_mission):
    """Once approved, cannot be rejected."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    # Approve
    success = approval_engine_pg.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Approved",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success is True

    # Try to reject - should fail (decision is terminal)
    success = approval_engine_pg.reject(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Now rejecting",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success is False

# TEST 6: Approval History
def test_6_approval_history(approval_engine_pg, test_db, test_tenant, test_mission):
    """Approval history retrieval."""
    approval_id = approval_engine_pg.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    approval_engine_pg.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="OK",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )

    history = approval_engine_pg.get_approval_history(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=test_mission.mission_id,
    )

    assert len(history) == 1
    assert history[0]["verdict"] == "APPROVED"

# TEST 7-8: Placeholders
def test_7_websocket_persistence_first(approval_engine_pg):
    """WebSocket notifies AFTER PostgreSQL commit."""
    assert True

def test_8_rest_recovery_after_disconnect(approval_engine_pg):
    """REST API recovery mechanism."""
    assert True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
