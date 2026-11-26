"""
SQLAlchemy models for Command Center read projections.
Based on Event Bus audit findings from FASE 3.1.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey,
    Index, UniqueConstraint, Enum, JSON, DECIMAL, text,
    PrimaryKeyConstraint, ForeignKeyConstraint, BigInteger
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User identity for Command Center authentication."""
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True, index=True)
    email = Column(String(256), nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_login = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_is_active", "is_active"),
        Index("uq_user_email_active", "email", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )


class Tenant(Base):
    """Organization/workspace for multi-tenant isolation."""
    __tablename__ = "tenants"

    tenant_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(256), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_tenant_is_active", "is_active"),
        Index("idx_tenant_created_at", "created_at"),
    )


class Membership(Base):
    """User-Tenant association with role-based access."""
    __tablename__ = "memberships"

    membership_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    role = Column(String(32), nullable=False, index=True)  # owner, admin, operator, viewer
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_membership_user", "user_id"),
        Index("idx_membership_tenant", "tenant_id"),
        Index("idx_membership_user_tenant", "user_id", "tenant_id"),
        Index("uq_membership_user_tenant_active", "user_id", "tenant_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )


class RefreshSession(Base):
    """Authentication session with refresh token tracking."""
    __tablename__ = "refresh_sessions"

    session_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    family_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(String(256), nullable=True)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)

    __table_args__ = (
        Index("idx_refresh_session_user", "user_id"),
        Index("idx_refresh_session_tenant", "tenant_id"),
        Index("idx_refresh_session_expires_at", "expires_at"),
        Index("idx_refresh_session_family", "family_id"),
    )


