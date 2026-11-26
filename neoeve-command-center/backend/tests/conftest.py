"""
Pytest configuration and fixtures for Command Center tests.
Ensures test isolation with proper database cleanup and independent sessions.
"""

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, Tenant, ProjectionCheckpoint


# Use SQLite in-memory for tests (creates fresh schema each session)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(scope="session")
def engine():
    """Create SQLAlchemy engine for test database."""
    # Use appropriate isolation level based on database
    if "sqlite" in TEST_DATABASE_URL:
        isolation_level = "SERIALIZABLE"
        connect_args = {"check_same_thread": False}
    else:
        isolation_level = "READ COMMITTED"
        connect_args = {}
    return create_engine(TEST_DATABASE_URL, echo=False, isolation_level=isolation_level, connect_args=connect_args)


@pytest.fixture(scope="session")
def setup_database(engine):
    """Create all tables before tests."""
    Base.metadata.create_all(engine)
    yield
    # Keep tables for inspection, don't drop


def cleanup_all_tables(engine):
    """Clean all test tables in correct dependency order."""
    with engine.connect() as conn:
        # Order matters: foreign keys first, then parent tables
        tables = [
            "projection_checkpoints",  # Must clean before tenants (FK dependency)
            "event_idempotency_keys", "execution_attempts", "executions",
            "refresh_tokens", "refresh_sessions", "invite_tokens",
            "memberships",  # Must clean before tenants/users
            "tenants", "users"
        ]
        for table in tables:
            try:
                conn.execute(text(f"DELETE FROM {table}"))
            except:
                pass
        conn.commit()


@pytest.fixture(autouse=True)
def cleanup_before_each_test(engine, setup_database):
    """Auto cleanup BEFORE each test for complete isolation."""
    cleanup_all_tables(engine)
    yield
    cleanup_all_tables(engine)


@pytest.fixture
def db(engine) -> Session:
    """
    Create independent database session for each test.
    Session uses READ COMMITTED isolation for realistic PostgreSQL concurrency.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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


# Alias for backward compatibility with existing tests
@pytest.fixture
def db_session(db) -> Session:
    """Alias for 'db' fixture for tests that use db_session name."""
    return db


@pytest.fixture
def test_tenant_id() -> str:
    """Provide a valid test tenant ID for FK constraint compliance."""
    return "test_tenant_01"


@pytest.fixture
def test_tenant(db_session, test_tenant_id):
    """
    Create a valid test tenant before tests run.
    Ensures FK constraint on projection_checkpoints.tenant_id is satisfied.
    """
    tenant = Tenant(tenant_id=test_tenant_id, name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def inject_test_session(engine, monkeypatch):
    """
    Inject test database SessionLocal into production modules.

    For Recovery integration tests: ensures Scheduler uses PostgreSQL test database
    (5433/neoeve_recovery_test) instead of production database (5432/neoeve_command_center).

    This fixture monkeypatches the SessionLocal factory in database.connection
    and app.core.scheduler to use the test engine.
    """
    # Create a SessionLocal using the test engine
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    # Monkeypatch the global SessionLocal in connection.py
    import database.connection
    original_session_local = database.connection.SessionLocal
    database.connection.SessionLocal = TestSessionLocal

    # Also patch the reference in scheduler.py (if already imported)
    try:
        from app.core import scheduler
        scheduler.PGSessionLocal = TestSessionLocal
    except (ImportError, AttributeError):
        pass

    yield TestSessionLocal

    # Restore original
    database.connection.SessionLocal = original_session_local


@pytest.fixture
def test_tenants(db_session) -> dict:
    """
    Create multiple test tenants for multi-tenant isolation tests.
    Returns dict of tenant_id -> Tenant object.
    """
    tenant_ids = ["tenant_a", "tenant_b", "tenant_c"]
    tenants = {}
    for tid in tenant_ids:
        tenant = Tenant(tenant_id=tid, name=f"Test Tenant {tid}")
        db_session.add(tenant)
        tenants[tid] = tenant
    db_session.commit()
    return tenants


@pytest.fixture
def test_checkpoint(db_session, test_tenant_id, test_tenant):
    """
    Create a valid ProjectionCheckpoint for tests.
    Ensures checkpoint exists before test logic runs.
    """
    checkpoint = ProjectionCheckpoint(
        tenant_id=test_tenant_id,
        consumer_id="test_consumer"
    )
    db_session.add(checkpoint)
    db_session.commit()
    return checkpoint
