"""
ARCHITECT ↔ OpenAI Validator Integration Adapter

This module bridges the ARCHITECT's task orchestration with the OpenAI Validator
independent review service. It transforms task deliveries into validation inputs,
submits them to the validator, and processes structured responses.

Purpose:
  - Collect evidence from task deliveries (Git commits, test reports, audit docs)
  - Build ValidationInput from ARCHITECT task context
  - Call OpenAI Validator with structured data
  - Process ValidationResult and update task status
  - Preserve audit trail (original evidence + validator verdict)

Architecture:
  ARCHITECT produces task delivery
    ↓
  ArchitectValidatorAdapter.validate_delivery()
    ├─ Collect evidence from markdown files & git
    ├─ Build ValidationInput
    ├─ Call OpenAIValidator.validate()
    ├─ Process ValidationResult
    └─ Store validation record
    ↓
  ARCHITECT receives validator verdict + confidence
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from openai_validator.validator import OpenAIValidator
    from openai_validator.schema import ValidationInput, ValidationResult
except ImportError:
    # Fallback if validator not installed yet
    OpenAIValidator = None
    ValidationInput = None
    ValidationResult = None


class ArchitectValidatorAdapter:
    """Bridge between ARCHITECT task orchestration and OpenAI Validator"""

    def __init__(self, validator_enabled: bool = True):
        """
        Initialize adapter.

        Args:
            validator_enabled: If False, validator will return NEEDS_HUMAN_REVIEW
        """
        self.validator = OpenAIValidator() if OpenAIValidator else None
        self.validator_enabled = validator_enabled and self.validator is not None
        self.validation_records: Dict[str, ValidationResult] = {}

    def validate_delivery(
        self,
        task_id: str,
        mission_id: str,
        agent_reporting: str,
        task_definition: Dict,
        evidence_files: List[str],
        acceptance_criteria: List[str],
        architecture_constraints: List[str],
        tenant_id: Optional[str] = None,
        docs_base_path: str = "C:/dev/neoeve/docs/agent-team"
    ) -> Tuple[str, float, str]:
        """
        Validate a task delivery by collecting evidence and submitting to Validator.

        Args:
            task_id: Task identifier (e.g., "task-002-d2-001")
            mission_id: Mission identifier (e.g., "mission-002-d2")
            agent_reporting: Which agent completed the work
            task_definition: Original task definition (dict)
            evidence_files: List of markdown files with evidence
            acceptance_criteria: Criteria that must be met
            architecture_constraints: Architecture rules to validate
            tenant_id: Optional tenant isolation scope
            docs_base_path: Base path for evidence files

        Returns:
            (verdict, confidence, executive_summary)
            verdict: "APPROVED" | "APPROVED_WITH_CONDITIONS" | "REJECTED" | ...
            confidence: Float 0-100 indicating confidence level
            executive_summary: Text summary of validation result
        """

        # Step 1: Collect evidence from markdown files
        evidence_summary = self._collect_evidence(evidence_files, docs_base_path)

        # Step 2: Build validation input
        validation_input = self._build_validation_input(
            task_id=task_id,
            mission_id=mission_id,
            agent_reporting=agent_reporting,
            task_definition=task_definition,
            evidence_summary=evidence_summary,
            acceptance_criteria=acceptance_criteria,
            architecture_constraints=architecture_constraints,
            tenant_id=tenant_id
        )

        # Step 3: Submit to Validator
        validation_result = self._submit_to_validator(validation_input)

        # Step 4: Store validation record for audit trail
        self._store_validation_record(task_id, validation_result)

        # Step 5: Return structured result to ARCHITECT
        # Handle both dict and dataclass results
        if isinstance(validation_result, dict):
            verdict = validation_result.get("verdict", "NEEDS_HUMAN_REVIEW")
            confidence = validation_result.get("confidence", 0)
            summary = validation_result.get("executive_summary", "")
        else:
            verdict = getattr(validation_result, "verdict", "NEEDS_HUMAN_REVIEW")
            confidence = getattr(validation_result, "confidence", 0)
            summary = getattr(validation_result, "executive_summary", "")

        return (verdict, confidence, summary)

    def _collect_evidence(
        self,
        evidence_files: List[str],
        docs_base_path: str
    ) -> Dict:
        """
        Collect and summarize evidence from markdown files.

        Returns:
            {
                "files_found": int,
                "files_readable": int,
                "tests_found": int,
                "tests_passed": int,
                "tests_failed": int,
                "git_commits": list,
                "critical_issues": list,
                "architecture_violations": list,
                "summary": str
            }
        """
        evidence = {
            "files_found": 0,
            "files_readable": 0,
            "content_snippets": [],
            "tests_found": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "git_commits": [],
            "critical_issues": [],
            "architecture_violations": [],
            "implementation_report": "",
            "qa_validation": "",
            "security_audit": ""
        }

        for file_name in evidence_files:
            # Construct full path
            file_path = os.path.join(docs_base_path, file_name)

            if os.path.exists(file_path):
                try:
                    evidence["files_found"] += 1
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        evidence["files_readable"] += 1

                        # Categorize content by filename
                        if "IMPLEMENTATION" in file_name or "BACKEND" in file_name:
                            evidence["implementation_report"] = content[:2000]  # First 2000 chars
                        elif "QA" in file_name or "TEST" in file_name:
                            evidence["qa_validation"] = content[:2000]
                        elif "SECURITY" in file_name or "AUDIT" in file_name:
                            evidence["security_audit"] = content[:2000]

                        # Extract counts
                        import re
                        tests_pass = len(re.findall(r'PASS|✅', content))
                        tests_fail = len(re.findall(r'FAIL|❌', content))
                        evidence["tests_passed"] += tests_pass
                        evidence["tests_failed"] += tests_fail

                        # Extract git commit info
                        commits = re.findall(r'\b[a-f0-9]{6,}\b', content)
                        evidence["git_commits"].extend(commits)

                        # Check for issues
                        if "CRITICAL" in content:
                            evidence["critical_issues"].append(f"Found in {file_name}")
                        if "violat" in content.lower():
                            evidence["architecture_violations"].append(f"Found in {file_name}")

                except Exception as e:
                    evidence["architecture_violations"].append(f"Error reading {file_path}: {str(e)}")

        return evidence

    def _build_validation_input(
        self,
        task_id: str,
        mission_id: str,
        agent_reporting: str,
        task_definition: Dict,
        evidence_summary: Dict,
        acceptance_criteria: List[str],
        architecture_constraints: List[str],
        tenant_id: Optional[str] = None
    ) -> ValidationInput:
        """Build structured ValidationInput from task context"""

        # Fallback to dict-based input if ValidationInput not available
        if ValidationInput is None:
            return {
                "task_id": task_id,
                "mission_id": mission_id,
                "agent_reporting": agent_reporting,
                "task_definition": task_definition,
                "implementation_report": evidence_summary.get("implementation_report", ""),
                "qa_validation": evidence_summary.get("qa_validation", ""),
                "security_audit": evidence_summary.get("security_audit", ""),
                "acceptance_criteria": acceptance_criteria,
                "architecture_constraints": architecture_constraints,
                "tenant_id": tenant_id,
                "evidence_files": list(evidence_summary.get("content_snippets", []))
            }

        return ValidationInput(
            task_id=task_id,
            mission_id=mission_id,
            agent_reporting=agent_reporting,
            task_definition=task_definition,
            implementation_report=evidence_summary.get("implementation_report", ""),
            qa_validation=evidence_summary.get("qa_validation", ""),
            security_audit=evidence_summary.get("security_audit", ""),
            acceptance_criteria=acceptance_criteria,
            architecture_constraints=architecture_constraints,
            tenant_id=tenant_id,
            evidence_files=list(evidence_summary.get("content_snippets", []))
        )

    def _submit_to_validator(self, validation_input) -> Dict:
        """
        Submit validation input to OpenAI Validator.

        Returns ValidationResult-like dict with:
            verdict, confidence, findings, etc.
        """

        if not self.validator_enabled or not self.validator:
            # Return mock result for testing without API key
            return self._create_mock_result(validation_input)

        try:
            # Call real validator
            result = self.validator.validate(validation_input)
            return result
        except Exception as e:
            # Fallback: create error result
            return self._create_error_result(validation_input, str(e))

    def _get_input_value(self, obj, key, default=""):
        """Extract value from dict or dataclass object"""
        if isinstance(obj, dict):
            return obj.get(key, default)
        else:
            # Assume dataclass
            return getattr(obj, key, default)

    def _create_mock_result(self, validation_input) -> Dict:
        """
        Create a mock validation result for testing without OpenAI API.

        This is used when OPENAI_API_KEY is not set or validator is disabled.
        Returns a structured dict that behaves like ValidationResult.
        """
        task_id = self._get_input_value(validation_input, "task_id", "unknown")
        mission_id = self._get_input_value(validation_input, "mission_id", "")

        return {
            "validation_id": f"val-mock-{task_id}-{datetime.now().isoformat()}",
            "mission_id": mission_id,
            "task_id": task_id,
            "verdict": "NEEDS_HUMAN_REVIEW",  # Safe default
            "confidence": 0,
            "executive_summary": "MOCK VALIDATION: OpenAI API key not configured. Human review required.",
            "findings": [{
                "severity": "INFO",
                "category": "validator_unavailable",
                "description": "Real OpenAI validation not performed. Using mock mode.",
                "evidence_reference": "OPENAI_API_KEY environment variable",
                "recommended_action": "Set OPENAI_API_KEY environment variable for real validation"
            }],
            "critical_issues": ["Validator not available in mock mode"],
            "missing_evidence": [],
            "contradictions": [],
            "architecture_compliance": False,
            "security_assessment": "NOT_VALIDATED",
            "test_assessment": "NOT_VALIDATED",
            "required_actions": ["Set OPENAI_API_KEY", "Re-submit for validation"],
            "recommended_owner": "SECURITY_AUDITOR",
            "human_review_required": True,
            "model_id": "mock",
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "created_at": datetime.now().isoformat()
        }

    def _create_error_result(self, validation_input, error_msg: str) -> Dict:
        """Create error result when validation fails"""
        task_id = self._get_input_value(validation_input, "task_id", "unknown")
        mission_id = self._get_input_value(validation_input, "mission_id", "")

        return {
            "validation_id": f"val-error-{task_id}",
            "mission_id": mission_id,
            "task_id": task_id,
            "verdict": "NEEDS_HUMAN_REVIEW",
            "confidence": 0,
            "executive_summary": f"Validation error: {error_msg}",
            "findings": [{
                "severity": "CRITICAL",
                "category": "validation_error",
                "description": f"Validator raised exception: {error_msg}",
                "evidence_reference": "OpenAI Validator",
                "recommended_action": "Investigate error and re-submit"
            }],
            "critical_issues": [f"Validation failed: {error_msg}"],
            "missing_evidence": [],
            "contradictions": [],
            "architecture_compliance": False,
            "security_assessment": "NOT_VALIDATED",
            "test_assessment": "NOT_VALIDATED",
            "required_actions": ["Fix validation error", "Re-submit for validation"],
            "recommended_owner": "ARCHITECT",
            "human_review_required": True,
            "model_id": "error",
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "created_at": datetime.now().isoformat()
        }

    def _store_validation_record(self, task_id: str, result: Dict):
        """Store validation record for audit trail"""
        self.validation_records[task_id] = result

        # Optionally persist to file
        records_path = "C:/dev/neoeve/docs/agent-team/validation-records"
        os.makedirs(records_path, exist_ok=True)

        record_file = os.path.join(records_path, f"{task_id}-validation.json")
        try:
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not persist validation record: {e}")

    def get_validation_record(self, task_id: str) -> Optional[Dict]:
        """Retrieve validation record from memory"""
        return self.validation_records.get(task_id)

    def list_validation_records(self) -> List[Tuple[str, str, float]]:
        """List all validation records with verdict and confidence"""
        return [
            (task_id, result.get("verdict", "UNKNOWN"), result.get("confidence", 0))
            for task_id, result in self.validation_records.items()
        ]
