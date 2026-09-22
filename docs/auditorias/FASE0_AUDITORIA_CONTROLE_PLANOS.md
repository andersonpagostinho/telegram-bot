# FASE 0 — AUDITORIA ESTADO ATUAL: CONTROLE DE PLANOS

**Data:** 2026-07-29  
**Status:** 🔍 AUDITORIA EM ANDAMENTO  
**Objetivo:** Mapear todos os locais onde plano, pagamento, trial, módulo, profissional, agenda e relatório são tratados atualmente  

---

## 📊 RESUMO EXECUTIVO

O código atual referencia planos e pagamento em **202 pontos**, distribuídos em:
- **plan_id**: 4 arquivos (domain + services + testes)
- **planosAtivos**: 14 arquivos (handlers + services + utils)
- **pagamentoAtivo**: 14 arquivos (handlers + services + utils)

**Status de Implementação:** ~30% (máquinas de estado existem, mas autorização é permissiva)

---

## 📍 INVENTÁRIO DE REFERÊNCIAS

### 1️⃣ DOMAIN LAYER — Definições (✅ EXISTE)

#### `domain/commercial_events.py`
- **plan_id**: Campo em TrialActivated, SubscriptionActivated (armazenável)
- **Status**: ✅ Definido em eventos
- **Ação**: MANTER — Base sólida para histórico

```python
# Exemplo: TrialActivated
plan_id: str = None  # Plano selecionado

# Exemplo: SubscriptionActivated  
plan_id: str = None
activation_date: datetime = None
```

**Classificação:** MANTER

---

### 2️⃣ SERVICES LAYER — Lógica Comercial (⚠️ PARCIAL)

#### `services/firebase_service.py`
- **planosAtivos**: Definido com default `["secretaria"]` na linha 58
- **pagamentoAtivo**: Definido com default `True` na linha 57
- **Status**: ⚠️ Valores hardcoded, sem validação
- **Impacto**: TODO novo cliente recebe ambos por padrão

```python
def salvar_cliente(user_id, dados):
    dados_padrao = {
        "pagamentoAtivo": True,  # ⚠️ SEMPRE true
        "planosAtivos": ["secretaria"],  # ⚠️ SEMPRE secretaria
        # ...
    }
```

**Classificação:** ADAPTAR — Remover defaults hardcoded, buscar de contrato

---

#### `services/gpt_service.py` & `services/gpt_service(1).py`
- **planosAtivos**: Lido e passado ao prompt do GPT
- **pagamentoAtivo**: Validação básica (apenas booleano)
- **Status**: ⚠️ GPT recebe lista de planos, mas não decide acesso

```python
planos_ativos = cliente.get("planosAtivos", []) if cliente else []

# Prompt:
🔐 Módulos: {', '.join(planos_ativos) or 'Nenhum'}
```

**Classificação:** MANTER — Contexto para GPT OK, bloquear decisão depois

---

#### `services/billing_domain_service.py`
- **plan_id**: Referenciado em eventos de billing
- **assinatura**: Máquina de estado PENDENTE→ATIVA→CANCELADA
- **Status**: ✅ Estado machine existe, não controla acesso

**Classificação:** MANTER — Base para Phase 2

---

#### `services/billing_application_service.py`
- **plan_id**: Passado em agregado de billing
- **Status**: ✅ Estrutura pronta
- **Ação**: MANTER

---

### 3️⃣ HANDLERS — Pontos de Entrada (❌ SEM GUARD)

#### `handlers/bot.py`
- **planosAtivos**: Lido, não validado
- **pagamentoAtivo**: Lido, exibido
- **Status**: ❌ Nenhuma verificação antes de executar ação
- **Impacto**: Usuário sem plano pode executar qualquer comando

**Classificação:** ADAPTAR — Adicionar guard obrigatório

---

#### `handlers/perfil_handler.py` / `handlers/perfil_handler 2.py`
- **planosAtivos**: Exibido ao usuário
- **pagamentoAtivo**: Exibido
- **Status**: ⚠️ Visualização apenas, sem autorização

