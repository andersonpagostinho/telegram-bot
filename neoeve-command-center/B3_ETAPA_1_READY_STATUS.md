# B3 ETAPA 1 — Ready Status

**Data:** 2026-11-25  
**Status:** ✅ **PRONTO PARA IMPLEMENTAÇÃO**

---

## Schema Analysis — Resultado

### ✅ Nenhuma Migração Necessária

**Execution model (linha 253) já suporta recovery:**
- `attempt_number` (Integer, default=1)
- `next_retry_at` (DateTime)
- `max_attempts` (Integer, default=3)

**ExecutionAttempt table (linha 329):**
- Auditoria de cada tentativa de retry
- Suporta fencing_token para idempotência

**RecoveryMetrics table (linha 482):**
- Coleta de métricas por tenant
- Tipos: total_recovered, successful, failed, pending_retry, active_lease

**RecoveryHistory table (linha 509):**
- Auditoria completa de recuperações

### TenantAgentState (pronto para B3)
- `status` → pode ser "RECOVERING" ou estender valores
- `last_event_at` → rastreia último evento
- `last_error` → armazena erro último
- Sem mudança necessária para ETAPA 1

---

## Componentes Prontos (B1-B2)

| Componente | Status | Para ETAPA 1 |
|-----------|--------|-------------|
| RecoveryService | ✅ EXISTE | Usar retry policy |
| RecoveryWorker | ✅ EXISTE | Integrar com AgentRuntime |
| RecoveryMetricsService | ✅ EXISTE | Registrar métricas |
| SELECT FOR UPDATE | ✅ IMPLEMENTADO | Usar em recovery transação |
| Multi-tenant isolation | ✅ IMPLEMENTADO | PK(tenant_id, agent_id) |
| _has_active_execution() | ✅ IMPLEMENTADO | Reutilizar em retry decision |

---

## Arquivos a Modificar (ETAPA 1)

### 1. agent_runtime.py

**Adicionar:**
- Importar `RecoveryWorker`
- Importar `FailureClassification` de RecoveryService
- Método `_should_retry(exception, attempt_count)` → determina se retry válido
- Lógica em `execute_task()` catch block para ativar recovery
- Integração com `recovery_metrics_service` para registrar tentativas

**Exemplo de fluxo:**
```python
except Exception as e:
    # Classificar falha
    failure_class = RecoveryService.classify_failure(e)
    
    if failure_class.is_transient and execution.attempt_number < max_attempts:
        # Marcar para retry
        execution.next_retry_at = utc_now() + backoff_duration
        execution.status = "RESERVED"  # Aguardando retry
        
        # Enqueuer recovery worker
        recovery_worker = RecoveryWorker(...)
        recovery_worker.enqueue(...)
        
        # Registrar métrica
        metrics_service.record_pending_retry(tenant_id, agent_id)
```

### 2. recovery_worker.py

**Adicionar:**
- Integração com TenantAgentStateService.update_with_transaction_lock()
- Verificar se tenant_id/agent_id ainda válidos
- Atualizar TenantAgentState durante recovery
- Usar SELECT FOR UPDATE para atomicidade

### 3. Sem mudança necessária:
- database/models.py (schema já pronto)
- migrations/ (nenhuma migração)

---

## Contrato de Integração ETAPA 1

**Ordem de execução:**

1. **Falha detectada em AgentRuntime**
   - exception caught em execute_task()

2. **Classificar falha**
   - Usar RecoveryService.classify_failure()
   - Determinar: transient vs permanent

3. **Se transient + tentativas restantes:**
   - Marcar Execution como "RESERVED"
   - Calcular backoff (exponential)
   - Enqueuer RecoveryWorker
   - UPDATE TenantAgentState (keep WORKING state)

4. **Se permanent:**
   - Marcar Execution como "FAILED_PERMANENT"
   - UPDATE TenantAgentState → ERROR
   - NÃO enqueuer recovery

5. **RecoveryWorker executa (separado):**
   - SELECT FOR UPDATE TenantAgentState
   - Verificar ainda válida
   - Executar retry
   - UPDATE estado final

---

## Riscos Mitigados por B2

✅ Race condition → SELECT FOR UPDATE (B2)  
✅ Cross-tenant recovery → PK(tenant_id, agent_id) + WHERE tenant_id (B2)  
✅ Idempotência → INSERT ON CONFLICT (B2)  
✅ Consultar execuções ativas → _has_active_execution() (B2)  

---

## Testes Esperados (subset de 10+)

| # | Teste | ETAPA 1? |
|---|-------|---------|
| 1 | Execução falha, retry ativado | ✅ SIM |
| 2 | Retry sucede | ✅ SIM |
| 3 | Falha permanente, sem retry | ✅ SIM |
| 4 | Max retries atingido | ✅ SIM |
| 5 | Isolamento multi-tenant (retry) | ✅ SIM |
| 6+ | Heartbeat/WebSocket/métricas | ❌ NÃO (ETAPA 2+) |

---

## Critérios de Aceite ETAPA 1

✅ Falhas transientes acionam retry  
✅ Falhas permanentes não retry  
✅ RecoveryWorker integrado com SELECT FOR UPDATE  
✅ TenantAgentState atualizado atomicamente  
✅ Isolamento multi-tenant mantido  
✅ 5+ testes PASS  
✅ Sem regressão em B2  

---

## Status Final

🟢 **PRONTO PARA IMPLEMENTAÇÃO**

**Próximo:**
1. Aprovar proposta de integração
2. Iniciar implementação de agent_runtime.py
3. Integrar recovery_worker.py
4. Executar testes ETAPA 1
5. Gerar B3_ETAPA_1_REPORT.md

