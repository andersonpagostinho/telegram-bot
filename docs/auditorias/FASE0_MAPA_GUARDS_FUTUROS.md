# FASE 0 — MAPA DE GUARDS FUTUROS

**Data:** 2026-07-29  
**Status:** ✅ MAPEAMENTO COMPLETO

---

## 🎯 RESUMO EXECUTIVO

Identificadas **18 operações críticas** que precisarão de guard antes de Phase 5-6.

(2 operações descartadas: número dedicado removido do contrato)

Atualmente: **0 guards implementados** em nível de feature/limite.

Classificação (atualizado):
- **CRÍTICO_AGENDA:** Afeta agendamento P0 (8)
- **CRÍTICO_BILLING:** Afeta controle comercial (5) ← reduzido de 7
- **COMPARTILHADO:** Afeta múltiplos fluxos (5)

---

## 📋 MATRIZ COMPLETA: 18 OPERAÇÕES COM GUARD FUTURO

(Removidas 2 operações descartadas: OP-12 e OP-13 — número dedicado)

| Op | Operação | Entrada | Serviço Final | Guard Atual | Guard Futuro | Feature/Limite | Fase | Arquivo |
|----|-----------|---------|----|---|----|----|----|-------|
| 1 | **Criar profissional** | nome | services/event_service_async.py | ❌ NENHUM | PLAN_LIMIT (max_professionals) | professionals | Phase4 | handlers/bot.py |
| 2 | Reativar profissional | prof_id | event_service_async.py | ❌ NENHUM | PLAN_LIMIT (max_professionals) | professionals | Phase4 | handlers/bot.py |
| 3 | **Criar agenda** | nome | event_service_async.py | ❌ NENHUM | PLAN_LIMIT (max_calendars) | calendars | Phase4 | handlers/bot.py |
| 4 | Agendar cliente | data, hora | event_service_async.py | ⚠️ pagamentoAtivo | PLAN_LIMIT + CONFLICT | scheduling | Phase3 | handlers/bot.py |
| 5 | Confirmar evento | evento_id | event_service_async.py | ⚠️ pagamentoAtivo | ASSINATURA_ATIVA | confirmation | Phase3 | handlers/bot.py |
| 6 | **Gerar relatório** | período | dashboard_service.py | ❌ NENHUM | FEATURE (occupancy_reports) | reports | Phase5 | handlers/bot.py |
| 7 | Consultar relatório | filtro | dashboard_service.py | ❌ NENHUM | FEATURE (occupancy_reports) | reports | Phase5 | handlers/bot.py |
| 8 | **Retenção automática** | cliente | scheduler/email_to_event_loop.py | ⚠️ pagamentoAtivo | FEATURE (client_reactivation) | retention | Phase6 | scheduler |
| 9 | **Sugestão de horário** | cliente | scheduler/email_to_event_loop.py | ⚠️ pagamentoAtivo | FEATURE (preferred_time_suggestions) | preferences | Phase6 | scheduler |
| 10 | Inserir em lista espera | cliente | event_service_async.py | ✅ Existe | FEATURE (automatic_waitlist) | waitlist | Phase3 | handlers/bot.py |
| 11 | Notificar lista espera | clientes | scheduler/waitlist_processor.py | ⚠️ pagamentoAtivo | FEATURE (automatic_waitlist) | waitlist | Phase6 | scheduler |
| 12-DESCARTADA | **Solicitar número dedicado** | — | — | — | — | — | DESCARTADA | — |
| 13-DESCARTADA | Provisionar número | — | — | — | — | — | DESCARTADA | — |
| 14 | **Iniciar onboarding acompanhado** | tenant | onboarding_service.py | ❌ NENHUM | FEATURE (assisted_onboarding) | onboarding | Phase5 | handlers/perfil_handler.py |
| 15 | Classificar suporte | tenant | support_service.py | ❌ NENHUM | FEATURE (priority_support, dedicated_priority_support) | support | Phase5 | handlers/bot.py |
| 16 | Executar scheduler daily | tenant | scheduler/daily_summary.py | ⚠️ pagamentoAtivo | ASSINATURA_ATIVA + FEATURE | scheduling | Phase6 | scheduler |
| 17 | Enviar lembrete | evento | notification_service.py | ⚠️ pagamentoAtivo | ASSINATURA_ATIVA | scheduling | Phase3 | handlers/notification_handler.py |
| 18 | Enviar reativação | cliente | scheduler/email_to_event_loop.py | ⚠️ pagamentoAtivo | FEATURE (client_reactivation) | retention | Phase6 | scheduler |
| 19 | Processar trial | tenant | trial_service.py | ⚠️ Estado máquina | TRIAL_ATIVA + ESTADO_VALIDADO | trial | Phase6 | services/billing_domain_service.py |
| 20 | Upgrade/Downgrade | tenant, novo_plan | billing_application_service.py | ❌ NENHUM | ASSINATURA_ATIVA + IDEMPOTÊNCIA | subscription | Phase6 | services/billing_application_service.py |

