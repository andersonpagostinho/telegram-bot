"""Agent endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...core import get_db, get_current_user, Identity
from ...schemas.agent import AgentResponse, AgentListResponse
from ...services.agent_service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    role: Optional[str] = Query(None, description="Filter by agent role"),
    status: Optional[str] = Query(None, description="Filter by agent status"),
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    List all agents.

    Agents are global system entities (not tenant-scoped).
    """
    try:
        service = AgentService(db)

        if role and status:
            agents_role, _ = service.list_by_role(role, page=page, per_page=per_page)
            agents_status = [a for a in agents_role if a.status == status]
            # For combined filters, manually paginate
            total = len(agents_status)
            agents = agents_status[:per_page]
        elif role:
            agents, total = service.list_by_role(role, page=page, per_page=per_page)
        elif status:
            agents, total = service.list_by_status(status, page=page, per_page=per_page)
        else:
            agents, total = service.list_all(page=page, per_page=per_page)

        logger.info(f"Listed {len(agents)} agents (user={current_user.user_id})")

        return AgentListResponse(
            total=total,
            agents=[AgentResponse.model_validate(a) for a in agents],
        )
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list agents",
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get specific agent by ID.
    """
    try:
        service = AgentService(db)
        agent = service.get_agent(current_user.tenant_id, agent_id)

        if not agent:
            logger.warning(f"Agent not found: {agent_id} (user={current_user.user_id})")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        logger.info(f"Retrieved agent {agent_id} (user={current_user.user_id})")

        return AgentResponse.model_validate(agent)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent",
        )


@router.get("/{agent_id}/events", response_model=list)
async def get_agent_recent_events(
    agent_id: str,
    limit: int = Query(10, ge=1, le=50, description="Max events to return"),
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get recent events for an agent.
    """
    try:
        from ...database.models import AgentEvent
        from ...schemas.agent import AgentEventResponse

        # Verify agent exists
        service = AgentService(db)
        agent = service.get_agent(current_user.tenant_id, agent_id)

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        # Get recent events for this agent
        events = (
            db.query(AgentEvent)
            .filter(
                AgentEvent.actor_id == agent_id,
                AgentEvent.tenant_id == current_user.tenant_id,
            )
            .order_by(AgentEvent.created_at.desc())
            .limit(limit)
            .all()
        )

        logger.info(
            f"Retrieved {len(events)} events for agent {agent_id} "
            f"(user={current_user.user_id})"
        )

        return [
            AgentEventResponse(
                event_id=e.event_id,
                event_type=e.event_type,
                created_at=e.created_at,
                summary=str(e.payload_summary),
            )
            for e in events
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving events for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve events",
        )
