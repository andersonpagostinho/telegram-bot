# FASE 2 — ANÁLISE: EVENTOS E ORQUESTRAÇÃO DE DOMÍNIO

**Data:** 2026-07-27  
**Fase:** 2 (Eventos Internos e Orquestração de Domínio)  
**Status:** Análise Pré-Implementação  

---

## 1. EXTRAÇÃO DE EVENTOS DOS CONTRATOS

### 1.1 Eventos Externos (Hotmart Webhooks)

Conforme CONTRATO_BILLING_NEOEVE.md § 5.1:

| Evento Hotmart | Categoria | Tipo de Agregado | Pré-condição | Efeito Esperado |
|---|---|---|---|---|
| `purchase_approved` | Pagamento | Assinatura + Pagamento | Payment PENDENTE | Assinatura ATIVA, Acesso LIBERADO |
| `purchase_pending` | Pagamento | Pagamento | Checkout iniciado | Pagamento PENDENTE, Notificar |
| `purchase_failed` | Pagamento | Pagamento | Payment attempt | Pagamento RECUSADO, Iniciar retry |
| `purchase_error` | Pagamento | Pagamento | Sistema error | Log erro, investigação manual |
| `subscription_renewed` | Assinatura | Assinatura | Ciclo venceu | Assinatura ATIVA, Renovação agendada |
| `subscription_renewed_failed` | Assinatura | Assinatura | Renewal attempt failed | Assinatura falha, Notificar |
| `subscription_canceled` | Assinatura | Assinatura | Lead pediu cancel | Assinatura CANCELADA |
| `subscription_expired` | Assinatura | Acesso | Período expirou sem pagamento | Acesso SUSPENSO |
| `chargeback_opened` | Contestação | Pagamento | Chargeback iniciado | Pagamento CONTESTADO |
| `customer_chargeback_dispute_won` | Contestação | Pagamento + Acesso | Chargeback resolvido favorável | Pagamento RESOLVIDO, Acesso LIBERADO |
| `customer_chargeback_dispute_lost` | Contestação | Pagamento + Acesso | Chargeback resolvido contra | Pagamento RESOLVIDO, Acesso SUSPENSO |

### 1.2 Eventos Internos Esperados (Derivados)

**Trial:**
- `TrialActivated` — PREPARADO → ATIVO (lead completou onboarding)
- `TrialExpired` — ATIVO → EXPIRADO (período expirou)
- `TrialConverted` — EXPIRADO → CONVERTIDO (lead pagou)
- `TrialCanceled` — ATIVO/EXPIRADO → CANCELADO (lead cancelou)
- `TrialDeleted` — EXPIRADO/CANCELADO → DELETADO (timeout)
- `TrialReactivated` — EXPIRADO/CANCELADO → ATIVO (lead reativou)

**Assinatura:**
- `SubscriptionActivated` — PENDENTE → ATIVA (payment_approved)
- `SubscriptionCancellationScheduled` — ATIVA → CANCELAMENTO_AGENDADO (lead pediu cancel)
- `SubscriptionCanceled` — CANCELAMENTO_AGENDADO → CANCELADA (fim de ciclo)
- `SubscriptionEnded` — (qualquer) → ENCERRADA (dados deletados)
- `SubscriptionReactivated` — CANCELAMENTO_AGENDADO → ATIVA (lead descancelou)

**Pagamento:**
- `PaymentApproved` — PENDENTE → APROVADO (cartão aceitou)
- `PaymentRejected` — PENDENTE → RECUSADO (cartão recusou)
- `PaymentAttemptFailed` — ATRASADO → RECUSADO (retry exaurido)
- `PaymentRefunded` — APROVADO → REEMBOLSADO (reembolso solicitado)
- `PaymentContested` — APROVADO/REEMBOLSADO → CONTESTADO (chargeback)
- `PaymentDisputeResolved` — CONTESTADO → RESOLVIDO (chargeback decidido)

**Acesso:**
- `AccessReleased` — (qualquer) → LIBERADO (payment_approved ou cancel descancelado)
- `AccessRestricted` — LIBERADO → RESTRITO (pendência confirmação)
- `AccessSuspended` — (qualquer) → SUSPENSO (payment falhou ou subscription_expired)
- `AccessEnded` — (qualquer) → ENCERRADO (dados deletados)

