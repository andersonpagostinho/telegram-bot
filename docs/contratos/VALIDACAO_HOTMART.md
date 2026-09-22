# VALIDACAO_HOTMART.md — Checklist de Integração

**Versão:** 1.0  
**Status:** Modelo de Teste  
**Data de Criação:** 2026-07-27  
**Propósito:** Checklist operacional para validação de cada funcionalidade Hotmart em Sandbox e Produção  

---

## 📋 Instruções de Uso

Para cada teste abaixo:

1. **Status** — Marcar com:
   - ☐ = Não testado
   - ⏳ = Em progresso
   - ✅ = PASS (comportamento esperado)
   - ❌ = FAIL (comportamento inesperado)

2. **Data/Hora** — Quando foi executado

3. **Observações** — Qualquer detalhe relevante
   - Payload recebido (se webhook)
   - Erro observado (se falhou)
   - Comportamento diferente do esperado

4. **Logs** — Referências
   - ID da transação Hotmart
   - ID do webhook (event_id)
   - Logs da aplicação
   - Screenshots (se relevante)

5. **Conclusão** — Anotar:
   - Se o requisito é confirmado
   - Se há desvio da expectativa
   - Próximas ações

---

## 🧪 TESTES — SANDBOX

Executar cada teste em ambiente Sandbox Hotmart. Documentar resultado.

### Teste 1: Criar Produto Sandbox

**Objetivo:** Validar que produto pode ser criado no Hotmart

**Passos:**
1. Logar no Hotmart (sandbox)
2. Criar novo produto "NeoEve Test"
3. Configurar preço R$ 87/mês
4. Salvar

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Comportamento esperado:
  └─ Produto criado com ID gerado

Comportamento observado:
  └─ _______________
```

**Logs:** _______________

**Conclusão:**

```
Requisito Confirmado? [ ]
Desvios? _______________
Próximas ações: _______________
```

---

### Teste 2: Criar Assinatura Teste

**Objetivo:** Validar fluxo de compra e criação de assinatura

**Passos:**
1. Ir para checkout do produto
2. Usar cartão de teste (Hotmart fornece)
3. Completar compra
4. Verificar: assinatura foi criada no painel

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Payload esperado no webhook payment_approved:
  ├─ product_id
  ├─ customer_name
  ├─ customer_email
  ├─ purchase_id
  ├─ purchase.transaction
  └─ subscription.id

Payload recebido:
  └─ _______________
```

**Logs:**

```
Webhook event_id: _______________
Transação Hotmart: _______________
Aplicação: _______________
```

**Conclusão:**

```
Assinatura criada? [ ]
Webhook recebido? [ ]
Payload contém todos campos esperados? [ ]
Desvios? _______________
```

---

### Teste 3: Webhook payment_approved

**Objetivo:** Validar que NeoEve recebe webhook quando pagamento é aprovado

**Passos:**
1. Completar compra (Teste 2)
2. Verificar: NeoEve recebeu webhook
3. Validar: payload está completo

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Tempo entre pagamento e webhook:
  └─ ___ segundos

Autenticação do webhook:
  ├─ Método: hotmkt credential? HMAC? Outro?
  └─ Validado com sucesso? [ ]

Conteúdo do payload:
  └─ _______________
```

**Logs:**

```
Webhook recebido em: _______________
Event ID Hotmart: _______________
Transação ID: _______________
```

**Conclusão:**

```
Webhook entregue? [ ]
Autenticação funcionou? [ ]
Payload válido? [ ]
Status de confirmação: A (documentação) / B (Sandbox confirmado)
```

---

### Teste 4: Cancelar Assinatura

**Objetivo:** Validar cancelamento e webhook correspondente

**Passos:**
1. Acessar assinatura criada (Teste 2)
2. Clicar "Cancelar"
3. Verificar: Hotmart mostra status "Cancelada"
4. Verificar: NeoEve recebe webhook subscription_canceled

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Cancelamento é imediato ou próximo ciclo?
  └─ _______________

Acesso ao produto permanece até fim ciclo?
  └─ [ ] Sim [ ] Não

Webhook recebido?
  └─ [ ] Sim [ ] Não (evento_id: ___)
```