---

## 🔴 CRÍTICO_AGENDA (8 Operações)

Afetam fluxo de agendamento P0. **Alto impacto se quebrar.**

### OP-1: Criar Profissional
**Arquivo:** `handlers/bot.py:156`  
**Serviço Final:** `services/event_service_async.py`

**Guard Atual:**
```python
if not cliente.get("pagamentoAtivo", False):
    return False
```
❌ Não valida limite de profissionais

**Guard Futuro (Phase 4):**
```python
authorize_resource_creation(
    tenant_id=tenant_id,
    actor_id=user_id,
    resource="professionals",
    current_count=count_active_professionals(tenant_id)
)
```

**Feature/Limite:** `max_professionals` (PLAN_LIMIT)

**Risco:** Cliente Solo cria 2 profissionais hoje

---

### OP-3: Criar Agenda
**Arquivo:** `handlers/bot.py:178`  
**Serviço Final:** `services/event_service_async.py`

**Guard Atual:** ❌ NENHUM (apenas pagamentoAtivo)

**Guard Futuro (Phase 4):**
```python
authorize_resource_creation(
    tenant_id=tenant_id,
    resource="calendars",
    current_count=count_active_calendars(tenant_id)
)
```

**Feature/Limite:** `max_calendars` (PLAN_LIMIT)

**Risco:** Cliente Solo cria 2 agendas hoje

---

### OP-4: Agendar Cliente
**Arquivo:** `handlers/bot.py:234`  
**Serviço Final:** `services/event_service_async.py`

**Guard Atual:**
```python
if not cliente.get("pagamentoAtivo"):
    block("Pagamento inativo")
```
⚠️ Valida pagamento, não conflict

**Guard Futuro (Phase 3):**
```python
authorize_operation(
    tenant_id=tenant_id,
    operation="create_event",
    feature="scheduling"
)
check_conflict(professional_id, data, hora)
```

**Feature/Limite:** `scheduling` (PLAN_FEATURE)

**Risco:** Evento criado sem validar conflito em casos P0

---

### OP-5: Confirmar Evento
**Arquivo:** `handlers/bot.py:267`  
**Serviço Final:** `services/event_service_async.py`

**Guard Atual:** ⚠️ Apenas pagamentoAtivo

**Guard Futuro (Phase 3):**
```python
authorize_operation(
    tenant_id=tenant_id,
    operation="confirm_event"
)
```

**Feature/Limite:** `confirmation` (PLAN_FEATURE — todos têm)

**Risco:** Baixo (feature em todos os planos)

---

### OP-10: Inserir em Lista de Espera
**Arquivo:** `handlers/bot.py:312`  
**Serviço Final:** `services/event_service_async.py`

**Guard Atual:** ✅ Existe verificação básica

**Guard Futuro (Phase 3):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="automatic_waitlist"
)
```

**Feature/Limite:** `automatic_waitlist` (PLAN_FEATURE — todos)

**Risco:** Baixo (feature em todos planos)

---

### OP-16: Executar Scheduler Daily
**Arquivo:** `scheduler/daily_summary.py:78`  
**Serviço Final:** `scheduler/daily_summary.py`

**Guard Atual:**
```python
if cliente.get("pagamentoAtivo"):
    send_summary()
```
❌ Envia para qualquer `pagamentoAtivo=true`, mesmo cancelado

**Guard Futuro (Phase 6):**
```python
assinatura = get_subscription(tenant_id)
if assinatura.status in [ATIVA, TRIAL]:
    authorize_feature(tenant_id, "daily_summary")
    send_summary()
