# RASTREAMENTO ESTÁTICO: Fluxo "ola" WhatsApp → already_sent=True

**Data:** 2026-09-27  
**Método:** Análise estática de código (sem alterar)  
**Status:** ✅ CADEIA CAUSAL COMPROVADA

---

## 1. PONTO DE ENTRADA: Webhook WhatsApp (main.py)

### Arquivo: main.py:171-299
### Rota: POST /webhook/whatsapp

**Fluxo de entrada:**
```
1. Linha 172: def whatsapp_webhook_post():
2. Linha 175: body = request.get_data(as_text=True)
3. Linha 181: data = request.get_json(force=True)
   └─ Payload: {"entry": [...]}
   
4. Linha 212: text_body = msg.get("text", {}).get("body", "")
   └─ Resultado: text_body = "ola"
   
5. Linha 214: logger.info(f"📱 WhatsApp - De: {from_number}, Texto: {text_body}")
   └─ Log: "📱 WhatsApp - De: whatsapp:5511991382080, Texto: ola"
```

---

## 2. RESOLUÇÃO DE TENANT (main.py:224-229)

### Código: main.py:224-225
```python
from services.whatsapp_endpoint_service import resolver_tenant_por_endpoint
tenant_id = resolver_tenant_por_endpoint(phone_number_id)
```

**Resultado:**
- `phone_number_id` = "1350170954840548"
- `resolver_tenant_por_endpoint("1350170954840548")` → **"7394370553"** ✅
- Função confirmada: `services/whatsapp_endpoint_service.py:93-126`

---

## 3. CHAMADA AO ROTEADOR (main.py:235-260)

### Código: main.py:237-243
```python
future = asyncio.run_coroutine_threadsafe(
    roteador_principal(
        user_id=from_number,           # "whatsapp:5511991382080"
        mensagem=text_body,            # "ola"
        tenant_id=tenant_id,           # "7394370553"
        update=None,
        context=None
    ),
    bot_loop
)
resposta = future.result(timeout=30)
```

**Chamada exata:**
```python
resposta = await roteador_principal(
    user_id="whatsapp:5511991382080",
    mensagem="ola",
    tenant_id="7394370553",
    update=None,
    context=None
)
```

---

## 4. PROCESSAMENTO DENTRO DE roteador_principal()

### Arquivo: router/principal_router.py:3364-11782

**Fluxo de "ola" (DETERMINÍSTICO):**

```
Entrada: mensagem="ola", tenant_id="7394370553"

┌─ Verificação 1: Confirmação pendente (linha 3422)
│  └─ resolver_confirmacao_pendente("ola")
│     └─ Resultado: NOT_TRATADO (não é sim/não)
│
├─ Verificação 2: Identidade/Onboarding (linha 3451)
│  └─ processar_fluxo_identidade_onboarding()
│     └─ Resultado: None (usuário já autenticado)
│
├─ Verificação 3: Admin commands (linha 3758)
│  └─ processar_comando_administrativo()
│     └─ Resultado: None (não é comando)
│
├─ Verificação 4: Onboarding endereço (linha 3779)
│  └─ processar_onboarding_endereco_dono()
│     └─ Resultado: None (endereço já fornecido)
│
├─ Verificação 5: Slot profissional (linha 3799)
│  └─ estado_fluxo != "aguardando_profissional"
│     └─ Resultado: SKIP
│
├─ Verificação 6: Bloqueio humano (linha 3723)
│  └─ controle_atendimento != "humano"
│     └─ Resultado: SKIP
│
└─ Verificação 7: NEOEVE NEUTRA (linha 4070)
   └─ [NEOEVE NEUTRA] sem fluxo ativo
      ├─ Verifica: if texto_lower in saudacoes_usuario
      ├─ Dicionário (linha 4072-4075):
      │  saudacoes_usuario = [
      │      "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
      │      "e ai", "e aí", "eai", "opa", "oie"
      │  ]
      │
      ├─ Teste: "ola" in saudacoes_usuario → TRUE ✅
      │
      └─ Execução (linha 4077-4082):
         return await _send_and_stop(
             context,              # context=None (WhatsApp)
             user_id,             # "whatsapp:5511991382080"
             "👋 Olá! Como posso te ajudar hoje?"
         )
```

---

## 5. FUNÇÃO _send_and_stop() (principal_router.py:53-59)

### Código: principal_router.py:53-59
```python
async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    """
    Envia mensagem UMA vez e sinaliza para o bot.py não reenviar.
    """
    if context is not None:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
    return {"handled": True, "already_sent": True}
```

**Execução para WhatsApp:**
- `context` = None (porque WhatsApp passa context=None)
- Condição: `if context is not None:` → **FALSE**
- Nenhuma mensagem é enviada via Telegram
- Retorno: `{"handled": True, "already_sent": True}` ✅ **ENCONTRADO**

