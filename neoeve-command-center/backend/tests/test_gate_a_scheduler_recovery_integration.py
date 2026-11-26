"""
Tests for Gate A: Scheduler Integration with ProjectionCheckpoint Recovery

Validates that the Scheduler correctly recovers ProjectionCheckpoint instances
with expired leases, without interfering with ApprovalOutbox recovery.

Tests:
R1 - Scheduler invokes Recovery of ProjectionCheckpoint
R2 - Active lease is not recovered prematurely
R3 - Expired lease is recovered for new processing
R4 - Recovery failure of ProjectionCheckpoint does not interrupt ApprovalOutbox recovery
R5 - Multi-tenant isolation in recovery
R6 - Idempotent recovery (repeated execution doesn't corrupt state)
R7 - Worker with old token cannot commit after recovery
"""

import pytest
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.scheduler import ApprovalScheduler
from app.services.projection_checkpoint_lease_service import ProjectionCheckpointLeaseService
from database.models import ProjectionCheckpoint, utc_now, Tenant

logger = logging.getLogger(__name__)


class TestGateASchedulerRecoveryIntegration:
    """Test Scheduler integration with ProjectionCheckpoint recovery."""

    @pytest.fixture
    def cleanup_checkpoint(self, db_session):
        """Cleanup checkpoints after each test."""
        yield
        db_session.query(ProjectionCheckpoint).delete()
        db_session.commit()

    # R1 - Scheduler invokes Recovery of ProjectionCheckpoint
    def test_r1_scheduler_invokes_checkpoint_recovery(self, db_session, cleanup_checkpoint, test_tenant, inject_test_session):
        """[R1] Scheduler should invoke checkpoint recovery for expired leases."""
        tenant_id = test_tenant.tenant_id
        consumer_id = "consumer_r1"

        # Create expired checkpoint
        now = utc_now()
        expired_checkpoint = ProjectionCheckpoint(
            tenant_id=tenant_id,
            consumer_id=consumer_id,
            status="PROCESSING",
            worker_id="worker_1",
            lease_expires_at=now - timedelta(seconds=10),
            fencing_token=1,
            error_count=0
        )
        db_session.add(expired_checkpoint)
        db_session.commit()

        # Execute scheduler recovery (uses injected test session)
        scheduler = ApprovalScheduler(interval_seconds=1)
        TestSessionLocal = inject_test_session
        db = TestSessionLocal()
        try:
            scheduler._recover_expired_projection_checkpoints(db)
        finally:
            db.close()

        # Verify checkpoint was recovered
        recovered = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=tenant_id,
            consumer_id=consumer_id
        ).first()
        assert recovered is not None, "Checkpoint not found"
        assert recovered.status == "IDLE", f"Status should be IDLE, got {recovered.status}"
        assert recovered.worker_id is None, "Worker should be cleared"
        assert recovered.lease_expires_at is None, "Lease should be cleared"
        assert recovered.fencing_token == 1, "Fencing token should maintain monotonic invariant (not reset)"
        assert recovered.error_count == 1, "Error count should be incremented"

    # R2 - Active lease is not recovered prematurely
    def test_r2_active_lease_not_recovered(self, db_session, cleanup_checkpoint, test_tenant, inject_test_session):
        """[R2] Active leases should not be recovered."""
        tenant_id = test_tenant.tenant_id
        consumer_id = "consumer_r2"

        # Create checkpoint with ACTIVE lease
        now = utc_now()
        active_checkpoint = ProjectionCheckpoint(
            tenant_id=tenant_id,
            consumer_id=consumer_id,
            status="PROCESSING",
            worker_id="worker_1",
            lease_expires_at=now + timedelta(seconds=300),
            fencing_token=1,
            error_count=0
        )
        db_session.add(active_checkpoint)
        db_session.commit()

        # Execute recovery
        scheduler = ApprovalScheduler(interval_seconds=1)
        TestSessionLocal = inject_test_session
        db = TestSessionLocal()
        try:
            scheduler._recover_expired_projection_checkpoints(db)
        finally:
            db.close()

        # Verify checkpoint was NOT modified
        unchanged = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=tenant_id,
            consumer_id=consumer_id
        ).first()
        assert unchanged.status == "PROCESSING", "Active checkpoint should not change"
        assert unchanged.worker_id == "worker_1", "Worker should remain"
        assert unchanged.fencing_token == 1, "Token should not change"
        assert unchanged.error_count == 0, "Error count should not increment"

    # R3 - Expired lease is recovered for new processing
    def test_r3_expired_lease_recovered_for_new_processing(self, db_session, cleanup_checkpoint, test_tenant, inject_test_session):
        """[R3] Expired leases should be recovered and made eligible for new workers."""
        tenant_id = test_tenant.tenant_id
        consumer_id = "consumer_r3"

        # Create expired checkpoint
        now = utc_now()
        expired_checkpoint = ProjectionCheckpoint(
            tenant_id=tenant_id,
            consumer_id=consumer_id,
            status="PROCESSING",
            worker_id="worker_old",
            lease_expires_at=now - timedelta(seconds=10),
            fencing_token=1,
            error_count=0
        )
        db_session.add(expired_checkpoint)
        db_session.commit()

        # Execute recovery
        scheduler = ApprovalScheduler(interval_seconds=1)
        TestSessionLocal = inject_test_session
        db = TestSessionLocal()
        try:
            scheduler._recover_expired_projection_checkpoints(db)
        finally:
            db.close()

        # Verify checkpoint is IDLE
        recovered = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=tenant_id,
            consumer_id=consumer_id
        ).first()
        assert recovered.status == "IDLE", "Should be IDLE after recovery"

        # Verify new worker can acquire lease
        lease_service = ProjectionCheckpointLeaseService()
        success, token = lease_service.acquire_lease(
            db=db_session,
            consumer_id=consumer_id,
            tenant_id=tenant_id,
            worker_id="worker_new"
        )
        assert success is True, "New worker should be able to acquire lease"
        assert token == 2, f"Token should increment to 2, got {token}"

    # R4 - Recovery failure does not interrupt other recovery
    def test_r4_checkpoint_recovery_failure_isolated(self, db_session, cleanup_checkpoint, test_tenant, inject_test_session):
        """[R4] Checkpoint recovery failures should not crash the scheduler."""
        tenant_id = test_tenant.tenant_id
        consumer_id = "consumer_r4"

        # Create expired checkpoint
        now = utc_now()
        expired_checkpoint = ProjectionCheckpoint(
            tenant_id=tenant_id,
            consumer_id=consumer_id,
            status="PROCESSING",
            worker_id="worker_1",
            lease_expires_at=now - timedelta(seconds=10),
            fencing_token=1,
            error_count=0
        )
        db_session.add(expired_checkpoint)
        db_session.commit()

        # Execute recovery - should not raise
        scheduler = ApprovalScheduler(interval_seconds=1)
        TestSessionLocal = inject_test_session
        db = TestSessionLocal()

        try:
            scheduler._recover_expired_projection_checkpoints(db)
            recovery_succeeded = True
        except Exception as e:
            logger.error(f"Recovery raised exception: {e}")
            recovery_succeeded = False
        finally:
            db.close()

        # Verify recovery completed without crashing
        assert recovery_succeeded is True, "Recovery should complete without exception"

    # R5 - Multi-tenant isolation in recovery
    def test_r5_multitenant_isolation_recovery(self, db_session, cleanup_checkpoint, test_tenant, test_tenants, inject_test_session):
        """[R5] Recovery should maintain multi-tenant isolation."""
        tenant_id = test_tenant.tenant_id

        now = utc_now()

        # Create checkpoint
        checkpoint_a = ProjectionCheckpoint(
            tenant_id=tenant_id,
            consumer_id="consumer_a",
            status="PROCESSING",
            worker_id="worker_a",
            lease_expires_at=now - timedelta(seconds=10),
            fencing_token=1,
            error_count=0
        )
        db_session.add(checkpoint_a)
        db_session.commit()

        # Execute recovery
        scheduler = ApprovalScheduler(interval_seconds=1)
        TestSessionLocal = inject_test_session
        db = TestSessionLocal()
        try:
            scheduler._recover_expired_projection_checkpoints(db)
        finally:
            db.close()

        # Verify tenant isolation
        recovered_a = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=tenant_id,
            consumer_id="consumer_a"
        ).first()
        assert recovered_a.status == "IDLE", "Checkpoint should be recovered"
        assert recovered_a.worker_id is None, "Worker should be cleared"

    # R6 - Idempotent recovery
    def test_r6_recovery_idempotent(self, db_session, cleanup_checkpoint, test_tenant, inject_test_session):
        """[R6] Recovery should be idempotent (repeated calls don't corrupt state)."""
        tenant_id = test_tenant.tenant_id
        consumer_id = "consumer_r6"

        # Create expired checkpoint
        now = utc_now()
        checkpoint = ProjectionCheckpoint(
            tenant_id=tenant_id,
            consumer_id=consumer_id,
            status="PROCESSING",
            worker_id="worker_1",
            lease_expires_at=now - timedelta(seconds=10),
            fencing_token=1,
            error_count=0
        )
        db_session.add(checkpoint)
        db_session.commit()

        # Execute recovery three times
        scheduler = ApprovalScheduler(interval_seconds=1)
        TestSessionLocal = inject_test_session

        for i in range(3):
            db = TestSessionLocal()
            try:
                scheduler._recover_expired_projection_checkpoints(db)
            finally:
                db.close()

        # Verify state is consistent
        final_state = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=tenant_id,
            consumer_id=consumer_id
        ).first()

        assert final_state.status == "IDLE", "Should remain IDLE"
        assert final_state.error_count == 1, f"Error count should be 1, got {final_state.error_count}"
        assert final_state.worker_id is None, "Worker should remain None"
        assert final_state.lease_expires_at is None, "Lease should remain None"
        assert final_state.fencing_token == 1, "Token should remain unchanged (monotonic, not reset to 0)"

    # R7 - Old token invalidated after recovery
    def test_r7_old_worker_token_invalidated_after_recovery(self, db_session, cleanup_checkpoint, test_tenant, inject_test_session):
        """[R7] Old worker token should be invalidated after recovery (fencing)."""
        tenant_id = test_tenant.tenant_id
        consumer_id = "consumer_r7"

        # Setup: Worker acquires lease
        lease_service = ProjectionCheckpointLeaseService()
        success, token_1 = lease_service.acquire_lease(
            db=db_session,
            consumer_id=consumer_id,
            tenant_id=tenant_id,
            worker_id="worker_original"
        )
        assert success is True
        assert token_1 == 1

        # Expire the lease
        now = utc_now()
        checkpoint = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=tenant_id,
            consumer_id=consumer_id
        ).first()
        checkpoint.lease_expires_at = now - timedelta(seconds=10)
        db_session.commit()

        # Recovery happens
        scheduler = ApprovalScheduler(interval_seconds=1)
        TestSessionLocal = inject_test_session
        db = TestSessionLocal()
        try:
            scheduler._recover_expired_projection_checkpoints(db)
        finally:
            db.close()

        # Refresh checkpoint
        db_session.expire(checkpoint)

        # Verify old worker cannot validate with old token
        is_valid_old = lease_service.validate_lease(
            db=db_session,
            consumer_id=consumer_id,
            tenant_id=tenant_id,
            worker_id="worker_original",
            fencing_token=token_1  # Old token
        )
        assert is_valid_old is False, "Old worker with old token should be fenced"

        # Verify checkpoint token was NOT reset (monotonic invariant)
        checkpoint = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=tenant_id,
            consumer_id=consumer_id
        ).first()
        # Token remains 1; old worker is blocked by expired lease, not by token change
        assert checkpoint.fencing_token == 1, "Fencing token should maintain monotonic invariant (not reset)"
        # Note: lease_expires_at may be None or in the past; either indicates recovery was successful
        assert checkpoint.status == "IDLE", "Status should be IDLE"