**Logs:**

```
Webhook event_id: _______________
Tempo após clicar cancelar: ___ segundos
```

**Conclusão:**

```
Cancelamento funcionou? [ ]
Webhook entregue? [ ]
Timing (imediato vs próximo ciclo)? _______________
Status de confirmação: A / B / D
```

---

### Teste 5: Solicitar Reembolso

**Objetivo:** Validar período de reembolso e processamento

**Passos:**
1. Criar nova assinatura (usar novo email)
2. Imediatamente solicitar reembolso (< 1 dia)
3. Verificar: Hotmart permite reembolso

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Reembolso aprovado em:
  └─ ___ horas após compra

Período máximo de elegibilidade:
  └─ ___ dias

Webhook recebido?
  └─ evento: purchase_refunded ou purchase_returned?
  └─ event_id: _______________
```

**Logs:**

```
Transação Hotmart: _______________
Webhook recebido em: _______________
Payload: _______________
```

**Conclusão:**

```
Reembolso processado? [ ]
Webhook informado? [ ]
Período de elegibilidade: ___ dias
Status de confirmação: B (Sandbox confirmado)
```

---

### Teste 6: Simular Chargeback

**Objetivo:** Validar se Hotmart simula chargebacks em Sandbox

**Nota:** Sandbox pode não suportar chargebacks simulados. Se não houver opção, marcar como "SANDBOX_NAO_SUPORTA" e validar em Produção.

**Passos:**
1. Procurar em Hotmart: opção de simular chargeback
2. Se houver: usar transação de teste
3. Verificar: webhook é recebido

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Sandbox suporta simulação de chargeback?
  └─ [ ] Sim [ ] Não (esperar produção)

Se sim:
  ├─ Evento recebido: _______________
  ├─ Payload: _______________
  └─ Time entre simulação e webhook: ___ segundos
```

**Logs:**

```
Event ID: _______________
Webhook: _______________
```

**Conclusão:**

```
Recurso disponível em Sandbox? [ ]
Se não: validar em Produção apenas.
Status de confirmação: B (se Sandbox) / C (produção)
```

---

### Teste 7: Trocar Plano (Upgrade)

**Objetivo:** Validar upgrade de plano e cobrança

**Passos:**
1. Ter assinatura em SOLO87 (R$ 87/mês)
2. Acessar mudança de plano
3. Escolher STUDIO157 (R$ 157/mês)
4. Verificar: cobrança acontece

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Upgrade entra em vigor:
  ├─ [ ] Imediato (cobra diferença agora)
  └─ [ ] Próximo ciclo (cobra valor completo)

Diferença cobrada:
  └─ R$ _____ (esperado: ~R$ 70 proporcional?)
  └─ Quando? _______________

Webhook recebido?
  └─ Tipo: _______________
  └─ Event ID: _______________
```

**Logs:**

```
Nova cobrança em: _______________
Valor: R$ _____
Webhook timestamp: _______________
```

**Conclusão:**

```
Upgrade funcionou? [ ]
Cobrança foi feita? [ ]
Valor esperado? [ ]
Timing (imediato vs próximo ciclo): _______________
Status de confirmação: D (aguardando validação)
```

---

### Teste 8: Trocar Plano (Downgrade)

**Objetivo:** Validar downgrade e sem-reembolso

**Passos:**
1. Ter assinatura em STUDIO157 (R$ 157/mês, 15 dias de ciclo restante)
2. Fazer downgrade para SOLO87 (R$ 87/mês)
3. Verificar: sem reembolso (entra em vigor próximo ciclo)

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Downgrade entra em vigor:
  ├─ [ ] Imediato
  └─ [ ] Próximo ciclo

Reembolso:
  ├─ [ ] Sim (inesperado)
  └─ [ ] Não (esperado)

Próxima cobrança:
  └─ Valor: R$ 87 (esperado)
  └─ Data: _______________
```

