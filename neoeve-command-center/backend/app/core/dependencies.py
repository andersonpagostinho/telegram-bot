"""
Dependency injection for FastAPI routes.
Database sessions, authentication, and common utilities.
"""

import logging
from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from .security import get_current_user, Identity

logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def get_current_tenant(current_user: Identity = Depends(get_current_user)) -> str:
    """
    Get authenticated tenant_id.

    CRITICAL: This extracts tenant_id from JWT, never from request.
    All queries must be filtered by this tenant_id.

    Usage:
        @app.get("/missions")
        def list_missions(tenant_id: str = Depends(get_current_tenant)):
            return db.query(Mission).filter_by(tenant_id=tenant_id).all()
    """
    return current_user.tenant_id


async def get_current_project(current_user: Identity = Depends(get_current_user)) -> tuple[str, str]:
    """
    Get authenticated tenant_id and project_id.

    For endpoints that need both tenant and project scope.

    Returns:
        (tenant_id, project_id) tuple from current user

    Usage:
        @app.get("/missions")
        def list_missions(scope: tuple = Depends(get_current_project)):
            tenant_id, project_id = scope
            return db.query(Mission).filter_by(
                tenant_id=tenant_id,
                project_id=project_id
            ).all()
    """
    # For now, tenant and project are linked 1:1 in JWT
    # Can be extended if multi-project per tenant needed
    return (current_user.tenant_id, current_user.actor_role)