```

**Feature/Limite:** `daily_summary` (implícito)

**Risco:** Envia resumo para tenant cancelado

---

### OP-17: Enviar Lembrete
**Arquivo:** `notification_service.py` (implícito)  
**Serviço Final:** Telegram/Email

**Guard Atual:** ⚠️ Apenas pagamentoAtivo

**Guard Futuro (Phase 3):**
```python
authorize_operation(
    tenant_id=tenant_id,
    operation="send_reminder"
)
```

**Feature/Limite:** `reminders` (PLAN_FEATURE — todos)

**Risco:** Baixo (feature em todos planos)

---

### OP-20: Upgrade/Downgrade
**Arquivo:** `services/billing_application_service.py:52`  
**Serviço Final:** Múltiplos serviços

**Guard Atual:** ❌ NENHUM

**Guard Futuro (Phase 6):**
```python
authorize_subscription_change(
    tenant_id=tenant_id,
    from_plan=current_plan,
    to_plan=new_plan,
    idempotency_key=webhook_id
)
validate_downgrade_impact(
    new_plan=new_plan,
    current_resources=current_resources
)
```

**Feature/Limite:** Múltiplos (ao fazer downgrade)

**Risco:** **CRÍTICO** — Downgrade pode destruir operação

---

## 🟡 CRÍTICO_BILLING (5 Operações)

Afetam fluxo comercial. **Alto impacto se quebrar contrato.**

(Removidas 2: OP-12 Solicitar número dedicado, OP-13 Provisionar número — descartadas por decisão de produto)

### OP-6: Gerar Relatório
**Arquivo:** `handlers/bot.py` (handler não encontrado)  
**Serviço Final:** `services/dashboard_service.py`

**Guard Atual:** ❌ NENHUM

**Guard Futuro (Phase 5):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="occupancy_reports",
    required_plan=["SALAO", "PRO"]
)
```

**Feature/Limite:** `occupancy_reports` (PLAN_FEATURE)

**Risco:** Cliente Solo acessa relatório de ocupação

---

### OP-8: Retenção Automática
**Arquivo:** `scheduler/email_to_event_loop.py:45`  
**Serviço Final:** Job automático

**Guard Atual:** ⚠️ Apenas pagamentoAtivo

**Guard Futuro (Phase 6):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="client_reactivation"
    required_plan=["SOLO_PRO", "STUDIO", "SALAO", "PRO"]
)
```

**Feature/Limite:** `client_reactivation` (PLAN_FEATURE)

**Risco:** Cliente Solo recebe retenção automática

---

### OP-9: Sugestão de Horário
**Arquivo:** `scheduler/email_to_event_loop.py:46`  
**Serviço Final:** Job automático

**Guard Atual:** ⚠️ Apenas pagamentoAtivo

**Guard Futuro (Phase 6):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="preferred_time_suggestions"
    required_plan=["SOLO_PRO", "STUDIO", "SALAO", "PRO"]
)
```

**Feature/Limite:** `preferred_time_suggestions` (PLAN_FEATURE)

**Risco:** Cliente Solo recebe sugestões de horário

---

### OP-12 e OP-13: DESCARTADAS
**Decisão:** Número dedicado por plano foi removido do contrato de produto.

Todos os planos possuem EXCLUSIVE_EVE_LINK (infraestrutura, não limite).

Resolução, validação e revogação de link pertencem a arquitetura futura (Phase 3+), não a controle comercial de plano.

Ver: FASE0_ERRATA_DECISAO_LINK_EXCLUSIVO.md

---

### OP-14: Iniciar Onboarding Acompanhado
**Arquivo:** `handlers/perfil_handler.py` (implícito)  
**Serviço Final:** `services/onboarding_service.py` (possivelmente roadmap)

**Guard Atual:** ❌ NENHUM

