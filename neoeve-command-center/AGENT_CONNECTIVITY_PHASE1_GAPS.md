# Agent Connectivity Phase 1 — Gaps & Homologation Assessment

**Data:** 2026-11-24  
**Auditoria:** Independente READ-ONLY  
**Recomendação Final:** ❌ **NÃO HOMOLOGAR** (Achados críticos bloqueiam)  

---

## GAPS ENCONTRADOS

### GAP 1: Multi-Tenant Isolation Quebrada 🔴 CRÍTICO

**Localização:** `backend/database/models.py:146-166`, `backend/app/services/agent_registry.py:144-146`

**Descrição:**
- Agent model é GLOBAL (sem tenant_id)
- AgentRegistry.get_agent() não filtra por tenant
- update_connectivity_state() afeta TODOS os tenants

**Impacto:**
```
Tenant A: marca agent-architect como OFFLINE
  ↓
Tenant B: consulta agent-architect
  ↓
Vê OFFLINE (errado para Tenant B)
```

**Causa Raiz:** Agent é entidade compartilhada (os 7 agentes são globais), mas status de conectividade deveria ser por-tenant.

**Solução Necessária (antes de homologação):**
```python
# OPÇÃO 1: Adicionar tenant_id a Agent
class Agent(Base):
    agent_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), primary_key=True)  # ← ADICIONAR
    connectivity_status = Column(String(32))
    
# OPÇÃO 2: Criar AgentTenantStatus tabela separada
class AgentTenantStatus(Base):
    agent_id = Column(String(64), ForeignKey("agents.agent_id"))
    tenant_id = Column(String(64), ForeignKey("tenants.tenant_id"))
    connectivity_status = Column(String(32))
    # ... (isolado por tenant)
```

**Severidade:** 🔴 CRÍTICO

---

### GAP 2: Health Check É One-Time (Não Contínuo) 🟠 ALTO

**Localização:** `backend/app/main.py:68-98`

**Descrição:**
- Health check ocorre APENAS no startup (lifespan)
- Se subscription expirar depois, agentes permanecem ONLINE
- Sem monitoramento periódico

**Impacto:**
```
Startup (10:00):
  health_check() → ONLINE ✅
  
Durante o dia (14:00):
  Subscription expira
  Agentes PERMANECEM ONLINE ⚠️
  
Executor indisponível, mas:
  Frontend exibe ONLINE
  Execuções falham com timeout
```

**Causa Raiz:** Health check integrado apenas em lifespan, não em background worker periódico.

**Solução Necessária (antes de homologação):**

Implementar heartbeat monitor periódico (Etapa 2):

```python
# Em Approval Scheduler ou novo background worker:
async def periodic_health_check():
    """Check agent health every 60 seconds."""
    while True:
        try:
            adapter = ClaudeCodeAdapter()
            health = adapter.health_check()
            
            db = next(get_db())
            if health["cli_available"] and health["subscription_valid"]:
                for agent_config in AgentRegistry.AGENTS.values():
                    AgentRegistry.update_connectivity_state(
                        db, agent_config["agent_id"], ConnectivityState.ONLINE
                    )
            else:
                # Mark all as UNKNOWN or OFFLINE
                for agent_config in AgentRegistry.AGENTS.values():
                    AgentRegistry.update_connectivity_state(
                        db, agent_config["agent_id"], ConnectivityState.UNKNOWN
                    )
        except Exception as e:
            logger.error(f"Periodic health check failed: {e}")
        
        await asyncio.sleep(60)  # Every 60 seconds
```

**Severidade:** 🟠 ALTO

---

### GAP 3: Classificação de Exceções Muito Ampla 🟠 ALTO

**Localização:** `backend/app/services/agent_runtime.py:364-367`

**Descrição:**
Substring matching (`.lower()`) busca por keywords que podem estar em mensagens não-relacionadas a conexão:

```python
is_connection_error = any(keyword in error_str for keyword in [
    "timeout", "connection", "refused", "unreachable", "unavailable",
    "socket", "network", "dns", "failed to connect"
])
```

