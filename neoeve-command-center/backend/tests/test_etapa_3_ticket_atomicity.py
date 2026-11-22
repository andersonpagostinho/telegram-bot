"""
ETAPA 3: WebSocket Ticket Atomicity Tests

Validates that WebSocket ticket consumption is atomic and thread-safe.
Prevents TOCTOU (Time-of-check Time-of-use) vulnerabilities.

Concurrency Scenario:
- 5+ threads attempt to consume the same ticket simultaneously
- Exactly 1 must succeed (get the ticket object)
- Others must fail with None
- No duplicate consumption
"""

import pytest
import threading
import time
from datetime import datetime, timezone, timedelta
from app.services.websocket_ticket_service import WebSocketTicketService, WebSocketTicket


class TestTicketAtomicity:
    """Test atomic ticket consumption with concurrent access."""

    @pytest.fixture
    def ticket_service():
        """Create a fresh ticket service for each test."""
        return WebSocketTicketService(ticket_ttl_minutes=5)

    def test_single_ticket_consumption(self, ticket_service):
        """Test basic single-threaded ticket consumption."""
        # Issue a ticket
        ticket_id = ticket_service.issue_ticket(
            tenant_id="test_tenant",
            user_id="user_1",
            actor_id="actor_1",
            actor_role="admin",
        )

        # First consume should succeed
        result = ticket_service.validate_and_consume_ticket(ticket_id)
        assert result is not None
        assert result.ticket_id == ticket_id
        assert result.consumed is True

        # Second consume should fail (already consumed)
        result = ticket_service.validate_and_consume_ticket(ticket_id)
        assert result is None

    def test_concurrent_consume_one_winner(self, ticket_service):
        """Test concurrent consumption - only one succeeds."""
        # Issue a ticket
        ticket_id = ticket_service.issue_ticket(
            tenant_id="test_tenant",
            user_id="user_1",
            actor_id="actor_1",
            actor_role="admin",
        )

        # Try to consume from multiple threads concurrently
        results = []
        lock = threading.Lock()

        def consumer(thread_id):
            """Attempt to consume ticket in a thread."""
            result = ticket_service.validate_and_consume_ticket(ticket_id)
            with lock:
                results.append({
                    "thread_id": thread_id,
                    "result": result,
                    "success": result is not None,
                })

        # Spawn 5 threads to consume the same ticket
        threads = []
        for i in range(5):
            t = threading.Thread(target=consumer, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify exactly 1 thread succeeded
        successes = [r for r in results if r["success"]]
        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"

        # Verify 4 threads failed
        failures = [r for r in results if not r["success"]]
        assert len(failures) == 4, f"Expected 4 failures, got {len(failures)}"

        # Verify the successful result
        success_result = successes[0]["result"]
        assert success_result.ticket_id == ticket_id
        assert success_result.consumed is True

    def test_concurrent_consume_different_tickets(self, ticket_service):
        """Test concurrent consumption of different tickets - all succeed."""
        # Issue multiple tickets
        tickets = []
        for i in range(5):
            ticket_id = ticket_service.issue_ticket(
                tenant_id="test_tenant",
                user_id=f"user_{i}",
                actor_id=f"actor_{i}",
                actor_role="admin",
            )
            tickets.append(ticket_id)

        # Try to consume each from a thread
        results = []
        lock = threading.Lock()

        def consumer(ticket_id):
            """Attempt to consume ticket in a thread."""
            result = ticket_service.validate_and_consume_ticket(ticket_id)
            with lock:
                results.append({
                    "ticket_id": ticket_id,
                    "result": result,
                    "success": result is not None,
                })

        # Spawn threads to consume different tickets
        threads = []
        for ticket_id in tickets:
            t = threading.Thread(target=consumer, args=(ticket_id,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # All should succeed (different tickets)
        successes = [r for r in results if r["success"]]
        assert len(successes) == 5, f"Expected 5 successes, got {len(successes)}"

    def test_expired_ticket_not_consumed(self, ticket_service):
        """Test that expired tickets cannot be consumed."""
        # Issue a ticket with 0 TTL (expired immediately)
        expired_service = WebSocketTicketService(ticket_ttl_minutes=0)

        ticket_id = expired_service.issue_ticket(
            tenant_id="test_tenant",
            user_id="user_1",
            actor_id="actor_1",
            actor_role="admin",
        )

        # Give the system a moment for expiry
        time.sleep(0.1)

        # Try to consume - should fail (expired)
        result = expired_service.validate_and_consume_ticket(ticket_id)
        assert result is None

    def test_already_consumed_cannot_be_consumed_again(self, ticket_service):
        """Test that consuming an already-consumed ticket fails."""
        ticket_id = ticket_service.issue_ticket(
            tenant_id="test_tenant",
            user_id="user_1",
            actor_id="actor_1",
            actor_role="admin",
        )

        # First consume succeeds
        result1 = ticket_service.validate_and_consume_ticket(ticket_id)
        assert result1 is not None
        assert result1.consumed is True

        # Second consume fails
        result2 = ticket_service.validate_and_consume_ticket(ticket_id)
        assert result2 is None

    def test_nonexistent_ticket_returns_none(self, ticket_service):
        """Test that consuming nonexistent ticket returns None."""
        result = ticket_service.validate_and_consume_ticket("nonexistent_ticket_xyz")
        assert result is None

    def test_ticket_stats_consistency_concurrent(self, ticket_service):
        """Test that stats remain consistent under concurrent access."""
        # Issue 10 tickets
        tickets = []
        for i in range(10):
            ticket_id = ticket_service.issue_ticket(
                tenant_id="test_tenant",
                user_id=f"user_{i}",
                actor_id=f"actor_{i}",
                actor_role="admin",
            )
            tickets.append(ticket_id)

        # Consume first 5 from different threads
        def consumer(ticket_id):
            ticket_service.validate_and_consume_ticket(ticket_id)

        threads = []
        for ticket_id in tickets[:5]:
            t = threading.Thread(target=consumer, args=(ticket_id,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Check stats
        stats = ticket_service.get_stats()
        assert stats["total_issued"] == 10
        assert stats["consumed"] == 5
        assert stats["active"] == 5  # 5 not yet consumed

    def test_high_concurrency_stress(self, ticket_service):
        """Stress test with high concurrency (20 threads on 1 ticket)."""
        ticket_id = ticket_service.issue_ticket(
            tenant_id="test_tenant",
            user_id="user_1",
            actor_id="actor_1",
            actor_role="admin",
        )

        results = []
        lock = threading.Lock()

        def consumer(thread_id):
            """Attempt to consume ticket."""
            result = ticket_service.validate_and_consume_ticket(ticket_id)
            with lock:
                results.append(result is not None)

        # Spawn 20 threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=consumer, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all
        for t in threads:
            t.join()

        # Exactly 1 success out of 20
        successes = sum(results)
        assert successes == 1, f"Expected exactly 1 success out of 20, got {successes}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
