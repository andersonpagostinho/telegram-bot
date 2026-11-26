# B3 ETAPA 1 — PostgreSQL Evidence

**Status:** ✅ **SCHEMA VALIDADO**

---

## Schema: Execution (Ready for Recovery)

```sql
Columns:
- execution_id (PK)
- tenant_id (indexed, isolamento)
- attempt_number (default=1)
- next_retry_at (DateTime, retry scheduling)
- max_attempts (default=3)
- failure_classification (VARCHAR)
- status (RUNNING, RESERVED, FAILED, etc.)
```

✅ **Suporta retry:** attempt_number, next_retry_at, max_attempts  
✅ **Suporta classificação:** failure_classification  
✅ **Suporta isolamento:** tenant_id indexed  

---

## Schema: ExecutionAttempt (Auditoria)

```sql
Table: execution_attempts
- execution_id (FK)
- attempt_number
- fencing_token (idempotência)
- failure_classification
```

✅ **Auditoria completa de tentativas**  
✅ **Fencing token contra duplicata**  

---

## Schema: RecoveryMetrics (Métricas)

```sql
Table: recovery_metrics
- tenant_id (isolamento)
- metric_type (total_recovered, failed, pending_retry)
- value (counter)
```

✅ **Coleta por tenant**  
✅ **Sem cross-tenant pollution**  

---

## Validação Multi-Tenant (PostgreSQL 5433)

✅ Execution.tenant_id obrigatório  
✅ Queries filtram por tenant_id  
✅ PK(tenant_id, agent_id) garante isolamento  
✅ Nenhuma atualização global  

---

## Status: PostgreSQL Pronto

🟢 Schema suporta ETAPA 1  
🟢 Sem migração necessária  
🟢 Isolamento validado  
🟢 Pronto para RecoveryWorker (ETAPA 2+)

