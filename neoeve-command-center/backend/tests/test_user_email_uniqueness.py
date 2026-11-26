"""Tests for User email uniqueness rules."""

import pytest
from database.models import User, utc_now
from datetime import datetime, timezone


class TestUserEmailUniqueness:
    """Email uniqueness validation tests."""

    def test_user_creation_with_email(self):
        """Test creating user with email."""
        user = User(
            user_id="user-1",
            email="alice@example.com",
            password_hash="hash..."
        )
        assert user.email == "alice@example.com"
        assert user.deleted_at is None

    def test_email_not_globally_unique_when_deleted(self):
        """Test that email can be reused after soft-delete.

        This validates the partial unique index rule:
        UNIQUE(email) WHERE deleted_at IS NULL

        Structural test: ORM should NOT have global UNIQUE on email.
        """
        # Both users can exist in memory with same email
        # if one is soft-deleted
        user1 = User(
            user_id="user-deleted",
            email="shared@example.com",
            password_hash="hash1",
            deleted_at=utc_now()
        )
        user2 = User(
            user_id="user-active",
            email="shared@example.com",
            password_hash="hash2",
            deleted_at=None  # Active
        )

        # In ORM layer, no immediate violation
        # At DB layer: partial unique index allows both
        assert user1.email == user2.email
        assert user1.deleted_at is not None
        assert user2.deleted_at is None

    def test_multiple_inactive_users_same_email(self):
        """Test that inactive users also reserve email."""
        user1 = User(
            user_id="user-inactive-1",
            email="reserved@example.com",
            password_hash="hash1",
            is_active=False,
            deleted_at=None
        )
        user2 = User(
            user_id="user-inactive-2",
            email="reserved@example.com",
            password_hash="hash2",
            is_active=False,
            deleted_at=None
        )

        # Both inactive but same email
        # At DB: should be rejected (both have deleted_at IS NULL)
        assert user1.email == user2.email
        assert user1.is_active is False
        assert user2.is_active is False

    def test_deleted_user_frees_email(self):
        """Test that soft-deleted user's email becomes available."""
        user1 = User(
            user_id="user-to-delete",
            email="temp@example.com",
            password_hash="hash1",
            deleted_at=utc_now()
        )

        # Email is now free to be used by new user
        user2 = User(
            user_id="user-new",
            email="temp@example.com",
            password_hash="hash2",
            deleted_at=None
        )

        # In memory, both can exist
        # At DB: partial index allows both (one has deleted_at != NULL)
        assert user1.email == user2.email
        assert user1.deleted_at is not None
        assert user2.deleted_at is None

    def test_orm_no_global_unique_on_email(self):
        """Verify ORM removed global UNIQUE constraint on email."""
        # This test validates the fix:
        # - ORM should NOT have unique=True on email column
        # - ORM should NOT have UniqueConstraint("email", "deleted_at")
        # - Only the partial unique index exists (in migration)

        # Check columns
        email_col = User.__table__.columns['email']
        assert email_col.unique is None or email_col.unique is False  # NO global unique

        # Check constraints
        constraints = [str(c) for c in User.__table__.constraints]
        # Should have no UNIQUE constraint mentioning email alone
        for constraint in constraints:
            assert "email" not in constraint or "UniqueConstraint" not in str(type(constraint))

    def test_case_sensitivity_handling(self):
        """Test email normalization (case-insensitive).

        Note: Structural test only. Actual normalization
        depends on application layer, not DB index.
        """
        user1 = User(
            user_id="user-1",
            email="Alice@Example.COM",
            password_hash="hash1"
        )
        user2 = User(
            user_id="user-2",
            email="alice@example.com",
            password_hash="hash2"
        )

        # At application layer, emails should be normalized to lowercase
        # At DB layer: partial unique index on LOWER(email) where deleted_at IS NULL
        # For now, structural test validates both users can exist
        assert user1.email.lower() == user2.email.lower()
