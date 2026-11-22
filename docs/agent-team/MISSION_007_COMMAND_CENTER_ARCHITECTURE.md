# MISSÃO 007 — COMMAND CENTER ARCHITECTURE

**Data**: 2026-11-22  
**Escopo**: Visualização multiagente em tempo real  
**Status**: 🟢 **DESIGN COMPLETO**

---

## 1. VISÃO GERAL

```
┌─────────────────────────────────────────────────┐
│         NEOEVE COMMAND CENTER                   │
│         (React Frontend + Real-time)             │
│                                                  │
│  5 Telas: Map | Stream | Missions | Validation │
│           History                               │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼────┐    ┌─────▼─────┐
    │ FastAPI │    │ WebSocket │
    │ REST    │    │ Real-time │
    │ Backend │    │  Events   │
    └────┬────┘    └──────┬────┘
         │                │
         └────────┬───────┘
                  │
         ┌────────▼─────────┐
         │   Event Bus      │
         │   (SQLite +      │
         │    JSONL)        │
         └────────┬─────────┘
                  │
    ┌─────────────┼──────────────┐
    │             │              │
┌───▼───┐    ┌───▼───┐    ┌────▼────┐
│Bridge │    │  7    │    │PostgreSQL│
│       │    │Agents │    │Projection│
│       │    │Claude │    │(Read-only)
└───────┘    └───────┘    └──────────┘
```

---

## 2. STACK TÉCNICO

### Frontend
```
✅ React 18.2+
✅ TypeScript
✅ React Flow (network visualization)
✅ Tailwind CSS (styling)
✅ WebSocket client
✅ React Query (data fetching)
✅ Dark mode (default)
```

### Backend
```
✅ FastAPI (async)
✅ Pydantic (validation)
✅ WebSocket (real-time)
✅ SQLAlchemy (ORM)
✅ Python 3.13
```

### Database
```
✅ SQLite (operational - source of truth)
✅ JSONL (audit trail)
⏳ PostgreSQL (read projection)
   - Not operational
   - Synced from Event Bus
   - For complex queries
```

---

## 3. TELA 1: AGENT MAP

### Layout
```
┌──────────────────────────────────────┐
│  AGENT MAP                   [Filter]│
├──────────────────────────────────────┤
│                                      │
│          ┌─────────────┐             │
│          │  ARCHITECT  │             │
│          │   (CENTER)  │             │
│          └──────┬──────┘             │
│                 │                    │
│    ┌────────────┼────────────┐       │
│    │            │            │       │
│  ┌─▼──┐    ┌───▼──┐    ┌───▼──┐    │
│  │Back│    │Debug │    │  QA  │    │
│  │end │    │ger   │    │      │    │
│  └────┘    └──────┘    └──────┘    │
│    │            │            │       │
│    └────────────┼────────────┘       │
│                 │                    │
│          ┌──────┴──────┐             │
│          │             │             │
│      ┌───▼──┐    ┌────▼────┐        │
│      │Sec   │    │Release  │        │
│      │      │    │Manager  │        │
│      └──────┘    └─────────┘        │
│                                      │
│  [External Validator - separate]     │
│                                      │
└──────────────────────────────────────┘

Legend:
─ → Active communication (animated)
  → Idle connection
● → Working
⏸ → Idle
✗ → Blocked
✓ → Completed
```

### Componentes

**Agent Node**
```
┌─────────────────┐
│   [Icon] Name   │
│                 │
│ State: WORKING  │
│ Task: test-001  │
│ Uptime: 2h 14m  │
└─────────────────┘
```

**Connection**
```
Animated quando evento real de comunicação

Cor por tipo:
- Blue: Task delegation
- Green: Result returned
- Yellow: Waiting
- Red: Error/Blocked
```

**Click Details**
```
┌─────────────────────────────────┐
│ Backend Developer               │
├─────────────────────────────────┤
│ Role: BACKEND                   │
│ Runtime: Claude Code CLI        │
│ Permissions: execute_task,      │
│              publish_result     │
│                                 │
│ Current State: WORKING          │
│ Current Task: task-001          │
│                                 │
│ Last Activity: 10s ago          │
│ Uptime: 2h 14m                  │
│                                 │
│ [Recent Events] [Error Log]     │
└─────────────────────────────────┘
```

---

## 4. TELA 2: ACTIVITY STREAM

