# B1 — Runtime Contract Adaptation Report

**Data:** 2026-11-24  
**Status:** 📋 PLANO TÉCNICO (ANTES DA IMPLEMENTAÇÃO)  
**Escopo:** Adaptar AgentRegistry e AgentRuntime com tenant_id obrigatório  

---

## Achados Críticos

### 1. TenantAgentStateService — JÁ EXISTE ✅

**Arquivo:** `backend/app/services/tenant_agent_state_service.py`

**Status:** Completo e pronto
- ✅ get_or_create(tenant_id, agent_id)
- ✅ update_status(tenant_id, agent_id, status)
- ✅ update_connectivity_status(tenant_id, agent_id, status)
- ✅ get_by_tenant_and_agent(tenant_id, agent_id)
- ✅ Isolamento PK composta

**Ação:** Usar "as is", adicionar import em AgentRegistry

---

### 2. AgentRuntime — TENANT_ID DISPONÍVEL ✅

**Arquivo:** `backend/app/services/agent_runtime.py`

**Status:** Já recebe tenant_id
- ✅ Linha 45: `def execute_task(..., tenant_id: str, ...)`
- ✅ Validação: linha 74-76 (verifica tenant_id não nulo)
- ✅ Logging: linha 78 (mostra tenant_id)

**Ação:** Propagar tenant_id nas 7 chamadas a AgentRegistry

---

### 3. AgentRegistry — ADAPTAR MÉTODOS

**Status:** Sem tenant_id (precisa de adaptação)

**Métodos a alterar:**
1. `update_operational_state()` — linha 214-228
2. `update_connectivity_state()` — linha 231-245

**Ação:** Adicionar tenant_id como parâmetro obrigatório

---

## Plano de Implementação

### FASE 1: Adaptar AgentRegistry

**Novo contrato:**
```python
@classmethod
def update_operational_state(
    cls,
    db: Session,
    tenant_id: str,          # ← NOVO (obrigatório)
    agent_id: str,
    state: OperationalState,
) -> bool:
    """Update agent operational state for a specific tenant."""
    if not tenant_id or not agent_id:
        logger.error(f"Missing tenant_id or agent_id")
        return False
    
    service = TenantAgentStateService(db)
    return service.update_status(tenant_id, agent_id, state.value)

@classmethod
def update_connectivity_state(
    cls,
    db: Session,
    tenant_id: str,          # ← NOVO (obrigatório)
    agent_id: str,
    state: ConnectivityState,
) -> bool:
    """Update agent connectivity state for a specific tenant."""
    if not tenant_id or not agent_id:
        logger.error(f"Missing tenant_id or agent_id")
        return False
    
    service = TenantAgentStateService(db)
    return service.update_connectivity_status(tenant_id, agent_id, state.value)
```

**Mudanças adicionais:**
- Adicionar `from app.services.tenant_agent_state_service import TenantAgentStateService`
- Remover atualização direta em Agent (não mais `agent.status = ...`)
- Manter permissões/capabilities (não sofrem isolamento)

---

### FASE 2: Adaptar AgentRuntime

**7 Chamadas a adaptar:**

**Linha 188:**
```python
# ANTES:
AgentRegistry.update_operational_state(db, agent_id, OperationalState.WORKING)

# DEPOIS:
AgentRegistry.update_operational_state(db, tenant_id, agent_id, OperationalState.WORKING)
```

**Linha 234, 349, 351, 370, 427, 440:** Mesmo padrão

**Adicionar validação:**
```python
if not tenant_id or not agent_id:
    logger.error(f"Cannot update state: missing tenant_id or agent_id")
    raise ValueError("tenant_id and agent_id required for state update")
```

**Sem mudanças em:**
- Lógica de execução
- Adapters
- Recovery service
- Retry policies
- Terminal access

---

## Teste de Contrato

### Teste 1: Chamada SEM tenant_id FALHA

```python
def test_update_state_without_tenant_fails():
    """Calling update_operational_state without tenant_id must fail."""
    try:
        # Esta assinatura NÃO deve mais funcionar:
        AgentRegistry.update_operational_state(db, agent_id, state)
        assert False, "Should have failed"
    except TypeError:  # Falta parâmetro
        assert True, "Correctly requires tenant_id"
```

**Resultado esperado:** ✅ TypeError (assinatura mudou)

---

### Teste 2: Chamada COM tenant_id FUNCIONA

```python
def test_update_state_with_tenant_works():
    """With tenant_id, update works."""
    result = AgentRegistry.update_operational_state(
        db, tenant_id, agent_id, OperationalState.WORKING
    )
    assert result == True
```

**Resultado esperado:** ✅ PASS (isolado por tenant)

---

### Teste 3: AgentRuntime Propaga tenant_id

```python
def test_agent_runtime_propagates_tenant_id():
    """AgentRuntime passes tenant_id to AgentRegistry."""
    success, _, _ = runtime.execute_task(
        task_id="task-1",
        agent_id="agent-architect",
        task_description="Test",
        mission_id="mission-1",
        tenant_id="tenant-123",    # ← Deve ser propagado
        project_id="proj-1",
        workspace_path="/tmp",
    )
    # Task completes successfully (tenant isolation works)
    assert success
```

**Resultado esperado:** ✅ PASS (AgentRuntime propaga corretamente)

---

## Riscos & Mitigação

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| AgentRuntime chamadas antigas quebram | ALTA | TypeError na assinatura (falha óbvia) |
| Consumidores externos quebram | MÉDIA | Auditoria de dependências verificará |
| Cross-tenant contamination | BAIXA | Testes 8-10 validarão isolamento |
| Regressão em lógica | BAIXA | Sem alteração em adapters/recovery |

---

## Checklist de Implementação

- [ ] Adicionar import TenantAgentStateService em AgentRegistry
- [ ] Adaptar update_operational_state() com tenant_id
- [ ] Adaptar update_connectivity_state() com tenant_id
- [ ] Adicionar validação de tenant_id não-nulo
- [ ] Adaptar 7 chamadas em AgentRuntime
- [ ] Adicionar validação em AgentRuntime (error explícito se sem tenant_id)
- [ ] Remover atualização direta em Agent.status
- [ ] Executar testes 1-10
- [ ] Auditoria: verificar sem chamadas antigas
- [ ] Auditoria: confirmar isolamento Tenant A/B
- [ ] Regressão: verificar nenhum consumidor quebrado

---

## Próximas Ações

**Autorizado:** ✅ Implementar B1

**Sequência:**
1. Adaptar AgentRegistry (20 minutos)
2. Adaptar AgentRuntime (10 minutos)
3. Executar testes 1-10 (15 minutos)
4. Auditoria final (10 minutos)
5. Relatório de testes

**Tempo estimado:** 55 minutos

