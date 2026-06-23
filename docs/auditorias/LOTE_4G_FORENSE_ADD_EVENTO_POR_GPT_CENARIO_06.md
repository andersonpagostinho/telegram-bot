# LOTE 4G — FORENSE add_evento_por_gpt NO CENÁRIO 06

**Data:** 2026-06-22  
**Escopo:** Investigação de por que add_evento_por_gpt não cria evento após confirmação  
**Objetivo:** Identificar causa raiz sem aplicar patch funcional

---

## FLUXO RASTREADO

### Etapa 1: executar_acao_gpt_resultado

**Chamada com:**
```
acao="criar_evento"
confirmado=True
dados={
  "profissional": "Bruna",
  "servico": "corte",
  "data_hora": "amanhã 14:00",
  "duracao": 30,
  "descricao": "Corte com Bruna",
  "confirmado": True,
  "status": "confirmado"
}
```

**Status:** ✅ Wrapper normalizou corretamente
- Recebeu bool
- Retornou dict

---

### Etapa 2: executar_acao_gpt

**Chamada:** linha 637 de gpt_executor.py

**Payload para add_evento_por_gpt:**
```json
{
  "profissional": "Bruna",
  "servico": "corte",
  "data_hora": "amanhã 14:00",
  "duracao": 30,
  "descricao": "Corte com Bruna",
  "confirmado": True,
  "status": "confirmado"
}
```

**Status:** ✅ Payload completo e correto

---

### Etapa 3: add_evento_por_gpt

**Chamada:** linha 637 de gpt_executor.py

**Entrada (dados):**
```
profissional: "Bruna"
servico: "corte"
data_hora: "amanhã 14:00"
duracao: 30
descricao: "Corte com Bruna"
confirmado: True
status: "confirmado"
```

**Início da função:** ✅ OK

**Verificação 1 - verificar_pagamento():**

```
user_id: "whatsapp:55119999006"
cliente_encontrado: False
pagamentoAtivo: N/A
```

❌ **FALHA AQUI**

```python
if not await verificar_pagamento(update, context):
    # Esta linha retorna False
    return False
```

**Razão:** Cliente não existe em banco de dados

**Evidência:** Log forense
```
[FORENSE] VERIFICAR_PAGAMENTO: user_id=whatsapp:55119999006, cliente_encontrado=False, pagamentoAtivo=N/A
[FORENSE] RETORNO EARLY: falha verificar_pagamento
```

---

## TABELA DE CAMPOS

| Campo | Valor | Tipo | Obrigatório? | Origem | Status |
|-------|-------|------|--------------|--------|--------|
| profissional | "Bruna" | str | ✅ SIM | executar_acao_gpt | ✅ PRESENTE |
| servico | "corte" | str | ✅ SIM | executar_acao_gpt | ✅ PRESENTE |
| data_hora | "amanhã 14:00" | str | ✅ SIM | executar_acao_gpt | ✅ PRESENTE |
| duracao | 30 | int | ✅ SIM | executar_acao_gpt | ✅ PRESENTE |
| descricao | "Corte com Bruna" | str | ✅ SIM | executar_acao_gpt | ✅ PRESENTE |
| confirmado | True | bool | ✅ SIM | executar_acao_gpt | ✅ PRESENTE |
| status | "confirmado" | str | ⚠️ EXTRA | executar_acao_gpt | ✅ PRESENTE |

---

## TABELA DE ETAPAS

| Etapa | Chamada? | Retorno | Observação |
|-------|----------|---------|------------|
| add_evento_por_gpt | ✅ SIM | N/A | Iniciado |
| verificar_pagamento | ✅ SIM | False | ❌ **BLOQUEANTE** |
| verificar_acesso_modulo | ❌ NÃO | N/A | Não chegou |
| salvar_evento | ❌ NÃO | N/A | Não chegou |
| salvar_contexto | ❌ NÃO | N/A | Não chegou |

---

## DESCOBERTA CRÍTICA

**Problema:** Cliente não está cadastrado no cenário 06

**Localização:** `add_evento_por_gpt` linha ~524-525

```python
if not await verificar_pagamento(update, context):
    return False  # ← Cliente não existe
```

**Causa Raiz:** Teste não cria cliente com `pagamentoAtivo=True` no cenário 06

**Impacto:** 
- Função retorna False (linha 524)
- Nenhum evento é criado
- Nenhum erro ao usuário (apenas retorna)
- Test vê `evento_criado=False`

**Código responsável:**
```python
async def verificar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)  # ← Retorna None

    if not cliente:  # ← Verdadeiro
        await update.message.reply_text("⚠️ Não encontramos seu cadastro. Use /start para começar.")
        return False  # ← Retorna False
```

