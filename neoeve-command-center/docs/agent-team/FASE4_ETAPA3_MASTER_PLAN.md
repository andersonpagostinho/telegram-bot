# FASE 4 — ETAPA 3 — MASTER PLAN
## NeoEve Command Center — UI Implementation

**Data:** 2026-11-22  
**Base:** Checkpoint 98c1899 (ETAPA 2 completa)  
**Objetivo:** Implementar as 9 telas do Command Center com dados reais dos agentes

---

## 1. ESTADO ATUAL (Auditado em 2026-11-22)

### Fundação ETAPA 2 ✅ COMPLETA
- ✅ React 18 + TypeScript strict mode
- ✅ Vite + HMR (port 5173)
- ✅ React Router com 9 rotas planejadas
- ✅ TanStack Query (caching + invalidation)
- ✅ WebSocket service (reconnection + cursor recovery)
- ✅ Zustand stores (3: auth, websocket, ui)
- ✅ 11 componentes layout + reusable
- ✅ 4 custom hooks (useAgents, useMissions, useExecutions, useWebSocket)
- ✅ 159 testes estruturalmente válidos
- ✅ Tailwind CSS dark theme
- ✅ Documentação completa (README + ARCHITECTURE)

### Arquivos Existentes (40 total)
- **Componentes:** 11 (layout: 5, common: 6)
- **Services:** 3 (api, websocket, errors)
- **Hooks:** 4 (data fetching + WebSocket)
- **Stores:** 3 (Zustand)
- **Types:** 2 (api, store)
- **Pages:** 2 (Overview stub, NotFound)
- **Config:** 8 (vite, tsconfig, tailwind, etc)
- **Docs:** 2 (README, ARCHITECTURE)

### Rotas Planejadas (9 total)
1. / → Overview
2. /agents → Agent Map
3. /activity → Activity Stream
4. /missions → Missions
5. /missions/:id → Mission Details
6. /executions → Executions
7. /validation → Validation Center
8. /history → Mission History
9. /settings → Settings

---

## 2. DEPENDÊNCIAS TÉCNICAS

### Backend (Requer Auditoria Real)
⚠️ **PENDENTE:** Verificação real dos endpoints, schemas e contratos

Pressupostos baseados em PHASE_4_BACKEND_FORENSIC_AUDIT.md:
- GET /api/v1/agents — Lista agentes com paginação
- GET /api/v1/missions — Lista missões
- GET /api/v1/executions — Lista execuções
- WebSocket /api/v1/websocket/ws — Eventos em tempo real
- Eventos: AGENT_UPDATED, MISSION_UPDATED, EXECUTION_STARTED, etc.
- Cursor-based recovery para reconexão

### React Flow
- Deve ser instalado para Agent Map (ainda não adicionado a package.json)
- Liberdade para usar Chart.js, Recharts ou similar para métricas

### Dados Reais Necessários
✅ Autenticação JWT (já implementada)
⚠️ Agentes reais (7 conforme especificado)
⚠️ Missões reais (backend deve ter)
⚠️ Execuções reais (backend deve ter)
⚠️ Eventos reais (WebSocket deve ter)

---

## 3. GOVERNANÇA E RESPONSABILIDADES

### 7 Agentes
1. **Architect** — Tech Lead (Central)
2. **Backend Developer** — Implementação de backend quando delegado
3. **Debugger** — Investigação e correção
4. **QA Engineer** — Testes e evidências
5. **Security Auditor** — Auditoria e veto de vulnerabilidades
6. **Release Manager** — Preparação e controle
7. **OpenAI Validator** — Validação externa (integração real ⚠️ PENDENTE)

### Separação de Responsabilidades
- **Architect:** Revisa arquitetura, aprova contratos, define padrões
- **Backend Dev:** Modifica backend APENAS se autorizado pelo Architect
- **Debugger:** Investiga falhas, propõe correções
- **QA:** Valida requisitos, executa testes, assina evidências
- **Security:** Revisa segurança, bloqueia vulnerabilidades críticas
- **Release Mgr:** Coordena milestones, controla qualidade de release
- **OpenAI Validator:** Validação independente (status atual: UNKNOWN)

---

## 4. REGRAS INEGOCIÁVEIS (ETAPA 3)

🚫 **Proibido:**
- Inventar dados (usar apenas backend real)
- Inventar endpoints
- Simular atividade de agentes
- Simular aprovações (esp. OpenAI Validator)
- Misturar tenants
- Alterar lógica operacional da NeoEve
- Quebrar infraestrutura ETAPA 2
- Refatorar sem evidência
- Push ou deploy

✅ **Obrigatório:**
- Usar dados reais do backend
- Respeitar isolamento multi-tenant
- Testes automatizados (TDD)
- Auditoria de segurança antes de merge
- Documentação de mudanças
- Commits atómicos com evidências

---

## 5. MATRIZ DAS 9 TELAS

