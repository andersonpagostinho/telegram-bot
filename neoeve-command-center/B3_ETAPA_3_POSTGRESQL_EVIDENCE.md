# B3 ETAPA 3 — PostgreSQL Evidence

**Status:** ✅ **SCHEMA PRONTO**

---

## Migration Applied (5433)

```sql
ALTER TABLE tenant_agent_states
ADD COLUMN last_heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();

CREATE INDEX idx_tenant_agent_state_heartbeat
ON tenant_agent_states(tenant_id, last_heartbeat_at)
WHERE connectivity_status != 'ONLINE';
```

---

## Validação

✅ Isolamento: PK(tenant_id, agent_id)  
✅ Timestamps: UTC only  
✅ Índice: Eficiente para STALE/OFFLINE  
✅ Concorrência: SELECT FOR UPDATE ready  

---

## Pronto para Testes

🟢 PostgreSQL 5433 (isolado)  
🟢 Schema validado  
🟢 Índices criados  

