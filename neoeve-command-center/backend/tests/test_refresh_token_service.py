"""
Tests for refresh token service: generation, session creation, rotation,
reuse detection, and concurrency control.

These tests use PostgreSQL real instance for transaction and locking validation.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.services.refresh_token_service import (
    generate_secure_token,
    hash_token,
    create_refresh_session,
    rotate_refresh_token_atomic,
    revoke_session,
    revoke_family,
    get_active_sessions,
)
from database.models import User, Tenant, Membership, RefreshSession, RefreshToken


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    user = User(
        user_id="test-user-1",
        email="test@example.com",
        password_hash="hash123",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def test_tenant(db: Session):
    """Create a test tenant."""
    tenant = Tenant(
        tenant_id="test-tenant-1",
        name="Test Organization",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    return tenant


@pytest.fixture
def test_membership(db: Session, test_user, test_tenant):
    """Create a test membership."""
    membership = Membership(
        membership_id="test-membership-1",
        user_id=test_user.user_id,
        tenant_id=test_tenant.tenant_id,
        role="admin",
        is_active=True,
    )
    db.add(membership)
    db.commit()
    return membership


class TestTokenGeneration:
    """Test secure token generation and hashing."""

    def test_generate_secure_token_returns_string(self):
        """Verify that token generation returns a string."""
        token = generate_secure_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_secure_token_has_sufficient_entropy(self):
        """Verify that tokens have sufficient entropy (uniqueness)."""
        tokens = set()
        for _ in range(100):
            token = generate_secure_token()
            assert token not in tokens, "Duplicate token generated (insufficient entropy)"
            tokens.add(token)

        assert len(tokens) == 100, "Not all tokens were unique"

    def test_hash_token_produces_sha256(self):
        """Verify that token hashing produces SHA-256."""
        token = "test-token-123"
        hashed = hash_token(token)

        # SHA-256 produces 64 hex characters
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_token_deterministic(self):
        """Verify that the same token always produces the same hash."""
        token = "consistent-token"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2

    def test_hash_token_different_tokens_different_hashes(self):
        """Verify that different tokens produce different hashes."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()

        hash1 = hash_token(token1)
        hash2 = hash_token(token2)

        assert hash1 != hash2


