"""Task queries and business logic."""

from typing import List, Optional
from sqlalchemy.orm import Session

from ..database.models import Task, Mission
from .base import BaseService


class TaskService(BaseService[Task]):
    """Service for Task queries with multi-tenant safety."""

    def __init__(self, db: Session):
        """Initialize with Task model."""
        super().__init__(Task, db)

    def get_task(
        self,
        tenant_id: str,
        task_id: str,
    ) -> Optional[Task]:
        """
        Get task by ID with tenant validation.

        Args:
            tenant_id: Tenant ID from JWT
            task_id: Task to fetch

        Returns:
            Task or None if not found/not authorized
        """
        try:
            task = (
                self.db.query(Task)
                .filter(Task.task_id == task_id)
                .first()
            )

            if not task:
                return None

            # Validate task belongs to tenant via mission
            mission = (
                self.db.query(Mission)
                .filter(
                    Mission.mission_id == task.mission_id,
                    Mission.tenant_id == tenant_id,
                )
                .first()
            )

            if not mission:
                self.logger.warning(
                    f"Access denied: Task {task_id} belongs to different tenant"
                )
                return None

            return task
        except Exception as e:
            self.logger.error(f"Error fetching task {task_id}: {e}")
            return None

    def list_tasks(
        self,
        tenant_id: str,
        page: int = 1,
        per_page: int = 20,
        mission_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[List[Task], int]:
        """
        List tasks for tenant with optional filters.

        Args:
            tenant_id: Tenant ID from JWT
            page: Page number
            per_page: Items per page
            mission_id: Filter by mission (optional)
            agent_id: Filter by assigned agent (optional)
            status: Filter by status (optional)

        Returns:
            (tasks, total_count) tuple
        """
        try:
            # Join with Mission to validate tenant
            query = (
                self.db.query(Task)
                .join(Mission, Task.mission_id == Mission.mission_id)
                .filter(Mission.tenant_id == tenant_id)
            )

            if mission_id:
                query = query.filter(Task.mission_id == mission_id)

            if agent_id:
                query = query.filter(Task.assigned_agent == agent_id)

            if status:
                query = query.filter(Task.status == status)

            total = query.count()

            tasks = (
                query.order_by(Task.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return tasks, total
        except Exception as e:
            self.logger.error(f"Error listing tasks: {e}")
            return [], 0
