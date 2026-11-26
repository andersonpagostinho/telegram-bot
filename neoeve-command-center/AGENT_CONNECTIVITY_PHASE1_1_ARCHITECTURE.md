# Agent Connectivity Phase 1.1 — Proposed Architecture

**Data:** 2026-11-24  
**Status:** Proposta Arquitetural (Auditoria Apenas)  
**Objetivo:** Separar estado global de Agent do estado por-tenant  

---

## PROBLEMA ATUAL

```
Agent (global)
├─ connectivity_status ← AFETA TODOS os tenants
├─ status ← AFETA TODOS os tenants
├─ current_mission_id ← De qual tenant?
└─ current_task_id ← De qual tenant?

Mission (multi-tenant)
├─ tenant_id
└─ ...

Execution (multi-tenant)
├─ tenant_id
└─ agent_id ← referencia Agent global
```

**Consequências:**
1. Tenant A marca agent como OFFLINE → Tenant B vê offline
2. Agent pode ter current_mission_id sem saber de qual tenant é
3. AgentService tenta filtrar por tenant mas Agent é global
4. Sem isolamento real de conectividade por tenant

---

## ARQUITETURA PROPOSTA

### Separação de Conceitos

#### **A. Agent (Global, sem mudanças)**
Identidade fixa do agente no sistema:
```python
class Agent(Base):
    __tablename__ = "agents"
    
    agent_id = Column(String(64), primary_key=True)      # agent-architect
    agent_role = Column(String(32), nullable=False)      # Role
    runtime = Column(String(64), nullable=True)          # Claude Code CLI
    
    # Removido: connectivity_status (move para TenantAgentState)
    # Removido: status (move para TenantAgentState)
    # Removido: current_mission_id (move para TenantAgentState)
    # Removido: current_task_id (move para TenantAgentState)
    
    # Campos que PERMANECEM globais (nunca mudam):
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
```

#### **B. TenantAgentState (Multi-tenant, NOVO)**
Estado operacional e conectividade por tenant:
```python
class TenantAgentState(Base):
    """Agent state scoped to a specific tenant."""
    __tablename__ = "tenant_agent_states"
    
    # Composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'agent_id', name='pk_tenant_agent'),
        Index('idx_tenant_agent_state_tenant', 'tenant_id'),
        Index('idx_tenant_agent_state_agent', 'agent_id'),
        ForeignKeyConstraint(['agent_id'], ['agents.agent_id']),
        ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id']),
    )
    
    tenant_id = Column(String(64), nullable=False)
    agent_id = Column(String(64), nullable=False)
    
    # Operacional state
    status = Column(String(32), default="IDLE")                    # IDLE, WORKING, ERROR
    connectivity_status = Column(String(32), default="UNKNOWN")    # ONLINE, OFFLINE, STALE
    
    # Contexto de execução
    current_mission_id = Column(String(64), nullable=True)
    current_task_id = Column(String(64), nullable=True)
    
    # Métricas
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    last_execution_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Subscription state
    subscription_status = Column(String(32), default="UNKNOWN")     # VALID, EXPIRED, INVALID
    executor_status = Column(String(32), default="UNKNOWN")         # AVAILABLE, UNAVAILABLE
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
```

#### **C. Execution (Sem mudanças — já multi-tenant)**
```python
class Execution(Base):
    __tablename__ = "executions"
    
    execution_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False)         # ← Isolamento
    agent_id = Column(String(64), nullable=False)          # ← FK para Agent.agent_id
    status = Column(String(32), default="PENDING")
    # ... resto continua igual
```

---

## FLUXO DE DADOS

### Antes (Quebrado)
```
AgentRuntime.execute_task(tenant_id=A, agent_id=architect)
  ↓
update_operational_state(agent_id, WORKING)
  ↓
Agent.status = WORKING  ← Afeta TODOS os tenants
  ↓
Tenant B consulta agent-architect
  ↓
Vê status = WORKING (mesmo que nunca pediu para usar!)
```

### Depois (Isolado)
```
AgentRuntime.execute_task(tenant_id=A, agent_id=architect)
  ↓
update_operational_state(tenant_id=A, agent_id=architect, WORKING)
  ↓
TenantAgentState(tenant_id=A, agent_id=architect).status = WORKING
  ↓
Tenant B consulta agent-architect
  ↓
Consulta TenantAgentState(tenant_id=B, agent_id=architect)
  ↓
Pode estar IDLE ou OFFLINE (isolado)
```

---

## MAPEAMENTO: Qual estado vai para onde?