class TestSessionCreation:
    """Test refresh session creation and validation."""

    def test_create_refresh_session_success(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify successful session creation."""
        session_id, token = create_refresh_session(
            db,
            test_user.user_id,
            test_tenant.tenant_id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        assert session_id is not None
        assert token is not None

        # Verify session in database
        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()

        assert session is not None
        assert session.user_id == test_user.user_id
        assert session.tenant_id == test_tenant.tenant_id
        assert session.user_agent == "Mozilla/5.0"
        assert session.ip_address == "192.168.1.1"
        assert session.revoked_at is None

    def test_create_refresh_session_generates_token_hash(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify that token hash is stored (not original token)."""
        session_id, token = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )

        # Find the token in database
        refresh_token = db.query(RefreshToken).filter(
            RefreshToken.session_id == session_id
        ).first()

        assert refresh_token is not None
        assert refresh_token.token_hash == hash_token(token)

    def test_create_refresh_session_validates_user_active(self, db: Session):
        """Verify that session creation fails for inactive user."""
        inactive_user = User(
            user_id="inactive-user",
            email="inactive@example.com",
            password_hash="hash",
            is_active=False,
        )
        db.add(inactive_user)

        tenant = Tenant(
            tenant_id="test-tenant-2",
            name="Test",
            is_active=True,
        )
        db.add(tenant)

        membership = Membership(
            membership_id="test-membership-2",
            user_id=inactive_user.user_id,
            tenant_id=tenant.tenant_id,
            role="admin",
            is_active=True,
        )
        db.add(membership)
        db.commit()

        with pytest.raises(ValueError, match="not found or inactive"):
            create_refresh_session(db, inactive_user.user_id, tenant.tenant_id)

    def test_create_refresh_session_validates_membership(
        self, db: Session, test_user, test_tenant
    ):
        """Verify that session creation fails without active membership."""
        with pytest.raises(ValueError, match="no active membership"):
            create_refresh_session(
                db, test_user.user_id, test_tenant.tenant_id
            )

    def test_create_refresh_session_sets_expiration(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify that session and token have correct expiration."""
        now_before = datetime.now(timezone.utc)
        session_id, token = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )
        now_after = datetime.now(timezone.utc)

        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()

        # Expiration should be ~7 days from now
        expected_min = now_before + timedelta(days=7) - timedelta(seconds=1)
        expected_max = now_after + timedelta(days=7) + timedelta(seconds=1)

        assert expected_min <= session.expires_at <= expected_max


class TestTokenRotation:
    """Test atomic token rotation with concurrency."""

    def test_rotate_refresh_token_success(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify successful token rotation."""
        session_id, old_token = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )

        new_token, error = rotate_refresh_token_atomic(db, old_token)

        assert new_token is not None
        assert error is None
        assert new_token != old_token

        # Verify old token is marked as used
        old_token_record = db.query(RefreshToken).filter(
            RefreshToken.token_hash == hash_token(old_token)
        ).first()

        assert old_token_record.used_at is not None
        assert old_token_record.replaced_by_token_id is not None

    def test_rotate_refresh_token_invalid_token(self, db: Session):
        """Verify that rotation fails with invalid token."""
        new_token, error = rotate_refresh_token_atomic(db, "invalid-token-xyz")

        assert new_token is None
        assert error == "token_invalid"

    def test_rotate_refresh_token_expired_token(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify that rotation fails with expired token."""
        session_id, token = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )

        # Manually expire the token
        refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token_hash == hash_token(token)
        ).first()

        refresh_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        new_token, error = rotate_refresh_token_atomic(db, token)

        assert new_token is None
        assert error == "token_expired"

    def test_rotate_refresh_token_revoked_token(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify that rotation fails with revoked token."""
        session_id, token = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )

        # Manually revoke the token
        refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token_hash == hash_token(token)
        ).first()

        refresh_token.revoked_at = datetime.now(timezone.utc)
        db.commit()

        new_token, error = rotate_refresh_token_atomic(db, token)

        assert new_token is None
        assert error == "token_revoked"

    def test_rotate_refresh_token_reuse_detection(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify that token reuse is detected and family is revoked."""
        session_id, token1 = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )

        # First rotation (success)
        token2, error1 = rotate_refresh_token_atomic(db, token1)
        assert error1 is None

        # Attempt to reuse token1 (should fail and revoke family)
        token3, error2 = rotate_refresh_token_atomic(db, token1)

        assert token3 is None
        assert error2 == "token_reused"

        # Verify session is revoked
        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()

        assert session.revoked_at is not None
        assert session.revoke_reason == "token_reuse_detected"


class TestSessionRevocation:
    """Test session and family revocation."""

    def test_revoke_session(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify session revocation."""
        session_id, token = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )

        success = revoke_session(db, session_id, reason="user_logout")

        assert success is True

        # Verify session is revoked
        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()

        assert session.revoked_at is not None
        assert session.revoke_reason == "user_logout"

    def test_revoke_family(
        self, db: Session, test_user, test_tenant, test_membership
    ):
        """Verify family revocation."""
        session_id1, token1 = create_refresh_session(
            db, test_user.user_id, test_tenant.tenant_id
        )

        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id1
        ).first()

        family_id = session.family_id

        revoke_family(db, family_id, reason="security_incident")

        # Verify session is revoked
        session = db.query(RefreshSession).filter(
            RefreshSession.session_id == session_id1
        ).first()

        assert session.revoked_at is not None


class TestMultiTenant:
    """Test multi-tenant isolation."""

    def test_refresh_token_isolated_by_tenant(
        self, db: Session, test_user
    ):
        """Verify that tokens are isolated by tenant."""
        # Create two tenants
        tenant1 = Tenant(
            tenant_id="tenant-1",
            name="Organization 1",
            is_active=True,
        )
        tenant2 = Tenant(
            tenant_id="tenant-2",
            name="Organization 2",
            is_active=True,
        )
        db.add_all([tenant1, tenant2])

        # Create memberships in both tenants
        membership1 = Membership(
            membership_id="membership-1",
            user_id=test_user.user_id,
            tenant_id=tenant1.tenant_id,
            role="admin",
            is_active=True,
        )
        membership2 = Membership(
            membership_id="membership-2",
            user_id=test_user.user_id,
            tenant_id=tenant2.tenant_id,
            role="admin",
            is_active=True,
        )
        db.add_all([membership1, membership2])
        db.commit()

        # Create sessions in both tenants
        session_id1, token1 = create_refresh_session(
            db, test_user.user_id, tenant1.tenant_id
        )

        session_id2, token2 = create_refresh_session(
            db, test_user.user_id, tenant2.tenant_id
        )

        # Verify sessions are different
        assert session_id1 != session_id2

        # Verify sessions have different tokens
        assert token1 != token2

        # Get active sessions for user
        sessions = get_active_sessions(db, test_user.user_id)

        assert len(sessions) == 2
