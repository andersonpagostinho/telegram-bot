"""Validation endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core import get_db, get_current_user, Identity
from app.schemas.validation import ValidationResponse, ValidationListResponse
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validations", tags=["validations"])


@router.get("", response_model=ValidationListResponse)
async def list_validations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    mission_id: Optional[str] = Query(None, description="Filter by mission"),
    validator: Optional[str] = Query(None, description="Filter by validator type"),
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    List validations for authenticated tenant.

    SECURITY: Results filtered by tenant via mission relationship.
    """
    try:
        service = ValidationService(db)

        validations, total = service.list_validations(
            tenant_id=current_user.tenant_id,
            page=page,
            per_page=per_page,
            mission_id=mission_id,
            validator=validator,
            verdict=verdict,
        )

        logger.info(
            f"Listed {len(validations)} validations for tenant={current_user.tenant_id} "
            f"(user={current_user.user_id})"
        )

        return ValidationListResponse(
            total=total,
            validations=[ValidationResponse.model_validate(v) for v in validations],
        )
    except Exception as e:
        logger.error(f"Error listing validations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list validations",
        )


@router.get("/{validation_id}", response_model=ValidationResponse)
async def get_validation(
    validation_id: str,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_user),
):
    """
    Get specific validation by ID with multi-tenant validation.
    """
    try:
        service = ValidationService(db)
        validation = service.get_validation(
            tenant_id=current_user.tenant_id,
            validation_id=validation_id,
        )

        if not validation:
            logger.warning(
                f"Validation access denied: {validation_id} (user={current_user.user_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        logger.info(f"Retrieved validation {validation_id} (user={current_user.user_id})")

        return ValidationResponse.model_validate(validation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving validation {validation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation",
        )