**Logs:**

```
Webhook recebido? [ ]
Event ID: _______________
Transação: _______________
```

**Conclusão:**

```
Downgrade processado? [ ]
Sem reembolso? [ ] (esperado)
Próxima cobrança correta? [ ]
Status de confirmação: A (documentação diz próximo ciclo, sem reembolso)
```

---

### Teste 9: Receber Webhook

**Objetivo:** Validar que NeoEve consegue receber webhook em Sandbox

**Passos:**
1. Configurar webhook URL em Hotmart Sandbox
   - URL: https://neoeve-staging.com/webhooks/hotmart
   - Autenticação: hotmkt credential
2. Completar compra
3. Verificar: webhook é recebido

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Webhook URL configurada:
  └─ https://_______________

Autenticação configurada:
  ├─ Método: _______________
  └─ Credencial: _______________ (ocultar em logs!)

Webhook recebido?
  └─ [ ] Sim [ ] Não (debugar)

Latência:
  └─ ___ segundos entre ação e recebimento
```

**Logs:**

```
NeoEve log: _______________
Hotmart webhook log: _______________
Erro (se houver): _______________
```

**Conclusão:**

```
URL alcançável? [ ]
Autenticação funcionou? [ ]
Payload desserializado? [ ]
Latência aceitável? [ ]
Status de confirmação: B (Sandbox confirmado)
```

---

### Teste 10: Duplicar Webhook

**Objetivo:** Validar idempotência (webhook duplicado não causa erro)

**Passos:**
1. Interceptar webhook recebido (usar event_id)
2. Simular reentrega (fazer NeoEve receber 2x)
3. Verificar: idempotência funciona

**Método:**
- Pausar processamento do 1º webhook
- Hotmart reenvia (retry automático)
- Verificar: NeoEve não processa 2x

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Event ID do webhook: _______________
Primeira entrega: _____ 
Segunda entrega: _____ (duração entre)

Resultado:
  ├─ Processado 1x? [ ]
  ├─ Processado 2x? [ ] (problema!)
  └─ Rejeitado 2º? [ ] (esperado)
```

**Logs:**

```
Primeiro processamento: _______________
Segundo webhook: _______________
Provider_event_id armazenado? [ ]
```

**Conclusão:**

```
Idempotência funcionou? [ ]
Nenhuma duplicação? [ ]
Status de confirmação: B (Sandbox)
```

---

### Teste 11: Webhook Fora de Ordem

**Objetivo:** Validar que eventos fora de ordem não quebram o sistema

**Passos:**
1. Criar assinatura → recebe purchase_approved
2. Depois: simular reembolso → recebe purchase_refunded
3. Se possível: entrega refund antes de approved
4. Verificar: sistema não quebra

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Ordem esperada:
  1. payment_approved
  2. subscription_created
  3. purchase_refunded

Ordem recebida:
  1. _______________
  2. _______________
  3. _______________

Sistema quebrou? [ ]
Reconciliação detectou? [ ]
```

**Logs:** _______________

**Conclusão:**

```
Sistema é resiliente a out-of-order? [ ]
Reconciliação corrige? [ ]
Status de confirmação: D (validar em produção)
```

---

### Teste 12: Timeout

**Objetivo:** Validar que sistema aguarda retries mesmo com timeout

**Passos:**
1. Configurar NeoEve para não responder (simular timeout)
2. Hotmart tenta enviar webhook
3. Verificar: Hotmart retentar automaticamente

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Timeout configurado: ___ segundos

Retry automático:
  ├─ Tentativa 1: _______________
  ├─ Tentativa 2: _______________
  ├─ Tentativa 3: _______________
  └─ Total de tentativas: ___

Intervalos entre retries:
  ├─ 1→2: ___ segundos
  └─ 2→3: ___ segundos
```

**Logs:**

```
Hotmart logs: _______________
NeoEve finalmente recebeu? [ ]
```

