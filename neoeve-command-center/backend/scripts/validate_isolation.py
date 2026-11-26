#!/usr/bin/env python3
"""
Validate that recovery test environment is properly isolated from production.
ETAPA 3.3.2 — Recovery Service Homologation Safety Check

Usage:
    python validate_isolation.py
"""

import os
import sys
from urllib.parse import urlparse

def validate_isolation():
    """Validate production vs test database isolation."""

    print("=" * 70)
    print("[ISOLATION CHECK] Recovery Service PostgreSQL Environment Validation")
    print("=" * 70)

    # 1. Check production DATABASE_URL
    prod_url = os.getenv("DATABASE_URL", "")
    print(f"\n[1] Production DATABASE_URL:")
    if prod_url:
        parsed = urlparse(prod_url)
        print(f"    Host: {parsed.hostname}")
        print(f"    Port: {parsed.port or 5432}")
        print(f"    DB: {parsed.path.lstrip('/')}")
        print(f"    User: {parsed.username}")
        prod_host = parsed.hostname
        prod_port = parsed.port or 5432
        prod_db = parsed.path.lstrip('/')
    else:
        print("    ⚠️  NOT SET (uses connection.py default)")
        prod_host = "localhost"
        prod_port = 5432
        prod_db = "neoeve_command_center"

    # 2. Check test TEST_DATABASE_URL
    test_url = os.getenv("TEST_DATABASE_URL", "")
    print(f"\n[2] Test TEST_DATABASE_URL:")
    if test_url:
        parsed = urlparse(test_url)
        print(f"    Host: {parsed.hostname}")
        print(f"    Port: {parsed.port or 5432}")
        print(f"    DB: {parsed.path.lstrip('/')}")
        print(f"    User: {parsed.username}")
        test_host = parsed.hostname
        test_port = parsed.port or 5432
        test_db = parsed.path.lstrip('/')
    else:
        print("    ✅ NOT SET (conftest.py uses SQLite in-memory by default)")
        test_host = "sqlite-memory"
        test_port = 0
        test_db = ":memory:"

    # 3. Validation
    print(f"\n[3] Isolation Validation:")

    errors = []

    # Check 3a: Ports must be different (if both PostgreSQL)
    if test_url and "sqlite" not in test_url:
        if test_port == prod_port:
            errors.append(f"❌ Same port ({test_port}) for prod and test")
        elif test_port == 5433 and prod_port == 5432:
            print(f"    ✅ Ports isolated: test=5433, prod=5432")
        else:
            print(f"    ✅ Ports different: test={test_port}, prod={prod_port}")
    else:
        print(f"    ✅ Test uses SQLite (completely isolated from PostgreSQL)")

    # Check 3b: Databases must be different
    if test_url and prod_url:
        if test_db == prod_db:
            errors.append(f"❌ Same database name: {test_db}")
        else:
            print(f"    ✅ Databases different: test={test_db}, prod={prod_db}")

    # Check 3c: TEST_DATABASE_URL cannot reference production markers
    if test_url:
        prod_markers = ["5432", "neoeve_dev", "neoeve_command_center"]
        found_prod_markers = [m for m in prod_markers if m in test_url.lower()]
        if found_prod_markers:
            errors.append(f"❌ TEST_DATABASE_URL contains production markers: {found_prod_markers}")
        else:
            print(f"    ✅ TEST_DATABASE_URL clean (no production markers)")

    # 4. Result
    print(f"\n[4] Result:")
    if errors:
        print(f"    ❌ ISOLATION FAILED:")
        for err in errors:
            print(f"       {err}")
        return False
    else:
        print(f"    ✅ ISOLATION VALIDATED")
        print(f"    ✅ Safe to run recovery service tests")
        return True

if __name__ == "__main__":
    success = validate_isolation()
    sys.exit(0 if success else 1)
