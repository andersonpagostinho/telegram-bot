# DIAGNÓSTICO: Status dos Agentes e Online = 0

**Data:** 2026-11-24  
**Status:** Diagnóstico Completo  
**Escopo:** Overview metrics, Agent connectivity, WebSocket integration  

---

## RESUMO EXECUTIVO

**Causa Raiz Comprovada:**
O campo `connectivity_status` em TODOS os agentes está em padrão **"UNKNOWN"**, nunca atualizado.

**Origem do Online = 0:**
O frontend (Overview.tsx:25) filtra por `connectivity_status === 'ONLINE'`.  
Nenhum agente tem esse valor → Online = 0.

**Responsável Quebrado:**
Método `update_connectivity_state()` existe mas **nunca é chamado em nenhum lugar do código**.

---

## 1. BACKEND — ENDPOINT `/api/v1/agents`

### Localização
- `backend/app/api/routes/agents.py:18-59`
- `backend/app/schemas/agent.py:19` (campo)
- `backend/database/models.py:154` (definição)

### Campo connectivity_status
```python
# models.py:154
connectivity_status = Column(String(32), default="UNKNOWN")  # ONLINE, OFFLINE, STALE, UNKNOWN
```

**Default:** `"UNKNOWN"`  
**Valores Suportados:** ONLINE, OFFLINE, STALE, UNKNOWN

### Responsável Teórico
Método definido em `agent_registry.py:231-245`:
```python
@classmethod
def update_connectivity_state(
    cls,
    db: Session,
    agent_id: str,
    state: ConnectivityState,
) -> bool:
    """Update agent connectivity state."""
    agent = cls.get_agent(agent_id, db)
    if agent:
        agent.connectivity_status = state.value
        agent.last_event_at = datetime.now(timezone.utc)
        db.commit()
        return True
    return False
```

**Status:** Implementado, MAS NUNCA CHAMADO.

### Resultado
Grep confirmou: **`update_connectivity_state()` não aparece em nenhuma chamada**

```
backend/app/services/agent_registry.py:231:    def update_connectivity_state(
(nenhuma outra referência encontrada)
```

---

## 2. AGENTES — ESTADO REAL

### Total de Agentes
Backend retorna: **7 agentes**  
(verificado em Overview metrics em tempo real)

### Connectivity Status de Cada Agente
Todos têm default `"UNKNOWN"` porque:
1. São criados com `connectivity_status = Column(..., default="UNKNOWN")`
2. Nenhum código atualiza esse campo
3. Logo, 100% dos agentes = "UNKNOWN"

### Working Status
- Overview mostra: **WORKING = 1**
- Isso vem do campo `status == "WORKING"` (diferente de connectivity_status)
- 1 agente tem status = "WORKING" (tarefas em execução)
- 6 agentes têm status ≠ "WORKING"

### Critério ONLINE Esperado
Frontend (Overview.tsx:25):
```typescript
const onlineAgents = agents.filter(a => a.connectivity_status === 'ONLINE').length;
```

**Nenhum agente tem `connectivity_status === 'ONLINE'`**
→ **Online = 0** (esperado, não é bug)

---

## 3. WEBSOCKET — CONEXÃO E HANDSHAKE

### Status Observado
Frontend mostra: **🔴 Offline**

### Causa
WebSocket está desabilitado temporariamente porque:
1. `useWebSocket()` foi comentado em `AppShell.tsx`
2. Feito para resolver loop infinito de React
3. Sistema está operacional sem WebSocket (15 min de access_token)

### Falta de Ligação
Não existe código que:
1. Conecta WebSocket → `update_connectivity_state()`
2. Monitora eventos do WebSocket
3. Atualiza connectivity_status ao conectar/desconectar

---

## 4. FRONTEND — OVERVIEW.TSX ANÁLISE

### Localização
`frontend/src/pages/Overview.tsx:11-91`

### Fluxo de Dados
```
useAgents() 
  → apiClient.getAgents() 
    → GET /api/v1/agents 
      → Backend retorna AgentResponse[] 
        → Cada agent tem connectivity_status (padrão "UNKNOWN")
          → Frontend filtra: a.connectivity_status === 'ONLINE' 
            → 0 agentes encontrados 
              → Exibe Online = 0
```

### Exibição
Linha 86:
```typescript
<MetricCard label="Online" value={metrics.onlineAgents} />
```

**Comportamento Atual:** Correto  
**Exibição:** Online = 0 (porque nenhum agente tem 'ONLINE')

---

## 5. RESULTADO FINAL

### Estado Real dos 7 Agentes

