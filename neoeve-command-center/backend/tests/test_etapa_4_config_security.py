"""
ETAPA 4: Configuration Security Tests

Validates:
1. No hardcoded credentials in config
2. Required environment variables are enforced
3. Rate limiting works correctly
4. Proper exception handling
"""

import pytest
import os
from unittest.mock import patch
from app.core.config import Settings
from app.services.websocket_ticket_service import WebSocketTicketService


class TestConfigSecurity:
    """Test configuration security."""

    def test_database_url_required(self):
        """Test that DATABASE_URL is required (not hardcoded)."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear all env vars
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "DATABASE_URL" in str(exc_info.value)
            assert "environment" in str(exc_info.value).lower()

    def test_secret_key_required(self):
        """Test that SECRET_KEY is required."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "SECRET_KEY" in str(exc_info.value)

    def test_valid_config_with_env_vars(self):
        """Test that config loads successfully with required env vars."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "SECRET_KEY": "test-secret-key-12345",
        }, clear=True):
            settings = Settings()
            assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
            assert settings.SECRET_KEY == "test-secret-key-12345"

    def test_no_default_credentials_exposed(self):
        """Test that no default credentials are in config."""
        # This test verifies the fix - check the source code
        with open("app/core/config.py", "r") as f:
            content = f.read()
            # Should not have hardcoded postgres credentials
            assert "neoeve_dev:neoeve_dev_123" not in content
            assert "neoeve_dev_123" not in content

    def test_cors_origins_configurable(self):
        """Test that CORS origins are configurable via env."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test",
            "SECRET_KEY": "test",
            "CORS_ORIGINS": "http://example.com,https://app.example.com",
        }, clear=True):
            settings = Settings()
            assert "http://example.com" in settings.CORS_ORIGINS
            assert "https://app.example.com" in settings.CORS_ORIGINS


class TestRateLimiting:
    """Test WebSocket ticket rate limiting."""

    def test_rate_limit_per_user(self):
        """Test that rate limiting is enforced per user."""
        # Create service with low rate limit for testing
        service = WebSocketTicketService(
            ticket_ttl_minutes=5,
            rate_limit=3,
            rate_window_seconds=60
        )

        user_id = "test_user_1"

        # First 3 tickets should succeed
        for i in range(3):
            ticket = service.issue_ticket(
                tenant_id="test_tenant",
                user_id=user_id,
                actor_id=f"actor_{i}",
                actor_role="admin",
            )
            assert ticket is not None, f"Ticket {i+1} should succeed (within limit)"

        # 4th ticket should fail (rate limit exceeded)
        ticket = service.issue_ticket(
            tenant_id="test_tenant",
            user_id=user_id,
            actor_id="actor_4",
            actor_role="admin",
        )
        assert ticket is None, "4th ticket should fail (rate limit exceeded)"

    def test_rate_limit_per_user_isolated(self):
        """Test that rate limiting is per user, not global."""
        service = WebSocketTicketService(
            ticket_ttl_minutes=5,
            rate_limit=2,
            rate_window_seconds=60
        )

        # User 1 issues 2 tickets (at limit)
        for i in range(2):
            ticket = service.issue_ticket(
                tenant_id="test_tenant",
                user_id="user_1",
                actor_id=f"actor_{i}",
                actor_role="admin",
            )
            assert ticket is not None

        # User 2 should still be able to issue tickets
        ticket = service.issue_ticket(
            tenant_id="test_tenant",
            user_id="user_2",
            actor_id="actor_new",
            actor_role="admin",
        )
        assert ticket is not None, "User 2 should not be affected by User 1's rate limit"

    def test_rate_limit_window_expires(self):
        """Test that rate limit resets after window expires."""
        service = WebSocketTicketService(
            ticket_ttl_minutes=5,
            rate_limit=1,  # Only 1 ticket per window
            rate_window_seconds=1  # 1 second window for testing
        )

        user_id = "test_user"

        # First ticket succeeds
        ticket1 = service.issue_ticket(
            tenant_id="test_tenant",
            user_id=user_id,
            actor_id="actor_1",
            actor_role="admin",
        )
        assert ticket1 is not None

        # Second ticket (within 1 second) fails
        ticket2 = service.issue_ticket(
            tenant_id="test_tenant",
            user_id=user_id,
            actor_id="actor_2",
            actor_role="admin",
        )
        assert ticket2 is None, "Rate limit should block second ticket"

        # Wait for window to expire
        import time
        time.sleep(1.1)

        # Third ticket (after window expires) succeeds
        ticket3 = service.issue_ticket(
            tenant_id="test_tenant",
            user_id=user_id,
            actor_id="actor_3",
            actor_role="admin",
        )
        assert ticket3 is not None, "Rate limit window should have expired"

    def test_rate_limit_configurable(self):
        """Test that rate limit is configurable."""
        # Service with higher limit
        service_high = WebSocketTicketService(rate_limit=10)
        assert service_high.rate_limit == 10

        # Service with lower limit
        service_low = WebSocketTicketService(rate_limit=1)
        assert service_low.rate_limit == 1

    def test_rate_limit_window_configurable(self):
        """Test that rate window is configurable."""
        service = WebSocketTicketService(rate_window_seconds=120)
        assert service.rate_window_seconds == 120


class TestExceptionHandling:
    """Test that exception handling is specific, not bare excepts."""

    def test_websocket_manager_no_bare_except(self):
        """Verify websocket_manager.py has no bare except clauses."""
        with open("app/services/websocket_manager.py", "r") as f:
            content = f.read()
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "except:" in line and not "except (" in line:
                    # Found a bare except - this should not exist
                    pytest.fail(f"Found bare except clause at line {i+1}: {line.strip()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
