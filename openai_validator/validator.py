"""
OpenAI Validator — Main Service
"""

import os
import json
from datetime import datetime
from typing import Optional
from .schema import ValidationInput, ValidationResult, VerdictEnum

class OpenAIValidator:
    """
    Independent technical review service using OpenAI API.
    Analyzes task evidence and produces structured validation results.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_VALIDATOR_MODEL", "gpt-4-turbo")
        self.enabled = os.getenv("OPENAI_VALIDATOR_ENABLED", "true").lower() == "true"
        self.max_input_tokens = int(os.getenv("OPENAI_VALIDATOR_MAX_INPUT_TOKENS", "2000"))
        self.max_cost_per_review = float(os.getenv("OPENAI_VALIDATOR_MAX_COST_PER_REVIEW", "0.10"))
        self.timeout = int(os.getenv("OPENAI_VALIDATOR_TIMEOUT", "30"))

    def validate(self, input_data: ValidationInput) -> ValidationResult:
        """
        Validate a task submission using OpenAI API (Structured Outputs).
        """

        if not self.enabled:
            return self._create_bypass_result(input_data, "Validator disabled")

        if not self.api_key:
            return self._create_error_result(input_data, "INSUFFICIENT_EVIDENCE", "API key not configured")

        # Build validation prompt
        prompt = self._build_prompt(input_data)

        try:
            # Call OpenAI API with Structured Outputs
            result = self._call_openai_api(prompt, input_data)
            return result
        except Exception as e:
            return self._create_error_result(input_data, "NEEDS_HUMAN_REVIEW", str(e))

    def _build_prompt(self, input_data: ValidationInput) -> str:
        """Build the validation prompt from input data."""

        prompt = f"""You are an independent technical validator for the NeoEve multi-tenant system.

Review the following task submission:

TASK: {input_data.task_id}
MISSION: {input_data.mission_id}
AGENT REPORTING: {input_data.agent_reporting}

ACCEPTANCE CRITERIA: {', '.join(input_data.acceptance_criteria)}
ARCHITECTURE CONSTRAINTS: {', '.join(input_data.architecture_constraints)}

IMPLEMENTATION REPORT:
{input_data.implementation_report}

QA VALIDATION:
{input_data.qa_validation}

SECURITY AUDIT:
{input_data.security_audit}

Evaluate whether:
1. All acceptance criteria are met with evidence
2. Tests are executed (not just documented)
3. No divergence between QA and Security
4. Multi-tenant isolation preserved
5. Architecture contracts respected
6. Sufficient evidence provided
7. No critical unmitigated risks

Provide your verdict and reasoning."""

        return prompt

    def _call_openai_api(self, prompt: str, input_data: ValidationInput) -> ValidationResult:
        """
        Call OpenAI API with Structured Outputs.
        (Actual implementation requires openai library)
        """

        # This is a placeholder - actual implementation would use:
        # from openai import OpenAI
        # client = OpenAI(api_key=self.api_key)
        # response = client.beta.messages.create(...)

        # For now, return a template result
        return ValidationResult(
            validation_id=f"VAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            mission_id=input_data.mission_id,
            task_id=input_data.task_id,
            verdict="NEEDS_HUMAN_REVIEW",
            confidence=0,
            executive_summary="OpenAI API call not yet implemented - requires openai library",
            critical_issues=["API client not implemented"],
            human_review_required=True,
            model_id=self.model,
            created_at=datetime.now().isoformat()
        )

    def _create_error_result(self, input_data: ValidationInput, verdict: str, reason: str) -> ValidationResult:
        """Create error result when validation cannot proceed."""

        return ValidationResult(
            validation_id=f"VAL-ERROR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            mission_id=input_data.mission_id,
            task_id=input_data.task_id,
            verdict=verdict,
            confidence=0,
            executive_summary=f"Validation failed: {reason}",
            critical_issues=[reason],
            human_review_required=True,
            model_id=self.model,
            created_at=datetime.now().isoformat()
        )

    def _create_bypass_result(self, input_data: ValidationInput, reason: str) -> ValidationResult:
        """Create bypass result when validator is disabled."""

        return ValidationResult(
            validation_id=f"VAL-BYPASS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            mission_id=input_data.mission_id,
            task_id=input_data.task_id,
            verdict="NEEDS_HUMAN_REVIEW",
            confidence=0,
            executive_summary=f"Validator bypassed: {reason}",
            human_review_required=True,
            model_id=self.model,
            created_at=datetime.now().isoformat()
        )

    def produce_report(self, result: ValidationResult) -> str:
        """
        Produce Markdown report from validation result.
        (Compatible with NeoEve documentation format)
        """

        report = f"""# OpenAI Validator Report

**Validation ID**: {result.validation_id}
**Task ID**: {result.task_id}
**Mission ID**: {result.mission_id}
**Verdict**: {result.verdict}
**Confidence**: {result.confidence}%

## Executive Summary

{result.executive_summary}

## Findings

{len(result.findings)} findings identified.

## Critical Issues

{chr(10).join(['- ' + issue for issue in result.critical_issues]) if result.critical_issues else 'None'}

## Verdict

**Status**: {result.verdict}
**Human Review Required**: {result.human_review_required}
**Recommended Owner**: {result.recommended_owner}

**Created**: {result.created_at}
"""

        return report
