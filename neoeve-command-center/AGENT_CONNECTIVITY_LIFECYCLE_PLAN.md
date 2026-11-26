# PLANO: Agent Connectivity Lifecycle Integration

**Data:** 2026-11-24  
**Status:** Plano Arquitetural (SEM IMPLEMENTAÇÃO)  
**Escopo:** Design do ciclo de vida correto de conectividade de agentes  

---

## RESUMO EXECUTIVO

**Problema:** Agentes em estado `connectivity_status = "UNKNOWN"`, método de atualização existe mas nunca é chamado.

**Solução Arquitetural:** Integrar updateconnectivity_state() em 5 pontos-chave do ciclo de vida.

**Risco:** Não separar WORKING (operacional) de ONLINE (conectado).

**Implementação:** Mínima invasiva, sem heartbeat artificial.

---

## 1. ARQUITETURA ATUAL

### 1.1 Agent Registry (Registro Central)

**Arquivo:** `backend/app/services/agent_registry.py`

**Responsabilidades:**
- Manter registro estático dos 7 agentes
- Prover métodos de lookup (get_agent, get_agent_by_role, list_agents)
- Validar permissões
- Atualizar estados (OperationalState e ConnectivityState)

**Estados Definidos:**

```python
# OperationalState (o que o agente está FAZENDO)
IDLE = "IDLE"           # Registrado, sem tarefa
WORKING = "WORKING"     # Executando tarefa
ANALYZING = "ANALYZING" # Fase de análise
TESTING = "TESTING"     # Fase de testes
REVIEWING = "REVIEWING" # Fase de revisão
BLOCKED = "BLOCKED"     # Bloqueado (aguardando)
COMPLETED = "COMPLETED" # Tarefa concluída
ERROR = "ERROR"         # Erro na execução

# ConnectivityState (disponibilidade do PROCESSO)
ONLINE = "ONLINE"              # Disponível para receber tarefas
OFFLINE = "OFFLINE"            # Não disponível
STALE = "STALE"                # Sem heartbeat por > N segundos
UNKNOWN = "UNKNOWN"            # Estado desconhecido
NOT_CONFIGURED = "NOT_CONFIGURED"  # Inicial
```

**Métodos Existentes:**
```python
# Atualizar estado operacional
update_operational_state(db, agent_id, state: OperationalState) → bool

# Atualizar estado de conectividade
update_connectivity_state(db, agent_id, state: ConnectivityState) → bool
```

**Status:** ✅ Implementado, mas `update_connectivity_state()` **nunca é chamado**.

### 1.2 Agent Runtime (Executor)

**Arquivo:** `backend/app/services/agent_runtime.py`

**Responsabilidades:**
- Executar tarefas
- Validar agente e permissões
- Gerenciar execuções ativas
- Suporte a recuperação com retries

**Fluxo de Execução:**
```
1. Validação (tenant, project, agent, permission)
2. Health check do adapter (Claude Code CLI)
3. Iniciar execução (logging, profiling)
4. Executar tarefa
5. Capturar resultado (stdout, stderr)
6. Finalizar execução
```

**Status:** ✅ Implementado, MAS sem integração com `update_connectivity_state()`.

### 1.3 Heartbeat (WebSocket)

**Localização:**
- `backend/app/api/routes/websocket.py` (linha 77-159)
- `backend/app/services/websocket_manager.py` (linha 68-71)

**Responsabilidade:** Manter conexão WebSocket viva (cliente ↔ servidor).

**NÃO mantém** agentes ONLINE (escopo diferente).

**Status:** ✅ Implementado para WebSocket, ❌ desconectado de agentes.

### 1.4 Health Check

**Localização:**
- `backend/app/main.py:132` (HTTP endpoint, não para agentes)
- `backend/app/services/claude_code_adapter.py:166` (validar CLI)

**Responsabilidade:** Verificar disponibilidade de executores/infraestrutura.

**NÃO mantém** agentes ONLINE (escopo diferente).

**Status:** ✅ Implementado, ❌ desconectado de agentes.

---

## 2. SEPARAÇÃO CLARA DE CONCEITOS

### CRITICAL: Não Confundir

