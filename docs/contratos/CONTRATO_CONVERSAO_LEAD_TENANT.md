# CONTRATO_CONVERSAO_LEAD_TENANT — Fluxo de Conversão Completo

**Versão:** 1.0  
**Status:** Especificação Final  
**Data de Criação:** 2026-07-27  
**Aprovação Pré-requisito:** CONTRATO_TRIAL_NEOEVE.md V1.2 ✅ + CONTRATO_BILLING_NEOEVE.md V1.1 ✅  

---

## 📐 PROPÓSITO

Consolida o **fluxo completo** de um Lead (prospect) → Tenant (cliente ativo).

Referencia (não duplica):
- ✅ Trial: CONTRATO_TRIAL_NEOEVE.md
- ✅ Billing: CONTRATO_BILLING_NEOEVE.md
- ✅ Elegibilidade: CATALOGO_COMERCIAL_NEOEVE.md (Seção 5)
- ✅ Arquitetura Webhook: ARQUITETURA_WEBHOOK_DOMAINSERVICE.md

---

## 🔄 FLUXO MACRO: Lead → Tenant

```
[PROSPECT ZERO]
    ↓
    Tenta acessar NeoEve
    ↓
[LEAD CRIADO + TRIAL INICIADO]
    │
    ├─ Estado Trial: PREPARADO → ATIVO
    ├─ Duração: conforme Catálogo V1.2
    ├─ Acesso: funcionalidades trial (subset)
    │
    ├─ → Acompanhamento Inteligente (5 perfis)
    │     ├─ Onboarding Incompleto
    │     ├─ Configurado sem Movimento
    │     ├─ Movimento Bloqueado
    │     ├─ Uso Saudável
    │     └─ Uso Intenso
    │
    ├─ → Check-in automático (sem CTA)
    ├─ → Sem pressão de conversão
    ├─ → Open door message (se quer expandir)
    │
    └─ → Final Report (3 dimensões)
          └─ mensagens, agendamentos, padrão de atividade
    ↓
[TRIAL EXPIRADO]
    │
    ├─ Opção 1: Lead compra plano → Webhook payment_approved
    │            ↓
    │            [CLIENTE ATIVO]
    │            ├─ Estado Assinatura: ATIVA
    │            ├─ Estado Pagamento: APROVADO
    │            ├─ Estado Acesso: LIBERADO
    │            ├─ Renovação automática no ciclo
    │            └─ Lead se torna Tenant
    │
    ├─ Opção 2: Lead não compra
    │            ↓
    │            [TRIAL CONVERTIDO = FALSE]
    │            ├─ Estado Trial: EXPIRADO
    │            ├─ Dados deletados conforme política LGPD
    │            └─ Sem mais acesso
    │
    └─ Opção 3: Lead reativa subscription após cancelamento
                 ↓
                 [CLIENTE REATIVADO]
                 ├─ Novo Trial? Não (já tinha)
                 └─ Plano direto (Hotmart reconhece)

```

---

## 📋 SEÇÕES CONTRATO

### 1. ESTADO LEAD

**Quando um Lead é criado?**

```
CONDIÇÃO: Primeiro acesso autenticado de novo usuário
    ↓
    Sistema cria:
    ├─ user_id (único)
    ├─ tenant_id (isolamento multi-tenant)
    ├─ estado_trial: PREPARADO
    ├─ estado_assinatura: —
    ├─ estado_pagamento: —
    └─ timestamp_criacao: agora
```

**Quem cria Lead?**

✅ Sistema automático (primeiro login)

❌ Manual (não permitido — causa inconsistência)

**Qual é o tenant_id de um Lead?**

```
tenant_id = hash(email_usuario)
    ↓
    Criado no primeiro acesso
    ↓
    Permanente durante trial
    ↓
    Preservado após conversão (mesma chave)
```

**Por quê prefixar com tenant?**

Isolamento multi-tenant **desde o primeiro acesso**.

