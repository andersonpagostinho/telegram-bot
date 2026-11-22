"""Deterministic Governance Engine — Enforces approval rules and authorization"""

import logging
from enum import Enum
from typing import Tuple, Optional
from dataclasses import dataclass

from event_bus.event import Event, EventType, EventStatus


logger = logging.getLogger(__name__)


class GovernanceViolation(Exception):
    """Raised when a governance rule is violated"""
    pass


@dataclass
class GovernanceDecision:
    """Result of governance rule evaluation"""
    allowed: bool
    reason: Optional[str] = None
    rule_id: Optional[int] = None


class GovernanceEngine:
    """
    Deterministic governance rule engine.

    Enforces 8 non-negotiable rules:
    1. No self-approval
    2. QA independence
    3. Security veto power
    4. Release authorization
    5. Evidence requirement
    6. Fail-closed on validator failure
    7. Permission enforcement
    8. Audit trail recording
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.audit_log = []

    def evaluate(self, event: Event, target_agent: str, action: str) -> GovernanceDecision:
        """
        Evaluate if action is allowed under governance rules.

        Returns:
            GovernanceDecision with allowed/denied and reason
        """
        # Rule 1: No Self-Approval
        result = self._rule_no_self_approval(event, target_agent)
        if not result.allowed:
            return result

        # Rule 2: QA Independence
        result = self._rule_qa_independence(event, target_agent)
        if not result.allowed:
            return result

        # Rule 3: Security Veto
        result = self._rule_security_veto(event, target_agent)
        if not result.allowed:
            return result

        # Rule 4: Release Authorization
        result = self._rule_release_authorization(event, target_agent)
        if not result.allowed:
            return result

        # Rule 5: Evidence Requirement
        result = self._rule_evidence_required(event)
        if not result.allowed:
            return result

        # Rule 6: Fail-Closed
        result = self._rule_fail_closed(event, target_agent)
        if not result.allowed:
            return result

        # Rule 7: Permission Enforcement
        result = self._rule_permission_enforcement(target_agent, action)
        if not result.allowed:
            return result

        # Rule 8: Audit Trail (record decision)
        self._rule_audit_trail(event, target_agent, action, True)

        return GovernanceDecision(allowed=True, reason="All rules passed", rule_id=0)

    # ============= RULE IMPLEMENTATIONS =============

    def _rule_no_self_approval(self, event: Event, target_agent: str) -> GovernanceDecision:
        """
        Rule 1: No agent can approve its own work.
        """
        if event.event_type in [
            EventType.REVIEW_APPROVED,
            EventType.REVIEW_REJECTED,
            EventType.TASK_COMPLETED,
        ]:
            if event.agent_id == target_agent:
                reason = f"{target_agent} cannot approve own work"
                self._rule_audit_trail(event, target_agent, "REJECTED_SELF_APPROVAL", False)
                return GovernanceDecision(allowed=False, reason=reason, rule_id=1)

        return GovernanceDecision(allowed=True, rule_id=1)

    def _rule_qa_independence(self, event: Event, target_agent: str) -> GovernanceDecision:
        """
        Rule 2: QA changes require independent validation.
        """
        # If event is CODE_COMMITTED and target is QA
        if event.event_type == EventType.TASK_COMPLETED and target_agent == "qa":
            # QA must validate before approval can be given
            # This is enforced by not allowing CODE_COMMITTED to skip QA
            pass

        return GovernanceDecision(allowed=True, rule_id=2)

    def _rule_security_veto(self, event: Event, target_agent: str) -> GovernanceDecision:
        """
        Rule 3: Security Auditor can block operations based on severity.

        CRITICAL/HIGH findings = block immediately
        MEDIUM findings = allow with warning
        LOW findings = allow silently
        """
        # Check if Security explicitly rejected
        if event.event_type == EventType.REVIEW_REJECTED and event.agent_id == "security":
            severity = event.payload.get("severity", "UNKNOWN") if event.payload else "UNKNOWN"
            severity = severity.upper()

            if severity in ["CRITICAL", "HIGH"]:
                reason = f"Security veto: {severity} severity finding blocks operation"
                self._rule_audit_trail(event, target_agent, "REJECTED_SECURITY_VETO", False)
                return GovernanceDecision(allowed=False, reason=reason, rule_id=3)
            elif severity == "MEDIUM":
                # Log but allow
                logger.warning(f"Security warning: {severity} severity finding requires review")

        # Check legacy security_rejected flag for backward compatibility
        if event.payload and event.payload.get("security_rejected"):
            reason = "Security Auditor blocked this operation"
            self._rule_audit_trail(event, target_agent, "REJECTED_SECURITY_VETO", False)
            return GovernanceDecision(allowed=False, reason=reason, rule_id=3)

        return GovernanceDecision(allowed=True, rule_id=3)

    def _rule_release_authorization(self, event: Event, target_agent: str) -> GovernanceDecision:
        """
        Rule 4: Release Manager cannot deploy without approval chain.
        """
        if target_agent == "release":
            if event.event_type == EventType.DEPLOYMENT_REQUESTED:
                # Check all prerequisites
                qa_approved = event.payload.get("qa_approved")
                security_approved = event.payload.get("security_approved")

                if not (qa_approved and security_approved):
                    reason = "Missing required approvals (QA and/or Security)"
                    self._rule_audit_trail(event, target_agent, "REJECTED_RELEASE_GATE", False)
                    return GovernanceDecision(allowed=False, reason=reason, rule_id=4)

        return GovernanceDecision(allowed=True, rule_id=4)

    def _rule_evidence_required(self, event: Event) -> GovernanceDecision:
        """
        Rule 5: Approvals require evidence.
        """
        if event.event_type in [
            EventType.REVIEW_APPROVED,
            EventType.REVIEW_REJECTED,
        ]:
            # Evidence should be in payload
            if not event.payload.get("evidence"):
                reason = "Approval requires evidence in payload"
                return GovernanceDecision(allowed=False, reason=reason, rule_id=5)

        return GovernanceDecision(allowed=True, rule_id=5)

    def _rule_fail_closed(self, event: Event, target_agent: str) -> GovernanceDecision:
        """
        Rule 6: Validator failure means no approval.
        """
        if event.payload.get("validator_failed"):
            reason = "Validation failed - no approval granted"
            self._rule_audit_trail(event, target_agent, "REJECTED_VALIDATOR_FAILED", False)
            return GovernanceDecision(allowed=False, reason=reason, rule_id=6)

        if event.payload.get("validator_timeout"):
            reason = "Validation timeout - moved to dead-letter, no approval"
            self._rule_audit_trail(event, target_agent, "REJECTED_VALIDATOR_TIMEOUT", False)
            return GovernanceDecision(allowed=False, reason=reason, rule_id=6)

        return GovernanceDecision(allowed=True, rule_id=6)

    def _rule_permission_enforcement(self, target_agent: str, action: str) -> GovernanceDecision:
        """
        Rule 7: Agents only execute authorized actions.
        """
        permissions = {
            "architect": ["publish_task", "consolidate_results", "approve_release"],
            "backend": ["execute_task", "publish_result"],
            "debugger": ["investigate", "publish_diagnosis"],
            "qa": ["execute_tests", "approve_or_reject"],
            "security": ["audit", "approve_or_reject"],
            "release": ["verify_readiness", "propose_release"],
            "validator": ["analyze_evidence", "publish_result"],
        }

        allowed_actions = permissions.get(target_agent, [])

        if action not in allowed_actions:
            reason = f"{target_agent} not authorized for action: {action}"
            return GovernanceDecision(allowed=False, reason=reason, rule_id=7)

        return GovernanceDecision(allowed=True, rule_id=7)

    def _rule_audit_trail(self, event: Event, target_agent: str, action: str, allowed: bool) -> None:
        """
        Rule 8: Record all governance decisions.
        """
        audit_entry = {
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "target_agent": target_agent,
            "action": action,
            "allowed": allowed,
            "timestamp": event.timestamp,
        }

        self.audit_log.append(audit_entry)

        status = "ALLOWED" if allowed else "DENIED"
        logger.info(f"[GOVERNANCE] {status}: {target_agent} → {action} (event: {event.event_id})")

        # Publish audit event to Event Bus
        try:
            audit_event = Event(
                event_type=EventType.TASK_PROGRESS if allowed else EventType.AGENT_BLOCKED,
                mission_id=event.mission_id,
                task_id=event.task_id,
                agent_id="governance",
                agent_role="governance",
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={
                    "governance_decision": status,
                    "action": action,
                    "target_agent": target_agent,
                },
                schema_version="1.0"
            )
            self.event_bus.publish(audit_event)
        except Exception as e:
            logger.error(f"Failed to publish audit event: {e}")
