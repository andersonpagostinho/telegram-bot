# CONTRATO_BILLING_NEOEVE

---

## 🔒 REFERENCIA OBRIGATÓRIA

**Versão:** 1.1 (Operacional — Estados, Transições, Eventos, Reconciliação)  
**Status:** ⚠️ RASCUNHO REVISADO — Requer Aprovação Hotmart + Finance + Jurídico  
**Data de Criação:** 2026-07-27  
**Última Atualização:** 2026-07-27 (Revisão de 8 bloqueadores aplicada)  

**Revisão V1.0 → V1.1 (Bloqueadores Resolvidos):**
- ✅ HMAC-SHA256 removido; mecanismo oficial Hotmart com ressalvas
- ✅ Firestore RLS corrigido para isolamento multi-tenant real
- ✅ Upgrade/downgrade alinhado à Hotmart (sem cálculos próprios)
- ✅ 4 tipos de retry separados (cobrança, reentrega, processamento, reconciliação)
- ✅ Idempotência refatorada com provider_event_id + hash
- ✅ 5 máquinas de estado separadas (trial, assinatura, pagamento, acesso, retenção)
- ✅ Reembolso 7 dias → configurável conforme oferta
- ✅ Reconciliação formalizada com hierarquia: API Hotmart > Webhooks > Registro Interno  

**Este contrato define ASSINATURA, CICLOS FINANCEIROS, EVENTOS HOTMART e RECONCILIAÇÃO.**

**Não define termos jurídicos** — veja TERMOS_DE_USO_NEOEVE.md (TBD)

**Documentos que este contrato referencia (nunca duplica):**

| Item | Encontre Em | Não Copie Para |
|------|---|---|
| Preços dos planos | Catálogo Comercial V1.2, Seção 6.1 | Este contrato (referencie) |
| Elegibilidade de planos | Catálogo Comercial V1.2, Seção 5 | Este contrato (referencie) |
| Upgrade/Downgrade regras | Catálogo Comercial V1.2, Seção 5.4 | Este contrato (referencie) |
| Política de trial | Contrato de Trial V1.2, Seções 1-6 | Este contrato (referencie) |
| Retenção de dados | Política de Privacidade (TBD) | Este contrato (referencie) |
| Reembolso (jurídico) | Termos de Uso (TBD) | Este contrato (operacional apenas) |

---

## 📋 ÍNDICE

1. **Estados Financeiros e Transições**
2. **Planos e Valores**
3. **Ciclo de Assinatura (Trial → Pagamento → Renovação)**
4. **Checkout e Processamento de Pagamento**
5. **Eventos Hotmart (Webhooks)**
6. **Falhas de Pagamento e Retries**
7. **Upgrades e Downgrades**
8. **Suspensão por Falta de Pagamento**
9. **Reativação de Tenant Suspenso**
10. **Cancelamento e Saída**
11. **Reembolso (Política Operacional)**
12. **Idempotência Financeira**
13. **Duplicidade de Webhooks**
14. **Reconciliação**
15. **Relação: Trial → Assinatura → Tenant**

---

## 1. MÁQUINAS DE ESTADO — 5 DIMENSÕES INDEPENDENTES

### 1.1 Separação Crítica

O contrato anterior misturava:
- **Estado do trial**
- **Estado da assinatura**
- **Estado do pagamento**
- **Estado de acesso**
- **Estado de retenção de dados**

Esses são **4 máquinas de estado independentes**. Uma assinatura pode estar CANCELADA enquanto o ACESSO permanece LIBERADO até fim do ciclo pago. Um PAGAMENTO pode estar ATRASADO enquanto ACESSO é SUSPENSO.

### 1.2 As 5 Máquinas de Estado

#### Estado 1: TRIAL

```
Estados possíveis:
├─ PREPARADO (lead criou conta, não iniciou teste)
├─ ATIVO (período de teste em execução)
├─ EXPIRADO (período acabou)
└─ CONVERTIDO (lead pagou, converteu em assinatura)

Transições:
    PREPARADO → ATIVO → EXPIRADO → (CONVERTIDO ou DELETADO)
```

#### Estado 2: ASSINATURA

```
Estados possíveis:
├─ PENDENTE (criada, confirmação Hotmart aguardada)
├─ ATIVA (paga e vigente)
├─ CANCELAMENTO_AGENDADO (lead pediu cancel, vigor até fim ciclo)
├─ CANCELADA (fim do ciclo atingido ou cancelamento efetivado)
└─ ENCERRADA (deletada, dados descartados)

Transições:
    PENDENTE → ATIVA → CANCELAMENTO_AGENDADO → CANCELADA → ENCERRADA
    (qualquer → ENCERRADA se dados deletados)
```

#### Estado 3: PAGAMENTO

```
Estados possíveis:
├─ PENDENTE (Hotmart processando)
├─ APROVADO (cartão aceitou)
├─ RECUSADO (cartão recusou, retry ativo)
├─ ATRASADO (renovação não chegou a tempo)
├─ REEMBOLSADO (dinheiro voltou para cliente)
├─ CONTESTADO (chargeback aberto)
└─ RESOLVIDO (chargeback ganho/perdido)

Transições:
    PENDENTE → APROVADO → (renovação) → ATRASADO → RECUSADO
    (qualquer) → CONTESTADO → RESOLVIDO
    APROVADO → REEMBOLSADO
```

#### Estado 4: ACESSO

```
Estados possíveis:
├─ LIBERADO (acesso completo)
├─ RESTRITO (funcionalidade limitada, ex: pendente de confirmação)
├─ SUSPENSO (bloqueado por falta de pagamento)
└─ ENCERRADO (sem acesso, dados deletados)

Transições:
    LIBERADO ↔ RESTRITO ↔ SUSPENSO → ENCERRADO
    (pode voltar de SUSPENSO se pagamento aprovado)
```

#### Estado 5: RETENÇÃO DE DADOS

```
Estados possíveis:
├─ ATIVO (dados sendo usados, sem prazo de exclusão)
├─ EM_RETENCAO (dados não acessíveis, aguardando período)
├─ ELEGIVEL_EXCLUSAO (período expirou, pronto para deletar)
└─ EXCLUIDO (completamente removido)

Transições:
    ATIVO → EM_RETENCAO → ELEGIVEL_EXCLUSAO → EXCLUIDO

Duração de retenção:
    └─ Conforme Política de Privacidade (TBD)
    └─ Tipicamente 30 dias após acesso bloqueado
```

---

## 2. ESTADOS FINANCEIROS E TRANSIÇÕES (Anterior/Histórico)

### 2.1 Mapa Completo de Estados (Anterior)

