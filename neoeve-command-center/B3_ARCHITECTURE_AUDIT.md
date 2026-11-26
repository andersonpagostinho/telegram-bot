# B3 — Architecture Audit

**Data:** 2026-11-25  
**Status:** ⏳ **ESCOPO PRELIMINAR**

---

## Componentes Identificados

### Recovery Layer (Potencial B3)

| Componente | Localização | Função |
|-----------|-------------|--------|
| **RecoveryService** | `services/recovery_service.py` | Retry policy, lease management, failure classification |
| **RecoveryWorker** | `services/recovery_worker.py` | Background worker para recovery |
| **RecoveryMetricsService** | `services/recovery_metrics_service.py` | Métricas de recuperação |

### Integração Existente

- **AgentRuntime** integra `RecoveryService` (linhas 34-37)
- **WebSocketManager** menciona recovery/websocket

---

## Dependências Identificadas

### Dependências Críticas para B3

1. **AgentRuntime** (já em B2)
   - Usa RecoveryService para retry policy
   - Passa tenant_id obrigatório
   - SELECT FOR UPDATE em transações

2. **AgentRegistry** (B1 finalizado)
   - update_operational_state() integrado
   - update_connectivity_state() integrado

3. **TenantAgentStateService** (B2 finalizado)
   - update_with_transaction_lock() com INSERT ON CONFLICT
   - Multi-tenant isolation com PK(tenant_id, agent_id)

4. **Execution Model**
   - Status transitions: RUNNING → COMPLETED/FAILED
   - Suporta retry, attempt tracking

---

## Escopo Preliminar de B3

### Hipótese de Escopo

**B3 pode envolver:**

1. **Recovery Worker Activation**
   - Integrar RecoveryWorker com AgentRuntime
   - Lógica de retry com tenant isolation
   - Heartbeat implementation

2. **Failure Classification**
   - Classificar falhas (transient vs permanent)
   - Retentar vs abandone
   - Métricas de recuperação

3. **WebSocket Integration**
   - Notificações de recovery
   - Status updates em tempo real
   - Multi-tenant event streaming

4. **State Persistence**
   - Salvar estado de recovery em TenantAgentState
   - Isolamento por tenant
   - Consistência com Execution model

---

## Riscos Preliminares

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Race condition em retry | 🔴 | Use transação com SELECT FOR UPDATE (B2 já pronto) |
| Heartbeat cross-tenant | 🔴 | Filtrar por tenant_id em todas queries |
| Recovery loop infinito | 🟡 | Implementar max attempts + exponential backoff |
| WebSocket broadcast global | 🟡 | Enviar eventos por tenant |

---

## Dependências em B2

✅ **B2 fornece:**
- Transações atômicas (INSERT ON CONFLICT + SELECT FOR UPDATE)
- Isolamento multi-tenant (PK composta)
- Consulta de execuções ativas (_has_active_execution)
- Integração em AgentRuntime

**B3 pode construir sobre B2 com segurança.**

---

## Próximo Passo

Aguardando autorização para detalhar B3_IMPLEMENTATION_PLAN.md com:
- Etapas específicas
- Contratos de interface
- Testes de concorrência e recovery
- Critérios de aceite

