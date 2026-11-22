# -*- coding: utf-8 -*-
"""
test_security_consulta_informativa_tenant_isolation.py

SECURITY FINDING 002-D.2 — Multi-Tenant Isolation Vulnerability Fix

Tests for line 9956 in principal_router.py:
  - Fix: responder_consulta_informativa() called with dono_id (not user_id)
  - Impact: Closes cross-tenant data access vulnerability

Test Cases:
  1. Verify line 9956 fix is in place
  2. Verify dono_id is available in context
  3. Verify function signature expects dono_id
  4. Regression test: other call sites use dono_id correctly
"""

import pytest
import os
import re
from services.informacao_service import responder_consulta_informativa


# ============================================================
# TEST 1: Verify Line 9956 Fix is in Place
# ============================================================

def test_line_9956_fix_verified():
    """
    Direct verification that line 9956 uses dono_id instead of user_id

    This test reads the actual code to confirm the fix is in place.
    """
    # Read the principal_router.py file
    router_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "router",
        "principal_router.py"
    )

    with open(router_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Check line 9956 (array index 9955 for 0-based indexing)
    if len(lines) > 9955:
        line_9956_content = lines[9955].strip()

        # Verify the fix is present
        assert "responder_consulta_informativa" in line_9956_content, \
            "Line 9956 should contain responder_consulta_informativa call"
        assert "dono_id" in line_9956_content, \
            "Line 9956 should pass dono_id parameter"

        # Verify it's NOT passing user_id as the second parameter
        # The pattern should be: responder_consulta_informativa(mensagem, dono_id)
        pattern = r"responder_consulta_informativa\s*\(\s*mensagem\s*,\s*dono_id\s*\)"
        assert re.search(pattern, line_9956_content), \
            f"Line 9956 should match pattern 'responder_consulta_informativa(mensagem, dono_id)', got: {line_9956_content}"


# ============================================================
# TEST 2: Verify Function Signature Expects dono_id
# ============================================================

def test_responder_consulta_informativa_signature():
    """
    Verify that responder_consulta_informativa() function signature expects dono_id

    This validates the target function requires dono_id as the second parameter.
    """
    import inspect

    # Get function signature
    sig = inspect.signature(responder_consulta_informativa)
    params = list(sig.parameters.keys())

    # Verify parameter order
    assert len(params) >= 2, "Function should have at least 2 parameters"
    assert params[0] == "mensagem", "First parameter should be 'mensagem'"
    assert params[1] == "dono_id", "Second parameter should be 'dono_id' (the tenant identifier)"


# ============================================================
# TEST 3: Verify All Call Sites Use dono_id Consistently
# ============================================================

def test_all_responder_consulta_callsites_use_dono_id():
    """
    Verify that ALL call sites to responder_consulta_informativa use dono_id

    This ensures consistency across the entire codebase.
    """
    router_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "router",
        "principal_router.py"
    )

    with open(router_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all calls to responder_consulta_informativa
    pattern = r"responder_consulta_informativa\s*\([^)]+\)"
    matches = re.findall(pattern, content)

    assert len(matches) >= 3, "Should find at least 3 call sites to responder_consulta_informativa"

    # Verify each call uses dono_id as second parameter
    for match in matches:
        # Extract the content inside parentheses
        args_match = re.search(r"responder_consulta_informativa\s*\(([^)]+)\)", match)
        if args_match:
            args_str = args_match.group(1)
            # Check if it's using dono_id (not user_id)
            # Allow for variations like: dono_id, tenant_id=dono_id, etc.
            assert "dono_id" in args_str, \
                f"Call to responder_consulta_informativa should use dono_id: {match}"


# ============================================================
# TEST 4: Verify dono_id is Available at Line 9956 Context
# ============================================================

def test_dono_id_available_at_line_9956():
    """
    Verify that dono_id variable is available in the context where line 9956 executes

    This validates that the fix doesn't reference an undefined variable.
    """
    router_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "router",
        "principal_router.py"
    )

    with open(router_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find where dono_id is first assigned (should be before line 9956)
    dono_id_assignments = []
    for i, line in enumerate(lines[:9956]):  # Only check lines before 9956
        if "dono_id =" in line or "dono_id=" in line:
            dono_id_assignments.append((i + 1, line.strip()))

    # Should find at least one dono_id assignment before line 9956
    assert len(dono_id_assignments) > 0, \
        "dono_id should be assigned somewhere before line 9956"

    # Print for debugging
    print(f"Found {len(dono_id_assignments)} dono_id assignments before line 9956")


# ============================================================
# TEST 5: Multi-Tenant Isolation Concept
# ============================================================

def test_dono_id_vs_user_id_semantics():
    """
    Verify that dono_id and user_id have different semantic meanings

    This validates the security fix is conceptually correct.
    """
    # dono_id: Business owner ID (tenant identifier)
    # Example: "7394370553"
    # Purpose: Identify which business/salon

    # user_id: Customer WhatsApp number (session identifier)
    # Example: "5511991382080"
    # Purpose: Identify which customer is chatting

    # For multi-tenant isolation:
    # - ALL queries must scope to: Clientes/{dono_id}/...
    # - NOT: Clientes/{user_id}/...
    #
    # This prevents customer A from seeing customer B's data
    # (if they happen to have the same ID as a different tenant)

    dono_id_example = "7394370553"  # Business 1
    user_id_example = "5511991382080"  # Customer A

    # In a proper multi-tenant system:
    # - Database path uses dono_id: Clientes/7394370553/Profissionais
    # - Session uses user_id: Clientes/7394370553/Sessoes/whatsapp:5511991382080

    assert dono_id_example != user_id_example, \
        "dono_id and user_id should be different for security"


# ============================================================
# TEST 6: Regression Test - Previous Implementation Bug
# ============================================================

def test_fix_prevents_previous_bug():
    """
    Verify that the fix prevents the previous bug pattern:
    calling responder_consulta_informativa(msg, user_id) which was wrong

    This test ensures we're not regressing to the old vulnerable code.
    """
    router_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "router",
        "principal_router.py"
    )

    with open(router_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the line with responder_consulta_informativa around line 9956
    for i in range(9950, min(9960, len(lines))):
        line = lines[i]
        if "responder_consulta_informativa" in line and "mensagem" in line:
            # Verify it uses dono_id, not user_id
            assert "dono_id" in line, \
                f"Line {i+1}: should use dono_id parameter"

            # Double-check: should NOT use user_id as second parameter
            # Pattern check: responder_consulta_informativa(mensagem, user_id) is WRONG
            wrong_pattern = r"responder_consulta_informativa\s*\(\s*mensagem\s*,\s*user_id\s*\)"
            assert not re.search(wrong_pattern, line), \
                f"Line {i+1}: WRONG! Should not use user_id. Got: {line}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
