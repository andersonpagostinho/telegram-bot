"""Mission schemas for API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MissionBase(BaseModel):
    """Base mission schema."""
    mission_id: str = Field(..., description="Unique mission identifier")
    name: str = Field(..., description="Mission name/title")
    project_id: str = Field(..., description="Project ID (multi-tenant)")
    tenant_id: str = Field(..., description="Tenant/Organization ID")


class MissionStatus(BaseModel):
    """Mission status and progress."""
    status: str = Field(..., description="Status: PENDING, RUNNING, COMPLETED, FAILED, BLOCKED")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class MissionProgress(BaseModel):
    """Mission progress and results."""
    progress_summary: Optional[dict] = Field(None, description="Progress breakdown")
    result_summary: Optional[dict] = Field(None, description="Result summary")


class MissionResponse(MissionBase, MissionStatus, MissionProgress):
    """Full mission response."""

    class Config:
        from_attributes = True


class MissionListResponse(BaseModel):
    """List of missions with pagination."""
    total: int = Field(..., description="Total missions matching filter")
    missions: list[MissionResponse] = Field(..., description="Missions in response")


class MissionEventResponse(BaseModel):
    """Event in mission event stream."""
    event_id: str = Field(..., description="Event ID")
    event_type: str = Field(..., description="Event type")
    source_agent: str = Field(..., description="Agent that created event")
    created_at: datetime = Field(..., description="Creation timestamp")
    payload_summary: Optional[dict] = Field(None, description="Event payload summary")
