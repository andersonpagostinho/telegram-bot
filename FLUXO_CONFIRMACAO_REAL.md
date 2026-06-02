# 🔍 Fluxo Real de Confirmação de Agendamento

**Objetivo:** Traçar o fluxo EXATO desde "usuário diz sim" até "evento persistido + limpeza"

**Evidência:** Arquivo, função, linha para cada passo

---

## 1️⃣ PASSO 1: Usuário Envia "sim"

**Localização:**
- `router/principal_router.py:3366-3368`
- Função: `handle_message()` (função principal de roteamento)

```python
# principal_router.py:3366-3368
if eh_confirmacao_pendente_ativa(ctx) and (
    eh_confirmacao(texto_lower) or eh_aceite_de_acao_pendente(texto_usuario, ctx)
):
```

**Verificações:**
- `eh_confirmacao_pendente_ativa(ctx)` retorna `bool(ctx.get("aguardando_confirmacao_agendamento"))`
  - Definição: `principal_router.py:1576-1578`
  
- `eh_confirmacao(texto_lower)` verifica se texto é confirmação
  - Definição: `principal_router.py:885-905`
  - Gatilhos: "sim", "ok", "pode", "confirmar", "agendar", "perfeito", etc.

---

## 2️⃣ PASSO 2: LÊ CONTEXTO DO FIRESTORE

**Localização:**
- `router/principal_router.py:3372-3391`
- Recupera dados armazenados

```python
# principal_router.py:3372
dados_confirmacao = ctx.get("dados_confirmacao_agendamento") or {}
#
# principal_router.py:3373
draft = ctx.get("draft_agendamento") or {}

# principal_router.py:3375-3391 — extrai dados de confirmação/draft/contexto
profissional = (
    dados_confirmacao.get("profissional")
    or draft.get("profissional")
    or ctx.get("profissional_escolhido")
)

servico = (
    dados_confirmacao.get("servico")
    or draft.get("servico")
    or ctx.get("servico")
)

data_hora = (
    dados_confirmacao.get("data_hora")
    or draft.get("data_hora")
    or ctx.get("data_hora")
)
```

**Estrutura de dados:**
```
dados_confirmacao_agendamento = {
    "profissional": "Bruna",
    "servico": "escova",
    "data_hora": "2026-06-03T14:00:00",
    "duracao": 40,
    "descricao": "Escova com Bruna"
}

draft_agendamento = {
    "profissional": "Bruna",
    "servico": "escova",
    "data_hora": "2026-06-03T14:00:00",
    "modo_prechecagem": True
}
```

---

## 3️⃣ PASSO 3: MARCA CONTEXTO COMO NÃO PENDENTE + SALVA

**Localização:**
- `router/principal_router.py:3409-3412`

```python
# principal_router.py:3409
ctx["aguardando_confirmacao_agendamento"] = False  # ✅ Marca como processado

# principal_router.py:3410
ctx.pop("dados_confirmacao_agendamento", None)  # ✅ Remove dados confirmação

# principal_router.py:3411
ctx.pop("ultima_opcao_profissionais", None)

# principal_router.py:3412
await salvar_contexto_temporario(user_id, ctx)  # ✅ SALVA EM FIRESTORE
```

**Donde:** 
- `utils/contexto_temporario.py` — salva em `Clientes/{user_id}/MemoriaTemporaria/contexto`

---

## 4️⃣ PASSO 4: MONTA PAYLOAD DE EVENTO

**Localização:**
- `router/principal_router.py:3397-3407`

```python
# principal_router.py:3397-3407
if profissional and servico and data_hora:
    dados_exec = {
        "profissional": profissional,
        "servico": servico,
        "data_hora": data_hora,
        "duracao": duracao,
        "descricao": formatar_descricao_evento(servico, profissional),
        # 🔒 commit real da agenda: só chega aqui após confirmação do cliente
        "confirmado": True,  # ✅ GATE CRÍTICO — sem isso, não salva
        "status": "confirmado",
    }
```

**Campo crítico:**
- `"confirmado": True` — gate de segurança
  - Sem isso, `salvar_evento()` rejeita (linha `event_service_async.py:64`)

---

## 5️⃣ PASSO 5: CHAMA AÇÃO GPT PARA CRIAR EVENTO

**Localização:**
- `router/principal_router.py:3415`

```python
# principal_router.py:3415
return await executar_acao_gpt(update, context, "criar_evento", dados_exec)
```

**Fluxo dentro de `executar_acao_gpt()`:**
- `services/gpt_executor.py:482` — processa ação "criar_evento"
- Chama: `handlers/event_handler.py:454` — `add_evento_por_gpt()`

---

## 6️⃣ PASSO 6: `add_evento_por_gpt()` SALVA EVENTO