**Retenção:**
- `DataRetentionStarted` — ATIVO → EM_RETENCAO (acesso bloqueado)
- `DataEligibleForDeletion` — EM_RETENCAO → ELEGIVEL_EXCLUSAO (período expirou)
- `DataDeleted` — ELEGIVEL_EXCLUSAO → EXCLUIDO (deleção executada)
- `DataRetentionCanceled` — EM_RETENCAO → ATIVO (lead reativou durante retenção)

**Conversão Lead → Tenant:**
- `TenantCreationRequested` — Prospect quer converter
- `TenantCreated` — Tenant criado, lead vinculado
- `ConversionCompleted` — Lead associado ao tenant

**Auditoria:**
- `EventProcessed` — Webhook recebido e processado
- `TransitionApplied` — Máquina mudou de estado
- `ValidationFailed` — Evento rejeitado (pré-condição falhou)
- `ReconciliationRequested` — Estado inconsistente, reconciliação necessária

---

## 2. DIFERENCIAÇÃO: EVENTO RECEBIDO → DECISÃO → EVENTO INTERNO → EFEITO

### 2.1 Exemplo: Webhook `purchase_approved`

```
┌─ ENTRADA (Evento Recebido)
│  └─ Hotmart Webhook: purchase_approved
│     ├─ provider_event_id: "hotmart_123456"
│     ├─ subscription_id: "sub_789"
│     ├─ product_id: "prod_neoeve_studio"
│     ├─ customer_id: "cust_555"
│     ├─ transaction_amount: 157.00
│     ├─ transaction_date: 2026-07-27T14:30:00Z
│     └─ [precisa extrair tenant_id do reference_id]
│
├─ NORMALIZAÇÃO (Comando de Domínio)
│  └─ PaymentApprovedCommand
│     ├─ tenant_id: "tenant_abc123" [extraído]
│     ├─ provider_event_id: "hotmart_123456"
│     ├─ source_event_type: "purchase_approved"
│     ├─ amount: 157.00
│     ├─ received_at: 2026-07-27T14:30:00Z
│     └─ correlation_id: "corr_xyz" [gerado]
│
├─ PRÉ-CONDIÇÕES (Decisão)
│  ├─ ✅ provider_event_id não processado antes (idempotência)
│  ├─ ✅ tenant_id existe
│  ├─ ✅ subscription_id existe
│  ├─ ✅ amount > 0
│  ├─ ✅ estado_assinatura = PENDENTE (pré-condição máquina)
│  └─ ✅ estado_pagamento = PENDENTE (pré-condição máquina)
│
├─ APLICAÇÃO DE MÁQUINAS (Transições)
│  │
│  ├─ Máquina 1: AssinaturaStateMachine
│  │  ├─ Entrada: PENDENTE + PAYMENT_APPROVED
│  │  ├─ Transição: PENDENTE → ATIVA
│  │  ├─ Efeitos sugeridos:
│  │  │  ├─ "publicar_evento:assinatura_ativada"
│  │  │  └─ "iniciar_timer_renovacao"
│  │  └─ Saída: novo estado ATIVA
│  │
│  ├─ Máquina 2: PagamentoStateMachine
│  │  ├─ Entrada: PENDENTE + PAYMENT_APPROVED
│  │  ├─ Transição: PENDENTE → APROVADO
│  │  ├─ Efeitos sugeridos:
│  │  │  ├─ "liberar_acesso"
│  │  │  └─ "publicar_evento:pagamento_aprovado"
│  │  └─ Saída: novo estado APROVADO
│  │
│  ├─ Máquina 3: AcessoStateMachine
│  │  ├─ Entrada: LIBERADO (ou SUSPENSO) + PAYMENT_APPROVED
│  │  ├─ Transição: (qualquer) → LIBERADO
│  │  ├─ Efeitos sugeridos:
│  │  │  └─ "liberar_acesso_completo"
│  │  └─ Saída: novo estado LIBERADO
│  │
│  ├─ Máquina 4: RetencaoStateMachine
│  │  ├─ Entrada: EM_RETENCAO (se estiver nesse estado)
│  │  ├─ Transição: EM_RETENCAO → ATIVO (se reativação explícita)
│  │  ├─ Nota: Purchase_approved NÃO afeta retenção automaticamente
│  │  └─ Saída: estado EM_RETENCAO (sem mudança neste caso)
│  │
│  └─ Máquina 5: TrialStateMachine
│     ├─ Nota: Se estado_trial = ATIVO
│     ├─ Transição: ATIVO → CONVERTIDO (event LEAD_PAYS)
│     ├─ Efeitos sugeridos:
│     │  ├─ "publicar_evento:trial_convertido"
│     │  └─ "encerrar_trial_period"
│     └─ Saída: novo estado CONVERTIDO
│
├─ EVENTOS INTERNOS PRODUZIDOS
│  ├─ SubscriptionActivated
│  │  ├─ correlation_id: "corr_xyz" [MESMO do comando]
│  │  ├─ source_event_id: "hotmart_123456"
│  │  ├─ tenant_id: "tenant_abc123"
│  │  ├─ produced_at: 2026-07-27T14:30:05Z
│  │  └─ reason: "payment_approved"
│  │
│  ├─ PaymentApproved
│  │  ├─ correlation_id: "corr_xyz"
│  │  ├─ source_event_id: "hotmart_123456"
│  │  ├─ amount: 157.00
│  │  └─ [similar structure]
│  │
│  ├─ AccessReleased
│  │  ├─ correlation_id: "corr_xyz"
│  │  ├─ previous_state: "SUSPENSO" (ou LIBERADO)
│  │  └─ [similar]
│  │
│  └─ [Condicionalmente] TrialConverted
│     ├─ Se estado_trial = ATIVO
│     ├─ correlation_id: "corr_xyz"
│     └─ [similar]
│
└─ EFEITOS SUGERIDOS (Não Executados em Fase 2)
   ├─ "publicar_evento:assinatura_ativada" → Fase 3
   ├─ "iniciar_timer_renovacao" → Fase 3
   ├─ "liberar_acesso_completo" → Fase 3
   ├─ "publicar_evento:pagamento_aprovado" → Fase 3
   └─ [Nenhum efeito executado, apenas sugerido e retornado]
```