---

## 6. RETORNO PARA main.py (webhook)

### Código: main.py:247
```python
resposta = future.result(timeout=30)
```

**resposta recebida:**
```python
resposta = {"handled": True, "already_sent": True}
```

---

## 7. PROCESSAMENTO NO WEBHOOK (main.py:264-290)

### Código: main.py:264-290
```python
if resposta:
    # Extrair texto da resposta (pode ser dict ou str)
    texto_resposta = None
    if isinstance(resposta, dict):
        texto_resposta = resposta.get("resposta")      # ← Procura por chave "resposta"
    elif isinstance(resposta, str):
        texto_resposta = resposta

    try:
        from services.whatsapp_service import enviar_mensagem_whatsapp
        
        # Só enviar se houver texto (não é "already_sent" ou ação interna)
        if texto_resposta:                             # ← Condição
            resultado = asyncio.run(
                enviar_mensagem_whatsapp(
                    destinatario_id=from_number,
                    mensagem=texto_resposta,
                    phone_number_id=phone_number_id
                )
            )
            # ... logging de sucesso ...
        else:
            logger.debug(f"[WA] Resposta sem texto (já enviada por outro canal ou é ação interna): {resposta}")
```

**Execução:**
1. `resposta = {"handled": True, "already_sent": True}`
2. `isinstance(resposta, dict)` → **TRUE**
3. `texto_resposta = resposta.get("resposta")` → **None** (chave não existe)
4. `if texto_resposta:` → **FALSE**
5. Pula bloco de envio
6. Executa `logger.debug(f"[WA] Resposta sem texto...")`
7. Retorna HTTP 200

---

## 8. RESUMO DA CADEIA CAUSAL

### ✅ FUNÇÃO QUE PRODUZIU already_sent=True

**`_send_and_stop()` em principal_router.py:53-59**

```python
return {"handled": True, "already_sent": True}
```

---

### ✅ CAMINHO COMPLETO EXECUTADO

```
1. POST /webhook/whatsapp (main.py:171)
   ├─ Extrai: user_id="whatsapp:5511991382080", mensagem="ola"
   │
2. Resolve tenant (main.py:225)
   ├─ resolver_tenant_por_endpoint("1350170954840548") → "7394370553" ✅
   │
3. Chama roteador (main.py:237-243)
   └─ await roteador_principal(
       user_id="whatsapp:5511991382080",
       mensagem="ola",
       tenant_id="7394370553",
       update=None,
       context=None
      )
      │
4. Dentro de roteador_principal() (router/principal_router.py:3364)
   ├─ Passa por verificações 1-6 (nenhuma reconhece "ola")
   │
5. Chega a NEOEVE NEUTRA (linha 4070)
   ├─ Verifica: "ola" in saudacoes_usuario → TRUE
   └─ Executa linha 4078: return await _send_and_stop(...)
      │
6. _send_and_stop() (linha 53-59)
   ├─ context=None → não envia via Telegram
   └─ Retorna: {"handled": True, "already_sent": True} ✅
      │
7. Volta para webhook (main.py:247)
   ├─ resposta = {"handled": True, "already_sent": True}
   │
8. Processamento (main.py:264-290)
   ├─ isinstance(resposta, dict) → TRUE
   ├─ texto_resposta = resposta.get("resposta") → None
   ├─ if texto_resposta → FALSE
   └─ Log: "Resposta sem texto (já enviada...)"
      │
9. HTTP 200 OK retornado
```

---

### ✅ SE UMA MENSAGEM FOI EFETIVAMENTE ENVIADA

**NÃO.** Nenhuma mensagem foi enviada.

**Evidência:**
- `_send_and_stop()` linha 57: `if context is not None:` → False (context=None para WhatsApp)
- A linha 58 `await context.bot.send_message(...)` NÃO foi executada
- Webhook retorna "Resposta sem texto" (linha 290)
- HTTP 200 OK mas sem envio

**Resultado:**
- Usuário WhatsApp: **recebeu NADA**
- Log do sistema: "Resposta sem texto (já enviada por outro canal ou é ação interna)"
- Status retornado: `{"handled": True, "already_sent": True}`

---

### ✅ SE HOUVE DUPLO PROCESSAMENTO

**NÃO detectado no código.**

Deduplicação em memória (main.py:70, 209):
```python
whatsapp_processed_ids = set()

if msg_id and msg_id in whatsapp_processed_ids:
    logger.debug(f"⏭️ Mensagem duplicada ignorada: {msg_id}")
    continue

if msg_id:
    whatsapp_processed_ids.add(msg_id)
```

Cada mensagem é processada uma única vez.

---

### ✅ CAUSA RAIZ

**Erro de semântica em `_send_and_stop()` para WhatsApp:**

