#!/bin/bash
# FASE 7 — Regression Test Suite
# Validate all 54 existing tests + 7 new PostgreSQL tests
# ETAPA 3.3.2 — Recovery Service Homologation

set -e

echo "============================================================"
echo "[PHASE 7] Regression Test Suite - Full Validation"
echo "============================================================"

# Set test database
export TEST_DATABASE_URL="postgresql://recovery_test_user:recovery_test_pass_7XqR9kL2mN4@localhost:5433/neoeve_recovery_test"

cd "$(dirname "$0")/../../backend"

TOTAL_PASS=0
TOTAL_FAIL=0

# Suites to run
declare -a SUITES=(
    "test_recovery_service.py::TestRecoveryServiceCore (20 tests)"
    "test_recovery_service.py::TestAgentRuntimeIntegration (12 tests)"
    "test_recovery_service.py::TestRecoveryDashboard (17 tests)"
    "test_recovery_service.py::TestPersistence (5 tests)"
    "test_recovery_service_postgresql.py::TestPostgresqlConcurrency (7 tests)"
)

echo ""
echo "Running test suites..."
echo ""

for suite in "${SUITES[@]}"; do
    suite_name=$(echo "$suite" | cut -d' ' -f1)
    suite_count=$(echo "$suite" | grep -o '[0-9]* tests' | cut -d' ' -f1)

    echo "[Running] $suite"

    if python -m pytest $suite_name -v --tb=short 2>&1 | tee /tmp/suite_output.txt; then
        pass_count=$(grep -c "PASSED" /tmp/suite_output.txt || echo 0)
        echo "  ✅ $pass_count/$suite_count tests passed"
        TOTAL_PASS=$((TOTAL_PASS + pass_count))
    else
        fail_count=$(grep -c "FAILED" /tmp/suite_output.txt || echo 0)
        echo "  ❌ $fail_count tests failed"
        TOTAL_FAIL=$((TOTAL_FAIL + fail_count))
    fi
    echo ""
done

echo "============================================================"
echo "[PHASE 7] Regression Results"
echo "============================================================"
echo "Total PASS: $TOTAL_PASS"
echo "Total FAIL: $TOTAL_FAIL"
echo ""

if [ $TOTAL_FAIL -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
    echo "✅ REGRESSION VALIDATION COMPLETE"
    exit 0
else
    echo "❌ FAILURES DETECTED"
    echo "❌ Review failures above"
    exit 1
fi