---

## 3. MATRIZ DE ORQUESTRAÇÃO

### 3.1 Estrutura da Matriz

Para cada evento externo (Hotmart webhook):

```
Evento Externo: purchase_approved
├─ Provider Event ID: (de payload Hotmart)
├─ Tipo Normalizado: PaymentApprovedEvent
├─ Tenant ID: (extraído de reference_id)
├─ Timestamp: (de Hotmart)
│
├─ Pré-Condições (Validação de Entrada)
│  ├─ provider_event_id deve ser único (idempotência)
│  ├─ tenant_id deve existir
│  ├─ subscription_id deve existir
│  └─ [validações estruturais de payload]
│
├─ Consulta de Estado Atual
│  ├─ estado_trial: ATIVO|EXPIRADO|CONVERTIDO|...
│  ├─ estado_assinatura: PENDENTE|ATIVA|...
│  ├─ estado_pagamento: PENDENTE|APROVADO|...
│  ├─ estado_acesso: LIBERADO|RESTRITO|...
│  └─ estado_retencao: ATIVO|EM_RETENCAO|...
│
├─ Máquinas Consultadas
│  ├─ TrialStateMachine (se estado_trial relevante)
│  ├─ AssinaturaStateMachine (OBRIGATÓRIO)
│  ├─ PagamentoStateMachine (OBRIGATÓRIO)
│  ├─ AcessoStateMachine (OBRIGATÓRIO)
│  └─ RetencaoStateMachine (condicional)
│
├─ Transições Aplicadas
│  ├─ Máquina 1: Estado → Novo Estado (validado)
│  ├─ Máquina 2: Estado → Novo Estado (validado)
│  ├─ Máquina 3: Estado → Novo Estado (validado)
│  ├─ Máquina 4: Estado → Novo Estado (validado)
│  └─ Máquina 5: Estado → Novo Estado (validado)
│
├─ Resultado
│  ├─ Sucesso: TRUE/FALSE
│  ├─ Snapshot Anterior: {trial, assinatura, pagamento, acesso, retencao}
│  ├─ Snapshot Resultante: {trial, assinatura, pagamento, acesso, retencao}
│  ├─ Transições Aplicadas: [...]
│  ├─ Transições Ignoradas: [...] (pré-condição falhou)
│  └─ Razão de Falha: (se sucesso = FALSE)
│
├─ Eventos Internos Emitidos
│  ├─ SubscriptionActivated (se assinatura PENDENTE → ATIVA)
│  ├─ PaymentApproved (se pagamento PENDENTE → APROVADO)
│  ├─ AccessReleased (se acesso (qualquer) → LIBERADO)
│  └─ [Todos com correlation_id e source_event_id]
│
├─ Efeitos Sugeridos (Não Executados)
│  ├─ publicar_evento:assinatura_ativada
│  ├─ liberar_acesso_completo
│  ├─ publicar_evento:pagamento_aprovado
│  └─ [Nenhum efeito real, apenas strings]
│
└─ Origem Documental
   ├─ Contrato: CONTRATO_BILLING_NEOEVE.md § 5.1
   ├─ Máquinas: FASE1_RECONCILIACAO (Assinatura, Pagamento, Acesso)
   ├─ Politica: [referência ao contrato que define a política]
   └─ Revisão: 2026-07-27
```

