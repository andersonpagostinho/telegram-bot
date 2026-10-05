# 🚨 SUMÁRIO — Bloqueador de Identidade em pre_confirmar_agendamento

**Data:** 2026-10-03  
**Status:** ⛔ BLOQUEADOR IDENTIFICADO (diagnóstico, NÃO corrigir ainda)  
**Impacto:** Resposta WhatsApp vazia, log "[P0.2] ERRO: Nem identidade nem update fornecidos"  
**Severidade:** P0 (resposta não chega ao usuário)

---

## 🎯 O Problema (Observado)

**Cenário:** Usuário envia "quero corte amanhã as 9"

**Fluxo esperado:**
```
1. WhatsApp recebe → parser → slots
2. P0 valida horário → pre_confirmar_agendamento
3. Resposta enviada: "Confirmando corte com Bruna amanhã às 09:00?"
```

**Fluxo observado:**
```
1. WhatsApp recebe → parser → slots ✅
2. P0 valida horário → pre_confirmar_agendamento ✅
3. [P0.2] ERRO: Nem identidade nem update fornecidos ❌
4. Resposta: (vazia) ❌
```

---

## 🔍 Causa Raiz Identificada

**Arquivo:** `router/principal_router.py`

**Múltiplos callsites de `executar_acao_gpt()` com `"pre_confirmar_agendamento"`**

### Callsite 1: Linha 10899-10909 ✅ CORRETO

```python
return await executar_acao_gpt(
    update,
    context,
    "pre_confirmar_agendamento",
    {...dados...},
    identidade=identidade_p01  # ✅ PASSA
)
```

**Status:** Funciona (identidade_p01 está disponível no escopo)

### Callsite 2: Linha 7591-7600 ❌ FALTA

```python
return await executar_acao_gpt(
    update,
    context,
    "pre_confirmar_agendamento",
    {...dados...}
    # ❌ NÃO PASSA identidade
)
```

**Status:** Quebrado (identidade_p01 não está sendo passado)

### Callsite 3: Linha 11396-11405 ❌ FALTA

```python
return await executar_acao_gpt(
    update,
    context,
    "pre_confirmar_agendamento",
    {...dados...}
    # ❌ NÃO PASSA identidade
)
```

**Status:** Quebrado (identidade_p01 não está sendo passado)

---

## 📊 Análise de Disponibilidade

**Onde identidade_p01 é criada:**
- `router/principal_router.py:3466-3478`
- Função: `processar_pre_checagem_p0()`
- Criação: `criar_identidade_telegram(telegram_id=user_id, canal_tenant_id=dono_id)`

**Todos os callsites (7591, 10899, 11396) estão na mesma função.**

**Conclusão:** `identidade_p01` DEVERIA estar disponível em todos os callsites.

---

## ⚠️ Por Que a Resposta fica Vazia

**Fluxo do erro em executar_acao_gpt():**

```python
async def executar_acao_gpt(..., identidade=None):
    
    if acao == "pre_confirmar_agendamento":
        # Tenta responder via WhatsApp
        
        if not identidade or not update:
            print("[P0.2] ERRO: Nem identidade nem update fornecidos")
            # ❌ NÃO consegue extrair phone_number_id
            # ❌ NÃO consegue chamar bot.send_message()
            # ❌ Resposta fica vazia
            return
        
        # Se chegasse aqui (mas não chega):
        # response = await enviar_resposta_whatsapp(...)
```

**Quando identidade=None:**
- Função não consegue extrair `phone_number_id` de `identidade`
- Não consegue chamar `bot.send_message(phone_number_id, mensagem)`
- Log: "[P0.2] ERRO: Nem identidade nem update fornecidos"
- Usuário vê: (nada)

---

## 📋 Callsites Mapeados

| Linha | Contexto | Status | Identidade Disponível? |
|-------|----------|--------|------------------------|
| 7591 | Escolha horário | ❌ FALTA | ✅ Sim (identidade_p01 em escopo) |
| 10899 | Validação P0 | ✅ OK | ✅ Sim (sendo passado) |
| 11396 | Outro fluxo | ❌ FALTA | ✅ Sim (identidade_p01 em escopo) |

---

## 🔧 Solução (Quando Autorizado)

**Padrão a Seguir (baseado em 10899):**

Para CADA callsite que não passa identidade, adicionar:

```python
return await executar_acao_gpt(
    update,
    context,
    "pre_confirmar_agendamento",
    {...dados...},
    identidade=identidade_p01  # ← ADICIONAR ISTO
)
```

**Mudanças necessárias:**
- Linha 7600: adicionar `, identidade=identidade_p01`
- Linha 11405: adicionar `, identidade=identidade_p01`
- Outros callsites: verificar e aplicar mesmo padrão

---

## 📍 Relatório Detalhado

**Arquivo:** `AUDITORIA_CALLSITES_PRE_CONFIRMAR_2026_10_03.md`

Contém:
- Localização exata de todos os callsites
- Código antes/depois
- Análise de disponibilidade de identidade em cada contexto
- Padrão correto identificado

---

## ⛔ NÃO FAZER AINDA

- ❌ Não alterar nenhum callsite
- ❌ Não fazer commit
- ❌ Não fazer push
- ❌ Não adivinhar variável de identidade

**Razão:** Precisa de autorização e análise cuidadosa de cada contexto.

---

## ✅ Estado Geral P0

| Componente | Status |
|------------|--------|
| **Parser "amanhã" → 04/10** | ✅ Correto |
| **P0 agenda (domingo fechado)** | ✅ Correto |
| **Filtro eventos** | ✅ Implementado (5/5 tests PASS, commitado) |
| **Chamada pre_confirmar** | ❌ Bloqueador: identidade não propagada |
| **Resposta WhatsApp** | ❌ Vazia (consequência do bloqueador acima) |

---

## 📊 Próximos Passos Recomendados

1. **Verificar relatório completo** → AUDITORIA_CALLSITES_PRE_CONFIRMAR_2026_10_03.md
2. **Confirmar padrão** → Qual variable de identidade deve ser usada em cada contexto
3. **Quando autorizado** → Alterar linhas 7600, 11405 (e outros se existirem)
4. **Testar** → Verificar que resposta WhatsApp volta
5. **Commit** → Se validado

---

**Bloqueador P0 mapeado. Aguardando autorização para corrigir.**

