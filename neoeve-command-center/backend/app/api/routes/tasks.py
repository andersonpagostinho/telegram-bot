"""Task endpoints."""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import get_db, get_current_user, Identity
from app.schemas.task import TaskResponse, TaskListResponse
from app.services.task_service import TaskService
from app.services.event_bus import publish_event
from database.models import Task, utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# B4 ETAPA 2: Request schema for task creation
class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    mission_id: str = Field(..., description="Mission ID this task belongs to")
    name: str = Field(..., min_length=1, max_length=256, description="Task name")
    description: Optional[str] = Field(None, description="Task description")


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Create a new task for a mission.

    B4 ETAPA 2: Task creation with multi-tenant isolation via mission.

    SECURITY: tenant_id from mission context, project_id derived.
    """
    try:
        # B4 ETAPA 2 BLOCKER FIX: Validate Mission ownership before creating Task
        from app.services.mission_service import MissionService

        mission_service = MissionService(db)
        mission = mission_service.get_mission(
            tenant_id=current_user.tenant_id,
            project_id=f"{current_user.tenant_id}_default",
            mission_id=request.mission_id,
        )

        if not mission:
            logger.warning(
                f"Task creation denied: Mission {request.mission_id} "
                f"not found or not accessible by tenant={current_user.tenant_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Mission not found",
            )

        # B4 ETAPA 2: Create task with multi-tenant isolation (Mission validated)
        task_id = f"task_{uuid4().hex[:12]}"
        project_id = f"{current_user.tenant_id}_default"

        task = Task(
            task_id=task_id,
            mission_id=request.mission_id,
            name=request.name,
            status="PENDING",
        )
        db.add(task)
        db.commit()

        # Publish task.created event
        publish_event(
            event_type="task.created",
            tenant_id=current_user.tenant_id,
            project_id=project_id,
            actor_id=current_user.user_id,
            mission_id=request.mission_id,
            task_id=task_id,
            payload={"name": request.name},
        )

        logger.info(
            f"Created task {task_id} for mission={request.mission_id} "
            f"(tenant={current_user.tenant_id})"
        )

        return TaskResponse.from_orm(task)

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


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
