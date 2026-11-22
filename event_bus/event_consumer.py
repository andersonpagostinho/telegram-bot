"""Event Consumption Interface"""

from typing import List, Callable, Optional
import threading

from event_bus.event import Event, EventStatus
from event_bus.event_store import EventStore
from event_bus.exceptions import ConsumerException


class EventConsumer:
    """Consumes pending events from the bus"""

    def __init__(self, event_store: EventStore, consumer_id: str):
        self.event_store = event_store
        self.consumer_id = consumer_id
        self._handlers: dict = {}
        self._lock = threading.RLock()

    def consume_pending(self, mission_id: str, limit: int = 10) -> List[Event]:
        """
        Get pending events for processing.

        Args:
            mission_id: Mission to get events for
            limit: Maximum events to return

        Returns:
            List of pending events
        """
        events = self.event_store.get_pending_events(mission_id, limit)

        # Mark as processing
        for event in events:
            self.event_store.update_event_status(event.event_id, EventStatus.PROCESSING)

        return events

    def mark_completed(self, event_id: str) -> None:
        """Mark event as successfully processed"""
        self.event_store.mark_completed(event_id)

    def mark_failed(self, event_id: str, reason: str, retry: bool = False) -> None:
        """Mark event as failed"""
        if retry:
            self.event_store.update_event_status(event_id, EventStatus.PENDING, reason)
        else:
            self.event_store.mark_failed(event_id, reason)

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register handler for event type"""
        with self._lock:
            self._handlers[event_type] = handler

    def handle_event(self, event: Event) -> bool:
        """
        Handle event using registered handler.

        Args:
            event: Event to handle

        Returns:
            True if handled successfully
        """
        with self._lock:
            handler = self._handlers.get(event.event_type.value)

        if not handler:
            return False

        try:
            handler(event)
            return True
        except Exception as e:
            raise ConsumerException(f"Handler failed: {e}")
