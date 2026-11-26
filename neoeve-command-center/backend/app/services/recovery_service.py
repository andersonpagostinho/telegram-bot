"""Recovery Service: Idempotent retry with lease management and fencing tokens."""

import logging
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from database.models import Execution, ExecutionAttempt, EventIdempotencyKey, utc_now
from database.connection import get_db

logger = logging.getLogger(__name__)


class FailureClassification:
    """Failure classification for retry decisions."""
    TRANSIENT = "TRANSIENT"      # Can retry (network, timeout, temporary)
    PERMANENT = "PERMANENT"      # Cannot retry (invalid command, permission)
    UNKNOWN = "UNKNOWN"          # Needs reconciliation


class RetryPolicy:
    """Configurable retry policy for executions."""

    def __init__(self, max_attempts: int = 3, backoff_ms: int = 1000,
                 backoff_multiplier: float = 2.0, max_backoff_ms: int = 60000):
        self.max_attempts = max_attempts
        self.backoff_ms = backoff_ms
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff_ms = max_backoff_ms

    def should_retry(self, failure_class: str, attempt: int) -> bool:
        """Determine if execution should be retried."""
        if failure_class == FailureClassification.PERMANENT:
            return False
        if failure_class == FailureClassification.UNKNOWN:
            return False  # Requires reconciliation first
        if attempt >= self.max_attempts:
            return False
        return failure_class == FailureClassification.TRANSIENT

    def calculate_delay(self, attempt: int) -> int:
        """Calculate exponential backoff delay in milliseconds."""
        delay = self.backoff_ms * (self.backoff_multiplier ** (attempt - 1))
        return int(min(delay, self.max_backoff_ms))


