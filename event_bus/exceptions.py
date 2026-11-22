"""Event Bus Exception Types"""


class EventBusException(Exception):
    """Base exception for Event Bus operations"""
    pass


class InvalidEventException(EventBusException):
    """Raised when event schema validation fails"""
    pass


class PersistenceException(EventBusException):
    """Raised when database operations fail"""
    pass


class DuplicateEventException(EventBusException):
    """Raised when event is already processed (idempotency violation)"""
    pass


class ConsumerException(EventBusException):
    """Raised when event consumption fails"""
    pass


class CorrelationException(EventBusException):
    """Raised when causation/correlation chain is broken"""
    pass
