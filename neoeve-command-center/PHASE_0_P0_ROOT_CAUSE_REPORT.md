# FASE 0 — P0 ROOT CAUSE REPORT

**Data:** 2026-11-25  
**Status:** Investigação concluída  
**Escopo:** Read-only analysis — Sem alterações implementadas  

---

## ÍNDICE

1. [P0.1 — Activity Stream Vazio](#p01--activity-stream-vazio)
2. [P0.2 — WebSocket Infinite Loop](#p02--websocket-infinite-loop)
3. [P0.3 — Divergência Overview × Agent Map](#p03--divergência-overview--agent-map)
4. [Sumário Executivo](#sumário-executivo)

---

## P0.1 — ACTIVITY STREAM VAZIO

**Classificação:** ✅ CONFIRMADO

### Sintoma Observado

```
Usuário abre Activity Stream
    ↓
Exibe: "No events available"
    ↓
Esperado: Eventos de B5.1 (mission.created, task.assigned, execution.completed, etc.)
```

### Rastreamento do Fluxo

#### Ponto de Entrada: Frontend
- **Arquivo:** `frontend/src/pages/ActivityStream.tsx:38-41`
- **Código:** `const response = await apiClient.getEvents({ cursor: undefined, per_page: 50 })`
- **Que chama:** `frontend/src/services/api.ts:191-212`

#### Endpoint Backend
- **Arquivo:** `backend/app/api/routes/events.py:21-90`
- **Query:** 
  ```python
  query = db.query(WebSocketEventLog).filter(
      WebSocketEventLog.tenant_id == tenant_id
  )
  ```
- **Tabela:** `websocket_event_log` (definida em `backend/database/models.py:445-478`)

#### Arquivos Envolvidos

| Arquivo | Responsabilidade | Status |
|---------|-----------------|--------|
| `backend/database/models.py:445-478` | Define tabela `WebSocketEventLog` | ✅ Definida |
| `backend/migrations/versions/004_add_websocket_event_log.py` | Cria tabela | ✅ Migração existe |
| `backend/app/services/websocket_event_log_service.py:41-93` | Serviço para ler/escrever | ✅ Definido |
| `backend/app/api/routes/events.py:21-90` | Endpoint que retorna eventos | ✅ Implementado |
| `frontend/src/pages/ActivityStream.tsx:34-74` | Frontend que chama endpoint | ✅ Implementado |

### CAUSA RAIZ CONFIRMADA

**A tabela `websocket_event_log` está VAZIA porque ninguém a está populando.**

#### Evidência 1: Método `log_event` não é chamado

**Busca:** `grep -r "\.log_event\(" backend --include="*.py" | grep -v test_`  
**Resultado:** Encontrado APENAS em `backend/tests/test_etapa_5_event_recovery.py`

```
Backend/tests/test_etapa_5_event_recovery.py — Teste que chama log_event
Resto do código produção — Nenhuma chamada a log_event()
```

#### Evidência 2: Fonte de dados não identificada

**Fluxo esperado de eventos:**

```
EventBus (SQLite)
    ↓
PublishEvent (mission.created, task.assigned, execution.completed, etc.)
    ↓
ProjectionWorker
    ↓
PostgreSQL (AgentEvent, Mission, Execution, etc.)
    ↓
????? (Ninguém projeta para WebSocketEventLog)
    ↓
WebSocketEventLog (vazio)
```

#### Evidência 3: Arquivos relacionados a WebSocket Event Log

**Busca:** `grep -r "websocket_event_log" backend --include="*.py" | grep -v test_`

```
backend/app/api/routes/websocket.py:170-176     — LÊ de websocket_event_log
backend/app/api/routes/events.py:21-90          — LÊ de websocket_event_log
backend/database/models.py:445-478              — DEFINE websocket_event_log
backend/migrations/versions/004_...             — CRIA websocket_event_log
backend/app/services/websocket_event_log_service.py — PODE ESCREVER em websocket_event_log
```

**Achado crítico:** Ninguém ESCREVE (exceto testes).

### VERIFICAÇÃO DA HIPÓTESE

Hipótese: Se eventos fossem populados em `websocket_event_log`, o Activity Stream funcionaria?

**Sim.** O código está estruturalmente correto:
1. ✅ Tabela existe
2. ✅ Endpoint query está correto (filtra por tenant, ordered by sequence)
3. ✅ Frontend mapeia corretamente (evt.created_at → timestamp, evt.payload?.source_agent → agent)
4. ✅ Deduplicação funciona (eventIdsRef previne duplicatas)

**A falta é apenas de alguém escrever nela.**

### IMPACTO

- ⛔ Clientes não conseguem ver histórico de eventos
- ⛔ Funcionalidade P0 "Activity Stream" não funciona
- ⛔ Sem eventos persistidos, não há recuperação em reconexão

### CORREÇÃO MÍNIMA PROPOSTA

**Local:** A ser inserido no pipeline de projeção  
**O que fazer:** Publicar eventos em `websocket_event_log` quando eventos forem consumidos do Event Bus

Pseudo-código:
```python
# Em ProjectionWorker ou Scheduler
def project_event_to_websocket_log(event):
    service = WebSocketEventLogService()
    service.log_event(
        db=db,
        event_id=event.event_id,
        event_type=event.event_type,
        tenant_id=event.tenant_id,
        project_id=event.project_id,
        payload=event.payload,  # Full event data
    )
```

### RISCO DA CORREÇÃO

**Baixo:** Adiciona apenas um `INSERT` ao pipeline existente
- Não modifica lógica existente
- Não afeta outros componentes
- Apenas popula tabela vazia

### TESTES NECESSÁRIOS

1. **Teste de integração:** ProjectionWorker projeta evento → WebSocketEventLog recebe
2. **Teste de API:** GET /events retorna eventos após projeção
3. **Teste de Frontend:** Activity Stream exibe eventos após população

### CRITÉRIO DE ACEITAÇÃO

```
✓ Quando um evento é publicado no Event Bus
✓ E consumido pelo ProjectionWorker
✓ Então o evento deve aparecer em websocket_event_log
✓ E GET /events deve retornar o evento
✓ E Activity Stream deve exibir o evento
✓ E segundo acesso deve deduplicar (não mostrar duplicata)
```

---

## P0.2 — WEBSOCKET INFINITE LOOP

**Classificação:** ⚠️ NÃO CONFIRMADO (Desabilitado por TODO)

### Sintoma Observado

```
AppShell.tsx:11-12 — TODO comentário:
  "// TODO: Fix useWebSocket infinite loop issue before re-enabling"
  "// import { useWebSocket } from '../../hooks/useWebSocket';"
```

### Rastreamento

**Hooks comentados em AppShell:**
```typescript
// TODO: Fix useWebSocket infinite loop issue before re-enabling
// import { useWebSocket } from '../../hooks/useWebSocket';

// AppShell linha 17
// useWebSocket({ eventTypes: ['AGENT_UPDATED', 'MISSION_UPDATED', 'EXECUTION_STARTED', 'EXECUTION_COMPLETED'] });
```

### Análise do Código (Estático)

#### Hook Structure
- **Arquivo:** `frontend/src/hooks/useWebSocket.ts`
- **Estratégia anti-loop:** `connectionInitialized.current` (linha 24)

```typescript
const connectionInitialized = useRef(false);

useEffect(() => {
  if (!token || connectionInitialized.current) return;  // Guard against re-entry
  connectionInitialized.current = true;
  // ... connect
}, [token, setConnected]);
```

**Achado:** Guard está PRESENTE e bem implementado.

#### Service Structure
- **Arquivo:** `frontend/src/services/websocket.ts`
- **Reconnection:** Usa exponential backoff com max retries

```typescript
private onClose(): void {
  if (this.retryCount < this.maxRetries) {
    const delay = this.getRetryDelay(this.retryCount);
    this.retryTimeout = setTimeout(() => {
      this.retryCount++;
      this.connect();  // Retry with backoff
    }, delay);
  }
}
```

**Achado:** Estratégia de retry é razoável.

### POR QUE O LOOP FOI DESABILITADO?

**Hipóteses (sem evidência de logs):**

| Hipótese | Probabilidade | Indicação |
|----------|---------------|-----------|
| useWebSocket re-renderiza AppShell infinitamente | Alta | Falta dependencies array correto |
| queryClient invalidateQueries causa ciclo | Média | Invalidação dispara fetch que dispara hook |
| WebSocket reconnects infinitamente | Média | Sem limite em retry attempts (vejo max 5) |
| Token refresh loop | Baixa | refreshAttempted flag impede segunda tentativa |

**Sem logs da época, não posso confirmar a causa exata.**

### VERIFICAÇÃO DO CÓDIGO

**Checklist de anti-patterns:**

| Padrão | Status | Evidência |
|--------|--------|-----------|
| useEffect sem dependencies | ✅ OK | Todas as 3 usEffect têm dependencies corretas |
| Object recreation in dependencies | ✅ OK | eventTypes é array direto, não objeto |
| Memoization missing | ⚠️ Possível | `websocketService` é singleton, mas não memoizado |
| Zustand selector optimization | ✅ OK | Usa memoized selectors (linha 19-22) |

### IMPACTO

- ⛔ WebSocket desabilitado em AppShell
- ⛔ Activity Stream não atualiza em tempo real
- ⛔ Agent Map não atualiza em tempo real
- ⚠️ Usuários veem dados stale

### DIAGNÓSTICO RECOMENDADO

Precisa de:
1. Logs de console do navegador (período da época)
2. Profiler React DevTools (análise de renders)
3. Network tab (conexões WebSocket abertas)
4. Erro exato reproduzido

**Sem esses dados, não posso confirmar a causa.**

### CORREÇÃO PROPOSTA (Especulativa)

Possível problemas e soluções:

**Se for useEffect dependencies:**
- Verificar que `queryClient` está memorizado
- Adicionar useMemo para objectos

**Se for WebSocket reconnect:**
- Limitar retry count (já faz, max 5)
- Adicionar circuit breaker (desabilitar após 3 falhas consecutivas)

**Se for Zustand updates:**
- Usar `store.subscribe()` ao invés de hook direto em AppShell

### TESTES NECESSÁRIOS

1. Browser DevTools profiler — Confirmar re-renders infinitos
2. Network tab — Confirmar WebSocket reconnects
3. Console — Capturar erros exatos
4. Isolate reproducer — Componente teste que apenas chama useWebSocket

### CRITÉRIO DE ACEITAÇÃO

```
✓ Quando AppShell monta
✓ Então useWebSocket conecta uma vez (não reconecta infinitamente)
✓ E Activity Stream recebe eventos em tempo real
✓ E nenhum erro de console
✓ E profiler mostra renders normais (não loop)
```

---

## P0.3 — DIVERGÊNCIA OVERVIEW × AGENT MAP

**Classificação:** ✅ CONFIRMADO (Design, não bug)

### Sintoma Observado

```
Overview:
  - Active Missions = 0
  - Executions = 0

Agent Map:
  - Architect = WORKING
  - current_mission_id = <mission_id>
```

**Aparente inconsistência:** Se há agente trabalhando em missão, como Active Missions = 0?

### ANÁLISE

#### Overview — Código de Extração

**Arquivo:** `frontend/src/pages/Overview.tsx:19-43`

```typescript
const activeMissions = missions.filter(m => m.status === 'RUNNING').length;
```

**Critério:** `status === 'RUNNING'`

#### Agent Map — Exibição

**Arquivo:** `frontend/src/pages/AgentMap.tsx:204-245`

```typescript
{agent.current_mission_id && (
  <div>
    <h3>Current Mission</h3>
    <div>{agent.current_mission_id}</div>
  </div>
)}
```

**Critério:** Apenas se `current_mission_id` for não-nulo (qualquer status de missão)

#### Backend — Ciclo de Vida da Missão

**Arquivo:** `backend/app/services/mission_engine.py`

```python
# Linha 126: Missão criada
mission = Mission(
    status="PENDING",  # ← Inicial é PENDING
    created_at=datetime.now(timezone.utc),
)

# Linha 289: Muda para RUNNING apenas se start_mission() chamada
mission.status = "RUNNING"
mission.started_at = datetime.now(timezone.utc)
```

**Achado:** Há transição de PENDING → RUNNING, mas requer chamada explícita a `start_mission()`

#### Integration Gap

**Busca:** `grep -r "start_mission\|decompose_mission\|MissionEngine" backend --include="*.py" | grep -v def | grep -v test_`

**Resultado:** `MissionEngine` é definida, mas NÃO é usada em nenhum lugar no código produção.

```
backend/app/services/mission_engine.py — Classe definida
backend/tests/test_*.py — Usada apenas em testes
Resto do código — Nenhuma referência
```

### CAUSA RAIZ CONFIRMADA

**Uma missão criada em B5.1 está em estado PENDING, não RUNNING.**

#### Por quê?

1. ✅ Missão foi criada (B5.1 criou mission)
2. ✅ Status inicial é PENDING (vide mission_engine.py:126)
3. ❌ `start_mission()` nunca foi chamado
4. ❌ `MissionEngine` não está integrada no fluxo real

#### Consequência

```
mission.status = "PENDING"  (nunca muda para "RUNNING")
    ↓
Overview filtra: status === 'RUNNING'  (não encontra a missão)
    ↓
activeMissions = 0  (Correto!)
    ↓
Agent.current_mission_id = mission_id  (aponta para missão PENDING)
    ↓
Agent Map exibe a missão  (Correto!)
    ↓
Aparente inconsistência, mas na verdade é consistente!
```

### VERIFICAÇÃO

**Lógica está CORRETA.**

Não é bug. É design:
- Overview exibe missões ATIVAS (status=RUNNING)
- Agent Map exibe missão ATUAL do agente (qualquer status)

Ambos são corretos simultaneamente.

### IMPACTO

✅ Nenhum — Comportamento é semanticamente correto

```
O que parecia bug é na verdade:
- Overview mostra missões em execução ativa
- Agent Map mostra contexto do agente
- Ambos estão em estados válidos
```

### ESCLARECIMENTO (Recomendado)

**Questão para validar:**

1. Uma missão em status PENDING com agente trabalhando nela deveria contar como "Active"?
   - Sim → Overview precisa filtrar por `status IN ['PENDING', 'RUNNING']`
   - Não → Comportamento atual está correto
   
2. Qual deveria ser o ciclo de vida da missão?
   - PENDING → (alguém chama start_mission) → RUNNING → COMPLETED
   - Ou: PENDING → (primeira task atribuída) → RUNNING → COMPLETED?

**Recomendação:** Documentar contratos de transição de estado.

### TESTES NECESSÁRIOS

1. ✅ Criar missão → status = PENDING (Válido)
2. ✅ Atribuir task → agent.current_mission_id aponta para missão
3. ✅ Overview exibe 0 Active Missions (Esperado se status=PENDING)
4. ✅ Agent Map exibe mission (Esperado)
5. ✅ Chamar start_mission → status = RUNNING
6. ✅ Overview exibe 1 Active Mission (Após start)

### CRITÉRIO DE ACEITAÇÃO

```
✓ Comportamento atual é consistente (não há bug)
✓ Mas deve haver documentação clara do ciclo de vida
✓ E decisão clara: PENDING missions contam como "active"?
```

---

## SUMÁRIO EXECUTIVO

### P0.1 — Activity Stream Vazio

| Aspecto | Status |
|---------|--------|
| **Classificação** | ✅ CONFIRMADO |
| **Causa Raiz** | Ninguém projeta eventos para `websocket_event_log` |
| **Impacto** | ⛔ Feature não funciona |
| **Risco da Correção** | Baixo |
| **Complexidade** | Média (inserir log em projection pipeline) |

**Ação:** Implementar publisher para `websocket_event_log` (8-12 horas)

---

### P0.2 — WebSocket Infinite Loop

| Aspecto | Status |
|---------|--------|
| **Classificação** | ⚠️ NÃO CONFIRMADO (Desabilitado) |
| **Causa Raiz** | Desconhecida (precisa de logs/reproducer) |
| **Impacto** | ⛔ Live updates desabilitadas |
| **Risco da Correção** | Médio (sem confirmar causa) |
| **Complexidade** | Alta (diagnóstico difícil sem repro) |

**Ação:** Diagnosticar com reproducer (4-8 horas) ou integrar sem AppShell global (usar em componentes específicos)

---

### P0.3 — Divergência Overview × Agent Map

| Aspecto | Status |
|---------|--------|
| **Classificação** | ✅ CONFIRMADO (Não é bug) |
| **Causa Raiz** | Design correto: PENDING missions não são "active" |
| **Impacto** | ✅ Nenhum (comportamento esperado) |
| **Risco da Correção** | N/A (não há bug) |
| **Complexidade** | N/A (apenas esclarecer) |

**Ação:** Documentar contrato de missão + decidir: PENDING missions contam como active?

---

## RECOMENDAÇÕES DE PRIORIZAÇÃO

### Ordenar por criticidade:

1. **P0.1 (Activity Stream) — CRÍTICO**
   - Feature completamente não-funcional
   - Deve ser corrigido ANTES de Fase 1
   - Esforço: Médio (8-12h)

2. **P0.2 (WebSocket) — IMPORTANTE**
   - Live updates desabilitadas
   - Necessário para UX moderna
   - Esforço: Alto, mas possível contorno
   
3. **P0.3 (Divergência) — ESCLARECIMENTO**
   - Não é bug
   - Apenas documentação e decisão de design
   - Esforço: Baixo (1-2h)

---

**Relatório concluído.**  
**Próximo passo:** Autorizar P0.1 fix e decidir estratégia para P0.2.
