"""Tests for Recovery Dashboard and monitoring."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from database.models import RecoveryHistory, utc_now
from app.services.recovery_metrics_service import RecoveryMetricsService
from app.services.recovery_service import FailureClassification


@pytest.fixture
def sample_history(db: Session):
    """Create sample recovery history for testing."""
    # Clean up any existing data first
    db.query(RecoveryHistory).delete()
    db.commit()

    histories = []

    # Successful recovery
    h1 = RecoveryHistory(
        execution_id="exec-001",
        mission_id="m1",
        task_id="t1",
        tenant_id="tenant-001",
        attempt_number=1,
        worker_id="worker-1",
        fencing_token=1,
        failure_classification=FailureClassification.TRANSIENT,
        error_message="Connection timeout",
        attempted_at=utc_now(),
        completed_at=utc_now(),
        duration_ms=500,
        status="COMPLETED",
    )
    db.add(h1)
    histories.append(h1)

    # Failed recovery
    h2 = RecoveryHistory(
        execution_id="exec-002",
        mission_id="m2",
        task_id="t2",
        tenant_id="tenant-001",
        attempt_number=1,
        worker_id="worker-1",
        fencing_token=1,
        failure_classification=FailureClassification.PERMANENT,
        error_message="Permission denied",
        attempted_at=utc_now(),
        completed_at=utc_now(),
        duration_ms=100,
        status="FAILED",
    )
    db.add(h2)
    histories.append(h2)

    # Pending retry
    h3 = RecoveryHistory(
        execution_id="exec-003",
        mission_id="m3",
        task_id="t3",
        tenant_id="tenant-001",
        attempt_number=2,
        worker_id="worker-2",
        fencing_token=2,
        failure_classification=FailureClassification.TRANSIENT,
        error_message="Network error",
        attempted_at=utc_now(),
        completed_at=None,
        duration_ms=None,
        status="QUEUED",
        next_retry_at=utc_now() + timedelta(seconds=60),
    )
    db.add(h3)
    histories.append(h3)

    db.commit()
    return histories


class TestRecoveryDashboard:
    """Recovery dashboard tests."""

    def test_total_recovered(self, db: Session, sample_history):
        """Test total recovered count."""
        total = RecoveryMetricsService.get_total_recovered(db, "tenant-001")
        assert total == 2  # 1 successful + 1 failed

    def test_successful_recoveries(self, db: Session, sample_history):
        """Test successful recovery count."""
        successful = RecoveryMetricsService.get_successful_recoveries(db, "tenant-001")
        assert successful == 1

    def test_failed_recoveries(self, db: Session, sample_history):
        """Test failed recovery count."""
        failed = RecoveryMetricsService.get_failed_recoveries(db, "tenant-001")
        assert failed == 1

    def test_pending_retry_count(self, db: Session, sample_history):
        """Test pending retry count."""
        pending = RecoveryMetricsService.get_pending_retry_count(db, "tenant-001")
        assert pending == 1

    def test_pending_executions(self, db: Session, sample_history):
        """Test retrieving pending executions."""
        pending = RecoveryMetricsService.get_pending_executions(db, "tenant-001")
        assert len(pending) == 1
        assert pending[0].execution_id == "exec-003"

    def test_failures_by_classification(self, db: Session, sample_history):
        """Test failures grouped by classification."""
        failures = RecoveryMetricsService.get_failures_by_classification(db, "tenant-001")
        assert failures[FailureClassification.PERMANENT] == 1

    def test_average_recovery_time(self, db: Session, sample_history):
        """Test average recovery time calculation."""
        avg_ms = RecoveryMetricsService.get_average_recovery_time(db, "tenant-001")
        # (500 + 100) / 2 = 300
        assert avg_ms == 300.0

    def test_recovery_history_for_execution(self, db: Session, sample_history):
        """Test retrieving history for specific execution."""
        history = RecoveryMetricsService.get_recovery_history(
            db, "tenant-001", execution_id="exec-001"
        )
        assert len(history) == 1
        assert history[0].execution_id == "exec-001"

    def test_recent_failures(self, db: Session, sample_history):
        """Test retrieving recent failures."""
        failures = RecoveryMetricsService.get_recent_failures(db, "tenant-001", hours=24)
        assert len(failures) == 1  # Only the PERMANENT failure
        assert failures[0].execution_id == "exec-002"

    def test_worker_health(self, db: Session, sample_history):
        """Test worker health metrics."""
        health = RecoveryMetricsService.get_worker_health(db, "tenant-001")
        assert "worker-1" in health
        assert health["worker-1"]["total_attempts"] == 2
        assert health["worker-1"]["successful"] == 1

    def test_dashboard_summary(self, db: Session, sample_history):
        """Test complete dashboard summary."""
        summary = RecoveryMetricsService.get_dashboard_summary(db, "tenant-001")
        assert summary["tenant_id"] == "tenant-001"
        assert summary["total_recovered"] == 2
        assert summary["successful_recoveries"] == 1
        assert summary["failed_recoveries"] == 1
        assert summary["pending_retry_count"] == 1


class TestDashboardIsolation:
    """Multi-tenant isolation tests."""

    def test_metrics_isolated_by_tenant(self, db: Session):
        """Test that metrics are isolated by tenant."""
        # Clean up first
        db.query(RecoveryHistory).delete()
        db.commit()

        # Tenant 1
        h1 = RecoveryHistory(
            execution_id="exec-t1-001",
            mission_id="m1",
            task_id="t1",
            tenant_id="tenant-001",
            attempt_number=1,
            worker_id="worker-1",
            fencing_token=1,
            failure_classification=FailureClassification.TRANSIENT,
            error_message="Error T1",
            attempted_at=utc_now(),
            completed_at=utc_now(),
            duration_ms=500,
            status="COMPLETED",
        )
        db.add(h1)

        # Tenant 2
        h2 = RecoveryHistory(
            execution_id="exec-t2-001",
            mission_id="m2",
            task_id="t2",
            tenant_id="tenant-002",
            attempt_number=1,
            worker_id="worker-2",
            fencing_token=1,
            failure_classification=FailureClassification.PERMANENT,
            error_message="Error T2",
            attempted_at=utc_now(),
            completed_at=utc_now(),
            duration_ms=100,
            status="FAILED",
        )
        db.add(h2)
        db.commit()

        # Verify isolation
        t1_total = RecoveryMetricsService.get_total_recovered(db, "tenant-001")
        t2_total = RecoveryMetricsService.get_total_recovered(db, "tenant-002")

        assert t1_total == 1
        assert t2_total == 1

        # Tenant 1 should have no failures (only successful)
        t1_failures = RecoveryMetricsService.get_failed_recoveries(db, "tenant-001")
        assert t1_failures == 0

        # Tenant 2 should have 1 failure
        t2_failures = RecoveryMetricsService.get_failed_recoveries(db, "tenant-002")
        assert t2_failures == 1

    def test_history_isolation_by_tenant(self, db: Session):
        """Test that history is isolated by tenant."""
        # Clean up first
        db.query(RecoveryHistory).delete()
        db.commit()

        # Add history for two tenants
        h1 = RecoveryHistory(
            execution_id="exec-t1",
            mission_id="m1",
            task_id="t1",
            tenant_id="tenant-001",
            attempt_number=1,
            worker_id="worker-1",
            fencing_token=1,
            failure_classification=FailureClassification.TRANSIENT,
            error_message="T1 error",
            attempted_at=utc_now(),
            completed_at=utc_now(),
            duration_ms=500,
            status="COMPLETED",
        )
        db.add(h1)

        h2 = RecoveryHistory(
            execution_id="exec-t2",
            mission_id="m2",
            task_id="t2",
            tenant_id="tenant-002",
            attempt_number=1,
            worker_id="worker-2",
            fencing_token=1,
            failure_classification=FailureClassification.TRANSIENT,
            error_message="T2 error",
            attempted_at=utc_now(),
            completed_at=utc_now(),
            duration_ms=300,
            status="COMPLETED",
        )
        db.add(h2)
        db.commit()

        # Query history for tenant-001
        t1_history = RecoveryMetricsService.get_recovery_history(db, "tenant-001")
        assert len(t1_history) == 1
        assert t1_history[0].execution_id == "exec-t1"

        # Query history for tenant-002
        t2_history = RecoveryMetricsService.get_recovery_history(db, "tenant-002")
        assert len(t2_history) == 1
        assert t2_history[0].execution_id == "exec-t2"


class TestDashboardAbsenceOfData:
    """Tests for handling empty metrics."""

    def test_metrics_empty_tenant(self, db: Session):
        """Test metrics when no history exists."""
        total = RecoveryMetricsService.get_total_recovered(db, "tenant-empty")
        successful = RecoveryMetricsService.get_successful_recoveries(db, "tenant-empty")
        failed = RecoveryMetricsService.get_failed_recoveries(db, "tenant-empty")
        pending = RecoveryMetricsService.get_pending_retry_count(db, "tenant-empty")

        assert total == 0
        assert successful == 0
        assert failed == 0
        assert pending == 0

    def test_average_time_empty_tenant(self, db: Session):
        """Test average recovery time for empty tenant."""
        avg_ms = RecoveryMetricsService.get_average_recovery_time(db, "tenant-empty")
        assert avg_ms == 0.0

    def test_worker_health_empty_tenant(self, db: Session):
        """Test worker health for empty tenant."""
        health = RecoveryMetricsService.get_worker_health(db, "tenant-empty")
        assert health == {}

    def test_dashboard_summary_empty_tenant(self, db: Session):
        """Test dashboard summary for empty tenant."""
        summary = RecoveryMetricsService.get_dashboard_summary(db, "tenant-empty")
        assert summary["total_recovered"] == 0
        assert summary["successful_recoveries"] == 0
        assert summary["failed_recoveries"] == 0
        assert summary["pending_retry_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
