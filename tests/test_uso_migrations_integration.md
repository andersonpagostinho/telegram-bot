# ETAPA 4 — USO MIGRATIONS INTEGRATION TESTS
## Validation that 4 uses work with bridge

This file documents the test cases that would validate all 4 migrations work correctly.

## Test Suite Structure

### Suite 1: USO 1 (PRE-CHECK) - validar_profissional_com_duracao()

**Purpose**: Validate that PRE-CHECK can determine if booking is possible AND get duration

**Test Cases**:

1. **test_uso1_precheck_happy_path**
   - Professional exists
   - Service in professional's portfolio
   - Duration configured
   - Expected: valido=True, duracao returned

2. **test_uso1_precheck_prof_not_found**
   - Professional doesn't exist in Atores
   - Expected: valido=False, motivo="profissional_inexistente"

3. **test_uso1_precheck_duracao_not_configured**
   - Professional exists
   - Service exists for professional
   - Duration NOT configured
   - Expected: valido=False, motivo="duracao_nao_configurada"

4. **test_uso1_precheck_tenant_isolation**
   - Same professional name in different tenants
   - Tenant 1 can do corte (60min), Tenant 2 cannot
   - Expected: Different results per tenant

---

### Suite 2: USO 2 (ALTERNATIVAS) - Alternative professional durations

**Purpose**: Validate that each alternative professional gets their correct duration

**Test Cases**:

1. **test_uso2_alternatives_different_durations**
   - Primary: Bruna (60min, unavailable)
   - Alt 1: Gloria (60min, available)
   - Alt 2: Joana (50min, available)
   - Expected: Alternatives returned with their specific durations

2. **test_uso2_alternatives_missing_duration_excluded**
   - Alternative suggested but duration not configured
   - Expected: Not included in suggestions

3. **test_uso2_alternatives_same_duration**
   - Multiple alternatives with same duration
   - Expected: All returned with correct duration

4. **test_uso2_alternatives_tenant_isolation**
   - Different tenants, same alternative names
   - Expected: Each tenant gets correct duration

---

### Suite 3: USO 3 (LOOP COM CACHE) - Operation-scoped caching

**Purpose**: Validate that cache prevents repeated lookups without spans requests

**Test Cases**:

1. **test_uso3_cache_single_operation**
   - Loop through 10 time slots, 3 services
   - First loop: 3 bridge calls (one per service)
   - Cache populated
   - Expected: Total 3 calls, not 30

2. **test_uso3_cache_scoped_to_operation**
   - Operation 1: Cache built (3 calls)
   - Operation 2: Fresh cache (3 calls)
   - Expected: New operation gets fresh cache, no sharing

3. **test_uso3_cache_no_tenant_cross_contamination**
   - Operation in Tenant 1, cache built
   - Operation in Tenant 2, fresh cache
   - Expected: No cross-tenant cache sharing

4. **test_uso3_cache_complex_services**
   - Manicure + pedicure + corte
   - Different durations
   - Expected: Each cached with correct value

---

### Suite 4: USO 4 (CONFIRMAÇÃO) - Confirmation with bridge

**Purpose**: Validate that confirmation uses bridge duration before fallback

**Test Cases**:

1. **test_uso4_confirmacao_bridge_over_estimate**
   - Service not in catalog
   - Bridge returns 40min
   - Estimate would be 30min
   - Expected: Confirmation uses 40min (from bridge)

2. **test_uso4_confirmacao_catalog_priority**
   - Service in catalog: 50min
   - Bridge returns: 40min
   - Estimate would be: 30min
   - Expected: Uses 50min (catalog priority)

3. **test_uso4_confirmacao_reject_if_unknown**
   - Bridge returns: None
   - Catalog doesn't have it
   - Expected: Confirmation not allowed, user notified

4. **test_uso4_confirmacao_tenant_isolation**
   - Same service, different tenants
   - Tenant 1: 60min, Tenant 2: 75min
   - Expected: Each gets correct duration

---

## Regression Test Coverage

### Core Infrastructure (existing, must not break)
- 7 core wrapper tests
- 7 bridge tests
- 4 integration examples
- = **18 tests** all passing ✅

### New Integration Tests (for migrations)
- Suite 1: 4 tests
- Suite 2: 4 tests
- Suite 3: 4 tests
- Suite 4: 4 tests
- = **16 new tests**

### Multi-Service Validation
- test_loop_manicure_pedicure: 2 services, different durations
- test_loop_corte_escova_hidratacao: 3 services
- Expected: Each service gets correct duration per professional

### Multi-Tenant Regression
- test_regression_tenant_a_basic_booking
- test_regression_tenant_b_alternative_available
- test_regression_tenant_a_vs_b_isolation
- Expected: All pass, no cross-contamination

### Conversation Flow Regression
- Test full scheduling flow with bridge
- Test confirmation flow with bridge
- Test alternative suggestion with bridge
- Expected: Existing conversations still work

---

## Success Criteria

**All migrations approved when**:
- ✅ 18 infrastructure tests passing
- ✅ 16 new integration tests passing
- ✅ 0 regressions in existing flow tests
- ✅ Multi-tenant isolation confirmed
- ✅ Real Firestore tested for USO 1
- ✅ Diffs minimal and focused per use
- ✅ None handling explicit throughout
- ✅ No data migration required
- ✅ No schema changes
- ✅ All 4 uses integrated

---

## Running These Tests

```bash
pytest tests/test_duracao_service.py -v          # 7 tests
pytest tests/test_duracao_bridge.py -v           # 7 tests
pytest tests/test_duracao_service_integration_examples.py -v  # 4 tests
pytest tests/test_uso_migrations.py -v          # 16 tests (new)
pytest tests/test_regression_full_flow.py -v    # Regression
```

**Expected**: 34+ tests, all PASS ✅