```
[TRIAL_ATIVO] (sem pagamento)
    ↓
    Lead fornece cartão e confirma plano
    ↓
[PAGAMENTO_PROCESSANDO] (enviado para Hotmart)
    ├─ Hotmart valida cartão
    ├─ Captura aprovada? 
    │  ├─ SIM → Evento: payment_approved
    │  │        ↓
    │  │        [CLIENTE_ATIVO]
    │  │        ├─ Assinatura válida
    │  │        ├─ Acesso completo
    │  │        ├─ Renovação automática agendada
    │  │        └─ Transições possíveis:
    │  │           ├─ Lead muda plano → [ASSINATURA_MODIFICADA]
    │  │           ├─ Lead cancela → [ASSINATURA_CANCELADA]
    │  │           ├─ Lead não renova → [PAGAMENTO_AGUARDANDO_RENOVACAO]
    │  │           └─ Pagamento falha → [PAGAMENTO_FALHOU]
    │  │
    │  └─ NÃO → Evento: payment_failed
    │           ↓
    │           [PAGAMENTO_FALHOU]
    │           ├─ Acesso mantido por período de retry
    │           ├─ Hotmart agenda retries automáticos (3x)
    │           ├─ Notificação enviada ao lead
    │           └─ Transições:
    │              ├─ Lead fornece novo cartão → [PAGAMENTO_PROCESSANDO]
    │              ├─ Todos os retries falham → [INADIMPLENTE]
    │              └─ Lead cancela explicitamente → [CANCELADO]
    │
    └─ OU: Evento: payment_pending (ex: boleto)
       ↓
       [PAGAMENTO_PENDENTE]
       ├─ Aguardando compensação
       ├─ Acesso pode estar limitado (conforme Política)
       └─ Transições:
          ├─ Pagamento compensou → [CLIENTE_ATIVO]
          ├─ Pagamento expirou → [PAGAMENTO_FALHOU]
          └─ Lead cancela → [CANCELADO]
```

### 1.2 Definição de Cada Estado

| Estado | Descrição | Acesso | Renovação | Duração Típica |
|--------|-----------|--------|-----------|---|
| **TRIAL_ATIVO** | Lead em período de teste, sem pagamento | Completo | Não | Conforme Catálogo |
| **PAGAMENTO_PROCESSANDO** | Hotmart validando cartão | Completo | Aguardando | <5 minutos |
| **CLIENTE_ATIVO** | Pagamento aprovado, assinatura válida | Completo | Automática | Até próxima renovação |
| **ASSINATURA_MODIFICADA** | Lead mudou plano durante ciclo | Novo plano | Ajustada | Até próxima renovação |
| **PAGAMENTO_FALHOU** | Cartão recusado, retry ativo | Completo | Retry automático | 14 dias de retry |
| **INADIMPLENTE** | Múltiplas falhas, sem pagamento válido | Bloqueado | Nenhuma | Até reativação ou deleção |
| **ASSINATURA_CANCELADA** | Lead solicitou cancelamento | Até fim do ciclo | Nenhuma | Até fim do período |
| **SUSPENSO** | Falta de pagamento, fora de retry | Read-only | Nenhuma | Até reativação ou deleção |
| **DELETADO** | Tenant removido permanentemente | Nenhum | N/A | Permanente |

---

## 2. PLANOS E VALORES

### 2.1 Referência Obrigatória ao Catálogo

**Nunca copiar preços ou estrutura de planos para este documento.**

✅ **Correto:**
```
"Conforme Catálogo Comercial V1.2, Seção 6.1:
- SOLO87: R$ 87/mês
- SOLOPRO117: R$ 117/mês
- STUDIO157: R$ 157/mês
- SALAO247: R$ 247/mês
- PRO347: R$ 347/mês"
```

❌ **Errado:**
```
"Os planos são:
- SOLO87: R$ 87/mês
- SOLOPRO117: R$ 117/mês
..." (duplicação)
```

### 2.2 Elegibilidade de Plano

Conforme **Catálogo Comercial V1.2, Seção 5 (Elegibilidade Comercial):**

- Quem pode contratar qual plano
- Pré-requisitos
- Regras de upgrade/downgrade
- Restrições

*Este contrato assume que validação de elegibilidade já foi feita no trial.*

---

## 3. CICLO DE ASSINATURA (Trial → Pagamento → Renovação)

### 3.1 Transição Trial → Assinatura

**Momento:** Fim do período de trial (conforme Catálogo V1.2, Seção 6.2)

```
[TRIAL_ATIVO] no penúltimo dia
    ↓
Lead recebe notificação: "Seu trial termina amanhã"
    ├─ Incluir link de checkout
    ├─ Descrever valor observado
    └─ Sem pressão

[TRIAL_ATIVO] no último dia
    ↓
Lead clica "Continuar" ou "Escolher Plano"
    ↓
Redireciona para Hotmart checkout
    ├─ URL: https://hotmart.com/...
    ├─ Lead escolhe plano (pode ser diferente do trial)
    ├─ Lead fornece cartão
    └─ Retorna para callback NeoEve
    
[PAGAMENTO_PROCESSANDO]
    ├─ NeoEve enviou dados para Hotmart
    ├─ Hotmart valida cartão e captura
    ├─ Retorna webhook com status
    └─ Transição conforme resultado do webhook
```

### 3.2 Primeiro Pagamento (Trial → Assinatura)

**Valores cobrados no primeiro pagamento:**

Conforme **Catálogo Comercial V1.2, Seção 5.4 (Upgrade/Downgrade):**

**Cenário A: Mesmo plano do trial**
```
Lead escolheu SOLO87 para trial
Continua com SOLO87 na assinatura

Cobrança:
└─ Valor completo do plano (R$ 87)
```

**Cenário B: Upgrade durante trial**
```
Lead escolheu SOLO87 para trial
Upgrade para STUDIO157 na assinatura

Cálculo (conforme Catálogo V1.2, Seção 5.4):
├─ Dias usados em trial: 5 dias
├─ Crédito de SOLO87: R$ 87 × (5/30) = R$ 14.50
├─ Novo plano STUDIO157: R$ 157
├─ Diferença: R$ 157 - R$ 14.50 = R$ 142.50
└─ Cobrado hoje: R$ 142.50
    Próxima renovação: R$ 157 (completo)
```

**Cenário C: Downgrade durante trial**
```
Lead escolheu SALAO247 para trial
Downgrade para STUDIO157 na assinatura

Política: Sem reembolso (conforme Termos)
└─ Cobrado: R$ 157 (novo plano)
```

### 3.3 Data de Renovação

**Primeira renovação:** 30 dias após data do primeiro pagamento aprovado (ou conforme ciclo do plano)

```
Pagamento aprovado: 27-07-2026
Próxima cobrança: 27-08-2026
E a cada 27 do mês daí em diante
```

**Alteração durante ciclo:** Renovação é ajustada proporcionalmente (conforme Catálogo V1.2, Seção 5.4)

---

## 4. CHECKOUT E PROCESSAMENTO DE PAGAMENTO

### 4.1 Fluxo de Checkout (Lead Perspective)

```
Lead em estado [TRIAL_ATIVO] ou [CLIENTE_ATIVO]
    ↓
Lead clica "Continuar" / "Renovar" / "Fazer pagamento"
    ↓
NeoEve valida:
    ├─ Tenant existe? SIM
    ├─ Lead é elegível? SIM (conforme Catálogo V1.2, Seção 5)
    └─ Plano solicitado está disponível? SIM
    
    ↓ (Se validação passar)
    
NeoEve constrói URL Hotmart com parâmetros:
    ├─ product_id (qual plano)
    ├─ customer_email (lead email)
    ├─ customer_name (lead nome)
    ├─ price (valor R$ conforme Catálogo V1.2)
    ├─ callback_url (onde Hotmart envia webhook)
    ├─ reference_id (tenant_id único)
    └─ utc_offset (timezone)
    
    ↓
Redireciona lead para Hotmart
    ├─ URL: https://checkout.hotmart.com/...
    ├─ Lead vê formulário de pagamento Hotmart
    └─ Lead fornece cartão/boleto
    
    ↓ (Hotmart processa)
    
Hotmart valida:
    ├─ Dados do cartão corretos?
    ├─ Saldo suficiente?
    ├─ Fraude detectada?
    └─ 3D Secure necessário?
    
    ↓
Hotmart retorna status:
    ├─ approved → Envia webhook payment_approved
    ├─ declined → Envia webhook payment_failed
    ├─ pending → Envia webhook payment_pending
    └─ error → Envia webhook payment_error
```

