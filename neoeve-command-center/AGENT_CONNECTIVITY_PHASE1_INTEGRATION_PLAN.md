# Agent Connectivity Lifecycle — Phase 1 Integration Plan

**Data:** 2026-11-24  
**Status:** Proposta de Implementação  
**Escopo:** Etapa 1 - Verificação Real de Disponibilidade  

---

## RESUMO EXECUTIVO

**Objetivo:** Integrar `update_connectivity_state()` em 4 pontos-chave do ciclo de vida para marcar agentes como ONLINE apenas com evidência válida.

**Implementação Mínima:** 4 alterações em 3 arquivos  
**Risco:** Baixo (métodos já existem, apenas chamar nos momentos certos)  
**Regressão:** Zero (não muda comportamento operacional, apenas conectividade)  

---

## 1. PONTOS DE INTEGRAÇÃO ENCONTRADOS

### Ponto 1: Registração Inicial ✅
**Arquivo:** `backend/app/services/agent_registry.py:129-141`  
**Status:** JÁ IMPLEMENTADO  
**Código Atual:**
```python
agent = Agent(
    agent_id=agent_config["agent_id"],
    agent_role=agent_config["role"].value,
    runtime="claude-code-cli",
    status=OperationalState.IDLE.value,
    connectivity_status=ConnectivityState.NOT_CONFIGURED.value,  # ✅ CORRETO
)
```
**Ação:** NÃO ALTERAR (estado inicial está correto)

---

### Ponto 2: Health Check no Startup 🔧
**Arquivo:** `backend/app/main.py:72`  
**Status:** NECESSITA INTEGRAÇÃO  
**Localização:** Função de startup (health_check do adapter)

**Código Atual:**
```python
# health_check do adapter é executado mas resultado não atualiza agentes
health = adapter.health_check()
```

**Proposta (ETAPA 1):**
```python
# APÓS health check passar:
health = adapter.health_check()

# NOVO: Se health check OK, marcar agentes como ONLINE
if health.get("available"):
    db = next(get_db())
    for agent_config in AgentRegistry.AGENTS.values():
        AgentRegistry.update_connectivity_state(
            db, 
            agent_config["agent_id"], 
            ConnectivityState.ONLINE
        )
        logger.info(f"Agent {agent_config['agent_id']} marked ONLINE (health check passed)")
```

**Quando:** Startup, quando GET `/health` é chamado  
**Por quê:** Antes, nenhum código verificava saúde e marcava ONLINE

---

### Ponto 3: Início/Fim de Execução 🔧
**Arquivo:** `backend/app/services/agent_runtime.py:188`  
**Status:** PARCIALMENTE IMPLEMENTADO

**Código Atual (linha 188):**
```python
# Update agent status
AgentRegistry.update_operational_state(db, agent_id, OperationalState.WORKING)  # ✅
```

**Proposta (ETAPA 1):**

Adicionar atualização de estado ao **final** da execução (após o bloco try/except):

```python
# [linha 188 - INÍCIO]
AgentRegistry.update_operational_state(db, agent_id, OperationalState.WORKING)

# ... código de execução ...

# [FINAL - adicionar após except blocks]
finally:
    # Determine final state
    if success:
        final_state = OperationalState.COMPLETED
    else:
        final_state = OperationalState.ERROR
    
    # Update agent status
    AgentRegistry.update_operational_state(db, agent_id, final_state)
    logger.info(f"Agent {agent_id} execution ended with state {final_state.value}")
```

**Quando:** Após execução terminar (sucesso ou erro)  
**Por quê:** Sem isso, agentes ficam em WORKING indefinidamente

---

### Ponto 4: Falha de Conexão 🔧
**Arquivo:** `backend/app/services/agent_runtime.py` (exception handlers)  
**Status:** NECESSITA INTEGRAÇÃO

**Localização:** Em exception handlers (timeout, connection_error, etc.)

**Proposta (ETAPA 1):**

Adicionar em blocos de erro:

```python
except Exception as e:
    # Se erro é timeout ou conexão:
    if "timeout" in str(e).lower() or "connection" in str(e).lower():
        # Marcar como OFFLINE
        AgentRegistry.update_connectivity_state(
            db, 
            agent_id, 
            ConnectivityState.OFFLINE
        )
        logger.warning(f"Agent {agent_id} marked OFFLINE due to connection error")
    
    # Resto do tratamento de erro...
```

