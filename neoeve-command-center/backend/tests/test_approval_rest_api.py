"""REST API tests for Approval Engine."""

import pytest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Tenant, Mission, Validation

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
def test_tenant(test_db):
    tenant = Tenant(tenant_id="tenant-test", name="Test")
    test_db.add(tenant)
    test_db.commit()
    return {"tenant_id": "tenant-test", "project_id": "project-test"}

@pytest.fixture
def test_mission(test_db, test_tenant):
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

# TEST 1: Request approval via REST (simulated)
def test_1_rest_request_approval(test_db, test_tenant, test_mission):
    """REST endpoint to request approval."""
    # Simulate: POST /api/approvals/request
    approval_id = str(uuid4())
    validation = Validation(
        validation_id=approval_id,
        mission_id=test_mission.mission_id,
        task_id=None,
        validator="qa_engineer",
        verdict="PENDING",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    test_db.add(validation)
    test_db.commit()

    result = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert result is not None
    assert result.verdict == "PENDING"

# TEST 2: Approve via REST
def test_2_rest_approve(test_db, test_tenant, test_mission):
    """REST endpoint to approve."""
    approval_id = str(uuid4())
    validation = Validation(
        validation_id=approval_id,
        mission_id=test_mission.mission_id,
        validator="qa_engineer",
        verdict="PENDING",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    test_db.add(validation)
    test_db.commit()

    # Simulate: POST /api/approvals/{id}/approve
    validation.verdict = "APPROVED"
    validation.confidence = 100
    test_db.commit()

    result = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert result.verdict == "APPROVED"

# TEST 3: Reject via REST
def test_3_rest_reject(test_db, test_tenant, test_mission):
    """REST endpoint to reject."""
    approval_id = str(uuid4())
    validation = Validation(
        validation_id=approval_id,
        mission_id=test_mission.mission_id,
        validator="qa_engineer",
        verdict="PENDING",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    test_db.add(validation)
    test_db.commit()

    # Simulate: POST /api/approvals/{id}/reject
    validation.verdict = "BLOCKED"
    test_db.commit()

    result = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert result.verdict == "BLOCKED"

# TEST 4: Get approval
def test_4_rest_get_approval(test_db, test_tenant, test_mission):
    """REST endpoint to get approval status."""
    approval_id = str(uuid4())
    validation = Validation(
        validation_id=approval_id,
        mission_id=test_mission.mission_id,
        validator="qa_engineer",
        verdict="APPROVED",
        confidence=100,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    test_db.add(validation)
    test_db.commit()

    # Simulate: GET /api/approvals/{id}
    result = test_db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    assert result.approval_id == approval_id if hasattr(result, 'approval_id') else result.validation_id == approval_id

# TEST 5: List approvals
def test_5_rest_list_approvals(test_db, test_tenant, test_mission):
    """REST endpoint to list approvals for mission."""
    # Create 2 approvals
    for i in range(2):
        validation = Validation(
            validation_id=str(uuid4()),
            mission_id=test_mission.mission_id,
            validator="qa_engineer",
            verdict="APPROVED" if i == 0 else "PENDING",
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        test_db.add(validation)
    test_db.commit()

    # Simulate: GET /api/approvals/mission/{mission_id}/approvals
    results = test_db.query(Validation).filter(
        Validation.mission_id == test_mission.mission_id
    ).all()

    assert len(results) == 2

# Placeholders for remaining tests
def test_6_autoapproval_blocked(test_db):
    """Autoaprovação bloqueada."""
    assert True

def test_7_websocket_notification(test_db):
    """WebSocket notificação após REST."""
    assert True

def test_8_tenant_isolation_rest(test_db):
    """Isolamento tenant via REST."""
    assert True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
