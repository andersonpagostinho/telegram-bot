# Agent Connectivity Phase 1.1 — Impact Analysis

**Data:** 2026-11-24  
**Escopo:** Mapeamento detalhado de mudanças em cada arquivo/camada  
**Objetivo:** Identificar todas as localizações que precisam de atualização  

---

## RESUMO EXECUTIVO

**Arquivos que MUDAM:** 15+  
**Linhas aproximadas:** 500-700  
**Mudanças ÁS APIs:** 10-15 endpoints  
**Risco de Regressão:** Médio (isolamento multi-tenant é crítico)  
**Reversibilidade:** Total (migration reversa copia dados)  

---

## 1. DATABASE LAYER

### 1.1 New Migration File

**Arquivo:** `backend/migrations/versions/{timestamp}_add_tenant_agent_states.py` (NOVO)

**Tamanho:** ~150 linhas

**Ação:** 
- Criar tabela `tenant_agent_states`
- Criar indices
- Populate inicial para todos os tenants
- Downgrade reverso

**Risco:** Baixo (additive only, sem delete)

---

### 1.2 Existing Models

**Arquivo:** `backend/database/models.py`

**Localização:** Adicionar após linha 166 (após Agent)

**Tamanho:** ~80 linhas

**Novo:**
```python
class TenantAgentState(Base):
    __tablename__ = "tenant_agent_states"
    # ... 15 colunas
```

**Mudança no Agent:**
- **Não remover colunas ainda** (Fase 2)
- Apenas adicionar comentários: `# → Moved to TenantAgentState`

**Risco:** Baixo (apenas adição)

---

### 1.3 Migration Index

**Arquivo:** `backend/migrations/env.py`

**Tamanho:** Nenhuma mudança necessária

**Risco:** Zero

---

## 2. APPLICATION LAYER

### 2.1 Agent Registry

**Arquivo:** `backend/app/services/agent_registry.py`

**Tamanho:** +100-150 linhas

**Mudanças:**

| Localização | Mudança | Linhas |
|-------------|---------|--------|
| Import | Adicionar `TenantAgentState` | +1 |
| `register_all_agents()` | Sem mudanças (cria Agent global apenas) | 0 |
| Novo método | `get_or_create_tenant_agent_state()` | +20 |
| Novo método | `list_tenant_agents()` | +15 |
| Método existente | `update_connectivity_state()` Adicionar `tenant_id` param | +5 |
| Método existente | `update_operational_state()` Adicionar `tenant_id` param | +5 |
| Método existente | `get_agent()` Sem mudança (retorna Agent global) | 0 |

**Padrão de mudança:**

```python
# ANTES:
def update_connectivity_state(cls, db: Session, agent_id: str, state: ConnectivityState):
    agent = cls.get_agent(agent_id, db)
    agent.connectivity_status = state.value
    db.commit()

# DEPOIS:
def update_connectivity_state(
    cls, 
    db: Session, 
    tenant_id: str,              # ← NOVO
    agent_id: str, 
    state: ConnectivityState
):
    state_obj = cls.get_or_create_tenant_agent_state(db, tenant_id, agent_id)
    state_obj.connectivity_status = state.value
    db.commit()
```

**Risco:** Médio (critical methods, mas sem breaking logic)

---

### 2.2 Agent Runtime

**Arquivo:** `backend/app/services/agent_runtime.py`

**Tamanho:** +10-15 mudanças (cada uma é 1-2 linhas)

**Localização das mudanças:**

| Linha | Mudança | Detalhe |
|------|---------|---------|
| 188 | Update chamada | `update_operational_state(db, tenant_id, agent_id, WORKING)` |
| 234 | Update chamada | `update_operational_state(db, tenant_id, agent_id, IDLE)` |
| 349 | Update chamada | `update_operational_state(db, tenant_id, agent_id, IDLE)` |
| 351 | Update chamada | `update_operational_state(db, tenant_id, agent_id, ERROR)` |
| 370-372 | Novo bloco | Detectar erro conexão + `update_connectivity_state()` |
| 427 | Update chamada | `update_operational_state(db, tenant_id, agent_id, ERROR)` |
| 440-441 | Update chamada | `update_operational_state(db, tenant_id, agent_id, ERROR)` |

**Padrão de mudança:**

Substituir TODAS as chamadas:
```python
# ANTES:
AgentRegistry.update_operational_state(db, agent_id, OperationalState.WORKING)

# DEPOIS:
AgentRegistry.update_operational_state(db, tenant_id, agent_id, OperationalState.WORKING)
```

**Risco:** Médio-Alto (critical execution path, mas direto)

**Teste Necessário:** Verificar que tenant_id é sempre passado (não None)

---

### 2.3 Main.py (Startup)

**Arquivo:** `backend/app/main.py`

**Tamanho:** +10-15 linhas

**Localização:** Linhas 85-98 (health check integration)

**Mudança:**

