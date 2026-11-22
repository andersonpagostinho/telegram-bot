"""
ProjectionWorker — Transform Event Bus events to PostgreSQL read projections

Responsibilities:
- Consume events from SQLite Event Bus
- Transform to PostgreSQL row(s)
- Handle idempotency (UPSERT)
- Manage checkpoints for recovery
- Track metrics
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

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
    ):
        """
        Initialize ProjectionWorker.

        Args:
            event_store: SQLite event store (source)
            db_session: PostgreSQL session (sink)
            consumer_id: Unique consumer identifier for checkpoint tracking
            mission_id: Specific mission to process (None = all missions)
            batch_size: Events to fetch per batch
        """
        self.event_store = event_store
        self.db_session = db_session
        self.consumer_id = consumer_id
        self.mission_id = mission_id or "default"
        self.batch_size = batch_size

        self._event_consumer = EventConsumer(event_store, consumer_id)
        self._metrics = {
            "processed": 0,
            "duplicates": 0,
            "failures": 0,
            "last_processed": None,
        }

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
            # Consume pending events with atomic reservation
            events = self._event_consumer.consume_pending(self.mission_id, limit)

            if not events:
                checkpoint.status = "IDLE"
                self.db_session.commit()
                return 0

            processed = 0
            for event in events:
                try:
                    # Project event to PostgreSQL
                    if self._project_event(event):
                        # Mark as completed in EventStore
                        self._event_consumer.mark_completed(event.event_id)
                        processed += 1

                        # Update checkpoint
                        checkpoint.last_processed_event_id = event.event_id
                        checkpoint.last_processed_at = datetime.now(timezone.utc)
                        checkpoint.error_count = 0
                except Exception as e:
                    logger.error(f"Failed to project event {event.event_id}: {e}")
                    self._metrics["failures"] += 1
                    # Mark as failed with retry flag
                    self._event_consumer.mark_failed(event.event_id, str(e), retry=True)
                    checkpoint.error_count += 1

            # Finalize checkpoint
            checkpoint.status = "IDLE"
            self.db_session.commit()

            self._metrics["processed"] += processed
            return processed

        except Exception as e:
            logger.error(f"Projection worker error: {e}")
            checkpoint.status = "ERROR"
            checkpoint.error_count += 1
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

            # UPSERT Pattern Step 1: Query to detect if already projected
            agent_event = self.db_session.query(AgentEvent).filter_by(
                event_id=event.event_id
            ).first()

            if agent_event:
                # Event already projected
                self._metrics["duplicates"] += 1
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
                self._metrics["duplicates"] += 1
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
        # Placeholder: In production, would query missions table or event metadata
        # For now, use mission_id as both tenant and project identifier
        tenant_id = "default-tenant"
        project_id = event.mission_id

        return tenant_id, project_id
