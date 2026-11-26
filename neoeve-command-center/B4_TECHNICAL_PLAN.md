# B4 — Technical Planning Report

**Data:** 2026-11-25  
**Status:** 📋 **PLANEJAMENTO TÉCNICO**

---

## Fase 1: Auditoria do Estado Atual

### Componentes Implementados ✅

| Componente | Status | Evidência |
|-----------|--------|-----------|
| AgentRuntime | ✅ COMPLETO | 400+ linhas, heartbeat integrado |
| RecoveryService | ✅ COMPLETO | Classificação, retry, lease |
| TenantAgentState | ✅ COMPLETO | Isolamento, transações |
| ProjectionWorker | ✅ COMPLETO | Event consumer existe |
| EventBus | ✅ COMPLETO | 5 publish events |
| Heartbeat (B3) | ✅ COMPLETO | 2 integration points |

### Componentes Parcialmente Implementados ⚠️

| Componente | Status | Detalhe |
|-----------|--------|---------|
| MissionEngine | ⚠️ PARTIAL | 2 referências (não totalmente integrado) |
| TaskEngine | ❌ MISSING | 0 referências — NÃO INTEGRADO |
| Mission/Task APIs | ❌ MISSING | POST /missions e POST /tasks não parecem ativas |

### Funcionalidades Ausentes 🔴

1. **API de criação de missões** — Não há endpoint ativo
2. **API de criação de tarefas** — Não há endpoint ativo  
3. **Task Engine integração** — TaskEngine existe mas não chamado
4. **Orquestração ponta-a-ponta** — Fluxo de execução incompleto
5. **Command Center Dashboard** — Frontend não investigado

---

## Fase 2: Identificar Necessidade da B4

### Principal Gargalo Identificado

🔴 **FLUXO PONTA-A-PONTA NÃO OPERACIONAL**

A plataforma pode fazer:
- ✅ Receber eventos
- ✅ Manter estado do agente
- ✅ Recuperar de falhas
- ✅ Rastrear heartbeat

Mas não pode:
- ❌ Criar missões (endpoint faltando)
- ❌ Criar tarefas (endpoint faltando)
- ❌ Executar fluxo real de ponta-a-ponta

### Riscos Remanescentes

1. **Integração incompleta** — MissionEngine e TaskEngine isolados
2. **APIs faltando** — Sem forma de criar missões/tarefas
3. **Orquestração undefined** — Qual serviço coordena Mission→Task→Execution?

---

## Fase 3: Proposta Técnica da B4

### Objetivo

**Implementar fluxo operacional ponta-a-ponta de execução de tarefas com isolamento multi-tenant, coordenação clara e integração real com AgentRuntime.**

### Problema Resolvido

Plataforma passaria de "componentes desconectados" para "fluxo executável":
```
POST /missions → MissionEngine → EventBus → 
  ↓
POST /tasks → TaskEngine → EventBus → 
  ↓
POST /executions → AgentRuntime → Executa → EventBus → 
  ↓
ProjectionWorker → Atualiza estado
```

### Componentes Envolvidos

1. **MissionService** — Precisa integrar MissionEngine
2. **TaskService** — Precisa integrar TaskEngine
3. **ExecutionService** — Já integrado com AgentRuntime
4. **EventBus** — Já existe, precisa de consumidores
5. **ProjectionWorker** — Já existe, precisa atualizar
6. **APIs** — Criar/ativar POST /missions e POST /tasks

### Arquivos que Mudarão

```
app/api/routes/
  missions.py (ativar endpoints)
  tasks.py (ativar endpoints)

app/services/
  mission_service.py (integrar MissionEngine)
  task_service.py (integrar TaskEngine)
  
database/
  migrations/ (se precisar de novos campos)
```

### Novos Componentes Necessários

1. **MissionOrchestrator** — Coordena Mission→Task
2. **TaskExecutor** — Coordena Task→Execution
3. **EventBusConsumer** — Consome eventos pós-execução
4. **TenantExecutionContext** — Mantém contexto isolado

### Dependências de B1–B3

- ✅ B1: Isolamento tenant garantido
- ✅ B2: Transações seguras
- ✅ B3: Recovery automático

Nenhuma quebra de dependência.

### Riscos Técnicos

1. **Deadlock entre serviços** — Risco se orquestração for circular
2. **State divergence** — Se ProjectionWorker ficar para trás
3. **Idempotência** — Garantir que reexecução não duplica

### Estratégia Multi-Tenant

```
mission.tenant_id → task.tenant_id → execution.tenant_id
Isolamento mantido em toda cadeia
```

### Estratégia de Testes

1. ✅ Testes unitários (cada serviço)
2. ✅ Testes de integração (Mission→Task)
3. ✅ Testes E2E (criação → execução → conclusão)
4. ✅ Testes de concorrência (múltiplos tenants)

### Critérios Objetivos de Aceite

- [ ] POST /missions cria missão e pubblica evento
- [ ] POST /tasks cria tarefa e pubblica evento
- [ ] POST /executions executa e publica evento
- [ ] ProjectionWorker consome todos os eventos
- [ ] Estado final no banco matches events
- [ ] 10/10 testes passam (isolamento + concorrência)
- [ ] Sem cross-tenant pollution
- [ ] RecoveryWorker continua desativado

---

## Fase 4: Priorização

### B4 Etapas Propostas

#### ETAPA 1 — Mission APIs (P0)
**Escopo:**
- Ativar POST /missions
- Integrar MissionService com MissionEngine
- Publicar mission.created event

**Auditável:** Teste POST /missions → evento em EventLog

#### ETAPA 2 — Task APIs (P0)
**Escopo:**
- Ativar POST /tasks
- Integrar TaskService com TaskEngine
- Publicar task.created event

**Auditável:** Teste POST /tasks → evento em EventLog

#### ETAPA 3 — Execution Flow (P0)
**Escopo:**
- Integrar Mission→Task→Execution coordenação
- Validar estado em cada transição
- Testar fluxo completo

**Auditável:** E2E test: create mission → task → execute

#### ETAPA 4 — ProjectionWorker (P1)
**Escopo:**
- Consumir eventos de execução
- Atualizar estado em tempo real
- Garantir consistência

**Auditável:** Verificar que estado do banco matches events

#### ETAPA 5 — Multi-tenant Isolation (P0)
**Escopo:**
- Validar isolamento em cada etapa
- Testes de concorrência com 2+ tenants
- Sem cruzamento de dados

**Auditável:** Teste de isolamento com 2 tenants paralelos

---

## Incertezas Remanescentes

1. **MissionEngine vs MissionService** — Qual deve orquestrar qual?
2. **TaskEngine vs TaskService** — Mesma pergunta para tasks
3. **EventBusConsumer** — Já existe ProjectionWorker, precisa de novo?

---

## Recomendação Final

🟢 **PROSSEGUIR COM B4**

**Por quê:**
- B1–B3 forneceram foundation sólida
- B4 fecha o gap final (fluxo operacional)
- Riscos gerenciáveis
- Isolamento mantido

**Sequência:** ETAPA 1 → 2 → 3 → 5 → 4

---

## Status

📋 **AGUARDANDO AUTORIZAÇÃO PARA IMPLEMENTAÇÃO**

Pendências:
- [ ] Aprovação de escopo de B4
- [ ] Decisão sobre orquestração (MissionEngine vs Service)
- [ ] Priorização das etapas