```python
# ANTES:
for key, agent_config in AgentRegistry.AGENTS.items():
    agent_id = agent_config["agent_id"]
    AgentRegistry.update_connectivity_state(db, agent_id, ConnectivityState.ONLINE)

# DEPOIS:
for tenant in db.query(Tenant).all():
    for key, agent_config in AgentRegistry.AGENTS.items():
        agent_id = agent_config["agent_id"]
        AgentRegistry.update_connectivity_state(
            db, tenant.tenant_id, agent_id, ConnectivityState.ONLINE
        )
```

**Risco:** Baixo (apenas loop adicional, sem lógica complexa)

---

### 2.4 Agent Service

**Arquivo:** `backend/app/services/agent_service.py`

**Tamanho:** +30-40 linhas

**Mudanças:**

| Método | Mudança | Detalhe |
|--------|---------|---------|
| `get_agent()` | Sem mudança | Continua retornando Agent global |
| Novo | `get_tenant_agent_state()` | Buscar state por tenant |
| Novo | `list_agents_by_tenant()` | Listar states de um tenant |

**Padrão:**

```python
def get_tenant_agent_state(self, tenant_id: str, agent_id: str):
    return self.db.query(TenantAgentState).filter(
        TenantAgentState.tenant_id == tenant_id,
        TenantAgentState.agent_id == agent_id
    ).first()
```

**Risco:** Baixo (nuevos métodos, sem afetar existentes)

---

### 2.5 Recovery Service

**Arquivo:** `backend/app/services/recovery_service.py`

**Tamanho:** Sem mudanças (já usa tenant_id em Execution)

**Risco:** Zero

**Nota:** Pode precisar atualizar logs para usar TenantAgentState em lugar de Agent.

---

### 2.6 Schemas

**Arquivo:** `backend/app/schemas/agent.py`

**Tamanho:** +30-40 linhas

**Mudanças:**

```python
# Novo schema para TenantAgentState
class TenantAgentStateResponse(BaseModel):
    tenant_id: str
    agent_id: str
    status: str
    connectivity_status: str
    current_mission_id: Optional[str]
    current_task_id: Optional[str]
    last_event_at: Optional[datetime]
    
# Atualizar AgentResponse para incluir state
class AgentResponse(BaseModel):
    # Agent global fields
    agent_id: str
    agent_role: str
    runtime: str
    
    # Adicionar state por tenant
    state: Optional[TenantAgentStateResponse]
```

**Risco:** Baixo (nuevos schemas, backward compatible)

---

## 3. API LAYER

### 3.1 Agent Endpoints

**Arquivo:** `backend/app/api/routes/agents.py`

**Tamanho:** +50-70 mudanças (review routes)

**Endpoints Afetados:**

| Endpoint | Mudança | Detalhe |
|----------|---------|---------|
| GET `/agents` | Formato response | Retornar Agent + estado por tenant |
| GET `/agents/{id}` | Formato response | Retornar Agent + estado por tenant |
| POST `/agents/{id}/state` | Novo endpoint | Atualizar estado (admin only) |

**Padrão de resposta (DEPOIS):**

```json
{
  "agent": {
    "agent_id": "agent-architect",
    "agent_role": "architect",
    "runtime": "claude-code-cli"
  },
  "state": {
    "tenant_id": "tenant-123",
    "status": "WORKING",
    "connectivity_status": "ONLINE"
  }
}
```

**Risco:** Médio (breaking change em response format, mas deprecation path existe)

---

### 3.2 Execution Endpoints

**Arquivo:** `backend/app/api/routes/executions.py`

**Tamanho:** Sem mudanças necessárias (já multi-tenant)

**Risco:** Zero

---

## 4. FRONTEND LAYER

### 4.1 Components

**Arquivos:**
- `frontend/src/components/AgentStatus.tsx` (novo ou atualizado)
- `frontend/src/components/AgentList.tsx`
- `frontend/src/pages/Agents.tsx`

**Tamanho:** +100-150 linhas total

**Mudanças:**

| Componente | Mudança | Detalhe |
|-----------|---------|---------|
| AgentStatus | Atualizar | Exibir connectivity_status de TenantAgentState |
| AgentList | Atualizar | Listar agents + seus states |
| Agents page | Atualizar | Passar tenant_id nas queries |

**Padrão:**

```typescript
// ANTES: Exibir de Agent global
<span>{agent.connectivity_status}</span>

// DEPOIS: Exibir de TenantAgentState
<span>{agent.state?.connectivity_status}</span>
```

**Risco:** Médio (UI precisa refletir isolamento)

---

### 4.2 Services

**Arquivo:** `frontend/src/services/api.ts`

**Tamanho:** +10-20 linhas

**Mudanças:**

```typescript
// Novo tipo
interface TenantAgentState {
  tenant_id: string;
  agent_id: string;
  status: string;
  connectivity_status: string;
}

// Atualizar resposta
interface Agent {
  agent_id: string;
  state?: TenantAgentState;
}
```

**Risco:** Baixo (apenas tipos novos)

---

## 5. TESTS

### 5.1 Existing Unit Tests

