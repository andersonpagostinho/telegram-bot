# Agent Connectivity Phase 1.1 — Migration Plan

**Data:** 2026-11-24  
**Escopo:** Migração sem perda de dados de Agent para Agent + TenantAgentState  
**Riscos:** Baixo (dados copiados, tabela expandida)  

---

## OVERVIEW

**Objetivo:** Mover estado por-tenant de Agent para nova tabela TenantAgentState.

**Estratégia:**
1. Criar nova tabela `tenant_agent_states`
2. Copiar dados existentes (populate inicial)
3. Atualizar queries e operações
4. Remover colunas de Agent (fase 2)

**Reversibilidade:** ✅ Sim (migration reversa copia dados de volta)

---

## FASE 0: Preparação

### 0.1 Backup do Banco

```bash
# Antes de qualquer alteração
pg_dump -U neoeve_dev -h localhost neoeve_command_center > backup_before_migration.sql

# Verificar se Agent tem dados
psql -U neoeve_dev -h localhost -c "SELECT COUNT(*) FROM agents;"
```

### 0.2 Auditoria de Dados

```sql
-- Verificar estado atual
SELECT 
  agent_id, 
  status, 
  connectivity_status, 
  current_mission_id,
  COUNT(*) as count
FROM agents
GROUP BY agent_id, status, connectivity_status, current_mission_id;
```

---

## FASE 1: Criar Nova Tabela (Migration 001)

### 1.1 Migration File

**Arquivo:** `backend/migrations/versions/{timestamp}_add_tenant_agent_states.py`

```python
"""Add tenant_agent_states table for multi-tenant isolation."""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "..."
down_revision = "d19e221b7b2a"  # Previous migration
branch_labels = None
depends_on = None

def utc_now():
    return datetime.now(timezone.utc)

def upgrade():
    """Create new table and copy data."""
    
    # 1. Create tenant_agent_states table
    op.create_table(
        'tenant_agent_states',
        sa.Column('tenant_id', sa.String(64), nullable=False, primary_key=True),
        sa.Column('agent_id', sa.String(64), nullable=False, primary_key=True),
        
        # Operational state
        sa.Column('status', sa.String(32), default='IDLE'),
        sa.Column('connectivity_status', sa.String(32), default='UNKNOWN'),
        
        # Context
        sa.Column('current_mission_id', sa.String(64), nullable=True),
        sa.Column('current_task_id', sa.String(64), nullable=True),
        
        # Metrics
        sa.Column('last_event_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_execution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text, nullable=True),
        
        # Subscription & executor
        sa.Column('subscription_status', sa.String(32), default='UNKNOWN'),
        sa.Column('executor_status', sa.String(32), default='UNKNOWN'),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), default=utc_now),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=utc_now),
        
        # Constraints
        sa.PrimaryKeyConstraint('tenant_id', 'agent_id', name='pk_tenant_agent_state'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.agent_id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id']),
    )
    
    # 2. Create indices
    op.create_index('idx_tenant_agent_state_tenant', 'tenant_agent_states', ['tenant_id'])
    op.create_index('idx_tenant_agent_state_agent', 'tenant_agent_states', ['agent_id'])
    op.create_index('idx_tenant_agent_state_updated', 'tenant_agent_states', ['updated_at'])
    
    # 3. Populate initial data for ALL tenants
    # For each existing tenant, create a TenantAgentState for each agent
    op.execute("""
        INSERT INTO tenant_agent_states 
        (tenant_id, agent_id, status, connectivity_status, current_mission_id, 
         current_task_id, last_event_at, last_execution_at, created_at, updated_at)
        SELECT 
            t.tenant_id,
            a.agent_id,
            COALESCE(a.status, 'IDLE'),
            COALESCE(a.connectivity_status, 'UNKNOWN'),
            a.current_mission_id,
            a.current_task_id,
            a.last_event_at,
            a.last_execution_at,
            NOW() AT TIME ZONE 'UTC',
            NOW() AT TIME ZONE 'UTC'
        FROM tenants t
        CROSS JOIN agents a
        ON CONFLICT (tenant_id, agent_id) DO NOTHING
    """)

def downgrade():
    """Reverse: drop table and copy data back to agents if needed."""
    
    # 1. Copy data back to agents (if agents still have columns)
    op.execute("""
        UPDATE agents a
        SET 
            status = tas.status,
            connectivity_status = tas.connectivity_status,
            current_mission_id = tas.current_mission_id,
            current_task_id = tas.current_task_id,
            last_event_at = tas.last_event_at,
            last_execution_at = tas.last_execution_at,
            last_error = tas.last_error,
            updated_at = NOW() AT TIME ZONE 'UTC'
        FROM tenant_agent_states tas
        WHERE a.agent_id = tas.agent_id
        AND tas.tenant_id = (SELECT tenant_id FROM tenants LIMIT 1)
    """)
    
    # 2. Drop indices
    op.drop_index('idx_tenant_agent_state_tenant')
    op.drop_index('idx_tenant_agent_state_agent')
    op.drop_index('idx_tenant_agent_state_updated')
    
    # 3. Drop table
    op.drop_table('tenant_agent_states')
```