### Layout
```
┌──────────────────────────────────────┐
│  ACTIVITY STREAM                     │
│  [Filter] [Date Range] [Search]      │
├──────────────────────────────────────┤
│                                      │
│  13:00:33 ✓ TASK_COMPLETED          │
│           Backend: test-read-file    │
│           execution_id: evt-...      │
│           [View Details]             │
│                                      │
│  13:00:19 → TASK_ASSIGNED            │
│           Architect → Backend        │
│           mission: etapa8-backend    │
│           [View Details]             │
│                                      │
│  12:59:17 ✓ GOVERNANCE ALLOWED       │
│           backend execute_task       │
│           [View Details]             │
│                                      │
│  12:59:05 → TASK_ASSIGNED            │
│           Architect → Backend        │
│           [View Details]             │
│                                      │
│  [Load More]                         │
│                                      │
└──────────────────────────────────────┘
```

### Event Details Modal
```
┌──────────────────────────────────┐
│ Event ID: evt-20261122160033-... │
├──────────────────────────────────┤
│ Type: TASK_COMPLETED             │
│ Timestamp: 2026-11-22 13:00:33   │
│ Agent: backend                   │
│ Mission: etapa8-backend-execution│
│ Task: backend-read-test-file     │
│                                  │
│ Status: COMPLETED                │
│ Duration: 14s                    │
│ Result: {                        │
│   status: "PARTIAL"              │
│   file_path: "tests/..."         │
│   ...                            │
│ }                                │
│                                  │
│ Correlation: corr-uuid           │
│ Causation: evt-prev-id           │
│                                  │
│ [Show Full Event JSON]           │
└──────────────────────────────────┘
```

---

## 5. TELA 3: MISSIONS

### Layout
```
┌──────────────────────────────────────┐
│  MISSIONS                            │
│  [Status Filter] [Sort By]           │
├──────────────────────────────────────┤
│                                      │
│  MISSION: etapa8-backend-execution   │
│  ├─ Status: COMPLETED ✓             │
│  ├─ Created: 13:00:19               │
│  ├─ Completed: 13:00:33             │
│  ├─ Duration: 14s                   │
│  ├─ Responsible: Architect          │
│  └─ Progress: 100%                  │
│      [View Details]                 │
│                                      │
│  MISSION: validation-review-001      │
│  ├─ Status: IN_PROGRESS             │
│  ├─ Created: 13:00:35               │
│  ├─ Responsible: QA                 │
│  └─ Progress: 50%                   │
│      [View Details]                 │
│                                      │
│  MISSION: security-audit-001         │
│  ├─ Status: PENDING                 │
│  ├─ Created: 13:00:35               │
│  ├─ Responsible: Security           │
│  └─ Progress: 0%                    │
│      [View Details]                 │
│                                      │
└──────────────────────────────────────┘
```

### Mission Details
```
┌────────────────────────────────────┐
│ Mission: etapa8-backend-execution  │
├────────────────────────────────────┤
│                                    │
│ Objective:                         │
│ Execute Backend Agent with read-   │
│ only file analysis. Validate       │
│ subscription runtime.              │
│                                    │
│ Status: COMPLETED ✓                │
│ Created: 2026-11-22 13:00:19       │
│ Completed: 2026-11-22 13:00:33     │
│ Duration: 14 seconds               │
│                                    │
│ Tasks:                             │
│ ├─ [✓] TASK_ASSIGNED (10ms)        │
│ ├─ [✓] GOVERNANCE_EVALUATED (5ms)  │
│ ├─ [✓] AGENT_EXECUTED (14000ms)    │
│ ├─ [✓] RESULT_PUBLISHED (10ms)     │
│ └─ [✓] VALIDATED (5ms)             │
│                                    │
│ Events: 5 total                    │
│ [Show Timeline]                    │
│                                    │
│ Responsible:                       │
│ Architect → Backend                │
│                                    │
│ Results:                           │
│ [Download] [View JSON]             │
│                                    │
└────────────────────────────────────┘
```

---

## 6. TELA 4: VALIDATION CENTER

### Layout
```
┌──────────────────────────────────────┐
│  VALIDATION CENTER                   │
│  [Filter] [Status]                   │
├──────────────────────────────────────┤
│                                      │
│  QA REVIEW: task-001                │
│  ├─ Validator: QA Engineer          │
│  ├─ Status: APPROVED ✓              │
│  ├─ Tests: 7/7 PASSED               │
│  ├─ Date: 13:00:35                  │
│  └─ Findings: None                  │
│      [View Details]                 │
│                                      │
│  SECURITY AUDIT: task-001           │
│  ├─ Validator: Security Auditor     │
│  ├─ Status: REVIEWING ⏳            │
│  ├─ Findings: 0 so far              │
│  └─ Started: 13:00:35               │
│      [View Details]                 │
│                                      │
│  ARCHITECT REVIEW: task-001         │
│  ├─ Validator: Architect            │
│  ├─ Status: PENDING                 │
│  └─ Awaiting: Security approval     │
│      [View Details]                 │
│                                      │
│  OPENAI VALIDATOR: task-001         │
│  ├─ Validator: OpenAI               │
│  ├─ Status: COMPLETED ✓             │
│  ├─ Confidence: 98%                 │
│  └─ Date: 13:00:40                  │
│      [View Report]                  │
│                                      │
└──────────────────────────────────────┘
```

