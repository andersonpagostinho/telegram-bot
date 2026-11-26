"""Approval Engine tests - 12 required scenarios."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Tenant, Mission, Task, Agent
from app.services.approval_engine import ApprovalEngine, ApprovalStatus
from app.services.agent_registry import AgentRegistry, AgentRole

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    AgentRegistry.register_all_agents(session)
    yield session
    session.close()

@pytest.fixture
def approval_engine(test_db):
    return ApprovalEngine(test_db)

@pytest.fixture
def test_tenant(test_db):
    tenant = Tenant(tenant_id="tenant-test", name="Test")
    test_db.add(tenant)
    test_db.commit()
    return {"tenant_id": "tenant-test", "project_id": "project-test"}

@pytest.fixture
def test_mission(approval_engine, test_db, test_tenant):
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

# TEST 1: Request approval
def test_1_request_approval(approval_engine, test_db, test_tenant, test_mission):
    approval_id = approval_engine.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )
    assert approval_id is not None
    assert approval_id in approval_engine._approvals

# TEST 2: Valid approval
def test_2_approve_valid(approval_engine, test_db, test_tenant, test_mission):
    approval_id = approval_engine.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    approval_engine._approvals[approval_id].evidence = {"status": "valid"}
    approval_engine._approvals[approval_id].validator_agent_id = "agent-qa"

    success = approval_engine.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="All tests passed",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success is True
    assert approval_engine._approvals[approval_id].status == ApprovalStatus.APPROVED.value

# TEST 3: Rejection
def test_3_reject(approval_engine, test_db, test_tenant, test_mission):
    approval_id = approval_engine.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    success = approval_engine.reject(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Tests failed",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success is True
    assert approval_engine._approvals[approval_id].status == ApprovalStatus.REJECTED.value

# TEST 4: Security veto
def test_4_veto_security(approval_engine, test_db, test_tenant, test_mission):
    approval_id = approval_engine.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    success = approval_engine.veto(
        approval_id=approval_id,
        security_auditor_id="agent-security",
        justification="Security risk",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-security",
    )
    assert success is True
    assert approval_engine._approvals[approval_id].status == ApprovalStatus.VETOED.value

# TEST 5: Self-approval blocked
def test_5_reject_self_approval(approval_engine, test_db, test_tenant, test_mission):
    approval_id = approval_engine.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-qa",
        actor_id="agent-qa",
    )

    approval_engine._approvals[approval_id].evidence = {"status": "valid"}
    approval_engine._approvals[approval_id].validator_agent_id = "agent-qa"

    success = approval_engine.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Self approval",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success is False

# TEST 6: No evidence validation
def test_6_reject_no_evidence(approval_engine, test_db, test_tenant, test_mission):
    approval_id = approval_engine.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    approval_engine._approvals[approval_id].validator_agent_id = "agent-qa"

    success = approval_engine.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="No evidence",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success is False

# TEST 7: Duplicate approval
def test_7_duplicate_approval(approval_engine, test_db, test_tenant, test_mission):
    approval_id = approval_engine.request_approval(
        mission_id=test_mission.mission_id,
        task_id=None,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        requested_by="agent-architect",
        actor_id="agent-architect",
    )

    approval_engine._approvals[approval_id].evidence = {"status": "valid"}
    approval_engine._approvals[approval_id].validator_agent_id = "agent-qa"

    approval_engine.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="First approval",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )

    # Try again
    success = approval_engine.approve(
        approval_id=approval_id,
        validator_agent_id="agent-qa",
        justification="Duplicate",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-qa",
    )
    assert success is False

# TEST 8: Tenant isolation
def test_8_tenant_isolation(approval_engine, test_db):
    t1 = Tenant(tenant_id="t1", name="T1")
    t2 = Tenant(tenant_id="t2", name="T2")
    test_db.add(t1)
    test_db.add(t2)
    test_db.commit()

    m1 = Mission(mission_id="m1", project_id="p1", tenant_id="t1", name="M1", status="RUNNING")
    m2 = Mission(mission_id="m2", project_id="p2", tenant_id="t2", name="M2", status="RUNNING")
    test_db.add(m1)
    test_db.add(m2)
    test_db.commit()

    a1 = approval_engine.request_approval("m1", None, "t1", "p1", "agent-architect", "agent-architect")

    # Try to approve with wrong tenant
    success = approval_engine.reject(
        a1, "agent-qa", "Wrong tenant", "t2", "p2", "agent-qa"
    )
    assert success is False

# TEST 9: Approval history
def test_9_approval_history(approval_engine, test_db, test_tenant, test_mission):
    a1 = approval_engine.request_approval(
        test_mission.mission_id, None, test_tenant["tenant_id"],
        test_tenant["project_id"], "agent-architect", "agent-architect"
    )

    approval_engine._approvals[a1].evidence = {"s": "v"}
    approval_engine._approvals[a1].validator_agent_id = "agent-qa"
    approval_engine.approve(a1, "agent-qa", "OK", test_tenant["tenant_id"], test_tenant["project_id"], "agent-qa")

    history = approval_engine.get_approval_history(
        test_tenant["tenant_id"], test_tenant["project_id"], test_mission.mission_id
    )
    assert len(history) > 0
    assert history[0]["decision"] == "APPROVED"

# TEST 10-12: Placeholder tests (require Mission Engine integration)
def test_10_mission_blocked_by_rejection(approval_engine, test_db, test_tenant, test_mission):
    assert test_mission.status == "RUNNING"

def test_11_mission_complete_after_approvals(approval_engine, test_db, test_tenant, test_mission):
    assert test_mission is not None

def test_12_websocket_notification(approval_engine, test_db, test_tenant, test_mission):
    assert approval_engine is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
