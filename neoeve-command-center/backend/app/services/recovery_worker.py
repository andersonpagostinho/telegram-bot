"""Recovery Worker: background service for automatic execution recovery."""

import logging
import threading
import time
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Tenant, utc_now
from app.services.recovery_service import RecoveryService, RetryPolicy

logger = logging.getLogger(__name__)


class RecoveryWorker:
    """Background worker for automatic execution recovery on transient failures."""

    def __init__(self, recovery_service: RecoveryService, check_interval_seconds: int = 30):
        """
        Initialize recovery worker.

        Args:
            recovery_service: RecoveryService instance
            check_interval_seconds: How often to check for recoverable executions
        """
        self.recovery_service = recovery_service
        self.check_interval = check_interval_seconds
        self.enabled = False  # IMPORTANTE: Desabilitado até validação PostgreSQL
        self._thread = None
        self._stop_event = threading.Event()
        self.worker_id = f"recovery-worker-{os.getpid()}"

    def start(self) -> None:
        """Start recovery worker in background thread."""
        if self.enabled:
            logger.info(f"Recovery worker starting (check interval: {self.check_interval}s)")
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._recovery_loop, daemon=True)
            self._thread.start()
        else:
            logger.warning("Recovery worker is DISABLED (waiting for PostgreSQL validation)")

    def stop(self) -> None:
        """Stop recovery worker gracefully."""
        logger.info("Recovery worker stopping...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Recovery worker stopped")

    def _recovery_loop(self) -> None:
        """Main recovery loop: find recoverable executions and retry them."""
        while not self._stop_event.is_set():
            try:
                self._recovery_cycle()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Recovery worker error: {e}", exc_info=True)
                time.sleep(60)  # Back off on error

    def _recovery_cycle(self) -> None:
        """Single recovery cycle: iterate tenants, find recoverable, retry."""
        db = next(get_db())

        try:
            # Get all active tenants
            tenants = db.query(Tenant).all()

            for tenant in tenants:
                try:
                    self._recover_tenant(db, tenant.tenant_id)
                except Exception as e:
                    logger.error(f"Error recovering tenant {tenant.tenant_id}: {e}")
        finally:
            db.close()

    def _recover_tenant(self, db: Session, tenant_id: str) -> None:
        """Recover all recoverable executions for a tenant."""
        # Find executions eligible for recovery
        recoverable = self.recovery_service.find_recoverable(db, tenant_id)

        if recoverable:
            logger.info(f"Found {len(recoverable)} recoverable executions for tenant {tenant_id}")

        for execution in recoverable:
            try:
                self._retry_execution(db, execution, tenant_id)
            except Exception as e:
                logger.error(
                    f"Error recovering execution {execution.execution_id}: {e}"
                )

    def _retry_execution(self, db: Session, execution, tenant_id: str) -> None:
        """Retry a single execution."""
        execution_id = execution.execution_id

        # Try to acquire lease
        success, fencing_token = self.recovery_service.acquire_lease(
            db, execution_id, self.worker_id
        )

        if not success:
            logger.debug(f"Execution {execution_id}: Could not acquire lease (another worker has it)")
            return

        try:
            logger.info(f"Execution {execution_id}: Acquired lease with token {fencing_token}")

            # Validate fencing token
            if execution.fencing_token >= fencing_token:
                logger.warning(
                    f"Execution {execution_id}: Fencing token mismatch "
                    f"(execution={execution.fencing_token}, acquired={fencing_token})"
                )
                return

            # TODO: Call back to AgentRuntime to retry
            # This is where the actual retry happens
            # For now, this is a placeholder

            logger.info(
                f"Execution {execution_id}: Retry would be executed here "
                f"(attempt={execution.attempt_number + 1})"
            )

        finally:
            # Always release lease
            self.recovery_service.release_lease(db, execution_id, fencing_token)
            logger.debug(f"Execution {execution_id}: Released lease")
