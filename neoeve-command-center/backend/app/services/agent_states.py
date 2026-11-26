"""Agent state enums - independent module to avoid circular imports."""

from enum import Enum


class OperationalState(Enum):
    """Operational state of an agent."""
    IDLE = "IDLE"
    WORKING = "WORKING"
    ANALYZING = "ANALYZING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ConnectivityState(Enum):
    """Connectivity state of an agent."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    NOT_CONFIGURED = "NOT_CONFIGURED"
