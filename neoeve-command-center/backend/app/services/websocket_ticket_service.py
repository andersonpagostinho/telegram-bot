"""
WebSocket ticket service for secure authentication.

Security model:
- Tickets are single-use, short-lived (5 minutes)
- Issued only to authenticated users
- Linked to tenant_id from authenticated identity
- Consumed atomically at handshake
- Never logged or exposed
"""

import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WebSocketTicket:
    """Single-use WebSocket authentication ticket."""
    ticket_id: str
    tenant_id: str
    user_id: str
    actor_id: str
    actor_role: str
    issued_at: datetime
    expires_at: datetime
    consumed: bool = False

    def is_valid(self) -> bool:
        """Check if ticket is still valid."""
        if self.consumed:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def consume(self) -> bool:
        """Mark ticket as consumed (atomic)."""
        if not self.is_valid():
            return False
        self.consumed = True
        logger.info(
            f"WebSocket ticket consumed: {self.ticket_id[:8]}... "
            f"(tenant={self.tenant_id})"
        )
        return True


class WebSocketTicketService:
    """
    Issue and validate short-lived WebSocket authentication tickets.

    Prevents JWT from appearing in URLs while maintaining security.
    """

    def __init__(self, ticket_ttl_minutes: int = 5):
        """
        Initialize ticket service.

        Args:
            ticket_ttl_minutes: Ticket time-to-live in minutes (default: 5)
        """
        self.tickets: dict[str, WebSocketTicket] = {}
        self.ticket_ttl = timedelta(minutes=ticket_ttl_minutes)

    def issue_ticket(
        self,
        tenant_id: str,
        user_id: str,
        actor_id: str,
        actor_role: str,
    ) -> str:
        """
        Issue a new WebSocket ticket.

        Args:
            tenant_id: Authenticated tenant
            user_id: Authenticated user
            actor_id: Canonical actor ID
            actor_role: User role

        Returns:
            Ticket string (should be transmitted securely, not logged)
        """
        ticket_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        ticket = WebSocketTicket(
            ticket_id=ticket_id,
            tenant_id=tenant_id,
            user_id=user_id,
            actor_id=actor_id,
            actor_role=actor_role,
            issued_at=now,
            expires_at=now + self.ticket_ttl,
        )

        self.tickets[ticket_id] = ticket

        # Log only minimal info (not the ticket itself)
        logger.debug(
            f"WebSocket ticket issued for tenant={tenant_id} "
            f"user={user_id}"
        )

        return ticket_id

    def validate_and_consume_ticket(self, ticket_id: str) -> Optional[WebSocketTicket]:
        """
        Validate and consume a ticket (atomic operation).

        Args:
            ticket_id: Ticket to validate and consume

        Returns:
            Ticket if valid and consumed, None otherwise
        """
        if ticket_id not in self.tickets:
            logger.warning(f"WebSocket ticket not found: {ticket_id[:8]}...")
            return None

        ticket = self.tickets[ticket_id]

        if not ticket.is_valid():
            logger.warning(
                f"WebSocket ticket invalid: {ticket_id[:8]}... "
                f"(consumed={ticket.consumed}, expired={datetime.now(timezone.utc) > ticket.expires_at})"
            )
            return None

        # Consume ticket (mark as used)
        ticket.consume()
        return ticket

    def cleanup_expired_tickets(self):
        """Remove expired tickets (run periodically)."""
        now = datetime.now(timezone.utc)
        expired = [
            ticket_id
            for ticket_id, ticket in self.tickets.items()
            if ticket.expires_at < now
        ]

        for ticket_id in expired:
            del self.tickets[ticket_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired WebSocket tickets")

    def get_stats(self) -> dict:
        """Get ticket service statistics."""
        now = datetime.now(timezone.utc)
        active = sum(
            1 for t in self.tickets.values()
            if t.is_valid()
        )
        consumed = sum(
            1 for t in self.tickets.values()
            if t.consumed
        )
        expired = sum(
            1 for t in self.tickets.values()
            if t.expires_at < now and not t.consumed
        )

        return {
            "total_issued": len(self.tickets),
            "active": active,
            "consumed": consumed,
            "expired": expired,
        }


# Global ticket service
ticket_service = WebSocketTicketService(ticket_ttl_minutes=5)