| Campo Atual | Novo Local | Isolamento |
|-------------|-----------|-----------|
| `Agent.connectivity_status` | `TenantAgentState.connectivity_status` | PER-TENANT |
| `Agent.status` | `TenantAgentState.status` | PER-TENANT |
| `Agent.current_mission_id` | `TenantAgentState.current_mission_id` | PER-TENANT |
| `Agent.current_task_id` | `TenantAgentState.current_task_id` | PER-TENANT |
| `Agent.last_event_at` | `TenantAgentState.last_event_at` | PER-TENANT |
| `Agent.last_execution_at` | `TenantAgentState.last_execution_at` | PER-TENANT |
| `Agent.last_error` | `TenantAgentState.last_error` | PER-TENANT |
| `Agent.metrics_summary` | `TenantAgentState` (separado) | PER-TENANT |
| `Agent.agent_id` | `Agent.agent_id` | GLOBAL |
| `Agent.agent_role` | `Agent.agent_role` | GLOBAL |
| `Agent.runtime` | `Agent.runtime` | GLOBAL |
| `Agent.created_at` | `Agent.created_at` | GLOBAL |
| `Agent.updated_at` | `Agent.updated_at` | GLOBAL |

---

## IMPACTO NAS CAMADAS

### 1. Database Layer
**Novo:**
- Criar migration: `add_tenant_agent_state_table`
- Tabela: `tenant_agent_states` (composite PK: tenant_id + agent_id)
- Indices para query rápida

**Modificado:**
- Agent: Remover 10 colunas (mover para TenantAgentState)
- **NÃO quebra dados existentes** (migration copia dados)

### 2. Models (`backend/database/models.py`)
**Novo:**
- Classe `TenantAgentState`

**Modificado:**
- Classe `Agent` (remover 10 colunas)

### 3. AgentRegistry (`backend/app/services/agent_registry.py`)
**Novo métodos:**
- `update_tenant_agent_state(tenant_id, agent_id, state)`
- `get_tenant_agent_state(tenant_id, agent_id)`
- `get_or_create_tenant_agent_state(tenant_id, agent_id)`

**Modificado:**
- `update_connectivity_state(tenant_id, agent_id, state)` ← Adicionar tenant_id
- `update_operational_state(tenant_id, agent_id, state)` ← Adicionar tenant_id
- `register_all_agents(db)` → ainda cria 7 Agent globais

### 4. AgentRuntime (`backend/app/services/agent_runtime.py`)
**Modificado:**
- Todas as chamadas `update_connectivity_state()` → incluir tenant_id
- Todas as chamadas `update_operational_state()` → incluir tenant_id
- `execute_task()` já tem tenant_id, basta passar

### 5. AgentService (`backend/app/services/agent_service.py`)
**Novo métodos:**
- `get_tenant_agent_state(tenant_id, agent_id)`
- `list_agents_by_tenant(tenant_id)` ← retorna TenantAgentState

**Modificado:**
- `get_agent(tenant_id, agent_id)` → volta a retornar Agent (global)

### 6. API Routes (`backend/app/api/routes/agents.py`)
**Modificado:**
- GET `/agents/{agent_id}` → Retornar Agent + TenantAgentState
  ```python
  GET /agents/agent-architect
  Response:
  {
    "agent": {
      "agent_id": "agent-architect",
      "agent_role": "architect",
      "runtime": "claude-code-cli"
    },
    "state": {
      "tenant_id": "tenant-123",
      "status": "WORKING",
      "connectivity_status": "ONLINE",
      "current_mission_id": "mission-456",
      "current_task_id": "task-789"
    }
  }
  ```

### 7. Frontend (`frontend/src/*`)
**Modificado:**
- Componentes que exibem agent status
- Consultar TenantAgentState (via API)
- Exibir estado per-tenant

### 8. RecoveryService
**Sem alterações diretas:**
- Já usa tenant_id em Execution
- Apenas usar TenantAgentState em lugar de Agent

---

## GARANTIAS ARQUITETURAIS

✅ **Agent permanece global** (7 agentes fixos)
✅ **Sem quebra de FK** (Execution.agent_id continua referenciando Agent.agent_id)
✅ **Isolamento real** (cada tenant vê seu próprio estado)
✅ **Sem perda de dados** (migration copia dados)
✅ **Backwards compatible** (APIs ajustadas, schema expandido)
✅ **Rastreabilidade** (last_event_at permanece)

---

## REGRAS CRÍTICAS

### 1. Sempre Usar tenant_id
```python
# ❌ ERRADO
update_connectivity_state(agent_id, OFFLINE)

# ✅ CORRETO
update_connectivity_state(tenant_id, agent_id, OFFLINE)
```

### 2. Validar tenant_id Sempre
```python
# ❌ ERRADO
state = TenantAgentState.query(agent_id=id).first()

# ✅ CORRETO
state = TenantAgentState.query(
    tenant_id=current_user.tenant_id,
    agent_id=id
).first()
```

### 3. Never Trust Frontend tenant_id
```python
# ❌ ERRADO
tenant_id = request.query_params.get("tenant_id")

# ✅ CORRETO
tenant_id = current_user.tenant_id  # De JWT token
```

---

## PRÓXIMO PASSO: PHASE 1.1

Este documento propõe a arquitetura. 

Próximos documentos:
1. **MIGRATION_PLAN.md** — Como migrar sem perda de dados
2. **IMPACT_ANALYSIS.md** — Quais arquivos mudam e como

Após aprovação desta arquitetura, proceder com implementação.

---

**Status:** Proposta Pronta para Revisão

Aguardando feedback antes de prosseguir para implementação real.
