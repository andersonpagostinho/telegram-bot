"""Event Bus Facade — Main Interface for Event-Driven Communication"""

from typing import List, Optional, Callable
from uuid import uuid4

from event_bus.event import Event, EventType, EventStatus
from event_bus.event_store import EventStore
from event_bus.event_publisher import EventPublisher
from event_bus.event_consumer import EventConsumer
from event_bus.idempotency import IdempotencyManager
from event_bus.audit_logger import AuditLogger


_bus_instance: Optional["EventBus"] = None


class EventBus:
    """
    Central Event Bus Facade

    Coordinates event publication, consumption, and persistence across the multi-agent system.
    """

    def __init__(self, db_path: str = "C:/dev/neoeve/.cache/event_bus.db"):
        self.store = EventStore(db_path)
        self.idempotency = IdempotencyManager(self.store)
        self.publisher = EventPublisher(self.store, self.idempotency)
        self.audit_logger = AuditLogger()
        self.consumers: dict = {}

    def publish(self, event: Event, idempotency_key: Optional[str] = None) -> str:
        """
        Publish event to the bus.

        Args:
            event: Event to publish
            idempotency_key: Optional key for deduplication

        Returns:
            Event ID
        """
        event_id = self.publisher.publish(event, idempotency_key)
        self.audit_logger.log_event(event, "PUBLISHED")
        return event_id

    def consume_pending(self, mission_id: str, consumer_id: str, limit: int = 10) -> List[Event]:
        """
        Consume pending events.

        Args:
            mission_id: Mission to consume events for
            consumer_id: Identifier of consuming agent
            limit: Max events to return

        Returns:
            List of pending events
        """
        consumer = self._get_or_create_consumer(consumer_id)
        events = consumer.consume_pending(mission_id, limit)

        for event in events:
            self.audit_logger.log_event(event, "PROCESSING", {"consumer": consumer_id})

        return events

    def mark_completed(self, event_id: str, consumer_id: str) -> None:
        """Mark event as successfully processed"""
        consumer = self._get_or_create_consumer(consumer_id)
        consumer.mark_completed(event_id)

        event = self.store.get_event(event_id)
        if event:
            self.audit_logger.log_event(event, "COMPLETED", {"consumer": consumer_id})

    def mark_failed(self, event_id: str, reason: str, consumer_id: str, retry: bool = False) -> None:
        """Mark event as failed"""
        consumer = self._get_or_create_consumer(consumer_id)
        consumer.mark_failed(event_id, reason, retry)

        event = self.store.get_event(event_id)
        if event:
            state = "PENDING" if retry else "FAILED"
            self.audit_logger.log_event(event, state, {"consumer": consumer_id, "reason": reason})

    def get_history(self, mission_id: str, limit: int = 100) -> List[Event]:
        """Get event history for mission"""
        return self.store.get_history(mission_id, limit)

    def register_handler(self, consumer_id: str, event_type: str, handler: Callable) -> None:
        """Register event handler"""
        consumer = self._get_or_create_consumer(consumer_id)
        consumer.register_handler(event_type, handler)

    def get_stuck_events(self, timeout_minutes: int = 30) -> List[Event]:
        """Get events stuck in processing"""
        return self.store.get_stuck_events(timeout_minutes)

    def recover_stuck_events(self, timeout_minutes: int = 30) -> int:
        """Recover stuck events back to PENDING"""
        stuck = self.get_stuck_events(timeout_minutes)
        for event in stuck:
            self.store.update_event_status(event.event_id, EventStatus.PENDING, "Recovery from stuck")
            self.audit_logger.log_error(event.event_id, f"Recovered from stuck state after {timeout_minutes}m")
        return len(stuck)

    def cleanup_old_events(self, days: int = 30) -> int:
        """Clean up old events"""
        return self.store.cleanup_old_events(days)

    def _get_or_create_consumer(self, consumer_id: str) -> EventConsumer:
        """Get or create consumer"""
        if consumer_id not in self.consumers:
            self.consumers[consumer_id] = EventConsumer(self.store, consumer_id)
        return self.consumers[consumer_id]


def get_event_bus(db_path: str = "C:/dev/neoeve/.cache/event_bus.db") -> EventBus:
    """Get singleton Event Bus instance"""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus(db_path)
    return _bus_instance
