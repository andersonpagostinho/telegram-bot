"""Mission Engine: coordinates missions, decomposes into tasks, delegates to agents."""

import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Set
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import Mission, Task, Execution, Agent
from app.services.agent_registry import (
    AgentRegistry,
    AgentRole,
    Permission,
    OperationalState,
)
from app.services.event_bus import publish_event
from app.services.agent_runtime import AgentRuntime

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DelegationMatrix:
    """
    Responsibility matrix: which agents can execute which types of tasks.

    Ensures specialized assignment:
    - Backend Developer: implementation
    - Debugger: investigation
    - QA Engineer: validation
    - Security Auditor: security review (read-only, can veto)
    - Release Manager: release preparation
    - OpenAI Validator: external validation (read-only)
    - Architect: planning and decomposition
    """

    TASK_TYPE_TO_ROLES = {
        "implement": {AgentRole.BACKEND_DEVELOPER, AgentRole.ARCHITECT},
        "refactor": {AgentRole.BACKEND_DEVELOPER, AgentRole.ARCHITECT},
        "test": {AgentRole.QA_ENGINEER, AgentRole.ARCHITECT},
        "debug": {AgentRole.DEBUGGER, AgentRole.ARCHITECT},
        "audit": {AgentRole.SECURITY_AUDITOR, AgentRole.ARCHITECT},
        "release": {AgentRole.RELEASE_MANAGER, AgentRole.ARCHITECT},
        "validate": {AgentRole.OPENAI_VALIDATOR, AgentRole.ARCHITECT},
        "plan": {AgentRole.ARCHITECT},
        "decompose": {AgentRole.ARCHITECT},
    }

    @staticmethod
    def can_assign(task_type: str, agent_id: str) -> bool:
        """Check if agent can execute task type."""
        allowed_roles = DelegationMatrix.TASK_TYPE_TO_ROLES.get(task_type, set())

        for key, config in AgentRegistry.AGENTS.items():
            if config["agent_id"] == agent_id:
                return config["role"] in allowed_roles

        return False


