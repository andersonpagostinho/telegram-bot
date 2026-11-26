"""Agent Runtime: execution engine for agents."""

import logging
import json
import os
import time
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from database.models import Execution, Agent, TerminalAuditLog, utc_now
from database.connection import get_db
from app.services.agent_registry import AgentRegistry, Permission, OperationalState, ConnectivityState
from app.services.claude_code_adapter import ClaudeCodeAdapter
from app.services.event_bus import publish_event
from app.services.terminal_access_control import TerminalAccessControl
from app.services.recovery_service import RecoveryService, RetryPolicy, FailureClassification
from app.services.recovery_metrics_service import RecoveryMetricsService
from app.services.tenant_agent_state_service import TenantAgentStateService

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Agent execution runtime with recovery support."""

    def __init__(self):
        self.adapters = {
            "claude-code-cli": ClaudeCodeAdapter(subscription_only=True),
        }
        self._active_executions = {}
        self._subscription_checked = False
        self.recovery_service = RecoveryService(
            retry_policy=RetryPolicy(max_attempts=3, backoff_ms=1000, backoff_multiplier=2.0),
            lease_timeout_s=300
        )
        self.metrics_service = RecoveryMetricsService()

    def _update_agent_state(
        self,
        db: Session,
        tenant_id: str,
        agent_id: str,
        status: str,
        connectivity_status: Optional[str] = None
    ) -> bool:
        """Update agent state with transaction lock (OPÇÃO A).

        Encapsulates TenantAgentStateService.update_with_transaction_lock()
        """
        try:
            service = TenantAgentStateService(db)
            return service.update_with_transaction_lock(
                tenant_id=tenant_id,
                agent_id=agent_id,
                new_status=status,
                connectivity_status=connectivity_status
            )
        except Exception as e:
            logger.error(f"Error updating agent state: {e}")
            return False

    def _has_active_execution(
        self,
        db: Session,
        tenant_id: str,
        agent_id: str,
        exclude_execution_id: Optional[str] = None
    ) -> bool:
        """Check if any other execution is active for this agent/tenant (ETAPA 3)."""
        try:
            query = db.query(Execution).filter(
                Execution.tenant_id == tenant_id,
                Execution.agent_id == agent_id,
                Execution.status.in_(["RUNNING", "RESERVED", "QUEUED"])
            )
            if exclude_execution_id:
                query = query.filter(Execution.execution_id != exclude_execution_id)
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking active executions: {e}")
            return False

    def execute_task(
        self,
        task_id: str,
        agent_id: str,
        task_description: str,
        mission_id: str,
        tenant_id: str,
        project_id: str,
        workspace_path: str,
        timeout_seconds: int = 300,
        execution_id: Optional[str] = None,
        attempt_number: int = 1,
    ) -> Tuple[bool, str, str, str]:
        """
        Execute a task with an agent. Supports recovery with automatic retries.

        Args:
            execution_id: Optional. If provided, retries previous execution with same ID.
            attempt_number: Current attempt (1, 2, 3...).

        Returns:
            (success, stdout, stderr, execution_id)
        """
        db = next(get_db())

        # Use provided execution_id for retries, or generate new one
        if not execution_id:
            execution_id = str(uuid4())

        worker_id = f"runtime-{os.getpid()}"
        fencing_token = None
        start_time = time.time()

        try:
            # 1. VALIDATE TENANT AND PROJECT ISOLATION
            if not tenant_id or not project_id:
                logger.error(f"Execution {execution_id}: Missing tenant_id or project_id")
                return False, "", "Invalid tenant/project"

            logger.info(f"Execution {execution_id}: Tenant={tenant_id}, Project={project_id}")

            # 2. VALIDATE AGENT
            agent_registry_config = None
            for key, config in AgentRegistry.AGENTS.items():
                if config["agent_id"] == agent_id:
                    agent_registry_config = config
                    break

            if not agent_registry_config:
                logger.error(f"Execution {execution_id}: Agent not found: {agent_id}")
                return False, "", "Agent not found"

            # 3. CHECK PERMISSION
            if not AgentRegistry.has_permission(agent_id, Permission.EXECUTE):
                logger.error(f"Execution {execution_id}: Agent {agent_id} not authorized")
                return False, "", "Permission denied"

            # 3.5 VERIFY CLAUDE SUBSCRIPTION (once per runtime instance)
            adapter = self.adapters.get("claude-code-cli")
            if not adapter:
                logger.error(f"Execution {execution_id}: Claude Code adapter not available")
                return False, "", "Executor not available"

            if not self._subscription_checked:
                is_valid, status = adapter.verify_subscription()
                self._subscription_checked = True
                if not is_valid:
                    error_detail = status.get("error", "Unknown subscription error")
                    logger.error(f"Execution {execution_id}: Subscription verification failed: {error_detail}")
                    return False, "", f"Claude subscription required: {error_detail}"
                logger.info(f"Execution {execution_id}: Claude subscription verified on runtime init")

            # 4. PREVENT DUPLICATE EXECUTION
            existing = db.query(Execution).filter(
                Execution.task_id == task_id,
                Execution.agent_id == agent_id,
                Execution.status.in_(["RUNNING", "COMPLETED"]),
                Execution.tenant_id == tenant_id,
                Execution.project_id == project_id,
            ).first()

            if existing:
                logger.warning(f"Execution {execution_id}: Task {task_id} already executed")
                return False, "", "Task already executed (idempotency)"

            # Check if this is a retry
            existing = db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).first()

            if existing:
                # Retry: load existing execution
                execution = existing
                attempt_number = execution.attempt_number + 1
                execution.attempt_number = attempt_number
            else:
                # First attempt: create new Execution record
                execution = Execution(
                    execution_id=execution_id,
                    mission_id=mission_id,
                    task_id=task_id,
                    agent_id=agent_id,
                    runtime="claude-code-cli",
                    status="RUNNING",
                    queued_at=utc_now(),
                    started_at=utc_now(),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    attempt_number=1,
                    fencing_token=0,
                    max_attempts=3,
                )
                db.add(execution)

            db.commit()

            # Acquire lease BEFORE execution
            lease_success, fencing_token = self.recovery_service.acquire_lease(
                db, execution_id, worker_id
            )

            if not lease_success:
                logger.warning(f"Execution {execution_id}: Could not acquire lease (concurrent execution)")
                execution.status = "FAILED"
                execution.error = "Could not acquire lease"
                execution.completed_at = utc_now()
                db.commit()
                db.close()
                return False, "", "Could not acquire lease (concurrent execution)"

            execution.fencing_token = fencing_token
            execution.worker_id = worker_id
            execution.lease_expires_at = utc_now() + timedelta(seconds=300)
            db.commit()

            # Publish execution.created event (only on first attempt)
            if attempt_number == 1:
                publish_event(
                    event_type="execution.created",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    actor_id=agent_id,
                    execution_id=execution_id,
                    mission_id=mission_id,
                    task_id=task_id,
                    payload={"agent_id": agent_id, "task_description": task_description},
                )

            # Update agent status (with transaction lock — OPÇÃO A)
            self._update_agent_state(db, tenant_id, agent_id, OperationalState.WORKING.value)

            # B3 ETAPA 4: Record heartbeat on actual execution start
            try:
                self.tenant_state_service.record_heartbeat(tenant_id, agent_id)
            except Exception as e:
                logger.warning(f"Failed to record heartbeat on start: {e}")

            # SECURITY: Validate command against whitelist BEFORE execution (OBRIGATÓRIO)
            is_allowed, block_reason = TerminalAccessControl.validate_command(
                command=task_description,
                agent_id=agent_id,
                workspace_path=workspace_path,
                tenant_id=tenant_id,
            )

            if not is_allowed:
                logger.warning(f"Execution {execution_id}: Command blocked: {block_reason}")

                # Audit the blocked command
                TerminalAccessControl.audit_command(
                    execution_id=execution_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    command=task_description,
                    workspace_path=workspace_path,
                    status="BLOCKED",
                    block_reason=block_reason,
                    db=db,
                )

                # Mark execution as failed
                execution.status = "FAILED"
                execution.error = f"Command blocked by security policy: {block_reason}"
                execution.completed_at = datetime.now(timezone.utc)
                db.commit()

                # Publish rejection event
                publish_event(
                    event_type="execution.rejected",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    actor_id=agent_id,
                    execution_id=execution_id,
                    mission_id=mission_id,
                    task_id=task_id,
                    payload={"reason": block_reason},
                )

                # Update agent status (with transaction lock — OPÇÃO A)
                self._update_agent_state(db, tenant_id, agent_id, OperationalState.IDLE.value)

                # B3 ETAPA 4: Record heartbeat on completion
                try:
                    self.tenant_state_service.record_heartbeat(tenant_id, agent_id)
                except Exception as e:
                    logger.warning(f"Failed to record heartbeat on completion: {e}")

                return False, "", block_reason

            # Command is allowed - audit it
            TerminalAccessControl.audit_command(
                execution_id=execution_id,
                agent_id=agent_id,
                task_id=task_id,
                tenant_id=tenant_id,
                project_id=project_id,
                command=task_description,
                workspace_path=workspace_path,
                status="PERMITTED",
                db=db,
            )

            # Execute via adapter
            exit_code, stdout, stderr = adapter.execute(
                execution_id,
                task_description,
                workspace_path,
                timeout_seconds,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Update execution result
            is_success = exit_code == 0
            execution.status = "COMPLETED" if is_success else "FAILED"
            execution.completed_at = utc_now()
            execution.result = {"exit_code": exit_code, "stdout": stdout[:1000]}
            execution.error = stderr[:1000] if stderr else None

            # Register attempt for auditoria
            self.recovery_service.record_attempt(
                db, execution_id, attempt_number,
                fencing_token, worker_id,
                status="COMPLETED" if is_success else "FAILED",
                duration_ms=elapsed_ms,
                result={"exit_code": exit_code, "stdout": stdout[:1000]},
                error_message=stderr[:1000] if stderr else None,
                tenant_id=tenant_id
            )

            # Register metrics for dashboard
            if is_success:
                self.metrics_service.record_recovery_attempt(
                    db, execution_id, mission_id, task_id, tenant_id,
                    attempt_number, worker_id, fencing_token,
                    failure_classification=None,
                    error_message=None,
                    status="COMPLETED",
                    duration_ms=elapsed_ms,
                    next_retry_at=None
                )

            # If failed, classify and potentially retry
            if not is_success and execution.attempt_number < execution.max_attempts:
                classification = self.recovery_service.classify_failure(stderr)
                execution.failure_classification = classification

                if classification == FailureClassification.TRANSIENT:
                    # Schedule retry
                    success, next_retry_at = self.recovery_service.schedule_retry(db, execution_id, fencing_token)
                    execution.status = "QUEUED" if success else "FAILED_PERMANENT"

                    # Register metrics for retry
                    self.metrics_service.record_recovery_attempt(
                        db, execution_id, mission_id, task_id, tenant_id,
                        attempt_number, worker_id, fencing_token,
                        failure_classification=classification,
                        error_message=stderr[:500] if stderr else None,
                        status="QUEUED",
                        duration_ms=elapsed_ms,
                        next_retry_at=next_retry_at
                    )
                    logger.info(f"Execution {execution_id}: Transient failure classified, scheduled for retry")
            elif not is_success:
                # Permanent failure or max attempts reached
                classification = self.recovery_service.classify_failure(stderr)
                execution.failure_classification = classification
                execution.status = "FAILED_PERMANENT"

                # Register metrics for permanent failure
                self.metrics_service.record_recovery_attempt(
                    db, execution_id, mission_id, task_id, tenant_id,
                    attempt_number, worker_id, fencing_token,
                    failure_classification=classification,
                    error_message=stderr[:500] if stderr else None,
                    status="FAILED",
                    duration_ms=elapsed_ms,
                    next_retry_at=None
                )

            # Release lease
            self.recovery_service.release_lease(db, execution_id, fencing_token)

            db.commit()

            # Publish execution.completed event (only if truly completed)
            if is_success or execution.status == "FAILED_PERMANENT":
                publish_event(
                    event_type="execution.completed",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    actor_id=agent_id,
                    execution_id=execution_id,
                    mission_id=mission_id,
                    task_id=task_id,
                    payload={"exit_code": exit_code, "success": is_success, "attempt": attempt_number},
                )

            # Update agent status (ETAPA 3: Check if any other execution is active)
            # If active execution exists → keep WORKING, else → final state (IDLE/ERROR)
            has_other_active = self._has_active_execution(db, tenant_id, agent_id, execution_id)

            if has_other_active:
                # Another execution is active → keep WORKING
                self._update_agent_state(db, tenant_id, agent_id, OperationalState.WORKING.value)
            elif execution.status == "COMPLETED":
                self._update_agent_state(db, tenant_id, agent_id, OperationalState.IDLE.value)
            elif execution.status == "FAILED_PERMANENT":
                self._update_agent_state(db, tenant_id, agent_id, OperationalState.ERROR.value)

            logger.info(f"Execution {execution_id} attempt {attempt_number} completed with code {exit_code}, status={execution.status}")
            return is_success, stdout, stderr, execution_id

        except Exception as e:
            logger.error(f"Execution {execution_id} failed with exception: {e}")

            elapsed_ms = int((time.time() - start_time) * 1000)
            error_str = str(e).lower()

            # PHASE 1: Detect connection errors and mark agent OFFLINE
            # Only mark OFFLINE for connection-related failures, not business logic errors
            is_connection_error = any(keyword in error_str for keyword in [
                "timeout", "connection", "refused", "unreachable", "unavailable",
                "socket", "network", "dns", "failed to connect"
            ])

            if is_connection_error:
                self._update_agent_state(
                    db, tenant_id, agent_id,
                    status=OperationalState.WORKING.value,
                    connectivity_status=ConnectivityState.OFFLINE.value
                )
                logger.warning(f"Agent {agent_id} marked OFFLINE due to connection error")

            # Mark as failed
            execution = db.query(Execution).filter(Execution.execution_id == execution_id).first()
            if execution:
                execution.error = str(e)

                # B3 ETAPA 1: Classify failure (TRANSIENT, PERMANENT, UNKNOWN)
                failure_class = self.recovery_service.classify_failure(str(e))
                execution.failure_classification = failure_class

                # Determine if should retry
                should_retry = self.recovery_service.retry_policy.should_retry(
                    failure_class, attempt_number
                )

                if should_retry:
                    # Schedule retry (TRANSIENT failure, attempts left)
                    execution.status = "RESERVED"  # Awaiting retry
                    next_retry_delay_ms = self.recovery_service.retry_policy.calculate_delay(attempt_number)
                    execution.next_retry_at = utc_now() + timedelta(milliseconds=next_retry_delay_ms)
                    logger.info(f"Execution {execution_id} scheduled for retry in {next_retry_delay_ms}ms")
                else:
                    # Mark as failed permanently
                    execution.status = "FAILED"
                    execution.completed_at = utc_now()
                    logger.warning(f"Execution {execution_id} marked FAILED (class={failure_class})")

                # Register attempt for auditoria
                if fencing_token:
                    self.recovery_service.record_attempt(
                        db, execution_id, attempt_number,
                        fencing_token, worker_id,
                        status="FAILED",
                        duration_ms=elapsed_ms,
                        error_message=str(e),
                        failure_classification=execution.failure_classification,
                        tenant_id=tenant_id
                    )

                    # Register metrics for exception
                    self.metrics_service.record_recovery_attempt(
                        db, execution_id, mission_id, task_id, tenant_id,
                        attempt_number, worker_id, fencing_token,
                        failure_classification=execution.failure_classification,
                        error_message=str(e)[:500],
                        status="FAILED",
                        duration_ms=elapsed_ms,
                        next_retry_at=None
                    )

                    # Release lease
                    self.recovery_service.release_lease(db, execution_id, fencing_token)

                db.commit()

            # Publish execution.failed event
            publish_event(
                event_type="execution.failed",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=agent_id,
                execution_id=execution_id,
                mission_id=mission_id,
                task_id=task_id,
                payload={"error": str(e), "attempt": attempt_number},
            )

            # Update agent status to ERROR (business logic errors, not connection)
            self._update_agent_state(db, tenant_id, agent_id, OperationalState.ERROR.value)

            return False, "", str(e)

        finally:
            # PHASE 1: Safety check - ensure agent is never left in WORKING state
            # This is a guard against premature termination/interruption
            try:
                agent = AgentRegistry.get_agent(agent_id, db)
                if agent and agent.status == OperationalState.WORKING.value:
                    logger.warning(f"Agent {agent_id} was still in WORKING state at finally block")
                    logger.warning(f"  This may indicate execution was interrupted unexpectedly")
                    # Mark as ERROR since we don't know the state
                    self._update_agent_state(
                        db, tenant_id, agent_id, OperationalState.ERROR.value
                    )
            except Exception as cleanup_err:
                logger.error(f"Error in finally cleanup for agent {agent_id}: {cleanup_err}")

            db.close()

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        adapter = self.adapters.get("claude-code-cli")
        if adapter:
            return adapter.cancel(execution_id)
        return False