---

## CLASSIFICAÇÃO FINAL

**Opção:** **A) PAYLOAD INCOMPLETO (NO TEST, NÃO NO HANDLER)**

Análise:
- ❌ A) Payload incompleto → NÃO (todos campos presentes)
- ❌ B) Campos em nomes errados → NÃO (nomes corretos)
- ❌ C) Tenant/dono_id inconsistente → NÃO (não chega lá)
- ❌ D) add_evento exige formato antigo → NÃO (não chega lá)
- ❌ E) Agenda/lock bloqueia → NÃO (não chega lá)
- ✅ **F) TESTE ESPERA EVENTO EM PATH ERRADO**

Realidade:
- Evento NÃO é criado
- Razão: Cliente não existe no banco
- Localizaçã: add_evento_por_gpt:524 (verificar_pagamento)
- **Escopo:** FORA DO LOTE 4G (é problema de setup do test, não de lógica de evento)

---

## RAIZ CAUSA - ESTRUTURA

```
Cenário 06 Setup:
├─ ✅ Cria tenant
├─ ✅ Cria MockUpdate
├─ ✅ Cria contexto de confirmação
├─ ❌ NÃO cria cliente com pagamentoAtivo=True
│  └─ buscar_cliente(user_id) retorna None
│
add_evento_por_gpt:524:
├─ Chama verificar_pagamento()
├─ verificar_pagamento() chama buscar_cliente()
├─ Resultado: None (cliente não existe)
│
Fluxo:
├─ verificar_pagamento() retorna False
├─ add_evento_por_gpt() retorna False
└─ Evento nunca é criado
```

---

## PATCH RECOMENDADO

**Escopo:** test/p1_robustez_fluxo_conversacional_real.py (NÃO toca em lógica de evento)

**Problema:** Cenário 06 não cria cliente antes de confirmar evento

**Solução Mínima:** Criar cliente com pagamento ativo no setup de cenário 06

**Local:** Antes de chamar roteador_principal em cenário 06

**Mudança:**
```python
# Criar cliente com pagamento ativo (ANTES de chamar router)
await salvar_cliente(actor_id, {
    "nome": "Cliente Teste",
    "pagamentoAtivo": True,  # ← CRÍTICO
    "planosAtivos": ["secretaria"],
    "canal": "whatsapp"
})
```

---

## VALIDAÇÃO

| Aspecto | Status | Evidência |
|---------|--------|-----------|
| Payload em executar_acao_gpt | ✅ OK | 7 campos presentes |
| Payload em add_evento_por_gpt | ✅ OK | Mesmo 7 campos |
| Campos obrigatórios | ✅ OK | profissional, servico, data_hora, duracao |
| tenant_id/dono_id | ⏭️ N/A | Não chega lá (falha antes) |
| add_evento chamado | ✅ SIM | Log mostra início |
| verificar_pagamento | ❌ FALHA | Cliente não existe |
| salvar_evento | ❌ N/A | Não chega |
| Evento criado | ❌ NÃO | Cliente bloqueou |

---

## CONCLUSÃO

**Descoberta:** add_evento_por_gpt NÃO está quebrado. A função retorna False porque o test não criou um cliente com `pagamentoAtivo=True`.

**Etapa bloqueante:** `verificar_pagamento()` em linha 524 de event_handler.py

**Tipo de problema:** Setup insuficiente no test, não lógica de evento

**Patch mínimo:** Adicionar criação de cliente no cenário 06 (ANTES de chamar router)

**Impacto:** 
- ✅ Cenário 06: evento será criado
- ✅ Cenário 07: sem impacto (negação não chama add_evento)
- ✅ P0 baseline: sem impacto (clientes existem)

---

## RECOMENDAÇÃO FINAL

**LOTE 4H — PATCH MÍNIMO:**

**Arquivo:** tests/p1_robustez_fluxo_conversacional_real.py

**Onde:** Cenário 06, antes de chamar roteador_principal (linha ~670)

**O que:** Criar cliente com pagamento ativo

**Linha aproximada:** 670 (antes de roteador_principal)

**Patch:**
```python
# Salvar cliente com pagamento ativo (necessário para add_evento_por_gpt)
await salvar_cliente(actor_id, {
    "nome": "Cliente Teste",
    "pagamentoAtivo": True,
    "planosAtivos": ["secretaria"],
    "canal": "whatsapp"
})
```

---

**Status:** FORENSE COMPLETA — CAUSA RAIZ IDENTIFICADA

Próxima etapa: LOTE 4H (aplicar patch mínimo de cliente no cenário 06)

