"""Tests for RecoveryService: idempotency, lease, fencing, and retry."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database.models import Execution, ExecutionAttempt, EventIdempotencyKey, utc_now
from app.services.recovery_service import RecoveryService, RetryPolicy, FailureClassification


@pytest.fixture
def recovery_service():
    """Create RecoveryService instance."""
    policy = RetryPolicy(max_attempts=3, backoff_ms=100, backoff_multiplier=2.0)
    return RecoveryService(retry_policy=policy, lease_timeout_s=60)


@pytest.fixture
def test_execution(db: Session):
    """Create a test execution."""
    execution = Execution(
        execution_id="test-exec-001",
        mission_id="mission-001",
        task_id="task-001",
        agent_id="agent-001",
        runtime="claude-code-cli",
        status="RUNNING",
        tenant_id="tenant-001",
        project_id="project-001",
        attempt_number=1,
        fencing_token=0,
    )
    db.add(execution)
    db.commit()
    return execution


class TestRecoveryServiceIdempotency:
    """Test idempotency guarantees."""

    def test_execution_maintains_id_across_retries(self, db: Session, test_execution):
        """Ensure execution_id stays same across retries."""
        original_id = test_execution.execution_id
        test_execution.status = "FAILED"
        test_execution.failure_classification = FailureClassification.TRANSIENT
        db.commit()

        # Simulate retry
        execution = db.query(Execution).filter(
            Execution.execution_id == original_id
        ).first()

        assert execution.execution_id == original_id
        assert execution.attempt_number == 1

    def test_attempt_number_increments(self, db: Session, recovery_service, test_execution):
        """Verify attempt number increments correctly."""
        test_execution.status = "FAILED"
        test_execution.failure_classification = FailureClassification.TRANSIENT
        db.commit()

        recovery_service.schedule_retry(db, test_execution.execution_id, test_execution.fencing_token)

        updated = db.query(Execution).filter(
            Execution.execution_id == test_execution.execution_id
        ).first()

        assert updated.attempt_number == 2


class TestRecoveryServiceLease:
    """Test lease management."""

    def test_acquire_lease_generates_token(self, db: Session, recovery_service, test_execution):
        """Lease acquisition generates increasing fencing token."""
        success, token = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-001")

        assert success is True
        assert token == 1  # First token after initial 0

    def test_lease_prevents_concurrent_acquisition(self, db: Session, recovery_service, test_execution):
        """Active lease prevents another worker from acquiring."""
        # First worker acquires lease
        success1, token1 = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-001")
        assert success1 is True

        # Second worker tries to acquire
        success2, token2 = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-002")
        assert success2 is False
        assert token2 is None

    def test_expired_lease_allows_new_acquisition(self, db: Session, recovery_service, test_execution):
        """Expired lease can be reacquired by new worker."""
        # First worker acquires lease
        success1, token1 = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-001")
        assert success1 is True

        # Expire the lease manually
        execution = db.query(Execution).filter(
            Execution.execution_id == test_execution.execution_id
        ).first()
        execution.lease_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
        db.refresh(execution)  # Reload from DB with correct timezone

        # Second worker can acquire
        success2, token2 = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-002")
        assert success2 is True
        assert token2 == 2  # Next token


class TestRecoveryServiceFencingToken:
    """Test fencing token protection."""

    def test_fencing_token_validates_on_update(self, db: Session, recovery_service, test_execution):
        """Update with correct token succeeds."""
        # Acquire lease
        success, token = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-001")
        assert success is True

        # Update with correct token
        result = recovery_service.update_with_fence(
            db, test_execution.execution_id, token, "COMPLETED", result={"ok": True}
        )

        assert result is True

    def test_old_fencing_token_rejected(self, db: Session, recovery_service, test_execution):
        """Update with old token is rejected."""
        # Acquire lease with token 1
        success1, token1 = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-001")

        # Expire and reacquire with new token
        execution = db.query(Execution).filter(
            Execution.execution_id == test_execution.execution_id
        ).first()
        execution.lease_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
        db.refresh(execution)  # Reload from DB with correct timezone

        success2, token2 = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-002")

        # Try to update with old token 1
        result = recovery_service.update_with_fence(
            db, test_execution.execution_id, token1, "COMPLETED"
        )

        assert result is False


class TestRecoveryServiceFailureClassification:
    """Test failure classification."""

    def test_classify_transient_timeout(self, recovery_service):
        """Timeout is TRANSIENT."""
        result = recovery_service.classify_failure("connection timeout after 30s")
        assert result == FailureClassification.TRANSIENT

    def test_classify_permanent_permission(self, recovery_service):
        """Permission denied is PERMANENT."""
        result = recovery_service.classify_failure("Permission denied: command not in whitelist")
        assert result == FailureClassification.PERMANENT

    def test_classify_unknown_error(self, recovery_service):
        """Unknown error is UNKNOWN."""
        result = recovery_service.classify_failure("Something went wrong")
        assert result == FailureClassification.UNKNOWN

    def test_classify_empty_error(self, recovery_service):
        """Empty error is UNKNOWN."""
        result = recovery_service.classify_failure("")
        assert result == FailureClassification.UNKNOWN


class TestRecoveryServiceRetryPolicy:
    """Test retry policy."""

    def test_should_retry_transient(self, recovery_service):
        """TRANSIENT failures should retry."""
        should_retry = recovery_service.retry_policy.should_retry(FailureClassification.TRANSIENT, 1)
        assert should_retry is True

    def test_should_not_retry_permanent(self, recovery_service):
        """PERMANENT failures should not retry."""
        should_retry = recovery_service.retry_policy.should_retry(FailureClassification.PERMANENT, 1)
        assert should_retry is False

    def test_exponential_backoff(self, recovery_service):
        """Backoff increases exponentially."""
        delay1 = recovery_service.retry_policy.calculate_delay(1)
        delay2 = recovery_service.retry_policy.calculate_delay(2)
        delay3 = recovery_service.retry_policy.calculate_delay(3)

        assert delay2 > delay1
        assert delay3 > delay2


class TestRecoveryServiceIdempotencyKey:
    """Test event deduplication."""

    def test_generate_deterministic_key(self, recovery_service):
        """Idempotency key is deterministic."""
        key1 = recovery_service.generate_idempotency_key("event.created", "exec-001", 1)
        key2 = recovery_service.generate_idempotency_key("event.created", "exec-001", 1)

        assert key1 == key2

    def test_different_executions_different_keys(self, recovery_service):
        """Different executions have different keys."""
        key1 = recovery_service.generate_idempotency_key("event.created", "exec-001", 1)
        key2 = recovery_service.generate_idempotency_key("event.created", "exec-002", 1)

        assert key1 != key2

    def test_mark_and_check_event_processed(self, db: Session, recovery_service):
        """Event can be marked as processed and checked."""
        key = recovery_service.generate_idempotency_key("event.created", "exec-001", 1)

        # Initially not processed
        assert recovery_service.is_event_processed(db, key) is False

        # Mark as processed
        recovery_service.mark_event_processed(db, key, "event.created", "exec-001", 1, "tenant-001")

        # Now it's processed
        assert recovery_service.is_event_processed(db, key) is True


class TestRecoveryServiceAuditTrail:
    """Test execution attempt audit trail."""

    def test_record_execution_attempt(self, db: Session, recovery_service):
        """Execution attempt is recorded."""
        # REQUIRED: Create Execution first (foreign key constraint)
        execution = Execution(
            execution_id="exec-001",
            mission_id="mission-001",
            task_id="task-001",
            tenant_id="tenant-001",
            project_id="project-001",
            agent_id="agent-001",
            runtime="test-runtime",
            status="RUNNING"
        )
        db.add(execution)
        db.commit()

        success = recovery_service.record_attempt(
            db, "exec-001", 1, 1, "worker-001", "COMPLETED",
            duration_ms=1000, result={"ok": True}, tenant_id="tenant-001"
        )

        assert success is True

        attempt = db.query(ExecutionAttempt).filter(
            ExecutionAttempt.execution_id == "exec-001"
        ).first()

        assert attempt is not None
        assert attempt.attempt_number == 1
        assert attempt.worker_id == "worker-001"


class TestRecoveryServiceFindRecoverable:
    """Test finding recoverable executions."""

    def test_find_recoverable_filters_correctly(self, db: Session, recovery_service):
        """Only eligible executions are found."""
        now = utc_now()

        # Create a recoverable execution
        exec1 = Execution(
            execution_id="exec-001",
            mission_id="m1",
            task_id="t1",
            agent_id="a1",
            runtime="claude-code-cli",
            status="FAILED",
            tenant_id="tenant-001",
            project_id="p1",
            failure_classification=FailureClassification.TRANSIENT,
            next_retry_at=now - timedelta(seconds=1),
        )
        db.add(exec1)

        # Create a non-recoverable execution (PERMANENT)
        exec2 = Execution(
            execution_id="exec-002",
            mission_id="m1",
            task_id="t2",
            agent_id="a1",
            runtime="claude-code-cli",
            status="FAILED",
            tenant_id="tenant-001",
            project_id="p1",
            failure_classification=FailureClassification.PERMANENT,
            next_retry_at=now - timedelta(seconds=1),
        )
        db.add(exec2)
        db.commit()

        # Find recoverable
        recoverable = recovery_service.find_recoverable(db, "tenant-001")

        assert len(recoverable) == 1
        assert recoverable[0].execution_id == "exec-001"


# Integration tests
class TestRecoveryServiceIntegration:
    """Integration tests for recovery workflow."""

    def test_complete_recovery_workflow(self, db: Session, recovery_service, test_execution):
        """Test complete workflow: fail → classify → retry → succeed."""
        # Execution starts
        test_execution.status = "RUNNING"
        db.commit()

        # Acquire lease
        success, token = recovery_service.acquire_lease(db, test_execution.execution_id, "worker-1")
        assert success and token == 1

        # Execution fails with transient error
        recovery_service.update_with_fence(
            db, test_execution.execution_id, token, "FAILED",
            error="Connection timeout after 30s"
        )

        execution = db.query(Execution).filter(
            Execution.execution_id == test_execution.execution_id
        ).first()
        assert execution.failure_classification == FailureClassification.TRANSIENT

        # Schedule retry
        recovery_service.schedule_retry(db, test_execution.execution_id, token)

        execution = db.query(Execution).filter(
            Execution.execution_id == test_execution.execution_id
        ).first()
        assert execution.attempt_number == 2
        assert execution.status == "QUEUED"
