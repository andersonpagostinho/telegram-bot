"""Base service class with common query patterns."""

import logging
from typing import Generic, TypeVar, Optional, List
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")  # Model type
S = TypeVar("S")  # Schema type


class BaseService(Generic[T]):
    """
    Base service with common query patterns.

    All queries MUST filter by tenant_id (and project_id if applicable).
    This is enforced at the service level, not just at the endpoint.
    """

    def __init__(self, model: type[T], db: Session):
        """
        Initialize service.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db
        self.logger = logger

    def get_by_id(
        self,
        tenant_id: str,
        resource_id: str,
        project_id: Optional[str] = None,
    ) -> Optional[T]:
        """
        Get single resource by ID with tenant validation.

        SECURITY: Always validates tenant_id.

        Args:
            tenant_id: Tenant ID from JWT
            resource_id: Resource ID to fetch
            project_id: Project ID (if applicable)

        Returns:
            Resource or None if not found/not authorized
        """
        try:
            query = self.db.query(self.model).filter(
                self.model.id == resource_id,
                self.model.tenant_id == tenant_id,
            )

            if project_id and hasattr(self.model, "project_id"):
                query = query.filter(self.model.project_id == project_id)

            return query.first()
        except Exception as e:
            self.logger.error(f"Error fetching {self.model.__name__}: {e}")
            return None

    def list_paginated(
        self,
        tenant_id: str,
        page: int = 1,
        per_page: int = 20,
        project_id: Optional[str] = None,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> tuple[List[T], int]:
        """
        List resources with pagination and optional filters.

        SECURITY: Always filters by tenant_id.

        Args:
            tenant_id: Tenant ID from JWT
            page: Page number (1-indexed)
            per_page: Items per page
            project_id: Project ID (if applicable)
            filters: Additional filter dict (column=value pairs)
            sort_by: Sort field name
            sort_order: "asc" or "desc"

        Returns:
            (resources, total_count) tuple
        """
        try:
            query = self.db.query(self.model).filter(
                self.model.tenant_id == tenant_id
            )

            if project_id and hasattr(self.model, "project_id"):
                query = query.filter(self.model.project_id == project_id)

            # Apply additional filters
            if filters:
                for column_name, value in filters.items():
                    if hasattr(self.model, column_name):
                        column = getattr(self.model, column_name)
                        if value is not None:
                            query = query.filter(column == value)

            # Count total before pagination
            total = query.count()

            # Sort
            if sort_by and hasattr(self.model, sort_by):
                column = getattr(self.model, sort_by)
                if sort_order == "asc":
                    query = query.order_by(column.asc())
                else:
                    query = query.order_by(column.desc())
            elif hasattr(self.model, "created_at"):
                # Default sort by created_at descending
                if sort_order == "asc":
                    query = query.order_by(self.model.created_at.asc())
                else:
                    query = query.order_by(self.model.created_at.desc())

            # Pagination
            offset = (page - 1) * per_page
            resources = query.offset(offset).limit(per_page).all()

            return resources, total
        except Exception as e:
            self.logger.error(f"Error listing {self.model.__name__}: {e}")
            return [], 0

    def get_recent(
        self,
        tenant_id: str,
        limit: int = 10,
        project_id: Optional[str] = None,
        days: int = 7,
    ) -> List[T]:
        """
        Get recent resources within time window.

        Args:
            tenant_id: Tenant ID from JWT
            limit: Max results to return
            project_id: Project ID (if applicable)
            days: Look back N days

        Returns:
            List of recent resources
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            query = self.db.query(self.model).filter(
                self.model.tenant_id == tenant_id,
                self.model.created_at >= cutoff,
            )

            if project_id and hasattr(self.model, "project_id"):
                query = query.filter(self.model.project_id == project_id)

            return (
                query.order_by(self.model.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error getting recent {self.model.__name__}: {e}")
            return []

    def count(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
    ) -> int:
        """
        Count resources for tenant.

        Args:
            tenant_id: Tenant ID from JWT
            project_id: Project ID (if applicable)

        Returns:
            Number of resources
        """
        try:
            query = self.db.query(func.count(self.model.id)).filter(
                self.model.tenant_id == tenant_id
            )

            if project_id and hasattr(self.model, "project_id"):
                query = query.filter(self.model.project_id == project_id)

            return query.scalar() or 0
        except Exception as e:
            self.logger.error(f"Error counting {self.model.__name__}: {e}")
            return 0
