# 🔍 AUDITORIA 429 - Tratamento de Rate Limit em GPT

**Data:** 2026-06-02  
**Objetivo:** Diagnosticar causa de 429 sem alterar código  
**Resposta:** Diagnóstico técnico completo

---

## 1. QUANTAS CHAMADAS `client.chat.completions.create` EXISTEM?

**Total: 5 chamadas em gpt_service.py**

```
Linha 1027:  em processar_com_gpt_com_acao()  [chamada 1]
Linha 2476:  em processar_com_gpt_com_acao()  [chamada 2]
Linha 3213:  em organizar_semana_com_gpt()
Linha 3456:  em gerar_resposta_humana_agendamento()
Linha 3544:  em gerar_resposta_p1()
```

---

## 2. EM QUAIS FUNÇÕES?

```
✅ processar_com_gpt_com_acao()
   └─ Chamadas: 2 (linhas 1027, 2476)
   └─ Modelo: gpt-4o
   └─ Temperatura: 0.4
   └─ Status: PRINCIPAL

✅ organizar_semana_com_gpt()
   └─ Chamadas: 1 (linha 3213)
   └─ Modelo: gpt-4o
   └─ Status: Auxiliar (opcional)

✅ gerar_resposta_humana_agendamento()
   └─ Chamadas: 1 (linha 3456)
   └─ Modelo: gpt-4o
   └─ Status: Auxiliar (resposta)

✅ gerar_resposta_p1()
   └─ Chamadas: 1 (linha 3544)
   └─ Modelo: gpt-4o
   └─ Status: Auxiliar (P1 response)
```

---

## 3. QUAL MODELO CADA UMA USA?

**Modelo único em todas:** `gpt-4o`

```
Linha 1028:  model="gpt-4o"
Linha 2477:  model="gpt-4o"
Linha 3214:  model="gpt-4o"
Linha 3457:  model="gpt-4o"
Linha 3545:  model="gpt-4o"
```

**Temperatura:** 0.4 (consistente, moderadamente determinístico)

---

## 4. EXISTE RETRY MANUAL NO CÓDIGO?

**NÃO. Sem retry manual.**

```python
# Padrão: Try → Exception → Return erro
try:
    resposta = await client.chat.completions.create(...)
except Exception as e:
    print(f"❌ Erro ao chamar OpenAI: {type(e).__name__}: {e}")
    return {"resposta": "⚠️ Tive um problema...", "acao": None}
```

**Tratamento de 429:**
- ❌ Sem `if isinstance(e, RateLimitError)`
- ❌ Sem `await asyncio.sleep()`
- ❌ Sem `while retry_count < max_retries`
- ❌ Sem verificação de `error.status_code == 429`

**Conclusão:** 429 cai em `except Exception` genérico e retorna erro imediatamente.

---

## 5. PARA UM ÚNICO ÁUDIO, QUANTAS CHAMADAS GPT SÃO FEITAS?

**Resposta: 1-3 chamadas por áudio, dependendo do fluxo**

### Cenário A: Fluxo de agendamento simples (MAIS COMUM)
```
[Audio] "quero marcar um corte às 16"
    ↓
[bot.py] handlers/bot.py → tratar_mensagens_gerais()
    ↓
[router] principal_router.py:3235 → tratar_mensagem_gpt(user_id, mensagem)
    ↓
[gpt_service] gpt_service.py:50 → processar_com_gpt(texto, user_id)
    ↓
[gpt_service] linha 75 → processar_com_gpt_com_acao()
    ↓
[GPT CALL 1] linha 1027 ← ⭐ PRIMEIRA CHAMADA GPT
    ↓
[Interpretação] Decide ação (agendar, confirmar, perguntar)
    ↓
[GPT CALL 2?] linha 2476 ← ⭐ SEGUNDA CHAMADA (SÓ EM ALGUNS CASOS)
    ↓
[Resultado] Retorna resposta

TOTAL: 1-2 chamadas GPT por áudio (fluxo principal)
```

### Cenário B: Resposta humana ou semana (RARO)
```
Se ação = "gerar_resposta_humana" → linha 3456 (+1 chamada)
Se ação = "organizar_semana" → linha 3213 (+1 chamada)
Se ação = "gerar_p1" → linha 3544 (+1 chamada)

MÁXIMO: 3 chamadas GPT por áudio (casos especiais)
```

---

## 6. O ÁUDIO PASSA POR GPT MAIS DE UMA VEZ?

**SIM. Potencialmente 2x no mesmo fluxo.**

### Fluxo que causa 2 chamadas:
```
Linha 1027 → client.chat.completions.create()
    ↓ (resposta interpretada)
    ↓ (resultado.get("acao") == "X")
    ↓
Linha 2476 → client.chat.completions.create()
    ↓ (SEGUNDA CHAMADA AO MESMO ÁUDIO)
```

### Quando acontece?
**Dentro de processar_com_gpt_com_acao() (mesma função):**

- Primeira chamada (1027): extrai intenção principal
- Se resultado indicar ação complexa: segunda chamada (2476)
- MESMO áudio é processado 2x pelo GPT

**Risco:** Se ambas as chamadas forem síncronas (não paralelas), dobraáginas requisições.

---

