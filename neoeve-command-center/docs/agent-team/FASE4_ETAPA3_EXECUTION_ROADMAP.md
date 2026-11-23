# EXECUTION ROADMAP — ETAPA 3
## Fases de Implementação das 9 Telas

**Base:** Checkpoint 98c1899  
**Duração Estimada:** 4-6 semanas  
**Equipe:** 7 agentes (Architect, Backend Dev, Debugger, QA, Security, Release Mgr, OpenAI Validator)

---

## FASES E SEQUÊNCIA

### FASE 3.1 — Design System & Foundation (P0)
**Duração:** 3-5 dias  
**Responsável:** Architect + Frontend Engineer  

**Objetivos:**
- [ ] Estender Tailwind para componentes específicas
- [ ] Setup React Flow (Agent Map)
- [ ] Chart wrapper component (Recharts ou Chart.js)
- [ ] Timeline component
- [ ] Status badge (separar estado operacional + conectividade)
- [ ] Testes de estrutura

**Deliverables:**
- component/charts/ChartWrapper.tsx
- components/timeline/Timeline.tsx
- components/status/StatusBadge.tsx (aprimorado)
- components/flow/AgentNode.tsx
- 10+ testes

**Critério GO:** Componentes prontos, sem dados reais necessários

---

### FASE 3.2 — Overview Dashboard (P1)
**Duração:** 4-6 dias  
**Responsável:** Frontend Engineer + QA  
**Dependências:** FASE 3.1 ✓

**Objetivos:**
- [ ] Dashboard com 4 métricas principais
- [ ] Recent activity list (últimos 5 eventos)
- [ ] Real-time updates via WebSocket
- [ ] Responsivo

**Dados Necessários:**
- GET /api/v1/agents (count)
- GET /api/v1/missions (count + active)
- GET /api/v1/events (últimos)
- WebSocket events

**Arquivos:**
- pages/Overview.tsx (expandir)
- hooks/useDashboardMetrics.ts (novo)
- __tests__/Overview.test.tsx

**Critério GO:** 
- [ ] Todos os números do backend real
- [ ] WebSocket updating metrics
- [ ] TypeScript strict
- [ ] 5+ testes PASS
- [ ] QA sign-off

---

### FASE 3.3 — Agent Map (P1)
**Duração:** 7-10 dias  
**Responsável:** Frontend Engineer + Architect  
**Dependências:** FASE 3.1 ✓

**Objetivos:**
- [ ] Topologia visual dos 7 agentes
- [ ] React Flow setup
- [ ] Status + conectividade visível
- [ ] Click node → modal com detalhes
- [ ] Real-time updates

**Dados Necessários:**
- GET /api/v1/agents (todos)
- WebSocket (status updates)

**Arquivos:**
- pages/AgentMap.tsx
- components/flow/AgentFlowChart.tsx
- components/flow/AgentNode.tsx
- components/flow/AgentDetailModal.tsx
- hooks/useAgentTopology.ts (novo)
- __tests__/AgentMap.test.tsx

**Critério GO:**
- [ ] 7 agentes renderizados corretamente
- [ ] Topologia visual clara (Architect central)
- [ ] Real-time updates
- [ ] Security audit PASS
- [ ] QA sign-off

---

### FASE 3.4 — Activity Stream (P1)
**Duração:** 5-7 dias  
**Responsável:** Frontend Engineer + QA  
**Dependências:** FASE 3.1 ✓

**Objetivos:**
- [ ] Timeline de eventos
- [ ] Filtros (tipo, agente, status)
- [ ] Paginação por cursor
- [ ] Real-time novos eventos

**Dados Necessários:**
- GET /api/v1/events (com cursor)
- WebSocket (novos eventos)

**Arquivos:**
- pages/ActivityStream.tsx
- components/ActivityFilterBar.tsx
- components/ActivityTimeline.tsx
- hooks/useEventStream.ts (novo)
- __tests__/ActivityStream.test.tsx

**Critério GO:**
- [ ] Eventos do backend real
- [ ] Sem eventos inventados
- [ ] Cursor pagination funciona
- [ ] Novo evento via WebSocket aparece
- [ ] QA sign-off

---

### FASE 3.5 — Missions & Details (P2)
**Duração:** 7-10 dias  
**Responsável:** Frontend Engineer + QA  
**Dependências:** Nenhuma crítica

**Objetivos:**
- [ ] Missions list page
- [ ] Mission details page
- [ ] Tarefas e eventos relacionados
- [ ] Progresso visual

**Dados Necessários:**
- GET /api/v1/missions
- GET /api/v1/missions/:id
- GET /api/v1/missions/:id/tasks
- GET /api/v1/events (filtrado por mission_id)

**Arquivos:**
- pages/Missions.tsx (expandir)
- pages/MissionDetails.tsx
- components/MissionCard.tsx
- components/TaskList.tsx
- components/MissionEvents.tsx
- hooks/useMissionDetail.ts (novo)

**Critério GO:**
- [ ] 100% dados do backend
- [ ] Real-time updates (tarefas/progresso)
- [ ] QA sign-off