**Conclusão:**

```
Retry automático funcionou? [ ]
Número de tentativas: ___
Intervalos exatos: _______________
Status de confirmação: D (confirmar exato em Sandbox)
```

---

### Teste 13: API Indisponível

**Objetivo:** Validar comportamento se API Hotmart fica offline

**Passos:**
1. Tentar reconciliação (chamar API Hotmart)
2. Simular falta de conectividade
3. Verificar: erro é capturado (não quebrá sistema)

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Erro esperado:
  └─ Connection timeout / 503 Service Unavailable / outro?

Comportamento:
  ├─ Log do erro? [ ]
  ├─ Retry agendado? [ ]
  ├─ Sistema continua operacional? [ ]
  └─ Lead consegue usar? [ ]
```

**Logs:** _______________

**Conclusão:**

```
Falha é tratada gracefully? [ ]
Retry é agendado? [ ]
Impacto no usuário? _______________
Status de confirmação: B (Sandbox)
```

---

### Teste 14: Reconciliação Manual

**Objetivo:** Validar que reconciliação via API funciona

**Passos:**
1. Criar assinatura (Teste 2)
2. Chamar API Hotmart manualmente
3. Consultar estado daquela assinatura
4. Verificar: API retorna dados esperados

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Endpoint usado:
  └─ https://api.hotmart.com/...

Parâmetros:
  ├─ Período: últimas 24h
  ├─ Subscription ID: _______________
  └─ Status: _______________

Resposta esperada:
  ├─ Assinatura encontrada? [ ]
  ├─ Status é ATIVA? [ ]
  ├─ Próxima renovação em? _______________
  └─ Payload completo? [ ]
```

**Logs:**

```
Request: _______________
Response: _______________
Tempo de resposta: ___ ms
```

**Conclusão:**

```
API funcionou? [ ]
Dados são precisos? [ ]
Status de confirmação: B (Sandbox confirmado)
```

---

### Teste 15: Renovação Automática

**Objetivo:** Validar renovação automática no dia da renovação

**Nota:** Este teste pode levar dias. Pode ser feito em Sandbox com clock acelerado, ou em Produção com assinatura real.

**Passos:**
1. Ter assinatura perto de vencer (usar clock acelerado se Sandbox suporta)
2. Aguardar dia de renovação
3. Verificar: Hotmart cobra automaticamente
4. Verificar: webhook é recebido

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Data da renovação esperada: _______________
Renovação aconteceu em: _______________
Atraso: ___ horas

Cobrança:
  ├─ Valor: R$ _______________
  ├─ Cartão foi cobrado? [ ]
  └─ Webhook recebido? [ ] (evento: ___)

Próxima renovação agendada para: _______________
```

**Logs:**

```
Hotmart: _______________
Webhook event_id: _______________
NeoEve log: _______________
```

**Conclusão:**

```
Renovação automática funcionou? [ ]
Webhook informou? [ ]
Próxima renovação agendada? [ ]
Status de confirmação: C (Produção validado)
```

---

### Teste 16: Falha de Renovação

**Objetivo:** Validar comportamento quando renovação falha (cartão recusado)

**Passos:**
1. Ter assinatura com cartão inválido
2. Aguardar dia de renovação
3. Verificar: Hotmart tenta cobrar, falha
4. Verificar: webhook payment_failed é recebido
5. Verificar: retry automático acontece

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Falha de cobrança:
  ├─ Data/Hora: _______________
  ├─ Motivo: _______________
  └─ Webhook recebido? [ ] (event_id: ___)

Retry automático:
  ├─ 1ª tentativa: _______________
  ├─ 2ª tentativa: _______________
  └─ Quantas tentativas total? ___

Intervalo entre retries: _______________

Assinatura suspende? [ ]
Quando? _______________
```

**Logs:**

```
Hotmart: _______________
Webhooks: _______________
NeoEve: _______________
```

**Conclusão:**

