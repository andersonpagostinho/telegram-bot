"""Event response schemas."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class EventResponse(BaseModel):
    """Single event response."""
    event_id: str
    event_type: str
    sequence: int
    tenant_id: str
    project_id: str
    payload: Any  # Full payload
    created_at: datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """List of events with pagination."""
    events: List[EventResponse]
    total: int
    cursor: Optional[int] = None  # Next page cursor
    has_more: bool = False
