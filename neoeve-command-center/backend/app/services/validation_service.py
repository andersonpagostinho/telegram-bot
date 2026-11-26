"""Validation queries and business logic."""

from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import Validation, Mission
from .base import BaseService


class ValidationService(BaseService[Validation]):
    """Service for Validation queries with multi-tenant safety."""

    def __init__(self, db: Session):
        """Initialize with Validation model."""
        super().__init__(Validation, db)

    def get_validation(
        self,
        tenant_id: str,
        validation_id: str,
    ) -> Optional[Validation]:
        """
        Get validation by ID with tenant validation.

        Args:
            tenant_id: Tenant ID from JWT
            validation_id: Validation to fetch

        Returns:
            Validation or None if not found/not authorized
        """
        try:
            validation = (
                self.db.query(Validation)
                .filter(Validation.validation_id == validation_id)
                .first()
            )

            if not validation:
                return None

            # Validate belongs to tenant via mission
            mission = (
                self.db.query(Mission)
                .filter(
                    Mission.mission_id == validation.mission_id,
                    Mission.tenant_id == tenant_id,
                )
                .first()
            )

            if not mission:
                self.logger.warning(
                    f"Access denied: Validation {validation_id} belongs to different tenant"
                )
                return None

            return validation
        except Exception as e:
            self.logger.error(f"Error fetching validation {validation_id}: {e}")
            return None

    def list_validations(
        self,
        tenant_id: str,
        page: int = 1,
        per_page: int = 20,
        mission_id: Optional[str] = None,
        validator: Optional[str] = None,
        verdict: Optional[str] = None,
    ) -> tuple[List[Validation], int]:
        """
        List validations for tenant with optional filters.

        Args:
            tenant_id: Tenant ID from JWT
            page: Page number
            per_page: Items per page
            mission_id: Filter by mission (optional)
            validator: Filter by validator type (qa, security, release, openai)
            verdict: Filter by verdict (APPROVED, CONDITIONAL, BLOCKED, PENDING)

        Returns:
            (validations, total_count) tuple
        """
        try:
            # Join with Mission to validate tenant
            query = (
                self.db.query(Validation)
                .join(Mission, Validation.mission_id == Mission.mission_id)
                .filter(Mission.tenant_id == tenant_id)
            )

            if mission_id:
                query = query.filter(Validation.mission_id == mission_id)

            if validator:
                query = query.filter(Validation.validator == validator)

            if verdict:
                query = query.filter(Validation.verdict == verdict)

            total = query.count()

            validations = (
                query.order_by(Validation.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return validations, total
        except Exception as e:
            self.logger.error(f"Error listing validations: {e}")
            return [], 0

    def get_blocked_validations(
        self,
        tenant_id: str,
        limit: int = 20,
    ) -> List[Validation]:
        """
        Get recent BLOCKED validations for tenant.

        Args:
            tenant_id: Tenant ID from JWT
            limit: Max results

        Returns:
            List of blocked validations
        """
        try:
            return (
                self.db.query(Validation)
                .join(Mission, Validation.mission_id == Mission.mission_id)
                .filter(
                    Mission.tenant_id == tenant_id,
                    Validation.verdict == "BLOCKED",
                )
                .order_by(Validation.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error fetching blocked validations: {e}")
            return []