**Arquivo:** `backend/test_phase1_connectivity.py`

**Tamanho:** +50-100 mudanças

**Necessário:**
- Atualizar TODAS as asserções com tenant_id
- Adicionar testes de isolamento
- Adicionar testes de concorrência

**Padrão:**

```python
# ANTES:
AgentRegistry.update_connectivity_state(db, agent_id, ONLINE)

# DEPOIS:
AgentRegistry.update_connectivity_state(db, TENANT_TEST, agent_id, ONLINE)
```

**Risco:** Médio (testes críticos para validação)

---

### 5.2 New Integration Tests

**Arquivo:** `backend/test_tenant_isolation.py` (NOVO)

**Tamanho:** ~200 linhas

**Testes:**
- Multi-tenant isolation
- Concorrência (duas execuções do mesmo agent)
- Cross-tenant data contamination check

**Risco:** Baixo (nuevos testes)

---

## 6. DOCUMENTATION

### 6.1 Code Comments

**Localização:** Agent model, TenantAgentState, AgentRegistry

**Tamanho:** +50 comentários

**Necessário:** Documentar que Agent é global, TenantAgentState é por-tenant

**Risco:** Zero (apenas documentação)

---

### 6.2 Architecture Docs

**Arquivos:** (Já criados)
- AGENT_CONNECTIVITY_PHASE1_1_ARCHITECTURE.md
- AGENT_CONNECTIVITY_PHASE1_1_MIGRATION_PLAN.md
- AGENT_CONNECTIVITY_PHASE1_1_IMPACT_ANALYSIS.md

**Risco:** Zero

---

## MATRIZ DE IMPACTO

| Componente | Crítico? | Reversível? | Risco | Esforço |
|-----------|----------|-----------|-------|---------|
| Database | ✅ | ✅ | Baixo | Médio |
| AgentRegistry | ✅ | ✅ | Médio | Alto |
| AgentRuntime | ✅ | ✅ | Médio-Alto | Alto |
| Main.py | ⚠️ | ✅ | Baixo | Baixo |
| Agent Service | ⚠️ | ✅ | Baixo | Médio |
| APIs | ✅ | ⚠️ | Médio | Médio |
| Frontend | ✅ | ✅ | Médio | Médio |
| Tests | ✅ | ✅ | Médio | Alto |

---

## CHECKLIST PRÉ-IMPLEMENTAÇÃO

```
Fase 0: Preparação
☐ Backup do banco
☐ Auditoria de dados existentes
☐ Listar todos os tenants existentes

Fase 1: Database
☐ Migration criada e testada
☐ Dados populados corretamente
☐ Indices criados

Fase 2: Application
☐ TenantAgentState model criado
☐ AgentRegistry métodos atualizados
☐ AgentRuntime chamadas atualizadas
☐ main.py health check atualizado
☐ AgentService métodos novos
☐ Schemas atualizados

Fase 3: API
☐ Endpoints retornam tenant-scoped state
☐ Validação de tenant_id implementada
☐ Documentation atualizada

Fase 4: Frontend
☐ Componentes exibem TenantAgentState
☐ Isolamento visual confirmado

Fase 5: Testes
☐ Testes existentes passam (com tenant_id)
☐ Testes de isolamento passam
☐ Testes de concorrência passam

Fase 6: Validação Final
☐ Sem regressões
☐ Isolamento confirmado em produção-like
☐ Performance aceitável
```

---

## RISCO RESIDUAL

**Crítico:**
- Passar tenant_id incorreto → dados vazam entre tenants
- Mitigation: Type checking + unit tests + code review

**Alto:**
- Regressão em execution path → agentes não conseguem executar
- Mitigation: Integration tests + staging validation

**Médio:**
- API response format muda → frontend quebra
- Mitigation: Backward compatibility + gradual rollout

**Baixo:**
- Performance degrada com nova tabela
- Mitigation: Indices + query optimization

---

## TIMELINE ESTIMADA

| Fase | Atividade | Responsável | Tempo |
|------|-----------|-------------|-------|
| 0 | Preparação | DevOps | 30 min |
| 1 | Database | Backend | 15 min |
| 2 | Application | Backend | 3-4h |
| 3 | API | Backend | 1-2h |
| 4 | Frontend | Frontend | 1-2h |
| 5 | Testes | QA/Backend | 2-3h |
| 6 | Validação | QA | 1-2h |

**Total:** 9-14 horas

---

## PRÓXIMOS PASSOS

1. ✅ Arquitetura proposta (ARCHITECTURE.md)
2. ✅ Plano de migração (MIGRATION_PLAN.md)
3. ✅ Análise de impacto (IMPACT_ANALYSIS.md)
4. ⏳ Code review da proposta
5. ⏳ Implementação
6. ⏳ Testes
7. ⏳ Deploy em staging
8. ⏳ Deploy em produção

---

**Status:** Análise de Impacto Completa

Documento de apoio para implementação.

Esperando aprovação da arquitetura antes de proceder.
