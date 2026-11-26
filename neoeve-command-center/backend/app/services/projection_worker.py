"""Projection Worker: Consume events from SQLite Event Store and project to PostgreSQL."""

import logging
from datetime import datetime, timezone
from typing import Optional, Callable
import json

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.event_store import Event
from app.services.event_bus import reserve_event_atomic, ack_event, fail_event
from database.models import Agent, Mission
from database.connection import get_db

logger = logging.getLogger(__name__)

# Event handler registry
EVENT_HANDLERS = {}


def register_handler(event_type: str):
    """Decorator to register event handler."""
    def decorator(func: Callable):
        EVENT_HANDLERS[event_type] = func
        return func
    return decorator


@register_handler("agent.status_changed")
def handle_agent_status_changed(event: Event, db_pg: Session) -> bool:
    """Project agent.status_changed event to PostgreSQL."""
    try:
        payload = json.loads(event.payload)
        agent_id = payload.get("agent_id")
        status = payload.get("status")

        # B4 ETAPA 4 FIX: Filter by tenant_id to prevent cross-tenant access
        agent = db_pg.query(Agent).filter(
            Agent.agent_id == agent_id,
            Agent.tenant_id == event.tenant_id
        ).first()
        if not agent:
            # Create if doesn't exist
            agent = Agent(
                agent_id=agent_id,
                agent_role=payload.get("agent_role", "unknown"),
                runtime=payload.get("runtime", "unknown"),
            )
            db_pg.add(agent)

        agent.status = status
        agent.last_event_at = datetime.now(timezone.utc)
        logger.info(f"Projected agent status: {agent_id} → {status}")
        return True
    except Exception as e:
        logger.error(f"Error projecting agent.status_changed: {e}")
        return False


@register_handler("mission.created")
def handle_mission_created(event: Event, db_pg: Session) -> bool:
    """Project mission.created event to PostgreSQL."""
    try:
        payload = json.loads(event.payload)
        mission_id = event.mission_id or payload.get("mission_id")

        mission = Mission(
            mission_id=mission_id,
            project_id=event.project_id,
            tenant_id=event.tenant_id,
            name=payload.get("name", "Unnamed Mission"),
            status="PENDING",
        )
        db_pg.add(mission)
        logger.info(f"Projected mission created: {mission_id}")
        return True
    except Exception as e:
        logger.error(f"Error projecting mission.created: {e}")
        return False


@register_handler("mission.updated")
def handle_mission_updated(event: Event, db_pg: Session) -> bool:
    """Project mission.updated event to PostgreSQL."""
    try:
        payload = json.loads(event.payload)
        mission_id = event.mission_id

        # B4 ETAPA 4 FIX: Filter by tenant_id to prevent cross-tenant access
        mission = db_pg.query(Mission).filter(
            Mission.mission_id == mission_id,
            Mission.tenant_id == event.tenant_id
        ).first()
        if mission:
            if "status" in payload:
                mission.status = payload["status"]
            if "name" in payload:
                mission.name = payload["name"]
            logger.info(f"Projected mission updated: {mission_id}")
        return True
    except Exception as e:
        logger.error(f"Error projecting mission.updated: {e}")
        return False


@register_handler("approval.requested")
def handle_approval_requested(event: Event, db_pg: Session) -> bool:
    """Project approval.requested event to PostgreSQL."""
    from database.models import AgentEvent, ProcessedEvent

    try:
        payload = json.loads(event.payload)
        approval_id = payload.get("approval_id")
        requested_by = payload.get("requested_by")

        # Check idempotency: if already processed, skip silently (return True)
        # B4 ETAPA 4 FIX: Filter by tenant_id to prevent cross-tenant access
        existing_processed = db_pg.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event.event_id,
            ProcessedEvent.tenant_id == event.tenant_id
        ).first()

        if existing_processed:
            logger.info(f"Approval event already processed (idempotent): {event.event_id}")
            return True

        # Create AgentEvent projection
        agent_event = AgentEvent(
            event_id=event.event_id,
            event_type="approval.requested",
            schema_version=1,
            mission_id=event.mission_id,
            task_id=event.task_id,
            execution_id=event.execution_id,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            project_id=event.project_id,
            tenant_id=event.tenant_id,
            actor_id=event.actor_id,
            source_agent=event.source_agent,
            target_agent=event.target_agent,
            payload_summary={"approval_id": approval_id, "requested_by": requested_by},
            created_at=event.created_at,
        )
        db_pg.add(agent_event)

        # Record processed event (idempotency marker)
        processed_event = ProcessedEvent(
            event_id=event.event_id,
            event_type="approval.requested",
            tenant_id=event.tenant_id,
            project_id=event.project_id,
        )
        db_pg.add(processed_event)

        logger.info(f"Projected approval.requested: {approval_id}")
        return True

    except Exception as e:
        logger.error(f"Error projecting approval.requested: {e}")
        return False


