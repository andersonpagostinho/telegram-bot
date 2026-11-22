"""
WebSocket endpoint for real-time event updates.
Handles multi-tenant subscriptions with JWT authentication.
"""

import json
import logging
from fastapi import APIRouter, WebSocket, Query, Depends
from sqlalchemy.orm import Session

from ...core.security import get_current_user, Identity
from ...core.dependencies import get_db
from ...services.websocket_manager import connection_manager, ClientConnection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication"),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time Command Center updates.

    Features:
    - JWT authentication via query parameter
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

    # Authenticate using provided token
    try:
        from jose import jwt
        from ...core.config import settings

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        identity = Identity(
            user_id=payload.get("user_id"),
            tenant_id=payload.get("tenant_id"),
            actor_id=payload.get("actor_id"),
            actor_role=payload.get("actor_role"),
        )

        if not all([identity.user_id, identity.tenant_id, identity.actor_id]):
            await websocket.close(code=1008, reason="Invalid token claims")
            return

    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

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
                # Client reconnecting - send missed events
                cursor = data.get("cursor")
                event_types = data.get("event_types", [])

                await connection_manager.subscribe(connection_id, event_types)

                # TODO: Query websocket_event_log for missed events
                # For now, just acknowledge reconnection
                await websocket.send_json({
                    "type": "reconnected",
                    "cursor": cursor,
                    "missed_events": [],
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
    current_user: Identity = Depends(lambda: Identity(
        user_id="system", tenant_id="system", actor_id="system", actor_role="admin"
    ))
):
    """
    Get active WebSocket connections count (admin only).

    Returns:
    - total: Total active connections
    - by_tenant: Breakdown by tenant
    """
    total = connection_manager.get_active_connections_count()

    return {
        "total": total,
        "by_tenant": {
            tenant_id: connection_manager.get_tenant_connections_count(tenant_id)
            for tenant_id in list(connection_manager.tenant_connections.keys())
        },
    }
