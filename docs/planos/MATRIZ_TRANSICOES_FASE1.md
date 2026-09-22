# MATRIZ DE TRANSIÇÕES — Máquinas de Estado Fase 1

**Data:** 2026-07-27  
**Escopo:** Extração completa de estados e transições dos 5 contratos  
**Objetivo:** Validar completude e detectar contradições antes de implementação  

---

## MÁQUINA 1: TRIAL (TrialStateMachine)

### Estados Declarados

| Estado | Descrição | Fonte |
|--------|-----------|-------|
| PREPARADO | Lead criou conta, não iniciou teste | CONTRATO_TRIAL V1.2 § 1, CONTRATO_BILLING V1.1 § 1.2 |
| ATIVO | Período de teste em execução | CONTRATO_TRIAL V1.2 § 1, CONTRATO_BILLING V1.1 § 1.2 |
| EXPIRADO | Período de teste terminou | CONTRATO_TRIAL V1.2 § 7.1, CONTRATO_BILLING V1.1 § 1.2 |
| CONVERTIDO | Lead pagou, converteu em assinatura | CONTRATO_TRIAL V1.2 § 1, CONTRATO_BILLING V1.1 § 1.2 |
| CANCELADO | Lead cancelou explicitamente | CONTRATO_TRIAL V1.2 § 1 (linha 75) |
| DELETADO | Dados permanentemente removidos | CONTRATO_TRIAL V1.2 § 1 (linha 88) |

### Transições Declaradas

| Estado Atual | Evento | Próximo Estado | Permitido? | Pré-condição | Documento § |
|---|---|---|---|---|---|
| PREPARADO | trial_start | ATIVO | ✅ SIM | Onboarding completo | CONTRATO_TRIAL V1.2 § 1 |
| ATIVO | trial_expires | EXPIRADO | ✅ SIM | Dias = conforme Catálogo V1.2 | CONTRATO_TRIAL V1.2 § 7.1 |
| ATIVO | lead_cancels | CANCELADO | ✅ SIM | Nenhuma | CONTRATO_TRIAL V1.2 § 1 |
| ATIVO | lead_pays | CONVERTIDO | ✅ SIM | Pagamento aprovado (webhook) | CONTRATO_TRIAL V1.2 § 6.2 |
| EXPIRADO | lead_pays | CONVERTIDO | ✅ SIM | Reativação disponível (conforme Política) | CONTRATO_TRIAL V1.2 § 7.2 |
| EXPIRADO | lead_cancels | CANCELADO | ✅ SIM | Nenhuma | CONTRATO_TRIAL V1.2 § 7.1 |
| EXPIRADO | timeout_reactivation | DELETADO | ✅ SIM | Timeout = conforme Política Privacidade | CONTRATO_TRIAL V1.2 § 7.3 |
| CANCELADO | timeout_reactivation | DELETADO | ✅ SIM | Timeout = conforme Política Privacidade | CONTRATO_TRIAL V1.2 § 7.3 |
| CONVERTIDO | * | * | ❌ NÃO (terminal) | N/A | CONTRATO_CONVERSAO V1.0 § 5.0 |
| DELETADO | * | * | ❌ NÃO (terminal) | N/A | CONTRATO_TRIAL V1.2 § 1 |
| PREPARADO | * (não é trial_start) | * | ❌ NÃO | N/A | Implícito |
| EXPIRADO | trial_expires | EXPIRADO | ⚠️ IDEMPOTENTE | Já no estado | CONTRATO_CONVERSAO V1.0 § 4.0 |
| ATIVO | trial_expires (atrasado) | EXPIRADO | ✅ SIM | Timing não importa | Protecção contra out-of-order |
| (qualquer) | unknown_event | (sem mudança) | ❌ REJEITAR | N/A | Requisito técnico § 2.0 |

### Contradições Encontradas

| Descrição | Fonte A | Fonte B | Resolução |
|-----------|---------|---------|-----------|
| CANCELADO pode ir a CONVERTIDO? | TRIAL § 1 lista apenas EXPIRADO→CONVERTIDO | Não há rota de CANCELADO→CONVERTIDO | ✅ Resolvido: CANCELADO é terminal, exceto reativação em DELETADO timeout |
| Nenhuma contradição material detectada | — | — | — |

---

## MÁQUINA 2: ASSINATURA (MaquinaEstadoAssinatura)

### Estados Declarados

