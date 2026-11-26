"""Approval Engine: independent validation layer for missions and tasks."""

import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional, List, Dict
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import Mission, Task, Execution
from app.services.agent_registry import AgentRegistry, AgentRole, Permission
from app.services.event_bus import publish_event

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval lifecycle states."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    VETOED = "VETOED"


class ApprovalRecord:
    """In-memory approval record (use database model in production)."""

    def __init__(
        self,
        approval_id: str,
        mission_id: str,
        task_id: Optional[str],
        tenant_id: str,
        project_id: str,
        requested_by: str,
        validator_agent_id: str,
        validator_role: str,
    ):
        self.approval_id = approval_id
        self.mission_id = mission_id
        self.task_id = task_id
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.requested_by = requested_by
        self.validator_agent_id = validator_agent_id
        self.validator_role = validator_role
        self.status = ApprovalStatus.PENDING.value
        self.decision = None
        self.justification = None
        self.evidence = None
        self.created_at = datetime.now(timezone.utc)
        self.decided_at = None


class ApprovalEngine:
    """Independent approval and validation layer."""

    def __init__(self, db: Session):
        """Initialize engine with database session."""
        self.db = db
        self._approvals = {}  # In-memory store for now
        logger.info("Approval Engine initialized")

    def request_approval(
        self,
        mission_id: str,
        task_id: Optional[str],
        tenant_id: str,
        project_id: str,
        requested_by: str,
        actor_id: str,
    ) -> Optional[str]:
        """
        Request approval for mission or task.

        Args:
            mission_id: Mission to validate
            task_id: Optional task (if approving specific task)
            tenant_id: Tenant ID
            project_id: Project ID
            requested_by: Agent/user requesting approval
            actor_id: Audit trail

        Returns:
            Approval ID or None if validation fails
        """
        mission = self.db.query(Mission).filter(
            Mission.mission_id == mission_id,
            Mission.tenant_id == tenant_id,
            Mission.project_id == project_id,
        ).first()

        if not mission:
            logger.warning(f"Mission not found: {mission_id}")
            return None

        approval_id = str(uuid4())

        # Determine which validator roles are needed
        validator_roles = self._determine_required_validators(task_id)

        # Create approval records for each validator
        for validator_role in validator_roles:
            record = ApprovalRecord(
                approval_id=approval_id,
                mission_id=mission_id,
                task_id=task_id,
                tenant_id=tenant_id,
                project_id=project_id,
                requested_by=requested_by,
                validator_agent_id=None,  # Will be assigned by validator
                validator_role=validator_role.value,
            )
            self._approvals[approval_id] = record

        # Publish event
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
                "validators": [r.value for r in validator_roles],
            },
            idempotency_key=f"approval.requested.{approval_id}",
        )

        logger.info(f"Approval requested: {approval_id} for mission {mission_id}")
        return approval_id

    def submit_validation(
        self,
        approval_id: str,
        validator_agent_id: str,
        evidence: Dict,
        tenant_id: str,
        project_id: str,
        actor_id: str,
    ) -> bool:
        """
        Submit validation evidence.

        Args:
            approval_id: Approval record ID
            validator_agent_id: Validating agent
            evidence: Validation results/findings
            tenant_id: Tenant ID
            project_id: Project ID
            actor_id: Audit trail

        Returns:
            True if submitted successfully
        """
        if approval_id not in self._approvals:
            logger.warning(f"Approval not found: {approval_id}")
            return False

        record = self._approvals[approval_id]

        # Validate tenant/project
        if record.tenant_id != tenant_id or record.project_id != project_id:
            logger.warning(f"Approval tenant/project mismatch: {approval_id}")
            return False

        # Validate validator role
        validator_role = AgentRegistry.AGENTS.get(next(
            (k for k, v in AgentRegistry.AGENTS.items() if v["agent_id"] == validator_agent_id),
            None
        ))

        if not validator_role or validator_role["role"].value != record.validator_role:
            logger.warning(f"Validator role mismatch: {validator_agent_id}")
            return False

        try:
            record.status = ApprovalStatus.SUBMITTED.value
            record.validator_agent_id = validator_agent_id
            record.evidence = evidence

            publish_event(
                event_type="approval.submitted",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=record.mission_id,
                task_id=record.task_id,
                payload={
                    "approval_id": approval_id,
                    "validator": validator_agent_id,
                },
                idempotency_key=f"approval.submitted.{approval_id}",
            )

            logger.info(f"Validation submitted: {approval_id} by {validator_agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error submitting validation: {e}")
            return False

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
        Approve mission/task.

        Returns:
            True if approved successfully
        """
        if approval_id not in self._approvals:
            logger.warning(f"Approval not found: {approval_id}")
            return False

        record = self._approvals[approval_id]

        # Validate tenant/project
        if record.tenant_id != tenant_id or record.project_id != project_id:
            return False

        # Idempotency: already decided
        if record.status in [ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value, ApprovalStatus.VETOED.value]:
            return False

        # Prevent self-approval
        if record.requested_by == validator_agent_id:
            logger.warning(f"Self-approval blocked: {approval_id}")
            return False

        # Require evidence
        if not record.evidence:
            logger.warning(f"Approval without evidence: {approval_id}")
            return False

        try:
            record.status = ApprovalStatus.APPROVED.value
            record.decision = "APPROVED"
            record.justification = justification
            record.decided_at = datetime.now(timezone.utc)

            publish_event(
                event_type="approval.approved",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=record.mission_id,
                task_id=record.task_id,
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
        """Reject mission/task with justification."""
        if approval_id not in self._approvals:
            return False

        record = self._approvals[approval_id]

        if record.tenant_id != tenant_id or record.project_id != project_id:
            return False

        # Idempotency: already decided
        if record.status in [ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value, ApprovalStatus.VETOED.value]:
            return False

        try:
            record.status = ApprovalStatus.REJECTED.value
            record.decision = "REJECTED"
            record.justification = justification
            record.decided_at = datetime.now(timezone.utc)

            publish_event(
                event_type="approval.rejected",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=record.mission_id,
                task_id=record.task_id,
                payload={
                    "approval_id": approval_id,
                    "validator": validator_agent_id,
                    "justification": justification,
                },
                idempotency_key=f"approval.rejected.{approval_id}",
            )

            logger.info(f"Approval rejected: {approval_id}")
            return True

        except Exception as e:
            logger.error(f"Error rejecting: {e}")
            return False

    def veto(
        self,
        approval_id: str,
        security_auditor_id: str,
        justification: str,
        tenant_id: str,
        project_id: str,
        actor_id: str,
    ) -> bool:
        """
        Security veto - blocks mission until resolved.

        Only Security Auditor can veto.
        """
        if approval_id not in self._approvals:
            return False

        record = self._approvals[approval_id]

        if record.tenant_id != tenant_id or record.project_id != project_id:
            return False

        # Idempotency: already decided
        if record.status in [ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value, ApprovalStatus.VETOED.value]:
            return False

        # Verify Security Auditor role
        agent_config = next(
            (v for v in AgentRegistry.AGENTS.values() if v["agent_id"] == security_auditor_id),
            None
        )

        if not agent_config or agent_config["role"] != AgentRole.SECURITY_AUDITOR:
            logger.warning(f"Non-Security Auditor veto blocked: {security_auditor_id}")
            return False

        try:
            record.status = ApprovalStatus.VETOED.value
            record.decision = "VETOED"
            record.justification = justification
            record.decided_at = datetime.now(timezone.utc)

            publish_event(
                event_type="approval.vetoed",
                tenant_id=tenant_id,
                project_id=project_id,
                actor_id=actor_id,
                mission_id=record.mission_id,
                task_id=record.task_id,
                payload={
                    "approval_id": approval_id,
                    "auditor": security_auditor_id,
                    "justification": justification,
                },
                idempotency_key=f"approval.vetoed.{approval_id}",
            )

            logger.info(f"Security veto issued: {approval_id}")
            return True

        except Exception as e:
            logger.error(f"Error issuing veto: {e}")
            return False

    def get_approval_status(self, approval_id: str) -> Optional[Dict]:
        """Get current approval status."""
        if approval_id not in self._approvals:
            return None

        record = self._approvals[approval_id]
        return {
            "approval_id": approval_id,
            "mission_id": record.mission_id,
            "status": record.status,
            "decision": record.decision,
            "validator": record.validator_agent_id,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        }

    def get_approval_history(
        self,
        tenant_id: str,
        project_id: str,
        mission_id: str,
    ) -> List[Dict]:
        """Get approval history for mission."""
        history = [
            self.get_approval_status(aid)
            for aid, record in self._approvals.items()
            if record.mission_id == mission_id and
            record.tenant_id == tenant_id and
            record.project_id == project_id
        ]
        return [h for h in history if h]

    def _determine_required_validators(self, task_id: Optional[str]) -> List[AgentRole]:
        """Determine which validators are required."""
        # For now: QA and Security Auditor always required
        # Production would have more complex logic
        return [AgentRole.QA_ENGINEER, AgentRole.SECURITY_AUDITOR]
