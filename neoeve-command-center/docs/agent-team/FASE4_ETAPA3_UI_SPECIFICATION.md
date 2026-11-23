# UI SPECIFICATION — ETAPA 3
## Nine Screens of NeoEve Command Center

---

## DESIGN PRINCIPLES

- **Premium Dark Mode:** Slate-900 background, slate-800 cards, slate-50 text
- **Professional Engineering Tool:** Clean, minimal, focused on data
- **Real-time Responsiveness:** Updates without delay
- **Clear Hierarchy:** Primary action visible, secondary options grouped
- **Multi-tenant Safe:** No tenant confusion in UI
- **No Simulated Activity:** Every indicator reflects real data

---

## TELA 1: OVERVIEW (Dashboard)

### Objetivo
Central dashboard com status global dos agentes e missões.

### Componentes Principais
1. **Top Row — Key Metrics**
   - Total de agentes
   - Agentes conectados
   - Agentes trabalhando
   - Falhas detectadas (count)

2. **Middle Row — System Status**
   - Missões ativas (count + progresso)
   - Execuções rodando (count)
   - Eventos/min (atualizado via WebSocket)

3. **Bottom Row — Recent Activity**
   - Últimos 5 eventos com timestamp
   - Agente origem
   - Tipo de evento
   - Status (sucesso/falha)

### Dados Necessários
- GET /api/v1/agents (para contagem)
- GET /api/v1/missions (para missões ativas)
- GET /api/v1/events (últimos eventos)
- WebSocket (atualização real-time)

### Critério de Aceite
- [ ] Todos os números vêm de API real
- [ ] Atualização em tempo real via WebSocket
- [ ] Nenhum número inventado
- [ ] Responsivo (mobile + desktop)

---

## TELA 2: AGENT MAP (Topologia)

### Objetivo
Visualizar os 7 agentes e suas relações em tempo real.

### Topologia Proposta (React Flow)
```
              Architect (Central)
              /      |      \
           /         |         \
    Backend        Debugger    QA
    Dev            /              \
         \        /                 \
      Security Auditor      Release Mgr
            |
       OpenAI Validator (externo)
```

### Nodes (Agentes)
Para cada agente mostrar:
1. **Avatar/Icon** — Role específico
2. **Nome + Role**
3. **Status Operacional** (IDLE/WORKING/ANALYZING/TESTING/REVIEWING/BLOCKED/COMPLETED/ERROR)
4. **Conectividade** (ONLINE/OFFLINE/STALE/UNKNOWN) — separada visualmente
5. **Last Event** — timestamp relativo (e.g., "2m ago")
6. **Cor indicativa** — verde (OK), amarelo (working), vermelho (blocked/error)

### Edges (Relações)
- Linhas entre agentes indicando delegação/dependência
- Animação discreta apenas quando há evento ativo
- Nunca animar se não houver atividade real

### Interatividade
- **Click no nó** → Modal com detalhes do agente
- **Detalhe modal:**
  - Nome + role + status
  - Última atividade (timestamp real)
  - Missão/tarefa atual (se houver)
  - Histórico de eventos (últimos 10)
  - Desconectar/reconectar (se aplicável)

### Dados Necessários
- GET /api/v1/agents (todos os 7)
- WebSocket (atualização de status)
- GET /api/v1/events (para "last event")

### Critério de Aceite
- [ ] 7 agentes renderizados
- [ ] Topologia visual clara
- [ ] Sem animação sem evento real
- [ ] Detalhes 100% do backend
- [ ] Responsivo

---

## TELA 3: ACTIVITY STREAM (Timeline)

### Objetivo
Feed de eventos em tempo real com história recuperável.

### Componentes
1. **Filter Bar**
   - Por tipo (dropdown: AGENT_*, MISSION_*, EXECUTION_*, etc)
   - Por agente (dropdown)
   - Por status (sucesso/falha/warning)
   - Intervalo de datas

2. **Timeline (Paginada)**
   - Item por evento
   - Timestamp (absolute + relative)
   - Agente origem
   - Missão/tarefa (se aplicável)
   - Tipo de evento + descrição
   - Status (✓ sucesso / ✗ falha)
   - Badge de impacto (crítico/warning/info)

3. **Pagination**
   - Cursor-based (para recuperação)
   - Botões: "Load More" ou infinite scroll

### Dados Necessários
- GET /api/v1/events (com paginação por cursor)
- WebSocket (novos eventos aparecem no topo)

### Critério de Aceite
- [ ] Eventos 100% do backend
- [ ] Sem eventos inventados
- [ ] Novo evento via WebSocket aparece no topo
- [ ] Paginação por cursor funciona
- [ ] Filtros reais

---

## TELA 4: MISSIONS (Lista)

### Objetivo
Listar todas as missões com status e progresso.

### Componentes
1. **Filtros**
   - Por status (all/active/completed/failed)
   - Por prioridade (high/medium/low)
   - Por agente responsável

2. **Tabela/Grid**
   - ID
   - Objetivo (truncado, com tooltip full)
   - Status + indicador visual
   - Responsável(is)
   - Progresso (%)
   - Data de início / prazo
   - Ações (View Details)

3. **Paginação**
   - Offset-based ou cursor-based (conforme backend)

### Dados Necessários
- GET /api/v1/missions

### Critério de Aceite
- [ ] Dados do backend
- [ ] Sem missões inventadas
- [ ] Link para Mission Details funciona

---

## TELA 5: MISSION DETAILS (Detalhe)

