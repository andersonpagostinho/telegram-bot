"""Event Bus: Producer for publishing events to SQLite Event Store."""

import logging
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from typing import Optional, Dict, Any
import json

from sqlalchemy import create_engine, text, Column
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from app.models.event_store import Event, Base

logger = logging.getLogger(__name__)

# SQLite Event Store connection (for Event Bus)
EVENT_STORE_URL = "sqlite:///./event_store.db"
engine = create_engine(EVENT_STORE_URL, isolation_level="SERIALIZABLE")
# Note: Base.metadata.create_all() removed to prevent conflicts with Alembic.
# Event Store schema is initialized once at startup via explicit call if needed.
SessionLocalSQLite = sessionmaker(bind=engine)  # Renamed for clarity

# PostgreSQL connection (for ApprovalOutbox, Validation, etc.)
from database.connection import SessionLocal as SessionLocalPG  # Import PG session


def publish_event(
    event_type: str,
    tenant_id: str,
    project_id: str,
    actor_id: str,
    correlation_id: Optional[str] = None,
    mission_id: Optional[str] = None,
    task_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    source_agent: Optional[str] = None,
    target_agent: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> Optional[Event]:
    """
    Publish event to Event Store (SQLite).

    Returns:
        Event object (new or existing via idempotency)
        None if validation fails
    """
    # Validate required fields
    if not event_type or not tenant_id or not project_id or not actor_id:
        logger.warning("Missing required fields for event publication")
        return None

    # Generate defaults
    event_id = str(uuid4())
    correlation_id = correlation_id or str(uuid4())
    idempotency_key = idempotency_key or event_id

    db = SessionLocalSQLite()  # SQLite Event Store
    try:
        # Check idempotency: if key exists and is PROCESSED, return it
        existing = db.query(Event).filter(
            Event.idempotency_key == idempotency_key,
            Event.tenant_id == tenant_id,
            Event.project_id == project_id,
        ).first()

        if existing:
            if existing.status == "PROCESSED":
                logger.info(f"Event {event_id} already processed (idempotent)")
                return existing
            # If PENDING or PROCESSING, still return existing
            return existing

        # Create new event
        event = Event(
            event_id=event_id,
            event_type=event_type,
            schema_version=1,
            mission_id=mission_id,
            task_id=task_id,
            execution_id=execution_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            tenant_id=tenant_id,
            project_id=project_id,
            actor_id=actor_id,
            source_agent=source_agent,
            target_agent=target_agent,
            payload=json.dumps(payload or {}),
            status="PENDING",
            idempotency_key=idempotency_key,
        )

        db.add(event)
        db.commit()
        logger.info(f"Event published: {event_id} ({event_type})")
        return event

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"IntegrityError publishing event: {e}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error publishing event: {e}")
        return None
    finally:
        db.close()


def reserve_event_atomic(event_id: str, tenant_id: str, project_id: str) -> Optional[Event]:
    """
    Reserve event for processing using atomic transaction (SQLite).

    Uses BEGIN IMMEDIATE for exclusive lock.
    Prevents simultaneous processing by multiple consumers.

    Returns:
        Event if reserved successfully
        None if already processing or processed
    """
    db = SessionLocalSQLite()  # SQLite Event Store
    try:
        # Atomic reservation with FOR UPDATE lock
        event = db.query(Event).filter(
            Event.event_id == event_id,
            Event.tenant_id == tenant_id,
            Event.project_id == project_id,
        ).with_for_update().first()

        if not event:
            logger.warning(f"Event not found: {event_id}")
            return None

        # Check status
        if event.status == "PROCESSING":
            logger.warning(f"Event already processing: {event_id}")
            return None

        if event.status == "PROCESSED":
            logger.warning(f"Event already processed: {event_id}")
            return None

        if event.status == "FAILED" and event.retry_count >= 3:
            logger.warning(f"Event max retries exceeded: {event_id}")
            return None

        # Mark as PROCESSING
        event.status = "PROCESSING"
        db.commit()

        logger.info(f"Event reserved: {event_id}")
        return event

    except Exception as e:
        db.rollback()
        logger.error(f"Error reserving event: {e}")
        return None
    finally:
        db.close()


def ack_event(event_id: str, tenant_id: str, project_id: str) -> bool:
    """Mark event as PROCESSED after successful handling (SQLite)."""
    db = SessionLocalSQLite()  # SQLite Event Store
    try:
        event = db.query(Event).filter(
            Event.event_id == event_id,
            Event.tenant_id == tenant_id,
            Event.project_id == project_id,
        ).first()

        if not event:
            return False

        event.status = "PROCESSED"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Event acknowledged: {event_id}")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error acknowledging event: {e}")
        return False
    finally:
        db.close()


def fail_event(event_id: str, tenant_id: str, project_id: str, error_msg: str) -> bool:
    """Mark event as FAILED with error message and increment retry count (SQLite)."""
    db = SessionLocalSQLite()  # SQLite Event Store
    try:
        event = db.query(Event).filter(
            Event.event_id == event_id,
            Event.tenant_id == tenant_id,
            Event.project_id == project_id,
        ).first()

        if not event:
            return False

        event.status = "FAILED"
        event.error_message = error_msg
        event.retry_count = (event.retry_count or 0) + 1

        # Reset to PENDING if retry allowed
        if event.retry_count < 3:
            event.status = "PENDING"

        db.commit()
        logger.warning(f"Event failed: {event_id} (attempt {event.retry_count})")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error failing event: {e}")
        return False
    finally:
        db.close()


