"""
Historical events API for Activity Stream.

Provides cursor-based pagination of WebSocket events with multi-tenant isolation.
ETAPA 5: Event Recovery mechanism HTTP interface.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime, timezone

from app.core import get_db, get_current_user, get_current_tenant
from database.models import WebSocketEventLog
from app.schemas.events import EventResponse, EventListResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    cursor: Optional[int] = Query(None, description="Start from sequence number (pagination cursor)"),
    limit: int = Query(50, ge=1, le=500, description="Max events to return"),
    agent_id: Optional[str] = Query(None, description="Filter by agent (source_agent in payload)"),
    mission_id: Optional[str] = Query(None, description="Filter by mission (mission_id in payload)"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g., MISSION_UPDATED)"),
) -> EventListResponse:
    """
    Get historical events with cursor-based pagination.

    Returns:
        EventListResponse with events, cursor for next page, and has_more flag.

    Multi-tenant: Results filtered by authenticated tenant_id.
    """
    try:
        # Start with base query for this tenant
        query = db.query(WebSocketEventLog).filter(
            WebSocketEventLog.tenant_id == tenant_id
        )

        # Filter by cursor (pagination)
        if cursor is not None:
            query = query.filter(WebSocketEventLog.sequence > cursor)

        # Apply optional filters (check payload JSON)
        if event_type:
            query = query.filter(WebSocketEventLog.event_type == event_type)

        # Note: agent_id and mission_id filtering would require payload JSON parsing
        # For now, we return events and let frontend filter
        # TODO: Add database-level filtering if needed

        # Order by sequence, limit
        events = query.order_by(WebSocketEventLog.sequence).limit(limit + 1).all()

        # Check if there's a next page
        has_more = len(events) > limit
        if has_more:
            events = events[:limit]

        # Determine next cursor
        next_cursor = None
        if events:
            next_cursor = events[-1].sequence if has_more else None

        # Convert to response schema
        event_responses = [
            EventResponse(
                event_id=evt.event_id,
                event_type=evt.event_type,
                sequence=evt.sequence,
                tenant_id=evt.tenant_id,
                project_id=evt.project_id,
                payload=evt.payload,
                created_at=evt.created_at,
            )
            for evt in events
        ]

        return EventListResponse(
            events=event_responses,
            total=len(event_responses),
            cursor=next_cursor,
            has_more=has_more,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> EventResponse:
    """
    Get a specific event by ID.

    Multi-tenant: Validates event belongs to authenticated tenant.
    """
    try:
        event = db.query(WebSocketEventLog).filter(
            and_(
                WebSocketEventLog.event_id == event_id,
                WebSocketEventLog.tenant_id == tenant_id,
            )
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return EventResponse(
            event_id=event.event_id,
            event_type=event.event_type,
            sequence=event.sequence,
            tenant_id=event.tenant_id,
            project_id=event.project_id,
            payload=event.payload,
            created_at=event.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve event: {str(e)}")