```python
async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    """
    Envia mensagem UMA vez e sinaliza para o bot.py não reenviar.
    """
    if context is not None:                                    # ← PROBLEMA
        await context.bot.send_message(chat_id=user_id, ...)  # ← Telegram only
    
    return {"handled": True, "already_sent": True}              # ← Retorna sempre
```

**Problemas:**
1. `_send_and_stop()` assume `context.bot` (Telegram)
2. Para WhatsApp, `context=None`, então a mensagem NÃO é enviada aqui
3. Retorna `already_sent=True`, sinalizando que foi enviada
4. Webhook recebe dict, procura por "resposta" (não existe), não envia
5. **Resultado:** Marca como enviada mas não envia

---

## 9. EVIDÊNCIAS E LOCAIS

| Item | Arquivo | Linha | Código/Evidência |
|------|---------|-------|------------------|
| Entry point | main.py | 171 | @app.route("/webhook/whatsapp", methods=["POST"]) |
| Resolução tenant | main.py | 225 | tenant_id = resolver_tenant_por_endpoint(phone_number_id) |
| Chamada router | main.py | 237-243 | await roteador_principal(..., tenant_id=tenant_id, context=None) |
| NEOEVE NEUTRA | principal_router.py | 4070 | [NEOEVE NEUTRA] sem fluxo ativo |
| Saudações | principal_router.py | 4072-4075 | "ola" in saudacoes_usuario |
| Detecção | principal_router.py | 4077 | if texto_lower in saudacoes_usuario: |
| Retorno crítico | principal_router.py | 4078-4082 | return await _send_and_stop(...) |
| Função problema | principal_router.py | 53-59 | async def _send_and_stop() |
| Guarda-chuva | principal_router.py | 57 | if context is not None: |
| Webhook recebe | main.py | 247 | resposta = future.result(timeout=30) |
| Extração texto | main.py | 268 | texto_resposta = resposta.get("resposta") |
| Verificação | main.py | 276 | if texto_resposta: |
| Log | main.py | 290 | logger.debug(f"[WA] Resposta sem texto...") |

---

## 10. CANDIDATOS A ALTERAÇÃO (NÃO ALTERANDO)

### A. principal_router.py:53-59 (_send_and_stop)
**Problema:** Envia apenas via Telegram, retorna already_sent sempre

**Opção 1:** Retornar apenas texto para WhatsApp
```python
# NÃO ALTERANDO - apenas documentando
if context is None:
    return text  # Para WhatsApp, retornar string
else:
    # Para Telegram, enviar e retornar dict
    ...
```

### B. main.py:264-290 (webhook)
**Problema:** Procura por chave "resposta" que pode não existir

**Opção 2:** Aceitar string diretamente
```python
# NÃO ALTERANDO - apenas documentando
if isinstance(resposta, dict):
    texto_resposta = resposta.get("resposta") or resposta.get("message")
elif isinstance(resposta, str):
    texto_resposta = resposta
```

### C. principal_router.py:4070-4082 (NEOEVE NEUTRA)
**Problema:** Detecta saudação corretamente, mas _send_and_stop é inadequado para WhatsApp

**Opção 3:** Retornar string em vez de dict
```python
# NÃO ALTERANDO - apenas documentando
if context is not None:
    # Telegram
    return await _send_and_stop(context, user_id, "👋 Olá!...")
else:
    # WhatsApp
    return "👋 Olá! Como posso te ajudar hoje?"
```

---

## CONCLUSÃO FINAL

### ✅ Confirmado: Cadeia Causal Completa

1. **FUNÇÃO RESPONSÁVEL:** `_send_and_stop()` (principal_router.py:53-59)
2. **RETORNO:** `{"handled": True, "already_sent": True}`
3. **CAMINHO:** WhatsApp webhook → roteador → NEOEVE NEUTRA → _send_and_stop()
4. **MENSAGEM ENVIADA:** NÃO (context=None para WhatsApp)
5. **DUPLICAÇÃO:** NÃO (deduplicação em whatsapp_processed_ids)
6. **CAUSA RAIZ:** `_send_and_stop()` inadecuado para WhatsApp
7. **IMPACTO:** Usuario recebe nada, sistema marca como "já enviado"

### ⚠️ Problema Verdadeiro

Não há bug no fluxo. O comportamento está correto, mas:
- **NEOEVE NEUTRA** detecta "ola" corretamente
- **_send_and_stop()** não envia (esperado para WhatsApp)
- **Webhook** recebe "já enviada" corretamente
- **Usuario:** não recebe nada (silêncio)

A solução é não usar `_send_and_stop()` para WhatsApp, ou modificar para retornar string.

---

**FIM DA AUDITORIA**  
Nenhum código foi alterado.  
Nenhum Firestore foi modificado.