### 4.2 Callback e Redirecionamento Pós-Pagamento

Após Hotmart processar, lead é redirecionado:

```
payment_approved
└─ Redireciona para: https://app.neoeve.com/sucesso
   ├─ Mensagem: "Bem-vindo! Sua assinatura está ativa"
   ├─ Exibe plano contratado
   └─ Lead pode começar usar

payment_failed
└─ Redireciona para: https://app.neoeve.com/erro-pagamento
   ├─ Mensagem: "Pagamento foi recusado"
   ├─ Motivo (se disponível)
   ├─ Link para tentar novamente
   └─ Lead volta a TRIAL_ATIVO (se trial não expirou)

payment_pending
└─ Redireciona para: https://app.neoeve.com/pagamento-pendente
   ├─ Mensagem: "Aguardando confirmação do pagamento"
   ├─ Instruções (se boleto)
   └─ Lead acesso pode estar limitado
```

---

## 5. EVENTOS HOTMART (Webhooks)

### 5.1 Eventos Esperados

NeoEve integra com Hotmart via webhooks. Cada evento dispara ação específica.

| Evento Hotmart | Payload | Ação NeoEve | Novo Estado |
|---|---|---|---|
| `purchase_approved` | {product, customer, price, reference_id} | Criar assinatura, ativar tenant | CLIENTE_ATIVO |
| `purchase_pending` | {product, customer, reference_id} | Notificar lead | PAGAMENTO_PENDENTE |
| `purchase_failed` | {product, customer, reason, reference_id} | Notificar lead, iniciar retry | PAGAMENTO_FALHOU |
| `purchase_error` | {error_code, reference_id} | Log de erro, investigação manual | PAGAMENTO_ERRO |
| `subscription_renewed` | {product, customer, reference_id} | Log de sucesso, próxima renovação | CLIENTE_ATIVO |
| `subscription_renewed_failed` | {reason, reference_id} | Notificar lead, marcar falha | PAGAMENTO_FALHOU |
| `subscription_canceled` | {customer, reference_id} | Marcar cancelamento | ASSINATURA_CANCELADA |
| `subscription_expired` | {reference_id} | Bloquear acesso | SUSPENSO |
| `chargeback_opened` | {customer, reference_id} | Investigação manual, possível bloqueio | INVESTIGACAO |
| `customer_chargeback_dispute_won` | {reference_id} | Reativar se suspenso | CLIENTE_ATIVO |
| `customer_chargeback_dispute_lost` | {reference_id} | Manter suspenso, investigação | SUSPENSO |

### 5.2 Autenticidade do Webhook

**Validação obrigatória:**

A autenticidade do webhook deverá ser validada pelo mecanismo oficial vigente da Hotmart, atualmente baseado em credencial de autenticação (`hottok`) disponibilizada na configuração do webhook.

⚠️ **O mecanismo concreto deverá ser confirmado na documentação oficial da Hotmart e validado em sandbox antes da implementação.**

**Camadas de proteção recomendadas (além do mecanismo Hotmart):**

```
1. HTTPS obrigatório
   └─ Garantir conexão segura end-to-end

2. Autenticação oficial Hotmart
   └─ Validar credencial conforme documentação

3. Segredo armazenado com segurança
   └─ Nunca em código-fonte
   └─ Usar gerenciador de secrets (ex: Google Secret Manager)

4. Comparação segura
   └─ Usar constant-time comparison (evitar timing attacks)
   └─ Não revelar diferenças de falha em logs públicos

5. Validação estrutural do payload
   └─ Verificar tipos esperados (product_id, customer_id, etc)
   └─ Rejeitar payloads malformados

6. Validação de origem
   └─ Validar que produto_id, oferta_id pertencem a NeoEve
   └─ Validar que transaction referencia assinatura conhecida

7. Idempotência (vide Seção 12)
   └─ Não processar eventos duplicados

8. Reconciliação posterior (vide Seção 14)
   └─ Consultando API Hotmart como fonte autoritária
   └─ Detectar webhooks perdidos ou fraudados
```

**Não depender unicamente de autenticação de webhook.** Usar webhook como aviso rápido, API como verdade autorizada.

### 5.3 Response e Retry

**NeoEve DEVE responder:**

```
Ao receber webhook:
├─ Validar assinatura (5.2)
├─ Processar evento (atomicamente)
├─ Responder com HTTP 200 OK em <10 segundos
└─ Retorno: {"status": "success", "processed": true}
```

**Se NeoEve não responder:**
```
Hotmart retry automático:
├─ Retry 1: 1 minuto depois
├─ Retry 2: 5 minutos depois
├─ Retry 3: 15 minutos depois
├─ Retry 4: 1 hora depois
├─ Retry 5: 6 horas depois
└─ Após 5 falhas: Registrar para investigação manual
```

---

## 6. FALHAS DE PAGAMENTO E RETRIES

### 6.1 Motivos de Falha (Hotmart)

Hotmart retorna código de erro:

| Código | Motivo | Ação NeoEve |
|--------|--------|------------|
| `insufficient_funds` | Saldo insuficiente | Retry automático, avisar lead |
| `expired_card` | Cartão vencido | Solicitar novo cartão |
| `fraud_detected` | Fraude suspeita | Bloquear, investigação manual |
| `card_declined` | Cartão recusado (genérico) | Retry automático |
| `3d_secure_required` | Autenticação 2FA necessária | Redirecionar para 3DS |
| `network_error` | Erro de conectividade | Retry automático |
| `invalid_card_number` | Cartão inválido | Solicitar novo cartão |
| `authentication_failed` | Dados incorretos | Solicitar revisão |

### 6.2 Mecanismos de Retry — 4 Tipos Distintos

Quando um pagamento falha, até **4 processos independentes** podem estar envolvidos. Cada um tem dono, limite, intervalo e semântica própria.

#### 6.2.1 Retry de Cobrança (Hotmart → Provedor de Pagamento)

**Responsável:** Hotmart  
**Limite:** Conforme configuração da oferta (tipicamente 3-5 tentativas)  
**Intervalo:** Conforme política Hotmart (tipicamente dia 3, 7, 14)  
**Parada:** Aprovação OU fim do intervalo  

```
Hotmart tenta cobrar novamente usando mesmo cartão
├─ Tentativa 1: 3 dias depois
├─ Tentativa 2: 7 dias depois
├─ Tentativa 3: 14 dias depois
├─ (...conforme configuração)
└─ Se aprovado em qualquer tentativa:
   └─ Webhook payment_approved enviado a NeoEve
```

#### 6.2.2 Reentrega de Webhook (Hotmart → NeoEve)

**Responsável:** Hotmart  
**Limite:** 5 reentregas (conforme documentação Hotmart)  
**Intervalo:** 1min, 5min, 15min, 1h, 6h  
**Parada:** NeoEve responde HTTP 200 OU fim do intervalo  

```
Se NeoEve não responde 200 OK em <10 segundos:
├─ Hotmart reenvia o webhook
├─ 1ª reentrega: 1 minuto depois
├─ 2ª reentrega: 5 minutos depois
├─ 3ª reentrega: 15 minutos depois
├─ 4ª reentrega: 1 hora depois
├─ 5ª reentrega: 6 horas depois
└─ Após 5: Registrar para investigação manual (Hotmart)
```

