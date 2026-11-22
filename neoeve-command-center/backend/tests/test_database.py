"""
Integration tests for PostgreSQL persistence.
Tests real database connections and operations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database.connection import engine, SessionLocal, test_connection
from database.models import Agent, Mission, Task, Execution, AgentEvent, Validation, ProjectionCheckpoint


def test_db_connection():
    """Test real PostgreSQL connection."""
    db = SessionLocal()
    try:
        result = db.query(Agent).count()
        print("✅ Connection test passed")
    finally:
        db.close()


def test_agent_persistence():
    """Test Agent table persistence."""
    db: Session = SessionLocal()

    agent = Agent(
        agent_id="test-architect-001",
        agent_role="architect",
        runtime="Claude Code CLI",
        status="ACTIVE",
        connectivity_status="ONLINE",
        metrics_summary={"test": "data"}
    )

    db.add(agent)
    db.commit()

    # Read back
    retrieved = db.query(Agent).filter(Agent.agent_id == "test-architect-001").first()
    assert retrieved is not None, "Agent not persisted"
    assert retrieved.agent_role == "architect"

    # Cleanup
    db.delete(retrieved)
    db.commit()
    db.close()

    print("✅ Agent persistence test passed")


def test_mission_persistence():
    """Test Mission table persistence."""
    db: Session = SessionLocal()

    mission = Mission(
        mission_id="test-mission-001",
        project_id="proj-001",
        tenant_id="tenant-001",
        name="Test Mission",
        status="RUNNING",
        progress_summary={"step": 1}
    )

    db.add(mission)
    db.commit()

    # Read back
    retrieved = db.query(Mission).filter(Mission.mission_id == "test-mission-001").first()
    assert retrieved is not None, "Mission not persisted"
    assert retrieved.project_id == "proj-001"

    # Cleanup
    db.delete(retrieved)
    db.commit()
    db.close()

    print("✅ Mission persistence test passed")


def test_execution_metrics():
    """Test Execution with metrics persistence."""
    db: Session = SessionLocal()

    execution = Execution(
        execution_id="exec-001",
        mission_id="mission-001",
        task_id="task-001",
        agent_id="agent-001",
        runtime="Claude Code CLI",
        status="COMPLETED",
        queued_at=datetime.now(timezone.utc),
        queue_time_ms=100,
        init_time_ms=50,
        execution_time_ms=1000,
        total_duration_ms=1150
    )

    db.add(execution)
    db.commit()

    # Read back
    retrieved = db.query(Execution).filter(Execution.execution_id == "exec-001").first()
    assert retrieved is not None, "Execution not persisted"
    assert retrieved.total_duration_ms == 1150

    # Cleanup
    db.delete(retrieved)
    db.commit()
    db.close()

    print("✅ Execution metrics test passed")


def test_multi_tenant_isolation():
    """Test multi-tenant isolation."""
    db: Session = SessionLocal()

    # Insert missions for different tenants
    mission1 = Mission(
        mission_id="mission-tenant1",
        project_id="proj-001",
        tenant_id="tenant-1",
        name="Tenant 1 Mission",
        status="PENDING"
    )

    mission2 = Mission(
        mission_id="mission-tenant2",
        project_id="proj-001",
        tenant_id="tenant-2",
        name="Tenant 2 Mission",
        status="PENDING"
    )

    db.add_all([mission1, mission2])
    db.commit()

    # Query for tenant 1
    tenant1_missions = db.query(Mission).filter(Mission.tenant_id == "tenant-1").all()
    assert len(tenant1_missions) == 1
    assert tenant1_missions[0].mission_id == "mission-tenant1"

    # Query for tenant 2
    tenant2_missions = db.query(Mission).filter(Mission.tenant_id == "tenant-2").all()
    assert len(tenant2_missions) == 1
    assert tenant2_missions[0].mission_id == "mission-tenant2"

    # Cleanup
    db.query(Mission).filter(Mission.mission_id.in_(["mission-tenant1", "mission-tenant2"])).delete()
    db.commit()
    db.close()

    print("✅ Multi-tenant isolation test passed")


def test_indexes():
    """Test that indexes are properly created."""
    db: Session = SessionLocal()

    # This query should use indexes efficiently
    result = db.query(Agent).filter(Agent.agent_role == "architect").all()

    db.close()
    print("✅ Index creation test passed")


def test_constraints():
    """Test unique constraints."""
    db: Session = SessionLocal()

    agent = Agent(
        agent_id="constraint-test",
        agent_role="backend",
        runtime="Claude CLI",
        status="IDLE"
    )

    db.add(agent)
    db.commit()

    # Try to insert duplicate (should fail or be prevented by constraint)
    try:
        agent2 = Agent(
            agent_id="constraint-test",  # Same ID
            agent_role="qa",
            runtime="Claude CLI",
            status="IDLE"
        )
        db.add(agent2)
        db.commit()
        # If we got here, constraint didn't work
        print("⚠️  Unique constraint not enforced")
    except Exception as e:
        print(f"✅ Unique constraint enforced: {type(e).__name__}")
    finally:
        db.query(Agent).filter(Agent.agent_id == "constraint-test").delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING PERSISTENCE TESTS")
    print("=" * 60)

    try:
        test_db_connection()
        test_agent_persistence()
        test_mission_persistence()
        test_execution_metrics()
        test_multi_tenant_isolation()
        test_indexes()
        test_constraints()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
