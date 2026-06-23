# LOTE 4E — CONTRATO DE RETORNO executar_acao_gpt

**Data:** 2026-06-22  
**Escopo:** `services/gpt_executor.py:720` (except block)  
**Objetivo:** Garantir que `executar_acao_gpt` sempre retorne dict, inclusive em erro

---

## IMPLEMENTAÇÃO

### Alteração Realizada

**Arquivo:** `services/gpt_executor.py:711-720`

**Antes:**
```python
except Exception as e:
    import traceback
    print("❌ ERRO DETALHADO em executar_acao_gpt:")
    traceback.print_exc()
    try:
        if getattr(update, "message", None):
            await update.message.reply_text(f"❌ Erro interno: {e}")
    except Exception:
        pass
    return True  # ← BOOL
```

**Depois:**
```python
except Exception as e:
    import traceback
    print("❌ ERRO DETALHADO em executar_acao_gpt:")
    traceback.print_exc()
    try:
        if getattr(update, "message", None):
            await update.message.reply_text(f"❌ Erro interno: {e}")
    except Exception:
        pass
    return {
        "ok": False,
        "erro": str(e),
        "tipo_erro": "exception_executar_acao_gpt",
        "acao": acao,
        "resultado": None
    }
```

### Validação

✅ **Sintaxe:** `python -m py_compile services/gpt_executor.py` — OK

---

## RESULTADO

### Teste Cenário 06

Status: **❌ AINDA FALHA**

```
[FAIL] 06. Confirmação embutida em parágrafo - Erro: 'bool' object has no attribute 'get'
```

### Teste Cenário 07

Status: **✅ PASS** (sem regressão)

### Descoberta Crítica

#### Problema: Múltiplos Returns Bool em executar_acao_gpt

A função tem **18 linhas** retornando `True` ou `False`:

```
Linha 175: return False  ← Na função
Linha 186: return True   ← Na função
Linha 193: return True   ← Na função
... (14 mais)
Linha 709: return False  ← Na função
```

Todas essas linhas retornam **bool**, não dict!

**Sequência no Cenário 06:**

1. Router chama: `return await executar_acao_gpt(update, context, "criar_evento", dados_exec)` (linha 4687)
2. executar_acao_gpt retorna: `True` (bool) em sucesso OU `dict` em erro
3. Router retorna: `True` (bool) ou `dict`
4. Teste faz: `resposta.get("resposta", "")` 
5. Se `resposta=True` (bool): `TypeError: 'bool' object has no attribute 'get'`

### Raiz: Contrato Incompleto

Apenas corrigir o except block não foi suficiente. O problema é que **toda a função** mistura returns:
- `return True` (linha 186, 193, 201, ...) — sucesso
- `return False` (linha 175, 709) — falha
- `return dict` (linha 720 agora) — erro com detalhes

**Contrato esperado:** SEMPRE retorna dict

**Contrato atual:** Retorna bool OU dict (AMBÍGUO)

---

## ANÁLISE: Por que isso é um padrão antigo

`executar_acao_gpt` foi escrito para retornar bool (True=tratado, False=não tratado). Mas o router e testes evoluíram para esperar dict.

Linhas que ainda retornam bool:
- 175: `if not acao or acao.strip() == "": return False`
- 186: `await add_task_por_gpt(...); return True`
- 193: `await update.message.reply_text(...); return True`
- 201: `await update.message.reply_text(...); return True`
- ... (14 mais retornos True/False em diferentes ações)

---

## RECOMENDAÇÃO: LOTE 4F (PRÓXIMO)

**Escopo expandido:** Todas as linhas de `executar_acao_gpt`

**Tarefa:** Unificar retorno para dict SEMPRE

**Padrão:**

```python
# Sucesso (diferentes ações)
return {
    "ok": True,
    "acao": acao,
    "resultado": {...},
    "erro": None
}

# Falha
return {
    "ok": False,
    "acao": acao,
    "resultado": None,
    "erro": str(e),
    "tipo_erro": "tipo_específico"
}
```

**Sequência:**
1. Mudar linha 175: `return {"ok": False, ...}`
2. Mudar linha 186, 193, 201, etc: `return {"ok": True, ...}`
3. Mudar linha 709: `return {"ok": False, ...}`
4. Executar testes: cenário 06 e 07, depois baseline

**Restrição:** Mantém lógica idêntica, apenas muda tipo de retorno

---

## STATUS LOTE 4E

| Aspecto | Status | Nota |
|---------|--------|------|
| Except block corrigido | ✅ FEITO | Agora retorna dict |
| Cenário 06 | ❌ AINDA FALHA | Retornos de sucesso ainda são bool |
| Cenário 07 | ✅ PASS | Sem regressão (não chama executar_acao_gpt via router) |
| Raiz identificada | ✅ SIM | Função mistura bool + dict |
| Solução completa | ⏳ PENDENTE | Requer unificação de TODOS os returns (LOTE 4F) |

---

## CONCLUSÃO

Erro "bool object has no attribute get" não é apenas sobre except block. É sobre todo o contrato da função estar quebrado.

**Descoberta:** O except block que foi mudado é apenas 1 de 18 returns bool na função.

**Próximo:** LOTE 4F — Unificar TODOS os returns para dict (mudança estrutural, não apenas patch).