**Falsos Positivos Identificados:**
1. `"Cannot connect to database: timeout"` → Classificado OFFLINE (deveria ser ERROR de BD)
2. `"Connection refused by business rule validation"` → Classificado OFFLINE (deveria ser ERROR de lógica)
3. `"Network interface timeout during data upload"` → Classificado OFFLINE (pode ser timeout de outro serviço)

**Falsos Negativos Identificados:**
1. `"Executor unavailable"` → Classificado ERROR (deveria ser OFFLINE)
2. `"Port 9000 not responding"` → Classificado ERROR (deveria ser OFFLINE)

**Impacto:**
```
Falso Positivo:
  Erro BD: "Connection refused: DB timeout"
  → Agent marcado OFFLINE
  → Não aceita execuções
  → Usuário vê agent como indisponível (falso)

Falso Negativo:
  Executor realmente down: "Port 9000 not responding"
  → Agent marcado ERROR (não OFFLINE)
  → Frontend mostra errado
  → Sem recupração automática
```

**Solução Necessária:**

Usar stack trace + contexto da execução:

```python
import traceback

except Exception as e:
    error_str = str(e).lower()
    tb = traceback.format_exc().lower()
    
    # Verificar se é REALMENTE erro de conexão do executor
    is_executor_connection = any([
        "executor" in error_str and ("timeout" in error_str or "refused" in error_str),
        "adapter" in error_str and ("unavailable" in error_str),
        "subprocess" in tb and ("timeout" in tb or "connection" in tb),
        "ProcessError" in str(type(e)) and "timeout" in error_str,
    ])
    
    # NÃO marcar OFFLINE se erro está relacionado a outro serviço
    is_other_service = any([
        "database" in error_str,
        "firestore" in error_str,
        "redis" in error_str,
        "external" in error_str,
    ])
    
    if is_executor_connection and not is_other_service:
        AgentRegistry.update_connectivity_state(db, agent_id, ConnectivityState.OFFLINE)
```

**Severidade:** 🟠 ALTO

---

### GAP 4: Testes São Unitários, Não de Integração 🟡 MÉDIO

**Localização:** `backend/test_phase1_connectivity.py`

**Descrição:**
- Testes propostos não possuem dependências instaladas (falha: ModuleNotFoundError)
- Testes simulam state transitions sem validar banco real
- Sem testes de integração com PostgreSQL real
- Sem testes de concorrência com múltiplas execuções

**Impacto:**
```
❌ Teste Unitário:
   def test_2_health_check_online():
       update_connectivity_state(db, agent_id, ONLINE)
       assert agent.connectivity_status == ONLINE
   # Passou! ✅
   
   Mas em produção:
   # update_connectivity_state() pode falhar (transaction, FK violation, etc)
   # Teste não pegou
```

**Causa Raiz:** Testes não rodam contra banco real, apenas contra mock/simulation.

**Solução Necessária:**

Implementar testes de integração:

```bash
# 1. Setup
docker run -d --name neoeve-test-db -e POSTGRES_PASSWORD=test postgres:15

# 2. Criar database de teste
createdb neoeve_test

# 3. Rodar migrations
alembic upgrade head

# 4. Rodar testes de integração
pytest backend/test_phase1_connectivity_integration.py -v

# 5. Limpar
dropdb neoeve_test
docker stop neoeve-test-db
```

Incluir testes:
- ✅ Health check marca agentes ONLINE em banco real
- ✅ Duas execuções concorrentes do mesmo agente não sobrescrevem estado
- ✅ Finally cleanup salva ERROR no banco quando agente em WORKING
- ✅ Conexão error→OFFLINE persiste em banco

**Severidade:** 🟡 MÉDIO

---

### GAP 5: Finally Cleanup Redundante Mas com Risk 🟡 MÉDIO

**Localização:** `backend/app/services/agent_runtime.py:431-446`

**Descrição:**
- Finally cleanup é redundante se exception handler já marcou ERROR
- Mas serve como safety net
- **RISCO:** Se exception ocorre DENTRO do except block (antes de update_operational_state), agente fica WORKING

