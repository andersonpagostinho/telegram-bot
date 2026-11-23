# BACKEND CONTRACT AUDIT — ETAPA 3
## Real Endpoints, Schemas, and Integration Points

**Status:** ⚠️ PENDENTE AUDITORIA REAL DO BACKEND

---

## ESCOPO DESTA AUDITORIA

Este documento deve ser preenchido com os contratos REAIS do backend.

Não usar pressupostos. Verificar código-fonte do backend ou documentação oficial.

---

## RECURSOS NECESSÁRIOS PARA ETAPA 3

### 1. AGENTES

**Endpoint Presumido:** `GET /api/v1/agents`

**Necessário Verificar:**
- [ ] Endpoint exato e método HTTP
- [ ] Schema de resposta (fields, types)
- [ ] Paginação (limit, offset, cursor?)
- [ ] Filtros disponíveis (status, role, online?)
- [ ] Autenticação (Bearer token?)
- [ ] Rate limiting
- [ ] Erros possíveis (401, 403, 500?)

**7 Agentes Esperados:**
1. Architect
2. Backend Developer
3. Debugger
4. QA Engineer
5. Security Auditor
6. Release Manager
7. OpenAI Validator

**Campos Críticos:**
- agent_id
- agent_role
- status (IDLE, WORKING, ANALYZING, TESTING, REVIEWING, BLOCKED, COMPLETED, ERROR)
- connectivity_status (ONLINE, OFFLINE, STALE, UNKNOWN)
- last_event_at (timestamp)
- current_mission_id (nullable)
- current_task_id (nullable)

---

### 2. MISSÕES

**Endpoint Presumido:** `GET /api/v1/missions`

**Necessário Verificar:**
- [ ] Endpoint e método
- [ ] Schema (mission_id, objective, status, priority)
- [ ] Paginação
- [ ] Filtros (status, agent_id, priority)
- [ ] Datas (created_at, started_at, completed_at)
- [ ] Responsáveis (agent assignments)

---

### 3. TAREFAS (dentro de Missão)

**Endpoint:** Pode estar em `/api/v1/missions/:id/tasks` ou incluído em GET /missions/:id

**Necessário Verificar:**
- [ ] Estrutura (task_id, objective, assignee, status)
- [ ] Dependências entre tarefas
- [ ] Progresso (percentage, status)
- [ ] Evidências/resultados

---

### 4. EXECUÇÕES

**Endpoint Presumido:** `GET /api/v1/executions`

**Necessário Verificar:**
- [ ] Endpoint e método
- [ ] Schema (execution_id, agent_id, mission_id, status, started_at, completed_at, duration)
- [ ] Paginação
- [ ] Filtros
- [ ] Logs (incluído ou separate endpoint?)
- [ ] Resultados/Output

---

### 5. WEBSOCKET

**Endpoint Presumido:** `WS /api/v1/websocket/ws?ticket=...`

**Necessário Verificar:**
- [ ] Endpoint exato e porta
- [ ] Protocolo de ticket (single-use, TTL?)
- [ ] Eventos disponíveis:
  - [ ] AGENT_UPDATED
  - [ ] AGENT_STATUS_CHANGED
  - [ ] MISSION_UPDATED
  - [ ] MISSION_COMPLETED
  - [ ] EXECUTION_STARTED
  - [ ] EXECUTION_COMPLETED
  - [ ] TASK_COMPLETED
  - [ ] EVENT_CREATED
  - [ ] VALIDATION_RESULT
  - [ ] ERROR

**Estrutura do Evento:**
```json
{
  "event_id": "...",
  "event_type": "AGENT_UPDATED",
  "timestamp": "...",
  "data": { ... },
  "cursor": 42
}
```

**Necessário Confirmar:**
- [ ] event_id (para deduplicação)
- [ ] cursor (para recovery)
- [ ] Comportamento em reconexão
- [ ] Intervalo de heartbeat
- [ ] Comportamento em desconexão

---

### 6. AUTENTICAÇÃO & MULTI-TENANT

**Necessário Confirmar:**
- [ ] JWT claim `tenant_id` presente
- [ ] JWT claim `user_id` presente
- [ ] JWT claim `actor_role` presente
- [ ] X-Tenant-ID header obrigatório
- [ ] Isolamento enforcement no backend
- [ ] Duração do token

---

### 7. EVENTOS E HISTÓRICO

**Endpoint Presumido:** `GET /api/v1/events` ou similar

**Necessário Verificar:**
- [ ] Endpoint para recuperar histórico
- [ ] Paginação por cursor
- [ ] Filtros (agent_id, mission_id, type, date_range)
- [ ] Ordem (chronological?)
- [ ] TTL (quantos dias de histórico?)

---

### 8. VALIDAÇÕES

**Endpoint Presumido:** Pode estar em `/api/v1/validations` ou `/api/v1/missions/:id/validations`

**Necessário Verificar:**
- [ ] Endpoint
- [ ] Schema (validator, result, timestamp, evidence?)
- [ ] Tipos de validadores (QA, Security, OpenAI?)
- [ ] Estados possíveis

---

### 9. OPENAI VALIDATOR

**Status Atual:** ❓ DESCONHECIDO

**Necessário Verificar:**
- [ ] É integração real?
- [ ] Endpoint?
- [ ] Como disparar validação?
- [ ] Como recuperar resultado?
- [ ] Timeout?
- [ ] Falha possível?

---

## GAPS ESPERADOS

Baseado em PHASE_4_BACKEND_FORENSIC_AUDIT.md:

- [ ] Duração de execução (pode estar faltando)
- [ ] Relatório de resultados padronizado
- [ ] Integração OpenAI Validator
- [ ] Esquema de validações QA

---

## TEMPLATE PARA PREENCHIMENTO

Para cada recurso:

```
### RECURSO: [Nome]

**Endpoint Real:** `[METHOD] /api/v1/[path]`

**Autenticação:** [Bearer? API Key?]

**Schema Resposta:**
{
  "field1": "type (required/optional)",
  "field2": "type",
  ...
}

**Paginação:** [cursor-based / offset-based / none]

**Filtros Disponíveis:** [field1, field2, ...]

**Erros Possíveis:**
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 500 Server Error

**Status:** ✅ VERIFICADO / ⚠️ PARCIAL / ❌ FALTA

**Notas:** [Observações importantes]
```

---

## RESULTADO ESPERADO

Após auditoria real do backend:
- [ ] Todos os 9 endpoints/recursos mapeados
- [ ] Schemas JSON confirmados
- [ ] Paginação validada
- [ ] WebSocket protocol testado
- [ ] Multi-tenant isolamento confirmado
- [ ] Erros e edge cases documentados
- [ ] OpenAI Validator status definido
- [ ] Blockers identificados

---

**Status:** 🟡 AGUARDANDO AUDITORIA REAL  
**Responsável:** Architect + Backend Developer  
**Próximo:** Preencher este documento com achados reais