⚠️ **Nota:** Reentrega reenvia o MESMO evento, não reaplica a ação.

#### 6.2.3 Reprocessamento Interno (NeoEve Backend)

**Responsável:** NeoEve  
**Limite:** Lógica de aplicação (backoff exponencial)  
**Intervalo:** 1s, 2s, 4s, 8s, ... (exponencial ou conforme implementação)  
**Parada:** Sucesso OU limite de tentativa  

```
Se webhook chegou mas processamento falhou:
├─ Idempotência detecta: mesmo provider_event_id
├─ Backend tenta reprocessar (backoff exponencial)
├─ Se persistir: log + alertar SRE
└─ Reconciliação detectará qualquer divergência remanescente
```

#### 6.2.4 Reconciliação Financeira (NeoEve via API)

**Responsável:** NeoEve backend  
**Frequência:** Diária (fora de pico)  
**Ámbito:** Todas assinaturas, últimas 24h  
**Ação:** Detectar webhooks perdidos, duplicados, fora de ordem  

```
NeoEve consulta API Hotmart automaticamente:
├─ "Quais transações foram criadas hoje?"
├─ "Qual é status de cada assinatura?"
├─ "Há pagamentos pendentes?"
└─ Compara com estado NeoEve
    ├─ Bate: OK, sem ação
    └─ Diverge: Reconciliar (vide Seção 14)
```

### 6.3 Transição para INADIMPLENTE

Quando **todos os 4 mecanismos** se esgotam:

```
Retry Cobrança (Hotmart): Esgotado ❌
Reentrega Webhook (Hotmart): Esgotada ❌
Reprocessamento (NeoEve): Falhou ❌
Reconciliação: Ainda mostra divergência ❌
    ↓
[INADIMPLENTE]
├─ Acesso bloqueado
├─ Notificação ao lead: "Assinatura suspensa"
├─ Oferecer novo cartão + suporte
└─ 30 dias para resolver antes de deleção
```

### 6.3 Ação do Lead Durante Falha

Lead pode:

```
Opção A: Tentar novo cartão
    └─ Vai ao dashboard
    └─ Clica "Atualizar método de pagamento"
    └─ Fornece novo cartão
    └─ NeoEve envia para Hotmart
    └─ Hotmart processa imediatamente

Opção B: Aguardar Hotmart retry
    └─ Nada fazer
    └─ Hotmart tenta automaticamente
    └─ Se funcionar: Aprovado

Opção C: Cancelar
    └─ Lead clica "Cancelar assinatura"
    └─ Estado muda para ASSINATURA_CANCELADA
    └─ Acesso é removido após fim do ciclo
```

---

## 7. UPGRADES E DOWNGRADES

### 7.1 Princípio Geral

**Upgrades e downgrades deverão seguir a modalidade suportada e configurada na Hotmart.**

O sistema NeoEve não calculará, concederá créditos, pró-rata ou reembolsos parciais sem confirmação explícita da plataforma de pagamento e validação da política comercial vigente.

⚠️ **Antes de implementar qualquer lógica de upgrade/downgrade, validar exatamente:**
1. Comportamento configurado na Hotmart
2. API disponível para trocar planos
3. Política comercial (crédito? sem reembolso? reembolso?)
4. Datas de entrada em vigor da mudança

### 7.2 Upgrade (Mudar para Plano Maior)

```
Lead solicita upgrade (SOLO87 → STUDIO157)
    ↓
NeoEve valida:
    ├─ Novo plano > plano atual? SIM
    ├─ Lead é elegível? SIM (conforme Catálogo V1.2, Seção 5)
    └─ Assinatura está ativa? SIM
    
    ↓
NeoEve envia mudança de plano para Hotmart
    ├─ Via API Hotmart (método e parâmetros por validar)
    └─ Hotmart processa a mudança conforme sua configuração
    
    ↓
Hotmart define:
    ├─ Quando entra em vigor (imediato? próximo ciclo?)
    ├─ Como cobrar diferença (imediato? próximo ciclo?)
    ├─ Se há crédito pró-rata (não será calculado por NeoEve)
    └─ Data da próxima renovação (Hotmart reclcula, NeoEve não)

[ASSINATURA_MODIFICADA]
    ├─ NeoEve aguarda webhook com status da mudança
    ├─ Webhook informa: plano efetivo, nova data renovação, etc
    └─ Transição: Próxima renovação → [CLIENTE_ATIVO]
```

**Nota:** NeoEve não calcula diferença, não concede créditos. Apenas coordena com Hotmart e aguarda confirmação.

### 7.3 Downgrade (Mudar para Plano Menor)

```
Lead solicita downgrade (SALAO247 → STUDIO157)
    ↓
NeoEve valida:
    ├─ Novo plano < plano atual? SIM
    ├─ Lead é elegível? SIM
    ├─ Há dados que serão perdidos? (ex: 5 profissionais → 3 slots)
    │  ├─ SIM → Solicitar confirmação explícita ao lead
    │  │         Lead reconhece perda de dados
    │  └─ NÃO → Prosseguir
    └─ Confirmação recebida
    
    ↓
NeoEve envia mudança de plano para Hotmart
    ├─ Via API Hotmart (método e parâmetros por validar)
    └─ Hotmart processa conforme sua configuração
    
    ↓
Hotmart define:
    ├─ Quando entra em vigor (imediato? próximo ciclo?)
    ├─ Reembolso? Crédito? Sem ação? (NeoEve não calcula)
    ├─ Próxima data de renovação (Hotmart recalcula)
    └─ Status da mudança (confirmado, pendente, erro)

[ASSINATURA_MODIFICADA]
    ├─ NeoEve aguarda webhook com confirmação
    ├─ Se confirmado: Features removidas param gradualmente
    ├─ Dados excess (ex: profissional 4-5) podem ser archive/removidos
    └─ Transição: Próxima renovação → [CLIENTE_ATIVO]
```

**Nota:** Downgrade respeita política de retenção de dados. NeoEve não faz cálculos de reembolso.

### 7.4 Validação Antes de Implementar

**Este contrato descreve o fluxo esperado, mas a implementação real depende:**

- [ ] Documentação oficial Hotmart (upgrade/downgrade via API)
- [ ] Comportamento exato em sandbox (entrar em vigor quando?)
- [ ] Política de crédito/reembolso (confirmado com Hotmart)
- [ ] Webhooks esperados (confirmado com Hotmart)
- [ ] Casos extremos (o que acontece se lead faz downgrade 2 vezes em 1 dia?)

---

## 8. SUSPENSÃO POR FALTA DE PAGAMENTO

### 8.1 Transição: INADIMPLENTE → SUSPENSO

```
[PAGAMENTO_FALHOU] + 14 dias de retry exauridos
    ↓
Hotmart completou 5 tentativas de retry
Nenhuma aprovação
    ↓
NeoEve recebe webhook: subscription_expired ou subscription_canceled
    ↓
[INADIMPLENTE]
    ├─ Estado muda para INADIMPLENTE
    ├─ Acesso ao tenant é bloqueado
    ├─ Eve para de responder
    ├─ Clientes do lead recebem mensagem: "Serviço temporariamente indisponível"
    ├─ Notificação ao lead: "Sua assinatura foi suspensa por falta de pagamento"
    ├─ Incluir: "Você tem 30 dias para pagar ou dados serão deletados"
    ├─ Incluir link: "Clique aqui para fornecer novo cartão"
    └─ Período de resolução: 30 dias
```

### 8.2 Ações Durante Suspensão