@register_handler("approval.approved")
def handle_approval_approved(event: Event, db_pg: Session) -> bool:
    """Project approval.approved event to PostgreSQL."""
    from database.models import AgentEvent, ProcessedEvent

    try:
        payload = json.loads(event.payload)
        approval_id = payload.get("approval_id")
        validator = payload.get("validator")

        # Check idempotency (B4.4 FIX: Filter by tenant_id)
        existing_processed = db_pg.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event.event_id,
            ProcessedEvent.tenant_id == event.tenant_id
        ).first()

        if existing_processed:
            logger.info(f"Approval event already processed (idempotent): {event.event_id}")
            return True

        # Create AgentEvent projection
        agent_event = AgentEvent(
            event_id=event.event_id,
            event_type="approval.approved",
            schema_version=1,
            mission_id=event.mission_id,
            task_id=event.task_id,
            execution_id=event.execution_id,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            project_id=event.project_id,
            tenant_id=event.tenant_id,
            actor_id=event.actor_id,
            source_agent=event.source_agent,
            target_agent=event.target_agent,
            payload_summary={"approval_id": approval_id, "validator": validator},
            created_at=event.created_at,
            processed_at=datetime.now(timezone.utc),
        )
        db_pg.add(agent_event)

        # Record processed event (idempotency marker)
        processed_event = ProcessedEvent(
            event_id=event.event_id,
            event_type="approval.approved",
            tenant_id=event.tenant_id,
            project_id=event.project_id,
        )
        db_pg.add(processed_event)

        logger.info(f"Projected approval.approved: {approval_id}")
        return True

    except Exception as e:
        logger.error(f"Error projecting approval.approved: {e}")
        return False


@register_handler("approval.rejected")
def handle_approval_rejected(event: Event, db_pg: Session) -> bool:
    """Project approval.rejected event to PostgreSQL."""
    from database.models import AgentEvent, ProcessedEvent

    try:
        payload = json.loads(event.payload)
        approval_id = payload.get("approval_id")
        validator = payload.get("validator")

        # Check idempotency (B4.4 FIX: Filter by tenant_id)
        existing_processed = db_pg.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event.event_id,
            ProcessedEvent.tenant_id == event.tenant_id
        ).first()

        if existing_processed:
            logger.info(f"Approval event already processed (idempotent): {event.event_id}")
            return True

        # Create AgentEvent projection
        agent_event = AgentEvent(
            event_id=event.event_id,
            event_type="approval.rejected",
            schema_version=1,
            mission_id=event.mission_id,
            task_id=event.task_id,
            execution_id=event.execution_id,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            project_id=event.project_id,
            tenant_id=event.tenant_id,
            actor_id=event.actor_id,
            source_agent=event.source_agent,
            target_agent=event.target_agent,
            payload_summary={"approval_id": approval_id, "validator": validator},
            created_at=event.created_at,
            processed_at=datetime.now(timezone.utc),
        )
        db_pg.add(agent_event)

        # Record processed event (idempotency marker)
        processed_event = ProcessedEvent(
            event_id=event.event_id,
            event_type="approval.rejected",
            tenant_id=event.tenant_id,
            project_id=event.project_id,
        )
        db_pg.add(processed_event)

        logger.info(f"Projected approval.rejected: {approval_id}")
        return True

    except Exception as e:
        logger.error(f"Error projecting approval.rejected: {e}")
        return False