---

## 4. CENÁRIOS CRÍTICOS MAPEADOS

### 4.1 Cenário 1: Pagamento Aprovado Durante Trial Ativo

```
Estado Inicial:
├─ trial: ATIVO (dia 3 de 7)
├─ assinatura: NÃO EXISTE (trial não cria assinatura)
├─ pagamento: PENDENTE (checkout iniciado)
├─ acesso: LIBERADO (trial ativo)
└─ retencao: ATIVO

Evento: purchase_approved

Fluxo:
├─ Pré-condição: estado_assinatura = PENDENTE? ✗ (não existe)
│  → ERRO: Assinatura não existe, não pode ativar
│  → Necessário criar assinatura ANTES de processar payment_approved
│
├─ OU: Política deve criar assinatura implicitamente?
│  → Decisão documentada: [AMBIGÜIDADE #1 - Ver seção 5.1]
│
└─ Resultado: Rejeição com motivo "assinatura_nao_existe" ou Criação?
```

### 4.2 Cenário 2: Pagamento Duplicado

```
Estado Inicial: (mesmo de antes, aceita)
├─ assinatura: ATIVA (primeira transação aceitou)
├─ pagamento: APROVADO
├─ acesso: LIBERADO

Evento: purchase_approved (SEGUNDA VEZ, mesmo provider_event_id)

Fluxo:
├─ Pré-condição: idempotência por provider_event_id
│  └─ Verificar: Já processamos "hotmart_123456"?
│     └─ SIM → Retornar resultado idempotente (aceitar, não aplicar novamente)
│
├─ Resultado:
│  ├─ success: TRUE (idempotência bem-sucedida)
│  ├─ transicoes_aplicadas: [] (nenhuma, foi ignorada)
│  ├─ razao: "evento_ja_processado"
│  └─ snapshot_anterior = snapshot_resultante (nada mudou)
```

### 4.3 Cenário 3: Evento Fora de Ordem

```
Estado Inicial:
├─ assinatura: PENDENTE
├─ pagamento: PENDENTE
└─ acesso: LIBERADO (trial)

Evento 1: purchase_failed (cartão recusado)
Evento 2: purchase_approved (cartão aprovado após retry)

Recebimento: purchase_approved chega PRIMEIRO, depois purchase_failed

Fluxo:
├─ Aplicar purchase_approved:
│  ├─ assinatura: PENDENTE → ATIVA ✓
│  ├─ pagamento: PENDENTE → APROVADO ✓
│  ├─ acesso: LIBERADO (sem mudança)
│  └─ Snapshot: {ATIVA, APROVADO, LIBERADO}
│
├─ Aplicar purchase_failed (RETROATIVO):
│  ├─ Pré-condição: pagamento = PENDENTE?
│  │  └─ NÃO (já é APROVADO)
│  ├─ Transição: APROVADO → RECUSADO?
│  │  └─ Máquina valida? NÃO DIRETAMENTE
│  │     (máquina prevê ATRASADO, não caminhos diretos pós-APROVADO)
│  │
│  └─ Decisão:
│     ├─ Opção A: Rejeitar (evento retroativo não permitido)
│     ├─ Opção B: Ignorar (timestamp de purchase_failed < purchase_approved)
│     └─ Opção C: Solicitar reconciliação [AMBIGÜIDADE #2]
```

---

