"""Mission queries and business logic."""

from typing import List, Optional
from sqlalchemy.orm import Session

from ..database.models import Mission, AgentEvent
from .base import BaseService


class MissionService(BaseService[Mission]):
    """Service for Mission queries with multi-tenant safety."""

    def __init__(self, db: Session):
        """Initialize with Mission model."""
        super().__init__(Mission, db)

    def get_mission(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
    ) -> Optional[Mission]:
        """
        Get mission by ID with multi-tenant validation.

        Args:
            tenant_id: Tenant ID from JWT
            project_id: Project ID from JWT
            mission_id: Mission to fetch

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
            self.logger.error(f"Error fetching mission {mission_id}: {e}")
            return None

    def list_missions(
        self,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        days: Optional[int] = None,
    ) -> tuple[List[Mission], int]:
        """
        List missions for tenant/project with optional filters.

        Args:
            tenant_id: Tenant ID from JWT
            project_id: Project ID from JWT
            page: Page number
            per_page: Items per page
            status: Filter by status (optional)
            days: Filter by created in last N days (optional)

        Returns:
            (missions, total_count) tuple
        """
        try:
            query = (
                self.db.query(Mission)
                .filter(
                    Mission.tenant_id == tenant_id,
                    Mission.project_id == project_id,
                )
            )

            if status:
                query = query.filter(Mission.status == status)

            if days:
                from datetime import datetime, timedelta, timezone
                cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                query = query.filter(Mission.created_at >= cutoff)

            total = query.count()

            missions = (
                query.order_by(Mission.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return missions, total
        except Exception as e:
            self.logger.error(f"Error listing missions: {e}")
            return [], 0

    def get_mission_events(
        self,
        tenant_id: str,
        mission_id: str,
        limit: int = 50,
    ) -> List[AgentEvent]:
        """
        Get recent events for a mission.

        Args:
            tenant_id: Tenant ID from JWT
            mission_id: Mission ID
            limit: Max events to return

        Returns:
            List of recent events
        """
        try:
            return (
                self.db.query(AgentEvent)
                .filter(
                    AgentEvent.mission_id == mission_id,
                    AgentEvent.tenant_id == tenant_id,
                )
                .order_by(AgentEvent.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error fetching events for mission {mission_id}: {e}")
            return []
