"""Mission Engine tests: C.2.1 implementation tests."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import patch, Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Tenant, Mission, Task, Agent, Execution
from app.services.mission_engine import MissionEngine, DelegationMatrix
from app.services.agent_registry import AgentRegistry, AgentRole


TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db_session():
    """Create test database with fresh session."""
    test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

    # Create all tables explicitly
    Base.metadata.create_all(test_engine)

    # Verify critical tables exist
    with test_engine.connect() as conn:
        try:
            conn.execute(("SELECT 1 FROM missions LIMIT 1"))
        except:
            pass  # Table may not have data, that's OK

    Session = sessionmaker(bind=test_engine)
    session = Session()

    # Register agents
    AgentRegistry.register_all_agents(session)

    yield session
    session.close()


@pytest.fixture
def engine_instance(test_db_session):
    """Create Mission Engine instance."""
    return MissionEngine(test_db_session)


@pytest.fixture
def test_tenant(test_db_session):
    """Create test tenant."""
    tenant = Tenant(tenant_id="tenant-test", name="Test Tenant")
    test_db_session.add(tenant)
    test_db_session.commit()
    return {"tenant_id": "tenant-test", "project_id": "project-test"}


# ========= TEST 1: CREATE MISSION =========
def test_1_create_mission(engine_instance, test_db_session, test_tenant):
    """Test: Create mission."""
    mission = engine_instance.create_mission(
        name="Test Mission",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    assert mission is not None
    assert mission.name == "Test Mission"
    assert mission.status == "PENDING"


# ========= TEST 2: GET MISSION =========
def test_2_get_mission(engine_instance, test_db_session, test_tenant):
    """Test: Retrieve mission."""
    mission = engine_instance.create_mission(
        name="Retrieve Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    retrieved = engine_instance.get_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id
    )
    assert retrieved is not None
    assert retrieved.mission_id == mission.mission_id


# ========= TEST 3: DECOMPOSE MISSION =========
def test_3_decompose_mission(engine_instance, test_db_session, test_tenant):
    """Test: Decompose mission into tasks."""
    mission = engine_instance.create_mission(
        name="Complex Mission",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[
            {"description": "Implement", "task_type": "implement", "priority": "HIGH"},
            {"description": "Debug", "task_type": "debug", "priority": "NORMAL"},
            {"description": "Test", "task_type": "test", "priority": "HIGH"},
        ],
        actor_id="agent-architect",
    )

    assert len(tasks) == 3
    assert all(t.mission_id == mission.mission_id for t in tasks)


# ========= TEST 4: ASSIGN AUTHORIZED AGENT =========
def test_4_assign_authorized_agent(engine_instance, test_db_session, test_tenant):
    """Test: Assign task to authorized agent."""
    mission = engine_instance.create_mission(
        name="Assignment Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[{"description": "Implement", "task_type": "implement"}],
        actor_id="agent-architect",
    )

    task = tasks[0]
    success = engine_instance.assign_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-backend",
        actor_id="agent-architect",
    )

    assert success is True
    test_db_session.refresh(task)
    assert task.assigned_agent == "agent-backend"


# ========= TEST 5: REJECT UNAUTHORIZED AGENT =========
def test_5_reject_unauthorized_agent(engine_instance, test_db_session, test_tenant):
    """Test: Reject agent without capability."""
    mission = engine_instance.create_mission(
        name="Capability Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[{"description": "Implement", "task_type": "implement"}],
        actor_id="agent-architect",
    )

    task = tasks[0]
    success = engine_instance.assign_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-validator",  # Read-only
        actor_id="agent-architect",
    )

    assert success is False


# ========= TEST 6: REJECT NO EXECUTOR =========
def test_6_reject_no_executor(engine_instance, test_db_session, test_tenant):
    """Test: Reject agent without executor."""
    # Create agent without executor
    agent = Agent(
        agent_id="agent-no-exec",
        agent_role="backend_developer",
        runtime=None,
        status="IDLE",
    )
    test_db_session.add(agent)
    test_db_session.commit()

    mission = engine_instance.create_mission(
        name="Executor Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[{"description": "Task", "task_type": "implement"}],
        actor_id="agent-architect",
    )

    # Register fake agent
    AgentRegistry.AGENTS["fake_no_exec"] = {
        "agent_id": "agent-no-exec",
        "role": AgentRole.BACKEND_DEVELOPER,
        "name": "No Executor",
        "description": "Test",
    }

    task = tasks[0]
    success = engine_instance.assign_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-no-exec",
        actor_id="agent-architect",
    )

    assert success is False


# ========= TEST 7: BLOCK UNMET DEPENDENCIES =========
def test_7_block_unmet_dependencies(engine_instance, test_db_session, test_tenant):
    """Test: Block task with unmet dependencies."""
    mission = engine_instance.create_mission(
        name="Dependency Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    # Create tasks with dependencies
    task1 = Task(
        task_id="task-1",
        mission_id=mission.mission_id,
        status="PENDING",
        priority="NORMAL",
    )
    task2 = Task(
        task_id="task-2",
        mission_id=mission.mission_id,
        status="PENDING",
        priority="NORMAL",
        result={"dependencies": ["task-1"]},
    )
    test_db_session.add(task1)
    test_db_session.add(task2)
    test_db_session.commit()

    success = engine_instance.assign_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id="task-2",
        agent_id="agent-backend",
        actor_id="agent-architect",
    )

    assert success is False
    test_db_session.refresh(task2)
    assert task2.status == "BLOCKED"


# ========= TEST 8: EXECUTE TASK =========
@patch('app.services.mission_engine.AgentRuntime.execute_task')
def test_8_execute_task(mock_runtime_execute, engine_instance, test_db_session, test_tenant):
    """Test: Execute task integration with AgentRuntime (mocked)."""
    # Mock runtime.execute_task() to return success
    mock_runtime_execute.return_value = (True, "test output", "")

    mission = engine_instance.create_mission(
        name="Execution Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[{"description": "Echo", "task_type": "implement"}],
        actor_id="agent-architect",
    )

    task = tasks[0]
    engine_instance.assign_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-backend",
        actor_id="agent-architect",
    )

    success, stdout, stderr = engine_instance.execute_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-backend",
        task_description="echo 'test'",
        workspace_path="/tmp",
        timeout_seconds=10,
    )

    # Verify success
    assert mock_runtime_execute.called
    assert success is True


# ========= TEST 9: PREVENT DUPLICATE EXECUTION =========
def test_9_prevent_duplicate_execution(engine_instance, test_db_session, test_tenant):
    """Test: Prevent duplicate execution."""
    mission = engine_instance.create_mission(
        name="Duplicate Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[{"description": "Task", "task_type": "implement"}],
        actor_id="agent-architect",
    )

    task = tasks[0]

    # Mark as completed
    execution = Execution(
        execution_id=str(uuid4()),
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-backend",
        runtime="claude-code-cli",
        status="COMPLETED",
    )
    test_db_session.add(execution)
    test_db_session.commit()

    # Try to assign again - should fail
    success = engine_instance.assign_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-backend",
        actor_id="agent-architect",
    )

    assert success is False


# ========= TEST 10: PAUSE MISSION =========
def test_10_pause_mission(engine_instance, test_db_session, test_tenant):
    """Test: Pause mission."""
    mission = engine_instance.create_mission(
        name="Pause Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    engine_instance.start_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
        "agent-architect",
    )

    success = engine_instance.pause_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
        "agent-architect",
    )

    assert success is True
    test_db_session.refresh(mission)
    assert mission.status == "PAUSED"


# ========= TEST 11: RESUME MISSION =========
def test_11_resume_mission(engine_instance, test_db_session, test_tenant):
    """Test: Resume mission."""
    mission = engine_instance.create_mission(
        name="Resume Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    engine_instance.start_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
        "agent-architect",
    )

    engine_instance.pause_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
        "agent-architect",
    )

    success = engine_instance.resume_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
        "agent-architect",
    )

    assert success is True
    test_db_session.refresh(mission)
    assert mission.status == "RUNNING"


# ========= TEST 12: CANCEL MISSION =========
def test_12_cancel_mission(engine_instance, test_db_session, test_tenant):
    """Test: Cancel mission."""
    mission = engine_instance.create_mission(
        name="Cancel Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[{"description": "Task", "task_type": "implement"}],
        actor_id="agent-architect",
    )

    success = engine_instance.cancel_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
        "agent-architect",
    )

    assert success is True
    test_db_session.refresh(mission)
    assert mission.status == "CANCELLED"


# ========= TEST 13: HANDLE FAILURES =========
@patch('app.services.mission_engine.AgentRuntime.execute_task')
def test_13_handle_failures(mock_runtime_execute, engine_instance, test_db_session, test_tenant):
    """Test: Handle task failures (mocked)."""
    # Mock runtime.execute_task() to return failure
    mock_runtime_execute.return_value = (False, "", "execution failed")

    mission = engine_instance.create_mission(
        name="Failure Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[{"description": "Task", "task_type": "implement"}],
        actor_id="agent-architect",
    )

    task = tasks[0]
    engine_instance.assign_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-backend",
        actor_id="agent-architect",
    )

    success, stdout, stderr = engine_instance.execute_task(
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        mission_id=mission.mission_id,
        task_id=task.task_id,
        agent_id="agent-backend",
        task_description="exit 1",
        workspace_path="/tmp",
        timeout_seconds=10,
    )

    # Verify failure is handled
    assert mock_runtime_execute.called
    assert success is False


# ========= TEST 14: TENANT ISOLATION =========
def test_14_tenant_isolation(engine_instance, test_db_session):
    """Test: Tenant isolation."""
    tenant1 = Tenant(tenant_id="tenant-1", name="Tenant 1")
    tenant2 = Tenant(tenant_id="tenant-2", name="Tenant 2")
    test_db_session.add(tenant1)
    test_db_session.add(tenant2)
    test_db_session.commit()

    m1 = engine_instance.create_mission(
        name="Mission T1",
        tenant_id="tenant-1",
        project_id="project-1",
        actor_id="agent-architect",
    )

    m2 = engine_instance.create_mission(
        name="Mission T2",
        tenant_id="tenant-2",
        project_id="project-2",
        actor_id="agent-architect",
    )

    # Tenant 1 should not see Tenant 2's mission
    retrieved = engine_instance.get_mission("tenant-1", "project-1", m2.mission_id)
    assert retrieved is None


# ========= TEST 15: MISSION STATUS =========
def test_15_mission_status(engine_instance, test_db_session, test_tenant):
    """Test: Get mission status."""
    mission = engine_instance.create_mission(
        name="Status Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    tasks = engine_instance.decompose_mission(
        mission_id=mission.mission_id,
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        task_decomposition=[
            {"description": "T1", "task_type": "implement"},
            {"description": "T2", "task_type": "debug"},
        ],
        actor_id="agent-architect",
    )

    status = engine_instance.get_mission_status(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
    )

    assert status is not None
    assert status["mission_id"] == mission.mission_id
    assert status["total_tasks"] == 2


# ========= TEST 16: PERSISTENCE AFTER RESTART =========
def test_16_persistence_after_restart(engine_instance, test_db_session, test_tenant):
    """Test: Persistence after restart."""
    mission = engine_instance.create_mission(
        name="Persistence Test",
        tenant_id=test_tenant["tenant_id"],
        project_id=test_tenant["project_id"],
        actor_id="agent-architect",
    )

    engine_instance.start_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission.mission_id,
        "agent-architect",
    )

    mission_id = mission.mission_id

    # "Restart" - create new engine
    new_engine = MissionEngine(test_db_session)

    # Verify mission still exists
    retrieved = new_engine.get_mission(
        test_tenant["tenant_id"],
        test_tenant["project_id"],
        mission_id,
    )

    assert retrieved is not None
    assert retrieved.status == "RUNNING"


# ========= DELEGATION MATRIX TEST =========
def test_delegation_matrix_valid_assignments():
    """Test: Delegation matrix."""
    assert DelegationMatrix.can_assign("implement", "agent-backend") is True
    assert DelegationMatrix.can_assign("debug", "agent-debugger") is True
    assert DelegationMatrix.can_assign("test", "agent-qa") is True
    assert DelegationMatrix.can_assign("implement", "agent-validator") is False
    assert DelegationMatrix.can_assign("implement", "agent-architect") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
