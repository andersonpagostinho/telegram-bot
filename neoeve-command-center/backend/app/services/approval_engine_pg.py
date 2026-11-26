"""Approval Engine: independent validation layer with PostgreSQL persistence."""

import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional, List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import text

from database.models import Mission, Validation
from app.services.agent_registry import AgentRegistry, AgentRole
from app.services.event_bus import publish_event

logger = logging.getLogger(__name__)


class ApprovalEnginePG:
    """PostgreSQL-backed approval and validation layer."""

    def __init__(self, db: Session):
        """Initialize engine with database session."""
        self.db = db
        logger.info("Approval Engine (PostgreSQL) initialized")

    def request_approval(
        self,
        mission_id: str,
        task_id: Optional[str],
        tenant_id: str,
        project_id: str,
        requested_by: str,
        actor_id: str,
    ) -> Optional[str]:
        """Request approval for mission or task."""
        mission = self.db.query(Mission).filter(
            Mission.mission_id == mission_id,
            Mission.tenant_id == tenant_id,
            Mission.project_id == project_id,
        ).first()

        if not mission:
            logger.warning(f"Mission not found: {mission_id}")
            return None

        approval_id = str(uuid4())

        # Create Validation record in PostgreSQL
        try:
            validation = Validation(
                validation_id=approval_id,
                mission_id=mission_id,
                task_id=task_id,
                validator="qa_engineer",  # Default validator role
                verdict="PENDING",
                findings_summary={"requested_by": requested_by},
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(validation)
            self.db.commit()

            # Publish event AFTER persistence
            publish_event(
                event_type="approval.requested",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=mission_id,
                task_id=task_id,
                payload={
                    "approval_id": approval_id,
                    "requested_by": requested_by,
                },
                idempotency_key=f"approval.requested.{approval_id}",
            )

            logger.info(f"Approval requested: {approval_id} for mission {mission_id}")
            return approval_id

        except Exception as e:
            logger.error(f"Error requesting approval: {e}")
            self.db.rollback()
            return None

    def approve(
        self,
        approval_id: str,
        validator_agent_id: str,
        justification: str,
        tenant_id: str,
        project_id: str,
        actor_id: str,
    ) -> bool:
        """
        Approve mission/task with concurrency safety.
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        try:
            # Use row-level lock to ensure atomicity
            validation = self.db.query(Validation).filter(
                Validation.validation_id == approval_id
            ).with_for_update().first()

            if not validation:
                logger.warning(f"Validation not found: {approval_id}")
                return False

            # Check if already decided
            if validation.verdict != "PENDING":
                logger.warning(f"Validation already decided: {approval_id}")
                return False

            # Persist decision to PostgreSQL
            validation.verdict = "APPROVED"
            validation.confidence = 100
            validation.findings_summary = {"justification": justification}
            self.db.commit()

            # Publish event AFTER persistence
            publish_event(
                event_type="approval.approved",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=validation.mission_id,
                task_id=validation.task_id,
                payload={
                    "approval_id": approval_id,
                    "validator": validator_agent_id,
                },
                idempotency_key=f"approval.approved.{approval_id}",
            )

            logger.info(f"Approval granted: {approval_id}")
            return True

        except Exception as e:
            logger.error(f"Error approving: {e}")
            self.db.rollback()
            return False

    def reject(
        self,
        approval_id: str,
        validator_agent_id: str,
        justification: str,
        tenant_id: str,
        project_id: str,
        actor_id: str,
    ) -> bool:
        """Reject mission/task with concurrency safety."""
        try:
            # Row-level lock
            validation = self.db.query(Validation).filter(
                Validation.validation_id == approval_id
            ).with_for_update().first()

            if not validation:
                return False

            if validation.verdict != "PENDING":
                return False

            validation.verdict = "BLOCKED"  # BLOCKED = Rejected
            validation.findings_summary = {"justification": justification}
            self.db.commit()

            publish_event(
                event_type="approval.rejected",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=validation.mission_id,
                task_id=validation.task_id,
                payload={
                    "approval_id": approval_id,
                    "validator": validator_agent_id,
                },
                idempotency_key=f"approval.rejected.{approval_id}",
            )

            logger.info(f"Approval rejected: {approval_id}")
            return True

        except Exception as e:
            logger.error(f"Error rejecting: {e}")
            self.db.rollback()
            return False

    def get_approval_status(self, approval_id: str) -> Optional[Dict]:
        """Get current approval status."""
        validation = self.db.query(Validation).filter(
            Validation.validation_id == approval_id
        ).first()

        if not validation:
            return None

        return {
            "approval_id": approval_id,
            "mission_id": validation.mission_id,
            "verdict": validation.verdict,
            "confidence": validation.confidence,
            "created_at": validation.created_at.isoformat() if validation.created_at else None,
        }

    def get_approval_history(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
    ) -> List[Dict]:
        """Get approval history for mission."""
        validations = self.db.query(Validation).filter(
            Validation.mission_id == mission_id,
        ).all()

        return [
            {
                "approval_id": v.validation_id,
                "mission_id": v.mission_id,
                "verdict": v.verdict,
                "confidence": v.confidence,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in validations
        ]