### Objetivo
Detalhe completo de uma missão com tarefas, eventos e progresso.

### Layout
1. **Header**
   - Missão ID
   - Objetivo completo
   - Status + data de criação

2. **Main Content (3 colunas)**
   - **Tasks (esquerda)** — Lista de tarefas, status de cada uma
   - **Progress (centro)** — Barra de progresso, timeline
   - **Events (direita)** — Eventos relacionados a esta missão

3. **Bottom**
   - Responsáveis
   - Dependências
   - Resultado final (se completado)

### Dados Necessários
- GET /api/v1/missions/:id
- GET /api/v1/missions/:id/tasks (ou incluído acima)
- GET /api/v1/events (filtrado por mission_id)
- WebSocket (atualização de tarefas/progresso)

### Critério de Aceite
- [ ] Dados 100% do backend
- [ ] Atualização real-time via WebSocket
- [ ] Responsivo

---

## TELA 6: EXECUTIONS (Histórico)

### Objetivo
Listar histórico de execuções com detalhes e duração.

### Componentes
1. **Filtros**
   - Por agente
   - Por missão
   - Por status
   - Intervalo de datas

2. **Tabela**
   - Execution ID
   - Agente executor
   - Missão + tarefa
   - Status (success/failure/timeout)
   - Duração (se backend tiver) ou "—"
   - Timestamp
   - Ações (View Logs, View Result)

### Dados Necessários
- GET /api/v1/executions

### Critério de Aceite
- [ ] Dados do backend
- [ ] Sem execuções inventadas
- [ ] Duração vem do backend (ou mostrar "—" se não disponível)

---

## TELA 7: VALIDATION CENTER

### Objetivo
Resultados de validações (QA, Security, OpenAI).

### Componentes
1. **Tabs**
   - QA Results
   - Security Audits
   - OpenAI Validator

2. **QA Results**
   - Lista de testes
   - Status (pass/fail/skipped)
   - Coverage %
   - Detalhes

3. **Security Audits**
   - Vulnerabilidades encontradas (se houver)
   - Severidade (critical/high/medium/low)
   - Status (open/resolved)

4. **OpenAI Validator**
   - Status (ONLINE/OFFLINE/UNKNOWN/ERROR)
   - Último resultado
   - Timestamp
   - Próxima validação agendada (se houver)

### Dados Necessários
- GET /api/v1/validations (ou resources específicos por tipo)
- Status do OpenAI Validator (como determinar?)

### Critério de Aceite
- [ ] Nunca simular aprovação do OpenAI Validator
- [ ] Mostrar status real (OFFLINE/UNKNOWN se não disponível)
- [ ] Dados de QA/Security do backend

---

## TELA 8: MISSION HISTORY

### Objetivo
Histórico agregado de mudanças em missões.

### Componentes
1. **Timeline**
   - Mudança de status
   - Atribuição de responsável
   - Progresso atualizado
   - Tarefa completa/falha
   - Evento importante

2. **Filtros**
   - Por tipo de mudança
   - Por agente/usuário que fez
   - Intervalo de datas

### Dados Necessários
- GET /api/v1/missions/:id/history ou GET /api/v1/events (filtrado por type + mission_id)

### Critério de Aceite
- [ ] Histórico recuperado do backend
- [ ] Ordem cronológica correta
- [ ] Sem mudanças inventadas

---

## TELA 9: SETTINGS

### Objetivo
Configurações do Command Center.

### Componentes
1. **Preferências Visuais**
   - Theme (já implementado em Zustand)
   - Sidebar collapsible (já implementado)

2. **Configurações de Conexão**
   - Backend URL (read-only, do env)
   - WebSocket status
   - Teste de conexão

3. **Dados do Usuário** (se aplicável)
   - Tenant ID (read-only)
   - Role
   - Último login

### Regra
- Apenas configurações que tenham implementação real no backend
- Não criar settings ornamentais sem propósito

### Critério de Aceite
- [ ] Configurações funcionam
- [ ] Nenhuma setting fake

---

## COMPONENTES REUTILIZÁVEIS (Estender ETAPA 2)

### Novos Componentes Necessários
1. **Chart Component** — Wrapper para gráficos (Recharts/Chart.js)
2. **Timeline Component** — Para eventos/histórico
3. **Status Badge** — Para operacional + conectividade
4. **Agent Node** — Componente do React Flow
5. **Event Card** — Para activity stream
6. **Metric Panel** — Para dashboard (estender MetricCard)

---

## PADRÕES DE INTERAÇÃO

1. **Carregamento** — LoadingState (já existe)
2. **Erro** — ErrorState com retry (já existe)
3. **Vazio** — EmptyState (já existe)
4. **Real-time Update** — Badge "New" ou highlight
5. **Seleção** — Modal ou painel lateral

---

## TIPOGRAFIA E ESPAÇAMENTO

- **Heading:** text-2xl font-bold (títulos de tela)
- **Subheading:** text-lg font-semibold
- **Body:** text-sm text-slate-400
- **Mono:** font-mono (IDs, timestamps)
- **Spacing:** 4px grid (Tailwind)

---

## Responsividade

- **Desktop (1024px+):** Layout completo, múltiplas colunas
- **Tablet (768px-1023px):** 2 colunas, collapsed sidebar
- **Mobile (<768px):** 1 coluna, full-width, hamburger menu

---

**Status:** 🟡 ESPECIFICAÇÃO INICIAL  
**Responsável:** Architect + Frontend Engineer  
**Próximo:** Revisão com Backend Contract Audit completo