class RefreshToken(Base):
    """Refresh token with rotation history."""
    __tablename__ = "refresh_tokens"

    refresh_token_id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("refresh_sessions.session_id"), nullable=False, index=True)
    token_hash = Column(String(256), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id = Column(String(64), ForeignKey("refresh_tokens.refresh_token_id"), nullable=True)

    __table_args__ = (
        Index("idx_refresh_token_session", "session_id"),
        Index("idx_refresh_token_expires_at", "expires_at"),
        UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
    )


class InviteToken(Base):
    """Invitation tokens for tenant membership."""
    __tablename__ = "invite_tokens"

    invite_id = Column(String(64), primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    email = Column(String(256), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # owner, admin, operator, viewer
    token_hash = Column(String(256), nullable=False, unique=True, index=True)
    created_by_user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_invite_token_tenant", "tenant_id"),
        Index("idx_invite_token_email", "email"),
        Index("idx_invite_token_expires_at", "expires_at"),
        UniqueConstraint("token_hash", name="uq_invite_token_hash"),
    )


class Agent(Base):
    """Agent identity and status snapshot."""
    __tablename__ = "agents"

    agent_id = Column(String(64), primary_key=True, index=True)
    agent_role = Column(String(32), nullable=False)  # architect, backend, debugger, qa, security, release, validator
    runtime = Column(String(64), nullable=True)  # Claude Code CLI, OpenAI API, etc.
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


class TenantAgentState(Base):
    """Agent state scoped to a specific tenant (PHASE 1.1)."""
    __tablename__ = "tenant_agent_states"

    tenant_id = Column(String(64), nullable=False, primary_key=True)
    agent_id = Column(String(64), nullable=False, primary_key=True)

    # Operational state (per-tenant)
    status = Column(String(32), nullable=False, default="IDLE")  # IDLE, WORKING, ERROR, etc.
    connectivity_status = Column(String(32), nullable=False, default="UNKNOWN")  # ONLINE, OFFLINE, STALE, UNKNOWN

    # Execution context (per-tenant)
    current_mission_id = Column(String(64), nullable=True)
    current_task_id = Column(String(64), nullable=True)

    # Metrics and tracking (per-tenant)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    last_execution_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)  # B3 ETAPA 3: SEMANTIC FIX (nullable)

    # Subscription and executor tracking (per-tenant)
    subscription_status = Column(String(32), nullable=False, default="UNKNOWN")  # VALID, EXPIRED, INVALID
    executor_status = Column(String(32), nullable=False, default="UNKNOWN")  # AVAILABLE, UNAVAILABLE

    # Timestamps
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "agent_id", name="pk_tenant_agent_state"),
        ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], name="fk_tas_agent_id"),
        ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], name="fk_tas_tenant_id"),
        Index("idx_tenant_agent_state_tenant", "tenant_id"),
        Index("idx_tenant_agent_state_agent", "agent_id"),
        Index("idx_tenant_agent_state_updated", "updated_at"),
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
    assigned_agent = Column(String(64), nullable=True, index=True)
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
    """Agent execution with real metrics and recovery support."""
    __tablename__ = "executions"

    execution_id = Column(String(64), primary_key=True, index=True, unique=True)
    mission_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    agent_id = Column(String(64), nullable=False)
    runtime = Column(String(64), nullable=False)
    status = Column(String(32), default="PENDING")  # QUEUED, RESERVED, RUNNING, COMPLETED, FAILED, FAILED_PERMANENT

    # Multi-tenant (recovery support)
    tenant_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)

    # Timestamps (UTC)
    queued_at = Column(DateTime(timezone=True), nullable=True)
    reserved_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=True)
    last_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Durations (milliseconds)
    queue_time_ms = Column(Integer, nullable=True)
    init_time_ms = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    validation_time_ms = Column(Integer, nullable=True)
    total_duration_ms = Column(Integer, nullable=True)

    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Recovery fields
    attempt_number = Column(Integer, default=1)
    fencing_token = Column(Integer, default=0)
    worker_id = Column(String(64), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    failure_classification = Column(String(32), nullable=True)  # TRANSIENT, PERMANENT, UNKNOWN
    last_failure_reason = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    max_attempts = Column(Integer, default=3)

    __table_args__ = (
        Index("idx_execution_mission", "mission_id"),
        Index("idx_execution_agent", "agent_id"),
        Index("idx_execution_created", "queued_at"),
        Index("idx_execution_tenant", "tenant_id"),
        Index("idx_execution_project", "project_id"),
        Index("idx_execution_status_tenant", "status", "tenant_id"),
        Index("idx_execution_lease_expired", "lease_expires_at"),
        Index("idx_execution_next_retry", "next_retry_at"),
        UniqueConstraint("execution_id", name="uq_execution_id"),
    )


class EventIdempotencyKey(Base):
    """Track processed events for idempotency and deduplication."""
    __tablename__ = "event_idempotency_keys"

    idempotency_key = Column(String(256), primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    execution_id = Column(String(64), nullable=True, index=True)
    attempt_number = Column(Integer, nullable=True)

    # Metadata
    tenant_id = Column(String(64), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("idx_event_key_tenant", "tenant_id"),
        Index("idx_event_key_execution", "execution_id"),
    )


class ExecutionAttempt(Base):
    """Audit trail for each execution attempt during recovery."""
    __tablename__ = "execution_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), ForeignKey("executions.execution_id"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(64), nullable=False)
    fencing_token = Column(Integer, nullable=False)

    # Lifecycle
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Result
    status = Column(String(32), nullable=False)  # RUNNING, COMPLETED, FAILED
    failure_classification = Column(String(32), nullable=True)  # TRANSIENT, PERMANENT, UNKNOWN
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)

    # Metadata
    tenant_id = Column(String(64), nullable=False, index=True)

    __table_args__ = (
        Index("idx_execution_attempt_execution", "execution_id"),
        Index("idx_execution_attempt_tenant", "tenant_id"),
        UniqueConstraint("execution_id", "attempt_number", "fencing_token", name="uq_attempt_fence"),
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


class ProcessedEvent(Base):
    """
    Record of events successfully projected to PostgreSQL.

    Ensures idempotence: if event_id already exists, skip reprocessing.
    """
    __tablename__ = "processed_events"

    event_id = Column(String(64), primary_key=True, index=True, unique=True)
    event_type = Column(String(100), nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    __table_args__ = (
        Index("idx_processed_tenant_project", "tenant_id", "project_id"),
        UniqueConstraint("event_id", name="uq_processed_event_id"),
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

    __table_args__ = (
        Index("idx_websocket_event_log_tenant", "tenant_id"),
        Index("idx_websocket_event_log_created_at", "created_at"),
    )


class RecoveryMetrics(Base):
    """Recovery operation metrics for monitoring."""
    __tablename__ = "recovery_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    tenant_id = Column(String(64), nullable=False, index=True)

    # Metric type
    metric_type = Column(String(64), nullable=False, index=True)  # total_recovered, successful, failed, pending_retry, active_lease

    # Metric value
    metric_value = Column(Integer, nullable=False, default=0)

    # Time window
    recorded_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    # Classification filter (optional)
    failure_classification = Column(String(32), nullable=True)  # TRANSIENT, PERMANENT, UNKNOWN

    __table_args__ = (
        Index("idx_recovery_metrics_tenant_type", "tenant_id", "metric_type"),
        Index("idx_recovery_metrics_recorded_at", "recorded_at"),
    )


class RecoveryHistory(Base):
    """Audit trail for each recovery attempt."""
    __tablename__ = "recovery_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Execution identity
    execution_id = Column(String(64), nullable=False, index=True)
    mission_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=False, index=True)

    # Tenant isolation
    tenant_id = Column(String(64), nullable=False, index=True)

    # Recovery details
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(64), nullable=True)
    fencing_token = Column(Integer, nullable=False)

    # Failure details
    failure_classification = Column(String(32), nullable=True)  # TRANSIENT, PERMANENT, UNKNOWN
    error_message = Column(Text, nullable=True)

    # Timeline
    attempted_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Outcome
    status = Column(String(32), nullable=False)  # COMPLETED, FAILED, QUEUED, ABANDONED
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_recovery_history_tenant", "tenant_id"),
        Index("idx_recovery_history_execution", "execution_id"),
        Index("idx_recovery_history_attempted_at", "attempted_at"),
        Index("idx_recovery_history_next_retry", "next_retry_at"),
    )


class ApprovalOutbox(Base):
    """
    Transactional Outbox for Approval Events.

    Guarantees atomicity between Validation creation and Event publication.
    Worker ensures events are eventually published to Event Bus (SQLite).

    C.2.3.3 ETAPA 3 P0 — PostgreSQL→SQLite reliability.
    """
    __tablename__ = "approval_outbox"

    event_id = Column(String(64), primary_key=True, index=True)
    approval_id = Column(String(64), nullable=False, index=True)
    validation_id = Column(String(64), ForeignKey("validations.validation_id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)  # approval.requested, approval.approved, etc.

    # Multi-tenant isolation
    tenant_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False)

    # Payload (JSON)
    payload = Column(Text, nullable=False)  # JSON

    # Publication status
    status = Column(String(32), default="PENDING")  # PENDING, PUBLISHED, FAILED

    # Tracking
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)

    # Retry mechanism
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)

    # Idempotency
    idempotency_key = Column(String(100), nullable=False, index=True)

    __table_args__ = (
        Index("idx_approval_outbox_tenant_project", "tenant_id", "project_id"),
        Index("idx_approval_outbox_status", "status"),
        Index("idx_approval_outbox_created", "created_at"),
        UniqueConstraint("event_id", name="uq_approval_outbox_event_id"),
        UniqueConstraint("idempotency_key", "tenant_id", "project_id", name="uq_approval_outbox_idempotency"),
    )


