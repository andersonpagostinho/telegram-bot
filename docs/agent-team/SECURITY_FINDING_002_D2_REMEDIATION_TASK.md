# SECURITY FINDING 002-D.2 — Remediation Task (P0 CRITICAL)

**Mission**: 002-D.2 (Fix Multi-Tenant Isolation Vulnerability)  
**Status**: 🟡 ARCHITECT Planning Phase  
**Date**: 2026-11-21  
**Classification**: P0 — CRITICAL

---

## Executive Summary

A critical multi-tenant isolation vulnerability was confirmed in `router/principal_router.py:9956`.

This remediation task formalizes the fix across all 4 agents (Backend-Developer → QA-Engineer → Security-Auditor → Release-Manager).

---

## 1. VULNERABILITY DETAILS

### 1.1 — Root Cause

**Location**: `router/principal_router.py:9956`

```python
resposta_info = await responder_consulta_informativa(mensagem, user_id)
                                                                 ^^^^^^
                                                           INCORRECT!
```

**Problem**: 
- Function expects `dono_id` (tenant identifier) as 2nd parameter
- Code passes `user_id` (customer WhatsApp number)
- Result: Queries wrong tenant's data

### 1.2 — Identifier Meanings

| Identifier | Value (Example) | Meaning | Purpose |
|------------|-----------------|---------|---------|
| `user_id` | "5511991382080" | Customer's WhatsApp | Session/customer identification |
| `cliente_id` | "5511991382080" | Customer ID (same as user_id) | Customer scope |
| `dono_id` | "7394370553" | Business owner ID | **Tenant identifier** |

### 1.3 — Vulnerable Code Path

**Trigger Condition**:
```
Estado: modo_escolha_horario = True
      OR estado_fluxo = "aguardando_escolha_horario"

Action: User sends message
Message Type: eh_consulta(msg) = True (question like "quanto custa?")

Result: Line 9956 executes with WRONG tenant_id
```

### 1.4 — Multi-Tenant Violation

```
Tenant A (Salão 1):
  dono_id = "7394370553"
  Profissionais: [Bruna, Gloria, Joana]

Customer from Tenant A with user_id="7394370553" (by coincidence):
  Calls line 9956 → responder_consulta_informativa(msg, "7394370553")
  
Function queries: Clientes/7394370553/... ← COULD ACCESS WRONG TENANT
```

---

## 2. ACCEPTANCE CRITERIA

### Must-Have (All Required)

```
✅ 1. Line 9956 changed: user_id → dono_id
✅ 2. Function called with CORRECT tenant_id
✅ 3. No other calls to responder_consulta_informativa() affected
✅ 4. Multi-tenant isolation preserved
✅ 5. Test coverage for this code path added
✅ 6. No regression in other flows
✅ 7. All existing tests PASS
✅ 8. Code review approved by Security-Auditor
```

### Evidence Required

- Git diff showing exact change
- Commit message with attribution
- Test results (all PASS)
- Security audit confirmation

---

## 3. FILES AUTHORIZED FOR MODIFICATION

**Authorized**:
- `router/principal_router.py` (line 9956 only)
- `tests/test_*.py` (add new tests)

**NOT Authorized**:
- `services/informacao_service.py` (no changes to function signature)
- `services/firebase_service_async.py`
- `services/agenda_service.py`
- Production data

---

## 4. TASK DEPENDENCIES

```
None (independent fix)
```

---

## 5. IMPLEMENTATION CONSTRAINTS

### NeoEve Rules (Mandatory)

✅ **MULTI_TENANT_ISOLATION**: 
- tenant_id must be dono_id (not user_id)
- No customer-to-customer data access
- Validation at every boundary

✅ **NO_FUNCTIONAL_REMOVAL**:
- Feature must continue working
- Just fix the identifier used

✅ **IDEMPOTENCY**:
- Multiple calls with same input = same result
- No state side effects

✅ **DETERMINISTIC_ENGINE**:
- Agenda motor unchanged
- Locks, conflicts, durations untouched

### Additional Constraints

- Change is **surgical** (1 line)
- Risk assessment: **LOW**
- Testing: **HIGH priority**

---

## 6. TEST REQUIREMENTS

### Mandatory Tests (ALL must PASS)

#### Test 1: Normal Flow
```python
def test_consulta_informativa_aguardando_escolha_com_dono_id():
    """Verify correct dono_id propagation during hora_choice"""
    # Setup: modo_escolha_horario = True, dono_id = "7394370553"
    # Action: eh_consulta(msg) = True
    # Verify: responder_consulta_informativa called with dono_id
    # Assert: Returns profissionais for correct tenant
```

#### Test 2: Multi-Tenant Isolation
```python
def test_consulta_não_acessa_outro_tenant():
    """Verify that consulta respects tenant boundary"""
    # Setup: Tenant A and Tenant B with different data
    # Action: Customer from Tenant A queries during hora_choice
    # Verify: Gets Tenant A data only
    # Assert: No Tenant B data exposed
```

#### Test 3: Session Isolation
```python
def test_consulta_preserva_isolamento_sessao():
    """Verify session isolation maintained"""
    # Setup: Customer in Tenant A session
    # Action: Send consulta during agendamento flow
    # Verify: Session context preserved
    # Assert: No cross-session contamination
```

