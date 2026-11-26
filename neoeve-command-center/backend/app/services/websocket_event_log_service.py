"""
WebSocket Event Log Service for reconnection recovery.

ETAPA 5: Event Recovery mechanism

Tracks events sent over WebSocket and allows clients to recover missed events
when reconnecting after network interruptions.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import WebSocketEventLog

logger = logging.getLogger(__name__)


class WebSocketEventLogService:
    """
    Service to log and retrieve WebSocket events for recovery.

    Features:
    - Log events with sequence numbers for client cursors
    - Query missed events for reconnecting clients
    - Automatic cleanup of old events (TTL)
    - Multi-tenant isolation
    """

    def __init__(self, event_ttl_hours: int = 24):
        """
        Initialize event log service.

        Args:
            event_ttl_hours: Time to live for events before cleanup (default: 24 hours)
        """
        self.event_ttl_hours = event_ttl_hours

    def log_event(
        self,
        db: Session,
        event_id: str,
        event_type: str,
        tenant_id: str,
        project_id: str,
        payload: dict,
    ) -> Optional[int]:
        """
        Log an event to the websocket event log.

        ETAPA 5: Persist events for recovery

        TRANSACTIONAL DESIGN:
        - This method flushes (not commits) to allow caller to control transaction boundary
        - Caller (ProjectionWorker.consume_and_project) manages the atomic commit
        - Atomicity: AgentEvent + WebSocketEventLog + ProcessedEvent all commit together
        - Idempotency: UNIQUE constraint on event_id prevents duplicates

        Args:
            db: Database session
            event_id: Unique event identifier
            event_type: Type of event (e.g., "MISSION_UPDATED")
            tenant_id: Tenant/Organization ID (multi-tenant isolation)
            project_id: Project ID
            payload: Event data to send to clients

        Returns:
            Sequence number of logged event, or None if failed
        """
        try:
            # Check if event already exists (idempotency)
            existing = db.query(WebSocketEventLog).filter_by(
                event_id=event_id
            ).first()

            if existing:
                logger.debug(
                    f"WebSocket event already logged (idempotent): event_id={event_id} "
                    f"sequence={existing.sequence}"
                )
                return existing.sequence

            # Create new event
            now = datetime.now(timezone.utc)
            ttl_expires = now + timedelta(hours=self.event_ttl_hours)

            event = WebSocketEventLog(
                event_id=event_id,
                event_type=event_type,
                tenant_id=tenant_id,
                project_id=project_id,
                payload=payload,
                created_at=now,
                ttl_expires_at=ttl_expires,
            )

            db.add(event)
            db.flush()  # Validate constraints but don't commit (let caller control transaction)

            logger.debug(
                f"WebSocket event prepared for logging: event_id={event_id} "
                f"type={event_type} tenant={tenant_id} sequence={event.sequence}"
            )

            return event.sequence

        except Exception as e:
            # Don't rollback here - let caller handle transaction state
            logger.error(f"Failed to prepare WebSocket event {event_id}: {e}")
            raise  # Propagate to caller for proper transaction handling

    def get_missed_events(
        self,
        db: Session,
        tenant_id: str,
        cursor: Optional[int] = None,
        limit: int = 100,
    ) -> List[WebSocketEventLog]:
        """
        Get events a client missed since reconnection.

        ETAPA 5: Event Recovery for reconnecting clients

        Args:
            db: Database session
            tenant_id: Tenant ID (multi-tenant isolation)
            cursor: Last sequence number seen by client (None = all recent events)
            limit: Max events to return (default: 100)

        Returns:
            List of events after cursor, ordered by sequence
        """
        try:
            query = db.query(WebSocketEventLog).filter(
                WebSocketEventLog.tenant_id == tenant_id
            )

            if cursor is not None:
                # Get events after this sequence
                query = query.filter(WebSocketEventLog.sequence > cursor)

            # Order by sequence and limit
            events = query.order_by(WebSocketEventLog.sequence).limit(limit).all()

            if events:
                logger.debug(
                    f"Retrieved {len(events)} missed events for tenant={tenant_id} "
                    f"cursor={cursor}"
                )

            return events

        except Exception as e:
            logger.error(
                f"Failed to retrieve missed events for tenant={tenant_id}: {e}"
            )
            return []

    def cleanup_expired_events(self, db: Session, dry_run: bool = False) -> int:
        """
        Clean up expired events (older than TTL).

        Args:
            db: Database session
            dry_run: If True, only count without deleting

        Returns:
            Number of events cleaned up
        """
        try:
            now = datetime.now(timezone.utc)

            # Find expired events
            query = db.query(WebSocketEventLog).filter(
                WebSocketEventLog.ttl_expires_at < now
            )

            count = query.count()

            if not dry_run and count > 0:
                query.delete()
                db.commit()
                logger.info(f"Cleaned up {count} expired WebSocket events")

            return count

        except Exception as e:
            logger.error(f"Failed to cleanup expired events: {e}")
            db.rollback()
            return 0

    def get_latest_sequence(
        self,
        db: Session,
        tenant_id: str,
    ) -> Optional[int]:
        """
        Get the latest sequence number for a tenant.

        Useful for new connections to know where to start recovery from.

        Args:
            db: Database session
            tenant_id: Tenant ID

        Returns:
            Latest sequence number, or None if no events
        """
        try:
            result = db.query(WebSocketEventLog.sequence).filter(
                WebSocketEventLog.tenant_id == tenant_id
            ).order_by(WebSocketEventLog.sequence.desc()).first()

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Failed to get latest sequence for tenant={tenant_id}: {e}")
            return None

    def prune_old_events(
        self,
        db: Session,
        days_to_keep: int = 7,
    ) -> int:
        """
        Prune events older than specified days.

        Args:
            db: Database session
            days_to_keep: Keep events from last N days (default: 7)

        Returns:
            Number of events deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            query = db.query(WebSocketEventLog).filter(
                WebSocketEventLog.created_at < cutoff_date
            )

            count = query.count()
            query.delete()
            db.commit()

            logger.info(f"Pruned {count} WebSocket events older than {days_to_keep} days")
            return count

        except Exception as e:
            logger.error(f"Failed to prune old events: {e}")
            db.rollback()
            return 0


# Convenience instance
def get_event_log_service() -> WebSocketEventLogService:
    """Get a WebSocket event log service instance."""
    return WebSocketEventLogService(event_ttl_hours=24)