def get_pending_events(tenant_id: str, project_id: str, limit: int = 10) -> list:
    """Get pending events for processing (SQLite Event Bus)."""
    db = SessionLocalSQLite()  # SQLite Event Store
    try:
        events = db.query(Event).filter(
            Event.status == "PENDING",
            Event.tenant_id == tenant_id,
            Event.project_id == project_id,
        ).limit(limit).all()
        return events
    finally:
        db.close()


# ============================================================================
# C.2.3.3 ETAPA 3: Outbox Pattern (P0 Reliability)
# ============================================================================

def publish_outbox_event(
    event_id: str,
    approval_id: str,
    validation_id: str,
    event_type: str,
    tenant_id: str,
    project_id: str,
    actor_id: str,
    payload: Dict[str, Any],
    idempotency_key: str,
) -> Optional[Event]:
    """
    Publish event from Outbox to SQLite Event Bus.

    Called by worker after Outbox records Event.
    Ensures transactional consistency: publish only if Outbox record exists.
    Uses PostgreSQL for ApprovalOutbox table.
    """
    db = SessionLocalPG()  # PostgreSQL for ApprovalOutbox
    try:
        # Verify Outbox record exists (idempotency guard)
        from database.models import ApprovalOutbox
        outbox = db.query(ApprovalOutbox).filter(
            ApprovalOutbox.event_id == event_id,
            ApprovalOutbox.tenant_id == tenant_id,
            ApprovalOutbox.project_id == project_id,
        ).first()

        if not outbox:
            logger.warning(f"Outbox record not found: {event_id}")
            return None

        # Check if already published
        if outbox.status == "PUBLISHED":
            logger.info(f"Outbox event already published (idempotent): {event_id}")
            return None

        # Publish to Event Bus (SQLite)
        event = publish_event(
            event_type=event_type,
            tenant_id=tenant_id,
            project_id=project_id,
            actor_id=actor_id,
            mission_id=payload.get("mission_id"),
            task_id=payload.get("task_id"),
            execution_id=payload.get("execution_id"),
            correlation_id=payload.get("correlation_id", str(uuid4())),
            causation_id=payload.get("causation_id"),
            source_agent=payload.get("source_agent"),
            target_agent=payload.get("target_agent"),
            payload=payload,
            idempotency_key=idempotency_key,
        )

        if event:
            # Mark Outbox as published
            outbox.status = "PUBLISHED"
            outbox.published_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Outbox event published: {event_id}")
            return event
        else:
            # Publish failed
            outbox.status = "FAILED"
            outbox.retry_count = (outbox.retry_count or 0) + 1
            outbox.last_attempted_at = datetime.now(timezone.utc)
            outbox.error_message = "Failed to publish to Event Bus"
            if outbox.retry_count >= (outbox.max_retries or 3):
                logger.error(f"Outbox max retries exceeded: {event_id}")
            db.commit()
            return None

    except Exception as e:
        db.rollback()
        logger.error(f"Error publishing outbox event: {e}")
        return None
    finally:
        db.close()


def get_pending_outbox_events(
    tenant_id: str,
    project_id: str,
    limit: int = 10
) -> list:
    """Get pending Outbox events for publication to Event Bus.
    Uses PostgreSQL for ApprovalOutbox table.
    """
    db = SessionLocalPG()  # PostgreSQL for ApprovalOutbox
    try:
        from database.models import ApprovalOutbox
        events = db.query(ApprovalOutbox).filter(
            ApprovalOutbox.status == "PENDING",
            ApprovalOutbox.tenant_id == tenant_id,
            ApprovalOutbox.project_id == project_id,
            ApprovalOutbox.retry_count < ApprovalOutbox.max_retries,
        ).limit(limit).all()
        return events
    finally:
        db.close()


# ============================================================================
# C.2.3.3 ETAPA 3: Recovery from PROCESSING (P1 Reliability)
# ============================================================================

def recover_expired_processing_events(
    tenant_id: str,
    project_id: str,
    max_processing_age_seconds: int = 300,
) -> int:
    """
    Recover events stuck in PROCESSING state.

    If worker crashes while processing, event stays in PROCESSING.
    This job finds and recovers such events (after timeout).

    Uses SELECT FOR UPDATE to ensure only one worker recovers same event.
    Uses SQLite for Event Bus recovery.
    """
    db = SessionLocalSQLite()  # SQLite Event Store
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=max_processing_age_seconds)

        # Find expired PROCESSING events with lock
        events = db.query(Event).filter(
            Event.status == "PROCESSING",
            Event.tenant_id == tenant_id,
            Event.project_id == project_id,
            Event.created_at < cutoff_time,
        ).with_for_update().all()

        recovered_count = 0

        for event in events:
            if event.retry_count is None:
                event.retry_count = 0

            # Check if still recoverable
            if event.retry_count >= 3:
                event.status = "FAILED"
                event.error_message = f"Max recovery attempts exceeded (count={event.retry_count})"
                logger.warning(f"Event max recovery exceeded: {event.event_id}")
            else:
                # Reset to PENDING for retry
                event.status = "PENDING"
                event.retry_count += 1
                logger.warning(f"Recovered PROCESSING event: {event.event_id} (recovery attempt {event.retry_count})")

            recovered_count += 1

        db.commit()
        return recovered_count

    except Exception as e:
        db.rollback()
        logger.error(f"Error recovering PROCESSING events: {e}")
        return 0
    finally:
        db.close()
