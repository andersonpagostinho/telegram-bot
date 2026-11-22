"""Event Publishing Interface"""

from typing import Optional
from uuid import uuid4

from event_bus.event import Event, EventType, validate_event
from event_bus.event_store import EventStore
from event_bus.idempotency import IdempotencyManager
from event_bus.exceptions import InvalidEventException


class EventPublisher:
    """Publishes events to the bus"""

    def __init__(self, event_store: EventStore, idempotency_manager: IdempotencyManager):
        self.event_store = event_store
        self.idempotency = idempotency_manager

    def publish(self, event: Event, idempotency_key: Optional[str] = None) -> str:
        """
        Publish event to bus.

        Args:
            event: Event to publish
            idempotency_key: Optional key for deduplication

        Returns:
            Event ID

        Raises:
            InvalidEventException: If event invalid
            DuplicateEventException: If already processed
        """
        # Validate event contract
        try:
            validate_event(event)
        except InvalidEventException:
            raise

        # Check idempotency
        if idempotency_key:
            if self.idempotency.is_duplicate(idempotency_key):
                return self.idempotency.get_result(idempotency_key) or event.event_id

        # Persist event
        self.event_store.store_event(event)

        # Mark as processed if idempotency key provided
        if idempotency_key:
            self.idempotency.mark_processed(idempotency_key, event.event_id)

        return event.event_id