**Quando:** Exceção de timeout, connection reset, ou falta de resposta  
**Por quê:** Sem isso, agentes permanecem ONLINE mesmo após falha

---

### Ponto 5: Heartbeat Periódico (ETAPA 2 - FUTURO)
**Status:** NÃO IMPLEMENTAR AGORA

Será implementado em Etapa 2 (background worker/scheduler).

---

## 2. IMPLEMENTAÇÃO MÍNIMA — ORDEM DE EXECUÇÃO

### Fase A: Leitura (diagnóstico)
1. ✅ Ler `main.py` para identificar health check
2. ✅ Ler `agent_runtime.py` para identificar exception handlers
3. ✅ Ler `agent_registry.py` para confirmar métodos (já feito)

### Fase B: Implementação
1. **ARQUIVO 1:** `agent_runtime.py` - Adicionar estado final após execução
2. **ARQUIVO 2:** `agent_runtime.py` - Adicionar detectioon de erro de conexão
3. **ARQUIVO 3:** `main.py` - Integrar health check com update_connectivity_state

### Fase C: Testes
1. Teste: Registrar agentes
2. Teste: Executar tarefa com sucesso
3. Teste: Executar tarefa com erro
4. Teste: Simular timeout/conexão
5. Teste: Verificar estados em banco de dados

---

## 3. CONTRATOS E GARANTIAS

### O Que Preservamos
✅ Nenhuma alteração em autenticação  
✅ Nenhuma alteração em refresh token  
✅ Nenhuma alteração em WebSocket  
✅ Nenhuma alteração em database schema  
✅ Nenhuma alteração em migrations  
✅ Nenhuma alteração em operações reais (execução continua igual)  
✅ Nenhuma remoção de funcionalidades  

### O Que Muda
🔧 `connectivity_status` é atualizado com evidência válida (health check, execução, erro)  
🔧 Agentes não ficam mais em UNKNOWN perpetuamente  
🔧 ONLINE significa verificação real, não suposição  

### Isolamento Multi-tenant
✅ Cada atualização respeita `tenant_id` (já isolado em `Agent` model)  
✅ Não há mistura entre tenants  

---

## 4. FLUXO DE DADOS — Antes vs Depois

### Antes (QUEBRADO)
```
Agent registrado
  ↓
connectivity_status = NOT_CONFIGURED (default)
  ↓
Nenhum código atualiza para ONLINE
  ↓
Muda para UNKNOWN (??)
  ↓
Fica UNKNOWN para sempre
  ↓
Frontend exibe Online = 0
```

### Depois (ETAPA 1)
```
Agent registrado (startup)
  ↓
connectivity_status = NOT_CONFIGURED
  ↓
Health check passa (main.py)
  ↓
update_connectivity_state() → ONLINE ✅
  ↓
Executar tarefa (agent_runtime.py)
  ↓
update_operational_state() → WORKING ✅
  ↓
Tarefa completa/erro (agent_runtime.py)
  ↓
update_operational_state() → COMPLETED ou ERROR ✅
  ↓
Frontend exibe Online = X (baseado em dados reais)
```

---

## 5. RISCO DE REGRESSÃO

**Avaliação: BAIXO**

| Componente | Risco | Motivo |
|-----------|-------|--------|
| Autenticação | 0% | Sem alteração |
| WebSocket | 0% | Sem alteração |
| Execução | 0% | Apenas atualiza status, não bloqueia |
| Persistência | 0% | Usa métodos já existentes |
| Multi-tenant | 0% | Isolamento já garantido |

---

## 6. CRONOGRAMA ETAPA 1

| Atividade | Duração | Status |
|-----------|---------|--------|
| Implementação Ponto 1 | 5 min | Pronto (não alterar) |
| Implementação Ponto 2 (main.py) | 10 min | Proposto |
| Implementação Ponto 3 (agent_runtime.py início/fim) | 15 min | Proposto |
| Implementação Ponto 4 (agent_runtime.py exceções) | 10 min | Proposto |
| Testes (8 cenários) | 30 min | Proposto |
| Relatórios (2 arquivos) | 10 min | Proposto |
| **TOTAL** | **~80 min** | **~1.5 horas** |

---

## 7. PRÓXIMOS PASSOS

✅ Essa proposta (aprovação visual)  
→ Implementação dos 4 pontos  
→ 8 testes de validação  
→ 2 relatórios finais (Phase1_Report + Phase1_Tests)  

---

**Status:** Pronto para Implementação

Aguardando aprovação para proceder aos 4 pontos de integração.