Lead pode:

```
Opção A: Fornecer novo cartão (30 dias)
    └─ NeoEve envia para Hotmart
    └─ Se aprovado: Estado volta para CLIENTE_ATIVO
    
Opção B: Contactar suporte (30 dias)
    └─ Suporte pode oferecer:
       ├─ Parcelamento
       ├─ Desconto
       └─ Extensão do período (caso a caso)
    
Opção C: Não fazer nada (30 dias)
    └─ Após 30 dias: Estado muda para DELETADO
    └─ Tenant e dados são removidos permanentemente
```

---

## 9. REATIVAÇÃO DE TENANT SUSPENSO

### 9.1 Processo de Reativação

```
[INADIMPLENTE] com período de reativação ainda válido
    ↓
Lead fornece novo cartão
    ↓
NeoEve envia para Hotmart
    ├─ Produto: Plano original
    ├─ Valor: Valor em aberto + próxima renovação
    └─ Hotmart processa
    
    ↓
Hotmart retorna:
    ├─ approval → Estado volta para CLIENTE_ATIVO
    ├─ decline → Permanecer em INADIMPLENTE, oferecer nova tentativa
    └─ pending → Estado para PAGAMENTO_PENDENTE
    
[CLIENTE_ATIVO]
    ├─ Acesso restaurado imediatamente
    ├─ Eve volta a responder
    ├─ Clientes veem agenda novamente
    ├─ Nova data de renovação calculada (30 dias após pagamento)
    └─ Lead recebe: "Bem-vindo de volta! Sua assinatura está ativa"
```

### 9.2 Impossibilidade de Reativação

Lead **NÃO pode reativar** se:

```
❌ Período de 30 dias exaurado (→ Estado DELETADO)
❌ Tenant foi deletado manualmente
❌ Conta foi bloqueada por violação de TOS
❌ Chargeback foi perdido (e não resolveido)
❌ Múltiplos chargebacks (padrão de fraude)
```

---

## 10. CANCELAMENTO E SAÍDA

### 10.1 Cancelamento Proativo (Lead Pede)

```
[CLIENTE_ATIVO]
    ↓
Lead acessa dashboard
    ↓
Lead clica "Cancelar assinatura"
    ↓
NeoEve solicita motivo (opcional)
    ├─ "Por que está saindo?"
    ├─ Lead pode responder ou pular
    └─ Feedback é armazenado para análise
    
    ↓
NeoEve confirma:
    "Sua assinatura será cancelada no final deste ciclo.
     Data: [data exata]
     Você não será cobrado depois disso."
    
    ↓
[ASSINATURA_CANCELADA]
    ├─ Cobranças futuras são bloqueadas
    ├─ Hotmart não cobra na próxima renovação
    ├─ Acesso continua até fim do ciclo
    ├─ Notificação ao lead 3 dias antes do término
    └─ No último dia: "Sua assinatura encerra hoje"
    
    ↓ (Fim do ciclo)
    
[SUSPENSO] ou [DELETADO]
    ├─ Conforme Política de Privacidade (TBD)
    └─ Lead pode reativar durante período de reativação (Contrato Trial)
```

### 10.2 Morte Natural (Não Renovação)

```
[CLIENTE_ATIVO]
    ↓
Data de renovação chega
    ↓
NeoEve envia 3 notificações:
    ├─ 30 dias antes: "Sua assinatura será renovada em 30 dias"
    ├─ 7 dias antes: "Renovação em 7 dias"
    └─ 1 dia antes: "Última chance: renovação amanhã"
    
    ↓
Hotmart tenta cobrar automaticamente
    ├─ Lead não respondeu, sem atualização de cartão
    ├─ Hotmart não consegue cobrar
    └─ Retorna webhook: subscription_expired
    
    ↓
[SUSPENSO]
    └─ Conforme Seção 8
```

---

## 11. REEMBOLSO (Política Operacional)

### 11.1 Elegibilidade de Reembolso

A elegibilidade de reembolso será determinada pela **política de garantia configurada na oferta** e pelas regras legais aplicáveis.

NeoEve não manterá uma duração fixa de reembolso independente da fonte comercial e da plataforma.

⚠️ **Antes de implementar reembolso:**

```
Validar:
├─ Qual é a política oficial da oferta no Hotmart?
├─ Qual é o período mínimo garantido por lei?
├─ Como Hotmart processa reembolsos?
├─ Qual é a política comercial vigente?
└─ Quem autoriza reembolsos (Hotmart, NeoEve, Finance)?
```

**Exemplo (ilustrativo, validar):**

```
Período de elegibilidade (conforme oferta):
    ├─ Até N dias após pagamento → Reembolso integral
    ├─ N+1 até M dias → Crédito (sem reembolso)
    └─ Após M dias → Sem reembolso

Nota: N e M são configuráveis por oferta.
      Hotmart mantém isso, NeoEve não calcula.
```

### 11.2 Processamento de Reembolso

```
Lead solicita reembolso
    ↓
NeoEve verifica:
    ├─ Data do pagamento (elegível?)
    ├─ Motivo (válido?)
    └─ Tenant (não foi usado extensivamente?)
    
    ↓
Se elegível:
    └─ NeoEve autoriza reembolso via Hotmart
    ├─ Hotmart processa (5-10 dias úteis)
    ├─ Lead vê devolução no cartão
    └─ Lead recebe notificação: "Reembolso processado"
    
Se não elegível:
    └─ NeoEve oferece alternativa:
    ├─ "Downgrade para plano menor?"
    ├─ "Crédito em conta?"
    └─ "Conversar com suporte?"
```

---

## 12. IDEMPOTÊNCIA FINANCEIRA

### 12.1 Princípio

Operações financeiras devem ser **idempotentes:** Se o mesmo evento for processado 2+ vezes, o resultado final deve ser idêntico à primeira execução.

**Chave:** Usar identidade do EVENTO, não apenas da transação. Uma assinatura pode gerar múltiplos eventos (payment, chargeback, refund, cancellation) ao longo do tempo.

### 12.2 Estrutura de Identificação

```
Cada evento Hotmart carrega (conforme documentação oficial):

provider = "HOTMART" (constante)
provider_event_id (único para cada evento Hotmart)
provider_event_type (ex: payment_approved, payment_failed, etc)
provider_transaction_id (referencia cobrança específica)
provider_subscription_id (referencia assinatura)
received_at (timestamp de recebimento)
payload_hash (hash SHA256 do corpo para auditoria)

Chave primária lógica para idempotência:
    └─ HOTMART + provider_event_id

Proteção alternativa se provider_event_id não disponível:
    └─ provider_event_type + provider_transaction_id + 
       provider_subscription_id + relevant_timestamp
```

### 12.3 Implementação