### 1.2 Executar Migration

```bash
# No projeto:
cd backend
alembic upgrade head

# Verificar resultado
psql -U neoeve_dev -h localhost -c "SELECT COUNT(*) FROM tenant_agent_states;"
# Esperado: (num_tenants * 7)  → ex: 10 tenants * 7 agents = 70 registros
```

---

## FASE 2: Atualizar Código (Application Layer)

### 2.1 Models - Adicionar TenantAgentState

**Arquivo:** `backend/database/models.py`

```python
class TenantAgentState(Base):
    """Agent state scoped to a specific tenant."""
    __tablename__ = "tenant_agent_states"

    tenant_id = Column(String(64), primary_key=True, nullable=False)
    agent_id = Column(String(64), primary_key=True, nullable=False)
    
    status = Column(String(32), default="IDLE")
    connectivity_status = Column(String(32), default="UNKNOWN")
    
    current_mission_id = Column(String(64), nullable=True)
    current_task_id = Column(String(64), nullable=True)
    
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    last_execution_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    
    subscription_status = Column(String(32), default="UNKNOWN")
    executor_status = Column(String(32), default="UNKNOWN")
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'agent_id'),
        ForeignKeyConstraint(['agent_id'], ['agents.agent_id']),
        ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id']),
        Index('idx_tenant_agent_state_tenant', 'tenant_id'),
        Index('idx_tenant_agent_state_agent', 'agent_id'),
    )
```

### 2.2 AgentRegistry - Adicionar Métodos

**Arquivo:** `backend/app/services/agent_registry.py`

Novos métodos:

```python
@classmethod
def get_or_create_tenant_agent_state(
    cls, db: Session, tenant_id: str, agent_id: str
) -> "TenantAgentState":
    """Get or create tenant-scoped agent state."""
    state = db.query(TenantAgentState).filter(
        TenantAgentState.tenant_id == tenant_id,
        TenantAgentState.agent_id == agent_id
    ).first()
    
    if not state:
        state = TenantAgentState(
            tenant_id=tenant_id,
            agent_id=agent_id,
            status=OperationalState.IDLE.value,
            connectivity_status=ConnectivityState.NOT_CONFIGURED.value
        )
        db.add(state)
        db.commit()
    
    return state

@classmethod
def update_connectivity_state(
    cls, 
    db: Session, 
    tenant_id: str,              # ← NOVO parâmetro
    agent_id: str, 
    state: ConnectivityState
) -> bool:
    """Update agent connectivity state for a tenant."""
    state_obj = cls.get_or_create_tenant_agent_state(db, tenant_id, agent_id)
    if state_obj:
        state_obj.connectivity_status = state.value
        state_obj.last_event_at = utc_now()
        db.commit()
        logger.info(f"Agent {agent_id} in tenant {tenant_id} marked {state.value}")
        return True
    return False

@classmethod
def update_operational_state(
    cls, 
    db: Session, 
    tenant_id: str,              # ← NOVO parâmetro
    agent_id: str, 
    state: OperationalState
) -> bool:
    """Update agent operational state for a tenant."""
    state_obj = cls.get_or_create_tenant_agent_state(db, tenant_id, agent_id)
    if state_obj:
        state_obj.status = state.value
        state_obj.last_event_at = utc_now()
        db.commit()
        logger.info(f"Agent {agent_id} in tenant {tenant_id} state {state.value}")
        return True
    return False
```

### 2.3 AgentRuntime - Atualizar Chamadas

**Arquivo:** `backend/app/services/agent_runtime.py`

Mudar **TODAS** as chamadas para métodos que atualizam estado:

```python
# ANTES:
AgentRegistry.update_operational_state(db, agent_id, OperationalState.WORKING)

# DEPOIS:
AgentRegistry.update_operational_state(db, tenant_id, agent_id, OperationalState.WORKING)
```

**Locais a atualizar:**
- Linha 188: Início da execução
- Linha 234: Bloqueio de comando
- Linha 349: Sucesso
- Linha 351: Erro permanente
- Linha 370-372: Erro de conexão
- Linha 427: Erro geral
- Linha 440-441: Finally cleanup

