"""Event Schema and Validation for Multi-Agent Communication"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime
import uuid
import json

from event_bus.exceptions import InvalidEventException


class EventType(str, Enum):
    """Supported event types in PHASE 1"""
    MISSION_CREATED = "mission_created"
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    AGENT_STARTED = "agent_started"
    AGENT_HEARTBEAT = "agent_heartbeat"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    AGENT_BLOCKED = "agent_blocked"
    VALIDATION_REQUESTED = "validation_requested"
    VALIDATION_COMPLETED = "validation_completed"
    MISSION_COMPLETED = "mission_completed"


class EventStatus(str, Enum):
    """State machine for event processing"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass
class Event:
    """
    Core event contract for multi-agent communication.

    Fields are immutable after creation for auditability.
    """

    # Identification
    event_id: str = field(default_factory=lambda: f"evt-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}")
    event_type: EventType = field(default=EventType.MISSION_CREATED)

    # Hierarchy
    mission_id: str = ""
    task_id: Optional[str] = None
    execution_id: Optional[str] = None

    # Source and target
    agent_id: str = ""
    agent_role: str = ""

    # Timestamps
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    # Traceability
    correlation_id: str = ""
    causation_id: Optional[str] = None

    # Content
    payload: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    schema_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Processing state (not part of event contract, managed by store)
    status: EventStatus = field(default=EventStatus.PENDING, init=False)
    created_at_local: str = field(default_factory=lambda: datetime.utcnow().isoformat(), init=False)

    def __post_init__(self):
        """Validate event after initialization"""
        validate_event(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["status"] = self.status.value
        return data

    def to_json(self) -> str:
        """Serialize event to JSON string"""
        data = self.to_dict()
        return json.dumps(data, default=str)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Event":
        """Deserialize event from dictionary"""
        # Convert string enums back to enum values
        if isinstance(data.get("event_type"), str):
            data["event_type"] = EventType(data["event_type"])
        if isinstance(data.get("status"), str):
            data["status"] = EventStatus(data["status"])

        # Remove fields that shouldn't be in __init__
        status = data.pop("status", EventStatus.PENDING)
        created_at_local = data.pop("created_at_local", None)

        event = Event(**data)
        event.status = status
        if created_at_local:
            event.created_at_local = created_at_local
        return event

    @staticmethod
    def from_json(json_str: str) -> "Event":
        """Deserialize event from JSON string"""
        data = json.loads(json_str)
        return Event.from_dict(data)


def validate_event(event: Event) -> None:
    """
    Validate event contract.

    Raises:
        InvalidEventException: If event violates contract
    """
    errors = []

    # Required fields
    if not event.event_id:
        errors.append("event_id is required")
    if not event.event_type:
        errors.append("event_type is required")
    if not event.mission_id:
        errors.append("mission_id is required")
    if not event.agent_id:
        errors.append("agent_id is required")
    if not event.correlation_id:
        errors.append("correlation_id is required")
    if not event.timestamp:
        errors.append("timestamp is required")

    # Type validation
    if not isinstance(event.event_type, EventType):
        errors.append(f"event_type must be EventType, got {type(event.event_type)}")
    if not isinstance(event.payload, dict):
        errors.append(f"payload must be dict, got {type(event.payload)}")
    if not isinstance(event.metadata, dict):
        errors.append(f"metadata must be dict, got {type(event.metadata)}")

    # Payload validation — no secrets allowed
    for key in event.payload:
        if any(secret in key.lower() for secret in ["secret", "password", "key", "token", "credential"]):
            errors.append(f"Secrets not allowed in payload: {key}")

    if errors:
        raise InvalidEventException("; ".join(errors))
