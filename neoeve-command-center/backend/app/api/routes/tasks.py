"""Task endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...core import get_db, get_current_user, Identity
from ...schemas.task import TaskResponse, TaskListResponse
from ...services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    mission_id: Optional[str] = Query(None, description="Filter by mission"),
    agent_id: Optional[str] = Query(None, description="Filter by assigned agent"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    List tasks for authenticated tenant.

    SECURITY: Results filtered by tenant via mission relationship.
    """
    try:
        service = TaskService(db)

        tasks, total = service.list_tasks(
            tenant_id=current_user.tenant_id,
            page=page,
            per_page=per_page,
            mission_id=mission_id,
            agent_id=agent_id,
            status=status,
        )

        logger.info(
            f"Listed {len(tasks)} tasks for tenant={current_user.tenant_id} "
            f"(user={current_user.user_id})"
        )

        return TaskListResponse(
            total=total,
            tasks=[TaskResponse.model_validate(t) for t in tasks],
        )
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tasks",
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get specific task by ID with multi-tenant validation.
    """
    try:
        service = TaskService(db)
        task = service.get_task(
            tenant_id=current_user.tenant_id,
            task_id=task_id,
        )

        if not task:
            logger.warning(f"Task access denied: {task_id} (user={current_user.user_id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        logger.info(f"Retrieved task {task_id} (user={current_user.user_id})")

        return TaskResponse.model_validate(task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task",
        )