@register_handler("approval.vetoed")
def handle_approval_vetoed(event: Event, db_pg: Session) -> bool:
    """Project approval.vetoed event to PostgreSQL."""
    from database.models import AgentEvent, ProcessedEvent

    try:
        payload = json.loads(event.payload)
        approval_id = payload.get("approval_id")
        validator = payload.get("validator")
        reason = payload.get("reason", "Security veto")

        # Check idempotency (B4.4 FIX: Filter by tenant_id)
        existing_processed = db_pg.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event.event_id,
            ProcessedEvent.tenant_id == event.tenant_id
        ).first()

        if existing_processed:
            logger.info(f"Approval event already processed (idempotent): {event.event_id}")
            return True

        # Create AgentEvent projection
        agent_event = AgentEvent(
            event_id=event.event_id,
            event_type="approval.vetoed",
            schema_version=1,
            mission_id=event.mission_id,
            task_id=event.task_id,
            execution_id=event.execution_id,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            project_id=event.project_id,
            tenant_id=event.tenant_id,
            actor_id=event.actor_id,
            source_agent=event.source_agent,
            target_agent=event.target_agent,
            payload_summary={"approval_id": approval_id, "validator": validator, "reason": reason},
            created_at=event.created_at,
            processed_at=datetime.now(timezone.utc),
        )
        db_pg.add(agent_event)

        # Record processed event (idempotency marker)
        processed_event = ProcessedEvent(
            event_id=event.event_id,
            event_type="approval.vetoed",
            tenant_id=event.tenant_id,
            project_id=event.project_id,
        )
        db_pg.add(processed_event)

        logger.info(f"Projected approval.vetoed: {approval_id}")
        return True

    except Exception as e:
        logger.error(f"Error projecting approval.vetoed: {e}")
        return False


class ProjectionWorker:
    """Worker that consumes events from SQLite and projects to PostgreSQL."""

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size

    def process_events(self, tenant_id: str, project_id: str) -> int:
        """
        Process pending events from Event Store.

        Returns: Number of events processed
        """
        from app.services.event_bus import get_pending_events

        db_sqlite = None
        db_pg = next(get_db())

        try:
            # Get pending events from SQLite
            pending_events = get_pending_events(tenant_id, project_id, self.batch_size)

            processed_count = 0

            for event in pending_events:
                # Reserve event
                reserved = reserve_event_atomic(event.event_id, tenant_id, project_id)
                if not reserved:
                    logger.warning(f"Could not reserve event: {event.event_id}")
                    continue

                # Project event (handlers check idempotency via ProcessedEvent)
                handler = EVENT_HANDLERS.get(event.event_type)
                if not handler:
                    logger.warning(f"No handler for event type: {event.event_type}")
                    fail_event(event.event_id, tenant_id, project_id, f"Unknown event type: {event.event_type}")
                    processed_count += 1
                    continue

                try:
                    success = handler(event, db_pg)

                    if success:
                        # Record event as processed
                        db_pg.commit()

                        # Acknowledge in SQLite
                        ack_event(event.event_id, tenant_id, project_id)
                        logger.info(f"Event processed: {event.event_id}")
                    else:
                        # Fail event
                        db_pg.rollback()
                        fail_event(event.event_id, tenant_id, project_id, "Handler returned false")
                        logger.warning(f"Event handler failed: {event.event_id}")

                    processed_count += 1

                except Exception as e:
                    db_pg.rollback()
                    fail_event(event.event_id, tenant_id, project_id, str(e))
                    logger.error(f"Error processing event {event.event_id}: {e}")
                    processed_count += 1

            return processed_count

        except Exception as e:
            logger.error(f"Error in process_events: {e}")
            return 0
        finally:
            if db_pg:
                db_pg.close()


def run_worker(tenant_id: str, project_id: str, continuous: bool = False):
    """Run projection worker."""
    worker = ProjectionWorker()

    if continuous:
        import time
        while True:
            processed = worker.process_events(tenant_id, project_id)
            if processed == 0:
                time.sleep(1)
    else:
        worker.process_events(tenant_id, project_id)
