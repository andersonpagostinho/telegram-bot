# B3 ETAPA 3 — Heartbeat Audit

**Data:** 2026-11-25  
**Status:** 🔍 **AUDITORIA COMPLETA**

---

## 1. Estado Atual de connectivity_status

### Localização
- **Agent model** (linha 155): `connectivity_status = "UNKNOWN"` (ONLINE, OFFLINE, STALE, UNKNOWN)
- **TenantAgentState** (linha 179): `connectivity_status = "UNKNOWN"` (mesmo enum)

### Uso Atual
```
agent_runtime.py:425
→ self._update_agent_state(..., connectivity_status=ConnectivityState.OFFLINE.value)
```

**Status:** ✅ Campo existe, mas **NÃO é atualizado** para ONLINE (apenas OFFLINE em erro)

---

## 2. Separação: operational_state vs connectivity_status

### operational_state
- Valores: IDLE, WORKING, ERROR
- Significado: **O que o agent está fazendo**
- Responsável: AgentRuntime (B2/B3)

### connectivity_status
- Valores: ONLINE, OFFLINE, STALE, UNKNOWN
- Significado: **Se o agent está reachable**
- Responsável: **TBD** (não existente ainda)

**Separação:** ✅ Já existe no design, mas **sem implementação de heartbeat**

---

## 3. Integração com TenantAgentStateService

✅ **Pronto para usar:**
- `update_with_transaction_lock()` (B2)
- Multi-tenant isolation (PK composta)
- SELECT FOR UPDATE (atômico)

**Recomendação:** Usar essa para atualizar connectivity_status

---

## 4. Registro de last_heartbeat_at

### Atualmente existe:
- **WebSocket.last_heartbeat** (in-memory, linha 35 websocket_manager.py)
  - Usa: cleanup_stale_connections() (timeout=60s)
  - Propósito: Detectar painel desconectado

### FALTANDO:
- **TenantAgentState.last_heartbeat_at** (persistente)
- **Agent.last_heartbeat_at** (persistente)

**Necessário criar:** Campo no model para rastrear heartbeat do agent

---

## 5. Detecção de STALE e OFFLINE

### STALE (parado há tempo)
- Atualmente: Apenas em WebSocket (60s)
- Necessário: Detector de agent stale
- Sugestão: last_heartbeat_at > timeout (ex: 300s)

### OFFLINE (desconectado)
- Atualmente: Setado em connection error (agent_runtime.py:425)
- Necessário: Revalidar com retry/heartbeat

**Ambos faltam:** Lógica determinística de transição

---

## 6. Concorrência e Isolamento Multi-Tenant

### Risco Identificado
Se múltiplos workers atualizarem connectivity_status simultaneously:

```
Worker A: SELECT FOR UPDATE tenant_agent_state (tenant_1, agent_1)
Worker B: SELECT FOR UPDATE tenant_agent_state (tenant_1, agent_1)  ← Bloqueado
```

**Mitigação:** B2 fornece SELECT FOR UPDATE ✅

### Cross-Tenant Pollution
- Operação: UPDATE connectivity_status WHERE agent_id = X
- Risco: 🔴 Sem WHERE tenant_id, afeta TODOS os tenants com agent_id=X
- Exigência: **Sempre filtrar tenant_id + agent_id**

---

## 7. WebSocket Heartbeat vs Agent Heartbeat

### WebSocket Heartbeat
- **O quê:** Painel conectado ao servidor
- **Frequência:** Ping/Pong (browser padrão)
- **Localização:** websocket_manager.py:282
- **Persistência:** ❌ In-memory apenas

### Agent Heartbeat (TBD)
- **O quê:** Agent respondendo e vivo
- **Frequência:** ⏳ A definir (ex: 30s, 60s)
- **Localização:** ⏳ A implementar
- **Persistência:** ✅ Deve persistir em Firestore/PostgreSQL

**DIFERENÇA CRÍTICA:** Um WebSocket ativo NÃO significa agent ativo!

---

## 8. Compatibilidade RecoveryService + AgentRuntime

### Fluxo de Recuperação (ETAPA 1 implementado)
1. Execução falha → classify_failure()
2. TRANSIENT → schedule_retry()
3. next_retry_at agendado
4. Status = "RESERVED"

### Integração Heartbeat (ETAPA 3)
1. Heartbeat timeout → connectivity_status = STALE
2. Se STALE + RESERVED → aumentar backoff?
3. Se OFFLINE + RESERVED → pausar retry?

**Compatibilidade:** ✅ Pode integrar, mas requer decisão de policy

---

## Conclusões da Auditoria

| Ponto | Status | Detalhe |
|-------|--------|---------|
| connectivity_status campo | ✅ Existe | Mas não usado para ONLINE |
| operational_state vs connectivity_status | ✅ Separado | Bem definido |
| TenantAgentStateService | ✅ Pronto | Para usar |
| last_heartbeat_at | ❌ Falta | Precisa criar |
| STALE/OFFLINE logic | ❌ Falta | Detector não existe |
| Concorrência | ✅ Mitigado | B2 provides SELECT FOR UPDATE |
| Isolamento multi-tenant | ⚠️ Risco | Sem WHERE tenant_id = risco |
| Compatibilidade | ✅ Possível | Com integração cuidadosa |

---

## Próximo: B3_ETAPA_3_HEARTBEAT_DESIGN.md

Design proposto inclui:
- Frequência de heartbeat
- Timeout policy
- Responsáveis (emit vs detect)
- Persistência strategy
- Testes PostgreSQL

