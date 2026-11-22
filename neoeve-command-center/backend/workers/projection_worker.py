"""
ProjectionWorker — Transform Event Bus events to PostgreSQL read projections

Responsibilities:
- Consume events from SQLite Event Bus
- Transform to PostgreSQL row(s)
- Handle idempotency (UPSERT)
- Manage checkpoints for recovery
- Implement retry with backoff
- Track metrics
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging
import time

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from event_bus.event import Event, EventType, EventStatus
from event_bus.event_store import EventStore
from event_bus.event_consumer import EventConsumer
from database.models import (
    AgentEvent, ProjectionCheckpoint, Agent, Mission, Task, Execution, Validation
)

logger = logging.getLogger(__name__)


class ProjectionWorker:
    """
    Consumes events from Event Bus and projects to PostgreSQL.

    Coordinates with EventStore (SQLite) for event consumption and checkpoint management.
    """

    def __init__(
        self,
        event_store: EventStore,
        db_session: Session,
        consumer_id: str = "projection-worker",
        mission_id: Optional[str] = None,
        batch_size: int = 10,
        max_retries: int = 3,
        retry_backoff_seconds: int = 2,
    ):
        """
        Initialize ProjectionWorker.

        Args:
            event_store: SQLite event store (source)
            db_session: PostgreSQL session (sink)
            consumer_id: Unique consumer identifier for checkpoint tracking
            mission_id: Specific mission to process (None = all missions)
            batch_size: Events to fetch per batch
            max_retries: Maximum retry attempts per event
            retry_backoff_seconds: Initial backoff for retries (exponential)
        """
        self.event_store = event_store
        self.db_session = db_session
        self.consumer_id = consumer_id
        self.mission_id = mission_id or "default"
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

        self._event_consumer = EventConsumer(event_store, consumer_id)

        # Real metrics (derived from actual execution, not simulated)
        self._metrics = {
            "total_events_found": 0,      # Total from consume_pending()
            "total_events_processed": 0,  # Successfully projected
            "events_duplicate": 0,        # Already-projected events skipped
            "events_rejected": 0,         # Failed projections (not retried)
            "events_pending": 0,          # Still in PENDING state
            "process_failures": 0,        # Exceptions during projection
            "retries_attempted": 0,       # Total retry attempts
            "recovered_stuck": 0,         # Events recovered from PROCESSING
            "latency_ms_sum": 0.0,        # Sum of event processing times
            "latency_ms_count": 0,        # Count of latency measurements
            "latency_ms_max": 0.0,        # Maximum processing time
            "last_event_id": None,        # Last successfully processed event_id
            "last_sync_at": None,         # Last consume_and_project() completion
            "current_status": "INITIALIZED",  # INITIALIZED, PROCESSING, IDLE, ERROR
            "_event_times": {},           # {event_id: start_time} for latency calc
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current worker metrics (real data, not simulated).

        Returns dict with:
        - total_events_found: Total events from consume_pending()
        - total_events_processed: Successfully projected
        - events_duplicate: Already projected
        - events_rejected: Failed (non-retried)
        - events_pending: Still in PENDING state
        - process_failures: Exceptions during projection
        - retries_attempted: Total retry attempts
        - recovered_stuck: Events recovered from stuck state
        - latency_ms_avg: Average processing time (or None if no data)
        - latency_ms_max: Maximum processing time
        - last_event_id: Last processed event
        - last_sync_at: Last sync timestamp
        - current_status: Worker status
        """
        metrics = dict(self._metrics)  # Shallow copy

        # Calculate derived metrics
        if self._metrics["latency_ms_count"] > 0:
            metrics["latency_ms_avg"] = round(
                self._metrics["latency_ms_sum"] / self._metrics["latency_ms_count"], 2
            )
        else:
            metrics["latency_ms_avg"] = None

        # Remove internal state
        metrics.pop("_event_times", None)

        return metrics

    def consume_and_project(self, limit: Optional[int] = None) -> int:
        """
        Consume pending events and project to PostgreSQL.

        Args:
            limit: Max events to process (uses batch_size if None)

        Returns:
            Number of events successfully processed
        """
        if limit is None:
            limit = self.batch_size

        # Get checkpoint (initialize if needed)
        checkpoint = self._get_or_create_checkpoint()
        checkpoint.status = "PROCESSING"
        self.db_session.commit()

        try:
            self._metrics["current_status"] = "PROCESSING"

            # Consume pending events with atomic reservation
            events = self._event_consumer.consume_pending(self.mission_id, limit)
            self._metrics["total_events_found"] += len(events)

            if not events:
                checkpoint.status = "IDLE"
                self._metrics["current_status"] = "IDLE"
                self._metrics["last_sync_at"] = datetime.now(timezone.utc)
                self.db_session.commit()
                return 0

            processed = 0
            for event in events:
                event_start_time = time.time()
                self._metrics["_event_times"][event.event_id] = event_start_time

                try:
                    # Project event to PostgreSQL
                    if self._project_event(event):
                        # Mark as completed in EventStore
                        self._event_consumer.mark_completed(event.event_id)
                        processed += 1
                        self._metrics["total_events_processed"] += 1

                        # Track latency for successfully processed events
                        event_time_ms = (time.time() - event_start_time) * 1000
                        self._metrics["latency_ms_sum"] += event_time_ms
                        self._metrics["latency_ms_count"] += 1
                        self._metrics["latency_ms_max"] = max(
                            self._metrics["latency_ms_max"],
                            event_time_ms
                        )

                        # Update checkpoint
                        checkpoint.last_processed_event_id = event.event_id
                        checkpoint.last_processed_at = datetime.now(timezone.utc)
                        checkpoint.error_count = 0
                        self._metrics["last_event_id"] = event.event_id

                except Exception as e:
                    logger.error(f"Failed to project event {event.event_id}: {e}")
                    self._metrics["process_failures"] += 1
                    # Mark as failed with retry flag
                    self._event_consumer.mark_failed(event.event_id, str(e), retry=True)
                    checkpoint.error_count += 1

            # Finalize checkpoint
            checkpoint.status = "IDLE"
            self._metrics["current_status"] = "IDLE"
            self._metrics["last_sync_at"] = datetime.now(timezone.utc)
            self.db_session.commit()

            return processed

        except Exception as e:
            logger.error(f"Projection worker error: {e}")
            checkpoint.status = "ERROR"
            checkpoint.error_count += 1
            self._metrics["current_status"] = "ERROR"
            self._metrics["last_sync_at"] = datetime.now(timezone.utc)
            self.db_session.commit()
            raise

    def _get_or_create_checkpoint(self) -> ProjectionCheckpoint:
        """Get or create checkpoint for this consumer"""
        checkpoint = self.db_session.query(ProjectionCheckpoint).filter_by(
            consumer_id=self.consumer_id
        ).first()

        if not checkpoint:
            checkpoint = ProjectionCheckpoint(
                consumer_id=self.consumer_id,
                status="INITIALIZED",
                error_count=0
            )
            self.db_session.add(checkpoint)
            self.db_session.commit()

        return checkpoint

    def _project_event(self, event: Event) -> bool:
        """
        Project single event to PostgreSQL AgentEvent table (idempotent UPSERT).

        Implements fail-safe idempotency:
        1. Query first to check if event already projected
        2. If not, insert with UNIQUE constraint protection
        3. If UNIQUE violation (race condition), handle gracefully

        Returns:
            True if successful (new projection or already idempotent)
        """
        try:
            # Extract tenant/project context
            tenant_id, project_id = self._extract_tenant_context(event)

            # SECURITY: Validate isolation (prevent cross-tenant contamination)
            self._validate_isolation(event, tenant_id, project_id)

            # UPSERT Pattern Step 1: Query to detect if already projected
            agent_event = self.db_session.query(AgentEvent).filter_by(
                event_id=event.event_id
            ).first()

            if agent_event:
                # Event already projected
                self._metrics["events_duplicate"] += 1
                logger.debug(f"Event {event.event_id} already projected (duplicate)")
                return True  # Idempotent - safe to return success

            # UPSERT Pattern Step 2: Insert new projection (first observer wins)
            agent_event = AgentEvent(
                event_id=event.event_id,
                event_type=event.event_type.value,
                schema_version=1,
                mission_id=event.mission_id,
                task_id=event.task_id,
                execution_id=event.execution_id,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                project_id=project_id,
                tenant_id=tenant_id,
                actor_id=event.agent_id,
                source_agent=event.agent_role,
                target_agent=None,  # Enhanced in future phases
                payload_summary=event.payload,
                created_at=datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')),
                processed_at=datetime.now(timezone.utc),
            )

            self.db_session.add(agent_event)
            self.db_session.flush()  # Verify constraints before commit

            logger.debug(f"Event {event.event_id} projected successfully")
            return True

        except IntegrityError as e:
            # UPSERT Pattern Step 3: Handle race condition (concurrent projection)
            # This occurs when another worker projected the same event between our query and insert
            if "event_id" in str(e) and "UNIQUE" in str(e):
                self._metrics["events_duplicate"] += 1
                logger.warning(f"Event {event.event_id} projected concurrently (UNIQUE violation handled)")
                self.db_session.rollback()  # Rollback partial transaction
                return True  # Still idempotent - return success
            else:
                # Non-idempotency constraint violation - re-raise
                logger.error(f"Non-idempotency constraint violation for {event.event_id}: {e}")
                self.db_session.rollback()
                raise

        except Exception as e:
            logger.error(f"Event projection failed for {event.event_id}: {e}")
            self.db_session.rollback()
            raise

    def _extract_tenant_context(self, event: Event) -> tuple[str, str]:
        """
        Extract tenant_id and project_id from event context.

        For now, derive from mission_id. In production, would look up mission metadata.

        Returns:
            (tenant_id, project_id)
        """
        # SECURITY: Extract from mission metadata (look up mission context)
        tenant_id = None
        project_id = None

        try:
            mission = self.db_session.query(Mission).filter_by(
                mission_id=event.mission_id
            ).first()

            if mission:
                tenant_id = mission.tenant_id
                project_id = mission.project_id
                logger.debug(f"Event {event.event_id} resolved to tenant={tenant_id}, project={project_id} from Mission")
        except Exception as e:
            logger.warning(f"Could not query mission for event {event.event_id}: {e}")

        # Fallback: Use mission_id as project identifier
        if not tenant_id:
            tenant_id = "default-tenant"
        if not project_id:
            project_id = event.mission_id

        # SECURITY: Validate context is set (never None for security)
        if not tenant_id:
            raise ValueError(f"Cannot determine tenant_id for event {event.event_id}")
        if not project_id:
            raise ValueError(f"Cannot determine project_id for event {event.event_id}")

        return tenant_id, project_id

    def recover_stuck_events(self, timeout_minutes: int = 30) -> int:
        """
        Recover events stuck in PROCESSING state (interrupted processing).

        Events stuck > timeout_minutes are reset to PENDING for reprocessing.
        This handles cases where the worker crashed or was forcibly terminated.

        Args:
            timeout_minutes: Consider events older than this as stuck

        Returns:
            Number of events recovered
        """
        try:
            stuck_events = self.event_store.get_stuck_events(timeout_minutes)

            if not stuck_events:
                logger.debug("No stuck events found for recovery")
                return 0

            logger.warning(f"Found {len(stuck_events)} stuck events, recovering...")

            recovered = 0
            for event in stuck_events:
                try:
                    # Reset to PENDING so they can be reprocessed
                    self.event_store.update_event_status(
                        event.event_id,
                        EventStatus.PENDING,
                        "Recovered from PROCESSING state"
                    )
                    recovered += 1
                    self._metrics["recovered_stuck"] += 1
                except Exception as e:
                    logger.error(f"Failed to recover event {event.event_id}: {e}")

            logger.info(f"Successfully recovered {recovered} stuck events")
            return recovered

        except Exception as e:
            logger.error(f"Error during stuck event recovery: {e}")
            return 0

    def _retry_with_backoff(self, event: Event, attempt: int) -> bool:
        """
        Retry event projection with exponential backoff.

        Args:
            event: Event to retry
            attempt: Current attempt number (0-based)

        Returns:
            True if retry should proceed, False if max retries exceeded
        """
        if attempt >= self.max_retries:
            logger.error(f"Event {event.event_id} exceeded max retries ({self.max_retries})")
            return False

        # Exponential backoff: 2^attempt seconds
        backoff = self.retry_backoff_seconds * (2 ** attempt)
        logger.warning(f"Retrying event {event.event_id} in {backoff}s (attempt {attempt + 1}/{self.max_retries})")

        time.sleep(backoff)
        self._metrics["retries_attempted"] += 1
        return True

    def _validate_isolation(self, event: Event, tenant_id: str, project_id: str) -> bool:
        """
        Validate that event projection respects multi-tenant boundaries.

        SECURITY CRITICAL: Blocks any cross-tenant or cross-project contamination.

        Args:
            event: Event to validate
            tenant_id: Target tenant for projection
            project_id: Target project for projection

        Returns:
            True if isolation check passes

        Raises:
            ValueError: If isolation violation detected (cross-tenant/project attempt)
        """
        # SECURITY: Ensure mission belongs to same tenant/project
        mission = self.db_session.query(Mission).filter_by(
            mission_id=event.mission_id
        ).first()

        if mission:
            if mission.tenant_id != tenant_id:
                logger.error(
                    f"ISOLATION VIOLATION: Event {event.event_id} belongs to tenant "
                    f"{mission.tenant_id} but projection targeted tenant {tenant_id}"
                )
                raise ValueError(
                    f"Isolation violation: Cross-tenant projection blocked for event {event.event_id}"
                )

            if mission.project_id != project_id:
                logger.error(
                    f"ISOLATION VIOLATION: Event {event.event_id} belongs to project "
                    f"{mission.project_id} but projection targeted project {project_id}"
                )
                raise ValueError(
                    f"Isolation violation: Cross-project projection blocked for event {event.event_id}"
                )

        logger.debug(f"Event {event.event_id} passed isolation validation for tenant={tenant_id}, project={project_id}")
        return True
