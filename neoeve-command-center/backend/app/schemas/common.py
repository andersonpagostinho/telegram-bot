"""Common schemas for pagination, error responses, and utilities."""

from typing import Generic, TypeVar, Optional
from datetime import datetime

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("desc", regex="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    total: int = Field(..., description="Total number of records")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    data: list[T] = Field(..., description="Items on this page")


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    error_type: Optional[str] = Field(None, description="Error type")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall status: ok, degraded, or error")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    components: Optional[dict] = Field(None, description="Component status breakdown")
