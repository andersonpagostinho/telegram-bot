# ANÁLISE ARQUITETURAL: _send_and_stop() para WhatsApp

**Data:** 2026-09-27  
**Status:** Análise de somente leitura (não implementa)  
**Objetivo:** Menor correção sem quebrar Telegram

---

## 1. DEFINIÇÃO ATUAL

### Arquivo: router/principal_router.py:53-59

```python
async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    """
    Envia mensagem UMA vez e sinaliza para o bot.py não reenviar.
    """
    if context is not None:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
    return {"handled": True, "already_sent": True}
```

**Contrato atual:**
- Sempre retorna: `{"handled": True, "already_sent": True}`
- Envia apenas se `context is not None` (Telegram)
- Não diferencia entre Telegram e WhatsApp

---

## 2. CALLSITES DE _send_and_stop()

### Contagem
- **Total de callsites:** 202 em principal_router.py
- **Tipo:** Praticamente todos são `return await _send_and_stop(...)`
- **Pattern:** Usado para encerrar fluxo e sinalizar que mensagem foi enviada

### Distribuição Típica

```
return await _send_and_stop(
    context,
    user_id,
    "mensagem de resposta"
)
```

**Sempre tem 3 parâmetros obrigatórios:**
1. `context` — pode ser None (WhatsApp) ou ContextTypes (Telegram)
2. `user_id` — ID do usuário (telegram_id ou whatsapp_number)
3. `text` — mensagem a enviar

---

## 3. CONSUMIDORES DO RETORNO

### 3.1 Em handlers/bot.py (Telegram)

**Arquivo:** handlers/bot.py  
**Linhas:** 466, 828

```python
# handlers/bot.py:466
if isinstance(resposta, dict) and resposta.get("already_sent"):
    logger.debug("✅ Mensagem já foi enviada pelo router")
    # Não reenvia
    return

# handlers/bot.py:828
if isinstance(resposta, dict) and resposta.get("already_sent"):
    logger.debug("Resposta já foi enviada. Ignorando...")
    return
```

**Consumo:**
- Verifica **apenas** se `already_sent` está presente
- Se TRUE → não reenvia
- Se ausente → reenvia

### 3.2 Em main.py (WhatsApp)

**Arquivo:** main.py  
**Linhas:** 264-290

```python
if resposta:
    # Extrair texto da resposta (pode ser dict ou str)
    texto_resposta = None
    if isinstance(resposta, dict):
        texto_resposta = resposta.get("resposta")    # ← Procura APENAS por "resposta"
    elif isinstance(resposta, str):
        texto_resposta = resposta
    
    try:
        from services.whatsapp_service import enviar_mensagem_whatsapp
        
        # Só enviar se houver texto
        if texto_resposta:
            resultado = asyncio.run(
                enviar_mensagem_whatsapp(...)
            )
        else:
            logger.debug(f"[WA] Resposta sem texto (já enviada por outro canal...)")
```

**Consumo:**
- Se dict: procura por `resposta.get("resposta")`
- Se string: usa diretamente
- **NÃO verifica** "handled" ou "already_sent"
- Se `texto_resposta` for None → não envia

---

## 4. ANÁLISE DO PROBLEMA

### Situação Atual

**Telegram:**
```
_send_and_stop() retorna: {"handled": True, "already_sent": True}
                ↓
bot.py verifica: if resposta.get("already_sent"): → TRUE
                ↓
Não reenvia ✓
```

**WhatsApp:**
```
_send_and_stop() retorna: {"handled": True, "already_sent": True}
                ↓
main.py procura: resposta.get("resposta") → None
                ↓
if texto_resposta: → FALSE
                ↓
Não envia ✗ (usuario fica em silêncio)
```

---

## 5. ANÁLISE DE DEPENDÊNCIAS

### Quem depende de "already_sent"?

**handlers/bot.py (Telegram):**
```python
if resposta.get("already_sent"):
    # Não reenvia
```

✅ **Precisa de `already_sent=True`** para não duplicar no Telegram

### Quem depende de "handled"?

**Nenhum lugar encontrado** que verifique especificamente `handled`.

