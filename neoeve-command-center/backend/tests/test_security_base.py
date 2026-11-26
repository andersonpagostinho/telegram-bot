"""Tests for security base functionality: token expiration and email normalization."""

import pytest
from datetime import timedelta, datetime, timezone
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    normalize_email,
    TokenPayload,
)
from app.core.config import settings
from jose import jwt


class TestAccessTokenExpiration:
    """Test access token expiration settings."""

    def test_access_token_expires_in_15_minutes(self):
        """Verify that ACCESS_TOKEN_EXPIRE_MINUTES is set to 15 (production default)."""
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15, \
            f"ACCESS_TOKEN_EXPIRE_MINUTES should be 15, got {settings.ACCESS_TOKEN_EXPIRE_MINUTES}"

    def test_create_access_token_uses_15_minute_default(self):
        """Verify that create_access_token uses the 15-minute default expiration."""
        token = create_access_token(
            user_id="user-1",
            tenant_id="tenant-1",
            actor_id="actor-1",
            actor_role="admin"
        )

        # Decode token to verify expiration
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Extract exp claim
        exp = payload.get("exp")
        assert exp is not None, "Token should have exp claim"

        # Verify exp is approximately 15 minutes from now
        now = datetime.now(timezone.utc).timestamp()
        exp_in_minutes = (exp - now) / 60

        # Allow ±1 minute tolerance for test execution time
        assert 14 <= exp_in_minutes <= 16, \
            f"Token expiration should be ~15 minutes, got {exp_in_minutes:.2f} minutes"

    def test_create_access_token_custom_expiration(self):
        """Verify that custom expiration can override default."""
        custom_expiration = timedelta(hours=1)
        token = create_access_token(
            user_id="user-1",
            tenant_id="tenant-1",
            actor_id="actor-1",
            actor_role="admin",
            expires_delta=custom_expiration
        )

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        exp = payload.get("exp")
        now = datetime.now(timezone.utc).timestamp()
        exp_in_minutes = (exp - now) / 60

        # Custom expiration is 1 hour
        assert 59 <= exp_in_minutes <= 61, \
            f"Token expiration should be ~60 minutes, got {exp_in_minutes:.2f} minutes"


class TestEmailNormalization:
    """Test email normalization for consistency and security."""

    def test_normalize_email_lowercase(self):
        """Verify that normalize_email converts to lowercase."""
        assert normalize_email("Alice@Example.COM") == "alice@example.com"
        assert normalize_email("TEST@EMAIL.ORG") == "test@email.org"

    def test_normalize_email_strip_whitespace(self):
        """Verify that normalize_email removes leading/trailing whitespace."""
        assert normalize_email("  alice@example.com  ") == "alice@example.com"
        assert normalize_email("\t  bob@test.com\n") == "bob@test.com"

    def test_normalize_email_combined(self):
        """Verify that normalize_email handles both case and whitespace together."""
        assert normalize_email("  Alice@Example.COM  ") == "alice@example.com"
        assert normalize_email("\n  TEST@EMAIL.ORG\t") == "test@email.org"

    def test_normalize_email_empty_raises_error(self):
        """Verify that normalize_email raises error on empty input."""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            normalize_email("")

        with pytest.raises(ValueError, match="Email cannot be empty"):
            normalize_email("   ")

        with pytest.raises(ValueError, match="Email cannot be empty"):
            normalize_email("\t\n")

    def test_normalize_email_consistency_with_database_index(self):
        """Verify that normalization is compatible with PostgreSQL LOWER(email) index."""
        # PostgreSQL LOWER(email) index should match normalized emails
        email = "Alice@Example.COM"
        normalized = normalize_email(email)

        # In PostgreSQL: SELECT * FROM users WHERE LOWER(email) = 'alice@example.com'
        # Should find user with original email "Alice@Example.COM"
        assert normalized == "alice@example.com"


class TestSecurityIntegration:
    """Integration tests for security functions."""

    def test_no_regression_hash_verify(self):
        """Verify password hashing and verification still work after changes."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_no_regression_jwt_validation(self):
        """Verify JWT token creation and validation still work after changes."""
        token = create_access_token(
            user_id="user-1",
            tenant_id="tenant-1",
            actor_id="actor-1",
            actor_role="admin"
        )

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert payload["user_id"] == "user-1"
        assert payload["tenant_id"] == "tenant-1"
        assert payload["actor_id"] == "actor-1"
        assert payload["actor_role"] == "admin"
        assert "exp" in payload