### 2.4 main.py - Atualizar Health Check

**Arquivo:** `backend/app/main.py`

```python
# ANTES:
AgentRegistry.update_connectivity_state(db, agent_id, ConnectivityState.ONLINE)

# DEPOIS:
# Necessário iterar sobre tenants:
for tenant in db.query(Tenant).all():
    for agent_config in AgentRegistry.AGENTS.values():
        agent_id = agent_config["agent_id"]
        AgentRegistry.update_connectivity_state(
            db, tenant.tenant_id, agent_id, ConnectivityState.ONLINE
        )
```

---

## FASE 3: Atualizar Testes

### 3.1 Existentes

**Arquivo:** `backend/test_phase1_connectivity.py`

Atualizar TODAS as asserções para incluir tenant_id:

```python
# ANTES:
AgentRegistry.update_connectivity_state(db, agent_id, ConnectivityState.ONLINE)

# DEPOIS:
AgentRegistry.update_connectivity_state(db, TENANT_TEST, agent_id, ConnectivityState.ONLINE)
```

### 3.2 Novos Testes

Adicionar testes para isolamento:

```python
def test_multi_tenant_isolation():
    """Verificar que estado é isolado por tenant."""
    agent_id = "agent-architect"
    
    # Tenant A marca como ONLINE
    AgentRegistry.update_connectivity_state(
        db, tenant_a, agent_id, ConnectivityState.ONLINE
    )
    
    # Tenant B marca como OFFLINE
    AgentRegistry.update_connectivity_state(
        db, tenant_b, agent_id, ConnectivityState.OFFLINE
    )
    
    # Verificar isolamento
    state_a = AgentRegistry.get_or_create_tenant_agent_state(db, tenant_a, agent_id)
    state_b = AgentRegistry.get_or_create_tenant_agent_state(db, tenant_b, agent_id)
    
    assert state_a.connectivity_status == "ONLINE"
    assert state_b.connectivity_status == "OFFLINE"
```

---

## FASE 4: Validação

### 4.1 Checklist Pré-Deploy

```
☐ Migration executada com sucesso
☐ tenant_agent_states tem (num_tenants * 7) registros
☐ Todos os métodos AgentRegistry atualizado com tenant_id
☐ Todos as chamadas em AgentRuntime passam tenant_id
☐ Testes de isolamento passam
☐ Testes de concorrência passam
☐ APIs retornam tenant-scoped state
☐ Frontend reflete estado por-tenant
☐ Backup restaurado e testado
```

### 4.2 Teste de Rollback

```bash
# Se necessário reverter:
alembic downgrade -1

# Verificar dados foram copiados de volta:
SELECT connectivity_status FROM agents WHERE agent_id = 'agent-architect';
```

---

## FASE 5: Remoção de Colunas (FASE 2 — após validação)

**Não fazer agora.** Apenas após semanas de validação em produção:

```python
# Migration futura (semanas depois):
# ALTER TABLE agents DROP COLUMN connectivity_status;
# ALTER TABLE agents DROP COLUMN status;
# ... etc
```

---

## TIMELINE

| Fase | Atividade | Tempo | Crítico? |
|------|-----------|-------|----------|
| 0 | Backup + Auditoria | 30 min | ✅ Sim |
| 1 | Migration 001 | 15 min | ✅ Sim |
| 2 | Atualizar código (AgentRegistry, AgentRuntime, main.py) | 2-3h | ✅ Sim |
| 3 | Atualizar/adicionar testes | 1-2h | ✅ Sim |
| 4 | Validação completa | 1-2h | ✅ Sim |
| 5 | Deploy em staging | 30 min | ⏳ Depois |
| 6 | Monitoramento (1-2 semanas) | - | ⏳ Depois |
| 7 | Remover colunas (Phase 2) | 30 min | ⏳ Depois |

**Total Fase 1.1:** 5-9 horas

---

## REVERSIBILIDADE

✅ **Totalmente reversível**

Se problemas forem encontrados:
```bash
alembic downgrade -1
# Código volta a usar Agent global
# Dados persistem (cópia de backup)
```

---

## NOTAS IMPORTANTES

1. **Sem breaking changes operacionais** — tenants continuam funcionando durante toda a migration
2. **Dados preservados** — nada é deletado, apenas movido/duplicado
3. **Isolamento imediato** — após migration, cada tenant vê seu próprio estado
4. **Auditoria completa** — antes e depois podem ser comparados

---

**Status:** Plano Pronto para Implementação

Próximo passo: IMPACT_ANALYSIS.md (quais arquivos exatamente mudam)
