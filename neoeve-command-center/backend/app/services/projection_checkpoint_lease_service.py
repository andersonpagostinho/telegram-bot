"""
Projection Checkpoint Lease Service — Atomic reservation for ProjectionWorker.

Implements Gate A: Atomic reservation + Lease + Worker ownership + Fencing.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from database.models import ProjectionCheckpoint, utc_now

logger = logging.getLogger(__name__)


class ProjectionCheckpointLeaseService:
    """Service for managing ProjectionCheckpoint leases and worker ownership."""

    def __init__(self, lease_timeout_s: int = 300):
        """
        Initialize lease service.

        Args:
            lease_timeout_s: Lease duration in seconds (default 5 minutes)
        """
        self.lease_timeout_s = lease_timeout_s

    def acquire_lease(
        self,
        db: Session,
        consumer_id: str,
        tenant_id: str,
        worker_id: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Acquire an atomic lease on a checkpoint using INSERT ON CONFLICT.

        Guarantees atomicity at database level:
        - Exactly one worker wins if checkpoint doesn't exist (no race condition)
        - Fencing token is monotonically incremented
        - Multi-tenant isolation enforced

        Returns:
            (success, fencing_token) or (False, None) if lease cannot be acquired
        """
        try:
            now = utc_now()
            lease_expiration = now + timedelta(seconds=self.lease_timeout_s)

            # Atomic INSERT ... ON CONFLICT DO UPDATE
            # PostgreSQL native atomicity: exactly one worker wins
            sql = text("""
                INSERT INTO projection_checkpoints
                    (tenant_id, consumer_id, worker_id, fencing_token, lease_expires_at, updated_at, status, error_count)
                VALUES
                    (:tenant_id, :consumer_id, :worker_id, 1, :lease_expires_at, :updated_at, 'IDLE', 0)
                ON CONFLICT (tenant_id, consumer_id) DO UPDATE SET
                    worker_id = CASE
                        WHEN projection_checkpoints.lease_expires_at IS NULL
                            OR projection_checkpoints.lease_expires_at <= :now_check
                        THEN :worker_id
                        ELSE projection_checkpoints.worker_id
                    END,
                    fencing_token = CASE
                        WHEN projection_checkpoints.lease_expires_at IS NULL
                            OR projection_checkpoints.lease_expires_at <= :now_check
                        THEN projection_checkpoints.fencing_token + 1
                        ELSE projection_checkpoints.fencing_token
                    END,
                    lease_expires_at = CASE
                        WHEN projection_checkpoints.lease_expires_at IS NULL
                            OR projection_checkpoints.lease_expires_at <= :now_check
                        THEN :lease_expires_at
                        ELSE projection_checkpoints.lease_expires_at
                    END,
                    updated_at = CASE
                        WHEN projection_checkpoints.lease_expires_at IS NULL
                            OR projection_checkpoints.lease_expires_at <= :now_check
                        THEN :updated_at
                        ELSE projection_checkpoints.updated_at
                    END
                RETURNING worker_id, fencing_token, lease_expires_at
            """)

            result = db.execute(sql, {
                "tenant_id": tenant_id,
                "consumer_id": consumer_id,
                "worker_id": worker_id,
                "lease_expires_at": lease_expiration,
                "updated_at": now,
                "now_check": now
            })

            row = result.first()
            if not row:
                return False, None

            returned_worker_id, fencing_token, returned_lease_exp = row

            # Check if WE acquired the lease (not someone else)
            if returned_worker_id != worker_id:
                logger.warning(
                    f"Checkpoint {tenant_id}/{consumer_id} already leased by {returned_worker_id}. "
                    f"Lease expires at {returned_lease_exp}"
                )
                return False, None

            logger.info(
                f"Checkpoint {tenant_id}/{consumer_id}: Lease acquired by {worker_id}, "
                f"token={fencing_token}, expires_at={returned_lease_exp}"
            )
            return True, fencing_token

        except Exception as e:
            logger.error(f"Failed to acquire lease for {tenant_id}/{consumer_id}: {e}")
            raise

    def validate_lease(
        self,
        db: Session,
        consumer_id: str,
        tenant_id: str,
        worker_id: str,
        fencing_token: int
    ) -> bool:
        """
        Validate that a worker still owns the lease with correct token.

        Uses WITH_FOR_UPDATE lock to prevent TOCTOU between validation and use.
        Prevents old workers from continuing after losing the lease.

        Returns:
            True if lease is valid, False otherwise
        """
        try:
            # WITH_FOR_UPDATE: lock prevents ownership change during validation
            checkpoint = db.query(ProjectionCheckpoint).filter(
                ProjectionCheckpoint.tenant_id == tenant_id,
                ProjectionCheckpoint.consumer_id == consumer_id
            ).with_for_update().first()

            if not checkpoint:
                logger.error(f"Checkpoint {tenant_id}/{consumer_id} not found for validation")
                return False

            # Check all three: worker_id, fencing_token, and lease not expired
            now = utc_now()
            is_owned = checkpoint.worker_id == worker_id
            is_token_valid = checkpoint.fencing_token == fencing_token
            is_lease_valid = (
                checkpoint.lease_expires_at and
                (checkpoint.lease_expires_at.tzinfo is None or
                 checkpoint.lease_expires_at > now)
            )

            if not (is_owned and is_token_valid and is_lease_valid):
                logger.warning(
                    f"Checkpoint {tenant_id}/{consumer_id}: Lease validation failed. "
                    f"Owned={is_owned}, Token valid={is_token_valid}, "
                    f"Lease valid={is_lease_valid}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating lease for {tenant_id}/{consumer_id}: {e}")
            return False

    def release_lease(
        self,
        db: Session,
        consumer_id: str,
        tenant_id: str,
        fencing_token: int
    ) -> bool:
        """
        Release lease atomically using UPDATE with WHERE conditions.

        Guarantees:
        - Only correct worker can release (token must match)
        - Atomic at database level
        - Prevents wrong worker from releasing wrong lease
        """
        try:
            now = utc_now()

            # Atomic UPDATE with WHERE conditions
            sql = text("""
                UPDATE projection_checkpoints
                SET lease_expires_at = :now,
                    updated_at = :now
                WHERE tenant_id = :tenant_id
                  AND consumer_id = :consumer_id
                  AND fencing_token = :fencing_token
                RETURNING tenant_id, consumer_id, fencing_token
            """)

            result = db.execute(sql, {
                "tenant_id": tenant_id,
                "consumer_id": consumer_id,
                "fencing_token": fencing_token,
                "now": now
            })

            row = result.first()
            if not row:
                logger.warning(
                    f"Token mismatch for {tenant_id}/{consumer_id}: "
                    f"lease not released (token={fencing_token} not found)"
                )
                return False

            logger.info(f"Checkpoint {tenant_id}/{consumer_id}: Lease released (token={fencing_token})")
            return True

        except Exception as e:
            logger.error(f"Failed to release lease for {tenant_id}/{consumer_id}: {e}")
            return False

    def find_expired_leases(
        self,
        db: Session,
        timeout_seconds: Optional[int] = None
    ):
        """
        Find checkpoints with expired leases ready for recovery.

        Args:
            db: Database session
            timeout_seconds: Override default timeout (for recovery) — currently unused

        Returns:
            List of checkpoints with expired leases
        """
        now = utc_now()

        expired = db.query(ProjectionCheckpoint).filter(
            ProjectionCheckpoint.lease_expires_at <= now,
            ProjectionCheckpoint.status == "PROCESSING"
        ).all()

        return expired