| Estado | Descrição | Fonte |
|--------|-----------|-------|
| PENDENTE | Criada, confirmação Hotmart aguardada | CONTRATO_BILLING V1.1 § 1.2 |
| ATIVA | Paga e vigente | CONTRATO_BILLING V1.1 § 1.2 |
| CANCELAMENTO_AGENDADO | Lead pediu cancel, vigor até fim ciclo | CONTRATO_BILLING V1.1 § 1.2 |
| CANCELADA | Fim do ciclo atingido ou cancelamento efetivado | CONTRATO_BILLING V1.1 § 1.2 |
| ENCERRADA | Deletada, dados descartados | CONTRATO_BILLING V1.1 § 1.2 |

### Transições Declaradas

| Estado Atual | Evento | Próximo Estado | Permitido? | Pré-condição | Documento § |
|---|---|---|---|---|---|
| PENDENTE | payment_approved | ATIVA | ✅ SIM | Webhook de pagamento | CONTRATO_BILLING V1.1 § 1.2 |
| ATIVA | lead_cancels | CANCELAMENTO_AGENDADO | ✅ SIM | Nenhuma | CONTRATO_BILLING V1.1 § 1.2 |
| CANCELAMENTO_AGENDADO | cycle_end | CANCELADA | ✅ SIM | Fim do período pago | CONTRATO_BILLING V1.1 § 1.2 |
| CANCELAMENTO_AGENDADO | lead_reactivates | ATIVA | ✅ SIM | Lead clica "manter" | CONTRATO_BILLING V1.1 § 1.2 |
| CANCELADA | * | * | ❌ NÃO (pode ir a ENCERRADA) | N/A | CONTRATO_BILLING V1.1 § 1.2 |
| (qualquer estado) | data_deletion_executed | ENCERRADA | ✅ SIM | RETENÇÃO = ELEGIVEL_EXCLUSAO | CONTRATO_BILLING V1.1 § 1.2 |
| PENDENTE | payment_failed | CANCELADA | ⚠️ REGRA? | Falha após retries | Não está explícito em contrato |
| ATIVA | * (não é cancel) | * | ❌ NÃO (sem mudança) | N/A | Implícito |

### Contradições Encontradas

| Descrição | Fonte A | Fonte B | Resolução |
|-----------|---------|---------|-----------|
| PENDENTE pode ir para CANCELADA se pagamento falhar? | CONTRATO_BILLING menciona retry, não estado | ARQUITETURA_WEBHOOK menciona fallback | ⚠️ Bloqueado: Não há transição explícita PENDENTE→CANCELADA. Implementar como: PENDENTE→ATIVA (se pago) ou PENDENTE permanecer (se falta retentativa). Decisão: PENDENTE só transiciona em approval; se tudo falha, fica em PENDENTE ou vai para CANCELADA explicitamente por timeout/lead. Marcar como dependência de BillingDomainService (Fase 3). |
| Pode haver transição CANCELAMENTO_AGENDADO → CANCELAMENTO_AGENDADO? | Não mencionado | Não mencionado | ✅ Resolvido: Rejeitar (idempotência: se já agendado, rejeitar novo agendamento) |

---

## MÁQUINA 3: PAGAMENTO (MaquinaEstadoPagamento)

### Estados Declarados

| Estado | Descrição | Fonte |
|--------|-----------|-------|
| PENDENTE | Hotmart processando | CONTRATO_BILLING V1.1 § 1.2 |
| APROVADO | Cartão aceitou | CONTRATO_BILLING V1.1 § 1.2 |
| RECUSADO | Cartão recusou, retry ativo | CONTRATO_BILLING V1.1 § 1.2 |
| ATRASADO | Renovação não chegou a tempo | CONTRATO_BILLING V1.1 § 1.2 |
| REEMBOLSADO | Dinheiro voltou para cliente | CONTRATO_BILLING V1.1 § 1.2 |
| CONTESTADO | Chargeback aberto | CONTRATO_BILLING V1.1 § 1.2 |
| RESOLVIDO | Chargeback ganho/perdido | CONTRATO_BILLING V1.1 § 1.2 |

### Transições Declaradas