### Validation Details
```
┌──────────────────────────────────┐
│ QA Review: task-001              │
├──────────────────────────────────┤
│                                  │
│ Validator: QA Engineer           │
│ Status: APPROVED ✓               │
│ Date: 2026-11-22 13:00:35        │
│ Duration: 2m 14s                 │
│                                  │
│ Test Results:                    │
│ ├─ Unit Tests: 7/7 PASSED        │
│ ├─ Integration: 3/3 PASSED       │
│ ├─ Regression: 15/15 PASSED      │
│ └─ Regressions: 0 found          │
│                                  │
│ Findings: None                   │
│                                  │
│ Evidence:                        │
│ [test_results.json]              │
│ [execution_log.txt]              │
│                                  │
│ [Approve] [Reject]               │
│                                  │
└──────────────────────────────────┘
```

---

## 7. TELA 5: MISSION HISTORY

### Layout
```
┌──────────────────────────────────────┐
│  MISSION HISTORY                     │
│  [Date Range] [Filter] [Search]      │
├──────────────────────────────────────┤
│                                      │
│  2026-11-22                          │
│  │                                   │
│  ├─ 13:00:33 ✓ etapa8-backend       │
│  │            (14 seconds)           │
│  │            Backend: test file     │
│  │            Status: COMPLETED      │
│  │            [Reopen]               │
│  │                                   │
│  ├─ 12:30:15 ✓ validation-review    │
│  │            (2m 14s)               │
│  │            QA: Approve            │
│  │            Status: COMPLETED      │
│  │            [Reopen]               │
│  │                                   │
│  └─ 12:00:00 ✓ security-audit-001   │
│             (45m 22s)                │
│             Security: Approved       │
│             Status: COMPLETED        │
│             [Reopen]                 │
│                                      │
│  2026-11-21                          │
│  │                                   │
│  └─ [23 more missions this month]    │
│                                      │
│  [Load Earlier]                      │
│                                      │
└──────────────────────────────────────┘
```

### Historical Reconstruction
```
┌────────────────────────────────────┐
│ Mission: etapa8-backend-execution  │
│ (Historical View)                  │
├────────────────────────────────────┤
│                                    │
│ Timeline (from Event Bus):         │
│                                    │
│ [13:00:19] ■ TASK_ASSIGNED         │
│            Architect created       │
│            evt-20261122160019...   │
│                                    │
│ [13:00:19] ■ GOVERNANCE_ALLOWED    │
│            Backend → execute_task  │
│            causation_id: ...       │
│                                    │
│ [13:00:19] ■ AGENT_STARTED         │
│            Runtime: Claude CLI     │
│            pid: 12345              │
│                                    │
│ [13:00:33] ■ TASK_COMPLETED        │
│            Result: {...}           │
│            duration: 14s           │
│                                    │
│ [13:00:33] ■ RESULT_PUBLISHED      │
│            evt-20261122160033...   │
│            correlation_id: ...     │
│                                    │
│ [Show All 5 Events]                │
│ [Export Timeline]                  │
│                                    │
└────────────────────────────────────┘
```

---

## 8. ESTADOS VISUAIS

### Estados de Atividade

```
IDLE      ⏸  Cinza   - Aguardando tarefa
WORKING   ⚙️  Azul    - Executando tarefa
ANALYZING 🔍 Amarelo  - Analisando dados
TESTING   ✓  Verde    - Executando testes
REVIEWING 👁  Roxo     - Revisando código
BLOCKED   ⛔ Vermelho  - Bloqueado
COMPLETED ✓  Verde    - Concluído
ERROR     ✗  Vermelho - Erro crítico
```

### Estados de Conectividade

```
ONLINE    ● Verde    - Conectado
OFFLINE   ◌ Cinza    - Desconectado
STALE     ⚠  Amarelo  - Sem heartbeat recente
UNKNOWN   ❓ Cinza    - Estado desconhecido
```

---

## 9. API REST ENDPOINTS

