# B1 — Agent Registry Tests (Planned)

**Data:** 2026-11-24  
**Status:** 📋 PLANO DE TESTES (ANTES DA IMPLEMENTAÇÃO)  
**Escopo:** Validação de AgentRegistry com isolamento multi-tenant  

---

## Testes Estáticos (1-7) — Sem DB

**Mantêm 100% das funcionalidades existentes.**

### Test 1: Seven Agents Registered
```python
def test_seven_agents_registered(self):
    """All seven agents in registry."""
    assert len(AgentRegistry.AGENTS) == 7
    expected = ["architect", "backend_developer", "debugger", "qa_engineer", 
                "security_auditor", "release_manager", "openai_validator"]
    for name in expected:
        assert name in AgentRegistry.AGENTS
    print("✓ Test 1: Seven agents registered")
```
**Resultado esperado:** ✅ PASS (sem mudança)

---

### Test 2: Agent Roles Correctly Assigned
```python
def test_agent_roles(self):
    """Agent roles correctly assigned."""
    assert AgentRegistry.AGENTS["architect"]["role"] == AgentRole.ARCHITECT
    assert AgentRegistry.AGENTS["backend_developer"]["role"] == AgentRole.BACKEND_DEVELOPER
    assert AgentRegistry.AGENTS["openai_validator"]["role"] == AgentRole.OPENAI_VALIDATOR
    print("✓ Test 2: Agent roles")
```
**Resultado esperado:** ✅ PASS (sem mudança)

---

### Test 3: Architect Permissions (WRITE, EXECUTE)
```python
def test_permission_matrix_architect(self):
    """Architect has WRITE and EXECUTE permissions."""
    agent_id = AgentRegistry.AGENTS["architect"]["agent_id"]
    assert AgentRegistry.has_permission(agent_id, Permission.WRITE)
    assert AgentRegistry.has_permission(agent_id, Permission.EXECUTE)
    print("✓ Test 3: Architect permissions")
```
**Resultado esperado:** ✅ PASS (sem mudança)

---

### Test 4: QA Engineer Denied WRITE
```python
def test_permission_deny_qa_write(self):
    """QA Engineer cannot have WRITE permission."""
    agent_id = AgentRegistry.AGENTS["qa_engineer"]["agent_id"]
    assert not AgentRegistry.has_permission(agent_id, Permission.WRITE)
    print("✓ Test 4: QA denied WRITE")
```
**Resultado esperado:** ✅ PASS (sem mudança)

---

### Test 5: Security Auditor Can Veto
```python
def test_security_auditor_veto(self):
    """Security Auditor can veto."""
    agent_id = AgentRegistry.AGENTS["security_auditor"]["agent_id"]
    assert AgentRegistry.can_veto(agent_id)
    print("✓ Test 5: Security Auditor veto")
```
**Resultado esperado:** ✅ PASS (sem mudança)

---

### Test 6: OpenAI Validator Read-Only
```python
def test_openai_validator_read_only(self):
    """OpenAI Validator is read-only."""
    agent_id = AgentRegistry.AGENTS["openai_validator"]["agent_id"]
    assert AgentRegistry.is_read_only(agent_id)
    assert not AgentRegistry.has_permission(agent_id, Permission.WRITE)
    print("✓ Test 6: OpenAI Validator read-only")
```
**Resultado esperado:** ✅ PASS (sem mudança)

---

### Test 7: Capabilities Available
```python
def test_capabilities(self):
    """Agent capabilities are available."""
    architect_id = AgentRegistry.AGENTS["architect"]["agent_id"]
    caps = AgentRegistry.get_capabilities(architect_id)
    assert "plan" in caps
    assert "decompose" in caps
    print("✓ Test 7: Capabilities")
```
**Resultado esperado:** ✅ PASS (sem mudança)

---

## Testes de Isolamento (8-10) — Com PostgreSQL 5433

**NOVO:** Validam isolamento entre Tenant A e Tenant B.

### Setup Pré-Teste
```python
@pytest.fixture
def db_isolated():
    """PostgreSQL 5433 isolated database."""
    # Usar porta 5433 (neoeve_etapa_a)
    # Limpar tabelas: agents, tenant_agent_states
    # Seed: 7 agentes em Agent table
    yield db
    # Teardown: limpar estados
```

---