class RecoveryService:
    """Service for managing execution recovery, retries, and idempotency."""

    def __init__(self, retry_policy: Optional[RetryPolicy] = None, lease_timeout_s: int = 300):
        self.retry_policy = retry_policy or RetryPolicy()
        self.lease_timeout_s = lease_timeout_s

    def find_recoverable(self, db: Session, tenant_id: str) -> List[Execution]:
        """Find executions eligible for recovery.

        Criteria:
        - Status FAILED
        - Lease expired
        - Attempt < max_attempts
        - failure_classification is TRANSIENT
        - next_retry_at <= now
        """
        now = utc_now()

        executions = db.query(Execution).filter(
            Execution.tenant_id == tenant_id,
            Execution.status == "FAILED",
            Execution.failure_classification == FailureClassification.TRANSIENT,
            Execution.attempt_number < Execution.max_attempts,
            (Execution.lease_expires_at.is_(None) | (Execution.lease_expires_at <= now)),
            (Execution.next_retry_at.is_(None) | (Execution.next_retry_at <= now)),
        ).all()

        return executions

    def acquire_lease(self, db: Session, execution_id: str, worker_id: str) -> Tuple[bool, Optional[int]]:
        """Acquire a lease on an execution.

        Returns:
            (success, fencing_token) or (False, None) if lease cannot be acquired
        """
        try:
            execution = db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).with_for_update().first()

            if not execution:
                logger.error(f"Execution {execution_id} not found for lease")
                return False, None

            # Check if another worker has an active lease
            now = utc_now()
            if execution.lease_expires_at:
                # Ensure datetime is aware (handle SQLite naive datetimes)
                lease_expires = execution.lease_expires_at
                if lease_expires.tzinfo is None:
                    lease_expires = lease_expires.replace(tzinfo=timezone.utc)
                if lease_expires > now:
                    logger.warning(f"Execution {execution_id} already leased by {execution.worker_id}")
                    return False, None

            # Acquire lease with new fencing token
            new_fencing_token = execution.fencing_token + 1
            execution.worker_id = worker_id
            execution.fencing_token = new_fencing_token
            execution.lease_expires_at = now + timedelta(seconds=self.lease_timeout_s)
            execution.last_updated_at = now

            db.commit()

            logger.info(f"Execution {execution_id}: Lease acquired by {worker_id}, token={new_fencing_token}")
            return True, new_fencing_token

        except Exception as e:
            logger.error(f"Failed to acquire lease for {execution_id}: {e}")
            db.rollback()
            return False, None

    def release_lease(self, db: Session, execution_id: str, fencing_token: int) -> bool:
        """Release lease on an execution (optional cleanup)."""
        try:
            execution = db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).first()

            if not execution:
                return False

            # Only release if token matches (prevent old workers from releasing)
            if execution.fencing_token != fencing_token:
                logger.warning(f"Token mismatch for {execution_id}: {fencing_token} vs {execution.fencing_token}")
                return False

            execution.lease_expires_at = utc_now()
            execution.last_updated_at = utc_now()
            db.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to release lease for {execution_id}: {e}")
            db.rollback()
            return False

    def classify_failure(self, error_message: str) -> str:
        """Classify failure to determine retry strategy."""
        if not error_message:
            return FailureClassification.UNKNOWN

        error_lower = error_message.lower()

        # TRANSIENT patterns
        transient_patterns = [
            "timeout", "timeout_seconds", "connection", "network", "temporary",
            "connection_reset", "connection_timeout", "broken pipe", "refused",
            "unable to connect", "no route to host"
        ]

        # PERMANENT patterns
        permanent_patterns = [
            "permission denied", "access denied", "unauthorized", "forbidden",
            "not found", "invalid command", "command not found", "not in whitelist",
            "blocked by security"
        ]

        for pattern in permanent_patterns:
            if pattern in error_lower:
                return FailureClassification.PERMANENT

        for pattern in transient_patterns:
            if pattern in error_lower:
                return FailureClassification.TRANSIENT

        # Default to UNKNOWN for unclassified errors
        return FailureClassification.UNKNOWN

    def schedule_retry(self, db: Session, execution_id: str, fencing_token: int):
        """Schedule an execution for retry.

        Increments attempt_number and calculates next retry time.

        Returns:
            (success, next_retry_at) or (False, None) if failed
        """
        try:
            execution = db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).first()

            if not execution:
                return False, None

            # Validate fencing token
            if execution.fencing_token != fencing_token:
                logger.warning(f"Fencing token mismatch for {execution_id}: {fencing_token} vs {execution.fencing_token}")
                return False, None

            # Check if retryable
            if not self.retry_policy.should_retry(execution.failure_classification, execution.attempt_number):
                execution.status = "FAILED_PERMANENT"
                logger.info(f"Execution {execution_id}: Marked as FAILED_PERMANENT")
                execution.last_updated_at = utc_now()
                db.commit()
                return True, None
            else:
                # Schedule retry
                next_attempt = execution.attempt_number + 1
                delay_ms = self.retry_policy.calculate_delay(next_attempt)
                next_retry_at = utc_now() + timedelta(milliseconds=delay_ms)

                execution.status = "QUEUED"
                execution.attempt_number = next_attempt
                execution.next_retry_at = next_retry_at
                execution.failure_classification = None
                execution.last_failure_reason = None

                logger.info(f"Execution {execution_id}: Scheduled for retry attempt {next_attempt}, delay={delay_ms}ms")

            execution.last_updated_at = utc_now()
            db.commit()
            return True, next_retry_at if execution.status == "QUEUED" else None

        except Exception as e:
            logger.error(f"Failed to schedule retry for {execution_id}: {e}")
            db.rollback()
            return False, None

    def update_with_fence(self, db: Session, execution_id: str, fencing_token: int,
                         status: str, result: Optional[dict] = None,
                         error: Optional[str] = None) -> bool:
        """Update execution with fencing token validation.

        Only allows updates if fencing token matches.
        """
        try:
            execution = db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).first()

            if not execution:
                return False

            # Validate fencing token
            if execution.fencing_token != fencing_token:
                logger.warning(f"Fencing token mismatch for {execution_id}: {fencing_token} vs {execution.fencing_token}")
                return False

            # Update execution
            execution.status = status
            execution.result = result
            execution.error = error
            execution.completed_at = utc_now()
            execution.last_updated_at = utc_now()

            # Classify failure if status is FAILED
            if status == "FAILED" and error:
                failure_class = self.classify_failure(error)
                execution.failure_classification = failure_class
                execution.last_failure_reason = error

            db.commit()
            logger.info(f"Execution {execution_id}: Updated to {status} with token={fencing_token}")
            return True

        except Exception as e:
            logger.error(f"Failed to update execution {execution_id}: {e}")
            db.rollback()
            return False

    def record_attempt(self, db: Session, execution_id: str, attempt_number: int,
                      fencing_token: int, worker_id: str, status: str,
                      duration_ms: Optional[int] = None, error: Optional[str] = None,
                      result: Optional[dict] = None, tenant_id: Optional[str] = None) -> bool:
        """Record an execution attempt for audit trail."""
        try:
            attempt = ExecutionAttempt(
                execution_id=execution_id,
                attempt_number=attempt_number,
                worker_id=worker_id,
                fencing_token=fencing_token,
                status=status,
                duration_ms=duration_ms,
                error_message=error,
                result=result,
                tenant_id=tenant_id or "unknown"
            )

            if status == "FAILED":
                attempt.failure_classification = self.classify_failure(error or "")

            db.add(attempt)
            db.commit()

            logger.info(f"Execution {execution_id}: Attempt {attempt_number} recorded")
            return True

        except Exception as e:
            logger.error(f"Failed to record attempt for {execution_id}: {e}")
            db.rollback()
            return False

    @staticmethod
    def generate_idempotency_key(event_type: str, execution_id: str, attempt_number: int) -> str:
        """Generate deterministic idempotency key for event deduplication."""
        combined = f"{event_type}:{execution_id}:{attempt_number}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def is_event_processed(self, db: Session, idempotency_key: str) -> bool:
        """Check if an event has already been processed."""
        result = db.query(EventIdempotencyKey).filter(
            EventIdempotencyKey.idempotency_key == idempotency_key
        ).first()

        return result is not None

    def mark_event_processed(self, db: Session, idempotency_key: str, event_type: str,
                            execution_id: str, attempt_number: int, tenant_id: str) -> bool:
        """Mark an event as processed for idempotency."""
        try:
            event_key = EventIdempotencyKey(
                idempotency_key=idempotency_key,
                event_type=event_type,
                execution_id=execution_id,
                attempt_number=attempt_number,
                tenant_id=tenant_id
            )

            db.add(event_key)
            db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to mark event as processed: {e}")
            db.rollback()
            return False
