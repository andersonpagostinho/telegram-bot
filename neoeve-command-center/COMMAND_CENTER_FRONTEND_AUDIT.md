# AUDITORIA FRONTEND — NEOEVE COMMAND CENTER

**Data:** 2026-11-25  
**Escopo:** Read-only audit do frontend e comparação com backend  
**Status:** Preliminar — Sem alterações implementadas  

---

## ÍNDICE

1. [Estado Atual do Frontend](#estado-atual-do-frontend)
2. [Rotas Existentes](#rotas-existentes)
3. [Componentes Existentes](#componentes-existentes)
4. [Auditoria das 3 Telas](#auditoria-das-3-telas)
5. [Investigação das Divergências](#investigação-das-divergências)
6. [Inventário de Telas Faltantes](#inventário-de-telas-faltantes)
7. [Proposta de Arquitetura de Navegação](#proposta-de-arquitetura-de-navegação)
8. [Priorização P0/P1/P2](#priorização-p0p1p2)
9. [Plano Incremental de Implementação](#plano-incremental-de-implementação)
10. [Dependências do Backend](#dependências-do-backend)
11. [Critérios de Aceitação](#critérios-de-aceitação)

---

## 1. ESTADO ATUAL DO FRONTEND

### Estrutura de Arquivos

```
frontend/src/
├── pages/                      # 5 páginas (3 ativas + 2 auxiliares)
│   ├── Overview.tsx           ✅ FUNCIONAL
│   ├── AgentMap.tsx           ✅ FUNCIONAL
│   ├── ActivityStream.tsx     ⚠️ PARCIAL (mostra "No events available")
│   ├── Login.tsx              ✅ FUNCIONAL
│   └── NotFound.tsx           ✅ FUNCIONAL
├── components/
│   ├── layout/                # Layout grid (Sidebar, Topbar, AppShell, PageHeader)
│   ├── common/                # Cards, indicators, loading states (8 componentes)
│   ├── charts/                # Visualização de métricas
│   ├── timeline/              # Timeline e event indicators
│   ├── topology/              # React Flow (AgentNode, AgentEdge, indicators)
│   ├── agent/                 # AgentDetailModal
│   ├── ProtectedRoute.tsx     # Route guarding
│   └── ErrorBoundary.tsx      # Error handling
├── hooks/                     # Custom React hooks (5 hooks)
│   ├── useAgents.ts           # List agents (via TanStack Query)
│   ├── useMissions.ts         # List missions
│   ├── useExecutions.ts       # List executions
│   ├── useWebSocket.ts        # WebSocket connection
│   └── useAuthPersist.ts      # Auth persistence
├── services/
│   ├── api.ts                 # Axios client + endpoints
│   ├── websocket.ts           # WebSocket client
│   └── errors.ts              # Error normalization
├── store/
│   ├── auth.ts                # Auth state (Zustand)
│   ├── ui.ts                  # UI state (sidebar, modals)
│   ├── websocket.ts           # WebSocket state
│   └── index.ts               # Store exports
├── types/
│   ├── api.ts                 # API response schemas
│   └── store.ts               # Store types
├── lib/
│   ├── theme/tokens.ts        # Design tokens
│   └── queryClient.ts         # TanStack Query setup
├── __tests__/                 # Test files (10 arquivos)
├── App.tsx                    # Root component
├── router.tsx                 # Route definitions
└── index.tsx                  # App entry point
```

### Dependências Principais

- **React Router v6** — Roteamento
- **React Flow** — Visualização de topologia de agentes
- **TanStack React Query** — Data fetching e caching
- **Zustand** — State management
- **Axios** — HTTP client
- **Tailwind CSS** — Styling
- **date-fns** — Date formatting
- **clsx** — Conditional classnames

### Padrões Estabelecidos

- ✅ **Multi-tenant** — Header `X-Tenant-ID` extraído do JWT
- ✅ **Protected routes** — All routes except `/login` require auth
- ✅ **TanStack Query** — Centralized data fetching com caching
- ✅ **Zustand stores** — Global state (auth, UI, WebSocket)
- ✅ **Error boundaries** — Graceful error handling
- ✅ **Loading states** — LoadingState, ErrorState, EmptyState components
- ✅ **WebSocket integration** — Live event subscriptions

---

## 2. ROTAS EXISTENTES

### Rotas de Frontend (router.tsx)

| Rota | Componente | Status | Escopo |
|------|-----------|--------|--------|
| `/login` | Login | ✅ Funcional | Autenticação |
| `/` | Overview | ✅ Funcional | Dashboard principal |
| `/agents` | AgentMap | ✅ Funcional | Topologia de agentes |
| `/activity` | ActivityStream | ⚠️ Parcial | Eventos históricos |
| `*` | NotFound | ✅ Funcional | 404 handling |

**Achado:** Apenas 3 rotas de negócio ativas. Nenhuma rota para:
- Missions (FALTA)
- Tasks (FALTA)
- Executions (FALTA)
- Validation Center (FALTA)
- Histórico/Analytics (FALTA)
- Release Center (FALTA)

---

## 3. COMPONENTES EXISTENTES

### Componentes de Layout

| Componente | Localização | Responsabilidade | Status |
|-----------|-------------|-----------------|--------|
| AppShell | `layout/AppShell.tsx` | Root layout grid | ✅ Funcional |
| Sidebar | `layout/Sidebar.tsx` | Main navigation (3 itens) | ✅ Funcional |
| Topbar | `layout/Topbar.tsx` | Top bar (user, logout) | ✅ Funcional |
| PageHeader | `layout/PageHeader.tsx` | Page title + optional action | ✅ Funcional |

**Código-chave:** `frontend/src/components/layout/Sidebar.tsx:17-22`
```typescript
const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', path: '/', icon: '📊' },
  { label: 'Agent Map', path: '/agents', icon: '🕸️' },
  { label: 'Activity Stream', path: '/activity', icon: '📡' },
  // Additional navigation items prepared for future expansion
];
```

### Componentes Comuns

| Componente | Responsabilidade |
|-----------|-----------------|
| MetricCard | Exibe métrica (label + value) |
| StatusIndicator | Status visual (operational + connectivity) |
| AgentCard | Card de agente (deprecated em favor de AgentNode?) |
| LoadingState | Spinner + mensagem |
| ErrorState | Error message + details |
| EmptyState | "No data available" message |

### Componentes de Topologia (React Flow)

| Componente | Responsabilidade | Status |
|-----------|-----------------|--------|
| AgentNode | Node customizado para agent | ✅ Funcional |
| AgentNodeStatus | Status visual dentro do node | ✅ Funcional |
| AgentConnectivityIndicator | Indicator de conectividade | ✅ Funcional |
| AgentEdge | Edge customizado entre agentes | ✅ Funcional |

**Código-chave:** `frontend/src/pages/AgentMap.tsx:71-79`
```typescript
const edgeDefinitions: Array<[string, string]> = [
  ['architect', 'backend_dev'],
  ['architect', 'debugger'],
  ['architect', 'qa'],
  ['backend_dev', 'security_auditor'],
  ['debugger', 'security_auditor'],
  ['qa', 'release_mgr'],
  ['security_auditor', 'openai_validator'],
];
```

### Componentes de Timeline

| Componente | Responsabilidade |
|-----------|-----------------|
| Timeline | Renderiza lista de eventos em timeline |
| EventItem | Item individual na timeline |
| EventTypeIndicator | Visual indicator do tipo de evento |

### Modal de Detalhes

| Componente | Localização | Responsabilidade | Status |
|-----------|-------------|-----------------|--------|
| AgentDetailModal | `agent/AgentDetailModal.tsx` | Drawer com detalhes do agent | ✅ Funcional |

**Código-chave:** `frontend/src/components/agent/AgentDetailModal.tsx:204-245`
```typescript
{agent.current_mission_id && (
  <div>
    <h3>Current Mission</h3>
    <div>{agent.current_mission_id}</div>
    {agent.current_task_id && (
      <div>Task: {agent.current_task_id}</div>
    )}
  </div>
)}
```

---

## 4. AUDITORIA DAS 3 TELAS

### TELA 1: OVERVIEW

**Localização:** `frontend/src/pages/Overview.tsx`  
**Endpoints utilizados:**
- `GET /api/v1/agents` (via useAgents hook)
- `GET /api/v1/missions` (via useMissions hook)
- `GET /api/v1/executions` (via useExecutions hook)

**Dados exibidos:**

| Métrica | Fonte | Extração | Status |
|--------|------|----------|--------|
| Total Agents | agentsData.agents.length | Contagem direta | ✅ |
| Online | agentsData.agents.filter(a => a.connectivity_status === 'ONLINE') | Filter em memória | ✅ |
| Working | agentsData.agents.filter(a => a.status === 'WORKING') | Filter em memória | ✅ |
| Errors | agentsData.agents.filter(a => a.status === 'ERROR') | Filter em memória | ✅ |
| Active Missions | missionsData.missions.filter(m => m.status === 'RUNNING') | Filter em memória | ✅ |
| Executions | executionsData.executions.length | Contagem direta | ✅ |

**Código-chave:** `frontend/src/pages/Overview.tsx:19-43`
```typescript
const metrics = useMemo(() => {
  if (!agentsData?.agents) return null;

  const agents = agentsData.agents;
  const totalAgents = agents.length;
  const onlineAgents = agents.filter(a => a.connectivity_status === 'ONLINE').length;
  const workingAgents = agents.filter(a => a.status === 'WORKING').length;
  const errorAgents = agents.filter(a => a.status === 'ERROR').length;

  const missions = missionsData?.missions || [];
  const activeMissions = missions.filter(m => m.status === 'RUNNING').length;

  const executions = executionsData?.executions || [];
  const totalExecutions = executions.length;

  return {
    totalAgents,
    onlineAgents,
    workingAgents,
    errorAgents,
    activeMissions,
    totalExecutions,
  };
}, [agentsData, missionsData, executionsData]);
```

**Problemas observados:**

✅ **Active Missions = 0**
- Código verifica: `missions.filter(m => m.status === 'RUNNING')`
- Backend endpoint `/api/v1/missions` retorna `status` = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "BLOCKED"
- Se B5.1 criou missões em status RUNNING, essas deveriam aparecer
- **Hipótese dominante:** Missões criadas durante B5.1 estão em status diferente de "RUNNING" (ex: PENDING, COMPLETED)
- **Ação necessária:** Verificar qual status as missões criadas em B5.1 possuem no banco

✅ **Executions = 0**
- Código verifica: `executionsData.executions.length`
- Backend endpoint `/api/v1/executions` retorna lista de execuções
- Se B5.1 criou execuções, essas deveriam aparecer
- **Hipótese dominante:** Execuções não foram criadas OU estão em outro tenant
- **Ação necessária:** Verificar se execuções foram criadas e qual tenant_id possuem

**Renderização visual:**
- 6 cards de métrica em grid
- 1 chart "Agent Distribution" (mostra apenas online agents)
- Timeline com últimos 5 executions (se houver)

---

### TELA 2: AGENT MAP

**Localização:** `frontend/src/pages/AgentMap.tsx`  
**Endpoints utilizados:**
- `GET /api/v1/agents?per_page=100`
- WebSocket (AGENT_UPDATED, AGENT_STATUS_CHANGED)

**Dados exibidos:**
- 7 agentes (hardcoded na topologia)
- Estados: `status` (IDLE, WORKING, etc.) + `connectivity_status` (ONLINE, OFFLINE, STALE, UNKNOWN)
- Conexões entre agentes (7 edges)
- AgentDetailModal ao clicar em nó

**Código-chave:** `frontend/src/pages/AgentMap.tsx:50-68`
```typescript
const newNodes: Array<Node<AgentNodeData>> = agentsData.agents.map((agent) => {
  let nodeId = agent.agent_id.toLowerCase();
  let position = positionMap[nodeId] || { x: 0, y: 0 };

  return {
    id: nodeId,
    type: 'agentNode',
    data: {
      agent_id: agent.agent_id,
      agent_role: agent.agent_role,
      status: agent.status,
      connectivity_status: agent.connectivity_status,
      last_event_at: agent.last_event_at,
      runtime: agent.runtime,
      current_mission_id: agent.current_mission_id,
    } as AgentNodeData,
    position,
  };
});
```

**Achados:**
- ✅ Exibe todos os 7 agentes corretamente
- ✅ Estados (status + connectivity_status) vêm de `/api/v1/agents`
- ✅ Exibe `current_mission_id` (que pode estar vazio)
- ✅ WebSocket integrado para atualizações em tempo real
- ✅ AgentDetailModal mostra mission e task atual

**Mas observe:** 
- AgentDetailModal em `frontend/src/components/agent/AgentDetailModal.tsx:23` busca o agente por ID na array passada
- Não faz request separada ao backend para detalhes

---

### TELA 3: ACTIVITY STREAM

**Localização:** `frontend/src/pages/ActivityStream.tsx`  
**Endpoints utilizados:**
- `GET /api/v1/events` (cursor-based pagination)
- WebSocket (AGENT_UPDATED, MISSION_UPDATED, EXECUTION_COMPLETED)

**Problema crítico:**

**Exibe:** `"No events available"`

**Investigação:**

1. **Código de fetch (linhas 34-74):**
```typescript
const response = await apiClient.getEvents({
  cursor: undefined,
  per_page: 50
});

if (response.events && Array.isArray(response.events)) {
  const mapped = response.events
    .filter((evt: any) => !eventIdsRef.current.has(evt.event_id))
    .map((evt: any) => {
      eventIdsRef.current.add(evt.event_id);
      return {
        id: evt.event_id,
        event_id: evt.event_id,
        event_type: evt.event_type,
        sequence: evt.sequence,
        timestamp: new Date(evt.created_at),
        agent: evt.payload?.source_agent || evt.payload?.agent_id || 'unknown',
        status: mapEventTypeToStatus(evt.event_type),
        description: formatEventDescription(evt),
        mission_id: evt.payload?.mission_id,
      };
    });

  setEvents(mapped);
  setCursor(response.cursor);
  setHasMore(response.has_more || false);
}
```

2. **Backend endpoint (backend/app/api/routes/events.py:21-90):**
   - Query: `db.query(WebSocketEventLog).filter(WebSocketEventLog.tenant_id == tenant_id)`
   - Filtro de cursor: `WebSocketEventLog.sequence > cursor`
   - Ordem: `by_sequence` (ASC)
   - Retorna: `EventResponse` com (event_id, event_type, sequence, tenant_id, project_id, payload, created_at)

3. **Possíveis causas:**

   | Hipótese | Probabilidade | Verificação |
   |----------|---------------|------------|
   | Nenhum evento foi criado em B5.1 | Alta | Query `SELECT COUNT(*) FROM websocket_event_logs WHERE tenant_id = ?` |
   | Eventos foram criados em outro tenant | Alta | Query `SELECT COUNT(*) FROM websocket_event_logs` (sem filter tenant) |
   | Eventos foram limpados/deletados | Média | Query `SELECT COUNT(*) FROM websocket_event_logs WHERE created_at > '2026-10-19'` |
   | EventLog não está sendo populado | Média | Verificar event bus e publishers |
   | Resposta do backend é vazia | Baixa | Adicionar logging no GET /events |

**Achados técnicos:**

- **Contrato esperado:** `{ events: [...], total: N, cursor: X, has_more: boolean }`
- **Mapeamento:** Frontend mapeia `evt.created_at` → `timestamp`, `evt.payload?.source_agent` → `agent`
- **Deduplicação:** `eventIdsRef` previne duplicatas ao adicionar eventos via WebSocket
- **Paginação:** Cursor-based (sequence number), não page/offset

---

## 5. INVESTIGAÇÃO DAS DIVERGÊNCIAS

### DIVERGÊNCIA 1: Overview.ActiveMissions = 0 vs. Agent Map mostra agent em WORKING com mission

**Contexto:**
- Overview exibe: Active Missions = 0
- Agent Map exibe: Architect em WORKING com `current_mission_id` = algum valor
- **Esperado:** Se há agente em WORKING com mission, deve haver ≥1 active mission

**Análise:**

```typescript
// Overview: filtra por status = 'RUNNING'
const activeMissions = missions.filter(m => m.status === 'RUNNING').length;

// Agent Map: exibe agent.current_mission_id (qualquer que seja)
{agent.current_mission_id && (
  <div>Mission: {agent.current_mission_id}</div>
)}
```

**Causa raiz (hipótese dominante):**
- Agent.current_mission_id aponta para uma missão
- Mas essa missão tem status ≠ "RUNNING" (ex: PENDING, COMPLETED, BLOCKED, FAILED)
- Logo, `activeMissions` = 0 está correto
- O que falta é: **definição clara de "active"**

**Questões:**
1. Uma missão em status PENDING com agente trabalhando nela deveria contar como "active"?
2. Uma missão em status COMPLETED com agente finalizando deveria contar?
3. Qual é o ciclo de vida esperado de uma mission?

**Backend schema (backend/app/schemas/mission.py):**
```python
status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED'
```

**Achado:** Não há documentação do contrato de transições de status.

---

### DIVERGÊNCIA 2: Overview.Executions = 0 vs. B5.1 reporta "Execution concluída"

**Contexto:**
- Overview exibe: Executions = 0
- Relatório B5.1 diz: "Execution concluída" e "Eventos persistidos"
- **Esperado:** Se B5.1 criou execução, `executionsData.executions.length` > 0

**Análise:**

```typescript
// Frontend: GET /api/v1/executions
const response = await this.client.get<ExecutionListResponse>('/executions', {
  params: queryParams,
});

// Backend: returns executions for current tenant
missions, total = service.list_executions(
  tenant_id=current_user.tenant_id,
  page=page,
  per_page=per_page,
)
```

**Possibilidades:**

| Cenário | Probabilidade | Prova |
|---------|---------------|-------|
| Execução criada em tenant diferente | Alta | `SELECT COUNT(*) FROM executions WHERE tenant_id != current_user_tenant` |
| Execução criada mas status = não-listável | Média | `SELECT COUNT(*) FROM executions` para todos os status |
| Execução no banco mas Query filtra errado | Baixa | Comparar SQL esperado vs. real |
| Backend paginação omite resultados | Baixa | Query com `page=1, per_page=20` vs. sem limit |

**Achado crítico:** Sem acesso ao banco durante auditoria, não posso confirmar se execuções existem.

---

## 6. INVENTÁRIO DE TELAS FALTANTES

### Telas que NÃO existem

| Tela | Propósito | Componentes necessários | Endpoints necessários | Prioridade |
|------|----------|------------------------|----------------------|-----------|
| **Missions** | CRUD + acompanhamento de missões | MissionList, MissionDetail, MissionCreate | GET/POST `/missions` | P1 |
| **Mission History** | Histórico pesquisável de missões | MissionHistoryTable, filters, search | GET `/missions?days=N` | P2 |
| **Tasks** | Ver tarefas, agente responsável, status | TaskList, TaskDetail, TaskFilters | GET/POST `/tasks` | P1 |
| **Executions** | Acompanhar execuções, duração, estado, logs | ExecutionList, ExecutionDetail, logs | GET `/executions` | P1 |
| **Execution Details** | Detalhes profundos: timeline, durations, logs, resultado | ExecutionTimeline, LogViewer, DurationChart | GET `/executions/{id}` | P1 |
| **Validation Center** | Resultados de QA, auditoria, aprovações | ValidationResults, ApprovalFlow | GET `/validations` | P1 |
| **Security Audit** | Auditoria de segurança | SecurityAuditResults, AuditTrail | GET `/validations?type=security` | P2 |
| **Release Center** | Preparação, validação, autorização de release | ReleasePrep, ReleaseApproval, DeployControl | POST `/releases` | P2 |
| **Agent Details (tela completa)** | Tela full-screen do agente (atualmente modal) | AgentDetailPage, AgentHistory, AgentMetrics | GET `/agents/{id}` | P2 |
| **Analytics** | Métricas de desempenho, falhas, produtividade | Analytics dashboard, charts, trends | GET `/metrics` | P2 |

**Componentes reutilizáveis a criar:**
- PaginationControls
- FilterBar (para missions, tasks, executions)
- SearchBox
- SortableTable
- SortableColumn
- Modal/Drawer reutilizável
- DataCard (versão expandida de MetricCard)
- StatusBadge (atualmente inline)

---

## 7. PROPOSTA DE ARQUITETURA DE NAVEGAÇÃO

### Opção 1: Navegação por Domínio (Recomendada)

```
Sidebar Navigation
├─ 📊 Overview           → Dashboard principal
├─ 🕸️  Agent Map         → Topologia e status
├─ 📡 Activity Stream    → Eventos históricos
├─ ─────────────────────── [Separator]
├─ 🎯 Operations         → Submenu:
│  ├─ Missions          → Lista e gerenciamento
│  ├─ Tasks             → Ver e filtrar tarefas
│  └─ Executions        → Acompanhar execuções
├─ ✅ Quality & Security → Submenu:
│  ├─ Validation        → Resultados de QA
│  └─ Security Audit    → Auditoria de segurança
├─ 📚 History           → Submenu:
│  ├─ Mission History   → Histórico pesquisável
│  └─ Analytics         → Métricas e tendências
└─ 🚀 Release           → Controle de release
```

**Vantagens:**
- Organização clara por domínio
- Collapsa submenu em mobile
- Reduz visuais "desordenados"

**Desvantagens:**
- Requer mudança no Sidebar.tsx
- Precisa de collapsa/expand state

---

### Opção 2: Navegação Simples (Atual)

```
Sidebar Navigation
├─ 📊 Overview
├─ 🕸️  Agent Map
├─ 📡 Activity Stream
├─ 🎯 Missions
├─ 📋 Tasks
├─ ⚙️ Executions
├─ ✅ Validation
├─ 📚 History
└─ 🚀 Release
```

**Vantagens:**
- Implementação simples
- Todos os items visíveis sempre
- Fast access

**Desvantagens:**
- Sidebar fica longa (~10+ items)
- Pouco intuitivo em mobile

---

### Opção 3: Tabs + Sidebar Secundário (Avançada)

```
Top Tabs:
├─ Monitoring (Overview, Agent Map, Activity Stream)
├─ Operations (Missions, Tasks, Executions)
├─ Quality (Validation, Security)
└─ Release & Analytics

Sidebar: Exibe items da tab ativa
```

**Vantagens:**
- UX moderna
- Agrupamento lógico

**Desvantagens:**
- Complexidade aumenta
- Descobribilidade reduz

---

**Recomendação:** **Opção 1 (Navegação por Domínio)** é a melhor para gerenciar crescimento da aplicação sem comprometer UX.

---

## 8. PRIORIZAÇÃO P0/P1/P2

### P0 — Problemas que impedem operação

| Item | Descrição | Impacto | Esforço | Blocker |
|------|-----------|--------|--------|---------|
| Activity Stream vazio | Nenhum evento aparece apesar de B5.1 | Impossível auditoria em tempo real | P0-diagnóstico | ✅ |
| Divergência Overview vs. Agent Map | Métricas inconsistentes | Confusão do usuário | P0-clarificação | ✅ |
| WebSocket TODO (AppShell) | "useWebSocket infinite loop" comentado | Live updates não funcionam | P0-fix | ✅ |

**Ação obrigatória antes de continuar:**
1. Diagnosticar Activity Stream (1-2h)
2. Confirmar status das missions criadas em B5.1 (30m)
3. Confirmar WebSocket infinite loop root cause (1-2h)

---

### P1 — Necessário para operação eficiente

| Item | Descrição | Componentes | Esforço | Dependências |
|------|-----------|-----------|---------|-------------|
| **Missions** | Criar, listar, detalhar, filtrar | MissionList, MissionDetail, MissionCreate, MissionFilters | 8-12h | Backend /missions endpoint (✅ existe) |
| **Tasks** | Listar, filtrar, ver detalhes | TaskList, TaskDetail, TaskFilters | 6-8h | Backend /tasks endpoint (✅ existe) |
| **Executions** | Listar, filtrar, ver logs, durations | ExecutionList, ExecutionDetail, LogViewer, DurationChart | 10-14h | Backend /executions endpoint (✅ existe) |
| **Validation Center** | Ver resultados QA + segurança | ValidationResults, ApprovalFlow, AuditTrail | 8-10h | Backend /validations endpoint (✅ existe) |
| **Fix WebSocket** | Resolver infinite loop | useWebSocket hook, AppShell integration | 3-4h | Diagnóstico P0 |
| **Search/Filter** | Pesquisar missions, tasks, executions | SearchBox, FilterBar, SortControls | 6-8h | Reutilizável em todas as telas |

**Total P1:** 41-56 horas de desenvolvimento

---

### P2 — Melhorias e recursos futuros

| Item | Descrição | Componentes | Esforço | Prioridade interna |
|------|-----------|-----------|---------|-----|
| Agent Details (full-page) | Versão completa vs. modal | AgentDetailPage, AgentHistory, AgentMetrics | 6-8h | Baixa |
| Mission History | Histórico pesquisável com filtros | MissionHistoryTable, DateRangePicker, ExportButton | 6-8h | Média |
| Analytics Dashboard | Métricas de desempenho, falhas, tendências | AnalyticsChart, MetricsSummary, TrendIndicators | 10-12h | Média |
| Release Center | Preparação, validação, autorização de release | ReleasePrep, ReleaseApproval, DeployControl | 12-16h | Baixa |
| Security Audit (tela separada) | Audit trail detalhado | AuditTrailTable, AuditFilters, ExportAudit | 6-8h | Baixa |

**Total P2:** 40-52 horas

---

## 9. PLANO INCREMENTAL DE IMPLEMENTAÇÃO

### Fase 0 (Preparação — 4-8 horas)

**Objetivo:** Resolver blockers P0 e preparar infraestrutura

**Tarefas:**
1. ✅ Diagnosticar Activity Stream (Backend query, tenant isolation)
2. ✅ Diagnosticar WebSocket infinite loop (AppShell, useWebSocket hook)
3. ✅ Confirmar status de missions em B5.1
4. ✅ Adicionar SearchBox + FilterBar componentes reutilizáveis
5. ✅ Adicionar SortableTable component
6. ✅ Atualizar Sidebar com submenu (ou preparar para Opção 1)

**Dependências:** Nenhuma (read-only analysis)

**Resultado esperado:**
- P0 issues identificadas e documentadas
- Componentes reutilizáveis prontos
- Plano de fix P0 definido

---

### Fase 1 (Core Features — 40-60 horas)

**Objetivo:** Implementar telas essenciais para operação

**Ordem recomendada:**

1. **Missions (8-12h)** — Alicerce para Tasks e Executions
   - MissionList (GET /missions)
   - MissionDetail (mostrar timeline, tasks, status)
   - MissionCreate (POST /missions)
   - MissionFilters (status, date range)

2. **Tasks (6-8h)** — Rápido, depende de Missions
   - TaskList (GET /tasks)
   - TaskDetail (agent, status, result)
   - TaskFilters (mission, agent, status)

3. **Executions (10-14h)** — Mais complexo, crucial
   - ExecutionList (GET /executions)
   - ExecutionDetail (timeline, logs, durations)
   - LogViewer (mostra error messages)
   - DurationChart (visualiza queue_time, execution_time, etc)

4. **Validation Center (8-10h)** — QA + Security
   - ValidationResults (GET /validations)
   - ApprovalFlow (mostrar status de aprovação)
   - AuditTrail (trace de decisões)

5. **Fix WebSocket (3-4h)** — Habilitar live updates
   - Resolver infinite loop
   - Re-enable em AppShell.tsx:17

6. **Search + Filter (6-8h)** — Reutilizável
   - SearchBox component
   - FilterBar component
   - SortControls

**Dependências:**
- Todas as rotas backend já existem ✅
- Schemas frontend já definem tipos ✅

**Resultado esperado:**
- Operador pode gerenciar missions, tasks, executions
- Dashboard completo para acompanhamento
- Live updates funcionando

---

### Fase 2 (Enhancement — 40-50 horas)

**Objetivo:** Melhorias e recursos futuros

**Ordem:**

1. **Mission History + Analytics (12-16h)**
   - Histórico pesquisável
   - Trends, charts, KPIs
   - Export capabilities

2. **Agent Details (full-page) (6-8h)**
   - Versão completa vs. modal
   - Agent metrics por tenant
   - Agent history

3. **Release Center (12-16h)**
   - Release prep workflow
   - Approval flow
   - Rollback controls

4. **Security Audit (6-8h)**
   - Dedicated audit trail
   - Filter por tipo de evento
   - Export para compliance

**Resultado esperado:**
- Produção ready
- Auditoria e compliance
- Analytics para decisões

---

## 10. DEPENDÊNCIAS DO BACKEND

### Endpoints já implementados e prontos

| Endpoint | Método | Status | Frontend Ready? |
|----------|--------|--------|-----------------|
| `/agents` | GET | ✅ Funciona | ✅ useAgents hook |
| `/agents/{id}` | GET | ✅ Funciona | ⚠️ Não usado |
| `/missions` | GET | ✅ Funciona | ✅ useMissions hook |
| `/missions` | POST | ✅ Funciona (BLOCKER FIX aplicado) | ❌ Not callable |
| `/missions/{id}` | GET | ⚠️ Não verificado | ❌ Não existe |
| `/tasks` | GET | ⚠️ Não verificado | ❌ Não existe |
| `/tasks` | POST | ⚠️ Não verificado | ❌ Não existe |
| `/executions` | GET | ✅ Funciona | ✅ useExecutions hook |
| `/executions/{id}` | GET | ⚠️ Não verificado | ❌ Não existe |
| `/events` | GET | ⚠️ Problemático (vazio) | ⚠️ ActivityStream usa |
| `/validations` | GET | ⚠️ Não verificado | ❌ Não existe |
| `/websocket/ticket` | POST | ✅ Funciona | ✅ useWebSocket usa |

### Endpoints que faltam ou estão incompletos

| Endpoint | Propósito | Status | Ação necessária |
|----------|-----------|--------|-----------------|
| `GET /missions/{id}` | Get mission details | ❌ Falta | Implementar no backend |
| `POST /missions/{id}` | Update mission (status, etc) | ❌ Falta | Implementar no backend |
| `GET /tasks` | List tasks | ⚠️ Talvez exista | Verificar |
| `GET /tasks/{id}` | Task details | ❌ Falta | Implementar no backend |
| `GET /executions/{id}` | Execution details | ❌ Falta | Implementar no backend |
| `GET /validations` | List validations | ⚠️ Talvez exista | Verificar |
| `GET /metrics` | Analytics | ❌ Falta | Implementar no backend |

---

## 11. CRITÉRIOS DE ACEITAÇÃO

### Critério AC-1: Overview — Consistência com Agent Map

**Dado** que Overview exibe "Active Missions" com contagem  
**E** Agent Map exibe "current_mission_id" para agentes  
**Quando** um agente está em status WORKING com mission_id não-nulo  
**Então** Active Missions deve incluir essa missão OU documentar por que não  

**Teste:**
1. Verificar qual status missão possui quando agente a está executando
2. Confirmar que filtro Overview usa status correto
3. Se divergência é esperada, adicionar documentação

---

### Critério AC-2: Activity Stream — Eventos aparecem

**Dado** que B5.1 criou eventos e os persistiu  
**Quando** usuário abre Activity Stream  
**Então** eventos aparecem na timeline com deduplicação correta  

**Teste:**
1. Verificar que `GET /events` retorna eventos
2. Verificar que eventos têm tenant_id correto
3. Verificar que frontend mapeia `created_at` → `timestamp` corretamente
4. Verificar deduplicação com `eventIdsRef`

---

### Critério AC-3: WebSocket — Live updates funcionam

**Dado** que AppShell comentou useWebSocket por infinite loop  
**Quando** loop é resolvido  
**Então** WebSocket deve estar conectado e receber atualizações  

**Teste:**
1. Verificar que useWebSocket não causa re-renders infinitos
2. Verificar que eventos em tempo real chegam ao Activity Stream
3. Verificar que Agent Map atualiza status em tempo real

---

### Critério AC-4: Missions — CRUD funcional

**Dado** que Missions não tem rota no frontend  
**Quando** rota é implementada  
**Então** usuário pode criar, listar, filtrar e ver detalhes de missions  

**Teste:**
1. GET /missions retorna lista paginada
2. POST /missions com payload válido cria mission
3. GET /missions/{id} retorna detalhes
4. Frontend filtra por status, data range, search
5. Paginação funciona (cursor ou page-based)

---

### Critério AC-5: Tasks — Visibilidade completa

**Dado** que Tasks não tem rota no frontend  
**Quando** rota é implementada  
**Então** usuário pode ver todas as tarefas com agent responsável, status, resultado  

**Teste:**
1. GET /tasks retorna lista
2. Task list mostra: mission_id, assigned_agent, status, priority
3. TaskDetail mostra: resultado, erro, timestamps
4. Filtros funcionam (mission, agent, status)

---

### Critério AC-6: Executions — Detalhes e logs

**Dado** que Executions tem endpoint mas sem detalhes completos  
**Quando** ExecutionDetail é implementado  
**Então** usuário vê timeline, durations, logs de erro, resultado  

**Teste:**
1. GET /executions/{id} retorna detalhes completos
2. Frontend exibe: timeline (queued → reserved → started → completed)
3. Frontend exibe: durations (queue_time_ms, execution_time_ms, etc)
4. Frontend exibe: logs (se houver)
5. Frontend exibe: result (JSON ou error message)

---

### Critério AC-7: Validation Center — Aprovações visíveis

**Dado** que Validation Center não tem rota  
**Quando** rota é implementada  
**Então** usuário vê resultados de QA e segurança com aprovação/veto  

**Teste:**
1. GET /validations retorna lista
2. Exibe: tipo (QA, Security, etc), status (PASSED, FAILED, PENDING), resultado
3. Exibe: quem validou, quando, comentários
4. Permite filtro por tipo, status, data

---

### Critério AC-8: Navegação — Sidebar limpo e funcional

**Dado** que Sidebar atualmente tem comentário "prepared for future expansion"  
**Quando** novas telas são adicionadas  
**Então** Sidebar deve ter navegação clara e intuitiva  

**Teste:**
1. Submenu (se Opção 1) exibe items relacionados
2. Collapse/expand não causa perda de scroll
3. Ícones são consistentes e reconhecíveis
4. Mobile: Sidebar collapsa ou drawer
5. Active route está highlighted

---

## CONCLUSÃO

O Command Center frontend está em bom estado estrutural com 3 telas funcionais (Overview, Agent Map, Activity Stream). Há dois problemas críticos (P0) que precisam ser resolvidos:

1. **Activity Stream vazio** — Requer investigação do backend (WebSocketEventLog não tem eventos OU tenant isolation está errada)
2. **WebSocket infinite loop** — Requer diagnóstico do hook `useWebSocket`

As telas P1 (Missions, Tasks, Executions, Validation) podem ser implementadas rapidamente pois os endpoints backend já existem.

A proposta de navegação com submenu (Opção 1) é recomendada para manter UX clara conforme o app cresce.

---

**Relatório concluído.**  
**Próximo passo:** Autorizar investigação dos problemas P0 e escolher primeira etapa de implementação.
