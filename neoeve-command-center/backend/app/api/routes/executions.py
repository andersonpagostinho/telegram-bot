"""Execution endpoints."""

import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core import get_db, get_current_user, Identity
from app.schemas.execution import ExecutionResponse, ExecutionListResponse
from app.services.execution_service import ExecutionService
from app.services.agent_runtime import AgentRuntime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/executions", tags=["executions"])


class ExecutionStartRequest(BaseModel):
    """Request to start a new execution."""
    task_id: str
    agent_id: str
    mission_id: str
    task_description: str
    workspace_path: str
    timeout_seconds: int = 300


class ExecutionStartResponse(BaseModel):
    """Response after starting execution."""
    execution_id: str
    status: str = "RUNNING"
    message: str


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    task_id: Optional[str] = Query(None, description="Filter by task"),
    status: Optional[str] = Query(None, description="Filter by status"),
    days: int = Query(30, ge=1, description="Look back N days"),
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    List executions for authenticated tenant.

    SECURITY: Results filtered by tenant via mission relationship.
    """
    try:
        service = ExecutionService(db)

        executions, total = service.list_executions(
            tenant_id=current_user.tenant_id,
            page=page,
            per_page=per_page,
            agent_id=agent_id,
            task_id=task_id,
            status=status,
            days=days,
        )

        logger.info(
            f"Listed {len(executions)} executions for tenant={current_user.tenant_id} "
            f"(user={current_user.user_id})"
        )

        return ExecutionListResponse(
            total=total,
            executions=[ExecutionResponse.model_validate(e) for e in executions],
        )
    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list executions",
        )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get specific execution by ID with multi-tenant validation.
    """
    try:
        service = ExecutionService(db)
        execution = service.get_execution(
            tenant_id=current_user.tenant_id,
            execution_id=execution_id,
        )

        if not execution:
            logger.warning(
                f"Execution access denied: {execution_id} (user={current_user.user_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        logger.info(f"Retrieved execution {execution_id} (user={current_user.user_id})")

        return ExecutionResponse.model_validate(execution)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve execution",
        )


@router.post("/start", response_model=ExecutionStartResponse)
async def start_execution(
    request: ExecutionStartRequest,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Start a new execution - REAL execution via Claude Code.

    SECURITY: Only authenticated users of the tenant can trigger executions.
    Tenant isolation enforced through mission validation.
    """
    try:
        # Validate mission belongs to current tenant
        from database.models import Mission
        mission = db.query(Mission).filter(
            Mission.mission_id == request.mission_id,
            Mission.tenant_id == current_user.tenant_id,
        ).first()

        if not mission:
            logger.warning(
                f"Mission access denied: {request.mission_id} (user={current_user.user_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mission not found or access denied",
            )

        # Start execution via AgentRuntime (B4 ETAPA 3 FIX: capture real execution_id)
        runtime = AgentRuntime()
        success, stdout, stderr, execution_id = runtime.execute_task(
            task_id=request.task_id,
            agent_id=request.agent_id,
            task_description=request.task_description,
            mission_id=request.mission_id,
            tenant_id=current_user.tenant_id,
            project_id=mission.project_id,
            workspace_path=request.workspace_path,
            timeout_seconds=request.timeout_seconds,
        )

        logger.info(
            f"Started execution {execution_id} for task {request.task_id} "
            f"(agent={request.agent_id}, user={current_user.user_id})"
        )

        return ExecutionStartResponse(
            execution_id=execution_id,  # B4 ETAPA 3 FIX: Use real UUID, not task_id
            status="RUNNING",
            message="Execution started successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start execution",
        )
