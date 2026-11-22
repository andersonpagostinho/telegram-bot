"""Validation schemas for API responses."""

from datetime import datetime
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field


class ValidationBase(BaseModel):
    """Base validation schema."""
    validation_id: str = Field(..., description="Unique validation identifier")
    mission_id: str = Field(..., description="Mission ID")
    task_id: Optional[str] = Field(None, description="Task ID (if applicable)")
    execution_id: Optional[str] = Field(None, description="Execution ID (if applicable)")


class ValidationVerdict(BaseModel):
    """Validation verdict and confidence."""
    validator: str = Field(..., description="Validator: qa, security, release, openai")
    verdict: str = Field(..., description="Verdict: APPROVED, CONDITIONAL, BLOCKED, PENDING")
    confidence: Optional[int] = Field(None, ge=0, le=100, description="Confidence level (0-100)")


class ValidationFindings(BaseModel):
    """Validation findings and details."""
    findings_summary: Optional[dict] = Field(None, description="Findings summary")
    cost: Optional[Decimal] = Field(None, description="Cost for validation (OpenAI)")
    tokens_used: Optional[int] = Field(None, description="Tokens used")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")


class ValidationResponse(ValidationBase, ValidationVerdict, ValidationFindings):
    """Full validation response."""
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class ValidationListResponse(BaseModel):
    """List of validations with pagination."""
    total: int = Field(..., description="Total validations matching filter")
    validations: list[ValidationResponse] = Field(..., description="Validations in response")
