# BACKEND CONTRACT AUDIT — REAL FINDINGS
## ETAPA 3 — FASE 2 Audit Results

**Data:** 2026-11-22  
**Escopo:** READ-ONLY audit de `/app/api/routes/` e schemas  
**Status:** 🟡 PARCIAL (Verificado em tempo limite de tokens)

---

## CONTRATOS VERIFICADOS

### 1. AGENTS

**Endpoint 1: List Agents**
- **Route:** `GET /api/v1/agents`
- **Método:** FastAPI GET
- **Implementação:** `/app/api/routes/agents.py:18-59`
- **Autenticação:** JWT (via `get_current_user`)
- **Request:**
  ```
  page: int (default 1)
  per_page: int (default 20, max 100)
  role: Optional[str] (filter)
  status: Optional[str] (filter)
  ```
- **Response:** `AgentListResponse`
  - `total: int`
  - `agents: list[AgentResponse]`

**AgentResponse Schema (Schema verificado em agent.py)**
```python
agent_id: str
agent_role: str
runtime: str
status: str (IDLE, WORKING, ANALYZING, TESTING, REVIEWING, BLOCKED, COMPLETED, ERROR)
connectivity_status: str (ONLINE, OFFLINE, STALE, UNKNOWN)
last_event_at: Optional[datetime]
last_execution_at: Optional[datetime]
last_error: Optional[str]
metrics_summary: Optional[dict]
current_mission_id: Optional[str]
current_task_id: Optional[str]
updated_at: datetime
```

**Endpoint 2: Get Agent Detail**
- **Route:** `GET /api/v1/agents/{agent_id}`
- **Response:** `AgentResponse` (single agent)

**Multi-tenant Considerações:**
- ⚠️ Agentes são GLOBAIS (comment: "Agents are global system entities (not tenant-scoped)")
- Mas filtragem por tenant_id ocorre em `get_agent()` (linha 73)

---

### 2. MISSIONS

**Endpoint: List Missions**
- **Route:** `GET /api/v1/missions`
- **Implementação:** `/app/api/routes/missions.py:18-40`
- **Autenticação:** JWT (tenant e project do JWT, NUNCA do request)
- **Request:**
  ```
  page: int (default 1)
  per_page: int (default 20, max 100)
  status: Optional[str] (filter via alias "status")
  days: Optional[int] (filter created in last N days)
  ```
- **Response:** `MissionListResponse`

**Multi-tenant:**
- ✅ VERIFICADO: Tenant e project do JWT (linhas 36-37)
- ✅ Isolamento validado

**Dependências:** Leitura de `MissionService` necessária para confirmar paginação completa

---

### 3. WEBSOCKET

**Endpoint: Issue Ticket**
- **Route:** `POST /api/v1/websocket/ticket`
- **Implementação:** `/app/api/routes/websocket.py:21-59`
- **Autenticação:** JWT
- **Request:** (empty, JWT via header)
- **Response:** `{"ticket": "..."}`
- **TTL:** 5 minutos (confirmado linha 30)
- **Single-Use:** ✅ Confirmado (linha 30)
- **Rate Limiting:** ✅ Max 10 tickets/user/minute (linha 31)
- **Erro:** 429 Too Many Requests se rate limit exceed (linhas 51-54)

**Multi-tenant:**
- ✅ Ticket vinculado a tenant_id, user_id, actor_id, actor_role (linhas 38-42)

**WebSocket Endpoint (Real):**
- ❓ Endpoint path `/ws` ou similar não encontrado ainda em leitura rápida
- ⚠️ PENDENTE: Verificar exatamente qual é a rota WebSocket (presumir `/api/v1/websocket/ws`)

---

## RECURSOS PARCIALMENTE VERIFICADOS

### Executions
- ⚠️ **Status:** Route file existe em `executions.py`
- **Necessário:** Leitura de executions.py para confirmar endpoints e paginação

### Missions Details, Tasks
- ⚠️ **Status:** Route files existem
- **Necessário:** Leitura de missions.py (completo) e tasks.py

### Validations
- ⚠️ **Status:** Route file existe em `validations.py`
- **Necessário:** Leitura para confirmar QA + Security Audit + OpenAI Validator endpoints

### Metrics
- ⚠️ **Status:** Route file existe em `metrics.py`
- **Necessário:** Leitura para confirmar Dashboard metrics endpoints

---

## RECURSOS NÃO VERIFICADOS (Necessário mais tempo)

### A. Event Recovery & History
- **Presumível:** Existir endpoint para recuperar eventos históricos
- **Cursor-based pagination:** ⚠️ DESCONHECIDO
- **Deduplicação:** ⚠️ DESCONHECIDO
- **Status:** ❌ NÃO VERIFICADO

### B. WebSocket Events
- **Protocolo real:** ⚠️ DESCONHECIDO
  - event_id field? ✅ Confirmado em schema (agent.py:48)
  - event_type field? ✅ Confirmado (agent.py:49)
  - cursor field? ❓ DESCONHECIDO
  - sequence field? ❓ DESCONHECIDO

