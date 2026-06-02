# 📊 AUDITORIA: Tamanho de Requisições GPT

**Objetivo:** Medir quanto de tokens/caracteres está sendo enviado ao GPT
**Data:** 2026-06-02
**Método:** Logs de medição sem alteração de lógica

---

## O que Está Sendo Medido

### Por cada chamada GPT:

1. **PROMPT_SIZE**
   - Caracteres totais do payload `messages` em JSON
   - Fórmula: `len(json.dumps(messages, ensure_ascii=False))`

2. **PROMPT_TOKENS_EST**
   - Estimativa de tokens (aproximação)
   - Fórmula: `payload_size / 4` (GPT usa ~4 caracteres por token)

3. **Contagem de mensagens**
   - Quantas messages estão sendo enviadas
   - Estrutura: `[system, user, assistant, ...]`

---

## Métricas a Rastrear

Para teste com: **"corte cabelo da Suri às 16 horas amanhã"**

### Esperado:
- Chamada 1: mensagem do usuário + histórico
- Chamada 2 (se existir): similar ou ampliado?

### Questão crítica:
```
Chamada 1: X tokens
Chamada 2: Y tokens

Y > X? 
  → Contexto foi ampliado
  → Dados foram adicionados
  → Duplicação com mudanças

Y = X?
  → Exatamente mesmo prompt
  → Duplicação pura
  → Desperdício

Y < X?
  → Contexto foi filtrado
  → Múltiplos caminhos com diferentes contextos
```

---

## Breakdown Esperado do Prompt

**Composição típica de `messages`:**

```
messages = [
  {
    "role": "system",
    "content": "<INSTRUCAO_SECRETARIA>"  ← manual_secretaria.py
  },
  {
    "role": "user", 
    "content": "<CONTEXTO + MENSAGEM_USUARIO>"  ← contexto + texto_usuario
  },
  ...histórico...
]
```

**Estimativa de proporções:**
- Manual da secretária: ~30-40% do prompt (instrução fixa)
- Contexto: ~20-30% (memória temporária)
- Mensagem do usuário: ~10-20% (entrada atual)
- Histórico: ~10-20% (conversas anteriores)

---

## Checklist de Medição

- [ ] Chamada 1: PROMPT_SIZE capturado
- [ ] Chamada 1: PROMPT_TOKENS_EST capturado
- [ ] Chamada 1: msgs count capturado
- [ ] Chamada 2 (se existir): PROMPT_SIZE capturado
- [ ] Chamada 2 (se existir): PROMPT_TOKENS_EST capturado
- [ ] Chamada 2 (se existir): msgs count capturado
- [ ] Comparação Chamada 1 vs 2 possível
- [ ] Nenhuma lógica foi alterada
- [ ] Nenhum modelo foi mudado
- [ ] Apenas logs de medição adicionados

---

## Próximas Análises

Com os dados coletados, será possível:

1. **Confirmar ou refutar duplicação**
   - Se Chamada 2 tem exatamente mesmo tamanho → duplicação
   - Se tem tamanho diferente → múltiplos caminhos

2. **Identificar impacto de tokens**
   - Tokens totais por áudio = Chamada 1 + Chamada 2 (se existir)
   - Multiplicado por volume de usuários → cálculo de 429

3. **Otimizar prompt**
   - Qual parte do prompt é redundante?
   - Qual parte é essencial?

---

## Estrutura Esperada de Logs

```
🧪 [GPT_ROUTE] CALL_1_START linha=1027
🤖 [GPT CALL] linha=1354 uid=... texto='...'
🧪 [PROMPT_SIZE] chars=5234 msgs=3
🧪 [PROMPT_TOKENS_EST] 1309
[resposta do GPT...]
🧪 [GPT_ROUTE] CALL_1_END
🧪 [GPT_ROUTE] CALL_1_RETURN linha=1172

(se existir Chamada 2)
🧪 [GPT_ROUTE] CALL_2_START linha=2476
🧪 [PROMPT_SIZE] chars=5234 msgs=3
🧪 [PROMPT_TOKENS_EST] 1309
[resposta do GPT...]
🧪 [GPT_ROUTE] CALL_2_END
🧪 [GPT_ROUTE] CALL_2_RETURN
```

---

**Status:** Instrumentação de medição completa. Pronto para teste.