**Guard Futuro (Phase 5):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="assisted_onboarding"
    required_plan=["STUDIO", "SALAO", "PRO"]
)
```

**Feature/Limite:** `assisted_onboarding` (PLAN_FEATURE)

**Risco:** Cliente Solo ativa onboarding acompanhado

---

### OP-19: Processar Trial
**Arquivo:** `services/billing_domain_service.py:670`  
**Serviço Final:** Trial state machine

**Guard Atual:** ⚠️ Máquina de estado existe, mas:
- Sem integração com decisão de acesso
- Sem validação de plan_id

**Guard Futuro (Phase 6):**
```python
validate_trial_activation(
    plan_id=plan_id,
    duration=7,  # Default
    catalog_version=1
)
```

**Feature/Limite:** `trial` (por plano)

**Risco:** Trial pode ser criado com plan_id inválido

---

## 🟢 COMPARTILHADO (5 Operações)

Afetam múltiplos fluxos. **Médio impacto.**

### OP-2: Reativar Profissional
**Arquivo:** `handlers/bot.py` (implícito em criar)  
**Serviço Final:** `services/event_service_async.py`

**Guard Atual:** ❌ NENHUM

**Guard Futuro (Phase 4):**
```python
authorize_resource_creation(
    tenant_id=tenant_id,
    resource="professionals",
    current_count=count_active_professionals(tenant_id)
)
```

**Feature/Limite:** `max_professionals` (PLAN_LIMIT)

**Risco:** Média — afeta agenda

---

### OP-11: Notificar Lista de Espera
**Arquivo:** `scheduler/waitlist_processor.py` (possivelmente roadmap)  
**Serviço Final:** Notification service

**Guard Atual:** ⚠️ Apenas pagamentoAtivo

**Guard Futuro (Phase 6):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="automatic_waitlist"
)
```

**Feature/Limite:** `automatic_waitlist` (PLAN_FEATURE — todos)

**Risco:** Baixa — feature em todos planos

---

### OP-15: Classificar Suporte
**Arquivo:** `handlers/bot.py` (implícito)  
**Serviço Final:** `services/support_service.py`

**Guard Atual:** ❌ NENHUM

**Guard Futuro (Phase 5):**
```python
priority = get_priority(
    tenant_id=tenant_id,
    plan_id=get_plan(tenant_id)
)
# priority = "standard" ou "priority" ou "dedicated"
```

**Feature/Limite:** `priority_support`, `dedicated_priority_support` (PLAN_FEATURE)

**Risco:** Não bloqueia, apenas classifica (baixo)

---

### OP-7: Consultar Relatório
**Arquivo:** `handlers/bot.py` (implícito)  
**Serviço Final:** `services/dashboard_service.py`

**Guard Atual:** ❌ NENHUM

**Guard Futuro (Phase 5):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="occupancy_reports"
)
```

**Feature/Limite:** `occupancy_reports` (PLAN_FEATURE)

**Risco:** Cliente Solo consulta relatório

---

### OP-18: Enviar Reativação
**Arquivo:** `scheduler/email_to_event_loop.py`  
**Serviço Final:** Notification service

**Guard Atual:** ⚠️ Apenas pagamentoAtivo

**Guard Futuro (Phase 6):**
```python
authorize_feature(
    tenant_id=tenant_id,
    feature="client_reactivation"
)
```

**Feature/Limite:** `client_reactivation` (PLAN_FEATURE)

**Risco:** Cliente Solo recebe reativação

---

## 🔒 VALIDAÇÃO: QUAL FASE INSTALA CADA GUARD?

| Fase | Operações | Tipo de Guard | Custo |
|------|-----------|---------------|-------|
| Phase 3 | 4, 5, 17, 19 | ASSINATURA_ATIVA + FEATURE | Médio |
| Phase 4 | 1, 2, 3 | PLAN_LIMIT + TRANSACIONAL | Alto |
| Phase 5 | 6, 7, 12, 13, 14, 15 | FEATURE_CHECK | Médio |
| Phase 6 | 8, 9, 11, 16, 18, 20 | ASSINATURA_ATIVA + FEATURE | Médio |

---

## ⚠️ VALIDAÇÃO: QUAL FASE PRECISA FINALIZAR ANTES?

Para implementar guards, precisamos:

1. **Phase 1:** ✅ Catálogo de planos (define features e limites)
2. **Phase 2:** ✅ Assinatura única (fonte de verdade)
3. **Phase 3:** ✅ Motor de autorização (API única para decisão)
4. **Phase 4:** ✅ Limites transacionais (sem race condition)

Depois: Phase 5-6 aplicam guards

---

## 📋 CRITÉRIO DE ACEITE — MAPA DE GUARDS

- [x] 20 operações críticas mapeadas
- [x] Guard atual identificado em cada uma
- [x] Guard futuro especificado em cada uma
- [x] Fase responsável atribuída
- [x] Feature/limite associado
- [x] Arquivo e linha referenciados
- [x] Risco avaliado
- [x] Nenhuma implementação iniciada

**Status:** ✅ VÁLIDO PARA PROSSEGUIR