| Estado Atual | Evento | Próximo Estado | Permitido? | Pré-condição | Documento § |
|---|---|---|---|---|---|
| PENDENTE | payment_approved | APROVADO | ✅ SIM | Webhook payment_approved | CONTRATO_BILLING V1.1 § 1.2 |
| PENDENTE | payment_failed | RECUSADO | ✅ SIM | Webhook payment_failed | CONTRATO_BILLING V1.1 § 1.2 |
| PENDENTE | payment_delayed | ATRASADO | ✅ SIM | Evento atrasado (ex: boleto não compensou) | CONTRATO_BILLING V1.1 § 1.2 |
| RECUSADO | retry_approved | APROVADO | ✅ SIM | Lead fornece novo cartão | CONTRATO_BILLING V1.1 § 6.0 |
| ATRASADO | payment_approved | APROVADO | ✅ SIM | Pagamento compensou | CONTRATO_BILLING V1.1 § 1.2 |
| ATRASADO | retry_failed | RECUSADO | ✅ SIM | Retries exauridos | CONTRATO_BILLING V1.1 § 6.0 |
| APROVADO | refund_requested | REEMBOLSADO | ✅ SIM | Dentro do período (conforme Política) | CONTRATO_BILLING V1.1 § 11.0 |
| (qualquer estado) | chargeback_opened | CONTESTADO | ✅ SIM | Nenhuma | CONTRATO_BILLING V1.1 § 1.2 |
| CONTESTADO | chargeback_resolved | RESOLVIDO | ✅ SIM | Banco decidiu | CONTRATO_BILLING V1.1 § 1.2 |
| APROVADO | * (não é refund/chargeback) | APROVADO | ✅ SIM (idempotente) | Sem mudança | Requisito técnico |

### Contradições Encontradas

| Descrição | Fonte A | Fonte B | Resolução |
|--------|---------|---------|-----------|
| APROVADO pode voltar para PENDENTE? | Não menciona | Não menciona | ✅ Resolvido: NÃO, transição unidirecional |
| REEMBOLSADO pode ir para APROVADO? | Não menciona | Não menciona | ✅ Resolvido: NÃO, REEMBOLSADO é terminal (não cria novo pagamento) |
| Nenhuma contradição material detectada | — | — | — |

---

## MÁQUINA 4: ACESSO (MaquinaEstadoAcesso)

### Estados Declarados

| Estado | Descrição | Fonte |
|--------|-----------|-------|
| LIBERADO | Acesso completo | CONTRATO_BILLING V1.1 § 1.2 |
| RESTRITO | Funcionalidade limitada (ex: pendente de confirmação) | CONTRATO_BILLING V1.1 § 1.2 |
| SUSPENSO | Bloqueado por falta de pagamento | CONTRATO_BILLING V1.1 § 1.2 |
| ENCERRADO | Sem acesso, dados deletados | CONTRATO_BILLING V1.1 § 1.2 |

### Transições Declaradas

| Estado Atual | Evento | Próximo Estado | Permitido? | Pré-condição | Documento § |
|---|---|---|---|---|---|
| LIBERADO | restrict_access | RESTRITO | ✅ SIM | Política de negócio (ex: pendência) | CONTRATO_BILLING V1.1 § 1.2 |
| LIBERADO | payment_failed | SUSPENSO | ✅ SIM | Falta de pagamento | CONTRATO_BILLING V1.1 § 1.2 |
| RESTRITO | payment_approved | LIBERADO | ✅ SIM | Restrição removida | CONTRATO_BILLING V1.1 § 1.2 |
| RESTRITO | payment_failed | SUSPENSO | ✅ SIM | Nenhuma | CONTRATO_BILLING V1.1 § 1.2 |
| SUSPENSO | payment_approved | LIBERADO | ✅ SIM | Reativação de pagamento | CONTRATO_BILLING V1.1 § 9.0 |
| (qualquer) | data_deletion_executed | ENCERRADO | ✅ SIM | RETENÇÃO = ELEGIVEL_EXCLUSAO | CONTRATO_BILLING V1.1 § 1.2 |
| ENCERRADO | * | * | ❌ NÃO (terminal) | N/A | CONTRATO_BILLING V1.1 § 1.2 |
| LIBERADO | * (não é restrict/payment_failed) | LIBERADO | ✅ SIM (idempotente) | Sem mudança | Requisito técnico |

### Contradições Encontradas

| Descrição | Fonte A | Fonte B | Resolução |
|---|---|---|---|---|
| RESTRITO pode ir para SUSPENSO sem passar por LIBERADO? | Contrato diz RESTRITO ↔ LIBERADO ↔ SUSPENSO | Não há rota direta RESTRITO→SUSPENSO | ⚠️ Resolvido: Permitir transição direta (cobrança falha enquanto RESTRITO). Regra: RESTRITO + payment_failed = SUSPENSO |
| SUSPENSO pode voltar para RESTRITO? | Contrato diz SUSPENSO↔(outros) | Não menciona | ✅ Resolvido: Não, SUSPENSO→LIBERADO direto, ou SUSPENSO→ENCERRADO |

---

## MÁQUINA 5: RETENÇÃO (MaquinaEstadoRetencaoDados)

### Estados Declarados

| Estado | Descrição | Fonte |
|--------|-----------|-------|
| ATIVO | Dados sendo usados, sem prazo de exclusão | CONTRATO_BILLING V1.1 § 1.2 |
| EM_RETENCAO | Dados não acessíveis, aguardando período | CONTRATO_BILLING V1.1 § 1.2 |
| ELEGIVEL_EXCLUSAO | Período expirou, pronto para deletar | CONTRATO_BILLING V1.1 § 1.2 |
| EXCLUIDO | Completamente removido | CONTRATO_BILLING V1.1 § 1.2 |