| Conceito | O Que É | Quem Atualiza | Frequência |
|----------|---------|---|---|
| **status (Operational)** | Fase da tarefa do agente | AgentRuntime.execute_task() | Por tarefa |
| **connectivity_status** | Disponibilidade do agente | ??? (NÃO IMPLEMENTADO) | Contínuo |
| **WebSocket.heartbeat** | Conexão cliente-servidor | WebSocketManager | A cada N seg |
| **health_check()** | Viabilidade de executor | Startup, diagnostics | On-demand |

### Erros Comuns a Evitar

❌ Usar status=WORKING como prova de ONLINE  
❌ Usar WebSocket.connected como prova de agente ONLINE  
❌ Usar health_check() para representar agente ONLINE  
❌ Criar heartbeat falso só para mudar cor do painel  

---

## 3. ESTADOS DO AGENTE — Contrato Proposto

### Transição de Estados

```
REGISTRO
   ↓
[NOT_CONFIGURED] ← Inicial (apenas criado)
   ↓ register_all_agents() chamado
[UNKNOWN] → Padrão quando conectividade não é conhecida
   ↓
[OFFLINE] → Agente registrado mas indisponível
   ↓
[ONLINE] → Agente disponível para receber tarefas
   ↓ tarefa atribuída
[WORKING] ← Operacional (paralelo a ONLINE)
   ↓ tarefa completa
[OFFLINE] ou [ONLINE] ← Volta dependendo de critérios
   ↓
[STALE] ← Sem heartbeat por > timeout
   ↓
[OFFLINE] ← Se stale por muito tempo
```

### Critério de ONLINE

Um agente é ONLINE se:
1. ✅ Registrado em banco (connectivity_status ≠ NOT_CONFIGURED)
2. ✅ Processo acessível (health_check pass)
3. ✅ Recente heartbeat (último < N segundos)
4. ✅ Sem erro crítico (connectivity_status ≠ ERROR)

### Não Confundir com WORKING

WORKING é **o que está FAZENDO**  
ONLINE é **se está DISPONÍVEL**

Um agente pode ser:
- ONLINE + IDLE → Pronto, sem tarefa
- ONLINE + WORKING → Executando
- OFFLINE + IDLE → Não está disponível
- OFFLINE + WORKING → Executação anterior pendente?

---

## 4. PONTOS DE INTEGRAÇÃO

### Ponto 1: Registração Inicial

**Arquivo:** `agent_registry.py:129-141`

**Função:** `register_all_agents(db)`

**Current:**
```python
connectivity_status=ConnectivityState.NOT_CONFIGURED.value
```

**Proposta:** Manter como está (NOT_CONFIGURED = estado inicial, não UNKNOWN).

---

### Ponto 2: Verificação de Saúde (Startup)

**Arquivo:** `main.py:72`

**Current:**
```python
health = adapter.health_check()
```

**Proposta:**
```python
health = adapter.health_check()
if health.get("available"):
    # Atualizar connectivity_status de cada agente
    for agent_config in AgentRegistry.AGENTS.values():
        AgentRegistry.update_connectivity_state(
            db, 
            agent_config["agent_id"], 
            ConnectivityState.ONLINE
        )
```

**Quando:** Startup, endpoint `/health` chamado.

---

### Ponto 3: Início de Execução

**Arquivo:** `api/routes/executions.py:152`

**Current:**
```python
success, stdout, stderr = runtime.execute_task(
    task_id=...,
    agent_id=...,
    ...
)
```

**Proposta (ANTES de execute_task):**
```python
# Atualizar status operacional ANTES
AgentRegistry.update_operational_state(
    db, 
    request.agent_id, 
    OperationalState.WORKING
)

# Executar tarefa
success, stdout, stderr = runtime.execute_task(...)

# Atualizar após conclusão
final_state = OperationalState.COMPLETED if success else OperationalState.ERROR
AgentRegistry.update_operational_state(db, request.agent_id, final_state)
```

**Quando:** A cada execução de tarefa.

---

### Ponto 4: Falha de Conexão

**Arquivo:** Novo — seria em recovery_service ou agentruntime.py