```
Ao receber webhook:
    ├─ Extrair provider_event_id (Hotmart)
    ├─ Extrair provider_event_type (ex: payment_approved)
    ├─ Extrair provider_subscription_id
    ├─ Calcular payload_hash = SHA256(corpo_raw)
    │
    ├─ Verificar se já foi processado:
    │  ├─ Consultar tabela: processed_events
    │  ├─ Buscar: provider=HOTMART + provider_event_id
    │  ├─ SIM → Retornar 200 OK (não processar)
    │  └─ NÃO → Prosseguir
    │
    └─ Processar evento atomicamente:
       ├─ Validar: payload_hash == hash armazenado?
       │            (detectar payload modificado)
       ├─ Executar lógica do evento (1 vez apenas)
       ├─ Gravar provider_event_id como "processado"
       ├─ Registrar: processed_at, processing_status=SUCCESS
       └─ Responder HTTP 200 OK
       
Banco de Dados (exemplo):
    ├─ Tabela: processed_webhook_events
    ├─ Colunas:
    │  ├─ provider (ex: HOTMART)
    │  ├─ provider_event_id (Hotmart event_id)
    │  ├─ provider_event_type (ex: payment_approved)
    │  ├─ provider_transaction_id (tx ref)
    │  ├─ provider_subscription_id (sub ref)
    │  ├─ payload_hash (auditoria)
    │  ├─ received_at (timestamp recebimento)
    │  ├─ processed_at (timestamp processamento)
    │  └─ processing_status (SUCCESS/FAILED/RETRY)
    │
    └─ Índices:
       ├─ PRIMARY KEY: (provider, provider_event_id)
       ├─ INDEX: provider_subscription_id (buscar eventos de sub)
       └─ INDEX: received_at (reconciliação histórico)
```

### 12.4 Exemplo de Cenário

```
Webhook payment_approved chega
    ├─ provider = "HOTMART"
    ├─ provider_event_id = "EVT-2026-07-27-99999"
    ├─ provider_transaction_id = "TXN-88888"
    ├─ provider_subscription_id = "SUB-77777"
    └─ Hotmart tenta entregar 2x (timeout de rede)
    
Primeira entrega:
    ├─ NeoEve valida payload_hash
    ├─ Consulta processed_events: não encontra provider_event_id
    ├─ Processa: cria assinatura
    ├─ Registra: provider_event_id=EVT-2026-07-27-99999, status=SUCCESS
    └─ Responde HTTP 200 OK
    
Segunda entrega (mesmo webhook, 5 minutos depois):
    ├─ NeoEve valida payload_hash (ok, conteúdo idêntico)
    ├─ Consulta processed_events: ENCONTRA EVT-2026-07-27-99999
    ├─ Status anterior: SUCCESS
    ├─ Detecta: evento já processado
    └─ Retorna HTTP 200 OK (não processa de novo)
    
Resultado:
    └─ Apenas 1 assinatura criada (não 2)
    └─ Webhook duplicado não causou cobrança duplicada
```

### 12.5 Proteção Adicional

```
Além de idempotência por provider_event_id:

1. Validação de payload
   └─ payload_hash desviou? Rejeitar (possível tampering)

2. Validação estrutural
   └─ Campos obrigatórios presentes? Tipos corretos?

3. Validação de origem
   └─ provider_subscription_id referencia sub conhecida?
   └─ provider_transaction_id é válido (formato)?

4. Proteção contra out-of-order
   └─ Evento é mais recente que último evento dessa sub?
   └─ Se não: flagged para investigação (pode ser indicador de replay)

5. Reconciliação posterior (Seção 14)
   └─ API Hotmart é fonte autoritária
   └─ Detecta qualquer anomalia em idempotência
```

---

## 13. DUPLICIDADE DE WEBHOOKS

### 13.1 Detecção

```
Hotmart pode entregar webhook mais de 1x:
    ├─ Timeout de rede (Hotmart não recebeu 200 OK)
    ├─ Retry automático (até 5 tentativas)
    ├─ Duplicação acidental (bug Hotmart)
    └─ Cada entrega pode ser segundos/minutos/horas depois
```

### 13.2 Proteção

Além de idempotência, implementar:

```
Rate Limiting por Lead:
    ├─ Máximo 1 payment_approved por lead por 60 segundos
    ├─ Se 2x no mesmo minuto: segunda é rejeitada (mas retorna 200)
    └─ Evita race condition

Idempotência via transaction_id (vide Seção 12)
    ├─ Cada evento tem ID único do Hotmart
    ├─ NeoEve armazena quais já foram processados
    └─ Duplicados são ignorados automaticamente
```

---

## 14. RECONCILIAÇÃO — HOTMART ↔ NEOEVE

### 14.1 Hierarquia de Verdade (Crítico)

```
Nenhuma fonte isolada é confiável. A reconciliação compara 3 fontes:

┌─────────────────────────────────────┐
│ FONTE 1: API Hotmart (MAIS CONFIÁVEL)
│ ├─ Estado atual de cada assinatura
│ ├─ Histórico de transações
│ ├─ Próximas cobranças agendadas
│ └─ Autorizações/chargebacks
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ FONTE 2: Webhooks Hotmart (AVISO RÁPIDO)
│ ├─ Eventos em tempo real
│ ├─ Pode estar perdido/duplicado/atrasado
│ ├─ Nunca é autoridade sozinho
│ └─ Sempre validar contra API
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ FONTE 3: Registro Interno NeoEve (OPERACIONAL)
│ ├─ Estado computado localmente
│ ├─ Pode estar desatualizado
│ ├─ Pode ter bugs de processamento
│ └─ Ferramenta para debug, não verdade
└─────────────────────────────────────┘

Reconciliação:
    └─ API Hotmart é VERDADE AUTORITÁRIA
    └─ Webhooks confirmam eventos
    └─ Registro NeoEve é validado contra API
```

### 14.2 Cenários Onde Reconciliação é Necessária

```
Cenário A: Webhook perdido
    ├─ Lead pagou na Hotmart ✓ (API mostra transação)
    ├─ Hotmart enviou webhook ✓ (tentou 5x)
    ├─ NeoEve nunca processou ✗ (registro vazio)
    └─ Ação: Criar assinatura faltante via API

Cenário B: Processamento falhou
    ├─ Webhook chegou ✓
    ├─ NeoEve bug: falhou ao processar ✗
    ├─ API Hotmart: transação aprovada ✓
    ├─ Registro NeoEve: vazio ✗
    └─ Ação: Reprocessar webhook manualmente

Cenário C: Duplicação acidental
    ├─ Webhook chegou 2x (retry Hotmart)
    ├─ Idempotência funcionou: 1 assinatura criada ✓
    ├─ Webhook 2x processado: não (detectado por provider_event_id)
    └─ Ação: Nenhuma (sistema funcionou)

Cenário D: Out-of-order
    ├─ Eventos chegam fora de sequência
    ├─ Ex: refund chega antes de payment_approved
    ├─ API Hotmart: verdade (ordem correta de fatos)
    └─ Ação: Validar contra API antes de falhar
```

### 14.3 Processo de Reconciliação

**Frequência:** Diária, fora de pico (ex: 02:00 UTC)  
**Escopo:** Últimas 24h + flag de divergências antigas  
**Fonte:** API Hotmart consultada diretamente  

```
Reconciliação Diária:

[1] Consultar API Hotmart:
    ├─ "Quais assinaturas foram modificadas nos últimos 24h?"
    ├─ "Qual é o status atual de cada assinatura?"
    ├─ "Houve novos pagamentos?"
    ├─ "Houve novos chargebacks?"
    └─ Hotmart retorna: [lista de eventos]

[2] Para cada evento Hotmart:
    ├─ Verificar: NeoEve tem registro desse evento?
    │  ├─ SIM (provider_event_id bate): ✓ OK
    │  └─ NÃO: ✗ MISMATCH → Investigar
    │
    └─ Se MISMATCH:
       ├─ Tipo: Webhook perdido, duplicado ou corrupção
       ├─ Ação conforme tipo
       └─ Registrar para análise

[3] Para cada assinatura NeoEve:
    ├─ Verificar: Hotmart tem esse ID?
    ├─ Se SIM: Estado bate? (ativo/cancelado/etc)
    └─ Se NÃO: Assinatura órfã (bug NeoEve)

[4] Gerar relatório:
    ├─ Total de comparações
    ├─ Matches (OK)
    ├─ Mismatches (divergências)
    ├─ Ações tomadas
    └─ Alertas (se houver anomalias)

[5] Alertar:
    └─ Se divergências: notificar SRE
```

