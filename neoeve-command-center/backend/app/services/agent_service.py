"""Agent queries and business logic."""

from typing import List, Optional
from sqlalchemy.orm import Session

from ...database.models import Agent
from .base import BaseService


class AgentService(BaseService[Agent]):
    """Service for Agent queries with multi-tenant safety."""

    def __init__(self, db: Session):
        """Initialize with Agent model."""
        super().__init__(Agent, db)

    def get_agent(self, tenant_id: str, agent_id: str) -> Optional[Agent]:
        """
        Get agent by ID.

        Note: Agents are global, but we can optionally scope by tenant
        if tenants have dedicated agents in future.
        """
        try:
            return self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        except Exception as e:
            self.logger.error(f"Error fetching agent {agent_id}: {e}")
            return None

    def list_by_role(
        self,
        role: str,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[List[Agent], int]:
        """
        List agents by role.

        Args:
            role: Agent role to filter by
            page: Page number
            per_page: Items per page

        Returns:
            (agents, total_count) tuple
        """
        try:
            query = self.db.query(Agent).filter(Agent.agent_role == role)
            total = query.count()

            agents = (
                query.order_by(Agent.updated_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return agents, total
        except Exception as e:
            self.logger.error(f"Error listing agents by role {role}: {e}")
            return [], 0

    def list_by_status(
        self,
        status: str,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[List[Agent], int]:
        """List agents by status."""
        try:
            query = self.db.query(Agent).filter(Agent.status == status)
            total = query.count()

            agents = (
                query.order_by(Agent.updated_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return agents, total
        except Exception as e:
            self.logger.error(f"Error listing agents by status {status}: {e}")
            return [], 0

    def list_all(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[List[Agent], int]:
        """
        List all agents with pagination.

        Note: Since agents are global system entities, we don't filter by tenant.
        """
        try:
            query = self.db.query(Agent)
            total = query.count()

            agents = (
                query.order_by(Agent.updated_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return agents, total
        except Exception as e:
            self.logger.error("Error listing all agents: {e}")
            return [], 0
