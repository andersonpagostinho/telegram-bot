"""
Validation Handler — Orchestrates ARCHITECT → Validator workflow

This handler:
1. Receives ARCHITECT task delivery requests
2. Collects evidence from task completion artifacts
3. Submits to OpenAI Validator via adapter
4. Processes validator verdict
5. Updates ARCHITECT with validation result
6. Produces validation event for event stream

Usage:
    handler = ValidationHandler()
    verdict, confidence, summary = handler.validate_task_delivery(
        task_id="task-002-d2-001",
        mission_id="mission-002-d2",
        evidence_files=["BACKEND_DEVELOPER_SECURITY_FIX_REPORT.md"],
        acceptance_criteria=["✓ Fix applied", "✓ Tests pass"],
        architecture_constraints=["MULTI_TENANT_ISOLATION"]
    )
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class ValidationHandler:
    """
    Orchestrates validation requests from ARCHITECT.

    Bridges task completion with independent validation.
    Maintains audit trail of all validation requests and responses.
    """

    def __init__(self, adapter=None):
        """
        Initialize handler with optional pre-configured adapter.

        Args:
            adapter: ArchitectValidatorAdapter instance (or None to create default)
        """
        self.adapter = adapter
        self.validation_history = []

    def validate_task_delivery(
        self,
        task_id: str,
        mission_id: str,
        agent_reporting: str = "backend-developer",
        task_definition: Optional[Dict] = None,
        evidence_files: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        architecture_constraints: Optional[List[str]] = None,
        tenant_id: Optional[str] = None
    ) -> Tuple[str, float, str]:
        """
        Validate a completed task delivery.

        Args:
            task_id: Task identifier
            mission_id: Parent mission
            agent_reporting: Which agent completed work
            task_definition: Original task spec
            evidence_files: List of markdown files with evidence
            acceptance_criteria: Criteria that must be met
            architecture_constraints: Architecture rules to validate
            tenant_id: Optional tenant scope

        Returns:
            (verdict: str, confidence: float, summary: str)

        Verdicts:
            - "APPROVED": Ready for deployment
            - "APPROVED_WITH_CONDITIONS": OK with caveats
            - "REJECTED": Do not deploy
            - "INSUFFICIENT_EVIDENCE": Need more proof
            - "NEEDS_HUMAN_REVIEW": Ambiguous case
        """

        # Lazy load adapter if not provided
        if self.adapter is None:
            from services.architect_validator_integration import ArchitectValidatorAdapter
            self.adapter = ArchitectValidatorAdapter()

        # Defaults
        if evidence_files is None:
            evidence_files = []
        if acceptance_criteria is None:
            acceptance_criteria = []
        if architecture_constraints is None:
            architecture_constraints = []
        if task_definition is None:
            task_definition = {}

        # Submit for validation
        verdict, confidence, summary = self.adapter.validate_delivery(
            task_id=task_id,
            mission_id=mission_id,
            agent_reporting=agent_reporting,
            task_definition=task_definition,
            evidence_files=evidence_files,
            acceptance_criteria=acceptance_criteria,
            architecture_constraints=architecture_constraints,
            tenant_id=tenant_id
        )

        # Record in history
        self.validation_history.append({
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "mission_id": mission_id,
            "verdict": verdict,
            "confidence": confidence,
            "summary": summary
        })

        return verdict, confidence, summary

    def get_validation_summary(self) -> Dict:
        """
        Get summary statistics of all validations performed.

        Returns:
            {
                "total_validations": int,
                "verdicts": {"APPROVED": int, ...},
                "avg_confidence": float,
                "history": [...]
            }
        """
        from collections import Counter

        verdicts = Counter(v.get("verdict") for v in self.validation_history)

        avg_confidence = 0
        if self.validation_history:
            avg_confidence = sum(
                v.get("confidence", 0) for v in self.validation_history
            ) / len(self.validation_history)

        return {
            "total_validations": len(self.validation_history),
            "verdicts": dict(verdicts),
            "avg_confidence": round(avg_confidence, 2),
            "history": self.validation_history
        }

    def export_validation_log(self, output_path: str = "validation-log.jsonl"):
        """
        Export validation history as JSONL for analysis.

        Each line is a JSON object representing one validation.
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for record in self.validation_history:
                f.write(json.dumps(record) + '\n')

        return output_path


# Singleton instance for use across modules
_handler = None

def get_validation_handler(adapter=None) -> ValidationHandler:
    """Get or create global validation handler instance"""
    global _handler
    if _handler is None:
        _handler = ValidationHandler(adapter=adapter)
    return _handler


def reset_handler():
    """Reset handler (for testing)"""
    global _handler
    _handler = None