**Exemplo de Risco:**
```python
except Exception as e:
    # Exceção aqui → pula update_operational_state()
    if is_connection_error:  # ← Falha aqui
        raise AnotherException()  # Oops
    
    # Nunca chega aqui:
    AgentRegistry.update_operational_state(db, agent_id, ERROR)

# Vai para finally:
finally:
    if agent.status == WORKING:  # Sim! Ainda WORKING
        update_operational_state(db, agent_id, ERROR)  # Salva
```

**Impacto:** Risco baixo mas real. Proteção adequada.

**Solução:** Já implementada. Apenas documentar a proteção.

**Severidade:** 🟡 MÉDIO

---

### GAP 6: Sem Teste de Concorrência Real 🟡 MÉDIO

**Localização:** Testes propostos não cobrem concorrência

**Descrição:**
- 13 testes propostos, nenhum testa duas execuções DO MESMO agent_id simultâneas
- Teste 8 testa "mixed availability", não concorrência de execução
- Risco: dois workers tentando update_operational_state() do mesmo agente simultaneamente

**Impacto:**
```
Worker A: execution_id_1 do agent-architect
  t=0: update_operational_state(WORKING)
  t=50ms: adapter.execute()
  
Worker B: execution_id_2 do agent-architect
  t=25ms: update_operational_state(WORKING)  ← Usa MESMO agent_id
  t=75ms: adapter.execute()

Race condition:
  A escreve status = WORKING
  B escreve status = WORKING (mesma coisa, ok)
  A termina: status = IDLE
  B termina: status = IDLE (certo)
  
MAS se A error:
  A escreve status = ERROR
  B escreve status = ERROR (correto)
  
MAS se ordering é:
  A escreve status = WORKING
  B escreve status = WORKING
  B escreve status = IDLE (completou primeiro)
  A escreve status = ERROR (errado! B passou mas A marcado ERROR)
```

**Solução Necessária:**

Adicionar testes de concorrência:

```python
def test_concurrent_executions_same_agent():
    """Duas execuções paralelas do mesmo agente."""
    import threading
    import time
    
    agent_id = "agent-architect"
    results = []
    
    def execute_task(exec_id, should_succeed):
        try:
            # Simula execution A e B
            AgentRegistry.update_operational_state(db, agent_id, WORKING)
            time.sleep(0.1)  # Simula execução
            
            if should_succeed:
                AgentRegistry.update_operational_state(db, agent_id, IDLE)
                results.append(("IDLE", exec_id))
            else:
                AgentRegistry.update_operational_state(db, agent_id, ERROR)
                results.append(("ERROR", exec_id))
        except Exception as e:
            results.append(("EXCEPTION", exec_id, str(e)))
    
    # Executar dois threads em paralelo
    t1 = threading.Thread(target=execute_task, args=("exec_1", True))
    t2 = threading.Thread(target=execute_task, args=("exec_2", False))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    # Verificar final state
    agent = AgentRegistry.get_agent(agent_id, db)
    # Estado final deve ser ERROR (última escrita)
    # ou IDLE dependendo de timing
    
    # Mas NÃO deve ser WORKING indefinidamente!
    assert agent.status != WORKING.value
```

**Severidade:** 🟡 MÉDIO

---

## RESUMO DE GAPS

| # | Gap | Severidade | Status | Requer Correção? |
|----|-----|-----------|--------|------------------|
| 1 | Multi-tenant isolation quebrada | 🔴 CRÍTICO | Bloqueador | ✅ SIM |
| 2 | Health check one-time | 🟠 ALTO | Bloqueador | ✅ SIM |
| 3 | Classificação de exceções ampla | 🟠 ALTO | Bloqueador | ✅ SIM |
| 4 | Testes unitários, não integração | 🟡 MÉDIO | Validação fraca | ✅ SIM |
| 5 | Finally cleanup redundante | 🟡 MÉDIO | Proteção existe | ⚠️ DOCUMENTAR |
| 6 | Sem teste de concorrência | 🟡 MÉDIO | Validação fraca | ✅ SIM |