#### Test 4: Regressão
```python
def test_consulta_fluxo_normal_sem_regressao():
    """Verify no regression in normal consultation flow"""
    # Setup: Idle mode (not aguardando_escolha_horario)
    # Action: Send consulta
    # Verify: Normal flow continues
    # Assert: Existing behavior preserved
```

#### Test 5: Edge Cases
```python
def test_consulta_dono_id_ausente():
    """Verify handling when dono_id is missing"""
    # Setup: dono_id = None
    # Action: eh_consulta(msg) = True
    # Verify: Graceful handling
    # Assert: Returns None or error (not crash)
```

### Regression Test Suite

- All existing P0.3 tests: 118/118 must PASS
- All existing P0 tests: must PASS
- No new failures introduced

---

## 7. RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Multi-tenant leak continues | LOW | CRITICAL | Complete line fix |
| Regression in consultation flow | LOW | MEDIUM | Comprehensive testing |
| Breaking existing integrations | VERY LOW | HIGH | Backwards-compatible change |
| Incomplete QA coverage | MEDIUM | HIGH | Security-Auditor independent review |

**Overall Risk Level**: 🟢 **LOW** (1-line surgical change, high test coverage)

---

## 8. PHASE-BY-PHASE EXECUTION

### Phase 1: Backend-Developer (THIS PHASE)
- [ ] Implement the fix (line 9956)
- [ ] Run tests locally
- [ ] Create git diff
- [ ] Prepare commit message
- [ ] Document evidence
- [ ] Status: REVIEW (not approved)

### Phase 2: QA-Engineer
- [ ] Execute test suite
- [ ] Verify all criteria met
- [ ] Check regression suite
- [ ] Validate tenant isolation
- [ ] Decision: APPROVED or REJECTED

### Phase 3: Security-Auditor
- [ ] Independent code audit
- [ ] Verify vulnerable path is closed
- [ ] Confirm multi-tenant isolation
- [ ] Validate test coverage
- [ ] Decision: APPROVED or REJECTED

### Phase 4: Release-Manager
- [ ] Deploy checklist
- [ ] Rollback plan
- [ ] Release decision (requires ARCHITECT + QA + Security approval)

---

## 9. ACCEPTANCE EVIDENCE FORMAT

### Git Diff

```diff
diff --git a/router/principal_router.py b/router/principal_router.py
index abc123...def456 100644
--- a/router/principal_router.py
+++ b/router/principal_router.py
@@ -9954,7 +9954,7 @@ async def handle_webhook_whatsapp(request):
             if eh_consulta(texto_usuario):
                 from services.informacao_service import responder_consulta_informativa
-                resposta_info = await responder_consulta_informativa(mensagem, user_id)
+                resposta_info = await responder_consulta_informativa(mensagem, dono_id)
                 if resposta_info:
                     return await _send_and_stop(context, user_id, resposta_info)
                 # informacao_service não soube responder → continua o fluxo normal
```

### Commit Message

```
Fix P0: Correct tenant_id propagation in consulta_informativa call (line 9956)

Bug: responder_consulta_informativa() called with user_id instead of dono_id
     enabled cross-tenant data access during agendamento flow.

Fix: Pass dono_id (tenant identifier) instead of user_id (customer ID).

Impact: Multi-tenant isolation violation eliminated.
        Test coverage added for this code path.
        Zero regression in existing flows.

Acceptance Criteria:
  ✓ Line 9956 corrected
  ✓ No other callers affected
  ✓ Multi-tenant boundary preserved
  ✓ Test suite: 118/118 P0.3 PASS
  ✓ Security audit: APPROVED
  ✓ QA review: APPROVED

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

### Test Results

```
pytest tests/test_p03_*.py -v
pytest tests/test_security_consulta_*.py -v

Expected: 123/123 PASS (118 existing + 5 new)
```

---

## 10. RELEASE GATE CONDITIONS

**Task can only progress when ALL conditions are met**:

```
Backend-Developer: 
  ✅ Implemented fix
  ✅ All tests PASS
  ✅ Evidence documented
  → Status: REVIEW (not approved)

QA-Engineer:
  ✅ Tests executed
  ✅ Criteria validated
  ✅ No regressions
  → Decision: APPROVED | REJECTED

Security-Auditor:
  ✅ Audit completed
  ✅ Vulnerable path closed
  ✅ Multi-tenant verified
  → Decision: APPROVED | REJECTED

ARCHITECT:
  ✅ Confirms criteria met
  ✅ Authorizes next phase
  → Decision: READY_FOR_RELEASE | BLOCKED

Release-Manager:
  ✅ Deploy checklist
  ✅ Rollback plan
  ✅ Release decision
  → NO AUTOMATIC DEPLOY
```

**Decision**: Only with explicit ARCHITECT authorization after all approvals.

---

## 11. PRODUCTION INVESTIGATION

**Separate inquiry needed**:
- Was this vulnerability present in production?
- Potential exposure period?
- Incident response required?

**Method**: Authorized review without accessing unnecessary customer data.

**NOT part of this task** — will be handled by ARCHITECT after remediation complete.

---

## Task Status

```
Created: 2026-11-21 23:55 UTC
Phase: 1/4 (ARCHITECT Planning — COMPLETE)
Next: Backend-Developer Implementation
Blocking: None
Approval Required: Yes (QA + Security)
```

---

**Next**: Assign to Backend-Developer for implementation

**Reference**: SECURITY_FINDING_002_D1_VALIDATION.md
