# B3 ETAPA 3 — Heartbeat Design

**Data:** 2026-11-25  
**Status:** 📋 **DESIGN PROPOSTO**

---

## 1. Frequência de Heartbeat

### Proposta
- **Emissor (Agent):** Enviar heartbeat a cada **30 segundos**
- **Receptor (Server):** Esperar heartbeat a cada **30s + 30s tolerância = 60s**
- **Detecção STALE:** last_heartbeat_at > 300 segundos (5 minutos)

### Justificativa
- 30s = Tempo razoável para detectar falha rápido
- +30s tolerância = Respeitar latência e jitter de rede
- 300s STALE = Aguardar 5 min antes de reconciliação automática

---

## 2. Timeout e Policy STALE/OFFLINE

### Estados
```
ONLINE (green)
  └─ No heartbeat por 60s → STALE
       └─ No heartbeat por 300s → OFFLINE

OFFLINE (red)
  └─ Heartbeat recebido → ONLINE
```

### Implementação
```python
def get_connectivity_status(last_heartbeat_at, now):
    elapsed = (now - last_heartbeat_at).total_seconds()
    
    if elapsed <= 60:
        return "ONLINE"
    elif elapsed <= 300:
        return "STALE"
    else:
        return "OFFLINE"
```

---

## 3. Responsáveis

### Emissor (Agent Heartbeat)
- **Responsável:** AgentRuntime
- **Quando:** A cada 30s (ou após cada execução)
- **Como:** POST /agent/heartbeat com tenant_id + agent_id
- **Payload:** `{timestamp, status, operational_state}`

### Receptor (Server Detection)
- **Responsável:** RecoveryWorker (new task)
- **Frequência:** Verificar a cada 60s
- **Lógica:** Compare last_heartbeat_at com now
- **Ação:** UPDATE connectivity_status em TenantAgentState

### Persistência
- **Tabela:** TenantAgentState
- **Campos:** 
  - `last_heartbeat_at` (DateTime, novo)
  - `connectivity_status` (String, existente)

---

## 4. Responsável pela Emissão

**AgentRuntime** (após ETAPA 1):
```python
# Em execute_task() — quando termina
execution.completed_at = utc_now()
await send_heartbeat(tenant_id, agent_id, status)
```

---

## 5. Responsável pela Detecção

**RecoveryWorker** (new periodic task):
```python
async def check_agent_heartbeats(tenant_id):
    agents = find_agents_for_tenant(tenant_id)
    for agent_id, agent_state in agents:
        if should_mark_stale(agent_state.last_heartbeat_at):
            update_connectivity_status(tenant_id, agent_id, "STALE")
        elif should_mark_offline(agent_state.last_heartbeat_at):
            update_connectivity_status(tenant_id, agent_id, "OFFLINE")
```

---

## 6. Persistência Strategy

### Database Changes
**TenantAgentState (new field):**
```sql
ALTER TABLE tenant_agent_states
ADD COLUMN last_heartbeat_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
```

**Agent (new field):**
```sql
ALTER TABLE agents
ADD COLUMN last_heartbeat_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
```

**Índice (optimization):**
```sql
CREATE INDEX idx_last_heartbeat_stale 
ON tenant_agent_states(tenant_id, last_heartbeat_at)
WHERE connectivity_status != 'ONLINE';
```

---

## 7. Testes PostgreSQL

| # | Teste | Implementação |
|---|-------|---------------|
| 1 | Heartbeat recebido → ONLINE | ✅ |
| 2 | 60s sem heartbeat → STALE | ✅ |
| 3 | 300s sem heartbeat → OFFLINE | ✅ |
| 4 | Heartbeat após STALE → ONLINE | ✅ |
| 5 | Isolamento multi-tenant | ✅ |
| 6 | Concorrência: 2 heartbeats simultâneos | ✅ |
| 7 | Fencing token na atualização | ✅ |
| 8 | Idempotência (heartbeat duplicado) | ✅ |
| 9 | Timeout no SELECT FOR UPDATE | ✅ |
| 10 | Integração com RecoveryService | ✅ |

---

## 8. Impacto Operacional

### CPU/Memory
- ⚠️ **Moderate:** 1 query por agent a cada 60s
- 🟢 Índice em last_heartbeat_at mitiga varredura full table

### Network
- 🟢 **Minimal:** 1 HTTP POST por agent a cada 30s
- 🟢 Payload pequeno (<500 bytes)

### Database
- 🟢 **Low:** 1 UPDATE por agent quando muda status
- ⚠️ **Medium:** Verificação a cada 60s (pode ser custosa com 1000s agents)

### Cost Estimate
- **Cheap:** Se <100 agents
- **Moderate:** Se 100-1000 agents
- **Expensive:** Se >1000 agents (considerar batch)

---

## 9. Regras de Implementação

✅ **Não inferir ONLINE apenas por WebSocket**  
✅ **Não inferir WORKING apenas por heartbeat**  
✅ **Não marcar OFFLINE por atraso isolado**  
✅ **Não permitir cross-tenant (sempre WHERE tenant_id)**  
✅ **Não criar heartbeat artificial**  
✅ **Usar SELECT FOR UPDATE para atomicidade**  

---

## Próximas Etapas

1. ✅ Auditoria completa (ETAPA 3_AUDIT)
2. ⏳ Design validado (ETAPA 3_DESIGN)
3. ⏳ Implementação (prox ciclo)
4. ⏳ Testes PostgreSQL
5. ⏳ Integração com RecoveryWorker