```
Falha foi reportada? [ ]
Retry automático funcionou? [ ]
Lead consegue atualizar cartão? [ ]
Assinatura foi suspensa corretamente? [ ]
Status de confirmação: D (validar em produção)
```

---

### Teste 17: Expiração de Assinatura

**Objetivo:** Validar que assinatura suspende após falhas exauridas

**Passos:**
1. Simular falha de renovação (Teste 16)
2. Aguardar exaurimento de retries (~14 dias)
3. Verificar: Hotmart suspende assinatura
4. Verificar: webhook subscription_expired ou similar

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Evento de expiração:
  ├─ Tipo: _______________
  ├─ Event ID: _______________
  └─ Recebido por NeoEve? [ ]

Status da assinatura:
  ├─ Antes: ATIVA
  ├─ Depois: SUSPENSA / EXPIRADA / outro?
  └─ Acesso do cliente: _______________

Período até expiração: ___ dias
```

**Logs:**

```
Hotmart: _______________
Webhook: _______________
NeoEve: _______________
```

**Conclusão:**

```
Expiração foi processada? [ ]
Webhook informou? [ ]
Acesso foi bloqueado? [ ]
Status de confirmação: D (validar em produção)
```

---

### Teste 18: Reativação

**Objetivo:** Validar reativação de assinatura suspensa

**Passos:**
1. Ter assinatura suspensa (Teste 17)
2. Lead fornece cartão novo/válido
3. Hotmart processa pagamento (valores em atraso)
4. Verificar: assinatura é reativada

**Status:** ☐

**Data/Hora:** _______________

**Observações:**

```
Valor em atraso: R$ _______________
Novo cartão aceito? [ ]

Cobrança:
  ├─ Valor total (atraso + novo período): R$ _______________
  ├─ Cobrado com sucesso? [ ]
  └─ Webhook recebido? [ ] (event_id: ___)

Status da assinatura:
  └─ Antes: SUSPENSA
  └─ Depois: ATIVA?

Acesso restaurado? [ ]
```

**Logs:**

```
Pagamento: _______________
Webhook: _______________
NeoEve: _______________
```

**Conclusão:**

```
Reativação funcionou? [ ]
Acesso foi restaurado? [ ]
Cobrança foi feita? [ ]
Status de confirmação: D (validar em produção)
```

---

## 🧪 TESTES — PRODUÇÃO

**Nota:** Após Sandbox estar completo, repetir testes críticos em Produção com dados reais.

| Teste | Sandbox | Produção | Resultado Final |
|-------|---------|----------|-----------------|
| 1. Criar Produto | ✅ | ☐ | ☐ |
| 2. Assinatura Teste | ✅ | ☐ | ☐ |
| 3. Webhook payment_approved | ✅ | ☐ | ☐ |
| 5. Reembolso | ✅ | ☐ | ☐ |
| 7. Upgrade | ⏳ | ☐ | ☐ |
| 14. Reconciliação API | ✅ | ☐ | ☐ |
| 15. Renovação | ⏳ | ☐ | ☐ |
| 16. Falha Renovação | ⏳ | ☐ | ☐ |

---

## 📊 RESUMO

**Data de Conclusão Esperada:** _______________

**Requisitos Confirmados (Status A/B/C):**
```
☐ Evento payment_approved
☐ Evento payment_failed
☐ Webhook redelivery automático
☐ Upgrade imediato
☐ Downgrade próximo ciclo
☐ Reconciliação API
☐ Chargeback
```

**Requisitos Aguardando Validação (Status D):**
```
☐ Retry webhook (limite exato)
☐ Upgrade cobrar diferença imediato?
☐ Chargeback em Sandbox
☐ Reativação fluxo
☐ Out-of-order handling
```

**Bloqueadores Encontrados:**
```
_______________
```

**Próximas Ações:**
```
1. _______________
2. _______________
3. _______________
```

---

**VALIDACAO_HOTMART.md** — Checklist de Testes  
**Status:** Template para execução  
**Última Atualização:** 2026-07-27

