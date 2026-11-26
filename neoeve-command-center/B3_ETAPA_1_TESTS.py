#!/usr/bin/env python3
"""B3 ETAPA 1 Tests: Recovery activation with tenant isolation."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Execution, utc_now
from app.services.recovery_service import RecoveryService, RetryPolicy, FailureClassification

# PostgreSQL 5433 connection
DATABASE_URL = "postgresql+psycopg://neoeve_dev:neoeve_dev_123@127.0.0.1:5433/neoeve_etapa_a"

@pytest.fixture
def db():
    """Create test database session."""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def recovery_service():
    """Create RecoveryService with retry policy."""
    return RecoveryService(
        retry_policy=RetryPolicy(max_attempts=3, backoff_ms=100, backoff_multiplier=2.0),
        lease_timeout_s=300
    )

# TEST 1: Transient failure classification
def test_classify_transient_failure(recovery_service):
    """Test that timeout errors are classified as TRANSIENT."""
    result = recovery_service.classify_failure("connection timeout after 30s")
    assert result == FailureClassification.TRANSIENT, f"Expected TRANSIENT, got {result}"
    print("✅ TEST 1 PASS: Transient failure classified correctly")

# TEST 2: Permanent failure classification
def test_classify_permanent_failure(recovery_service):
    """Test that permission errors are classified as PERMANENT."""
    result = recovery_service.classify_failure("permission denied: access to resource blocked")
    assert result == FailureClassification.PERMANENT, f"Expected PERMANENT, got {result}"
    print("✅ TEST 2 PASS: Permanent failure classified correctly")

# TEST 3: Unknown failure classification
def test_classify_unknown_failure(recovery_service):
    """Test that unknown errors are classified as UNKNOWN."""
    result = recovery_service.classify_failure("random internal error")
    assert result == FailureClassification.UNKNOWN, f"Expected UNKNOWN, got {result}"
    print("✅ TEST 3 PASS: Unknown failure classified correctly")

# TEST 4: Retry policy - should retry transient
def test_should_retry_transient(recovery_service):
    """Test that transient failures with attempts left should retry."""
    result = recovery_service.retry_policy.should_retry(
        FailureClassification.TRANSIENT, attempt=1
    )
    assert result is True, "Expected should_retry=True for transient with attempt=1"
    print("✅ TEST 4 PASS: Transient failure can be retried")

# TEST 5: Retry policy - should not retry permanent
def test_should_not_retry_permanent(recovery_service):
    """Test that permanent failures never retry."""
    result = recovery_service.retry_policy.should_retry(
        FailureClassification.PERMANENT, attempt=1
    )
    assert result is False, "Expected should_retry=False for permanent"
    print("✅ TEST 5 PASS: Permanent failure not retried")

# TEST 6: Retry policy - max attempts
def test_max_attempts_exceeded(recovery_service):
    """Test that retries stop at max_attempts."""
    result = recovery_service.retry_policy.should_retry(
        FailureClassification.TRANSIENT, attempt=3
    )
    assert result is False, f"Expected should_retry=False for attempt=3 (max=3), got {result}"
    print("✅ TEST 6 PASS: Max attempts respected")

# TEST 7: Backoff calculation
def test_exponential_backoff(recovery_service):
    """Test exponential backoff calculation."""
    delay_1 = recovery_service.retry_policy.calculate_delay(attempt=1)
    delay_2 = recovery_service.retry_policy.calculate_delay(attempt=2)
    delay_3 = recovery_service.retry_policy.calculate_delay(attempt=3)

    # Should be: 100ms, 200ms, 400ms
    assert delay_1 == 100, f"Expected 100ms, got {delay_1}ms"
    assert delay_2 == 200, f"Expected 200ms, got {delay_2}ms"
    assert delay_3 == 400, f"Expected 400ms, got {delay_3}ms"
    assert delay_2 > delay_1, "Backoff should increase"
    assert delay_3 > delay_2, "Backoff should increase"
    print("✅ TEST 7 PASS: Exponential backoff calculated correctly")

# TEST 8: Backoff max cap
def test_backoff_max_cap(recovery_service):
    """Test that backoff respects max cap."""
    # Max backoff is 60000ms, so attempts beyond threshold should cap
    delay_10 = recovery_service.retry_policy.calculate_delay(attempt=10)
    assert delay_10 <= 60000, f"Delay {delay_10}ms exceeds max {recovery_service.retry_policy.max_backoff_ms}ms"
    print("✅ TEST 8 PASS: Backoff max cap respected")

# TEST 9: Multi-pattern transient
def test_multi_pattern_transient(recovery_service):
    """Test that multiple transient patterns are recognized."""
    patterns = [
        "network unreachable after 5s",
        "connection refused by server",
        "broken pipe error",
        "unable to connect to database"
    ]
    for pattern in patterns:
        result = recovery_service.classify_failure(pattern)
        assert result == FailureClassification.TRANSIENT, f"Pattern '{pattern}' not classified as TRANSIENT"
    print("✅ TEST 9 PASS: Multiple transient patterns recognized")

# TEST 10: Multi-pattern permanent
def test_multi_pattern_permanent(recovery_service):
    """Test that multiple permanent patterns are recognized."""
    patterns = [
        "permission denied for operation",
        "access denied: insufficient rights",
        "command not found in whitelist",
        "resource not found (404)"
    ]
    for pattern in patterns:
        result = recovery_service.classify_failure(pattern)
        assert result == FailureClassification.PERMANENT, f"Pattern '{pattern}' not classified as PERMANENT"
    print("✅ TEST 10 PASS: Multiple permanent patterns recognized")

if __name__ == "__main__":
    recovery_service = RecoveryService(
        retry_policy=RetryPolicy(max_attempts=3, backoff_ms=100, backoff_multiplier=2.0),
        lease_timeout_s=300
    )

    print("\n" + "="*60)
    print("B3 ETAPA 1 TESTS: Recovery Classification & Retry Policy")
    print("="*60 + "\n")

    test_classify_transient_failure(recovery_service)
    test_classify_permanent_failure(recovery_service)
    test_classify_unknown_failure(recovery_service)
    test_should_retry_transient(recovery_service)
    test_should_not_retry_permanent(recovery_service)
    test_max_attempts_exceeded(recovery_service)
    test_exponential_backoff(recovery_service)
    test_backoff_max_cap(recovery_service)
    test_multi_pattern_transient(recovery_service)
    test_multi_pattern_permanent(recovery_service)

    print("\n" + "="*60)
    print("✅ ALL 10 TESTS PASSED")
    print("="*60 + "\n")

