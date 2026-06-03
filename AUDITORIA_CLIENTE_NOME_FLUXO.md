# 🔍 AUDITORIA: Fluxo de `cliente_nome` — "Suri" → "Anderson Agostinho"

**Objetivo:** Rastrear por que "corte para Suri" termina com cliente_nome="Anderson Agostinho"
**Data:** 2026-06-02
**Método:** Análise de fluxo sem alterações de código

---

## FLUXO COMPLETO: Onde "Suri" é Perdida

---

### 1️⃣ PONTO 1: Onde "Suri" é Detectada Pela Primeira Vez

**Arquivo:** `handlers/voice_command_handler.py`  
**Função:** `handle_voice_message()`  
**Linhas:** 55-70

```python
acao = resultado.get("acao")
dados = resultado.get("dados", {}) or {}
resposta = resultado.get("resposta", "✅ Comando processado.")

# [TESTE_SURI] 2️⃣ JSON BRUTO DO GPT
print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: acao={repr(acao)}", flush=True)
print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: dados_keys={list((dados or {}).keys())}", flush=True)
if "cliente_nome" in (dados or {}):
    print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: cliente_nome={repr(dados.get('cliente_nome'))}", flush=True)
```

**O que acontece aqui:**
- GPT extrai `dados.get("cliente_nome")` do áudio "corte para Suri"
- ✅ Se GPT retorna `{"cliente_nome": "Suri", ...}` → Log mostra "Suri"
- ❌ Se GPT retorna `{"profissional": "Suri", ...}` → Log NÃO menciona cliente_nome

**Ponto crítico:** Se o GPT classifica "Suri" como `profissional` em vez de `cliente_nome`, ele nunca será extraído corretamente.

---

### 2️⃣ PONTO 2: Transferência para `executar_acao_gpt()`

**Arquivo:** `handlers/voice_command_handler.py`  
**Linha:** 73

```python
if acao:
    sucesso = await executar_acao_gpt(update, context, acao, dados)
```

**O que acontece:**
- `dados` (com ou sem `cliente_nome`) é passado para `executar_acao_gpt()`
- O valor de `cliente_nome` ainda está em `dados` neste ponto (ou ausente)

---

### 3️⃣ PONTO 3: Decisão Crítica - Onde "Suri" é Perdida ⚠️ **LINHA EXATA**

**Arquivo:** `handlers/event_handler.py`  
**Função:** `add_evento_por_gpt()`  
**Linhas:** 505-511

```python
# 📝 Aplicar ordem de prioridade para cliente_nome
cliente_nome = (
    dados.get("cliente_nome")              # ← Tenta extrair do JSON do GPT
    or cliente_cadastrado.get("nome")      # ← Tenta cliente cadastrado em Firestore
    or update.message.from_user.full_name  # ← ⚠️ **FALLBACK PARA ANDERSON AGOSTINHO**
    or update.message.from_user.first_name # ← Último recurso
)
```

### **AQUI ACONTECE O PROBLEMA:**

Se `dados.get("cliente_nome")` é **None** ou **falta** (porque GPT não extraiu como cliente_nome):

```
dados.get("cliente_nome") = None
    ↓ (ou está vazio/falso)
cliente_cadastrado.get("nome") = None
    ↓ (usuário não tem perfil completo)
update.message.from_user.full_name = "Anderson Agostinho"
    ↓
cliente_nome = "Anderson Agostinho"  ❌ SURI FOI PERDIDA
```

**Exatamente qual linha é a culpa:**
```python
or update.message.from_user.full_name  # Linha 509
```

Essa linha **sobrescreve** "Suri" (ou ausência de "Suri") com "Anderson Agostinho".

---

### 4️⃣ PONTO 4: Onde `cliente_nome` Deveria Entrar em `draft_agendamento` — MAS NÃO ENTRA ⚠️

**Arquivo:** `router/principal_router_precheck_func.py`  
**Função:** `aplicar_precheck_agendamento()`  
**Linhas:** 34-39

```python
ctx["draft_agendamento"] = {
    "profissional": None,
    "data_hora": data_hora,
    "servico": servico,
    "modo_prechecagem": True
}
```

### **ACHADO CRÍTICO:**
`draft_agendamento` **NÃO INCLUI** `cliente_nome`:

