"""
Tests for Gate A: Atomic Reservation, Lease, Worker Ownership, Fencing, Recovery.

Validates ProjectionCheckpointLeaseService and integration with ProjectionWorker.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Minimal imports for Gate A tests - avoids loading FastAPI app
from app.services.projection_checkpoint_lease_service import ProjectionCheckpointLeaseService
from database.models import ProjectionCheckpoint, utc_now


class TestProjectionCheckpointLease:
    """Test lease acquisition, validation, and release."""

    @pytest.fixture
    def lease_service(self):
        """Create lease service with 1-minute timeout."""
        return ProjectionCheckpointLeaseService(lease_timeout_s=60)

    @pytest.fixture
    def checkpoint_id(self):
        """Test checkpoint ID."""
        return "test_consumer_checkpoint"

    @pytest.fixture
    def cleanup_checkpoint(self, db_session, checkpoint_id, test_tenant_id, test_tenant):
        """Clean up test checkpoint after test completes."""
        yield
        db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=test_tenant_id,
            consumer_id=checkpoint_id
        ).delete()
        db_session.commit()

    # TEST A: Simple lease acquisition
    def test_lease_acquisition_simple(self, lease_service, db_session, checkpoint_id, cleanup_checkpoint, test_tenant_id):
        """
        GIVEN a checkpoint without active lease
        WHEN acquire_lease is called
        THEN lease should be granted with fencing token
        """
        success, token = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1"
        )

        assert success is True
        assert token == 1  # First token is 1

        # Verify checkpoint state
        checkpoint = db_session.query(ProjectionCheckpoint).filter_by(
            consumer_id=checkpoint_id
        ).first()
        assert checkpoint is not None
        assert checkpoint.worker_id == "worker_1"
        assert checkpoint.fencing_token == 1
        assert checkpoint.lease_expires_at is not None

    # TEST B: Concurrent lease acquisition (simulated)
    def test_lease_acquisition_concurrent_rejection(self, lease_service, db_session, checkpoint_id, cleanup_checkpoint, test_tenant_id):
        """
        GIVEN a checkpoint with active lease
        WHEN another worker tries to acquire
        THEN lease should be rejected
        """
        # First worker acquires
        success1, token1 = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1"
        )
        assert success1 is True

        # Second worker attempts (should fail - lease active)
        success2, token2 = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_2"
        )
        assert success2 is False
        assert token2 is None

    # TEST C: Lease expiration and takeover
    def test_lease_expiration_and_takeover(self, db_session, checkpoint_id, cleanup_checkpoint, test_tenant_id):
        """
        GIVEN a checkpoint with expired lease
        WHEN another worker acquires
        THEN new lease should be granted with incremented token
        """
        # First acquisition
        lease_service1 = ProjectionCheckpointLeaseService(lease_timeout_s=1)
        success1, token1 = lease_service1.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1"
        )
        assert success1 is True
        assert token1 == 1

        # Manually expire lease
        checkpoint = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=test_tenant_id,
            consumer_id=checkpoint_id
        ).first()
        checkpoint.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db_session.commit()

        # Second worker acquires (should succeed - lease expired)
        lease_service2 = ProjectionCheckpointLeaseService(lease_timeout_s=60)
        success2, token2 = lease_service2.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_2"
        )
        assert success2 is True
        assert token2 == 2  # Incremented token

    # TEST D: Lease validation
    def test_lease_validation(self, lease_service, db_session, checkpoint_id, cleanup_checkpoint, test_tenant_id):
        """
        GIVEN a worker with active lease and correct token
        WHEN validate_lease is called
        THEN validation should pass
        """
        # Acquire lease
        success, token = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1"
        )

        # Validate (should pass)
        is_valid = lease_service.validate_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1",
            fencing_token=token
        )
        assert is_valid is True

    # TEST E: Fencing - old worker blocked
    def test_fencing_token_prevents_old_worker(self, db_session, checkpoint_id, cleanup_checkpoint, test_tenant_id):
        """
        GIVEN a worker lost lease to new worker
        WHEN old worker tries to validate with old token
        THEN validation should fail (fencing)
        """
        # First worker acquires
        lease_service = ProjectionCheckpointLeaseService(lease_timeout_s=1)
        success1, token1 = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1"
        )
        assert success1 is True
        assert token1 == 1

        # Expire and new worker takes over
        checkpoint = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id=test_tenant_id,
            consumer_id=checkpoint_id
        ).first()
        checkpoint.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db_session.commit()

        success2, token2 = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_2"
        )
        assert success2 is True
        assert token2 == 2

        # Old worker tries to validate with old token (should FAIL)
        is_valid_old = lease_service.validate_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1",
            fencing_token=token1  # Old token
        )
        assert is_valid_old is False

        # New worker validates (should pass)
        is_valid_new = lease_service.validate_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_2",
            fencing_token=token2
        )
        assert is_valid_new is True

    # TEST F: Lease release
    def test_lease_release(self, lease_service, db_session, checkpoint_id, cleanup_checkpoint, test_tenant_id):
        """
        GIVEN a worker with active lease
        WHEN release_lease is called with correct token
        THEN lease should expire
        """
        # Acquire
        success, token = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1"
        )

        # Release
        released = lease_service.release_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            fencing_token=token
        )
        assert released is True

        # Try to acquire again (should succeed - lease expired)
        success2, token2 = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_2"
        )
        assert success2 is True

    # TEST G: Release with wrong token (fencing)
    def test_lease_release_wrong_token(self, lease_service, db_session, checkpoint_id, cleanup_checkpoint, test_tenant_id):
        """
        GIVEN a worker with token X
        WHEN another worker tries to release with token Y
        THEN release should fail (fencing)
        """
        # Worker 1 acquires
        success1, token1 = lease_service.acquire_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            worker_id="worker_1"
        )

        # Worker 2 tries to release with wrong token (should fail)
        released = lease_service.release_lease(
            db=db_session,
            consumer_id=checkpoint_id,
            tenant_id=test_tenant_id,
            fencing_token=token1 + 999  # Wrong token
        )
        assert released is False

    # TEST H: Multi-tenant isolation
    def test_lease_multi_tenant_isolation(self, lease_service, db_session, test_tenants):
        """
        GIVEN two checkpoints with different tenant IDs
        WHEN each acquires a lease
        THEN leases should be independent and isolated per tenant
        """
        # Tenant A acquires
        success_a, token_a = lease_service.acquire_lease(
            db=db_session,
            consumer_id="consumer_a",
            tenant_id="tenant_a",
            worker_id="worker_a"
        )
        assert success_a is True

        # Tenant B acquires (should succeed - different tenant_id)
        success_b, token_b = lease_service.acquire_lease(
            db=db_session,
            consumer_id="consumer_b",
            tenant_id="tenant_b",
            worker_id="worker_b"
        )
        assert success_b is True

        # Verify isolation: each tenant has its own lease
        checkpoint_a = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id="tenant_a",
            consumer_id="consumer_a"
        ).first()
        assert checkpoint_a is not None
        assert checkpoint_a.worker_id == "worker_a"
        assert checkpoint_a.fencing_token == token_a

        checkpoint_b = db_session.query(ProjectionCheckpoint).filter_by(
            tenant_id="tenant_b",
            consumer_id="consumer_b"
        ).first()
        assert checkpoint_b is not None
        assert checkpoint_b.worker_id == "worker_b"
        assert checkpoint_b.fencing_token == token_b

        # Cleanup performed by conftest cleanup_all_tables
