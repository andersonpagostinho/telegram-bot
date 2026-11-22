"""Execution endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...core import get_db, get_current_user, Identity
from ...schemas.execution import ExecutionResponse, ExecutionListResponse
from ...services.execution_service import ExecutionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/executions", tags=["executions"])


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