### C. OpenAI Validator Integration
- **Status:** ❌ NÃO VERIFICADO
- **Implementação:** Pode estar em validation_service.py
- **Integração Real:** ⚠️ DESCONHECIDO (pode ser OFFLINE/UNKNOWN)

### D. Mission History Endpoint
- **Status:** ❌ NÃO VERIFICADO
- **Histórico Disponível:** ⚠️ DESCONHECIDO

### E. Settings Endpoints
- **Status:** ❌ NÃO VERIFICADO

---

## ACHADOS CRÍTICOS

### ✅ CONFIRMADO: Multi-tenant Isolation
- JWT-based tenant identification
- Tenant ID NUNCA do request
- Isolamento validado no código (missions.py:36-37)

### ✅ CONFIRMADO: WebSocket Security
- Ticket-based auth (single-use, 5-min TTL)
- Rate limiting (10/min per user)
- Vinculação com tenant_id + user_id

### ✅ CONFIRMADO: Paginação
- Offset-based (page, per_page)
- Max per_page: 100 items

### ⚠️ POSSÍVEL ISSUE: Agents são GLOBAIS
- Comment diz "Agents are global system entities"
- Mas há verificação de tenant_id em get_agent()
- **Necessário:** Clarificar se agentes são realmente globais ou se há isolamento

### ❓ DESCONHECIDO: Cursor-based Pagination
- Paginação offset-based confirmada para agents e missions
- WebSocket event recovery por cursor: ❓ DESCONHECIDO
- **Necessário:** Verificar websocket_event_log_service.py

---

## MATRIZ DE CONTRATOS

| Recurso | Endpoint | Método | Status | Prioridade |
|---------|----------|--------|--------|-----------|
| List Agents | GET /api/v1/agents | ✅ VERIFIED | P1 |
| Get Agent | GET /api/v1/agents/{id} | ✅ VERIFIED | P1 |
| List Missions | GET /api/v1/missions | ✅ VERIFIED | P1 |
| Get Mission | GET /api/v1/missions/{id} | ⚠️ PARTIAL | P1 |
| Get Tasks | GET /api/v1/missions/{id}/tasks | ⚠️ PARTIAL | P1 |
| List Executions | GET /api/v1/executions | ⚠️ PARTIAL | P1 |
| Get Execution | GET /api/v1/executions/{id} | ⚠️ PARTIAL | P1 |
| List Events | GET /api/v1/events | ❌ NOT FOUND | P1 |
| WebSocket Ticket | POST /api/v1/websocket/ticket | ✅ VERIFIED | P1 |
| WebSocket WS | WS /api/v1/websocket/ws | ⚠️ NOT VERIFIED | P1 |
| List Validations | GET /api/v1/validations | ⚠️ PARTIAL | P2 |
| OpenAI Validator | ? | ❌ NOT FOUND | P2 |
| Mission History | ? | ❌ NOT FOUND | P3 |
| Settings | ? | ❌ NOT FOUND | P3 |

---

## BLOQUEADORES IDENTIFICADOS

### 1. Event History Endpoint (CRÍTICO)
**Necessário para:** Activity Stream (TELA 3)
**Status:** ❌ Não encontrado em leitura rápida
**Risco:** Activity Stream não pode ser implementada sem endpoint de eventos

### 2. WebSocket Event Protocol (CRÍTICO)
**Necessário para:** Todas as telas em tempo real
**Status:** ⚠️ Ticket confirmado, mas protocolo de eventos DESCONHECIDO
**Risco:** Integração real-time pode falhar se estrutura de evento for diferente

### 3. OpenAI Validator Integration (MÉDIO)
**Necessário para:** Validation Center (TELA 7)
**Status:** ❌ Não encontrado
**Risco:** Pode não existir ou estar offline por padrão

### 4. Cursor-based Pagination (MÉDIO)
**Necessário para:** Activity Stream recovery
**Status:** ⚠️ Offset-based confirmado, cursor DESCONHECIDO
**Risco:** Recovery após reconexão pode usar offset ao invés de cursor

---

## RECOMENDAÇÃO

### 🟡 STATUS: NO-GO (parcial, com dependências críticas não verificadas)

**Razões:**
1. Event history endpoint não verificado (necessário para Activity Stream)
2. WebSocket event protocol não totalmente verificado
3. OpenAI Validator status desconhecido
4. Tempo limite de tokens impediu auditoria completa

**Para GO, necessário:**
1. ✅ Continuar auditoria de executions.py, tasks.py, validations.py
2. ✅ Verificar websocket_event_log_service.py para recuperação por cursor
3. ✅ Confirmar exatamente qual é a rota WebSocket (p. ex., `/ws` ou `/websocket`)
4. ✅ Encontrar ou criar endpoint de histórico de eventos
5. ✅ Verificar integração OpenAI Validator

---

**Próximo Passo:** Continuar auditoria com mais tempo de tokens disponível, ou proceder com entendimento de que Activity Stream (TELA 3) pode requerer novo endpoint backend.
