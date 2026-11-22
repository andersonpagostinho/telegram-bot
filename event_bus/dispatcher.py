"""Event Dispatcher — Routes events to authorized agent handlers"""

import threading
import logging
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum

from event_bus.event import Event, EventStatus, EventType
from event_bus.event_bus import EventBus


logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Authorized agent roles"""
    ARCHITECT = "architect"
    BACKEND = "backend"
    DEBUGGER = "debugger"
    QA = "qa"
    SECURITY = "security"
    RELEASE = "release"
    VALIDATOR = "validator"


@dataclass
class DispatchRule:
    """Rule for routing events to agents"""
    event_type: EventType
    agent_role: AgentRole
    required_fields: List[str] = None

    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []


class EventDispatcher:
    """
    Routes events from Event Bus to appropriate agent handlers.

    Ensures:
    - Only authorized agents receive events
    - No duplicate invocations (idempotency)
    - Proper isolation (mission_id, tenant_id)
    - Auditability via correlation_id
    """

    def __init__(self, event_bus: EventBus, governance=None):
        self.event_bus = event_bus
        self.governance = governance
        self.handlers: Dict[str, Callable] = {}
        self._lock = threading.RLock()

        # Routing rules: event_type → authorized_agents
        self.routing_rules = {
            EventType.TASK_ASSIGNED: [AgentRole.BACKEND, AgentRole.DEBUGGER, AgentRole.QA],
            EventType.REVIEW_REQUESTED: [AgentRole.SECURITY, AgentRole.QA, AgentRole.RELEASE],
            EventType.VALIDATION_REQUESTED: [AgentRole.VALIDATOR],
            EventType.MISSION_CREATED: [AgentRole.ARCHITECT],
        }

    def register_handler(self, agent_role: AgentRole, handler: Callable) -> None:
        """Register handler for agent role"""
        with self._lock:
            self.handlers[agent_role.value] = handler
            logger.info(f"Handler registered for {agent_role.value}")

    def dispatch(self, event: Event, target_agent: AgentRole) -> bool:
        """
        Dispatch event to target agent.

        Returns:
            True if dispatched, False if rejected
        """
        # Validate authorization
        if not self._is_authorized(event.event_type, target_agent):
            logger.warning(
                f"Unauthorized: {target_agent.value} cannot receive {event.event_type.value}"
            )
            return False

        # Check governance rules for sensitive event types (e.g., security rejections)
        if self.governance and event.event_type in [EventType.REVIEW_REJECTED, EventType.REVIEW_APPROVED]:
            decision = self.governance.evaluate(event, target_agent.value, "receive")
            if not decision.allowed:
                logger.warning(f"Governance blocked dispatch: {decision.reason}")
                return False

        # Get handler
        handler = self.handlers.get(target_agent.value)
        if not handler:
            logger.error(f"No handler registered for {target_agent.value}")
            return False

        try:
            # Invoke handler
            logger.info(
                f"Dispatching {event.event_type.value} to {target_agent.value} "
                f"(correlation_id={event.correlation_id})"
            )
            result = handler(event)

            if result:
                logger.info(f"Handler succeeded for {event.event_id}")
            else:
                logger.warning(f"Handler failed for {event.event_id}")

            return result

        except Exception as e:
            logger.error(f"Dispatch failed: {e}", exc_info=True)
            # Mark event as failed for recovery
            self.event_bus.mark_failed(
                event.event_id,
                f"Dispatch error: {str(e)}",
                "dispatcher",
                retry=True
            )
            return False

    def _is_authorized(self, event_type: EventType, agent_role: AgentRole) -> bool:
        """Check if agent is authorized to receive this event type"""
        authorized = self.routing_rules.get(event_type, [])
        return agent_role in authorized

    def consume_and_dispatch(self, mission_id: str, limit: int = 10) -> int:
        """
        Consume pending events and dispatch to appropriate handlers.

        Returns:
            Number of events dispatched
        """
        dispatched = 0

        # Get pending events (not consumer-specific, all agents)
        events = self.event_bus.store.get_pending_events(mission_id, limit)

        for event in events:
            # Determine target agent from event metadata or routing rules
            target_agent = self._determine_target_agent(event)

            if not target_agent:
                logger.warning(f"Cannot determine target for {event.event_id}")
                self.event_bus.mark_failed(
                    event.event_id,
                    "No target agent determined",
                    "dispatcher"
                )
                continue

            # Atomically reserve
            if not self.event_bus.store.reserve_event_atomic(event.event_id):
                logger.debug(f"Event {event.event_id} already reserved")
                continue

            # Dispatch to handler
            if self.dispatch(event, target_agent):
                dispatched += 1
            else:
                # Return to PENDING for retry
                self.event_bus.store.update_event_status(
                    event.event_id,
                    EventStatus.PENDING,
                    "Handler failed, returned to PENDING"
                )

        return dispatched

    def _determine_target_agent(self, event: Event) -> Optional[AgentRole]:
        """Determine target agent based on event metadata"""
        # Priority 1: Explicit target_agent in payload
        if "target_agent" in event.payload:
            try:
                return AgentRole(event.payload["target_agent"])
            except ValueError:
                logger.warning(f"Invalid target_agent: {event.payload['target_agent']}")

        # Priority 2: Infer from event_type
        authorized = self.routing_rules.get(event.event_type, [])
        if len(authorized) == 1:
            return authorized[0]

        # Cannot determine uniquely
        return None