---

### FASE 3.6 — Executions (P2)
**Duração:** 4-6 dias  
**Responsável:** Frontend Engineer + QA  
**Dependências:** Nenhuma crítica

**Objetivos:**
- [ ] Executions list page
- [ ] Histórico com duração (se disponível)
- [ ] Filtros e paginação

**Dados Necessários:**
- GET /api/v1/executions

**Arquivos:**
- pages/Executions.tsx (expandir)
- components/ExecutionTable.tsx
- hooks/useExecutionList.ts (novo)

**Critério GO:**
- [ ] Dados do backend
- [ ] Duração: usar se houver, mostrar "—" se não
- [ ] QA sign-off

---

### FASE 3.7 — Validation Center (P3)
**Duração:** 5-7 dias  
**Responsável:** Frontend Engineer + Security Auditor  
**Dependências:** Nenhuma crítica (OpenAI status: UNKNOWN/OFFLINE é aceitável)

**Objetivos:**
- [ ] Tabs para QA, Security, OpenAI Validator
- [ ] Nunca simular aprovação
- [ ] Mostrar status real

**Dados Necessários:**
- GET /api/v1/validations (ou resources específicos)
- Status do OpenAI Validator (como determinar?)

**Arquivos:**
- pages/ValidationCenter.tsx
- components/QAResults.tsx
- components/SecurityAudits.tsx
- components/OpenAIValidatorStatus.tsx

**Critério GO:**
- [ ] Nunca simula aprovação
- [ ] Status OpenAI Validator = real (OFFLINE/UNKNOWN é ok)
- [ ] Security Auditor aprova
- [ ] QA sign-off

---

### FASE 3.8 — History & Settings (P3)
**Duração:** 3-5 dias  
**Responsável:** Frontend Engineer + QA  
**Dependências:** Nenhuma

**Objetivos:**
- [ ] Mission History timeline
- [ ] Settings page (apenas config com implementação real)

**Dados Necessários:**
- GET /api/v1/missions/:id/history ou eventos filtrados

**Arquivos:**
- pages/MissionHistory.tsx
- pages/Settings.tsx (aprimorar)

**Critério GO:**
- [ ] Histórico do backend real
- [ ] Settings sem ornamentação fake
- [ ] QA sign-off

---

### FASE 3.9 — Integration & Polish (P4)
**Duração:** 7-10 dias  
**Responsável:** Toda equipe  
**Dependências:** FASES 3.2-3.8 ✓

**Objetivos:**
- [ ] E2E testing (9 telas)
- [ ] Performance tuning
- [ ] Security audit completo
- [ ] Documentação final
- [ ] Preparação para produção

**Critério GO:**
- [ ] 90%+ E2E tests PASS
- [ ] Performance <2s por página
- [ ] Security Auditor aprova
- [ ] Release Manager GO

---

## TIMELINE RESUMIDA

```
FASE 3.1 ——— Design System (3-5d)
  └→ FASE 3.2 ——— Overview (4-6d) →→→ FASE 3.5 ——— Missions (7-10d) →→→ FASE 3.9 ——— Polish (7-10d)
  └→ FASE 3.3 ——— Agent Map (7-10d) ↓
  └→ FASE 3.4 ——— Activity Stream (5-7d) →→ FASE 3.6 ——— Executions (4-6d) ↑
  └→ FASE 3.7 ——— Validation (5-7d)
  └→ FASE 3.8 ——— History/Settings (3-5d)

Total Estimado: 46-70 dias de trabalho (~7-10 semanas)
```

---

## BLOCKERS POTENCIAIS

1. **Backend Gaps** ⚠️ — Contratos não implementados
2. **OpenAI Validator Integração** — Status desconhecido
3. **WebSocket Instabilidade** — Em produção
4. **Performance** — 7 agentes + eventos contínuos
5. **React Flow Complexidade** — Agent Map pode ser complexa

---

## GOVERNANÇA POR FASE

### FASE 3.1
- [ ] Architect aprova design
- [ ] Security Auditor valida componentes

### FASES 3.2-3.8
- [ ] Frontend Engineer implementa
- [ ] QA testa + assina
- [ ] Security Auditor valida (anualmente)
- [ ] Debugger disponível para investigação

### FASE 3.9
- [ ] QA lidera E2E
- [ ] Security Auditor bloqueia vulnerabilidades críticas
- [ ] Release Manager coordena
- [ ] OpenAI Validator (status real apenas)

---

## PRÓXIMO PASSO

✅ **Auditoria do Backend Real** (documento FASE4_ETAPA3_BACKEND_CONTRACT_AUDIT.md)

Depois de confirmar todos os contratos do backend:
1. Revisar e ajustar UI_SPECIFICATION.md
2. Ajustar EXECUTION_ROADMAP.md se necessário
3. Iniciar FASE 3.1 com Architect + Frontend Engineer

---

**Status:** 🟡 ROADMAP PLANEJADO  
**Próximo:** Backend Contract Audit (real)  
**GO/NO-GO:** Aguardando confirmação dos contratos do backend