**Proposta:**
```python
if connection_fails:
    AgentRegistry.update_connectivity_state(
        db, 
        agent_id, 
        ConnectivityState.OFFLINE
    )
elif connection_recovers:
    AgentRegistry.update_connectivity_state(
        db, 
        agent_id, 
        ConnectivityState.ONLINE
    )
```

**Quando:** Exceção de conexão, timeout, ou falta de resposta.

---

### Ponto 5: Heartbeat Periódico (Futuro)

**Arquivo:** Novo — seria em scheduler ou background worker

**Proposta (pseudo-código):**
```python
async def heartbeat_monitor():
    """Monitorar heartbeat dos agentes a cada N segundos."""
    while running:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
        
        for agent_id in [a["agent_id"] for a in AgentRegistry.AGENTS.values()]:
            agent = AgentRegistry.get_agent(agent_id, db)
            
            # Se último evento > TIMEOUT
            if (now - agent.last_event_at) > HEARTBEAT_TIMEOUT:
                AgentRegistry.update_connectivity_state(
                    db, 
                    agent_id, 
                    ConnectivityState.STALE
                )
            
            # Se stale por muito tempo, ir para OFFLINE
            if agent.connectivity_status == "STALE" and \
               (now - agent.last_event_at) > OFFLINE_TIMEOUT:
                AgentRegistry.update_connectivity_state(
                    db, 
                    agent_id, 
                    ConnectivityState.OFFLINE
                )
```

**Quando:** Background task, não bloqueante.

---

## 5. DEFINIÇÃO DE HEARTBEAT

### O Que É

**Heartbeat** = `last_event_at` atualizado quando agente faz algo.

**Não é:**
- Ping HTTP periódico (caro)
- WebSocket heartbeat (fluxo diferente)
- Simulação artificial (veta-se criação de eventos falsos)

### Como Implementar

```python
# Toda vez que update_connectivity_state() é chamado:
agent.last_event_at = datetime.now(timezone.utc)
db.commit()
```

**Já implementado em:**
- `update_operational_state()` (linha 224)
- `update_connectivity_state()` (linha 241)

### Timeout Sugerido

```python
HEARTBEAT_TIMEOUT = 60  # segundos (após isso = STALE)
OFFLINE_TIMEOUT = 300   # segundos (após isso = OFFLINE)
```

**Garantia:** Nunca haverá heartbeat falso (pois atualizar status = heartbeat real).

---

## 6. WEBSOCKET — Integração Separada

### Status Atual

✅ WebSocket está implementado  
❌ NÃO está conectado a `update_connectivity_state()`  
❌ Desabilitado por loop React (não escopo aqui)

### Proposta de Integração

**Arquivo:** `websocket.py` (futuro)

```python
# Quando cliente conecta ao WebSocket:
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, ticket: str):
    # ... autenticação do ticket ...
    
    # Atualizar connectivity_status
    actor_id = payload["actor_id"]
    AgentRegistry.update_connectivity_state(
        db, 
        actor_id, 
        ConnectivityState.ONLINE
    )
    
    # ... resto da conexão ...
    
    # Quando desconecta:
    finally:
        AgentRegistry.update_connectivity_state(
            db, 
            actor_id, 
            ConnectivityState.OFFLINE
        )
```

**Quando:** Integração WebSocket (fase 2, após fix de loop React).

---

## 7. ARQUIVOS QUE PRECISARIAM MUDAR

### Necessários (Core)

1. **`backend/app/api/routes/executions.py`**
   - Adicionar `update_operational_state()` antes/depois de execute_task()
   - Verificar linhas 150-162

2. **`backend/app/main.py`**
   - Adicionar inicialização de connectivity_status no health check
   - Verificar linhas 72, 132

3. **`backend/app/services/agent_runtime.py`** (Futuro)
   - Adicionar chamadas a `update_connectivity_state()` em error handling
   - Verificar linhas 70-100 (exceções)

### Opcionais (Futuro)

4. **Novo arquivo: `backend/app/services/agent_heartbeat_monitor.py`**
   - Background task para monitorar STALE → OFFLINE
   - Integração com scheduler

5. **`backend/app/api/routes/websocket.py`** (Futuro)
   - Integração com `update_connectivity_state()` on connect/disconnect
   - Após fix do loop React