**Localização:**
- `handlers/event_handler.py:454` — função
- `handlers/event_handler.py:929` — chama `salvar_evento()`

```python
# event_handler.py:929
resultado_salvamento = await salvar_evento(user_id, evento_data)
```

**Onde `salvar_evento()` está:**
- `services/event_service_async.py:57`

### 6.1 Gate de Confirmação em `salvar_evento()`

**Localização:**
- `event_service_async.py:64-70`

```python
# event_service_async.py:64
if evento.get("confirmado") is not True:
    print("🚫 [SALVAR_EVENTO_BLOQUEADO] tentativa de salvar evento não confirmado...")
    return False  # ✅ REJEITA se não confirmado
```

### 6.2 Verificação de Conflito

**Localização:**
- `event_service_async.py:87-98`

```python
# event_service_async.py:87-98
conflitos = await verificar_conflito(
    user_id=user_id,
    data=evento["data"],
    hora_inicio=evento["hora_inicio"],
    duracao_min=evento.get("duracao", 60),
    profissional=evento.get("profissional", "")
)

if conflitos:
    print("⛔ Conflito de horário detectado. Evento não será salvo.")
    return False  # ✅ REJEITA se conflito
```

### 6.3 Idempotência (Proteção Contra Duplicação)

**Localização:**
- `event_service_async.py:100-135`

```python
# event_service_async.py:100-103
# ID idempotente por slot (evita duplicar ao confirmar/retentar)
base_id = f"{evento.get('cliente_id')}_{evento.get('profissional')}_{evento.get('data')}_{evento.get('hora_inicio')}"
event_id = base_id.replace(" ", "_").lower()

# event_service_async.py:131-135
# ANTIDUPLICIDADE (AQUI)
existente = await buscar_dado_em_path(path)
if existente:
    print("♻️ Evento já existe (idempotente). Não criando duplicado.")
    return "duplicado"  # ✅ DETECTA duplicação
```

### 6.4 Salva em Firestore

**Localização:**
- `event_service_async.py:137`

```python
# event_service_async.py:137
await salvar_dado_em_path(path, evento)  # ✅ PERSISTE EM FIRESTORE

# event_service_async.py:129
# Path: f"Clientes/{user_id_efetivo}/Eventos/{event_id}"
```

---

## 7️⃣ PASSO 7: ENVIA RESPOSTA AO USUÁRIO

**Localização:**
- `handlers/event_handler.py:989-990`

```python
# event_handler.py:989
msg_sucesso = montar_mensagem_confirmacao_sucesso(servico, profissional, start_time.isoformat())

# event_handler.py:990
await update.message.reply_text(msg_sucesso)  # ✅ RESPONDE COM MENSAGEM NATURAL
```

**Função `montar_mensagem_confirmacao_sucesso()`:**
- Localização: `utils/mensagens_agendamento.py:61-76`
- Gera: "Pronto, sua escova com Bruna ficou agendada para amanhã às 14h."

---

## 8️⃣ PASSO 8: LIMPA CONTEXTO DE AGENDAMENTO

**Localização:**
- `handlers/event_handler.py:992`

```python
# event_handler.py:992
await limpar_contexto_agendamento(user_id)  # ✅ LIMPA FIRESTORE
```

**Função `limpar_contexto_agendamento()`:**
- Localização: `utils/contexto_temporario.py:30-54`
- Path: `Clientes/{user_id}/MemoriaTemporaria/contexto`
- Remove:
  - `aguardando_confirmacao_agendamento` (DELETE_FIELD)
  - `dados_confirmacao_agendamento` (DELETE_FIELD)
  - `dados_anteriores` (DELETE_FIELD)
  - `draft_agendamento` (reseta para `{}`)

```python
# contexto_temporario.py:39-40
"aguardando_confirmacao_agendamento": firestore.DELETE_FIELD,
"dados_confirmacao_agendamento": firestore.DELETE_FIELD,
```

---

## 📊 Fluxo Visual Completo

