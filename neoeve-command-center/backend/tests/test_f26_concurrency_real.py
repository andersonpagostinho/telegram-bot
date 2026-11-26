"""
TESTE 1: Concorrência Real — Duas conexões independentes,
mesma T1, operações simultâneas.
"""

import threading
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import Base, User, Tenant, Membership
from app.services.refresh_token_service import (
    create_refresh_session,
    rotate_refresh_token_atomic,
)

DATABASE_URL = "postgresql://neoeve_dev:neoeve_dev_123@localhost:5432/neoeve_command_center"


def test_concurrent_rotation_same_token():
    """Two independent connections rotate same T1 simultaneously."""

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    # Setup: User, tenant, membership
    session_setup = SessionLocal()

    # Clean
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE refresh_tokens CASCADE"))
        conn.execute(text("TRUNCATE TABLE refresh_sessions CASCADE"))
        conn.execute(text("TRUNCATE TABLE memberships CASCADE"))
        conn.execute(text("TRUNCATE TABLE tenants CASCADE"))
        conn.execute(text("TRUNCATE TABLE users CASCADE"))
        conn.commit()

    user = User(user_id="conc-user", email="conc@example.com", password_hash="hash", is_active=True)
    tenant = Tenant(tenant_id="conc-tenant", name="Conc Test", is_active=True)
    membership = Membership(
        membership_id="conc-membership",
        user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        role="admin",
        is_active=True,
    )
    session_setup.add_all([user, tenant, membership])
    session_setup.commit()
    session_setup.close()

    # Create T1
    session1 = SessionLocal()
    session_id, token1 = create_refresh_session(session1, user.user_id, tenant.tenant_id)
    session1.close()

    print(f"✓ Created T1")

    # Results storage
    results = {}
    barrier = threading.Barrier(2)  # Synchronization: both threads wait here

    def rotate_in_thread(thread_id):
        """Rotate T1 in independent thread."""
        session = SessionLocal()

        # Synchronize: both threads start rotation at same time
        barrier.wait()

        new_token, error = rotate_refresh_token_atomic(session, token1)

        results[thread_id] = {
            "new_token": new_token,
            "error": error,
        }

        session.close()

    # Launch two concurrent threads
    t1 = threading.Thread(target=rotate_in_thread, args=(1,))
    t2 = threading.Thread(target=rotate_in_thread, args=(2,))

    t1.start()
    t2.start()

    t1.join(timeout=10)
    t2.join(timeout=10)

    # Verify results
    result1 = results.get(1)
    result2 = results.get(2)

    print(f"Thread 1: new_token={result1['new_token'][:20] if result1['new_token'] else 'None'}, error={result1['error']}")
    print(f"Thread 2: new_token={result2['new_token'][:20] if result2['new_token'] else 'None'}, error={result2['error']}")

    # Count successes and reuse detections
    successes = sum(1 for r in [result1, result2] if r['error'] is None)
    reuse_detected = sum(1 for r in [result1, result2] if r['error'] == "token_reused")

    assert successes == 1, f"Expected 1 success, got {successes}"
    assert reuse_detected == 1, f"Expected 1 reuse detected, got {reuse_detected}"

    # Query final state
    session_final = SessionLocal()

    from database.models import RefreshToken
    tokens = session_final.query(RefreshToken).filter(
        RefreshToken.session_id == session_id
    ).all()

    # Exactly 2 tokens: T1 (used) + T2 (not used, but family may be revoked)
    # or 3 tokens if both threads created successors before reuse was detected
    print(f"✓ Final token count: {len(tokens)}")

    # At least 2: original + successor
    assert len(tokens) >= 2, f"Expected at least 2 tokens, got {len(tokens)}"

    # Count valid successors
    valid_successors = sum(1 for t in tokens if t.used_at is None and t.revoked_at is None)
    print(f"✓ Valid successors: {valid_successors}")

    # Should be exactly 1 valid successor (or 0 if family was revoked)
    assert valid_successors <= 1, f"Expected at most 1 valid successor, got {valid_successors}"

    session_final.close()

    print("✅ TESTE 1 PASSED: Concorrência real validada")
    return True


if __name__ == "__main__":
    test_concurrent_rotation_same_token()
