"""Agent schemas for API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    """Base agent schema."""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_role: str = Field(..., description="Agent role (architect, backend, qa, security, etc.)")
    runtime: str = Field(..., description="Runtime environment (Claude Code CLI, OpenAI API, etc.)")


class AgentStatus(BaseModel):
    """Agent status information."""
    status: str = Field(..., description="Current status (IDLE, WORKING, ANALYZING, TESTING, REVIEWING, BLOCKED, COMPLETED, ERROR)")
    connectivity_status: str = Field(..., description="Connectivity status (ONLINE, OFFLINE, STALE, UNKNOWN)")
    last_event_at: Optional[datetime] = Field(None, description="Last event timestamp")
    last_execution_at: Optional[datetime] = Field(None, description="Last execution timestamp")
    last_error: Optional[str] = Field(None, description="Last error message")


class AgentMetrics(BaseModel):
    """Agent performance metrics."""
    metrics_summary: Optional[dict] = Field(None, description="Summary metrics")
    current_mission_id: Optional[str] = Field(None, description="Currently working mission")
    current_task_id: Optional[str] = Field(None, description="Currently working task")


class AgentResponse(AgentBase, AgentStatus, AgentMetrics):
    """Full agent response."""
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """List of agents."""
    total: int = Field(..., description="Total number of agents")
    agents: list[AgentResponse] = Field(..., description="Agents in response")


class AgentEventResponse(BaseModel):
    """Recent event for an agent."""
    event_id: str = Field(..., description="Event ID")
    event_type: str = Field(..., description="Type of event")
    created_at: datetime = Field(..., description="Creation timestamp")
    summary: Optional[str] = Field(None, description="Event summary")