| # | Tela | Componentes Necessários | Dados Backend | WebSocket | Prioridade |
|---|------|------------------------|---------------|-----------| ---|
| 1 | Overview | Métricas, cards, stats | Agentes, missões | Sim | P1 |
| 2 | Agent Map | React Flow, nodes, edges | Agentes + relações | Sim | P1 |
| 3 | Activity Stream | Timeline, eventos, filtros | Eventos | Sim | P1 |
| 4 | Missions | Lista, paginação, filtros | Missões | Não | P2 |
| 5 | Mission Details | Painel, tasks, eventos | Missão + tarefas | Sim | P2 |
| 6 | Executions | Tabela, histórico | Execuções | Sim | P2 |
| 7 | Validation | Resultados, auditorias | Validações | Não | P3 |
| 8 | Mission History | Timeline, mudanças | Histórico | Não | P3 |
| 9 | Settings | Form, preferências | Config do usuário | Não | P3 |

---

## 6. FLUXO DE DADOS

### REST (TanStack Query)
```
API Endpoint → HTTP Client (axios) → Error Normalization → TanStack Query
    ↓
Cache (5min stale, 10min GC)
    ↓
Hook (useAgents, useMissions, etc)
    ↓
React Component (renderização)
```

### WebSocket (Real-time)
```
Backend Event → WebSocket Service → Event Deduplication → Zustand (connection state)
    ↓
useWebSocket Hook (cache invalidation)
    ↓
TanStack Query Invalidation
    ↓
Component Re-render com dados atualizados
```

---

## 7. FASES PROPOSTAS (ETAPA 3)

### FASE 3.1 — Design System & Components (P0)
- Estender Tailwind para componentes específicas (gráficos, timelines)
- React Flow setup
- Componentes para métrica (chart wrappers)
- Testes de estrutura

### FASE 3.2 — Overview (P1)
- Dashboard com métricas (agentes, missões, execuções, falhas)
- Cards com dados real-time
- WebSocket para atualização

### FASE 3.3 — Agent Map (P1)
- Topologia de agentes com React Flow
- 7 agentes: Architect central, 6 em volta
- Estados + conectividade visível
- Seleção com detalhes

### FASE 3.4 — Activity Stream (P1)
- Timeline de eventos
- Paginação com cursor
- Filtros por tipo/agente/missão
- Real-time updates via WebSocket

### FASE 3.5 — Missions & Details (P2)
- Lista de missões
- Detalhe com tarefas e eventos
- Progresso visual

### FASE 3.6 — Executions (P2)
- Histórico de execuções
- Duração + logs (conforme backend)
- Filtros por agente/missão

### FASE 3.7 — Validation Center (P3)
- Resultados de QA
- Auditorias de segurança
- Status OpenAI Validator

### FASE 3.8 — History & Settings (P3)
- Histórico de mudanças
- Configurações de usuário
- Preferências visuais

### FASE 3.9 — Integration & Polish (P4)
- E2E testing
- Performance tuning
- Segurança final
- Documentação

---

## 8. CRITÉRIOS DE ACEITE

Cada tela deve ter:
- ✅ Dados 100% reais do backend
- ✅ Sem dados inventados ou hardcoded
- ✅ WebSocket integrado (se aplicável)
- ✅ Responsividade (mobile + desktop)
- ✅ Testes (componentes + integração)
- ✅ TypeScript strict (100% tipado)
- ✅ Acessibilidade básica (WCAG AA)
- ✅ Sem vulnerabilidades (SecurityAuditor aprova)
- ✅ Documentação de componentes

---

## 9. RISCOS E BLOQUEADORES

### Riscos Identificados
1. **Backend Gap** — Contrato real desconhecido ⚠️ Requer auditoria
2. **OpenAI Validator** — Integração desconhecida ⚠️ Pode ser OFFLINE
3. **Performance** — 7 agentes + eventos contínuos = carga
4. **WebSocket Stability** — Reconexão em produção (testar bem)
5. **Data Consistency** — Multi-tenant isolamento crítico

### Bloqueadores Potenciais
- Backend não implementado (endpoints faltando)
- WebSocket instável em produção
- OpenAI Validator não acessível
- Performance inaceitável em mobile

---

## 10. PRÓXIMOS PASSOS

1. ✅ **Auditoria do Backend Real** (documento FASE4_ETAPA3_BACKEND_CONTRACT_AUDIT.md)
2. ✅ **Especificação UI** (documento FASE4_ETAPA3_UI_SPECIFICATION.md)
3. ✅ **Roadmap Executável** (documento FASE4_ETAPA3_EXECUTION_ROADMAP.md)
4. ⏳ **FASE 3.1:** Design System
5. ⏳ **FASE 3.2+:** Implementação das telas

---

**Status:** 🟡 PLANEJAMENTO EM ANDAMENTO  
**Checkpoint:** 98c1899  
**Versão:** Plano Inicial  
**Próximo:** Auditoria do Backend Real
