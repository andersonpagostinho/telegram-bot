# B2 — Concurrency Design (ETAPA 2)

**Status:** 📋 **DESIGN DOCUMENT**

## Modelo Atual

**Execuções simultâneas:** Permitidas por design
- `execution_id` permite retry da mesma execução
- Nenhum lock global
- TenantAgentState isolado por `(tenant_id, agent_id)`

## Problema Identificado

**Multiple active executions:**
- Execução 1: agent → WORKING
- Execução 2: agent → WORKING (simultâneo)
- Execução 1 finaliza: agent → IDLE
- Execução 2 finaliza: agent → IDLE/ERROR (OU cai em race condition)

**Risco:** Estado final inconsistente

## Solução Proposta

### Opção A: Execution-scoped state (Recomendado)

Associar estado ao execution_id, não apenas ao agent_id:

```
TenantAgentState: (tenant_id, agent_id) → último estado
ExecutionState: (execution_id) → estado durante execução

Finalização: Consultar execuções ativas restantes
  - Se nenhuma: agent → IDLE
  - Se ativa: manter WORKING
```

**Vantagem:** Suporta múltiplas execuções  
**Custo:** Schema novo (ExecutionState table)

### Opção B: Execution counter

Rastrear número de execuções ativas:
- Incrementar ao iniciar
- Decrementar ao finalizar
- IDLE apenas se counter = 0

**Vantagem:** Simples  
**Risco:** Race condition em increment/decrement

### Opção C: Transaction-scoped state (Mínimo)

Usar transaction + lock em TenantAgentState:

```
BEGIN TRANSACTION
  SELECT state FOR UPDATE (locked)
  UPDATE with new state
COMMIT
```

**Vantagem:** Sem schema novo  
**Risco:** Serialização pode bloquear execuções legítimas

## Recomendação

**Opção A** com schema cauto:

1. Manter TenantAgentState para estado atual do agente
2. Usar Execution.status para rastrear execução individual
3. Consultar execuções ativas ao finalizar
4. Atualizar agent_state apenas se nenhuma ativa

**Schema change:** Nenhum (usar tables existentes)

## Próximo

Aguardar autorização e especificação antes de implementar.

