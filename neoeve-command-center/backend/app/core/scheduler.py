"""
Scheduler — Background jobs for Outbox Publisher and Recovery.

ETAPA 4: Scheduler Integration
Responsibilities:
- Publish pending Outbox events to Event Bus
- Recover expired PROCESSING events
- Handle retry and error recovery
- Prevent concurrent execution (single-threaded)
- Support graceful shutdown
"""

import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from threading import Thread, Event
from sqlalchemy.orm import sessionmaker, Session

from app.services.event_bus import (
    publish_outbox_event,
    get_pending_outbox_events,
    recover_expired_processing_events,
)
from app.services.projection_checkpoint_lease_service import ProjectionCheckpointLeaseService
from database.connection import SessionLocal as PGSessionLocal
from database.models import ApprovalOutbox, ProjectionCheckpoint, utc_now

logger = logging.getLogger(__name__)


class ApprovalScheduler:
    """
    Scheduler for Approval Workflow automation.

    Executes in background thread:
    - Publishes pending Outbox records to Event Bus (SQLite)
    - Recovers expired PROCESSING events
    """

    def __init__(
        self,
        interval_seconds: int = 10,
        outbox_batch_size: int = 10,
        projection_batch_size: int = 50,
        max_processing_age_seconds: int = 300,
    ):
        """
        Initialize scheduler.

        Args:
            interval_seconds: Run interval for background jobs (default 10s)
            outbox_batch_size: Max Outbox events to publish per batch
            projection_batch_size: Max Event Bus events to project per batch
            max_processing_age_seconds: Timeout for recovering PROCESSING events
        """
        self.interval_seconds = interval_seconds
        self.outbox_batch_size = outbox_batch_size
        self.projection_batch_size = projection_batch_size
        self.max_processing_age_seconds = max_processing_age_seconds

        self._stop_event = Event()
        self._thread: Optional[Thread] = None

        # Metrics
        self._metrics = {
            "total_runs": 0,
            "outbox_published": 0,
            "outbox_failed": 0,
            "events_recovered": 0,
            "checkpoints_recovered": 0,  # Gate A: ProjectionCheckpoint recovery
            "events_projected": 0,
            "errors": 0,
            "last_run_at": None,
        }

    def start(self):
        """Start background scheduler thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Scheduler already running")
            return

        logger.info(f"Starting Approval Scheduler (interval={self.interval_seconds}s)")
        self._stop_event.clear()
        self._thread = Thread(target=self._run, daemon=False)
        self._thread.start()

    def stop(self):
        """Stop scheduler gracefully."""
        logger.info("Stopping Approval Scheduler...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            logger.info("Scheduler stopped")

    def _run(self):
        """Background thread main loop."""

        while not self._stop_event.is_set():
            try:
                self._metrics["total_runs"] += 1
                self._metrics["last_run_at"] = datetime.now(timezone.utc)

                # Phase 1: Publish pending Outbox events
                self._publish_outbox_batch()

                # Phase 2: Recover expired PROCESSING events
                self._recover_expired_events()

                # Sleep until next cycle
                self._stop_event.wait(self.interval_seconds)

            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                self._metrics["errors"] += 1
                # Wait before retrying
                self._stop_event.wait(2)

    def _publish_outbox_batch(self):
        """Publish pending Outbox events (all tenants/projects)."""
        db = PGSessionLocal()
        try:
            # Get all pending Outbox records (grouped by tenant/project)
            query = db.query(
                ApprovalOutbox.tenant_id,
                ApprovalOutbox.project_id
            ).filter(
                ApprovalOutbox.status == "PENDING"
            ).distinct()

            for tenant_id, project_id in query.all():
                pending = get_pending_outbox_events(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    limit=self.outbox_batch_size,
                )

                for outbox in pending:
                    try:
                        result = publish_outbox_event(
                            event_id=outbox.event_id,
                            approval_id=outbox.approval_id,
                            validation_id=outbox.validation_id,
                            event_type=outbox.event_type,
                            tenant_id=outbox.tenant_id,
                            project_id=outbox.project_id,
                            actor_id=outbox.actor_id,
                            payload=outbox.payload if isinstance(outbox.payload, dict) else {},
                            idempotency_key=outbox.idempotency_key,
                        )
                        if result:
                            self._metrics["outbox_published"] += 1
                            logger.info(f"Published Outbox event: {outbox.event_id}")
                        else:
                            self._metrics["outbox_failed"] += 1
                    except Exception as e:
                        logger.error(f"Failed to publish Outbox event {outbox.event_id}: {e}")
                        self._metrics["outbox_failed"] += 1

        except Exception as e:
            logger.error(f"Error in publish_outbox_batch: {e}")
        finally:
            db.close()

    def _recover_expired_events(self):
        """Recover events stuck in PROCESSING state (Approval Outbox + Gate A ProjectionCheckpoint)."""
        db = PGSessionLocal()
        try:
            # Phase A: Recover ApprovalOutbox PROCESSING events
            query = db.query(
                ApprovalOutbox.tenant_id,
                ApprovalOutbox.project_id
            ).distinct()

            for tenant_id, project_id in query.all():
                try:
                    recovered = recover_expired_processing_events(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        max_processing_age_seconds=self.max_processing_age_seconds,
                    )
                    if recovered > 0:
                        self._metrics["events_recovered"] += recovered
                        logger.info(f"Recovered {recovered} PROCESSING events ({tenant_id}/{project_id})")
                except Exception as e:
                    logger.error(f"Failed to recover events ({tenant_id}/{project_id}): {e}")

            # Phase B: Recover ProjectionCheckpoint with expired leases (Gate A)
            self._recover_expired_projection_checkpoints(db)

        except Exception as e:
            logger.error(f"Error in recover_expired_events: {e}")
        finally:
            db.close()

    def _recover_expired_projection_checkpoints(self, db: Session):
        """
        Recover ProjectionCheckpoint instances with expired leases (Gate A).

        When a checkpoint's lease expires, the worker holding it has stopped responding.
        Recovery resets the checkpoint to IDLE, allowing a new worker to process it.

        Guarantees:
        - Atomic: lease expiration checked and checkpoint reset in same transaction
        - Idempotent: repeated calls don't corrupt state
        - Isolated: multi-tenant checksums remain independent
        - Fenced: worker with old token cannot commit after recovery
        """
        try:
            lease_service = ProjectionCheckpointLeaseService()

            # Find all checkpoints with expired leases
            expired_checkpoints = lease_service.find_expired_leases(db)

            if not expired_checkpoints:
                return

            logger.info(f"Found {len(expired_checkpoints)} ProjectionCheckpoint(s) with expired leases")

            for checkpoint in expired_checkpoints:
                try:
                    # Atomically reset checkpoint for recovery:
                    # 1. Verify lease is still expired (re-check for safety)
                    now = utc_now()
                    if checkpoint.lease_expires_at and checkpoint.lease_expires_at > now:
                        logger.debug(f"Checkpoint {checkpoint.tenant_id}/{checkpoint.consumer_id}: lease no longer expired, skipping")
                        continue

                    # 2. Reset to IDLE, clear worker, increment error count
                    checkpoint.status = "IDLE"
                    checkpoint.worker_id = None  # Clear ownership
                    checkpoint.lease_expires_at = None  # Clear lease
                    # NOTE: fencing_token is intentionally NOT reset to maintain monotonic invariant
                    # (1 → 2 → 3...). The token is only used to fence old workers, not to control state.
                    checkpoint.error_count = checkpoint.error_count + 1 if checkpoint.error_count else 1
                    checkpoint.updated_at = now

                    db.flush()  # Persist within current transaction

                    self._metrics["checkpoints_recovered"] += 1
                    logger.info(
                        f"Recovered ProjectionCheckpoint {checkpoint.tenant_id}/{checkpoint.consumer_id}: "
                        f"status=IDLE, error_count={checkpoint.error_count}, "
                        f"worker_id=None (fencing token invalidated)"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to recover ProjectionCheckpoint {checkpoint.tenant_id}/{checkpoint.consumer_id}: {e}",
                        exc_info=True
                    )

            # Commit all checkpoint updates as one batch
            db.commit()

        except Exception as e:
            logger.error(f"Error in recover_expired_projection_checkpoints: {e}", exc_info=True)
            # Don't re-raise; let scheduler continue

    def get_metrics(self) -> dict:
        """Get scheduler metrics."""
        return self._metrics.copy()


# Global scheduler instance
_scheduler: Optional[ApprovalScheduler] = None


def init_scheduler(
    interval_seconds: int = 10,
    outbox_batch_size: int = 10,
    projection_batch_size: int = 50,
) -> ApprovalScheduler:
    """Initialize and start the approval scheduler."""
    global _scheduler
    _scheduler = ApprovalScheduler(
        interval_seconds=interval_seconds,
        outbox_batch_size=outbox_batch_size,
        projection_batch_size=projection_batch_size,
    )
    _scheduler.start()
    return _scheduler


def get_scheduler() -> Optional[ApprovalScheduler]:
    """Get the current scheduler instance."""
    return _scheduler


def stop_scheduler():
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None