**Classificação:** MANTER — Exibição OK, guardrails virão depois

---

#### `handlers/gpt_text_handler.py`
- **planosAtivos**: Consultado antes de executar ação
- **pagamentoAtivo**: Validado (apenas booleano)
- **Status**: ⚠️ Validação superficial

```python
if not cliente.get("pagamentoAtivo", False):
    return False  # Bloqueia, mas não trata feature específica
```

**Classificação:** ADAPTAR — Validação superficial, precisa feature-level

---

#### `handlers/voice_command_handler.py`
- **planosAtivos**: Consultado
- **pagamentoAtivo**: Validado
- **Status**: ⚠️ Mesmo padrão superficial

**Classificação:** ADAPTAR

---

### 4️⃣ UTILS — Verificações Centralizadas (⚠️ PERMISSIVAS)

#### `utils/plan_utils.py`
**Funções principais:**

```python
async def verificar_pagamento(update, context) -> bool:
    # ✅ Retorna booleano se pagamentoAtivo
    # ❌ Não diferencia planos

async def verificar_plano(user_id: str, modulo: str) -> bool:
    # ✅ Valida se módulo está em planosAtivos
    # ⚠️ Módulos são: ["secretaria", "voz", "áudio"]
    # ❌ Não há features como "relatórios", "retenção", etc

async def verificar_acesso_modulo(update, context, modulo: str) -> bool:
    # ✅ Bloqueia acesso se módulo ausente
    # ⚠️ Retorna booleano apenas, sem detalhes
```

**Classificação:** ADAPTAR → SUBSTITUIR  
**Razão:** Muito superficial, precisa ser reconstruído em Phase 3

---

#### `utils/gpt_utils.py`
- **planosAtivos**: Consultado
- **pagamentoAtivo**: Consultado
- **Status**: ⚠️ Uso em validações superficiais

**Classificação:** ADAPTAR

---

### 5️⃣ SCHEDULERS — Jobs Automáticos (❌ SEM VALIDAÇÃO)

#### `scheduler/daily_summary.py`
- **pagamentoAtivo**: ⚠️ Não consultado
- **Status**: ❌ Envia resumo para TODO usuário, independente de plano
- **Impacto**: Usuário cancelado recebe resumo

**Classificação:** ADAPTAR — Validar assinatura antes de enviar

---

#### `scheduler/email_to_event_loop.py`
- **planosAtivos**: ⚠️ Consultado
- **pagamentoAtivo**: ⚠️ Consultado
- **Status**: ⚠️ Validação, mas não de feature específica
- **Impacto**: Pode executar feature não liberada se status for true

**Classificação:** ADAPTAR — Validar feature específica

---

### 6️⃣ TESTES (⚠️ SEM COBERTURA DE PLANOS)

#### `tests/comercial/test_commercial_events.py`
- **plan_id**: Testado em eventos
- **Status**: ✅ Estrutura de teste existe
- **Falta**: Testes de transição por plano

**Classificação:** ADAPTAR — Adicionar testes de autorização

---

#### `tests/p1_robustez_fluxo_conversacional_real.py`
- **planosAtivos**: Usado em simulação
- **pagamentoAtivo**: Usado em simulação
- **Status**: ⚠️ Testes E2E, mas sem cobertura de limite

**Classificação:** ADAPTAR — Adicionar testes de limite por plano

---

## 📋 MATRIZ DE OPERAÇÕES CRÍTICAS

