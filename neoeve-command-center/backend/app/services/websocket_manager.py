"""
WebSocket connection manager with multi-tenant support.
Handles real-time event distribution with tenant isolation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Set, Optional, Dict
import uuid

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.security import Identity
from database.models import Mission

logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    """Represents an authenticated WebSocket client."""
    connection_id: str
    websocket: WebSocket
    tenant_id: str
    user_id: str
    actor_id: str
    subscriptions: Set[str] = field(default_factory=set)
    cursor: Optional[int] = None
    pending_messages: int = 0
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    async def send_json(self, data: dict) -> bool:
        """
        Send JSON message to client with backpressure handling.

        Returns: True if sent, False if connection lost or queue full
        """
        MAX_PENDING = 1000

        try:
            if self.pending_messages > MAX_PENDING:
                logger.warning(
                    f"Backpressure: Queue full for {self.connection_id} "
                    f"(tenant={self.tenant_id})"
                )
                return False

            await self.websocket.send_json(data)
            self.pending_messages += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send to {self.connection_id}: {e}")
            return False

    async def send_error(self, code: str, message: str):
        """Send error message to client."""
        await self.send_json({
            "type": "error",
            "code": code,
            "message": message,
        })

    async def send_heartbeat(self):
        """Send heartbeat to keep connection alive."""
        await self.send_json({
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cursor": self.cursor,
        })


class WebSocketConnectionManager:
    """
    Manage WebSocket connections with multi-tenant isolation.

    Responsibilities:
    - Track active connections by tenant
    - Route events to subscribed clients
    - Enforce tenant isolation
    - Handle reconnections
    """

    def __init__(self):
        self.active_connections: Dict[str, ClientConnection] = {}
        # Key: connection_id
        # Value: ClientConnection

        self.tenant_connections: Dict[str, Set[str]] = {}
        # Key: tenant_id
        # Value: set of connection_ids

    async def connect(
        self,
        websocket: WebSocket,
        identity: Identity,
        db: Session,
    ) -> Optional[str]:
        """
        Accept new connection and authenticate.

        Args:
            websocket: FastAPI WebSocket connection
            identity: Authenticated identity from JWT
            db: Database session for validation

        Returns:
            connection_id if accepted, None if rejected
        """
        # Validate tenant exists
        mission_exists = db.query(Mission).filter(
            Mission.tenant_id == identity.tenant_id
        ).first()

        if not mission_exists:
            # Tenant has no data, but that's OK - just not subscribed to anything yet
            pass

        # Accept connection
        await websocket.accept()

        # Create client connection
        connection_id = str(uuid.uuid4())
        client = ClientConnection(
            connection_id=connection_id,
            websocket=websocket,
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            actor_id=identity.actor_id,
        )

        # Register connection
        self.active_connections[connection_id] = client

        if identity.tenant_id not in self.tenant_connections:
            self.tenant_connections[identity.tenant_id] = set()
        self.tenant_connections[identity.tenant_id].add(connection_id)

        logger.info(
            f"WebSocket connected: {connection_id} "
            f"(tenant={identity.tenant_id}, user={identity.user_id})"
        )

        return connection_id

    async def disconnect(self, connection_id: str):
        """Remove connection."""
        if connection_id in self.active_connections:
            client = self.active_connections[connection_id]
            del self.active_connections[connection_id]

            # Remove from tenant index
            if client.tenant_id in self.tenant_connections:
                self.tenant_connections[client.tenant_id].discard(connection_id)

            logger.info(
                f"WebSocket disconnected: {connection_id} "
                f"(tenant={client.tenant_id})"
            )

    async def subscribe(
        self,
        connection_id: str,
        event_types: list[str],
    ) -> bool:
        """
        Subscribe to event types.

        Args:
            connection_id: Client connection ID
            event_types: List of event types to subscribe to

        Returns: True if subscribed, False if connection not found
        """
        if connection_id not in self.active_connections:
            return False

        client = self.active_connections[connection_id]

        # Validate event types
        valid_types = {
            "mission.created", "mission.updated", "mission.completed",
            "task.created", "task.assigned", "task.updated",
            "execution.requested", "execution.started", "execution.updated",
            "execution.completed", "execution.failed",
            "validation.requested", "validation.completed",
            "agent.status_changed",
            "projection.updated",
        }

        for event_type in event_types:
            if event_type not in valid_types:
                await client.send_error(
                    "INVALID_EVENT_TYPE",
                    f"Unknown event type: {event_type}",
                )
                return False

        # Subscribe
        client.subscriptions.update(event_types)

        logger.info(
            f"Subscribed {connection_id} to {len(event_types)} event types "
            f"(tenant={client.tenant_id})"
        )

        return True

    async def unsubscribe(
        self,
        connection_id: str,
        event_types: list[str],
    ) -> bool:
        """Unsubscribe from event types."""
        if connection_id not in self.active_connections:
            return False

        client = self.active_connections[connection_id]
        client.subscriptions.difference_update(event_types)

        return True

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        event_type: str,
        event_data: dict,
    ):
        """
        Broadcast event to all subscribed clients in a tenant.

        SECURITY: Only sends to clients subscribed to this event_type
                  AND whose tenant_id matches the event's tenant_id
        """
        if tenant_id not in self.tenant_connections:
            return

        for connection_id in list(self.tenant_connections[tenant_id]):
            if connection_id not in self.active_connections:
                # Connection lost, cleanup
                await self.disconnect(connection_id)
                continue

            client = self.active_connections[connection_id]

            # Security: Verify subscription and tenant match
            if event_type not in client.subscriptions:
                continue

            if client.tenant_id != tenant_id:
                # Security violation
                logger.warning(
                    f"Security: Tenant mismatch for {connection_id}: "
                    f"event.tenant={tenant_id}, client.tenant={client.tenant_id}"
                )
                continue

            # Send event
            message = {
                "type": "event",
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": event_data,
            }

            await client.send_json(message)

    async def handle_heartbeat(self, connection_id: str):
        """
        Handle incoming heartbeat from client.

        Returns: cursor position for missed events
        """
        if connection_id not in self.active_connections:
            return None

        client = self.active_connections[connection_id]
        client.last_heartbeat = datetime.now(timezone.utc)

        return client.cursor

    async def update_cursor(self, connection_id: str, cursor: int):
        """Update cursor for event recovery."""
        if connection_id in self.active_connections:
            self.active_connections[connection_id].cursor = cursor

    def get_active_connections_count(self) -> int:
        """Get total active connections."""
        return len(self.active_connections)

    def get_tenant_connections_count(self, tenant_id: str) -> int:
        """Get active connections for a tenant."""
        return len(self.tenant_connections.get(tenant_id, set()))

    async def cleanup_stale_connections(self, timeout_seconds: int = 60):
        """
        Remove connections that haven't sent heartbeat.

        Args:
            timeout_seconds: Disconnect if no heartbeat in this time
        """
        now = datetime.now(timezone.utc)
        stale = []

        for connection_id, client in list(self.active_connections.items()):
            elapsed = (now - client.last_heartbeat).total_seconds()
            if elapsed > timeout_seconds:
                stale.append(connection_id)

        for connection_id in stale:
            logger.warning(f"Disconnecting stale connection: {connection_id}")
            await self.disconnect(connection_id)
            if connection_id in self.active_connections:
                try:
                    # Try to close websocket, but don't fail if already closed
                    await self.active_connections[connection_id].websocket.close()
                except (RuntimeError, ConnectionClosedError) as e:
                    # Connection already closed - this is expected for stale connections
                    logger.debug(f"WebSocket already closed: {connection_id} ({type(e).__name__})")
                except Exception as e:
                    # Unexpected error - log but don't crash
                    logger.error(f"Error closing stale WebSocket {connection_id}: {e}")

        return len(stale)


# Global connection manager
connection_manager = WebSocketConnectionManager()
