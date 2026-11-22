"""Mission endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...core import get_db, get_current_user, Identity
from ...schemas.mission import MissionResponse, MissionListResponse, MissionEventResponse
from ...services.mission_service import MissionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("", response_model=MissionListResponse)
async def list_missions(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    days: Optional[int] = Query(None, ge=1, description="Filter by created in last N days"),
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    List missions for authenticated tenant/project.

    SECURITY: Tenant and project are from JWT, never from request parameters.
    """
    try:
        service = MissionService(db)

        missions, total = service.list_missions(
            tenant_id=current_user.tenant_id,
            project_id=current_user.actor_role,  # Using actor_role as project for now
            page=page,
            per_page=per_page,
            status=status_filter,
            days=days,
        )

        logger.info(
            f"Listed {len(missions)} missions for tenant={current_user.tenant_id} "
            f"(user={current_user.user_id})"
        )

        return MissionListResponse(
            total=total,
            missions=[MissionResponse.model_validate(m) for m in missions],
        )
    except Exception as e:
        logger.error(f"Error listing missions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list missions",
        )


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: str,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get specific mission by ID with multi-tenant validation.

    SECURITY: Returns 403 Forbidden (not 404) if mission belongs to different tenant.
    """
    try:
        service = MissionService(db)
        mission = service.get_mission(
            tenant_id=current_user.tenant_id,
            project_id=current_user.actor_role,
            mission_id=mission_id,
        )

        if not mission:
            logger.warning(
                f"Mission access denied or not found: {mission_id} "
                f"(tenant={current_user.tenant_id})"
            )
            # Return 403 (Forbidden) instead of 404 to prevent information leakage
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        logger.info(
            f"Retrieved mission {mission_id} for tenant={current_user.tenant_id} "
            f"(user={current_user.user_id})"
        )

        return MissionResponse.model_validate(mission)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving mission {mission_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve mission",
        )


@router.get("/{mission_id}/events", response_model=list[MissionEventResponse])
async def get_mission_events(
    mission_id: str,
    limit: int = Query(50, ge=1, le=100, description="Max events to return"),
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get event stream for a mission.

    SECURITY: Validates mission belongs to authenticated tenant before returning events.
    """
    try:
        service = MissionService(db)

        # Verify mission exists and belongs to tenant
        mission = service.get_mission(
            tenant_id=current_user.tenant_id,
            project_id=current_user.actor_role,
            mission_id=mission_id,
        )

        if not mission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get events for mission
        events = service.get_mission_events(
            tenant_id=current_user.tenant_id,
            mission_id=mission_id,
            limit=limit,
        )

        logger.info(
            f"Retrieved {len(events)} events for mission {mission_id} "
            f"(user={current_user.user_id})"
        )

        return [
            MissionEventResponse(
                event_id=e.event_id,
                event_type=e.event_type,
                source_agent=e.source_agent,
                created_at=e.created_at,
                payload_summary=e.payload_summary,
            )
            for e in events
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving events for mission {mission_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve events",
        )
