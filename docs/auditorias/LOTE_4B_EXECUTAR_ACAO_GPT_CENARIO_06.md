# LOTE 4B — AUDITORIA executar_acao_gpt CENÁRIO 06

**Data:** 2026-06-22  
**Escopo:** Somente cenário 06  
**Objetivo:** Identificar por que `executar_acao_gpt` falha após handler passar fluxo

---

## RESUMO EXECUTIVO

**Classificação:** B) Payload correto, `executar_acao_gpt` espera contrato que não está sendo honrado

**Raiz:** `executar_acao_gpt` assume que `update` nunca é `None`, mas o teste passa `update=None`

---

## CADEIA DE EVENTOS

### 1️⃣ Handler Executa Corretamente

✅ **LOTE 3E Handler Status:**
```
[LOTE_3E_CONFIRMACAO_EARLY] Confirmação detectada: pode deixar. li tudo...
[LOTE_3E_CONFIRMACAO] Confirmacao detectada
```

Handler retorna:
```python
{
    "tratado": True,
    "acao": "confirmar",
    "motivo": "confirmacao_detectada",
    "ctx_modificado": {...}
}
```

### 2️⃣ Router Passa Fluxo para criar_evento

**Linha:** `router/principal_router.py:4687`

```python
return await executar_acao_gpt(update, context, "criar_evento", dados_exec)
```

**Parâmetros:**
- `update=None` ← **PROBLEMA CRÍTICO**
- `context=MockContext()`
- `acao="criar_evento"`
- `dados_exec={...}` (dict com draft e confirmação)

### 3️⃣ executar_acao_gpt Falha em Linha 178

**Arquivo:** `services/gpt_executor.py:178`

```python
user_id = str(update.message.from_user.id)  # ❌ update é None
```

**Erro gerado:**
```
AttributeError: 'NoneType' object has no attribute 'message'
```

### 4️⃣ Except Block Captura e Retorna bool

**Arquivo:** `services/gpt_executor.py:711-720`

```python
except Exception as e:
    print("❌ ERRO DETALHADO em executar_acao_gpt:")
    traceback.print_exc()
    try:
        if getattr(update, "message", None):
            await update.message.reply_text(f"❌ Erro interno: {e}")
    except Exception:
        pass
    return True  # ← RETORNA BOOL
```

### 5️⃣ Teste Tenta `.get()` em bool

**Arquivo:** `tests/p1_robustez_fluxo_conversacional_real.py:635`

```python
resultado.resposta_enviada = resposta.get("resposta", "")
                              ^^^^^^
                              bool(True) não tem .get()
```

**Erro gerado:**
```
TypeError: 'bool' object has no attribute 'get'
```

---

## TABELA DE DIAGNÓSTICO

| Campo | Valor | Tipo | Esperado | Origem |
|-------|-------|------|----------|--------|
| `update` | `None` | `NoneType` | `Update` object | teste (MockContext) |
| `context` | `MockContext()` | `MockContext` | `ContextTypes.DEFAULT_TYPE` | teste |
| `acao` | `"criar_evento"` | `str` | `str` | router |
| `dados_exec` | `{...}` | `dict` | `dict` | router |
| **Retorno esperado** | `{...}` | `dict` | `dict` | contrato quebrado |
| **Retorno real** | `True` | `bool` | - | except block |

---

## RAIZ: CONTRATO QUEBRADO

### Problema Fundamental

`executar_acao_gpt` assume que `update` é sempre um objeto `Update` válido:

```python
async def executar_acao_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, acao: str, dados: dict):
    # Linha 178 — sem validação de update
    user_id = str(update.message.from_user.id)  # ❌ assume update é válido
```

### Em Contexto Real

Em cenário 06, a cadeia é:

1. Router chama: `await executar_acao_gpt(update=None, ...)`
2. `executar_acao_gpt` tenta: `update.message.from_user.id`
3. Exceção capturada, **retorna bool** em vez de dict
4. Teste espera dict, recebe bool
5. `.get()` falha em bool

---

## CLASSIFICAÇÃO FINAL

**Tipo:** B) Payload correto, `executar_acao_gpt` espera contrato antigo

**Descrição:**

- ✅ Handler funciona corretamente
- ✅ Contexto está sendo carregado corretamente (LOTE 4A fix)
- ✅ Dados passados para `executar_acao_gpt` estão corretos
- ❌ `executar_acao_gpt` não valida `update` antes de usar
- ❌ Except block retorna `bool` em vez de manter contrato `dict`

---

## VALIDAÇÃO DE NÃO-REGRESSÃO

✅ **Cenário 07 (Negação):** PASS (não usa `criar_evento`)  
✅ **Handler LOTE 3E:** Funciona 100%  
✅ **Contexto Path:** Corrigido em LOTE 4A  
⚠️  **Cenário 06:** Falha em `executar_acao_gpt`, não no handler

---

## RECOMENDAÇÃO

**Opção 1: Validar update em executar_acao_gpt (RECOMENDADO)**

```python
# Em services/gpt_executor.py:177-179
if not update:
    print("[AVISO] executar_acao_gpt chamada sem update")
    return {"acao": None, "resposta": "Contexto de update não disponível"}

user_id = str(update.message.from_user.id)
```

**Opção 2: Não passar update=None do router**

```python
# Em router/principal_router.py:4687
# Usar None-safe executar_acao_gpt ou chamar sem update
```

**Opção 3: Adicionar função wrapper**

```python
async def executar_acao_gpt_safe(update, context, acao, dados):
    """Versão que lida com update=None"""
    if not update:
        return {"acao": None}
    return await executar_acao_gpt(update, context, acao, dados)
```

---

## LOGS COMPLETOS DE EXECUÇÃO

### Início do Cenário 06

```
[LOTE_3E_CONFIRMACAO_EARLY] Confirmação detectada
[LOTE_3E_CONFIRMACAO] Confirmacao detectada
```

### Chamada para criar_evento

```
[AUDIT-CONF:BLOCO_PENDENTE_ENTRADA] texto='Pode deixar...' | estado_fluxo=confirmacao_pendente
[AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto
```

### Erro Capturado

```
Traceback (most recent call last):
  File "services/gpt_executor.py", line 178, in executar_acao_gpt
    user_id = str(update.message.from_user.id)
                  ^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'message'

🪵 Ação recebida: 'criar_evento'
❌ ERRO DETALHADO em executar_acao_gpt:

[FAIL] 06. Confirmação embutida em parágrafo - Erro: 'bool' object has no attribute 'get'
```

---

## STATUS FINAL

- ✅ Handler LOTE 3E: **FUNCIONAL**
- ✅ Contexto Path: **CORRIGIDO** (LOTE 4A)
- ❌ executar_acao_gpt: **REQUER VALIDAÇÃO** (Não valida update=None)
- ⚠️ Cenário 06: **FALHA EM ETAPA POSTERIOR**, não no handler
- ✅ Cenário 07: **PASS CONFIRMADO**

---

## PRÓXIMAS AÇÕES

1. Decidir se `executar_acao_gpt` deve suportar `update=None`
2. Se sim, adicionar validação em linha 177-179
3. Se não, garantir que router nunca chama com `update=None`
4. Validar contrato: função deve retornar dict, não bool
