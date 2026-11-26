"""Event Store model for SQLite-based event sourcing."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base
import json

Base = declarative_base()


class Event(Base):
    """
    Event envelope for SQLite Event Store.

    Columns:
    - event_id: Unique event identifier
    - event_type: Type of event (e.g., mission.created, task.assigned)
    - schema_version: Version for compatibility
    - mission_id: Mission context
    - task_id: Task context
    - execution_id: Execution context
    - correlation_id: Trace ID across distributed operations
    - causation_id: ID of the event that caused this one
    - project_id: Project isolation
    - tenant_id: Tenant isolation (critical for multi-tenant)
    - actor_id: User/agent who triggered the event
    - source_agent: Agent that published the event
    - target_agent: Intended recipient agent
    - payload: Event data (JSON)
    - status: PENDING, PROCESSING, PROCESSED, FAILED
    - created_at: Timestamp
    - processed_at: When projection worker completed
    - error_message: If status=FAILED
    - idempotency_key: Prevents duplicate processing
    """

    __tablename__ = "events"

    event_id = Column(String(36), primary_key=True)
    event_type = Column(String(100), nullable=False)
    schema_version = Column(Integer, default=1)
    mission_id = Column(String(36))
    task_id = Column(String(36))
    execution_id = Column(String(36))
    correlation_id = Column(String(36), nullable=False)
    causation_id = Column(String(36))
    project_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False)
    actor_id = Column(String(36), nullable=False)
    source_agent = Column(String(100))
    target_agent = Column(String(100))
    payload = Column(Text, default="{}")  # JSON
    status = Column(String(20), default="PENDING")  # PENDING, PROCESSING, PROCESSED, FAILED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime)
    error_message = Column(Text)
    idempotency_key = Column(String(100), nullable=False)
    retry_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_tenant_project", "tenant_id", "project_id"),
        Index("idx_status", "status"),
        Index("idx_mission", "mission_id"),
        Index("idx_correlation", "correlation_id"),
        UniqueConstraint("idempotency_key", "tenant_id", "project_id", name="uc_idempotency"),
    )

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "payload": json.loads(self.payload) if isinstance(self.payload, str) else self.payload,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