---

## 8. TESTES NECESSÁRIOS

### Unit Tests

```python
def test_update_connectivity_state_online():
    """Agente muda para ONLINE após health check."""
    
def test_update_connectivity_state_offline():
    """Agente muda para OFFLINE após falha."""
    
def test_heartbeat_timeout():
    """Agente muda para STALE após N segundos sem evento."""
    
def test_operational_vs_connectivity():
    """Agente pode ser ONLINE+IDLE, ONLINE+WORKING, OFFLINE+IDLE."""
```

### Integration Tests

```python
def test_execution_updates_operational_state():
    """Iniciar execução atualiza status para WORKING."""
    
def test_execution_failure_updates_to_error():
    """Execução falha atualiza status para ERROR."""
    
def test_no_heartbeat_no_online():
    """Sem heartbeat, agente não fica ONLINE (evitar falso positivo)."""
```

### E2E Tests

```python
def test_overview_online_count():
    """Overview mostra agentes ONLINE após health check."""
    
def test_online_disappears_after_timeout():
    """Agente desaparece de ONLINE após heartbeat timeout."""
```

---

## 9. RISCOS E ESTRATÉGIA

### Risco 1: Heartbeat Falso

**Risco:** Criar eventos artificiais para fazer agente parecer ONLINE.

**Estratégia:** Não fazer. Heartbeat = last_event_at atualizado por ação real.

### Risco 2: Confundindo Estados

**Risco:** Usar WORKING como prova de ONLINE.

**Estratégia:** Manter estados separados, testes para evitar.

### Risco 3: Regressão

**Risco:** Quebrar fluxo de execução existente.

**Estratégia:** Mínima invasão. Apenas adicionar calls, não mudar lógica.

### Risco 4: Performance

**Risco:** Background task de heartbeat afeta banco.

**Estratégia:** Usar índices (last_event_at), limitar frequência.

---

## 10. IMPLEMENTAÇÃO FASEADA

### Fase 1 (Core — Semana 1)

✅ Fix registração: NOT_CONFIGURED → (UNKNOWN ou ONLINE)?  
✅ Fix startup health check → atualizar connectivity_status  
✅ Fix execução → update_operational_state antes/depois  
✅ Testes unit  

**Resultado:** Online = X (onde X é número real de agentes saudáveis)

### Fase 2 (Heartbeat — Semana 2)

✅ Background task de heartbeat monitor  
✅ Timeout STALE → OFFLINE  
✅ Testes de timeout  

**Resultado:** Online decresce após inatividade (esperado)

### Fase 3 (WebSocket — Semana 3+)

✅ Fix loop React (habilitar useWebSocket)  
✅ Integrar WebSocket com update_connectivity_state()  
✅ Testes E2E  

**Resultado:** Online = real-time, sincronizado com conexões

---

## 11. DIAGRAMA DE FLUXO

```
                     Agent Registry
                          ↓
                   [NOT_CONFIGURED]
                          ↓
         register_all_agents() / Startup health check
                          ↓
                   [ONLINE/UNKNOWN]
                          ↓
         ┌────────────────┬────────────────┐
         ↓                ↓                ↓
    [Execute]       [No Activity]    [Failure]
      ↓                 ↓                ↓
   [WORKING]       [Timeout N sec]  [OFFLINE]
      ↓                 ↓                
   [IDLE/ERROR]     [STALE]        
      ↓                 ↓
   [ONLINE]        [Timeout M sec]
                        ↓
                    [OFFLINE]
```

---

## 12. RECOMENDAÇÃO FINAL

### NÃO Implementar Ainda

Aguardar aprovação e priorização.

### Pré-Requisito

Resolver loop React (habilitar WebSocket corretamente).

### Mínimo Viável

Implementar apenas Fase 1:
- Fix registração
- Fix startup health check
- Fix execução

**Resultado:** Online = número real de agentes, mudando com execuções.

### Próximo Passo

Apresentar plano ao time, coletar feedback, avaliar impacto em outros sistemas.

---

**Status:** 🔴 Plano Pronto (Aguardando Aprovação)  
**Data:** 2026-11-24  
**Próximo:** Reunião de design para validar com time