```python
# Agentes
GET /api/agents
GET /api/agents/{agent_id}
GET /api/agents/{agent_id}/status
GET /api/agents/{agent_id}/tasks
GET /api/agents/{agent_id}/errors

# Missões
GET /api/missions
GET /api/missions/{mission_id}
GET /api/missions/{mission_id}/events
GET /api/missions/{mission_id}/timeline
GET /api/missions/{mission_id}/stats

# Tarefas
GET /api/tasks
GET /api/tasks/{task_id}
GET /api/tasks/{task_id}/events

# Atividade
GET /api/activity
GET /api/activity/stream
GET /api/activity/correlations/{correlation_id}

# Validação
GET /api/validations
GET /api/validations/{validation_id}
GET /api/validations/task/{task_id}

# Histórico
GET /api/history
GET /api/history/range/{start_date}/{end_date}

# Sistema
GET /api/health
GET /api/stats
GET /api/stats/agents
GET /api/stats/missions
GET /api/stats/validations
```

---

## 10. WEBSOCKET EVENTS

```python
# Agente
agent.status_changed
agent.heartbeat
agent.task_started
agent.task_completed
agent.task_failed
agent.message_sent
agent.error

# Tarefa
task.created
task.started
task.completed
task.failed
task.validated

# Missão
mission.created
mission.started
mission.completed
mission.failed
mission.blocked

# Validação
validation.started
validation.completed
validation.failed
validation.approved
validation.rejected

# Segurança
security.blocked
security.warning
security.cleared

# Sistema
system.error
system.warning
system.info
```

---

## 11. BANCO DE DADOS (PostgreSQL - Read Projection)

### Schema

```sql
-- Agentes (snapshot)
CREATE TABLE agents (
    agent_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    role VARCHAR,
    state VARCHAR,
    last_activity TIMESTAMP,
    current_task_id VARCHAR,
    uptime INTERVAL,
    execution_count INT,
    error_count INT,
    success_count INT
);

-- Missões (snapshot)
CREATE TABLE missions (
    mission_id VARCHAR PRIMARY KEY,
    objective VARCHAR,
    state VARCHAR,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration INTERVAL,
    agent_responsible VARCHAR
);

-- Tarefas
CREATE TABLE tasks (
    task_id VARCHAR PRIMARY KEY,
    mission_id VARCHAR,
    agent_id VARCHAR,
    state VARCHAR,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration INTERVAL
);

-- Events (materialized view from Event Bus)
CREATE TABLE events (
    event_id VARCHAR PRIMARY KEY,
    event_type VARCHAR,
    mission_id VARCHAR,
    task_id VARCHAR,
    agent_id VARCHAR,
    correlation_id VARCHAR,
    causation_id VARCHAR,
    timestamp TIMESTAMP,
    payload JSONB
);

-- Validations
CREATE TABLE validations (
    validation_id VARCHAR PRIMARY KEY,
    task_id VARCHAR,
    validator_agent VARCHAR,
    result VARCHAR,
    findings JSONB,
    timestamp TIMESTAMP
);
```

---

## 12. FLUXO DE SINCRONIZAÇÃO

```
Event Bus (SQLite)
    │
    ├─ Event published
    ├─ JSONL appended
    └─ WebSocket broadcast → Frontend
         │
         ├─ Trigger sync job
         └─ Update PostgreSQL
              │
              └─ Materialize view
                   │
                   └─ Query for dashboard
```

**Garantias**:
- ✅ SQLite = Fonte de verdade operacional
- ✅ JSONL = Trilha de auditoria completa
- ✅ PostgreSQL = Leitura otimizada (não crítica)
- ✅ WebSocket = Tempo real (UI apenas)

---

## 13. SEGURANÇA

```
✅ Autenticação do proprietário
✅ Sessão segura (JWT/Session)
✅ HTTPS/WSS only
✅ Sanitização de dados
✅ Sem exposição de secrets
✅ Sem exposição de OAuth tokens
✅ Logs de acesso
✅ Rate limiting
✅ CORS restritivo
✅ CSP headers
```

---

## 14. PERFORMANCE

```
Target latency:
- Initial page load: < 2s
- Event broadcast: < 100ms
- API response: < 500ms
- WebSocket message: < 50ms
```

---

## 15. PRÓXIMOS PASSOS

1. ✅ Arquitetura definida
2. ⏳ Backend FastAPI + WebSocket
3. ⏳ Frontend React (5 screens)
4. ⏳ PostgreSQL sync
5. ⏳ Integração Event Bus
6. ⏳ Testes E2E
7. ⏳ Deployment

**Status**: 🟢 Pronto para implementação