Dados de um Lead NÃO vazam para outro tenant.

---

### 2. TRANSIÇÃO: LEAD → TRIAL

**Quando inicia Trial?**

```
Condição: Lead criado
    ↓
    Sistema:
    ├─ Calcula: data_expiracao = agora + duração (conforme Catálogo V1.2)
    ├─ Define: estado_trial = ATIVO
    ├─ Publica evento_interno: trial_iniciado
    └─ Define acesso_funcionalidades = TRIAL_SUBSET

Resultado: Lead pode usar funcionalidades trial por N dias
```

**Duração trial?**

→ Conforme `CATALOGO_COMERCIAL_NEOEVE.md`, Seção 6.2

NÃO hardcode em código. Consultar Catálogo via configuração.

---

### 3. ACOMPANHAMENTO INTELIGENTE (Trial Value Reinforcement)

Referência: CONTRATO_TRIAL_NEOEVE.md, Seção "Acompanhamento Inteligente"

**5 Perfis operacionais:**

| Perfil | Critério | Ação | CTA? |
|--------|----------|------|------|
| **Onboarding Incompleto** | Sem dados básicos | Check-in | ❌ Não |
| **Configurado sem Movimento** | Dados mas sem uso | Aguardar | ❌ Não |
| **Movimento Bloqueado** | Tentou usar, erro | Diagnóstico | ❌ Não |
| **Uso Saudável** | Usando bem | Mantém | ❌ Não |
| **Uso Intenso** | Atingindo limites | Open Door | ✅ "Quer expandir?" |

**Importante:**

- ✅ Mensagens são **observações**, não vendas
- ✅ Permissão para sugerir upgrade (sem pressão)
- ✅ Base de dados: telemetria real, não psicologia
- ✅ Nenhuma decisão automática baseado em perfil

---

### 4. TRANSIÇÃO: TRIAL EXPIRADO → DECISÃO

**Quando trial expira?**

```
Condição: Timestamp agora ≥ data_expiracao
    ↓
    Sistema:
    ├─ Define: estado_trial = EXPIRADO
    ├─ Bloqueia: acesso_funcionalidades = NENHUM
    ├─ Publica: trial_expirado
    ├─ Gera: relatorio_final_trial
    └─ Registra: converteu_para_cliente? [SIM|NÃO]
```

**Relatório final contém:**

Conforme CONTRATO_TRIAL_NEOEVE.md:
- ✅ mensagensProcessadas
- ✅ agendamentosRealizados
- ✅ padrãoAtividade
- ✅ disponibilidadeOperacional

**Resultado observável:**

```
{
  "relatorio_trial": {
    "mensagens": 0,
    "agendamentos": 0,
    "padrao_atividade": "sem_movimento",
    "disponibilidade": "100%"
  }
}
```

---

### 5. OPÇÃO A: LEAD COMPRA PLANO

**Sequência:**

```
[TRIAL EXPIRADO]
    ↓
    Lead acessa pagina upgrade
    ↓
    Escolhe plano (SOLO87, STUDIO157, etc)
    ↓
    Hotmart checkout
    ↓
    Paga com cartão
    ↓
    [WEBHOOK payment_approved]
        ↓
        BillingDomainService:
        ├─ Valida evento
        ├─ Verifica idempotência
        ├─ Carrega estado atual (era TRIAL_EXPIRADO)
        ├─ Aplica máquina de estados
        │   ├─ Trial: EXPIRADO → CONVERTIDO
        │   ├─ Assinatura: PENDENTE → ATIVA
        │   ├─ Pagamento: PENDENTE → APROVADO
        │   ├─ Acesso: SUSPENSO → LIBERADO
        │   └─ Retenção: ATIVO
        ├─ Persiste com transação
        ├─ Registra auditoria
        └─ Publica eventos internos
    ↓
[CLIENTE ATIVO = TENANT]
    ├─ estado_trial: CONVERTIDO
    ├─ estado_assinatura: ATIVA
    ├─ estado_pagamento: APROVADO
    ├─ estado_acesso: LIBERADO
    ├─ estado_retencao: ATIVO
    │
    ├─ tenant_id: [mesmo do Lead]
    ├─ plano: [escolhido]
    ├─ data_inicio: agora
    ├─ data_proxima_renovacao: agora + 1 ciclo (conforme Hotmart)
    │
    └─ Acesso: Funcionalidades PLANO_COMPLETO
```