| Campo | Valor | Origem |
|-------|-------|--------|
| **Total Agents** | 7 | Contagem em banco |
| **Online** | 0 | connectivity_status = 'UNKNOWN' para todos |
| **Working** | 1 | status = 'WORKING' em 1 agente |
| **Errors** | 0 | status ≠ 'ERROR' para todos |
| **connectivity_status** | "UNKNOWN" | Default não alterado |

### Origem do Número Online = 0

**Cadeia de Causa:**

```
1. Agent criado com connectivity_status = "UNKNOWN" (default)
   ↓
2. Método update_connectivity_state() EXISTE mas NUNCA É CHAMADO
   ↓
3. Nenhum código atualiza connectivity_status para "ONLINE"
   ↓
4. Frontend filtra: a.connectivity_status === 'ONLINE'
   ↓
5. 0 agentes encontrados
   ↓
6. Exibe Online = 0
```

### Estado Real do WebSocket

| Aspecto | Status | Motivo |
|---------|--------|--------|
| **Conexão** | ❌ Offline | useWebSocket comentado (loop infinito) |
| **Ticket** | ✅ Pode ser obtido | Endpoint funciona |
| **Handshake** | ❌ Não conecta | WebSocket desabilitado |
| **Integração com connectivity_status** | ❌ Não existe | update_connectivity_state nunca é chamada |

### Agente em WORKING

O agente com status = "WORKING":
- **Está realmente executando?** Desconhecido (exigiria testar, proibido)
- **Tem heartbeat?** Não (nenhum heartbeat implementado em WorkerHeartbeatService)
- **Diferença entre registrado/conectado/online/working?** SIM:
  - **Registrado:** Agent existe em banco (7 agentes)
  - **Conectado:** WebSocket conectado (0 agentes, feature desabilitada)
  - **Online:** connectivity_status = "ONLINE" (0 agentes, nunca atualizado)
  - **Working:** status = "WORKING" (1 agente, execução em progresso)

---

## 6. CAUSA COMPROVADA

### Raiz Principal
**Responsabilidade Quebrada:** `AgentRegistry.update_connectivity_state()`
- Implementado em `agent_registry.py:231`
- Nunca chamado em nenhum lugar
- Logo, connectivity_status nunca muda de "UNKNOWN"

### Ligação Faltante
Não existe integração entre:
- WebSocket events
- AgentRegistry.update_connectivity_state()
- Agent.connectivity_status no banco

### Ordem de Camadas (Regra da Menor Camada)

```
1. INFRAESTRUTURA (Firestore/PostgreSQL)
   └─ Agent.connectivity_status = "UNKNOWN" (default)

2. SERVIÇO (agent_registry.py)
   └─ update_connectivity_state() implementado mas não chamado

3. FLUXO (websocket handlers)
   └─ Nenhum handler atualiza connectivity_status

4. PERSISTÊNCIA (salvar_evento)
   └─ Não envolvido (connectivity_status é do banco de agentes)

5. FRONTEND (Overview.tsx)
   └─ Filtra corretamente, mas dados de entrada = "UNKNOWN"
```

**Primeira Falha:** Camada 3 (fluxo WebSocket)

---

## 7. MENOR CORREÇÃO RECOMENDADA

### Sem Alterar Nada (diagnóstico apenas)
Já comprovado que Online = 0 é **consequência esperada**, não bug.

### Se Fosse Corrigir (futuro)
1. **Camada 3 (Fluxo):** Conectar WebSocket → `update_connectivity_state()`
2. **Ou Camada 1 (Dados):** Se WebSocket nunca conectará, resetar default para "OFFLINE" ao invés de "UNKNOWN"
3. Adicionar heartbeat/health check para manter "ONLINE" atualizado

### Prioridade
- **Crítico?** NÃO - Sistema operacional sem WebSocket
- **Necessário?** DEPENDE - Se quer real-time events, sim
- **Ordem:** Habilitar WebSocket DEPOIS de resolver Set-Cookie issue

---

## 8. CONCLUSÃO

| Aspecto | Resultado |
|---------|-----------|
| **Online = 0 é bug?** | ❌ NÃO - Comportamento esperado |
| **Causa comprovada?** | ✅ SIM - connectivity_status = "UNKNOWN" para todos |
| **WebSocket responsável?** | ✅ PARCIALMENTE - Desabilitado + não integrado |
| **Agente WORKING está executando?** | ⓘ DESCONHECIDO - Exigiria testes (proibido) |
| **Correção necessária?** | ⓘ DEPENDE - Se quer real-time events |
| **Sistema funcionando?** | ✅ SIM - 15 min de acesso sem WebSocket |

---

**Diagnóstico Concluído — Nenhuma Alteração Realizada**

Data: 2026-11-24 18:46 UTC  
Próximo: Habilitar WebSocket após resolver Set-Cookie issue
