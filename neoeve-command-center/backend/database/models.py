"""
SQLAlchemy models for Command Center read projections.
Based on Event Bus audit findings from FASE 3.1.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey,
    Index, UniqueConstraint, Enum, JSON, DECIMAL
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def utc_now():
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class Agent(Base):
    """Agent identity and status snapshot."""
    __tablename__ = "agents"

    agent_id = Column(String(64), primary_key=True, index=True)
    agent_role = Column(String(32), nullable=False)  # architect, backend, debugger, qa, security, release, validator
    runtime = Column(String(64), nullable=False)  # Claude Code CLI, OpenAI API, etc.
    status = Column(String(32), default="IDLE")  # IDLE, WORKING, ANALYZING, TESTING, REVIEWING, BLOCKED, COMPLETED, ERROR
    connectivity_status = Column(String(32), default="UNKNOWN")  # ONLINE, OFFLINE, STALE, UNKNOWN
    current_mission_id = Column(String(64), nullable=True)
    current_task_id = Column(String(64), nullable=True)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    last_execution_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    metrics_summary = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("idx_agent_role", "agent_role"),
        Index("idx_agent_status", "status"),
    )


class Mission(Base):
    """Mission history and progress tracking."""
    __tablename__ = "missions"

    mission_id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    status = Column(String(32), default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED, BLOCKED
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    progress_summary = Column(JSON, nullable=True)
    result_summary = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_mission_project", "project_id"),
        Index("idx_mission_tenant", "tenant_id"),
        UniqueConstraint("project_id", "tenant_id", "mission_id", name="uq_mission_scope"),
    )


class Task(Base):
    """Task assignment and execution tracking."""
    __tablename__ = "tasks"

    task_id = Column(String(64), primary_key=True, index=True)
    mission_id = Column(String(64), ForeignKey("missions.mission_id"), nullable=False, index=True)
    assigned_agent = Column(String(64), nullable=False)
    status = Column(String(32), default="PENDING")  # PENDING, STARTED, COMPLETED, FAILED
    priority = Column(String(16), default="NORMAL")  # LOW, NORMAL, HIGH, CRITICAL
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_task_mission", "mission_id"),
        Index("idx_task_agent", "assigned_agent"),
    )


class Execution(Base):
    """Agent execution with real metrics."""
    __tablename__ = "executions"

    execution_id = Column(String(64), primary_key=True, index=True, unique=True)
    mission_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    agent_id = Column(String(64), nullable=False)
    runtime = Column(String(64), nullable=False)
    status = Column(String(32), default="PENDING")  # QUEUED, RESERVED, RUNNING, COMPLETED, FAILED

    # Timestamps (UTC)
    queued_at = Column(DateTime(timezone=True), nullable=True)
    reserved_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=True)

    # Durations (milliseconds)
    queue_time_ms = Column(Integer, nullable=True)
    init_time_ms = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    validation_time_ms = Column(Integer, nullable=True)
    total_duration_ms = Column(Integer, nullable=True)

    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_execution_mission", "mission_id"),
        Index("idx_execution_agent", "agent_id"),
        Index("idx_execution_created", "queued_at"),
        UniqueConstraint("execution_id", name="uq_execution_id"),
    )


class AgentEvent(Base):
    """Event projections from Event Bus."""
    __tablename__ = "agent_events"

    event_id = Column(String(64), primary_key=True, index=True)
    event_type = Column(String(32), nullable=False)  # TASK_ASSIGNED, TASK_COMPLETED, etc.
    schema_version = Column(Integer, default=1)

    # Identifiers
    mission_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    execution_id = Column(String(64), nullable=True, index=True)
    correlation_id = Column(String(64), nullable=True)
    causation_id = Column(String(64), nullable=True)

    # Multi-tenant
    project_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=True)

    # Agent info
    source_agent = Column(String(32), nullable=False)
    target_agent = Column(String(32), nullable=True)

    # Data
    payload_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_event_mission", "mission_id"),
        Index("idx_event_correlation", "correlation_id"),
        Index("idx_event_causation", "causation_id"),
        Index("idx_event_project", "project_id"),
        Index("idx_event_tenant", "tenant_id"),
        UniqueConstraint("event_id", name="uq_event_id"),
    )


class Validation(Base):
    """QA, Security, Release, OpenAI Validator findings."""
    __tablename__ = "validations"

    validation_id = Column(String(64), primary_key=True, index=True)
    mission_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    execution_id = Column(String(64), nullable=True, index=True)

    validator = Column(String(32), nullable=False)  # qa, security, release, openai
    verdict = Column(String(32), nullable=False)  # APPROVED, CONDITIONAL, BLOCKED, PENDING
    confidence = Column(Integer, nullable=True)  # 0-100

    findings_summary = Column(JSON, nullable=True)
    cost = Column(DECIMAL(10, 6), nullable=True)  # For OpenAI
    tokens_used = Column(Integer, nullable=True)  # For OpenAI
    duration_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    __table_args__ = (
        Index("idx_validation_mission", "mission_id"),
        Index("idx_validation_validator", "validator"),
    )


class WebSocketEventLog(Base):
    """
    WebSocket event log for reconnection recovery.

    Tracks events sent over WebSocket so that clients can recover missed events
    when reconnecting (e.g., after network interruption).

    ETAPA 5: Event Recovery mechanism
    """
    __tablename__ = "websocket_event_log"

    # Primary key - sequence number (auto-incrementing)
    # Used for client reconnection cursor
    sequence = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Event identification
    event_id = Column(String(64), nullable=False, index=True, unique=True)
    event_type = Column(String(64), nullable=False)  # e.g., "MISSION_UPDATED", "TASK_COMPLETED"

    # Multi-tenant isolation
    tenant_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)

    # Event data
    payload = Column(JSON, nullable=False)  # Full event payload for client
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    # Retention (for cleanup)
    # Events older than 24 hours can be pruned
    ttl_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_websocket_event_tenant", "tenant_id"),
        Index("idx_websocket_event_created", "created_at"),
        Index("idx_websocket_event_ttl", "ttl_expires_at"),
        UniqueConstraint("event_id", name="uq_websocket_event_id"),
    )


class ProjectionCheckpoint(Base):
    """Projection Worker progress tracking for recovery."""
    __tablename__ = "projection_checkpoints"

    consumer_id = Column(String(64), primary_key=True)
    last_processed_event_id = Column(String(64), nullable=True)
    last_processed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="INITIALIZED")  # INITIALIZED, PROCESSING, IDLE, ERROR
    error_count = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("idx_checkpoint_status", "status"),
    )