### 14.4 Estrutura de Dados para Reconciliação

```
Tabela: hotmart_reconciliation_run

Colunas:
├─ run_id (único)
├─ run_date (dia da reconciliação)
├─ run_time (hora início)
├─ duration_seconds
├─ total_subscriptions_hotmart
├─ total_subscriptions_neoeve
├─ matches_count
├─ mismatches_count
├─ actions_taken
├─ status (SUCCESS, PARTIAL, FAILED)
└─ notes

Tabela: hotmart_reconciliation_mismatch

Colunas:
├─ run_id (referência)
├─ subscription_id
├─ mismatch_type (webhook_lost, duplicate, corrupt, orphan)
├─ hotmart_state
├─ neoeve_state
├─ discovered_at
├─ resolved (TRUE/FALSE)
├─ resolution_action
└─ notes
```

### 14.5 Exemplo de Reconciliação

```
[2026-07-27 02:00:00] Reconciliação iniciada

API Hotmart retorna: 47 transações últimas 24h
Registro NeoEve: 45 assinaturas encontradas

Análise:

Match ✓ [43 casos]: NeoEve tem webhook de cada transação
Mismatch ✗ [2 casos]:
│
├─ Mismatch 1: João Silva
│  ├─ Hotmart: transação aprovada 2026-07-26 23:15
│  ├─ NeoEve: registro vazio (webhook nunca chegou)
│  ├─ Tipo: Webhook perdido
│  ├─ Ação: Processar webhook manualmente
│  └─ Resultado: Assinatura criada, tenant ativado
│
└─ Mismatch 2: Maria Santos
   ├─ Hotmart: 1 transação em 2026-07-26 19:00
   ├─ NeoEve: 1 assinatura (idempotência evitou duplicação)
   ├─ Webhook recebido 2x (retry)
   ├─ Tipo: Duplicate (não um problema, funcionou)
   └─ Ação: Nenhuma (sistema resiliente)

Orphan check (NeoEve sem correspondência Hotmart): 0 encontradas

[2026-07-27 02:15:00] Reconciliação concluída
Status: SUCCESS
├─ Discrepâncias resolvidas: 1
├─ Duplicações detectadas e ignoradas: 1
└─ Relatório enviado para logs + SRE
```

---

## 15. RELAÇÃO: TRIAL → ASSINATURA → TENANT

### 15.1 Diagrama de Relacionamentos

```
[LEAD] (usuário externo)
    ↓
    ├─ Email único
    ├─ Telefone
    └─ Nome
    
    ↓
    
[TENANT] (instância isolada)
    ├─ tenant_id único
    ├─ lead_id (referência)
    ├─ Estado: TRIAL_ATIVO → CLIENTE_ATIVO → SUSPENSO/DELETADO
    ├─ Plano atual: SOLO87, SOLOPRO117, etc (referência ao Catálogo)
    └─ Acesso: Conforme estado
    
    ↓
    
[ASSINATURA] (contrato financeiro)
    ├─ subscription_id único
    ├─ tenant_id (referência)
    ├─ plano: SOLO87, SOLOPRO117, etc
    ├─ valor: R$ (conforme Catálogo V1.2)
    ├─ data_start: quando assinatura ativa
    ├─ data_renovacao: próxima cobrança
    ├─ status: ATIVO, CANCELADO, SUSPENSO, etc
    └─ Hotmart transaction_id: para rastrear pagamentos
    
    ↓
    
[TRIAL] (período de teste)
    ├─ trial_id
    ├─ tenant_id (referência)
    ├─ data_inicio: quando trial começou
    ├─ data_fim: quando trial expira (conforme Catálogo V1.2)
    ├─ duracao: número de dias (conforme Catálogo V1.2)
    └─ Ao expirar:
       ├─ Lead não pagou → Tenant SUSPENSO (Contrato Trial)
       ├─ Lead pagou → Assinatura criada (este contrato)
       └─ Tenant transiciona: TRIAL_ATIVO → CLIENTE_ATIVO
```

### 15.2 Fluxo Completo: Lead → Tenant → Assinatura

```
1. Lead cria conta
   └─ Cria [LEAD]
   └─ Cria [TENANT] com estado = TRIAL_ATIVO
   └─ Cria [TRIAL] com duração = conforme Catálogo V1.2
   
2. Lead usa sistema durante trial
   └─ Telemetria coletada (para Check-in, conforme Contrato Trial)
   └─ Tenant acessa todas as features
   
3. Trial próximo de expirar
   └─ Check-in (Contrato Trial, Seção 6)
   └─ Relatório (Contrato Trial, Seção 6)
   
4. Lead decide continuar
   └─ Clica "Continuar" ou "Assinar"
   └─ Vai para Hotmart checkout
   └─ Fornece cartão
   └─ Hotmart processa
   
5. Hotmart aprova pagamento
   └─ Envia webhook: payment_approved
   └─ Cria [ASSINATURA]
   ├─ subscription_id = gerado
   ├─ tenant_id = referência
   ├─ plano = escolha do lead (conforme Catálogo V1.2)
   ├─ valor = conforme Catálogo V1.2
   ├─ data_start = hoje
   ├─ data_renovacao = 30 dias depois
   └─ transaction_id = Hotmart transaction (para rastreamento)
   
6. Estado do Tenant muda
   └─ Antes: TRIAL_ATIVO
   └─ Depois: CLIENTE_ATIVO
   └─ Acesso: Mantém completo (não há interrupção)

7. Lead continua usando (com assinatura ativa)
   └─ Próxima renovação agendada em data_renovacao
   └─ Conforme Hotmart webhook, state muda (vide Seção 1.1)

8. Ao cancelar
   └─ Assinatura muda de estado
   └─ Tenant transiciona conforme Contrato Trial
```

### 15.3 Isolamento Multi-tenant

**Isolamento por estrutura de caminhos, validação de tenant_id e regras de segurança.**

```
Cada TENANT é isolado por múltiplas camadas:

1. Estrutura de Caminhos (Cloud Firestore)
   ├─ Coleção: /tenants/{tenant_id}/agendamentos
   ├─ Coleção: /tenants/{tenant_id}/clientes
   ├─ Coleção: /tenants/{tenant_id}/profissionais
   └─ Estrutura força isolamento no design

2. Validação Obrigatória de tenant_id no Backend
   ├─ Toda query verifica: usuario.tenant_id == parametro.tenant_id
   ├─ Nenhuma query executa sem validação
   ├─ Servidor administrativo (Admin SDK) também valida
   └─ Mesmo SDK admin não contorna validação

3. Firebase Security Rules (Cliente)
   ├─ match /tenants/{tenant_id}/agendamentos/{doc} {
   │    allow read, write: if request.auth.uid == tenant_id
   ├─ Impede acesso direto do cliente a outro tenant
   └─ Camada de defesa em profundidade

4. Backend Service (Servidor NeoEve)
   ├─ Todas operações validam tenant_id do usuário
   ├─ Queries sempre filtram: where("tenant_id", "==", user_tenant_id)
   ├─ Admin SDK não substitui essa validação
   └─ Isolamento existe mesmo com credenciais administrativas

5. Validação de Integridade
   ├─ Ao salvar documento, verificar tenant_id está presente
   ├─ Ao ler documento, verificar tenant_id bate com usuário
   └─ Logs de segurança registram tentativas de cruzamento
```