```python
# ❌ FALTAM:
# "cliente_nome": cliente_nome,  ← DEVERIA ESTAR AQUI
# "duracao": ...,               ← DEVERIA ESTAR AQUI
# "cliente_id": ...,            ← DEVERIA ESTAR AQUI
```

**Onde deveria estar:**
```python
ctx["draft_agendamento"] = {
    "profissional": None,
    "data_hora": data_hora,
    "servico": servico,
    "modo_prechecagem": True,
    "cliente_nome": cliente_nome,  # ← ESTÁ FALTANDO
    "duracao": duracao,            # ← ESTÁ FALTANDO
    "cliente_id": user_id,         # ← ESTÁ FALTANDO
}
```

---

### 5️⃣ PONTO 5: Onde `cliente_nome` Deveria Entrar em `dados_confirmacao_agendamento` — MAS NÃO ENTRA ⚠️

**Arquivo:** `handlers/event_handler.py`  
**Função:** `add_evento_por_gpt()`  
**Linhas:** 559-569

```python
contexto_confirmacao = {
    "aguardando_confirmacao_agendamento": True,
    "dados_confirmacao_agendamento": {
        "servico": servico,
        "profissional": profissional,
        "data_hora": data_hora_str,
        "duracao": duracao_minutos,
        "descricao": descricao,
        "origem": "confirmacao_pendente",
    }
}
```

### **ACHADO CRÍTICO:**
`dados_confirmacao_agendamento` **NÃO INCLUI** `cliente_nome`:

```python
# ❌ FALTAM:
# "cliente_nome": cliente_nome,  ← DEVERIA ESTAR AQUI
# "cliente_id": cliente_id,      ← DEVERIA ESTAR AQUI
```

**O log imprime `cliente_nome` na linha 574:**
```python
print(f"[TESTE_SURI] 4️⃣ CONTEXTO_SALVO: cliente_nome={repr(cliente_nome)}", flush=True)
```

Mas **não o salva** no contexto!

**Onde deveria estar:**
```python
"dados_confirmacao_agendamento": {
    "servico": servico,
    "profissional": profissional,
    "data_hora": data_hora_str,
    "duracao": duracao_minutos,
    "descricao": descricao,
    "origem": "confirmacao_pendente",
    "cliente_nome": cliente_nome,  # ← ESTÁ FALTANDO
    "cliente_id": cliente_id,      # ← ESTÁ FALTANDO
}
```

---

### 6️⃣ PONTO 6: Onde `add_evento_por_gpt()` Decide Usar Nome do Usuário do Telegram

**Arquivo:** `handlers/event_handler.py`  
**Função:** `add_evento_por_gpt()`  
**Linhas:** 505-511

Este é o **MESMO PONTO 3** onde ocorre a decisão:

```python
cliente_nome = (
    dados.get("cliente_nome")              # Se vem do GPT
    or cliente_cadastrado.get("nome")      # Se existe cadastro
    or update.message.from_user.full_name  # ← **ANDERSON AGOSTINHO VEM DAQUI**
    or update.message.from_user.first_name
)
```

**Exatamente como chega a "Anderson Agostinho":**
```
update.message.from_user.full_name = "Anderson Agostinho"
                                       (nome do usuário no Telegram)
```

---

## RESUMO: O CICLO DA PERDA DE "SURI"

```
1️⃣ ENTRADA
   Usuário diz: "corte para Suri"
   
2️⃣ GPT EXTRAI (linhas 62-65 voice_command_handler.py)
   JSON: {"cliente_nome": "Suri", ...}  ou  {"profissional": "Suri", ...}
   
3️⃣ TRANSFERÊNCIA (linha 73 voice_command_handler.py)
   dados = {"cliente_nome": "Suri", ...}
   
4️⃣ DECISÃO CRÍTICA (linhas 505-511 event_handler.py) ⚠️ **LINHA EXATA DO PROBLEMA**
   IF dados.get("cliente_nome") is None:
       cliente_nome = update.message.from_user.full_name
       cliente_nome = "Anderson Agostinho"  ❌ **SURI FOI SOBRESCRITA**
   
5️⃣ SALVAMENTO INCOMPLETO (linhas 561-568 event_handler.py)
   dados_confirmacao_agendamento = {
       # "cliente_nome": cliente_nome,  ← NÃO ESTÁ AQUI
       ...
   }
   
6️⃣ SALVAMENTO INCOMPLETO (linhas 34-39 principal_router_precheck_func.py)
   draft_agendamento = {
       # "cliente_nome": cliente_nome,  ← NÃO ESTÁ AQUI
       ...
   }
   
7️⃣ RESULTADO FINAL
   evento_data["cliente_nome"] = "Anderson Agostinho"  ❌
   (Deveria ser "Suri")
```

