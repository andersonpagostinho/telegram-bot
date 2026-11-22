"""
NeoEve Event Bus — Core Multi-Agent Communication Layer

PHASE 1 — Foundational Event Bus Implementation
- Event schema and validation
- SQLite persistence
- Publisher/Consumer pattern
- Idempotency management
- Audit logging

NOT included in PHASE 1:
- Command Center integration
- Advanced recovery mechanisms
- WebSocket/real-time features
- Automatic agent orchestration
"""

__version__ = "0.1.0"
__phase__ = "1_core"

from event_bus.event import Event, EventType, EventStatus, validate_event
from event_bus.event_bus import EventBus, get_event_bus
from event_bus.exceptions import (
    EventBusException,
    InvalidEventException,
    PersistenceException,
    DuplicateEventException,
)

__all__ = [
    "Event",
    "EventType",
    "EventStatus",
    "EventBus",
    "get_event_bus",
    "validate_event",
    "EventBusException",
    "InvalidEventException",
    "PersistenceException",
    "DuplicateEventException",
]