## 5. AMBIGÜIDADES E LACUNAS IDENTIFICADAS

### 5.1 Ambigüidade #1: Criação Implícita de Assinatura

**Pergunta:** Quando purchase_approved chega, e não existe assinatura para o tenant?

**Hipóteses:**
- A) Rejeitar o webhook (assinatura deve existir antes)
- B) Criar assinatura implicitamente (Adapter cria assinatura? Ou BillingDomainService?)
- C) Webhook presume que assinatura já existe (design error)

**Localização no Contrato:** CONTRATO_BILLING_NEOEVE.md § 1.2 e § 5.1 não especificam ordem

**Impacto:** Bloqueador de implementação

**Recomendação Provisória:** Rejeitar (opção A) até contrato esclarecer

---

### 5.2 Ambigüidade #2: Eventos Retroativos

**Pergunta:** Se payment_failed chega APÓS payment_approved, qual é a semântica?

**Cenários:**
- Falha de transação que Hotmart detectou tarde
- Retry que falhou dias depois
- Webhook duplicado atrasado

**Localização no Contrato:** § 6.2.2 (reentrega de webhook) trata reenvios do MESMO evento, não eventos retroativos

**Impacto:** Precisamos definir política de out-of-order

**Recomendação Provisória:** Rejeitar eventos com timestamp < último evento processado para o tenant

---

### 5.3 Ambigüidade #3: Estado Inconsistente Entre Máquinas

**Pergunta:** E se uma transição falhar a meio? Ex:
- AssinaturaStateMachine.transition() ✓ SUCESSO
- PagamentoStateMachine.transition() ✗ FALHA

**Localização no Contrato:** Seção 14 (Reconciliação) menciona mas não detalha

**Impacto:** Requer transação Firestore ou lógica de rollback

**Recomendação Provisória:** Todas as transições sãoatômicas (tudo ou nada)

---

### 5.4 Lacuna #1: Ordem Determinística de Aplicação de Máquinas

**Pergunta:** Em qual ordem aplicamos as máquinas? Trial → Assinatura → Pagamento → Acesso → Retenção?

**Justificativa:** Reivindicações de efeitos podem depender de ordem

**Localização no Contrato:** Não especificado

**Recomendação Provisória:** Ordem fixa: Assinatura → Pagamento → Acesso → Trial → Retenção

---

## 6. REQUISITOS DE IMPLEMENTAÇÃO

### 6.1 commercial_events.py

```python
# Deve incluir:
├─ Base class Event (tipado, imutável)
├─ Tipos de evento (TrialActivated, PaymentApproved, etc.)
├─ Validação de payload
├─ Correlação e rastreabilidade (correlation_id, source_event_id)
└─ Versioning de schema
```

### 6.2 billing_domain_service.py

```python
# Deve incluir:
├─ Entrada: snapshot + comando normalizado
├─ Validação de pré-condições
├─ Orquestração das 5 máquinas em ordem determinística
├─ Retorno estruturado (sucesso/falha + snapshots + eventos)
└─ Determinismo garantido
```

### 6.3 Testes

```python
# Deve cobrir:
├─ Eventos válidos (feliz)
├─ Eventos duplicados (idempotência)
├─ Eventos fora de ordem (rejeição ou reconciliação)
├─ Estados inconsistentes (falha segura)
├─ Isolamento por tenant
├─ Determinismo (mesmo input → mesmo output)
└─ [20+ cenários críticos listados antes]
```

---

## 7. CONCLUSÃO PRÉ-IMPLEMENTAÇÃO

✅ **Pronto para Implementar:**
- Estrutura base de eventos
- Orquestração pura das máquinas
- Validação de pré-condições
- Testes unitários

⚠️ **Bloqueadores (Resolvidos com Decisão Arquitetural):**
1. Criação implícita de assinatura → **REJEITAR** até clareza contratual
2. Eventos retroativos → **REJEITAR** eventos antigos
3. Transações atômicas → **IMPLEMENTAR** com try-rollback

❌ **Não Fazer (Fora de Escopo Fase 2):**
- Persistência Firestore (Fase 3)
- Publicação de eventos reais (Fase 3)
- Webhook endpoint (Fase 4)
- Adapter Hotmart (Fase 4)

---

**Próximo Passo:** Iniciar implementação com commercial_events.py

