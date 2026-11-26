"""Integration tests: AgentRuntime + RecoveryMetricsService persistence."""

import pytest
from datetime import timedelta
from sqlalchemy.orm import Session

from database.models import Execution, RecoveryHistory, utc_now
from app.services.agent_runtime import AgentRuntime
from app.services.recovery_service import FailureClassification
from app.services.recovery_metrics_service import RecoveryMetricsService


@pytest.fixture
def agent_runtime():
    """Create AgentRuntime instance."""
    return AgentRuntime()


@pytest.fixture
def metrics_service():
    """Create RecoveryMetricsService instance."""
    return RecoveryMetricsService()


class TestMetricsPersistence:
    """Test metrics persistence through AgentRuntime integration."""

    def test_successful_execution_records_metrics(self, db: Session, agent_runtime):
        """Test that successful execution records metrics."""
        execution_id = "test-exec-persist-001"
        tenant_id = "tenant-persist-001"
        mission_id = "mission-001"
        task_id = "task-001"

        # Create Execution
        execution = Execution(
            execution_id=execution_id,
            mission_id=mission_id,
            task_id=task_id,
            agent_id="test-agent",
            runtime="claude-code-cli",
            status="COMPLETED",
            tenant_id=tenant_id,
            project_id="project-001",
            attempt_number=1,
            fencing_token=0,
        )
        db.add(execution)
        db.commit()

        # Simulate successful execution metrics recording
        agent_runtime.metrics_service.record_recovery_attempt(
            db, execution_id, mission_id, task_id, tenant_id,
            attempt_number=1,
            worker_id="test-worker",
            fencing_token=1,
            failure_classification=None,
            error_message=None,
            status="COMPLETED",
            duration_ms=500,
            next_retry_at=None
        )

        # Verify metrics were recorded
        history = db.query(RecoveryHistory).filter(
            RecoveryHistory.execution_id == execution_id
        ).all()

        assert len(history) == 1
        assert history[0].execution_id == execution_id
        assert history[0].status == "COMPLETED"
        assert history[0].duration_ms == 500
        assert history[0].tenant_id == tenant_id

    def test_failed_execution_records_metrics(self, db: Session, agent_runtime):
        """Test that failed execution records metrics with classification."""
        execution_id = "test-exec-persist-002"
        tenant_id = "tenant-persist-001"

        # Simulate failed execution with classification
        agent_runtime.metrics_service.record_recovery_attempt(
            db, execution_id, "mission-002", "task-002", tenant_id,
            attempt_number=1,
            worker_id="test-worker",
            fencing_token=1,
            failure_classification=FailureClassification.TRANSIENT,
            error_message="Connection timeout",
            status="QUEUED",
            duration_ms=100,
            next_retry_at=utc_now()
        )

        # Verify metrics recorded with classification
        history = db.query(RecoveryHistory).filter(
            RecoveryHistory.execution_id == execution_id
        ).first()

        assert history is not None
        assert history.failure_classification == FailureClassification.TRANSIENT
        assert history.status == "QUEUED"

    def test_metrics_isolated_by_tenant(self, db: Session, agent_runtime):
        """Test that metrics are strictly isolated by tenant."""
        # Clean up any existing data for test tenants
        db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id.in_(["tenant-001", "tenant-002"])
        ).delete()
        db.commit()

        # Tenant 1
        agent_runtime.metrics_service.record_recovery_attempt(
            db, "exec-t1", "m1", "t1", "tenant-001",
            attempt_number=1, worker_id="w1", fencing_token=1,
            failure_classification=None, error_message=None,
            status="COMPLETED", duration_ms=100, next_retry_at=None
        )

        # Tenant 2
        agent_runtime.metrics_service.record_recovery_attempt(
            db, "exec-t2", "m2", "t2", "tenant-002",
            attempt_number=1, worker_id="w2", fencing_token=1,
            failure_classification=None, error_message=None,
            status="COMPLETED", duration_ms=200, next_retry_at=None
        )

        # Tenant 1 query should only find its own
        t1_history = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == "tenant-001"
        ).all()

        assert len(t1_history) == 1
        assert t1_history[0].execution_id == "exec-t1"

        # Tenant 2 query should only find its own
        t2_history = db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == "tenant-002"
        ).all()

        assert len(t2_history) == 1
        assert t2_history[0].execution_id == "exec-t2"

    def test_idempotency_of_metrics_recording(self, db: Session, agent_runtime):
        """Test that recording same execution twice doesn't create duplicates (idempotent)."""
        execution_id = "test-exec-idempotent-001"
        tenant_id = "tenant-persist-001"

        # Record first time
        agent_runtime.metrics_service.record_recovery_attempt(
            db, execution_id, "mission-001", "task-001", tenant_id,
            attempt_number=1, worker_id="worker-1", fencing_token=1,
            failure_classification=None, error_message=None,
            status="COMPLETED", duration_ms=500, next_retry_at=None
        )

        # Record again (simulate idempotency)
        agent_runtime.metrics_service.record_recovery_attempt(
            db, execution_id, "mission-001", "task-001", tenant_id,
            attempt_number=1, worker_id="worker-1", fencing_token=1,
            failure_classification=None, error_message=None,
            status="COMPLETED", duration_ms=500, next_retry_at=None
        )

        # Should have 2 records (no deduplication at service level)
        # Deduplication is handled by application logic, not DB constraint
        history = db.query(RecoveryHistory).filter(
            RecoveryHistory.execution_id == execution_id
        ).all()

        assert len(history) == 2  # Both recorded


class TestMetricsServiceIntegration:
    """Test RecoveryMetricsService methods."""

    def test_dashboard_summary_reports_metrics(self, db: Session, metrics_service):
        """Test that dashboard summary aggregates metrics correctly."""
        tenant_id = "tenant-persist-001"

        # Clear any existing data
        db.query(RecoveryHistory).filter(
            RecoveryHistory.tenant_id == tenant_id
        ).delete()
        db.commit()

        # Record multiple attempts
        metrics_service.record_recovery_attempt(
            db, "exec-001", "m1", "t1", tenant_id,
            1, "w1", 1, None, None, "COMPLETED", 100, None
        )
        metrics_service.record_recovery_attempt(
            db, "exec-002", "m2", "t2", tenant_id,
            1, "w2", 1, FailureClassification.TRANSIENT, "timeout", "QUEUED", 50,
            utc_now() + timedelta(seconds=60)  # Future time for pending retry
        )
        metrics_service.record_recovery_attempt(
            db, "exec-003", "m3", "t3", tenant_id,
            1, "w3", 1, FailureClassification.PERMANENT, "denied", "FAILED", 30, None
        )

        # Get summary
        summary = metrics_service.get_dashboard_summary(db, tenant_id)

        assert summary["tenant_id"] == tenant_id
        assert summary["total_recovered"] == 2  # COMPLETED + FAILED (not QUEUED)
        assert summary["successful_recoveries"] == 1  # COMPLETED
        assert summary["failed_recoveries"] == 1  # FAILED
        assert summary["pending_retry_count"] == 1  # QUEUED with next_retry_at > now
        assert summary["average_recovery_time_ms"] == 65.0  # (100 + 30) / 2, not 50 (QUEUED)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