---

## RECOMENDAÇÃO FINAL

### ❌ **NÃO HOMOLOGAR PHASE 1**

**Razões:**

1. **GAP 1 (Crítico):** Multi-tenant isolation quebrada é uma falha de segurança/isolamento que pode afetar múltiplos clientes. Não pode ir para produção.

2. **GAP 2 (Alto):** Health check one-time significa que agentes podem continuar marcados ONLINE mesmo após indisponibilidade. Requer implementação de heartbeat periódico.

3. **GAP 3 (Alto):** Classificação de exceções muito ampla causará falsos positivos/negativos que prejudicam monitoramento de agentes.

4. **Gaps 4, 6 (Médio):** Testes não são de integração e não cobrem concorrência. Sem validação real de comportamento.

---

## ROADMAP PARA HOMOLOGAÇÃO

**Ordem de Prioridade:**

```
BLOQUEADOR 1: Corrigir multi-tenant isolation (Gap 1)
  Tempo: 2-4 horas
  Risco: Alto (altera schema ou adiciona tabela)
  
BLOQUEADOR 2: Refinar classificação de exceções (Gap 3)
  Tempo: 1-2 horas
  Risco: Médio
  
BLOQUEADOR 3: Implementar health check periódico (Gap 2)
  Tempo: 2-3 horas (Etapa 2)
  Risco: Médio
  
VALIDAÇÃO: Implementar testes de integração (Gap 4, 6)
  Tempo: 3-4 horas
  Risco: Baixo (testes, não produção)
```

**Timeline Sugerida:**
- Corrigir Gaps 1 e 3: **Hoje** (4-6 horas)
- Implementar Gap 2: **Amanhã** (Etapa 2: Heartbeat, 2-3 horas)
- Adicionar testes de integração: **Amanhã** (3-4 horas)
- **Re-auditoria completa:** Após correções
- **Homologação:** Após re-auditoria passar

---

## PRÓXIMAS ETAPAS

### Imediatamente (Hoje)

**Ação 1: Resolver Multi-Tenant Isolation**

```
Opção A (Recomendada): Adicionar Agent_per_Tenant tabela
├─ Nova tabela: agent_tenant_status
├─ Chaves: (agent_id, tenant_id)
├─ Update AgentRegistry.get_agent() para aceitar tenant_id
└─ Update update_connectivity_state() para usar tenant_id

Opção B: Remover status de Agent para ExecutionStatus
├─ Mover connectivity_status para Execution
├─ Agent permanece global (apenas referência)
└─ Isolamento natural por Execution.tenant_id
```

**Ação 2: Refinar Exceções**

```
Substituir substring matching por:
├─ Stack trace analysis
├─ Exception type detection
├─ Service context validation
└─ Whitelist de erros "reais de conexão"
```

---

### Curto Prazo (Próximos 2 dias)

**Ação 3: Health Check Periódico (Etapa 2)**

```
Implementar background worker:
├─ Scheduler interval: 60 segundos
├─ Checa adapter.health_check()
├─ Atualiza connectivity_status
└─ Loga mudanças de estado
```

**Ação 4: Testes de Integração**

```
Criar test suite real:
├─ PostgreSQL real (não mock)
├─ Testa concurrent executions
├─ Valida estado em banco
└─ CI/CD pipeline
```

---

## CONCLUSÃO

Phase 1 foi implementada com boas intenções, MAS **3 Gaps críticos/altos bloqueiam homologação**:

1. ✋ **Multi-tenant isolation não funciona** (Crítico)
2. ✋ **Health check é ponto único de falha** (Alto)
3. ✋ **Exceções classificadas incorretamente** (Alto)

**Sem resolver esses 3, Phase 1 não é confiável para produção.**

Tempo estimado para corrigir: **8-12 horas**

Recomendação: Voltar para desenvolvimento, corrigir, re-auditar, depois homologar.

---

**Data:** 2026-11-24  
**Auditoria por:** Claude Haiku 4.5  
**Status:** ❌ Bloqueado para produção  
**Próximo passo:** Correção de Gaps críticos
