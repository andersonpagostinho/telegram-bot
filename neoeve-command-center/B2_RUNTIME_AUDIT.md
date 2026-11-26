# B2 — Runtime Audit (READ-ONLY)

**Data:** 2026-11-24  
**Status:** 🔴 **BLOQUEADOR ENCONTRADO**  
**Escopo:** Auditoria de ciclo de vida operacional em AgentRuntime  

---

## Achados Críticos

### 🔴 BUG CRÍTICO: Falta tenant_id em linha 440

**Localização:** `backend/app/services/agent_runtime.py:440`

```python
# ERRADO (sem tenant_id):
AgentRegistry.update_operational_state(db, agent_id, OperationalState.ERROR)

# CORRETO (com tenant_id):
AgentRegistry.update_operational_state(db, tenant_id, agent_id, OperationalState.ERROR)
```

**Impacto:** 
- Cross-tenant contamination possível
- Estado de ERROR afeta TODOS os tenants com mesmo agent_id
- Violação de isolamento multi-tenant
- **BLOQUEADOR PARA B2**

**Contexto:** Exception handling — quando há erro desconhecido durante execução

---

## Mapa de Transições de Estado

### Estados Encontrados em Execution

```
Inicial → RUNNING/COMPLETED → Final
├── FAILED (linhas 162, 216, 378)
├── COMPLETED (linha 263)
├── QUEUED (linha 299)
├── FAILED_PERMANENT (linhas 299, 316)
└── ERROR (linha 427)
```

### Transições de Estado do Agente (via AgentRegistry)

**Linha 188:** `tenant_id, agent_id` → WORKING (Início execução)  
**Linha 234:** `tenant_id, agent_id` → IDLE (Acesso negado)  
**Linha 349:** `tenant_id, agent_id` → IDLE (Sucesso)  
**Linha 351:** `tenant_id, agent_id` → ERROR (Falha permanente)  
**Linha 370:** `tenant_id, agent_id` → OFFLINE (Erro conexão)  
**Linha 427:** `tenant_id, agent_id` → ERROR (Business error)  
**Linha 440:** `agent_id` APENAS → ERROR ⚠️ **BUG**

---

## Problemas de Concorrência Identificados

### 1. Sem verificação de execution_id ativo

**Comportamento atual:** 
- Cria nova execução se execution_id não existe
- Pode ter múltiplas execuções simultâneas do mesmo agent_id

**Risco:**
- Duas execuções simultâneas: qual estado prevalece?
- Finally block em uma pode sobrescrever a outra

**Exemplo:**
```
Exec 1: agent → WORKING
Exec 2: agent → WORKING (simultâneo)
Exec 1 termina: agent → IDLE
Exec 2 termina: agent → ERROR (sobrescreve Exec 1)
```

### 2. Sem lock/transaction para estado do agente

**Risco:**
- RMW (read-modify-write) sem proteção em TenantAgentState
- Duas atualizações simultâneas podem resultar em estado inconsistente

---

## Pontos de Falha Identificados

### 1. Exception em linha 427 (Business error)

```python
except Exception as e:
    AgentRegistry.update_operational_state(db, tenant_id, agent_id, OperationalState.ERROR)
    return False, "", str(e)
```

**OK:** Tem tenant_id ✅

### 2. Exception em linha 440 (Unknown error)

```python
except Exception as e:  # Fallback catch-all
    AgentRegistry.update_operational_state(db, agent_id, OperationalState.ERROR)  # ❌ BUG
```

**ERRO:** Falta tenant_id ⚠️

---

## Fluxos de Término

### Sucesso
- Linha 349: COMPLETED → IDLE

### Falha Permanente
- Linha 351: FAILED_PERMANENT → ERROR

### Erro Conexão
- Linha 370: CONNECTION_ERROR → OFFLINE

### Business Error
- Linha 427: EXCEPTION → ERROR (com tenant_id ✅)

### Unknown Error
- Linha 440: EXCEPTION → ERROR (SEM tenant_id ⚠️)

---

## Validação de tenant_id

**Localização:** Linhas 73-78

```python
if not tenant_id or not project_id:
    logger.error(f"Execution {execution_id}: Missing tenant_id or project_id")
    return False, "", "Invalid tenant/project"
```

✅ Validação presente no início

---

## Associação execução ↔ agente

**execution.agent_id:** ✅ Armazenado na BD
**execution.tenant_id:** ✅ Armazenado na BD
**execution.execution_id:** ✅ Usado para retry

---

## Classificação de Problemas

| Problema | Severidade | Localização | Correção |
|----------|------------|-------------|----------|
| Falta tenant_id | 🔴 CRÍTICO | Linha 440 | Adicionar tenant_id |
| Concorrência sem lock | 🟡 MÉDIO | Geral | Usar transaction/lock |
| Sem verificação ativa | 🟡 MÉDIO | Geral | Validar execution ativa |

---

## Recomendações para B2

**BLOQUEADOR:**
- ✅ Corrigir linha 440: adicionar tenant_id

**IMPLEMENTAÇÃO:**
- ✅ Garantir atomicidade de state update
- ✅ Validar múltiplas execuções simultâneas
- ✅ Testar concorrência em PostgreSQL

**NÃO FAZER:**
- ❌ Alterar RecoveryService
- ❌ Implementar heartbeat
- ❌ Mudar contratos públicos

---

## Status de Auditoria

✅ **AUDITORIA COMPLETA**  
🔴 **BLOQUEADOR ENCONTRADO** (Linha 440)  
⏳ **Aguardando correção antes de B2 continuar**

