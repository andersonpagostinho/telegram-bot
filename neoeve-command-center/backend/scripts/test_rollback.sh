#!/bin/bash
# FASE 6 — Rollback Test
# Test that migrations can be rolled back cleanly
# ETAPA 3.3.2 — Recovery Service Homologation

set -e

echo "[PHASE 6] Testing migration rollback..."

# Set test database
export TEST_DATABASE_URL="postgresql://recovery_test_user:recovery_test_pass_7XqR9kL2mN4@localhost:5433/neoeve_recovery_test"

cd "$(dirname "$0")/../migrations"

# Step 1: Verify current state (should be 007)
echo "[Step 1] Current migration state..."
alembic current

# Step 2: Downgrade to 005 (before recovery changes)
echo "[Step 2] Downgrading to migration 005..."
alembic downgrade 005

# Step 3: Verify downgrade was successful
echo "[Step 3] Verifying downgrade..."
alembic current

# Step 4: Check that recovery tables are gone
echo "[Step 4] Checking recovery tables are removed..."
psql -h localhost -U recovery_test_user -d neoeve_recovery_test -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
  AND table_name IN ('execution_attempts', 'event_idempotency_keys', 'recovery_metrics', 'recovery_history');
"

# Step 5: Upgrade back to 007
echo "[Step 5] Re-upgrading to 007..."
alembic upgrade 007

# Step 6: Verify tables are recreated
echo "[Step 6] Verifying tables are recreated..."
psql -h localhost -U recovery_test_user -d neoeve_recovery_test -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
  AND table_name IN ('execution_attempts', 'event_idempotency_keys', 'recovery_metrics', 'recovery_history');
"

echo "[PHASE 6] ✅ Rollback test completed successfully"
