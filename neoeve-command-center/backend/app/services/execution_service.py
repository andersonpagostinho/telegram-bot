"""Execution queries and business logic."""

from typing import List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from ..database.models import Execution, Mission
from .base import BaseService


class ExecutionService(BaseService[Execution]):
    """Service for Execution queries with multi-tenant safety."""

    def __init__(self, db: Session):
        """Initialize with Execution model."""
        super().__init__(Execution, db)

    def get_execution(
        self,
        tenant_id: str,
        execution_id: str,
    ) -> Optional[Execution]:
        """
        Get execution by ID with tenant validation.

        Args:
            tenant_id: Tenant ID from JWT
            execution_id: Execution to fetch

        Returns:
            Execution or None if not found/not authorized
        """
        try:
            execution = (
                self.db.query(Execution)
                .filter(Execution.execution_id == execution_id)
                .first()
            )

            if not execution:
                return None

            # Validate execution belongs to tenant via mission
            mission = (
                self.db.query(Mission)
                .filter(
                    Mission.mission_id == execution.mission_id,
                    Mission.tenant_id == tenant_id,
                )
                .first()
            )

            if not mission:
                self.logger.warning(
                    f"Access denied: Execution {execution_id} belongs to different tenant"
                )
                return None

            return execution
        except Exception as e:
            self.logger.error(f"Error fetching execution {execution_id}: {e}")
            return None

    def list_executions(
        self,
        tenant_id: str,
        page: int = 1,
        per_page: int = 20,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        days: int = 30,
    ) -> tuple[List[Execution], int]:
        """
        List executions for tenant with optional filters.

        Args:
            tenant_id: Tenant ID from JWT
            page: Page number
            per_page: Items per page
            agent_id: Filter by agent (optional)
            task_id: Filter by task (optional)
            status: Filter by status (optional)
            days: Look back N days (default 30)

        Returns:
            (executions, total_count) tuple
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            # Join with Mission to validate tenant
            query = (
                self.db.query(Execution)
                .join(Mission, Execution.mission_id == Mission.mission_id)
                .filter(
                    Mission.tenant_id == tenant_id,
                    Execution.queued_at >= cutoff,
                )
            )

            if agent_id:
                query = query.filter(Execution.agent_id == agent_id)

            if task_id:
                query = query.filter(Execution.task_id == task_id)

            if status:
                query = query.filter(Execution.status == status)

            total = query.count()

            executions = (
                query.order_by(Execution.queued_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return executions, total
        except Exception as e:
            self.logger.error(f"Error listing executions: {e}")
            return [], 0

    def get_agent_executions(
        self,
        tenant_id: str,
        agent_id: str,
        limit: int = 10,
    ) -> List[Execution]:
        """Get recent executions for an agent."""
        try:
            return (
                self.db.query(Execution)
                .join(Mission, Execution.mission_id == Mission.mission_id)
                .filter(
                    Mission.tenant_id == tenant_id,
                    Execution.agent_id == agent_id,
                )
                .order_by(Execution.queued_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error fetching executions for agent {agent_id}: {e}")
            return []
