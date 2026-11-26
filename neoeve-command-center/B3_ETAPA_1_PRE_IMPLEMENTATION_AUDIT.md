# B3 ETAPA 1 — Pre-Implementation Audit

**Data:** 2026-11-25  
**Status:** 🔍 **DIAGNÓSTICO COMPLETO**

---

## Escopo Exato de ETAPA 1: Recovery Activation

### Objetivo
Integrar RecoveryWorker com AgentRuntime para implementar retry policy com tenant isolation, usando TenantAgentState para persistir recovery state.

### 3 Componentes Críticos

| Componente | Localização | Ação |
|-----------|------------|------|
| **RecoveryWorker** | `services/recovery_worker.py` | Ativar integração |
| **AgentRuntime** | `services/agent_runtime.py` | Adicionar retry logic |
| **TenantAgentState** | `database/models.py` + `services/tenant_agent_state_service.py` | Persistir recovery state |

---

## Arquivos Envolvidos

### READ (diagnóstico)
1. ✅ recovery_service.py — entender retry policy, lease management
2. ✅ recovery_worker.py — entender estrutura
3. ✅ recovery_metrics_service.py — entender coleta de métricas
4. ✅ agent_runtime.py — entender pontos de integração
5. ✅ tenant_agent_state_service.py — entender persistência

### MODIFY (implementação)
1. ⏳ agent_runtime.py — integrar RecoveryWorker
2. ⏳ recovery_worker.py — ativar com tenant isolation
3. ⏳ Possibly: database/models.py — adicionar recovery fields se necessário
4. ⏳ Possibly: migrations — schema changes

---

## Dependências Confirmadas

| Dependência | Status | Fornecedor |
|-----------|--------|-----------|
| SELECT FOR UPDATE | ✅ PRONTO | B2 (TenantAgentStateService) |
| Multi-tenant isolation (PK) | ✅ PRONTO | B2 (TenantAgentState) |
| _has_active_execution() | ✅ PRONTO | B2 (AgentRuntime) |
| RetryPolicy | ✅ EXISTE | RecoveryService (B1) |
| RecoveryMetrics | ✅ EXISTE | RecoveryMetricsService (B1) |

---

## Verificações Pré-Implementação

### Schema Changes?

**Necessário verificar:**
- TenantAgentState: existe campo para retry_count?
- Execution: existe campo para retry_attempt?
- Necessário adicionar recovery_state column?

**Ação:** Inspecionar database/models.py

### Contrato de Integração

```python
# Esperado em AgentRuntime:
recovery_worker = RecoveryWorker(
    db=db,
    tenant_id=tenant_id,
    agent_id=agent_id,
    execution_id=execution_id,
    retry_policy=retry_policy  # De RecoveryService
)

# Fluxo:
1. Execução falha → exception caught
2. Classificar falha (transient vs permanent)
3. Se retry válido:
   - Marcar tentativa em Execution
   - Atualizar TenantAgentState com recovery_state
   - Enqueuer RecoveryWorker
4. Se falha permanente:
   - Marcar FAILED_PERMANENT
   - Nenhum retry
```

---

## Riscos Identificados

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Race condition em retry duplicado | 🔴 | Use SELECT FOR UPDATE (B2 pronto) |
| Cross-tenant recovery | 🔴 | Filtrar tenant_id em TODAS queries |
| Recovery loop infinito | 🟡 | Max attempts + exponential backoff (RecoveryService) |
| Deadlock com locked execution | 🟡 | Timeout no SELECT FOR UPDATE |

---

## Critério de Pré-Implementação

Antes de modificar código:

- [ ] Schema inspection completo
- [ ] Contrato de integração validado
- [ ] Nenhuma mudança de schema necessária OU migração proposta
- [ ] Risco assessment completo

---

## Próximo Passo

**Autorizado a:**
1. Inspecionar recovery_service.py, recovery_worker.py
2. Inspecionar database/models.py para schema
3. Propor integração exata
4. Identificar se migração necessária

**Não autorizado a:**
- Modificar código
- Criar migrations
- Ativar RecoveryWorker automaticamente

