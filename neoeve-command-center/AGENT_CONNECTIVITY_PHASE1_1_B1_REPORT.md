# B1 — Agent Registry Migration Report

**Data:** 2026-11-24  
**Status:** 🔵 DIAGNÓSTICO E PLANEJAMENTO  
**Escopo:** Adaptar AgentRegistry para usar TenantAgentState  

---

## Situação Atual

### Estrutura de AgentRegistry

**Arquivo:** `backend/app/services/agent_registry.py`

**7 Agentes Globais:**
1. ✅ Architect (`agent-architect`) — Planejar, decompor
2. ✅ Backend Developer (`agent-backend`) — Implementar, refatorar
3. ✅ Debugger (`agent-debugger`) — Investigar, diagnosticar
4. ✅ QA Engineer (`agent-qa`) — Testar, validar
5. ✅ Security Auditor (`agent-security`) — Auditar, vetar
6. ✅ Release Manager (`agent-release`) — Coordenar release
7. ✅ OpenAI Validator (`agent-validator`) — Validar (read-only)

### Problemas Identificados

| Problema | Impacto | Raiz |
|----------|--------|------|
| **Estado Global sem Tenant** | Agente ONLINE em Tenant A afeta Tenant B | Tabela `Agent` não tem tenant_id |
| **Atualização sem Isolamento** | `update_operational_state()` muda para todos | Métodos recebem apenas agent_id |
| **Consultas Genéricas** | `get_agent()` retorna sem contexto tenant | Query não filtra por tenant |
| **Sem TenantAgentState** | Nenhuma isolação implementada | Migration 008 criada mas não utilizada |

---

## Plano B1 — Migração

### Fase 1: Análise de Dependências (READ-ONLY)

**Arquivos a verificar:**
```
✓ backend/app/services/agent_registry.py (Usar TenantAgentState)
✓ backend/app/services/agent_runtime.py (Passa tenant_id? Precisa?)
✓ backend/app/services/recovery_service.py (Recovery precisa de isolamento)
✓ backend/app/routes/agents.py (Endpoints expõem tenant_id?)
✓ backend/tests/test_c11_agent_registry.py (Adaptar para tenant_id)
```

### Fase 2: Criar TenantAgentStateService

**Nova classe:** `backend/app/services/tenant_agent_state_service.py`

**Responsabilidades:**
- ✅ Inicializar TenantAgentState para (tenant_id, agent_id)
- ✅ Atualizar estado por tenant
- ✅ Consultar estado por tenant
- ✅ Garantir isolamento (WHERE tenant_id = ? AND agent_id = ?)
- ✅ Idempotência de criação

**Interface:**
```python
class TenantAgentStateService:
    @staticmethod
    def get_or_create(db: Session, tenant_id: str, agent_id: str) -> TenantAgentState
    
    @staticmethod
    def update_operational_state(db: Session, tenant_id: str, agent_id: str, state: str) -> bool
    
    @staticmethod
    def update_connectivity_state(db: Session, tenant_id: str, agent_id: str, state: str) -> bool
    
    @staticmethod
    def get_state(db: Session, tenant_id: str, agent_id: str) -> Optional[TenantAgentState]
```

### Fase 3: Adaptar AgentRegistry

**Mudanças:**

1. **Adicionar tenant_id como parâmetro obrigatório:**
```python
# ANTES (sem tenant):
AgentRegistry.update_operational_state(db, "agent-architect", OperationalState.WORKING)

# DEPOIS (com tenant):
AgentRegistry.update_operational_state(db, "tenant-123", "agent-architect", OperationalState.WORKING)
```

2. **Usar TenantAgentState para estado operacional:**
```python
# Para estado por tenant → TenantAgentState
# Para permissões/capabilities → Manter global em AGENTS
```

3. **Preservar identidades dos 7 agentes:**
```python
# AGENTS dict continua idêntico (identidade global)
# Comportamento muda para isolação por tenant
```

### Fase 4: Testes Obrigatórios B1

**Testes 1-7:** Estáticos (sem DB, sem tenant)
```
✓ test_seven_agents_registered
✓ test_agent_roles
✓ test_permission_matrix_architect
✓ test_permission_deny_qa_write
✓ test_security_auditor_veto
✓ test_openai_validator_read_only
✓ test_capabilities
```

**Testes 8-10:** Novo — Isolamento Multi-Tenant (COM DB porta 5433)
```
✓ test_isolamento_tenant_a_operacional_tenant_b_idle
✓ test_atualizacao_tenant_a_nao_afeta_tenant_b
✓ test_mesmo_agente_em_tenants_diferentes
```

---

## Risco & Mitigação

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| Quebrar AgentRuntime | ALTA | Adaptar tenant_id propag. em paralelo |
| Perder identidade dos 7 agentes | BAIXA | Manter AGENTS dict intacto |
| Cross-tenant contamination | ALTA | Testes isolamento obrigatórios |
| Regressão em permissões | MÉDIA | Rodar testes 1-7 antes de integrar |

---

## Próximas Ações

**Autorizar:** ✅ CONFIRMADO

**Executar B1 em sequência:**
1. ✅ Criar TenantAgentStateService
2. ✅ Adaptar AgentRegistry.update_*_state()
3. ✅ Executar testes 1-10
4. ✅ Apresentar relatório final B1_TESTS.md

**Depois:** Aguardar revisão + autorização para B2 (AgentRuntime)

---

## Critério de Aceitação B1

✅ **Pronto quando:**
- Nenhum teste falha (1-10)
- tenant_id é obrigatório (sem fallback)
- Sem código duplicado (reutilizar TenantAgentStateService)
- Sem alterações em AGENTS dict
- Sem quebra em outras camadas (B2 responsável por AgentRuntime)

