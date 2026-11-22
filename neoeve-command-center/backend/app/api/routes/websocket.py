"""
WebSocket endpoint for real-time event updates.
Handles multi-tenant subscriptions with ticket-based authentication.
"""

import logging
from fastapi import APIRouter, WebSocket, Query, Depends
from sqlalchemy.orm import Session

from ...core.security import get_current_user, get_admin_user, Identity
from ...core.dependencies import get_db
from ...services.websocket_manager import connection_manager
from ...services.websocket_ticket_service import ticket_service
from ...services.websocket_event_log_service import get_event_log_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.post("/ticket")
async def issue_websocket_ticket(
    current_user: Identity = Depends(get_current_user),
):
    """
    Issue a short-lived WebSocket ticket.

    Security:
    - JWT auth required
    - Ticket is single-use and expires in 5 minutes
    - Rate limited: max 10 tickets per user per minute
    - Returns 429 Too Many Requests if rate limit exceeded

    Returns: {"ticket": "..."} or 429 if rate limited
    """
    from fastapi import HTTPException, status

    ticket = ticket_service.issue_ticket(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        actor_id=current_user.actor_id,
        actor_role=current_user.actor_role,
    )

    if ticket is None:
        # Rate limit exceeded - notify client
        logger.warning(
            f"WebSocket ticket rate limit exceeded: "
            f"user={current_user.user_id} tenant={current_user.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many ticket requests. Please wait before requesting again.",
        )

    logger.info(
        f"WebSocket ticket issued for tenant={current_user.tenant_id} "
        f"user={current_user.user_id}"
    )

    return {"ticket": ticket}


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: str = Query(..., description="WebSocket ticket from /ticket endpoint"),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time Command Center updates.

    Features:
    - Ticket-based authentication (single-use, 5 minute expiry)
    - Multi-tenant isolation (events scoped to tenant)
    - Event subscription management
    - Automatic heartbeat and reconnection

    Protocol:
    - Client sends: {"action": "subscribe", "event_types": [...]}
    - Client sends: {"action": "heartbeat"}
    - Client sends: {"action": "reconnect", "cursor": N}
    - Server sends: {"type": "event", "event_type": "...", "data": {...}}
    - Server sends: {"type": "heartbeat", "cursor": N}
    """

    # Validate and consume ticket (atomic operation)
    ws_ticket = ticket_service.validate_and_consume_ticket(ticket)

    if not ws_ticket:
        logger.warning(f"WebSocket ticket validation failed: {ticket[:8]}...")
        await websocket.close(code=1008, reason="Invalid or expired ticket")
        return

    # Build identity from ticket claims
    identity = Identity(
        user_id=ws_ticket.user_id,
        tenant_id=ws_ticket.tenant_id,
        actor_id=ws_ticket.actor_id,
        actor_role=ws_ticket.actor_role,
    )

    # Accept connection
    connection_id = await connection_manager.connect(
        websocket=websocket,
        identity=identity,
        db=db,
    )

    if not connection_id:
        await websocket.close(code=1011, reason="Connection rejected")
        return

    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "connection_id": connection_id,
        "tenant_id": identity.tenant_id,
        "user_id": identity.user_id,
    })

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            action = data.get("action")

            if action == "subscribe":
                # Subscribe to events
                event_types = data.get("event_types", [])
                if await connection_manager.subscribe(connection_id, event_types):
                    await websocket.send_json({
                        "type": "subscribed",
                        "event_types": event_types,
                        "status": "ok",
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "code": "SUBSCRIPTION_FAILED",
                        "message": "Failed to subscribe",
                    })

            elif action == "unsubscribe":
                # Unsubscribe from events
                event_types = data.get("event_types", [])
                await connection_manager.unsubscribe(connection_id, event_types)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "event_types": event_types,
                })

            elif action == "heartbeat":
                # Client heartbeat - respond with server heartbeat
                await connection_manager.handle_heartbeat(connection_id)
                client = connection_manager.active_connections.get(connection_id)
                if client:
                    await client.send_heartbeat()

            elif action == "reconnect":
                # Client reconnecting - send missed events (ETAPA 5: Event Recovery)
                cursor = data.get("cursor")  # Last sequence number seen by client
                event_types = data.get("event_types", [])

                await connection_manager.subscribe(connection_id, event_types)

                # Query websocket_event_log for missed events
                try:
                    event_log_service = get_event_log_service()
                    missed_events = event_log_service.get_missed_events(
                        db=db,
                        tenant_id=identity.tenant_id,
                        cursor=cursor,
                        limit=100,  # Max 100 events to avoid flooding
                    )

                    # Filter by event types if specified
                    if event_types:
                        missed_events = [
                            e for e in missed_events
                            if e.event_type in event_types
                        ]

                    # Get latest cursor
                    latest_cursor = None
                    if missed_events:
                        latest_cursor = missed_events[-1].sequence
                        logger.info(
                            f"Sending {len(missed_events)} missed events to reconnecting client: "
                            f"connection_id={connection_id} cursor={cursor}→{latest_cursor}"
                        )

                    # Send reconnection acknowledgment with missed events
                    await websocket.send_json({
                        "type": "reconnected",
                        "cursor": latest_cursor,
                        "missed_events": [
                            {
                                "sequence": e.sequence,
                                "event_id": e.event_id,
                                "event_type": e.event_type,
                                "payload": e.payload,
                                "created_at": e.created_at.isoformat(),
                            }
                            for e in missed_events
                        ],
                        "count": len(missed_events),
                    })
                except Exception as e:
                    logger.error(f"Error retrieving missed events: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "code": "RECOVERY_FAILED",
                        "message": "Failed to retrieve missed events",
                    })

            else:
                logger.warning(f"Unknown action: {action}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        # Cleanup on disconnect
        await connection_manager.disconnect(connection_id)


@router.get("/ws/connections")
async def get_connections_count(
    current_user: Identity = Depends(get_admin_user)
):
    """
    Get active WebSocket connections count (admin only).

    Security:
    - Requires JWT authentication
    - Requires actor_role="admin"
    - Returns 403 Forbidden if not admin

    Returns:
    - total: Total active connections
    - by_tenant: Breakdown by tenant
    """
    logger.info(f"Admin querying connections: user={current_user.user_id} tenant={current_user.tenant_id}")

    total = connection_manager.get_active_connections_count()

    return {
        "total": total,
        "by_tenant": {
            tenant_id: connection_manager.get_tenant_connections_count(tenant_id)
            for tenant_id in list(connection_manager.tenant_connections.keys())
        },
    }
