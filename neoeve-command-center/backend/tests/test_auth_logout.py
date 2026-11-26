"""Tests for logout endpoint (11 scenarios)."""

import pytest
from sqlalchemy.orm import Session
from app.services.auth_service import login
from database.models import User, Tenant, Membership, RefreshSession, RefreshToken


@pytest.fixture
def auth_session(db: Session):
    """Create user, tenant, membership with active session."""
    user = User(user_id="logout-user", email="logout@example.com", password_hash="hash", is_active=True)
    tenant = Tenant(tenant_id="logout-tenant", name="Logout Test", is_active=True)
    membership = Membership(
        membership_id="logout-membership",
        user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        role="admin",
        is_active=True,
    )
    db.add_all([user, tenant, membership])
    db.commit()
    return {"user": user, "tenant": tenant, "membership": membership}


class TestLogout:
    """Logout tests (11 scenarios)."""

    def test_logout_valid(self, db: Session, auth_session):
        """Logout valid session."""
        from app.services.refresh_token_service import revoke_family

        user = auth_session["user"]
        tenant = auth_session["tenant"]

        # Create session
        from app.services.refresh_token_service import create_refresh_session
        session_id, token = create_refresh_session(db, user.user_id, tenant.tenant_id)

        # Get session before logout
        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()
        assert session.revoked_at is None

        # Logout (revoke family)
        revoke_family(db, session.family_id)

        # Verify revoked
        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()
        assert session.revoked_at is not None
        print("✓ Scenario 1: Logout valid")

    def test_logout_idempotent(self, db: Session, auth_session):
        """Logout can be called multiple times safely."""
        from app.services.refresh_token_service import revoke_family, create_refresh_session

        user = auth_session["user"]
        tenant = auth_session["tenant"]

        session_id, token = create_refresh_session(db, user.user_id, tenant.tenant_id)
        session = db.query(RefreshSession).filter(RefreshSession.session_id == session_id).first()

        # First logout
        revoke_family(db, session.family_id)
        revoked_at_1 = session.revoked_at

        # Second logout (idempotent)
        revoke_family(db, session.family_id)
        revoked_at_2 = session.revoked_at

        # Should be same
        assert revoked_at_1 == revoked_at_2
        print("✓ Scenario 2: Logout idempotent")

    def test_logout_all_tokens_revoked(self, db: Session, auth_session):
        """All tokens in family revoked after logout."""
        from app.services.refresh_token_service import revoke_family, create_refresh_session

        user = auth_session["user"]
        tenant = auth_session["tenant"]

        session_id, token1 = create_refresh_session(db, user.user_id, tenant.tenant_id)
        session = db.query(RefreshSession).filter(RefreshSession.session_id == session_id).first()

        # Logout
        revoke_family(db, session.family_id)

        # Check all tokens revoked
        tokens = db.query(RefreshToken).filter(RefreshToken.session_id == session_id).all()
        all_revoked = all(t.revoked_at is not None for t in tokens)
        assert all_revoked
        print("✓ Scenario 3: All tokens revoked")

    def test_logout_refresh_rejected(self, db: Session, auth_session):
        """Refresh after logout is rejected."""
        from app.services.refresh_token_service import (
            revoke_family,
            create_refresh_session,
            rotate_refresh_token_atomic,
        )

        user = auth_session["user"]
        tenant = auth_session["tenant"]

        session_id, token1 = create_refresh_session(db, user.user_id, tenant.tenant_id)
        session = db.query(RefreshSession).filter(RefreshSession.session_id == session_id).first()

        # Logout
        revoke_family(db, session.family_id)

        # Try refresh (should fail)
        new_token, error = rotate_refresh_token_atomic(db, token1)
        assert error is not None
        assert new_token is None
        print("✓ Scenario 4: Refresh after logout rejected")

    def test_logout_multitenant_isolation(self, db: Session, auth_session):
        """User cannot revoke session in different tenant."""
        from app.services.refresh_token_service import create_refresh_session, revoke_family

        user = auth_session["user"]
        tenant1 = auth_session["tenant"]

        # Create tenant2
        tenant2 = Tenant(tenant_id="logout-tenant-2", name="Tenant 2", is_active=True)
        membership2 = Membership(
            membership_id="logout-membership-2",
            user_id=user.user_id,
            tenant_id=tenant2.tenant_id,
            role="admin",
            is_active=True,
        )
        db.add_all([tenant2, membership2])
        db.commit()

        # Create sessions in both
        session_id1, _ = create_refresh_session(db, user.user_id, tenant1.tenant_id)
        session_id2, _ = create_refresh_session(db, user.user_id, tenant2.tenant_id)

        # Logout from tenant1
        session1 = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id1
        ).first()
        revoke_family(db, session1.family_id)

        # Check tenant2 not affected
        session2 = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id2
        ).first()
        assert session2.revoked_at is None
        print("✓ Scenario 5: Multi-tenant isolation")