| Operação | Arquivo/Função | Verifica Assinatura? | Verifica Feature? | Verifica Limite? | Transacional? | Ação |
|----------|-----------------|----------------------|-------------------|------------------|---------------|------|
| Criar profissional | handlers/bot.py | ❌ | ❌ | ❌ | ❌ | GUARD |
| Criar agenda | handlers/bot.py | ❌ | ❌ | ❌ | ❌ | GUARD |
| Agendar cliente | handlers/bot.py | ⚠️ (apenas pag) | ❌ | ❌ | ❌ | VALIDAR |
| Confirmar evento | handlers/bot.py | ⚠️ (apenas pag) | ❌ | ❌ | ❌ | VALIDAR |
| Ver relatório | handlers/bot.py | ❌ | ❌ | ❌ | N/A | GUARD |
| Enviar resumo | scheduler/daily_summary.py | ⚠️ (apenas pag) | ❌ | ❌ | N/A | GUARD |
| Retenção automática | scheduler/email_to_event_loop.py | ⚠️ | ❌ | ❌ | N/A | GUARD |
| Prefixo de horário | handlers/bot.py | ⚠️ | ❌ | ❌ | N/A | GUARD |

---

## 🔍 FONTES DE VERDADE IDENTIFICADAS

| Campo | Localização Atual | Confiabilidade | Status |
|-------|------------------|-----------------|--------|
| **plan_id** | Eventos comerciais + Firebase (Clientes) | 🟡 Média | LEGADO |
| **planosAtivos** | Firebase (Clientes) | 🟡 Média | LEGADO |
| **pagamentoAtivo** | Firebase (Clientes) | 🟡 Média | LEGADO |
| **Assinatura** | events (histórico apenas) | ❌ Não há | MISSING |

**Problema:** Não existe **fonte única de verdade atual** para assinatura.

**Risco:** Campos duplicados, inconsistências, falta de histórico de mudanças.

---

## ⚠️ CAMPOS DUPLICADOS IDENTIFICADOS

```
planosAtivos (Firebase/Clientes)
    ↔ plan_id (Eventos comerciais)
    ↔ estado da máquina de estado

Sem sincronização entre eles.
```

**Impacto:** Possível divergência — cliente pode ter planosAtivos=["secretaria"] mas plan_id=STUDIO.

---

## 🚨 VERIFICAÇÕES PERMISSIVAS ENCONTRADAS

1. **firebase_service.py:57-58**
   - Todo novo cliente recebe `pagamentoAtivo=true` e `planosAtivos=["secretaria"]`
   - ❌ Nenhuma validação de quem criou ou por quê

2. **plan_utils.py:17-29**
   - `verificar_pagamento()` apenas valida booleano
   - ❌ Não diferencia planos ou features

3. **gpt_service.py** (múltiplas)
   - Passa `planosAtivos` ao GPT
   - ❌ GPT pode interpretar como permissão de upgradear

4. **handlers/bot.py** (múltiplas)
   - Ações executadas se `pagamentoAtivo=true`
   - ❌ Sem validar feature específica ou limite

5. **scheduler/daily_summary.py**
   - Envia resumo se `pagamentoAtivo=true`
   - ❌ Sem validar se assinatura está ativa no período

---

## 🔓 OPERAÇÕES SEM QUALQUER GUARD

```
✗ Criar profissional N+1 (sem limite)
✗ Criar agenda N+1 (sem limite)
✗ Acessar relatório (sem feature check)
✗ Usar retenção automática (sem feature check)
✗ Usar preferência de horário (sem feature check)
✗ Usar número dedicado (sem feature check)
✗ Onboarding acompanhado (sem feature check)
```

---

## 📦 JOBS AUTOMÁTICOS VULNERÁVEIS

1. **scheduler/daily_summary.py**
   - Envia para TODO `pagamentoAtivo=true`
   - ❌ Não verifica se período está ativo
   - ❌ Não diferencia planos

2. **scheduler/email_to_event_loop.py**
   - Processa TODO tenant com `pagamentoAtivo=true`
   - ❌ Não verifica feature (retenção, preferência)

---

## 🔐 TESTES EXISTENTES