```
Usuário: "sim"
│
├─► eh_confirmacao_pendente_ativa(ctx)?
│   └─► ctx.get("aguardando_confirmacao_agendamento") == True
│
├─► eh_confirmacao(texto_lower)?
│   └─► principal_router.py:885-905
│
├─► principal_router.py:3372-3391
│   └─► LÊ: dados_confirmacao_agendamento, draft_agendamento, ctx
│
├─► principal_router.py:3409-3412
│   ├─► ctx["aguardando_confirmacao_agendamento"] = False
│   ├─► ctx.pop("dados_confirmacao_agendamento")
│   └─► await salvar_contexto_temporario(user_id, ctx)
│       └─► MemoriaTemporaria/contexto (FIRESTORE)
│
├─► principal_router.py:3397-3407
│   └─► Monta dados_exec com confirmado=True
│
├─► principal_router.py:3415
│   └─► executar_acao_gpt(..., "criar_evento", dados_exec)
│       └─► gpt_executor.py:482 → event_handler.py:454
│           └─► add_evento_por_gpt()
│
├─► event_handler.py:929
│   └─► salvar_evento(user_id, evento_data)
│       ├─► event_service_async.py:64
│       │   └─► Gate: confirmado == True?
│       ├─► event_service_async.py:87-98
│       │   └─► Verifica conflito
│       ├─► event_service_async.py:131-135
│       │   └─► Detecta duplicação (idempotência)
│       └─► event_service_async.py:137
│           └─► await salvar_dado_em_path()
│               └─► Clientes/{dono}/Eventos/{event_id} (FIRESTORE)
│
├─► event_handler.py:989-990
│   ├─► msg_sucesso = montar_mensagem_confirmacao_sucesso()
│   └─► await update.message.reply_text(msg_sucesso)
│
└─► event_handler.py:992
    └─► await limpar_contexto_agendamento(user_id)
        └─► MemoriaTemporaria/contexto (DELETE_FIELD)
            ├─► aguardando_confirmacao_agendamento
            ├─► dados_confirmacao_agendamento
            └─► dados_anteriores
```

---

## ⚠️ Gates Críticos (Proteção Contra Erros)

| Gate | Localização | Condição | Rejeita Se |
|------|-------------|----------|-----------|
| **Confirmação Pendente** | principal_router.py:3366 | `aguardando_confirmacao_agendamento == True` | False |
| **Confirmação Válida** | principal_router.py:3367 | `eh_confirmacao()` ou aceite pendente | False |
| **Dados Completos** | principal_router.py:3397 | profissional AND servico AND data_hora | Qualquer nulo |
| **Confirmado Flag** | event_service_async.py:64 | `confirmado == True` | False |
| **Sem Conflito** | event_service_async.py:96 | Sem sobreposição horária | True |
| **Sem Duplicação** | event_service_async.py:132 | Evento não existe yet | True |

---

## 🔍 Estruturas de Dados Reais

### `aguardando_confirmacao_agendamento`
- **Tipo:** `bool`
- **Escopo:** `MemoriaTemporaria/contexto`
- **Valores:** `True` (aguardando) / `False` (não aguardando) / `DELETE_FIELD` (limpeza)
- **Definição:** principal_router.py:1730 (setado como True)
- **Leitura:** principal_router.py:3366

### `dados_confirmacao_agendamento`
- **Tipo:** `dict`
- **Escopo:** `MemoriaTemporaria/contexto`
- **Campos:**
  ```python
  {
      "profissional": str,
      "servico": str,
      "data_hora": str (ISO format),
      "duracao": int,
      "descricao": str,
      "origem": str (opcional)
  }
  ```
- **Definição:** principal_router.py:1732 (estrutura setada)
- **Leitura:** principal_router.py:3372

---

## 🚨 Cenários P0 — Validações Necessárias

### Cenário 11: Confirmação Duplicada
- **Verificar:** Após primeiro "sim", `aguardando_confirmacao_agendamento` fica `False`
- **Validar:** Segundo "sim" não entra no bloco principal_router.py:3366 (falha condition)
- **Resultado esperado:** 1 evento em Firestore

### Cenário 12: Dois Usuários Simultâneos
- **Gate crítico:** event_service_async.py:131-135 (antiduplicidade)
- **ID da chave:** `{cliente_id}_{profissional}_{data}_{hora_inicio}`
- **Resultado esperado:** 1 evento (segundo é detectado como "duplicado")

### Cenário 12B: Mesmo Usuário, Duas Confirmações Simultâneas
- **Gate crítico:** event_service_async.py:131-135 (antiduplicidade)
- **Também:** principal_router.py:3409 deve ser atômico
- **Risco:** Race condition em leitura/escrita de MemoriaTemporaria
- **Proteção:** Idempotência por ID de evento

---

## ✅ Resumo: Fluxo Validado

```
✅ Usuário diz "sim"
✅ Valida: aguardando_confirmacao_agendamento == True
✅ Valida: eh_confirmacao(texto)
✅ Lê: dados_confirmacao_agendamento
✅ Marca: aguardando_confirmacao_agendamento = False (LOCAL)
✅ Salva contexto (FIRESTORE)
✅ Cria evento com confirmado=True
✅ Salva evento (FIRESTORE) com antiduplicidade
✅ Responde mensagem natural
✅ Limpa contexto (FIRESTORE DELETE_FIELD)
```

**Fluxo É REAL. Não é hipótese.**