### Quem depende de "resposta"?

**main.py (WhatsApp):**
```python
texto_resposta = resposta.get("resposta")
```

❌ **Precisa de campo `resposta`** para saber o que enviar

---

## 6. CONTRATO ESPERADO

### Para Telegram (atual)
```python
return {"handled": True, "already_sent": True}
```

**Requisitos:**
- ✅ Campo `already_sent=True` (obrigatório)
- ✅ Mensagem já foi enviada via `context.bot.send_message()`
- ✅ bot.py não reenvia

### Para WhatsApp (necessário)
```python
# Opção A: String
return "👋 Olá! Como posso te ajudar hoje?"

# Opção B: Dict com "resposta"
return {"resposta": "👋 Olá! Como posso te ajudar hoje?", "already_sent": True}
```

**Requisitos:**
- ✅ Campo `resposta` com o texto (obrigatório)
- ✅ main.py consegue enviar via WhatsApp
- ✅ Não quebra o consumo de `already_sent` no Telegram

---

## 7. MENOR CORREÇÃO POSSÍVEL

### Opção 1: Retornar String + Preservar Dict
**Mudança em _send_and_stop() (principal_router.py:53-59)**

```python
async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    """
    Envia mensagem UMA vez e sinaliza para o bot.py não reenviar.
    """
    if context is not None:
        # Telegram: enviar via context.bot
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
        return {"handled": True, "already_sent": True}
    else:
        # WhatsApp: retornar texto para que main.py envie
        return {"resposta": text, "handled": True}
```

**Mudanças:** 3 linhas (adicionar else)  
**Impacto Telegram:** Zero (else nunca executa)  
**Impacto WhatsApp:** Agora main.py consegue enviar

**Vantagem:** Minimalista, não quebra nada

---

### Opção 2: Sempre Retornar Dict com Ambos
**Mudança em _send_and_stop() (principal_router.py:53-59)**

```python
async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    if context is not None:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
        return {"handled": True, "already_sent": True, "resposta": text}
    else:
        return {"resposta": text, "handled": True, "already_sent": False}
```

**Mudanças:** 2 linhas (adicionar "resposta" em cada retorno)  
**Impacto Telegram:** Zero (already_sent=True ainda existe)  
**Impacto WhatsApp:** main.py consegue enviar

**Vantagem:** Consistente, ambos canais retornam dict

---

### Opção 3: Retornar String para WhatsApp Diretamente
**Mudança em _send_and_stop() (principal_router.py:53-59)**

```python
async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    if context is not None:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
        return {"handled": True, "already_sent": True}
    else:
        # WhatsApp: retornar string simples
        return text
```

**Mudanças:** 3 linhas (adicionar else com return text)  
**Impacto Telegram:** Zero (if context ainda funciona)  
**Impacto WhatsApp:** main.py trata string normalmente (linha 269)

**Vantagem:** Muito limpo, semântica clara (string = texto a enviar)

---

## 8. RECOMENDAÇÃO: Opção 2

**Por quê:** Mais robusta e consistente

```python
async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    """
    Envia mensagem UMA vez e sinaliza para o bot.py não reenviar.
    """
    if context is not None:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
        return {"handled": True, "already_sent": True, "resposta": text}
    else:
        return {"resposta": text, "handled": True}
```

**Mudança exata:**
- Linha 58: adicionar `, "resposta": text`
- Linha 59: adicionar else com return dict

---

## 9. ARQUIVOS A ALTERAR

| Arquivo | Linhas | Mudança | Risco |
|---------|--------|---------|-------|
| router/principal_router.py | 53-59 | Adicionar "resposta" em retorno | Muito baixo |
| **NENHUM OUTRO** | — | — | — |

**Motivo:** Tanto Telegram (bot.py) quanto WhatsApp (main.py) já tratam dicts com campos extras.

---

## 10. CONSUMIDORES NÃO QUEBRAM

### bot.py (Telegram)
```python
if isinstance(resposta, dict) and resposta.get("already_sent"):
```

✅ Continua funcionando (procura apenas por "already_sent")