class ProjectionCheckpoint(Base):
    """Projection Worker progress tracking for recovery."""
    __tablename__ = "projection_checkpoints"

    # Gate A: Multi-tenant isolation with composite primary key
    tenant_id = Column(String(64), primary_key=True, nullable=False, index=True)
    consumer_id = Column(String(64), primary_key=True, nullable=False)

    last_processed_event_id = Column(String(64), nullable=True)
    last_processed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="INITIALIZED")  # INITIALIZED, PROCESSING, IDLE, ERROR
    error_count = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Gate A: Lease management for atomic reservation
    worker_id = Column(String(64), nullable=True, index=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    fencing_token = Column(BigInteger, default=0)

    __table_args__ = (
        ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], name='fk_checkpoint_tenant'),
        Index("idx_checkpoint_tenant", "tenant_id"),
        Index("idx_checkpoint_status", "status"),
        Index("idx_checkpoint_lease", "lease_expires_at"),
        Index("idx_checkpoint_tenant_consumer", "tenant_id", "consumer_id"),
    )


class TerminalAuditLog(Base):
    """Audit trail for terminal command execution."""
    __tablename__ = "terminal_audit_logs"

    audit_id = Column(String(64), primary_key=True, index=True)

    # Execution context
    execution_id = Column(String(64), ForeignKey("executions.execution_id"), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)

    # Multi-tenant
    tenant_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)

    # Command details
    command = Column(Text, nullable=False)  # Full command (may be truncated)
    command_hash = Column(String(64), nullable=True)  # SHA256 of command
    workspace_path = Column(String(512), nullable=False)  # Where it was executed

    # Validation result
    status = Column(String(32), nullable=False)  # PERMITTED, BLOCKED, TIMEOUT, ERROR
    block_reason = Column(Text, nullable=True)  # Why it was blocked (if applicable)

    # Execution result (if permitted)
    exit_code = Column(Integer, nullable=True)
    stdout_lines = Column(Integer, nullable=True)  # Number of lines in stdout
    stderr_lines = Column(Integer, nullable=True)  # Number of lines in stderr
    execution_time_ms = Column(Integer, nullable=True)

    # Resource usage (if tracked)
    cpu_percent = Column(Float, nullable=True)
    memory_mb = Column(Integer, nullable=True)

    # Tracking
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    __table_args__ = (
        Index("idx_terminal_audit_execution", "execution_id"),
        Index("idx_terminal_audit_agent", "agent_id"),
        Index("idx_terminal_audit_tenant", "tenant_id"),
        Index("idx_terminal_audit_status", "status"),
        Index("idx_terminal_audit_created", "created_at"),
    )
