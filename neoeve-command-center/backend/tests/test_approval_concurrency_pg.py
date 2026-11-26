"""Concurrency tests for Approval Engine with real PostgreSQL."""

import pytest
import threading
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from database.models import Base, Tenant, Mission, Validation
from app.services.approval_engine_pg import ApprovalEnginePG

# IMPORTANTE: Requer PostgreSQL real (não SQLite)
DATABASE_URL = "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"

@pytest.fixture(scope="module")
def test_db():
    """Connect to real PostgreSQL for concurrency testing."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # Setup
    session = Session()
    yield session
    session.close()

@pytest.fixture
def test_mission_concurrent(test_db):
    """Create fresh mission for each test."""
    mission = Mission(
        mission_id=str(uuid4()),
        project_id="project-concurrent",
        tenant_id="tenant-concurrent",
        name="Concurrent Test Mission",
        status="RUNNING",
    )
    test_db.add(mission)
    test_db.commit()
    return mission

# TEST 1: Concurrent approvals - only one wins
def test_1_concurrent_approvals_pg(test_db, test_mission_concurrent):
    """REAL: Two concurrent threads, same approval, different decisions."""

    # Create approval
    engine1 = ApprovalEnginePG(test_db)
    approval_id = engine1.request_approval(
        mission_id=test_mission_concurrent.mission_id,
        task_id=None,
        tenant_id="tenant-concurrent",
        project_id="project-concurrent",
        requested_by="user-1",
        actor_id="user-1",
    )
    assert approval_id is not None

    results = {}

    def approve_in_thread():
        """Thread 1: Try to approve."""
        Session = sessionmaker(bind=test_db.get_bind())
        db = Session()
        engine = ApprovalEnginePG(db)

        try:
            success = engine.approve(
                approval_id=approval_id,
                validator_agent_id="agent-qa",
                justification="Approved from thread 1",
                tenant_id="tenant-concurrent",
                project_id="project-concurrent",
                actor_id="agent-qa",
            )
            results["approve"] = success
        finally:
            db.close()

    def reject_in_thread():
        """Thread 2: Try to reject simultaneously."""
        # Add small delay to ensure SELECT FOR UPDATE lock works
        time.sleep(0.1)

        Session = sessionmaker(bind=test_db.get_bind())
        db = Session()
        engine = ApprovalEnginePG(db)

        try:
            success = engine.reject(
                approval_id=approval_id,
                validator_agent_id="agent-qa",
                justification="Rejected from thread 2",
                tenant_id="tenant-concurrent",
                project_id="project-concurrent",
                actor_id="agent-qa",
            )
            results["reject"] = success
        finally:
            db.close()

    # Run concurrently
    t1 = threading.Thread(target=approve_in_thread)
    t2 = threading.Thread(target=reject_in_thread)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Only one should succeed
    success_count = sum(1 for v in results.values() if v is True)
    assert success_count == 1, f"Expected 1 success, got {success_count}: {results}"

    # Verify final state
    validation = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert validation.verdict in ["APPROVED", "BLOCKED"], f"Unexpected verdict: {validation.verdict}"

# TEST 2: Idempotent after decision
def test_2_idempotent_after_decision_pg(test_db, test_mission_concurrent):
    """Verify that decision is terminal and idempotent."""

    engine = ApprovalEnginePG(test_db)
    approval_id = engine.request_approval(
        mission_id=test_mission_concurrent.mission_id,
        task_id=None,
        tenant_id="tenant-concurrent",
        project_id="project-concurrent",
        requested_by="user-2",
        actor_id="user-2",
    )

    # First approval
    success1 = engine.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="First approval",
        tenant_id="tenant-concurrent",
        project_id="project-concurrent",
        actor_id="agent-qa",
    )
    assert success1 is True

    # Second attempt (should fail)
    success2 = engine.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Second attempt",
        tenant_id="tenant-concurrent",
        project_id="project-concurrent",
        actor_id="agent-qa",
    )
    assert success2 is False, "Second approval should fail (idempotency)"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