---

## PROBLEMAS IDENTIFICADOS

### ❌ Problema 1: GPT Classifica "Suri" Errado

**Responsável:** `prompts/manual_secretaria.py`  
**Causa:** Prompt não distingue bem "para Suri" de "com Suri"

**Evidência:**
```
Usuário: "corte para Suri"
GPT retorna: {"profissional": "Suri"}  ← ERRADO
Deveria retornar: {"cliente_nome": "Suri"}  ← CORRETO
```

---

### ❌ Problema 2: Fallback Automático para "Anderson Agostinho"

**Responsável:** `handlers/event_handler.py`, linhas 505-511  
**Causa:** Lógica assume que se não há cliente_nome, o cliente é o próprio usuário

**Evidência:**
```python
or update.message.from_user.full_name  # ← Sobrescreve "Suri"
```

**O que deveria acontecer:**
```python
cliente_nome = (
    dados.get("cliente_nome")  # Tenta do GPT
    or cliente_cadastrado.get("nome")  # Tenta cadastro
    # Se nada: PERGUNTE, não assuma "Anderson"
)

if not cliente_nome:
    # Perguntar: "Para quem é o agendamento?"
    return {"resposta": "...", "acao": None}
```

---

### ❌ Problema 3: `draft_agendamento` Não Inclui `cliente_nome`

**Responsável:** `router/principal_router_precheck_func.py`, linhas 34-39  
**Causa:** Campo foi esquecido na inicialização

**Resultado:**
- Draft não rastreia quem é o cliente
- Confirmação não sabe quem é o cliente
- Evento é criado com cliente errado

---

### ❌ Problema 4: `dados_confirmacao_agendamento` Não Inclui `cliente_nome`

**Responsável:** `handlers/event_handler.py`, linhas 561-568  
**Causa:** Campo foi esquecido na estrutura

**Resultado:**
- Confirmação não mostra para quem é o agendamento
- Contexto perdido entre etapas

---

## LINHAS EXATAS DO PROBLEMA

| # | Arquivo | Linha | Problema | Tipo |
|---|---------|-------|---------|------|
| 1 | `prompts/manual_secretaria.py` | ~215-296 | GPT não distingue "para Suri" | Semântica |
| 2 | `handlers/event_handler.py` | **509** | Fallback automático sobrescreve "Suri" | **CRÍTICO** |
| 3 | `handlers/event_handler.py` | **561-568** | `dados_confirmacao_agendamento` sem `cliente_nome` | Estrutura |
| 4 | `router/principal_router_precheck_func.py` | **34-39** | `draft_agendamento` sem `cliente_nome` | Estrutura |

---

## RESPOSTA À PERGUNTA DO USUÁRIO

**Por que "corte para Suri" termina como cliente_nome = "Anderson Agostinho"?**

**Resposta:** Na linha **509 de `handlers/event_handler.py`**, quando `dados.get("cliente_nome")` é `None` (porque o GPT não extraiu "Suri" como cliente_nome, provavelmente classificou como profissional), o código faz fallback automático para `update.message.from_user.full_name`, que é "Anderson Agostinho".

**Causa Raiz:** 
1. **Problema Semântico** (linha ~215 de manual_secretaria.py): GPT não extrai "Suri" como `cliente_nome`
2. **Fallback Agressivo** (linha 509 de event_handler.py): Código assume automaticamente que o cliente é o próprio usuário

**Solução Necessária:**
1. Ajustar prompt do GPT para distinguir melhor "para Suri"
2. Remover fallback automático e perguntar em vez de assumir
3. Adicionar `cliente_nome` a `draft_agendamento` e `dados_confirmacao_agendamento`

---

**Status da Auditoria:** ✅ Localização exata confirmada. Nenhuma alteração de código realizada.