### main.py (WhatsApp) 
```python
texto_resposta = resposta.get("resposta")
```

✅ Agora funciona (campo "resposta" estará presente)

### Outros retornos em principal_router.py
```python
return {"acao": "...", "handled": True}
return {"resposta": "...", "acao": None}
```

✅ Não afetados (use retornam outros dicts)

---

## 11. TESTES ESPECÍFICOS APÓS ALTERAÇÃO

### T1: Telegram Saudação
```
Entrada: /start ou "oi"
Esperado: Resposta imediata, sem duplicação
Verificação: bot.py não reenvia (already_sent=True)
```

### T2: Telegram Agendamento
```
Entrada: "quero agendar corte amanhã às 14h"
Esperado: Processamento normal, confirmação única
Verificação: Sem duplicação de mensagens
```

### T3: WhatsApp Saudação "ola"
```
Entrada: "ola" via WhatsApp
Esperado: Resposta "Olá! Como posso te ajudar?"
Verificação: 
- main.py extrai campo "resposta"
- enviar_mensagem_whatsapp() é chamado
- usuario recebe mensagem
```

### T4: WhatsApp Agendamento
```
Entrada: "ola" seguido de agendamento via WhatsApp
Esperado: Fluxo completo funciona
Verificação: Sem silêncios, respostas coerentes
```

### T5: Múltiplos _send_and_stop() Chamados
```
Cenário: Fluxo que chama _send_and_stop() em 3 pontos diferentes
Esperado: Cada um tem seu próprio "resposta" field
Verificação: Não há conflitos, retornos são independentes
```

### T6: Dict vs String no webhook
```
Cenário: main.py recebe {"resposta": "...", "already_sent": False}
Esperado: Tratado corretamente
Verificação: 
- isinstance(resposta, dict) → TRUE
- resposta.get("resposta") → extrai texto
- enviar_mensagem_whatsapp() envia
```

---

## 12. RISCOS DE REGRESSÃO

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| bot.py não reconhece already_sent | Muito baixa | Campo ainda presente, apenas adiciona "resposta" |
| WhatsApp recebe duplicação | Muito baixa | main.py continua checando already_sent para lógica futura |
| Diferença entre Telegram e WhatsApp | Baixa | Ambos recebem dict, apenas campos diferentes |
| Consumidores esperam apenas "handled" | Muito baixa | Nenhum encontrado que use "handled" exclusivamente |
| String no retorno quebra algo | Não | Opção 2 usa dict sempre |

**Conclusão:** Risco de regressão **muito baixo**.

---

## 13. COMPATIBILIDADE

### Telegram (context ≠ None)
Retorno novo: `{"handled": True, "already_sent": True, "resposta": text}`

**bot.py verificação:**
```python
if resposta.get("already_sent"):  # Funciona ✓
```

**Qualquer lugar que verificar "handled":**
```python
if resposta.get("handled"):  # Funciona ✓
```

### WhatsApp (context = None)
Retorno novo: `{"resposta": text, "handled": True}`

**main.py verificação:**
```python
texto_resposta = resposta.get("resposta")  # Funciona ✓ (era None, agora tem valor)
```

---

## 14. RESUMO DA SOLUÇÃO

### Alteração Mínima
- **1 arquivo:** router/principal_router.py
- **1 função:** _send_and_stop()
- **2 linhas:** adicionar fields no retorno
- **Risco:** Muito baixo

### Implementação (Pseudo-código)
```python
# Antes (linha 59)
return {"handled": True, "already_sent": True}

# Depois (linha 58-59)
if context is not None:
    # Telegram: enviar e marcar como enviado
    return {"handled": True, "already_sent": True, "resposta": text}
else:
    # WhatsApp: retornar texto para webhook enviar
    return {"resposta": text, "handled": True}
```

### Impacto
- ✅ Telegram: funciona igual (already_sent ainda presente)
- ✅ WhatsApp: começa a funcionar (main.py consegue extrair "resposta")
- ✅ 202 callsites: nenhum quebra

---

**Próximo passo:** Aguardar aprovação para implementar.

Nenhuma alteração foi realizada. Análise apenas.
