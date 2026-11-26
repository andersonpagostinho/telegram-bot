"""
Real concurrency tests for refresh token service using PostgreSQL 16.
Tests simultaneous token rotation with multiple independent sessions.
"""

import pytest
import threading
import time
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.services.refresh_token_service import (
    create_refresh_session,
    rotate_refresh_token_atomic,
    hash_token,
)
from database.models import Base, User, Tenant, Membership, RefreshSession, RefreshToken

# Shared engine for concurrent tests
DATABASE_URL = "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"


class TestConcurrencyRealPostgreSQL:
    """Concurrency tests using real PostgreSQL connections."""

    @pytest.fixture(scope="class")
    def setup_concurrency_db(self):
        """Setup database for concurrency tests."""
        engine = create_engine(DATABASE_URL, echo=False)
        Base.metadata.create_all(engine)
        yield engine

        # Cleanup
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE refresh_tokens CASCADE"))
            conn.execute(text("TRUNCATE TABLE refresh_sessions CASCADE"))
            conn.execute(text("TRUNCATE TABLE invite_tokens CASCADE"))
            conn.execute(text("TRUNCATE TABLE memberships CASCADE"))
            conn.execute(text("TRUNCATE TABLE tenants CASCADE"))
            conn.execute(text("TRUNCATE TABLE users CASCADE"))
            conn.commit()

    @pytest.fixture
    def concurrent_session_factory(self, setup_concurrency_db):
        """Create independent sessions for concurrent operations."""
        SessionLocal = sessionmaker(bind=setup_concurrency_db, autocommit=False)

        def create_session():
            return SessionLocal()

        return create_session

    def test_concurrent_token_rotation_same_token(self, concurrent_session_factory):
        """
        Test: Two simultaneous rotations with the same token.
        Expected: Only one succeeds, other detects reuse and revokes family.
        """
        # Setup: Create user, tenant, membership
        session1 = concurrent_session_factory()
        user = User(
            user_id="concurrent-user-1",
            email="concurrent@example.com",
            password_hash="hash",
            is_active=True,
        )
        session1.add(user)

        tenant = Tenant(
            tenant_id="concurrent-tenant-1",
            name="Concurrent Test",
            is_active=True,
        )
        session1.add(tenant)

        membership = Membership(
            membership_id="concurrent-membership-1",
            user_id=user.user_id,
            tenant_id=tenant.tenant_id,
            role="admin",
            is_active=True,
        )
        session1.add(membership)
        session1.commit()
        session1.close()

        # Create initial session and token
        session2 = concurrent_session_factory()
        session_id, token = create_refresh_session(
            session2, user.user_id, tenant.tenant_id
        )
        session2.close()

        # Results storage
        results = {"rotation1": None, "rotation2": None, "errors": []}
        lock = threading.Lock()

        def rotate_in_thread(thread_id):
            """Rotate token in independent thread with new session."""
            try:
                # Create independent session for this thread
                session = concurrent_session_factory()

                new_token, error = rotate_refresh_token_atomic(session, token)

                with lock:
                    results[f"rotation{thread_id}"] = (new_token, error)

                session.close()
            except Exception as e:
                with lock:
                    results["errors"].append(f"Thread {thread_id}: {str(e)}")

        # Launch two concurrent rotations
        t1 = threading.Thread(target=rotate_in_thread, args=(1,))
        t2 = threading.Thread(target=rotate_in_thread, args=(2,))

        t1.start()
        t2.start()

        # Wait for both to complete
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Verify results
        rotation1 = results["rotation1"]
        rotation2 = results["rotation2"]

        assert rotation1 is not None, "Thread 1 did not complete"
        assert rotation2 is not None, "Thread 2 did not complete"

        # One should succeed, one should detect reuse
        successful = sum(1 for r in [rotation1, rotation2] if r[1] is None)
        reuse_detected = sum(1 for r in [rotation1, rotation2] if r[1] == "token_reused")

        assert successful == 1, (
            f"Expected 1 success, got {successful}. "
            f"Results: {rotation1}, {rotation2}"
        )
        assert reuse_detected == 1, (
            f"Expected 1 reuse detected, got {reuse_detected}. "
            f"Results: {rotation1}, {rotation2}"
        )

        # Verify family is revoked in database
        session3 = concurrent_session_factory()
        refresh_session = session3.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()

        assert refresh_session is not None
        assert refresh_session.revoked_at is not None, (
            "Session should be revoked after reuse detection"
        )
        assert refresh_session.revoke_reason == "token_reuse_detected"

        # Verify all tokens are revoked
        tokens = session3.query(RefreshToken).filter(
            RefreshToken.session_id == session_id
        ).all()

        all_revoked = all(t.revoked_at is not None for t in tokens)
        assert all_revoked, "All tokens should be revoked after reuse detection"

        session3.close()

    def test_token_reuse_persists_after_session_close(self, concurrent_session_factory):
        """
        Test: Revocation persists in PostgreSQL after all sessions close.
        This validates the commit() persists the data.
        """
        # Setup user/tenant/membership in one session
        session1 = concurrent_session_factory()
        user = User(
            user_id="persist-user",
            email="persist@example.com",
            password_hash="hash",
            is_active=True,
        )
        session1.add(user)

        tenant = Tenant(
            tenant_id="persist-tenant",
            name="Persist Test",
            is_active=True,
        )
        session1.add(tenant)

        membership = Membership(
            membership_id="persist-membership",
            user_id=user.user_id,
            tenant_id=tenant.tenant_id,
            role="admin",
            is_active=True,
        )
        session1.add(membership)
        session1.commit()
        session1.close()

        # Create session and token
        session2 = concurrent_session_factory()
        session_id, token = create_refresh_session(
            session2, user.user_id, tenant.tenant_id
        )
        session2.close()

        # Rotate once (success)
        session3 = concurrent_session_factory()
        new_token, error1 = rotate_refresh_token_atomic(session3, token)
        assert error1 is None
        session3.close()

        # Rotate again with old token (reuse detection)
        session4 = concurrent_session_factory()
        result_token, error2 = rotate_refresh_token_atomic(session4, token)
        assert error2 == "token_reused"
        session4.close()

        # NOW: Close all sessions and query fresh to verify persistence
        time.sleep(0.5)  # Ensure writes complete

        # Create brand new session
        session5 = concurrent_session_factory()

        # Query session state
        refresh_session = session5.query(RefreshSession).filter(
            RefreshSession.session_id == session_id
        ).first()

        # Verify revocation persisted in PostgreSQL
        assert refresh_session is not None
        assert refresh_session.revoked_at is not None, (
            "Revocation must persist after session close"
        )

        session5.close()
