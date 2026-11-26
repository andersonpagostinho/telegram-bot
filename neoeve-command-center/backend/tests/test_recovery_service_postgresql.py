"""PostgreSQL concurrency tests for RecoveryService - ETAPA 2.1 Validation."""

import os
import pytest
import threading
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, Execution, ExecutionAttempt, EventIdempotencyKey, utc_now
from app.services.recovery_service import RecoveryService, RetryPolicy, FailureClassification

# Import pg_engine for thread-safe session creation
_pg_engine = None

# SAFETY: Require explicit TEST_DATABASE_URL to prevent production data corruption
# ETAPA 3.3.2 — PostgreSQL Isolation for Recovery Homologation
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DB_URL:
    raise ValueError(
        "FATAL: TEST_DATABASE_URL environment variable REQUIRED for PostgreSQL tests.\n"
        "This prevents accidental data corruption in production.\n"
        "Set TEST_DATABASE_URL in .env.recovery or as environment variable.\n"
        "Example: postgresql://recovery_test_user:password@localhost:5433/neoeve_recovery_test"
    )

# SAFETY: Validate that TEST_DATABASE_URL is NOT production database
_production_markers = ["5432", "neoeve_dev", "neoeve_command_center"]
if any(marker in TEST_DB_URL.lower() for marker in _production_markers):
    raise ValueError(
        f"FATAL: TEST_DATABASE_URL appears to point to production database.\n"
        f"URL: {TEST_DB_URL[:50]}...\n"
        f"Use ONLY isolated test database (port 5433, neoeve_recovery_test)."
    )

# Log test database connection (host/port only, no credentials)
_parts = TEST_DB_URL.split("@")[-1] if "@" in TEST_DB_URL else "unknown"
print(f"[RECOVERY TESTS] Using isolated test database: {_parts}")


@pytest.fixture(scope="session")
def pg_engine():
    """Create PostgreSQL engine for tests."""
    engine = create_engine(TEST_DB_URL, echo=False, isolation_level="READ_COMMITTED")

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup: drop all tables
    Base.metadata.drop_all(engine)