**Hierarquia de confiança:**

```
Mais confiável (sempre execute):
    ↓
Backend Server + Validação tenant_id
    ↓
Cloud Firestore Rules
    ↓
Cliente (JavaScript/React)
    ↓
Menos confiável (pode ser contornado)
```

⚠️ **Nota crítica:** Acessos feitos pelo servidor com SDK administrativo NÃO estão automaticamente protegidos apenas pelas regras do cliente. O isolamento DEVE existir também:
- No código backend (validação de tenant_id)
- Em queries (filter by tenant_id)
- Em testes (usar tenant_id correto)
- Em logs/auditoria (rastrear por tenant_id)

---

## 16. GLOSSÁRIO DE ESTADOS

Para evitar confusão entre estados similares:

| Estado | Significado | Ação do Lead | Acesso | Próximo Estado |
|--------|------------|---|---|---|
| **TRIAL_ATIVO** | Período de teste, sem cobrança | Usar e testar | Completo | CLIENTE_ATIVO (pagou) ou SUSPENSO (não pagou) |
| **PAGAMENTO_PROCESSANDO** | Hotmart validando cartão | Aguardar | Mantém | CLIENTE_ATIVO ou PAGAMENTO_FALHOU |
| **CLIENTE_ATIVO** | Assinatura válida, pagamento aprovado | Usar normalmente | Completo | ASSINATURA_MODIFICADA, ASSINATURA_CANCELADA, PAGAMENTO_FALHOU (se renovação falhar) |
| **ASSINATURA_MODIFICADA** | Lead mudou de plano durante ciclo | Usar novo plano | Novo plano | CLIENTE_ATIVO (próxima renovação) |
| **PAGAMENTO_FALHOU** | Cartão recusado, retry ativo | Tentar novo cartão | Mantém (3 dias) | CLIENTE_ATIVO (se pagou) ou INADIMPLENTE (se retry falhar) |
| **INADIMPLENTE** | Múltiplas falhas, sem pagamento válido | Fornecer cartão ou suporte | Bloqueado | CLIENTE_ATIVO (se reativar) ou DELETADO (se timeout) |
| **ASSINATURA_CANCELADA** | Lead solicitou cancelamento | Nada (esperar fim ciclo) | Até fim ciclo | SUSPENSO ou DELETADO |
| **SUSPENSO** | Falta de pagamento, fora de retry | Fornecer cartão | Read-only | CLIENTE_ATIVO (se reativar) ou DELETADO (se timeout) |
| **DELETADO** | Tenant permanentemente removido | Novo signup necessário | Nenhum | (Não há próximo) |

---

## 📋 CHECKLIST DE APROVAÇÃO

Este contrato requer aprovação de:

- [ ] **Hotmart:** Validação de fluxos webhook, integrações, taxa de rejeição esperada
- [ ] **Finance:** Aprovação de upgrade/downgrade (crédito vs sem reembolso), reembolso (7 dias)
- [ ] **Jurídico:** Conformidade com leis de consumidor, cobrança, reembolso
- [ ] **Engenharia:** Validação de implementação (idempotência, webhooks, reconciliação)
- [ ] **Produto:** Alinhamento com Catálogo Comercial V1.2 e Contrato Trial V1.2

---

## ✅ VALIDAÇÃO DE REQUISITOS

Cada item do contrato possui um status de confirmação. **Não se aguarda "aprovação" da Hotmart** — a plataforma não aprova arquiteturas de terceiros. Em vez disso, cada requisito é validado em seus respectivos níveis:

### Status de Confirmação de Requisitos

| Nível | Significado | Ação Necessária |
|-------|------------|---|
| **A** | Confirmado pela documentação oficial Hotmart | Implementar conforme documentado |
| **B** | Confirmado em ambiente Sandbox Hotmart | Testar antes de produção |
| **C** | Confirmado em Produção | Já validado com dados reais |
| **D** | Hipótese aguardando validação | Testar em Sandbox + Prod |

### Mapeamento de Requisitos

| Requisito | Descrição | Status |
|-----------|-----------|--------|
| Evento payment_approved | Webhook quando pagamento é aprovado | A (documentação oficial) |
| Evento payment_failed | Webhook quando pagamento é recusado | A |
| Evento subscription_renewed | Webhook quando renovação é cobrada | A |
| Evento subscription_canceled | Webhook quando assinatura é cancelada | A |
| Estrutura de payload webhook | Campos do JSON recebido | A |
| Autenticação de webhook | Mecanismo hottok (conforme docs) | A |
| Retry webhook automático | Hotmart retentar até 5x | D (confirmar limite exato) |
| Upgrade imediato | Mudar plano entra em vigor na hora | D (validar em Sandbox) |
| Downgrade próximo ciclo | Mudança entra em vigor na renovação | A (documentação) |
| Reembolso até N dias | Período configurável por oferta | B (testar em Sandbox) |
| Histórico de transações via API | Consultar últimas 24h/7d/30d | B (testar em Sandbox) |
| Chargebacks via webhook | Notificação de chargeback aberto/resolvido | B (testar em Sandbox) |
| Reconciliação via API | Consultar estado completo assinatura | B (testar em Sandbox) |
| Renovação automática | Hotmart cobra automaticamente no dia X | C (comportamento conhecido) |
| Cancelamento imediato | Lead pode cancelar a qualquer momento | C |
| Reativação de tenant | Reativar assinatura suspensa | D (fluxo em validação) |

### Requisitos Críticos (Status D)

Estes itens precisam ser validados antes de produção:

```
□ Upgrade imediato vs próximo ciclo
  └─ Validar: Hotmart cobra diferença imediato ou espera renovação?
  └─ Sandbox: criar upgrade, verificar cobrança
  └─ Produção: validar primeira cobrança real

□ Retry webhook (limite e intervalo)
  └─ Validar: limite exato (3x? 5x? 10x?)
  └─ Validar: intervalos (1m, 5m, 15m, 1h, 6h exato?)
  └─ Sandbox: deixar falhar, contar tentativas

□ Reativação de tenant suspenso
  └─ Validar: possível reativar durante janela 30d?
  └─ Validar: cobrar valores em atraso?
  └─ Sandbox: suspender → reativar, verificar comportamento

□ Chargeback e disputa
  └─ Validar: webhooks informam transições?
  └─ Validar: possível ganhar/perder disputa?
  └─ Sandbox: não há chargebacks simulados? Produção apenas.
```

---

## ✅ PRÓXIMAS AÇÕES

**1. Validação de Requisitos (Status D)**
   - Consultar documentação oficial Hotmart
   - Criar ambiente Sandbox
   - Executar VALIDACAO_HOTMART.md (checklist completo)
   - Documentar resultados com Status B/C

**2. Integração com Trial**
   - Após Status A/B confirmados: integrar com CONTRATO_TRIAL_NEOEVE.md
   - Validar fluxo completo: trial → pagamento → assinatura

**3. Contrato de Conversão**
   - Após Billing V1.1 e Trial V1.2 validados
   - Criar CONTRATO_CONVERSAO_LEAD_TENANT.md

---

**Contrato de Billing:** 2026-07-27  
**Versão:** 1.1  
**Status:** Rascunho Operacional Completo — Requisitos Classificados  
**Próximas Ações:** Executar VALIDACAO_HOTMART.md para confirmar Status D