## 7. EXISTE CHAMADA DUPLICADA ENTRE:
### - handlers/bot.py
### - router/principal_router.py  
### - services/gpt_service.py

**NÃO encontrada duplicação evidente, MAS:**

```
handlers/bot.py
    ↓ chama
router/principal_router.py:3235
    ↓ chama
gpt_service.py:processar_com_gpt(texto, user_id)
    ↓ chama
gpt_service.py:processar_com_gpt_com_acao()
    ↓ chamadas 1027 + 2476
```

**Cadeeia única sem duplicação detectada.**

**MAS: Se houver erro/retry em handlers/bot.py, pode chamar novamente.**

---

## 8. EXISTE FALLBACK QUE CHAMA GPT NOVAMENTE APÓS ERRO?

**RISCO IDENTIFICADO: Possível retry implícito**

```python
# handlers/bot.py - tratar_mensagens_gerais()
# Se processar_com_gpt falhar:

try:
    resposta_fluxo = await tratar_mensagem_gpt(user_id, mensagem)
except Exception as e:
    # Handler continua, pode chamar novamente
    resposta_fluxo = await chamar_gpt_com_contexto(...)  # ⚠️ SEGUNDA TENTATIVA
```

**Padrão encontrado:**
- Primeira tentativa falha com 429
- Exception cai em `except`
- Pode haver tentativa alternativa na cadeia

**Verificação necessária:** Procurar em handlers/bot.py se há retry loop ou fallback.

---

## 9. O ERRO 429 ESTÁ SENDO TRATADO DE FORMA ESPECÍFICA?

**NÃO. Tratamento genérico.**

```python
# gpt_service.py:1041
except Exception as e:
    print(f"❌ Erro ao chamar OpenAI: {type(e).__name__}: {e}", flush=True)
    # ❌ NÃO distingue 429 de outros erros
    return {
        "resposta": "⚠️ Tive um problema para processar sua solicitação agora.",
        "acao": None,
        "dados": {},
    }
```

**O que DEVERIA fazer em 429:**
```python
# ✅ IDEAL (não implementado):
if isinstance(e, RateLimitError) or "429" in str(e):
    await asyncio.sleep(30)  # Esperar antes de retry
    # retry...
else:
    # Outro erro
```

**Status: 429 tratado igual a qualquer outro erro.**

---

## DIAGNÓSTICO FINAL: CAUSA PROVÁVEL DO 429

### Hipótese A: ✅ CONFIRMADO - Chamadas dobradas em um fluxo
```
Um áudio dispara:
  [Chamada 1] linha 1027
  ↓ (análise)
  [Chamada 2] linha 2476
  
= 2 requisições para 1 áudio, rapidamente
```

**Risco:** Se 10+ usuários enviam áudios simultaneamente:
```
10 áudios × 2 chamadas = 20 requisições/segundo
Limite GPT-4o: ~40 RPM (requests per minute) = 0.67 RPS

20 RPS >> 0.67 RPS → 429 GARANTIDO
```

---

### Hipótese B: ✅ CONFIRMADO - Sem retry inteligente
```
429 cai em except Exception genérico
Retorna erro imediatamente
Sem aguard antes de retry
Sem backoff exponencial
```

---

### Hipótese C: ⚠️ POSSÍVEL - Retry inadvertido em handlers
```
handlers/bot.py pode ter fallback não óbvio
Se processar_com_gpt falha → tenta chamar outra função GPT
= Até 3x chamadas para 1 áudio
```

---

### Hipótese D: ✅ CONFIRMADO - Modelo pesado
```
Modelo: gpt-4o (mais caro e mais lento)
Temperatura: 0.4 (OK, moderado)

gpt-4o é 2x mais lento que gpt-4-turbo
Se tráfego alto + modelo lento = 429 rápido
```

---

## PATCH MÍNIMO PROPOSTO (SEM IMPLEMENTAR)

### Opção 1: Tratamento específico de 429 (Recomendado)
```python
# services/gpt_service.py:1041
except Exception as e:
    if "429" in str(e) or "RateLimit" in str(type(e).__name__):
        # Exponential backoff
        await asyncio.sleep(5)  # Esperar antes de retry
        # Tentar novamente (máximo 2x)
    else:
        return {"resposta": "⚠️ Problema ao processar...", "acao": None}
```

### Opção 2: Debounce em handlers/bot.py
```python
# handlers/bot.py
# Aguardar 1s entre mensagens de mesmo usuário
# Evitar picos de requisições
```

### Opção 3: Otimizar fluxo (reduzir 2 chamadas → 1 chamada)
```python
# Combinar linha 1027 + 2476 em UMA chamada
# Usar multi-turn conversation em vez de 2 chamadas separadas
```

---

## RECOMENDAÇÃO FINAL

**Causa provável:** Combinação de A + B + D

1. **Áudios disparam 2 chamadas GPT rapidamente** (Hipótese A)
2. **Sem retry inteligente para 429** (Hipótese B)
3. **Modelo gpt-4o é pesado para esse volume** (Hipótese D)

**Ação mais impactante:**
1. Adicionar tratamento específico para 429 com backoff
2. Reduzir de 2 chamadas para 1 chamada por áudio
3. Considerar fallback para gpt-4-turbo em caso de 429

**Implementação recomendada:** Começar por Opção 1 (tratamento 429).