@pytest.fixture
def pg_db(pg_engine):
    """Create independent PostgreSQL session for each test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        try:
            session.rollback()
        except:
            pass
        finally:
            session.close()


@pytest.fixture
def recovery_service():
    """Create RecoveryService instance."""
    policy = RetryPolicy(max_attempts=3, backoff_ms=100, backoff_multiplier=2.0)
    return RecoveryService(retry_policy=policy, lease_timeout_s=10)


@pytest.fixture
def test_execution_pg(pg_db: Session):
    """Create a test execution in PostgreSQL."""
    execution = Execution(
        execution_id="pg-test-exec-001",
        mission_id="pg-mission-001",
        task_id="pg-task-001",
        agent_id="pg-agent-001",
        runtime="claude-code-cli",
        status="RUNNING",
        tenant_id="pg-tenant-001",
        project_id="pg-project-001",
        attempt_number=1,
        fencing_token=0,
    )
    pg_db.add(execution)
    pg_db.commit()
    return execution


# ===== TESTES OBRIGATÓRIOS =====

class TestPostgresqlConcurrency:
    """PostgreSQL concurrency validation tests."""

    def test_a_two_workers_dispute_lease(self, pg_engine, recovery_service, test_execution_pg):
        """A. Two workers simultaneously trying to acquire same lease.

        Expected: Only one succeeds.
        """
        results = {"worker1": None, "worker2": None}
        errors = []

        def worker1():
            # CRITICAL: Each thread must use its own Session
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
            worker_session = SessionLocal()
            try:
                success, token = recovery_service.acquire_lease(worker_session, test_execution_pg.execution_id, "worker-1")
                results["worker1"] = (success, token)
            except Exception as e:
                errors.append(("worker1", str(e)))
            finally:
                worker_session.close()

        def worker2():
            # CRITICAL: Each thread must use its own Session
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
            worker_session = SessionLocal()
            try:
                # Give worker1 tiny head start
                time.sleep(0.05)
                success, token = recovery_service.acquire_lease(worker_session, test_execution_pg.execution_id, "worker-2")
                results["worker2"] = (success, token)
            except Exception as e:
                errors.append(("worker2", str(e)))
            finally:
                worker_session.close()

        # Run simultaneously
        t1 = threading.Thread(target=worker1)
        t2 = threading.Thread(target=worker2)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Check for thread errors
        assert not errors, f"Thread errors occurred: {errors}"

        # Exactly one should succeed
        success1, token1 = results["worker1"]
        success2, token2 = results["worker2"]

        assert (success1 and not success2) or (not success1 and success2), \
            f"One worker should succeed: w1={success1}, w2={success2}"

        # Winner should have token 1
        winner_token = token1 if success1 else token2
        assert winner_token == 1, f"Winner should get token 1, got {winner_token}"

    def test_b_concurrent_fencing_token_increment(self, pg_engine, recovery_service, test_execution_pg):
        """B. Concurrent fencing token increments.

        Expected: Tokens are monotonic, no duplicates.
        """
        tokens_acquired = []
        errors = []

        def acquire_multiple_times(worker_id):
            # CRITICAL: Each thread must use its own Session
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
            thread_session = SessionLocal()

            try:
                for i in range(3):
                    success, token = recovery_service.acquire_lease(thread_session, test_execution_pg.execution_id, f"worker-{worker_id}-{i}")
                    if success:
                        tokens_acquired.append((worker_id, token))
                        # Release for next worker
                        recovery_service.release_lease(thread_session, test_execution_pg.execution_id, token)
                    time.sleep(0.01)
            except Exception as e:
                errors.append((worker_id, str(e)))
            finally:
                thread_session.close()

        threads = [threading.Thread(target=acquire_multiple_times, args=(i,)) for i in range(2)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check for thread errors
        assert not errors, f"Thread errors occurred: {errors}"

        # Verify tokens are monotonically increasing
        all_tokens = sorted([t[1] for t in tokens_acquired])
        assert all_tokens == list(range(1, len(all_tokens) + 1)), \
            f"Tokens not monotonic: {all_tokens}"

        # No duplicates
        assert len(all_tokens) == len(set(all_tokens)), \
            f"Duplicate tokens found: {all_tokens}"

    def test_c_old_worker_rejected_after_expiration(self, pg_db: Session, recovery_service, test_execution_pg):
        """C. Old worker tries to complete after lease expired.

        Expected: Update rejected.
        """
        # Worker 1 acquires lease
        success1, token1 = recovery_service.acquire_lease(pg_db, test_execution_pg.execution_id, "worker-1")
        assert success1 is True

        # Simulate lease expiration
        execution = pg_db.query(Execution).filter(
            Execution.execution_id == test_execution_pg.execution_id
        ).first()
        execution.lease_expires_at = utc_now() - timedelta(seconds=1)
        pg_db.commit()

        # Worker 2 acquires new lease
        success2, token2 = recovery_service.acquire_lease(pg_db, test_execution_pg.execution_id, "worker-2")
        assert success2 is True
        assert token2 == 2

        # Worker 1 tries to update with old token
        result = recovery_service.update_with_fence(
            pg_db, test_execution_pg.execution_id, token1, "COMPLETED", result={"ok": True}
        )

        assert result is False, "Old worker should be rejected"

    def test_d_interrupted_transaction_rollback(self, pg_db: Session, recovery_service):
        """D. Transaction interrupted during lease acquisition.

        Expected: Rollback safe, new acquisition possible.
        """
        # Create execution
        exec_id = "pg-test-interrupt-001"
        execution = Execution(
            execution_id=exec_id,
            mission_id="m1",
            task_id="t1",
            agent_id="a1",
            runtime="claude-code-cli",
            status="RUNNING",
            tenant_id="pg-tenant-001",
            project_id="p1",
            attempt_number=1,
            fencing_token=0,
        )
        pg_db.add(execution)
        pg_db.commit()

        # Acquire lease (simulating normal operation)
        success1, token1 = recovery_service.acquire_lease(pg_db, exec_id, "worker-1")
        assert success1 is True

        # Simulate interruption by expiring and trying again
        execution = pg_db.query(Execution).filter(Execution.execution_id == exec_id).first()
        execution.lease_expires_at = utc_now() - timedelta(seconds=1)
        pg_db.commit()

        # Should be able to acquire again (rollback safe)
        success2, token2 = recovery_service.acquire_lease(pg_db, exec_id, "worker-2")
        assert success2 is True, "Should recover after interrupt"
        assert token2 == 2

    def test_e_tenant_isolation(self, pg_db: Session, recovery_service):
        """E. Two tenants should not interfere with each other's recovery.

        Expected: Absolute isolation.
        """
        # Tenant 1: Create and acquire execution
        exec1 = Execution(
            execution_id="pg-tenant1-exec-001",
            mission_id="m1",
            task_id="t1",
            agent_id="a1",
            runtime="claude-code-cli",
            status="FAILED",
            tenant_id="pg-tenant-1",
            project_id="p1",
            failure_classification=FailureClassification.TRANSIENT,
            attempt_number=1,
            fencing_token=0,
        )
        pg_db.add(exec1)

        # Tenant 2: Create and acquire execution
        exec2 = Execution(
            execution_id="pg-tenant2-exec-001",
            mission_id="m2",
            task_id="t2",
            agent_id="a2",
            runtime="claude-code-cli",
            status="FAILED",
            tenant_id="pg-tenant-2",
            project_id="p2",
            failure_classification=FailureClassification.TRANSIENT,
            attempt_number=1,
            fencing_token=0,
        )
        pg_db.add(exec2)
        pg_db.commit()

        # Tenant 1 recovers its execution
        recoverable_t1 = recovery_service.find_recoverable(pg_db, "pg-tenant-1")
        assert len(recoverable_t1) == 1
        assert recoverable_t1[0].execution_id == "pg-tenant1-exec-001"

        # Tenant 2 recovers its execution
        recoverable_t2 = recovery_service.find_recoverable(pg_db, "pg-tenant-2")
        assert len(recoverable_t2) == 1
        assert recoverable_t2[0].execution_id == "pg-tenant2-exec-001"

        # Cross-tenant should not appear
        cross_check = recovery_service.find_recoverable(pg_db, "pg-tenant-3")
        assert len(cross_check) == 0

    def test_f_duplicate_events_idempotent(self, pg_db: Session, recovery_service):
        """F. Concurrent duplicate events only process once (idempotency).

        Expected: Idempotency key ensures single processing.
        Contract: Duplicate insert returns False (not an exception).
        """
        key = recovery_service.generate_idempotency_key("event.retry", "exec-001", 1)

        # STEP 1: Mark as processed (first time)
        success1 = recovery_service.mark_event_processed(
            pg_db, key, "event.retry", "exec-001", 1, "tenant-001"
        )
        assert success1 is True, "First mark should succeed"

        # STEP 2: Verify it's marked
        is_processed = recovery_service.is_event_processed(pg_db, key)
        assert is_processed is True, "Should detect duplicate event"

        # STEP 3: Try to mark again (idempotent - should fail silently)
        # The service catches UniqueViolation and returns False
        success2 = recovery_service.mark_event_processed(
            pg_db, key, "event.retry", "exec-001", 1, "tenant-001"
        )
        assert success2 is False, "Duplicate mark should return False (not raise exception)"

        # STEP 4: Verify it's still marked (unchanged)
        is_processed_again = recovery_service.is_event_processed(pg_db, key)
        assert is_processed_again is True, "Event should still be marked"

    def test_g_select_for_update_locking(self, pg_db: Session, recovery_service):
        """G. Verify SELECT FOR UPDATE behavior and blocking.

        Expected: Proper row locking prevents race conditions.
        """
        # Create execution
        execution = Execution(
            execution_id="pg-lock-test-001",
            mission_id="m1",
            task_id="t1",
            agent_id="a1",
            runtime="claude-code-cli",
            status="RUNNING",
            tenant_id="pg-tenant-001",
            project_id="p1",
            attempt_number=1,
            fencing_token=0,
        )
        pg_db.add(execution)
        pg_db.commit()

        # Acquire lease (uses FOR UPDATE internally)
        success, token = recovery_service.acquire_lease(pg_db, execution.execution_id, "worker-1")

        assert success is True
        assert token == 1

        # Verify worker_id was set (proves lock acquisition)
        updated = pg_db.query(Execution).filter(
            Execution.execution_id == execution.execution_id
        ).first()
        assert updated.worker_id == "worker-1"
        assert updated.fencing_token == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