class MissionEngine:
    """Central mission coordination engine."""

    def __init__(self, db: Session):
        """Initialize engine with database session."""
        self.db = db
        self.runtime = AgentRuntime()
        logger.info("Mission Engine initialized")

    # =========================================================================
    # MISSION OPERATIONS
    # =========================================================================

    def create_mission(
        self,
        mission_id: Optional[str] = None,
        name: str = None,
        tenant_id: str = None,
        project_id: str = None,
        actor_id: str = None,
    ) -> Optional[Mission]:
        """
        Create new mission.

        Args:
            mission_id: Optional mission ID (generated if not provided)
            name: Mission name/title
            tenant_id: Tenant/Organization ID
            project_id: Project ID
            actor_id: Creating agent/user

        Returns:
            Mission object or None if validation fails
        """
        if not name or not tenant_id or not project_id:
            logger.warning("Missing required fields for mission creation")
            return None

        try:
            mission_id = mission_id or str(uuid4())

            mission = Mission(
                mission_id=mission_id,
                project_id=project_id,
                tenant_id=tenant_id,
                name=name,
                status="PENDING",
                created_at=datetime.now(timezone.utc),
            )

            self.db.add(mission)
            self.db.commit()

            # Publish event
            publish_event(
                event_type="mission.created",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id or "system",
                mission_id=mission_id,
                payload={
                    "mission_id": mission_id,
                    "name": name,
                    "status": "PENDING",
                },
                idempotency_key=f"mission.created.{mission_id}",
            )

            logger.info(f"Mission created: {mission_id} ({name})")
            return mission

        except Exception as e:
            logger.error(f"Error creating mission: {e}")
            self.db.rollback()
            return None

    def get_mission(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
    ) -> Optional[Mission]:
        """
        Get mission by ID with multi-tenant validation.

        Returns:
            Mission or None if not found/not authorized
        """
        try:
            return (
                self.db.query(Mission)
                .filter(
                    Mission.mission_id == mission_id,
                    Mission.tenant_id == tenant_id,
                    Mission.project_id == project_id,
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching mission {mission_id}: {e}")
            return None

    def decompose_mission(
        self,
        mission_id: str,
        tenant_id: str,
        project_id: str,
        task_decomposition: List[Dict],
        actor_id: str,
    ) -> List[Task]:
        """
        Decompose mission into tasks.

        Args:
            mission_id: Mission to decompose
            tenant_id: Tenant ID
            project_id: Project ID
            task_decomposition: List of task defs:
                [
                    {
                        "task_id": "...",
                        "description": "...",
                        "task_type": "implement|debug|test|...",
                        "priority": "LOW|NORMAL|HIGH|CRITICAL",
                        "dependencies": ["task_id1", "task_id2"],
                    },
                    ...
                ]
            actor_id: Creating agent

        Returns:
            List of created Task objects
        """
        mission = self.get_mission(tenant_id, project_id, mission_id)
        if not mission:
            logger.warning(f"Mission not found: {mission_id}")
            return []

        created_tasks = []

        try:
            for task_def in task_decomposition:
                task_id = task_def.get("task_id") or str(uuid4())
                description = task_def.get("description", "")
                task_type = task_def.get("task_type", "implement")
                priority = task_def.get("priority", "NORMAL")
                dependencies = task_def.get("dependencies", [])

                task = Task(
                    task_id=task_id,
                    mission_id=mission_id,
                    assigned_agent=None,  # Not assigned yet
                    status="PENDING",
                    priority=priority,
                    created_at=datetime.now(timezone.utc),
                    result={"description": description, "task_type": task_type, "dependencies": dependencies},
                )

                self.db.add(task)
                created_tasks.append(task)

            self.db.commit()

            # Publish event
            publish_event(
                event_type="mission.decomposed",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=mission_id,
                payload={
                    "mission_id": mission_id,
                    "task_count": len(created_tasks),
                    "task_ids": [t.task_id for t in created_tasks],
                },
                idempotency_key=f"mission.decomposed.{mission_id}",
            )

            logger.info(f"Mission {mission_id} decomposed into {len(created_tasks)} tasks")
            return created_tasks

        except Exception as e:
            logger.error(f"Error decomposing mission: {e}")
            self.db.rollback()
            return []

    def start_mission(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
        actor_id: str,
    ) -> bool:
        """
        Start mission execution.

        Returns:
            True if successful, False otherwise
        """
        mission = self.get_mission(tenant_id, project_id, mission_id)
        if not mission:
            logger.warning(f"Mission not found: {mission_id}")
            return False

        if mission.status != "PENDING":
            logger.warning(f"Mission {mission_id} not in PENDING state: {mission.status}")
            return False

        try:
            mission.status = "RUNNING"
            mission.started_at = datetime.now(timezone.utc)
            self.db.commit()

            publish_event(
                event_type="mission.started",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=mission_id,
                payload={"mission_id": mission_id, "status": "RUNNING"},
                idempotency_key=f"mission.started.{mission_id}",
            )

            logger.info(f"Mission {mission_id} started")
            return True

        except Exception as e:
            logger.error(f"Error starting mission: {e}")
            self.db.rollback()
            return False

    def pause_mission(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
        actor_id: str,
    ) -> bool:
        """
        Pause mission execution.

        Returns:
            True if successful, False otherwise
        """
        mission = self.get_mission(tenant_id, project_id, mission_id)
        if not mission:
            return False

        if mission.status not in ["RUNNING", "BLOCKED"]:
            logger.warning(f"Cannot pause mission {mission_id} in state {mission.status}")
            return False

        try:
            mission.status = "PAUSED"
            self.db.commit()

            publish_event(
                event_type="mission.paused",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=mission_id,
                payload={"mission_id": mission_id, "status": "PAUSED"},
                idempotency_key=f"mission.paused.{mission_id}",
            )

            logger.info(f"Mission {mission_id} paused")
            return True

        except Exception as e:
            logger.error(f"Error pausing mission: {e}")
            self.db.rollback()
            return False

    def resume_mission(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
        actor_id: str,
    ) -> bool:
        """
        Resume mission execution from pause.

        Returns:
            True if successful, False otherwise
        """
        mission = self.get_mission(tenant_id, project_id, mission_id)
        if not mission:
            return False

        if mission.status != "PAUSED":
            logger.warning(f"Cannot resume mission {mission_id} not in PAUSED state")
            return False

        try:
            mission.status = "RUNNING"
            self.db.commit()

            publish_event(
                event_type="mission.resumed",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=mission_id,
                payload={"mission_id": mission_id, "status": "RUNNING"},
                idempotency_key=f"mission.resumed.{mission_id}",
            )

            logger.info(f"Mission {mission_id} resumed")
            return True

        except Exception as e:
            logger.error(f"Error resuming mission: {e}")
            self.db.rollback()
            return False

    def cancel_mission(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
        actor_id: str,
    ) -> bool:
        """
        Cancel mission and all pending tasks.

        Returns:
            True if successful, False otherwise
        """
        mission = self.get_mission(tenant_id, project_id, mission_id)
        if not mission:
            return False

        try:
            mission.status = "CANCELLED"
            mission.completed_at = datetime.now(timezone.utc)

            # Cancel all pending tasks
            pending_tasks = self.db.query(Task).filter(
                Task.mission_id == mission_id,
                Task.status == "PENDING",
            ).all()

            for task in pending_tasks:
                task.status = "CANCELLED"
                task.completed_at = datetime.now(timezone.utc)

            self.db.commit()

            publish_event(
                event_type="mission.cancelled",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=mission_id,
                payload={"mission_id": mission_id, "status": "CANCELLED"},
                idempotency_key=f"mission.cancelled.{mission_id}",
            )

            logger.info(f"Mission {mission_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"Error cancelling mission: {e}")
            self.db.rollback()
            return False

    def get_mission_status(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
    ) -> Optional[Dict]:
        """
        Get mission status with task breakdown.

        Returns:
            Status dictionary or None
        """
        mission = self.get_mission(tenant_id, project_id, mission_id)
        if not mission:
            return None

        try:
            tasks = self.db.query(Task).filter(Task.mission_id == mission_id).all()

            task_counts = {
                "PENDING": len([t for t in tasks if t.status == "PENDING"]),
                "STARTED": len([t for t in tasks if t.status == "STARTED"]),
                "COMPLETED": len([t for t in tasks if t.status == "COMPLETED"]),
                "FAILED": len([t for t in tasks if t.status == "FAILED"]),
                "BLOCKED": len([t for t in tasks if t.status == "BLOCKED"]),
            }

            return {
                "mission_id": mission.mission_id,
                "name": mission.name,
                "status": mission.status,
                "created_at": mission.created_at.isoformat() if mission.created_at else None,
                "started_at": mission.started_at.isoformat() if mission.started_at else None,
                "completed_at": mission.completed_at.isoformat() if mission.completed_at else None,
                "task_summary": task_counts,
                "total_tasks": len(tasks),
            }

        except Exception as e:
            logger.error(f"Error getting mission status: {e}")
            return None

    # =========================================================================
    # TASK MANAGEMENT
    # =========================================================================

    def assign_task(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
        task_id: str,
        agent_id: str,
        actor_id: str,
    ) -> bool:
        """
        Assign task to agent with validation.

        Validates:
        - Agent exists and is registered
        - Agent has execute permission
        - Agent has appropriate capabilities
        - Agent executor is configured
        - Task type matches agent capabilities

        Returns:
            True if successful, False if validation fails
        """
        mission = self.get_mission(tenant_id, project_id, mission_id)
        if not mission:
            logger.warning(f"Mission not found: {mission_id}")
            return False

        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return False

        # Validate agent
        agent = AgentRegistry.get_agent(agent_id, self.db)
        if not agent:
            logger.warning(f"Agent not registered: {agent_id}")
            return False

        # Check permissions
        if not AgentRegistry.has_permission(agent_id, Permission.EXECUTE):
            logger.warning(f"Agent {agent_id} lacks EXECUTE permission")
            return False

        # Check executor configuration
        if not agent.runtime:
            logger.warning(f"Agent {agent_id} has no executor configured")
            return False

        # Validate task type matches agent capability
        task_type = task.result.get("task_type", "implement") if task.result else "implement"
        if not DelegationMatrix.can_assign(task_type, agent_id):
            logger.warning(f"Agent {agent_id} cannot execute task type {task_type}")
            return False

        # Check for dependencies
        dependencies = task.result.get("dependencies", []) if task.result else []
        blocked_deps = self._check_blocked_dependencies(mission_id, dependencies)
        if blocked_deps:
            logger.info(f"Task {task_id} has blocked dependencies: {blocked_deps}")
            task.status = "BLOCKED"
            self.db.commit()
            return False

        # Check for duplicate execution
        existing_execution = (
            self.db.query(Execution)
            .filter(
                Execution.task_id == task_id,
                Execution.status.in_(["RUNNING", "COMPLETED"]),
            )
            .first()
        )
        if existing_execution:
            logger.warning(f"Task {task_id} already executed or running")
            return False

        try:
            task.assigned_agent = agent_id
            task.status = "STARTED"
            task.started_at = datetime.now(timezone.utc)
            self.db.commit()

            publish_event(
                event_type="task.assigned",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=mission_id,
                task_id=task_id,
                payload={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "agent_role": agent.agent_role,
                },
                idempotency_key=f"task.assigned.{task_id}.{agent_id}",
            )

            logger.info(f"Task {task_id} assigned to agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            self.db.rollback()
            return False

    def _check_blocked_dependencies(
        self,
        mission_id: str,
        dependencies: List[str],
    ) -> List[str]:
        """
        Check which dependencies are not completed.

        Returns:
            List of blocked task IDs (empty if all dependencies met)
        """
        if not dependencies:
            return []

        blocked = []
        for dep_task_id in dependencies:
            dep_task = self.db.query(Task).filter(Task.task_id == dep_task_id).first()
            if not dep_task:
                blocked.append(dep_task_id)
            elif dep_task.status not in ["COMPLETED", "SKIPPED"]:
                blocked.append(dep_task_id)

        return blocked

    def execute_task(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
        task_id: str,
        agent_id: str,
        task_description: str,
        workspace_path: str,
        timeout_seconds: int = 300,
    ) -> Tuple[bool, str, str]:
        """
        Execute task via AgentRuntime.

        Returns:
            (success, stdout, stderr)
        """
        # Validate authorization
        agent = AgentRegistry.get_agent(agent_id, self.db)
        if not agent:
            logger.error(f"Agent not found: {agent_id}")
            return False, "", "Agent not found"

        if not AgentRegistry.has_permission(agent_id, Permission.EXECUTE):
            logger.error(f"Agent {agent_id} not authorized to execute")
            return False, "", "Permission denied"

        # Execute (B4 ETAPA 3 FIX: capture execution_id from new 4-value return)
        success, stdout, stderr, execution_id = self.runtime.execute_task(
            task_id=task_id,
            agent_id=agent_id,
            task_description=task_description,
            mission_id=mission_id,
            tenant_id=tenant_id,
            project_id=project_id,
            workspace_path=workspace_path,
            timeout_seconds=timeout_seconds,
        )

        # Update task
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if task:
            task.status = "COMPLETED" if success else "FAILED"
            task.completed_at = datetime.now(timezone.utc)
            task.result = {"stdout": stdout[:500]} if success else None
            task.error = stderr[:500] if not success else None
            self.db.commit()

        return success, stdout, stderr
