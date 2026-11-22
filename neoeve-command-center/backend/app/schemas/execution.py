"""Execution schemas for API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExecutionBase(BaseModel):
    """Base execution schema."""
    execution_id: str = Field(..., description="Unique execution identifier")
    mission_id: str = Field(..., description="Mission ID")
    task_id: Optional[str] = Field(None, description="Task ID (if task-scoped)")
    agent_id: str = Field(..., description="Agent executing")
    runtime: str = Field(..., description="Runtime environment")


class ExecutionTimeline(BaseModel):
    """Execution timeline with timestamps."""
    status: str = Field(..., description="Status: QUEUED, RESERVED, RUNNING, COMPLETED, FAILED")
    queued_at: Optional[datetime] = Field(None, description="Queued timestamp")
    reserved_at: Optional[datetime] = Field(None, description="Reserved timestamp")
    started_at: Optional[datetime] = Field(None, description="Started timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completed timestamp")
    validated_at: Optional[datetime] = Field(None, description="Validation timestamp")
    recorded_at: Optional[datetime] = Field(None, description="Recorded timestamp")


class ExecutionDurations(BaseModel):
    """Execution duration measurements in milliseconds."""
    queue_time_ms: Optional[int] = Field(None, description="Time in queue (ms)")
    init_time_ms: Optional[int] = Field(None, description="Initialization time (ms)")
    execution_time_ms: Optional[int] = Field(None, description="Execution time (ms)")
    validation_time_ms: Optional[int] = Field(None, description="Validation time (ms)")
    total_duration_ms: Optional[int] = Field(None, description="Total duration (ms)")


class ExecutionResults(BaseModel):
    """Execution results and errors."""
    result: Optional[dict] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")


class ExecutionResponse(ExecutionBase, ExecutionTimeline, ExecutionDurations, ExecutionResults):
    """Full execution response."""

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """List of executions with pagination."""
    total: int = Field(..., description="Total executions matching filter")
    executions: list[ExecutionResponse] = Field(..., description="Executions in response")
