"""
Validation schema contracts (Pydantic models for structured output)
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class VerdictEnum(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    REJECTED = "REJECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"

class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

@dataclass
class ValidationFinding:
    severity: str
    category: str
    description: str
    evidence_reference: str
    recommended_action: str

@dataclass
class ValidationResult:
    validation_id: str
    mission_id: str
    task_id: str
    verdict: str  # VerdictEnum value
    confidence: float  # 0-100
    executive_summary: str
    findings: List[ValidationFinding] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    architecture_compliance: bool = True
    security_assessment: str = "PASS"
    test_assessment: str = "PASS"
    required_actions: List[str] = field(default_factory=list)
    recommended_owner: str = "ARCHITECT"
    human_review_required: bool = False
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    created_at: str = ""

@dataclass
class ValidationInput:
    task_id: str
    mission_id: str
    agent_reporting: str
    task_definition: dict
    implementation_report: str
    qa_validation: str
    security_audit: str
    acceptance_criteria: List[str]
    architecture_constraints: List[str]
    tenant_id: Optional[str] = None
    evidence_files: List[str] = field(default_factory=list)
