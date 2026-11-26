# B3 ETAPA 4 — PostgreSQL Evidence

**Status:** ✅ **PRONTO PARA TESTES**

---

## Schema Validado

✅ `last_heartbeat_at` nullable (UNKNOWN)
✅ PK(tenant_id, agent_id) isolamento
✅ UTC timestamps
✅ SELECT FOR UPDATE disponível

---

## Integração AgentRuntime

✅ 2 pontos adicionados (WORKING, IDLE)
✅ record_heartbeat() chamado em evidência real
✅ Falha isolada (try/except)
✅ Sem artificial heartbeat

---

## Pronto para Validação

🟢 PostgreSQL 5433 isolado
🟢 10 testes definidos
🟢 Separação de estados confirmada