### Test 8: Isolate Agent State by Tenant
```python
def test_isolamento_tenant_a_operacional_tenant_b_idle(self, db_isolated):
    """
    Agent ONLINE in Tenant A, OFFLINE in Tenant B.
    
    Cenário:
    1. Inicializar agent-architect em Tenant A como IDLE
    2. Mudar para WORKING em Tenant A
    3. Inicializar agent-architect em Tenant B como IDLE
    4. Verificar: Tenant A = WORKING, Tenant B = IDLE
    5. Mudar para BLOCKED em Tenant B
    6. Verificar: Tenant A = WORKING (SEM MUDANÇA)
    """
    # Setup
    service = TenantAgentStateService()
    tenant_a = "tenant-123"
    tenant_b = "tenant-456"
    agent_id = "agent-architect"
    
    # Tenant A: IDLE → WORKING
    service.get_or_create(db_isolated, tenant_a, agent_id)
    service.update_operational_state(db_isolated, tenant_a, agent_id, "WORKING")
    state_a1 = service.get_state(db_isolated, tenant_a, agent_id)
    assert state_a1.status == "WORKING"
    
    # Tenant B: IDLE (default)
    service.get_or_create(db_isolated, tenant_b, agent_id)
    state_b1 = service.get_state(db_isolated, tenant_b, agent_id)
    assert state_b1.status == "IDLE"
    
    # Tenant B: IDLE → BLOCKED
    service.update_operational_state(db_isolated, tenant_b, agent_id, "BLOCKED")
    state_b2 = service.get_state(db_isolated, tenant_b, agent_id)
    assert state_b2.status == "BLOCKED"
    
    # Tenant A: WORKING (SEM MUDANÇA)
    state_a2 = service.get_state(db_isolated, tenant_a, agent_id)
    assert state_a2.status == "WORKING"
    
    print("✓ Test 8: Tenant isolation confirmed")
```
**Resultado esperado:** ✅ PASS (isolamento por tenant_id funciona)

---

### Test 9: Update Tenant A Does Not Affect Tenant B
```python
def test_atualizacao_tenant_a_nao_afeta_tenant_b(self, db_isolated):
    """
    Update connectivity in Tenant A without changing Tenant B.
    
    Cenário:
    1. Ambos: ONLINE (inicial)
    2. Tenant A: ONLINE → STALE
    3. Tenant B: ONLINE (SEM MUDANÇA)
    """
    service = TenantAgentStateService()
    tenant_a = "tenant-123"
    tenant_b = "tenant-456"
    agent_id = "agent-debugger"
    
    # Initialize both
    service.get_or_create(db_isolated, tenant_a, agent_id)
    service.get_or_create(db_isolated, tenant_b, agent_id)
    
    # Both ONLINE initially
    for tid in [tenant_a, tenant_b]:
        service.update_connectivity_state(db_isolated, tid, agent_id, "ONLINE")
    
    # Change Tenant A
    service.update_connectivity_state(db_isolated, tenant_a, agent_id, "STALE")
    
    # Verify isolation
    state_a = service.get_state(db_isolated, tenant_a, agent_id)
    state_b = service.get_state(db_isolated, tenant_b, agent_id)
    
    assert state_a.connectivity_status == "STALE"
    assert state_b.connectivity_status == "ONLINE"
    
    print("✓ Test 9: Tenant A update does not affect Tenant B")
```
**Resultado esperado:** ✅ PASS (isolamento mantido)

---

### Test 10: Same Agent in Different Tenants, Different States
```python
def test_mesmo_agente_em_tenants_diferentes(self, db_isolated):
    """
    Same agent (agent-backend) has different states in different tenants.
    
    Cenário:
    1. Tenant A: agent-backend = WORKING (Implementando)
    2. Tenant B: agent-backend = IDLE (Aguardando)
    3. Tenant C: agent-backend = ERROR (Erro ocorreu)
    4. Verificar: Todos isolados e diferentes
    """
    service = TenantAgentStateService()
    agent_id = "agent-backend"
    tenants = ["tenant-a", "tenant-b", "tenant-c"]
    states = ["WORKING", "IDLE", "ERROR"]
    
    # Create and set different states
    for tid, state in zip(tenants, states):
        service.get_or_create(db_isolated, tid, agent_id)
        service.update_operational_state(db_isolated, tid, agent_id, state)
    
    # Verify all different
    for tid, expected_state in zip(tenants, states):
        actual_state = service.get_state(db_isolated, tid, agent_id)
        assert actual_state.status == expected_state, \
            f"{tid}: expected {expected_state}, got {actual_state.status}"
    
    print("✓ Test 10: Same agent, different tenants, different states")
```
**Resultado esperado:** ✅ PASS (isolamento completo funciona)

---

## Critério de Aceitação B1

**PASSAR 100% dos testes (1-10) para conclusão B1:**

| Teste | Tipo | Status | Requisito |
|-------|------|--------|-----------|
| 1-7 | Estático | ✅ PASS (sem mudança) | Regressão zero |
| 8 | DB (isolamento) | ✅ PASS | tenant_id obrigatório |
| 9 | DB (isolamento) | ✅ PASS | Sem cross-tenant |
| 10 | DB (isolamento) | ✅ PASS | Estados independentes |

**Falha em qualquer teste = Parar B1, revisar, reportar.**

---

## Documentação de Falha B1 (se ocorrer)

Caso falhe, criar: `AGENT_CONNECTIVITY_PHASE1_1_B1_FAILURE.md` com:
- Qual teste falhou
- Erro exato
- Causa raiz investigada
- Recomendação de ação

Aguardar revisão e autorização antes de prosseguir.