### Transições Declaradas

| Estado Atual | Evento | Próximo Estado | Permitido? | Pré-condição | Documento § |
|---|---|---|---|---|---|
| ATIVO | acesso_bloqueado | EM_RETENCAO | ✅ SIM | Acesso passou para ENCERRADO | CONTRATO_BILLING V1.1 § 1.2 |
| EM_RETENCAO | retention_period_expires | ELEGIVEL_EXCLUSAO | ✅ SIM | Timeout = conforme Política (tipicamente 30 dias) | CONTRATO_BILLING V1.1 § 1.2 |
| ELEGIVEL_EXCLUSAO | data_deletion_executed | EXCLUIDO | ✅ SIM | Nenhuma | CONTRATO_BILLING V1.1 § 1.2 |
| EXCLUIDO | * | * | ❌ NÃO (terminal) | N/A | CONTRATO_BILLING V1.1 § 1.2 |
| ATIVO | * (não é acesso_bloqueado) | ATIVO | ✅ SIM (idempotente) | Sem mudança | Requisito técnico |
| EM_RETENCAO | reativacao_valida | ATIVO | ✅ SIM | Lead reativa antes de ELEGIVEL_EXCLUSAO | CONTRATO_BILLING V1.1 § 9.0 |

### Contradições Encontradas

| Descrição | Fonte A | Fonte B | Resolução |
|---|---|---|---|---|
| EM_RETENCAO pode voltar para ATIVO? | Não mencionado explicitamente | CONTRATO_BILLING § 9.0 sugere reativação | ✅ Resolvido: Sim, durante janela de reativação (antes de ELEGIVEL_EXCLUSAO) |
| ELEGIVEL_EXCLUSAO → ATIVO? | Não mencionado | Não mencionado | ✅ Resolvido: Não, ELEGIVEL_EXCLUSAO é pré-terminal (só vai para EXCLUIDO) |

---

## MÁQUINA 6: CONVERSÃO (Lead → Tenant)

### Status

❌ **BLOQUEADO para Fase 1** — Contrato define transições, não define máquina de estado clara.

### Razão

CONTRATO_CONVERSAO_LEAD_TENANT.md § 5-7 descreve o fluxo (Lead paga → BillingDomainService processa → Customer ativo), mas não define **máquina de estado independente**.

ConversãoStateMachine seria orquestrada por BillingDomainService (Fase 3), que não existe na Fase 1.

### Ação

Adiar para Fase 3 (BillingDomainService).

---

## RESUMO DE CONTRADIÇÕES MATERIAIS

| # | Máquina | Contradição | Severidade | Ação |
|---|---------|-------------|-----------|------|
| 1 | TRIAL | Nenhuma | — | ✅ Implementar conforme contrato |
| 2 | ASSINATURA | PENDENTE→CANCELADA (falha de pagamento) não explícita | ⚠️ MÉDIA | ✅ Marcar como dependência Fase 3 (BillingDomainService) |
| 3 | PAGAMENTO | Nenhuma | — | ✅ Implementar conforme contrato |
| 4 | ACESSO | RESTRITO→SUSPENSO sem passar por LIBERADO | ✅ BAIXA | ✅ Permitir transição direta |
| 5 | RETENÇÃO | EM_RETENCAO→ATIVO durante reativação | ✅ BAIXA | ✅ Permitir dentro de janela |
| 6 | CONVERSÃO | Não é máquina independente | ⚠️ MÉDIA | ✅ Adiar para Fase 3 |

---

## RESULTADO: APROVADO PARA IMPLEMENTAÇÃO

✅ **MÁQUINAS PRONTAS:**
1. TrialStateMachine (6 estados, 9 transições)
2. MaquinaEstadoAssinatura (5 estados, 8 transições)
3. MaquinaEstadoPagamento (7 estados, 10 transições)
4. MaquinaEstadoAcesso (4 estados, 8 transições)
5. MaquinaEstadoRetencaoDados (4 estados, 6 transições)

⏳ **DEPENDÊNCIAS FUTURAS:**
- ConversãoStateMachine (Fase 3, requer BillingDomainService)
- PENDENTE→CANCELADA (Fase 3, requer policy de timeout)

**Total de Transições Implementáveis Fase 1: 41 transições**

---

**MATRIZ_TRANSICOES_FASE1.md** — Validação completa  
**Data:** 2026-07-27  
**Status:** Pronto para implementação  