**Transição automática:**

O mesmo tenant_id permite acesso direto → sem refazer onboarding.

---

### 6. OPÇÃO B: LEAD NÃO COMPRA

**Sequência:**

```
[TRIAL EXPIRADO]
    ↓
    Lead não faz nada (não clica compra)
    ↓
    Sistema aguarda (sem pressão)
    ↓
    [PERÍODO DE RETENÇÃO]
        └─ 30 dias (conforme Política Privacidade TBD)
    ↓
[DADOS DELETADOS]
    ├─ tenant_id: [deletado]
    ├─ Contexto: [deletado]
    ├─ Histórico: [deletado]
    └─ LGPD: Política de retenção respeitada
```

**Registro persistente:**

```
deleted_leads: [
  {
    "user_id": "...",
    "email": "...",
    "tenant_id": "...",
    "motivo": "trial_expirado_sem_conversao",
    "data_deletion": "..."
  }
]
```

---

### 7. OPÇÃO C: REATIVAÇÃO APÓS CANCELAMENTO

**Sequência:**

```
[CLIENTE ATIVO]
    ↓
    Lead cancela assinatura
    ↓
    [ASSINATURA CANCELADA]
    ├─ estado_assinatura: CANCELADA
    ├─ estado_acesso: SUSPENSO
    └─ Dados retidos conforme política
    ↓
    Depois: Lead quer reativar
    ↓
    Hotmart: Reativa assinatura
    ↓
    [WEBHOOK subscription_reactivated]
        ↓
        BillingDomainService:
        ├─ Valida evento
        ├─ Verifica idempotência
        ├─ Carrega estado
        ├─ Aplica transição:
        │   ├─ Assinatura: CANCELADA → ATIVA
        │   ├─ Acesso: SUSPENSO → LIBERADO
        │   └─ Mantém mesma trial_id (não recria)
        └─ Publica eventos internos
    ↓
[CLIENTE REATIVADO]
    ├─ Mesmo tenant_id
    ├─ Histórico preservado (nunca foi deletado)
    ├─ Sem novo trial
    └─ Funcionalidades liberadas
```

**Importante:**

Reativação NÃO cria novo trial.

Usa diretamente o plano da assinatura reativada.

---

## 🏗️ REQUISITOS ARQUITETURAIS

### Requisito 1: Webhook → BillingDomainService (Obrigatório)

Conforme **ARQUITETURA_WEBHOOK_DOMAINSERVICE.md**:

```
Webhook payment_approved
    ↓
    ❌ NÃO: Firestore direto
    ✅ SIM: Adapter → BillingDomainService
            └─ Máquinas de estado
            └─ Validação
            └─ Idempotência
            └─ Auditoria
```

**Checklist:**
- ☐ BillingDomainService existe?
- ☐ Verifica idempotência via provider_event_id?
- ☐ Aplica máquina de estados?
- ☐ Persiste com transação?
- ☐ Registra auditoria?

---

### Requisito 2: Transições de Estado Garantidas

**Trial:**
```
PREPARADO → ATIVO → EXPIRADO → CONVERTIDO
                            ↓
                         DELETADO (se não converteu)
```

**Assinatura:**
```
—  → ATIVA → CANCELAMENTO_AGENDADO → CANCELADA → ENCERRADA
     ↑       ↓
     └───────┘ (reativar)
```

**Pagamento:**
```
PENDENTE → APROVADO/RECUSADO/ATRASADO → REEMBOLSADO/RESOLVIDO
```

