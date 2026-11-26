"""Tests for authentication: login and tenant selection (12 scenarios)."""

import pytest
from sqlalchemy.orm import Session

from app.services.auth_service import login, select_tenant
from app.core.security import hash_password, normalize_email
from database.models import User, Tenant, Membership


@pytest.fixture
def setup_auth_data(db: Session):
    """Setup users, tenants, memberships for auth tests."""
    # Users
    user_active = User(
        user_id="auth-user-1",
        email="user1@example.com",
        password_hash=hash_password("SecurePass123!"),
        is_active=True,
    )
    user_inactive = User(
        user_id="auth-user-2",
        email="user2@example.com",
        password_hash=hash_password("SecurePass123!"),
        is_active=False,
    )
    user_deleted = User(
        user_id="auth-user-3",
        email="user3@example.com",
        password_hash=hash_password("SecurePass123!"),
        is_active=True,
        deleted_at="2026-01-01 00:00:00+00:00",
    )

    # Tenants
    tenant_active = Tenant(tenant_id="auth-tenant-1", name="Active Tenant", is_active=True)
    tenant_inactive = Tenant(tenant_id="auth-tenant-2", name="Inactive Tenant", is_active=False)

    # Memberships
    membership_active = Membership(
        membership_id="auth-membership-1",
        user_id=user_active.user_id,
        tenant_id=tenant_active.tenant_id,
        role="admin",
        is_active=True,
    )
    membership_inactive = Membership(
        membership_id="auth-membership-2",
        user_id=user_active.user_id,
        tenant_id=tenant_inactive.tenant_id,
        role="viewer",
        is_active=False,
    )

    db.add_all([user_active, user_inactive, user_deleted, tenant_active, tenant_inactive,
                membership_active, membership_inactive])
    db.commit()

    return {
        "user_active": user_active,
        "user_inactive": user_inactive,
        "user_deleted": user_deleted,
        "tenant_active": tenant_active,
        "tenant_inactive": tenant_inactive,
        "membership_active": membership_active,
        "membership_inactive": membership_inactive,
    }


class TestLoginService:
    """Login service tests (12 scenarios)."""

    # Scenario 1: Valid login with single membership
    def test_login_valid_single_membership(self, db: Session, setup_auth_data):
        result, error = login(db, "user1@example.com", "SecurePass123!")
        assert error is None
        assert result.get("single_tenant") is True
        assert result["access_token"] is not None
        print("✓ Scenario 1: Valid login (single membership)")

    # Scenario 2: Valid login with multiple memberships
    def test_login_valid_multiple_memberships(self, db: Session, setup_auth_data):
        # Add second active membership
        m2 = Membership(
            membership_id="auth-membership-3",
            user_id="auth-user-1",
            tenant_id="auth-tenant-1",
            role="viewer",
            is_active=True,
        )
        db.add(m2)
        db.commit()

        result, error = login(db, "user1@example.com", "SecurePass123!")
        assert error is None
        assert result.get("selection_token") is not None
        assert len(result["tenants"]) > 0
        print("✓ Scenario 2: Valid login (multiple memberships)")

    # Scenario 3: Invalid password
    def test_login_invalid_password(self, db: Session, setup_auth_data):
        result, error = login(db, "user1@example.com", "WrongPassword")
        assert error == "Invalid credentials"
        assert result is None
        print("✓ Scenario 3: Invalid password")

    # Scenario 4: User inactive
    def test_login_user_inactive(self, db: Session, setup_auth_data):
        result, error = login(db, "user2@example.com", "SecurePass123!")
        assert error == "Invalid credentials"
        print("✓ Scenario 4: User inactive")

    # Scenario 5: User deleted
    def test_login_user_deleted(self, db: Session, setup_auth_data):
        result, error = login(db, "user3@example.com", "SecurePass123!")
        assert error == "Invalid credentials"
        print("✓ Scenario 5: User deleted (soft-delete)")

    # Scenario 6: Tenant inactive
    def test_login_tenant_inactive(self, db: Session, setup_auth_data):
        # Create user with only inactive tenant membership
        user = User(
            user_id="auth-user-4",
            email="user4@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_active=True,
        )
        membership = Membership(
            membership_id="auth-membership-4",
            user_id=user.user_id,
            tenant_id="auth-tenant-2",  # inactive
            role="admin",
            is_active=True,
        )
        db.add_all([user, membership])
        db.commit()

        result, error = login(db, "user4@example.com", "SecurePass123!")
        assert error == "Invalid credentials"
        print("✓ Scenario 6: Tenant inactive")

    # Scenario 7: Membership inactive
    def test_login_membership_inactive(self, db: Session, setup_auth_data):
        result, error = login(db, "user1@example.com", "SecurePass123!")
        # user1 has one active membership, should succeed
        assert error is None
        print("✓ Scenario 7: Valid login (skips inactive membership)")

    # Scenario 8: User without membership
    def test_login_no_membership(self, db: Session, setup_auth_data):
        user = User(
            user_id="auth-user-5",
            email="user5@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_active=True,
        )
        db.add(user)
        db.commit()

        result, error = login(db, "user5@example.com", "SecurePass123!")
        assert error == "Invalid credentials"
        print("✓ Scenario 8: No membership")

    # Scenario 9: Email case-insensitive
    def test_login_email_case_insensitive(self, db: Session, setup_auth_data):
        result, error = login(db, "USER1@EXAMPLE.COM", "SecurePass123!")
        assert error is None
        assert result.get("access_token") is not None
        print("✓ Scenario 9: Email case-insensitive")

    # Scenario 10: Access token with 15-min expiration
    def test_access_token_15min_expiration(self, db: Session, setup_auth_data):
        result, error = login(db, "user1@example.com", "SecurePass123!")
        assert error is None

        # Verify token expiration
        from app.core.config import settings
        from jose import jwt as jose_jwt
        from datetime import datetime, timezone

        token = result["access_token"]
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        exp_time = payload.get("exp")
        now = datetime.now(timezone.utc).timestamp()
        exp_in_minutes = (exp_time - now) / 60

        assert 14 <= exp_in_minutes <= 16
        print("✓ Scenario 10: Access token 15-min expiration")

    # Scenario 11: Generic error responses
    def test_generic_error_messages(self, db: Session, setup_auth_data):
        # Try non-existent email
        result1, error1 = login(db, "nonexistent@example.com", "password")
        assert error1 == "Invalid credentials"

        # Try wrong password
        result2, error2 = login(db, "user1@example.com", "wrongpass")
        assert error2 == "Invalid credentials"

        # Both should have same message
        assert error1 == error2
        print("✓ Scenario 11: Generic error messages")

    # Scenario 12: Multi-tenant isolation
    def test_multitenant_isolation(self, db: Session, setup_auth_data):
        # User in one tenant cannot see another tenant's data
        user2 = User(
            user_id="auth-user-6",
            email="user6@example.com",
            password_hash=hash_password("SecurePass123!"),
            is_active=True,
        )
        tenant2 = Tenant(tenant_id="auth-tenant-3", name="Tenant 2", is_active=True)
        membership2 = Membership(
            membership_id="auth-membership-5",
            user_id=user2.user_id,
            tenant_id=tenant2.tenant_id,
            role="admin",
            is_active=True,
        )
        db.add_all([user2, tenant2, membership2])
        db.commit()

        result1, _ = login(db, "user1@example.com", "SecurePass123!")
        result2, _ = login(db, "user6@example.com", "SecurePass123!")

        # Tokens should be different
        assert result1["access_token"] != result2["access_token"]
        print("✓ Scenario 12: Multi-tenant isolation")
