"""Task schemas for API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Base task schema."""
    task_id: str = Field(..., description="Unique task identifier")
    mission_id: str = Field(..., description="Parent mission ID")
    assigned_agent: str = Field(..., description="Agent assigned to task")


class TaskStatus(BaseModel):
    """Task status and timeline."""
    status: str = Field(..., description="Status: PENDING, STARTED, COMPLETED, FAILED")
    priority: str = Field(..., description="Priority: LOW, NORMAL, HIGH, CRITICAL")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class TaskResults(BaseModel):
    """Task results and errors."""
    result: Optional[dict] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")


class TaskResponse(TaskBase, TaskStatus, TaskResults):
    """Full task response."""

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """List of tasks with pagination."""
    total: int = Field(..., description="Total tasks matching filter")
    tasks: list[TaskResponse] = Field(..., description="Tasks in response")