**Acesso:**
```
LIBERADO ↔ SUSPENSO ↔ RESTRITO → ENCERRADO
```

**Idempotência:** Provider_event_id previne reprocessamento.

---

### Requisito 3: Isolamento Multi-tenant

```
tenant_id = hash(email_usuario)
    ↓
    Criado na primeira mensagem
    ↓
    Permanece mesmo após trial/conversão
    ↓
    Firestore paths sempre incluem tenant_id
    ↓
    Backend valida tenant_id a cada operação
    ↓
    Resultado: Dados de um lead nunca vazam para outro
```

---

### Requisito 4: Auditoria Completa

Toda transição registrada:

```
{
  "tipo": "conversao_trial_para_cliente",
  "tenant_id": "...",
  "user_id": "...",
  
  "transicao_trial": "EXPIRADO → CONVERTIDO",
  "transicao_assinatura": "— → ATIVA",
  "transicao_pagamento": "— → APROVADO",
  "transicao_acesso": "— → LIBERADO",
  
  "webhook_hotmart_event_id": "...",
  "timestamp": "...",
  
  "dados_antes": { ... },
  "dados_depois": { ... }
}
```

---

## 🚫 OPERAÇÕES PROIBIDAS

### ❌ Proibição 1: Mudar tenant_id após criação

```
tenant_id criado no primeiro acesso é IMUTÁVEL.

Nunca fazer:
┌─────────────────────────────────┐
│ tenant_id = hash(novo_email)    │  ❌ PROIBIDO
└─────────────────────────────────┘
```

**Por quê?** Dados seriam abandonados.

---

### ❌ Proibição 2: Criar lead manualmente

```
Nunca fazer:
┌────────────────────────────────┐
│ INSERT leads (email, ...)       │  ❌ PROIBIDO
└────────────────────────────────┘
```

**Por quê?** Causaria inconsistência com trial.

**Correto:** Sistema cria automaticamente no primeiro login.

---

### ❌ Proibição 3: Webhook direto em Firestore

```
Nunca fazer:
┌──────────────────────────────────┐
│ webhook → firestore (direto)     │  ❌ PROIBIDO
└──────────────────────────────────┘
```

**Conforme ARQUITETURA_WEBHOOK_DOMAINSERVICE.md.**

---

### ❌ Proibição 4: Pular máquina de estados

```
Nunca fazer:
┌─────────────────────────────────────┐
│ SET trial = CONVERTIDO (direto)     │  ❌ PROIBIDO
│ SET assinatura = ATIVA (direto)     │  ❌ PROIBIDO
└─────────────────────────────────────┘
```

**Correto:** Passar por BillingDomainService + máquina de estados.

---

### ❌ Proibição 5: Conversão automática baseado em perfil

```
Nunca fazer:
┌───────────────────────────────────────┐
│ IF uso_intenso:                       │  ❌ PROIBIDO
│   CHARGE_CARD_AUTOMATICAMENTE()       │
└───────────────────────────────────────┘
```

**Correto:** Apenas mensagens observacionais. Lead decide comprar.

---

## 📊 MATRIZ ESTADO-SAÍDA

**Qual é o acesso garantido em cada estado?**

| Estado Trial | Estado Assinatura | Estado Pagamento | Estado Acesso | Resultado |
|---|---|---|---|---|
| PREPARADO | — | — | — | Trial subset |
| ATIVO | — | — | — | Trial subset |
| EXPIRADO | — | — | SUSPENSO | ❌ Bloqueado |
| CONVERTIDO | ATIVA | APROVADO | LIBERADO | ✅ Plano completo |
| CONVERTIDO | CANCELADA | — | SUSPENSO | ❌ Bloqueado |

---

## 🔗 DEPENDÊNCIAS DOCUMENTAÇÃO

Esse contrato **referencia e não duplica:**

