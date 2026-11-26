# B3 — Implementation Plan (Preliminar)

**Data:** 2026-11-25  
**Status:** ⏳ **AWAITING AUTHORIZATION**

---

## Escopo Proposto de B3

### ETAPA 1: Recovery Activation
- Integrar RecoveryWorker com AgentRuntime
- Implementar retry policy com tenant isolation
- Usar TenantAgentState para persistir estado de recovery

### ETAPA 2: Failure Classification
- Estender evento de falha com FailureClassification
- Implementar decision tree: retry vs abandon
- Registrar métricas de recovery

### ETAPA 3: Heartbeat Implementation
- Adicionar heartbeat periodic ao Recovery Worker
- Filtrar por tenant_id em todas as queries
- Implementar tenant-scoped notifications

### ETAPA 4: WebSocket Integration
- Estender WebSocketManager para recovery events
- Enviar status updates por tenant
- Implementar subscriber filtering

---

## Contratos Obrigatórios

### Transação de Recovery
```
BEGIN TRANSACTION
  → SELECT FOR UPDATE tenant_agent_state (tenant_id, agent_id)
  → Verificar se em WORKING
  → Se retry válido: marcar tentativa
  → UPDATE tenant_agent_state com novo status
  → Atualizar metrics
COMMIT (ou ROLLBACK se erro)
```

### Isolamento Multi-Tenant
- Todas queries filtram `tenant_id`
- Sem broadcast global
- Nenhuma execução acessa outro tenant

### Idempotência
- Retry duplicado não cria entrada duplicate
- INSERT ON CONFLICT já existe (B2)
- Reutilizar _has_active_execution()

---

## Testes Obrigatórios (10+)

| # | Cenário | Validação |
|---|---------|-----------|
| 1 | Execução falha, retry ativado | Execution status = RUNNING (retry) |
| 2 | Retry sucede | Execution status = COMPLETED |
| 3 | Falha permanente, sem retry | Execution status = FAILED_PERMANENT |
| 4 | Max retries atingido | Execução abandona |
| 5 | Dois tenants, mesma execução ID | Isolamento mantido |
| 6 | Heartbeat atualiza status | TenantAgentState reflete saúde |
| 7 | WebSocket notifica recovery | Cliente recebe evento |
| 8 | Concorrência: dois retries simultaneamente | SELECT FOR UPDATE bloqueia corretamente |
| 9 | Recovery durante shutdown | Idempotência sem duplicata |
| 10 | Métricas de recovery incrementam | Contadores corretos por tenant |

---

## Critérios de Aceite

✅ Nenhuma execução atravessa tenant boundary  
✅ Recovery usa transações com lock (B2)  
✅ Heartbeat não causa broadcast global  
✅ Todos 10+ testes PASS  
✅ Sem regressão em B2  
✅ Nenhuma mudança em produção  

---

## Restrições (como em B2)

- ❌ Não fazer commit/push/deploy
- ❌ Não modificar produção
- ❌ Não executar agentes reais
- ❌ Não alterar WebSocket sem autorização
- ❌ Não criar migrations sem necessidade

---

## Próximo Passo

**Aguardando:**
1. Aprovação de B3_ARCHITECTURE_AUDIT.md
2. Aprovação de B3_IMPLEMENTATION_PLAN.md
3. Autorização para iniciar ETAPA 1