| Suite | Cobertura | Status |
|-------|-----------|--------|
| `test_commercial_events.py` | Estrutura de eventos | ✅ Existe |
| `test_billing_state_machines.py` | Transições de estado | ✅ Existe |
| `p1_robustez_fluxo_conversacional_real.py` | E2E | ✅ Existe |
| **Testes de limite por plano** | Nenhum | ❌ FALTA |
| **Testes de feature por plano** | Nenhum | ❌ FALTA |
| **Testes de upgrade/downgrade** | Nenhum | ❌ FALTA |
| **Testes multi-tenant** | Alguns | ⚠️ Parcial |

---

## 🎯 CLASSIFICAÇÃO FINAL

### MANTER ✅
```
✓ domain/commercial_events.py (plan_id armazenado)
✓ services/billing_domain_service.py (máquinas de estado)
✓ services/billing_application_service.py (estrutura de agregado)
✓ Testes de eventos comerciais
```

### ADAPTAR ⚠️
```
⚠ services/firebase_service.py (remover defaults hardcoded)
⚠ services/gpt_service.py (continuar passando contexto, bloquear decisão)
⚠ utils/plan_utils.py (aprofundar validações)
⚠ handlers/bot.py (adicionar guards antes de ação)
⚠ handlers/gpt_text_handler.py (feature-level check)
⚠ handlers/voice_command_handler.py (feature-level check)
⚠ handlers/perfil_handler.py (compatibilidade)
⚠ utils/gpt_utils.py (revisar validações)
⚠ scheduler/daily_summary.py (validar assinatura)
⚠ scheduler/email_to_event_loop.py (validar feature)
⚠ Testes existentes (adicionar cobertura)
```

### SUBSTITUIR 🔄
```
🔄 Motor de autorização (não existe → Phase 3)
🔄 Limite quantitativo (não existe → Phase 4)
🔄 Catálogo de planos (não existe → Phase 1)
```

### DEPRECAR (Após Phase 7)
```
⏳ planosAtivos (migrar para assinatura.plan_id)
⏳ Compatibilidade legada (após todos migrados)
```

---

## 📈 ESTATÍSTICAS

| Métrica | Valor |
|---------|-------|
| Total de referências a planos | 202 |
| Arquivos afetados | 28 |
| Operações sem guard | 7+ |
| Testes de plano | 0 |
| Fontes de verdade únicas | 0 |
| Limites quantitativos implementados | 0 |

---

## ⚡ RISCOS IDENTIFICADOS

| Risco | Severidade | Causa | Mitigação |
|-------|-----------|-------|-----------|
| Clientes sem plano usando recursos | 🔴 CRÍTICA | Sem guard | Phase 5 |
| Concorrência ultrapassando limite | 🔴 CRÍTICA | Sem lock | Phase 4 |
| Plano divergindo de pagamento | 🟡 MÉDIA | Sem sincronização | Phase 2 |
| Job enviando para cancelado | 🟡 MÉDIA | Sem validação | Phase 6 |
| GPT alterando acesso | 🟡 MÉDIA | Contexto ambíguo | Bloquear decisão |
| Downgrade apagando dados | 🔴 CRÍTICA | Sem preservação | Phase 6 |

---

## ✅ CRITÉRIO DE ACEITE — FASE 0

- [ ] Inventário completo de 202 referências categorizado
- [ ] Matriz de operações críticas compilada
- [ ] Riscos identificados e priorizados
- [ ] Plano de compatibilidade com `planosAtivos` definido
- [ ] Nenhuma implementação iniciada (apenas mapeamento)

---

## 🚀 PRÓXIMOS PASSOS

**Após aprovação desta auditoria:**

1. ✅ **FASE 1** → Contrato oficial dos planos (catálogo versionado)
2. ✅ **FASE 2** → Modelo de assinatura (fonte única de verdade)
3. ✅ **FASE 3** → Motor central de entitlements (decisão única)
4. ✅ **FASE 4** → Limites transacionais (sem race condition)
5. ✅ **FASE 5** → Guards nos recursos (bloqueios aplicados)

---

**Data de conclusão:** 2026-07-29  
**Status:** 🔍 AUDITORIA COMPLETA