| Item | Encontre em | Referência |
|------|---|---|
| Duração Trial | CATALOGO_COMERCIAL_NEOEVE.md § 6.2 | "conforme Catálogo" |
| Planos | CATALOGO_COMERCIAL_NEOEVE.md § 2 | "conforme Catálogo" |
| Limites | CATALOGO_COMERCIAL_NEOEVE.md § 4 | "conforme Catálogo" |
| Elegibilidade | CATALOGO_COMERCIAL_NEOEVE.md § 5 | "conforme Catálogo" |
| Trial | CONTRATO_TRIAL_NEOEVE.md | "conforme Contrato Trial" |
| Billing | CONTRATO_BILLING_NEOEVE.md | "conforme Contrato Billing" |
| Webhook | ARQUITETURA_WEBHOOK_DOMAINSERVICE.md | "conforme arquitetura" |
| LGPD | Política Privacidade (TBD) | "conforme política" |

---

## ✅ CHECKLIST IMPLEMENTAÇÃO

### Pré-requisitos

```
☐ CATALOGO_COMERCIAL_NEOEVE.md V1.2 congelado
☐ CONTRATO_TRIAL_NEOEVE.md V1.2 aprovado
☐ CONTRATO_BILLING_NEOEVE.md V1.1 aprovado
☐ ARQUITETURA_WEBHOOK_DOMAINSERVICE.md implementado
☐ BillingDomainService codificado + testado
```

### Implementação

```
☐ Lead criado automaticamente no primeiro login
☐ tenant_id = hash(email_usuario) imutável
☐ Trial iniciado com duração conforme Catálogo
☐ Acompanhamento Inteligente (5 perfis)
☐ Trial expira automaticamente
☐ Relatório final gerado (3 dimensões)
☐ Webhook payment_approved → BillingDomainService
☐ Máquinas de estado aplicadas
☐ Transição garantida com transação Firestore
☐ Auditoria registrada
☐ Eventos internos publicados
```

### Testes

```
☐ P0 Cenário feliz: Lead → Trial → Expira → Compra → Cliente ativo
☐ P0 Cenário não compra: Lead → Trial → Expira → Deletado
☐ P0 Reativação: Cliente → Cancela → Reativa
☐ P1 Duplicado webhook: Payment_approved chega 2x → Processado 1x
☐ P1 Webhook fora ordem: Pagamento antes de criação → Máquina detecta
☐ P1 Concorrência: 2 webhooks simultâneos → Transação garante consistência
```

---

## 🎯 RESULTADO ESPERADO

```
Prospect
    ↓
[Primeiro login]
    ↓
Lead criado + Trial iniciado
    ↓
[7 dias de trial]
    ├─ Acompanhamento inteligente (sem pressão)
    └─ Relatório final
    ↓
[Escolhe comprar]
    ↓
Webhook payment_approved
    ↓
BillingDomainService
    ├─ Valida
    ├─ Verifica idempotência
    ├─ Aplica máquina de estados
    └─ Persiste com transação
    ↓
[Cliente Ativo = Tenant]
    ├─ Mesma tenant_id do Lead
    ├─ Acesso liberado
    ├─ Renovação automática
    └─ Dados auditados
```

---

## 📅 TIMELINE

**Fase 1: Implementação BillingDomainService**
- Criar classe com 6 camadas (Webhook → DomainService → States → Firestore)
- Testes unitários de máquinas de estado

**Fase 2: Integração Hotmart**
- VALIDACAO_HOTMART.md testes 2, 3, 14, 15
- Webhook reais via Sandbox

**Fase 3: Produção**
- VALIDACAO_HOTMART.md testes críticos com dados reais
- Monitoramento de conversão

---

**CONTRATO_CONVERSAO_LEAD_TENANT.md** — Especificação Final  
**Status:** Pronto para implementação  
**Validação:** VALIDACAO_HOTMART.md checklist operacional (Testes 2-18)  
**Próximo:** Code review de BillingDomainService contra essa especificação

