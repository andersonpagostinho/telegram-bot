"""REST API routes for Approval Engine."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database.models import Validation
from app.services.approval_engine_pg import ApprovalEnginePG
from app.core.security import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.post("/request")
def request_approval(
    mission_id: str,
    task_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Request approval for mission or task."""
    # SECURITY: tenant_id and project_id MUST come from JWT, never from request
    tenant_id = current_user.get("tenant_id")
    project_id = current_user.get("project_id")

    engine = ApprovalEnginePG(db)
    approval_id = engine.request_approval(
        mission_id=mission_id,
        task_id=task_id,
        tenant_id=tenant_id,
        project_id=project_id,
        requested_by=current_user["user_id"],
        actor_id=current_user["user_id"],
    )

    if not approval_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    return {"approval_id": approval_id, "status": "PENDING"}


@router.post("/{approval_id}/approve")
def approve_decision(
    approval_id: str,
    justification: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Approve an approval request."""
    # SECURITY: tenant_id and project_id MUST come from JWT, never from request
    tenant_id = current_user.get("tenant_id")
    project_id = current_user.get("project_id")

    engine = ApprovalEnginePG(db)
    success = engine.approve(
        approval_id=approval_id,
        validator_agent_id=current_user["user_id"],
        justification=justification,
        tenant_id=tenant_id,
        project_id=project_id,
        actor_id=current_user["user_id"],
    )

    if not success:
        raise HTTPException(status_code=409, detail="Cannot approve - already decided")

    return {"approval_id": approval_id, "status": "APPROVED"}


@router.post("/{approval_id}/reject")
def reject_decision(
    approval_id: str,
    justification: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Reject an approval request."""
    # SECURITY: tenant_id and project_id MUST come from JWT, never from request
    tenant_id = current_user.get("tenant_id")
    project_id = current_user.get("project_id")

    engine = ApprovalEnginePG(db)
    success = engine.reject(
        approval_id=approval_id,
        validator_agent_id=current_user["user_id"],
        justification=justification,
        tenant_id=tenant_id,
        project_id=project_id,
        actor_id=current_user["user_id"],
    )

    if not success:
        raise HTTPException(status_code=409, detail="Cannot reject - already decided")

    return {"approval_id": approval_id, "status": "BLOCKED"}


@router.get("/{approval_id}")
def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get approval status."""
    # SECURITY: tenant_id MUST come from JWT, never from request
    tenant_id = current_user.get("tenant_id")

    validation = db.query(Validation).filter(
        Validation.validation_id == approval_id
    ).first()

    if not validation:
        raise HTTPException(status_code=404, detail="Approval not found")

    return {
        "approval_id": validation.validation_id,
        "mission_id": validation.mission_id,
        "task_id": validation.task_id,
        "verdict": validation.verdict,
        "confidence": validation.confidence,
        "created_at": validation.created_at.isoformat() if validation.created_at else None,
    }


@router.get("/mission/{mission_id}/approvals")
def list_mission_approvals(
    mission_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all approvals for a mission."""
    # SECURITY: tenant_id MUST come from JWT, never from request
    tenant_id = current_user.get("tenant_id")

    validations = db.query(Validation).filter(
        Validation.mission_id == mission_id
    ).all()

    return [
        {
            "approval_id": v.validation_id,
            "mission_id": v.mission_id,
            "verdict": v.verdict,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in validations
    ]
