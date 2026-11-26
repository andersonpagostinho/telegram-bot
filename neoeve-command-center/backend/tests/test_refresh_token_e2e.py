"""
End-to-end test: Token rotation and reuse detection with persistence validation.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.refresh_token_service import (
    create_refresh_session,
    rotate_refresh_token_atomic,
    hash_token,
)
from database.models import User, Tenant, Membership, RefreshSession, RefreshToken


def test_e2e_token_rotation_and_reuse_detection(db: Session):
    """E2E: Create T1 → Rotate to T2 → Reuse T1 → Verify revocation persists."""

    # Setup: User, tenant, membership
    user = User(user_id="e2e-user", email="e2e@example.com", password_hash="hash", is_active=True)
    tenant = Tenant(tenant_id="e2e-tenant", name="E2E Test", is_active=True)
    membership = Membership(
        membership_id="e2e-membership",
        user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        role="admin",
        is_active=True,
    )
    db.add_all([user, tenant, membership])
    db.commit()

    # 1. Create session and T1
    session_id, token1 = create_refresh_session(db, user.user_id, tenant.tenant_id)
    assert token1 is not None
    print(f"✓ Created T1: {token1[:20]}...")

    # 2. Rotate T1 → T2 (success)
    token2, error1 = rotate_refresh_token_atomic(db, token1)
    assert error1 is None, f"Rotation failed: {error1}"
    assert token2 is not None
    print(f"✓ Rotated T1 → T2: {token2[:20]}...")

    # 3. Query: T1 should be marked as used
    t1_record = db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(token1)).first()
    assert t1_record.used_at is not None
    assert t1_record.replaced_by_token_id is not None
    print(f"✓ T1 marked as used")

    # 4. Reuse T1 (should detect and revoke family)
    token3, error2 = rotate_refresh_token_atomic(db, token1)
    assert error2 == "token_reused", f"Expected 'token_reused', got {error2}"
    assert token3 is None
    print(f"✓ T1 reuse detected")

    # 5. Verify family is revoked
    session = db.query(RefreshSession).filter(RefreshSession.session_id == session_id).first()
    assert session.revoked_at is not None
    assert session.revoke_reason == "token_reuse_detected"
    print(f"✓ Session revoked: {session.revoked_at}")

    # 6. Verify all tokens in family are revoked
    tokens = db.query(RefreshToken).filter(RefreshToken.session_id == session_id).all()
    all_revoked = all(t.revoked_at is not None for t in tokens)
    assert all_revoked, f"Not all tokens revoked: {[(t.refresh_token_id, t.revoked_at) for t in tokens]}"
    print(f"✓ All {len(tokens)} tokens in family revoked")

    # 7. Try to use T2 (should fail - family revoked)
    new_token_from_t2, error3 = rotate_refresh_token_atomic(db, token2)
    assert error3 is not None, "T2 should be rejected (family revoked)"
    assert new_token_from_t2 is None
    print(f"✓ T2 rejected: {error3}")

    # 8. Close session and query fresh to verify persistence
    db.close()

    # Create NEW session (simulates client reconnect)
    SessionLocal = type(db)
    fresh_session = SessionLocal()

    fresh_session_record = fresh_session.query(RefreshSession).filter(
        RefreshSession.session_id == session_id
    ).first()

    assert fresh_session_record.revoked_at is not None, "Revocation must persist after session close"
    fresh_tokens = fresh_session.query(RefreshToken).filter(
        RefreshToken.session_id == session_id
    ).all()
    fresh_all_revoked = all(t.revoked_at is not None for t in fresh_tokens)
    assert fresh_all_revoked, "Revocation must persist across new sessions"
    print(f"✓ Revocation persists after session close")

    fresh_session.close()
    print("\n✅ E2E TEST PASSED: Rotation, reutilização, revogação e persistência validadas")
