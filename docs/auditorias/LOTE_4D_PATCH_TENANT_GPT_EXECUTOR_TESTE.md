# LOTE 4D — PATCH TENANT EM gpt_executor NO TESTE

**Data:** 2026-06-22  
**Escopo:** Somente runner/teste do cenário 06  
**Objetivo:** Resolver tenant mismatch causado por referência não patchada de `obter_id_dono`

---

## AUDITORIA DE IMPORTS

### Import Chain Analysis

**firebase_service_async.py (origem)**
```python
async def obter_id_dono(user_id: str) -> str:
    # Definição única em linha 279
```

**router/principal_router.py (linha 10)**
```python
from services.firebase_service_async import obter_id_dono, buscar_subcolecao
# ↓ Cria referência local: router.principal_router.obter_id_dono
```

**services/gpt_executor.py (linha 20)**
```python
from services.firebase_service_async import buscar_subcolecao, obter_id_dono
# ↓ Cria referência local: services.gpt_executor.obter_id_dono
```

### Problema Identificado

Teste patchava:
```python
with patch('router.principal_router.obter_id_dono') as mock_obter_id:
    mock_obter_id.return_value = tenant_id
    # ✓ Router usa referência patchada
    # ❌ gpt_executor usa referência NÃO patchada
```

Resultado:
- Router: `obter_id_dono(actor_id)` → `tenant_id` ✓
- gpt_executor: `obter_id_dono(actor_id)` → busca real em Firebase

---

## SOLUÇÃO IMPLEMENTADA

### Patch Duplo

Atualizar cenários 06 e 07 em teste (linhas 642-643):

**Antes:**
```python
with patch('router.principal_router.obter_id_dono') as mock_obter_id:
    mock_obter_id.return_value = tenant_id
```

**Depois:**
```python
with patch('router.principal_router.obter_id_dono') as mock_router, \
     patch('services.gpt_executor.obter_id_dono') as mock_gpt:
    mock_router.return_value = tenant_id
    mock_gpt.return_value = tenant_id
```

### Aplicação

- **Cenário 06:** Linhas 642-649 — Duplo patch
- **Cenário 07:** Linhas 712-719 — Duplo patch (via replace_all)

---

## RESULTADO PÓS-PATCH

### Tenant Mismatch: ✅ RESOLVIDO

**Antes:**
```
🚨 [CTX_LEGADO_TENANT_MISMATCH] CRÍTICO 
   | tenant mismatch: esperado=whatsapp:55119999006 | armazenado=teste_fluxo_p1_bc0eb3fa
```

**Depois:**
```
[DIAG_CARREGAR] guard_validacao: 
    guard_tenant=teste_fluxo_p1_bc0eb3fa 
    | esperado=teste_fluxo_p1_bc0eb3fa 
    | match=True
[CTX_LEGADO_COMPAT] | path=Clientes/whatsapp:55119999006/MemoriaTemporaria/contexto 
                    | tenant_id=teste_fluxo_p1_bc0eb3fa 
                    | guard_validado
```

### Novo Ponto de Falha Identificado

**Após contexto carregado corretamente:**

```
⚙️ Executando add_evento_por_gpt
[TESTE_SURI] 5️⃣ PAYLOAD_ADD_EVENTO: ...
[FAIL] 06. Confirmação embutida em parágrafo - Erro: 'bool' object has no attribute 'get'
```

---

## NOVO ERRO: CONTRATO RETORNO QUEBRADO

### Tipo

Função `executar_acao_gpt` retorna `True` (bool) em contextos de erro, mas caller (teste) espera `dict` com `.get()` disponível.

### Cenário

```python
# Na linha 635 do teste:
resultado.resposta_enviada = resposta.get("resposta", "")
                             ^^^^^^^^
                             executar_acao_gpt pode retornar True (bool)
```

### Código Problem

em `services/gpt_executor.py:711-720`:

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
    return True  # ← RETORNA BOOL, NÃO DICT
```

---

## VALIDAÇÃO

### Cenário 07: ✅ PASS (SEM REGRESSÃO)

```
[LOTE_3E_NEGACAO] Desistencia detectada
[PASS] 07. Negação embutida em parágrafo
```

### Cenário 06: ❌ FALHA EM NOVO PONTO

```
[LOTE_3E_CONFIRMACAO] Confirmacao detectada ✅
[AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto ✅
⚙️ Executando add_evento_por_gpt ✅
[FAIL] 06. Confirmação embutida em parágrafo - Erro: 'bool' object has no attribute 'get' ❌
```

### Classificação Novo Erro

**Tipo:** D) Bug real em execução de ação

**Causa:** Contrato retorno de `executar_acao_gpt` está quebrado

**Ponto:** `services/gpt_executor.py:720` retorna bool em lugar de dict

**Impacto:** Qualquer caller esperando dict fará `.get()` e receberá TypeError

---

## STATUS FINAL

| Aspecto | Status | Nota |
|---------|--------|------|
| Tenant mismatch em gpt_executor | ✅ RESOLVIDO | Patch duplo aplicado |
| Cenário 07 regressão | ✅ SEM REGRESSÃO | Continua PASS |
| Cenário 06 - Handler | ✅ OK | Detecta confirmação |
| Cenário 06 - Contexto Loaded | ✅ OK | Guard validado, match=True |
| Cenário 06 - executar_acao_gpt | ✅ CHAMADO | Executa `add_evento_por_gpt` |
| Cenário 06 - Retorno | ❌ CONTRATO QUEBRADO | Retorna bool em exc |

---

## RECOMENDAÇÃO LOTE 4E

**Problema:** `executar_acao_gpt` except block retorna `True` (bool), mas função assina como retornando dict

**Solução Mínima:** 

Em `services/gpt_executor.py:720`, retornar dict em vez de bool:

```python
except Exception as e:
    # ... existing code ...
    return {
        "acao": None,
        "resposta": f"Erro interno: {e}",
        "dados": {}
    }
```

**Alternativa:** Verificar contrato esperado e se `True` é valid de verdade

---

## CONCLUSÃO

**LOTE 4D alcançou objetivo:** Tenant mismatch resolvido com patch duplo.

**Novo ponto identificado:** Contrato de retorno quebrado em `executar_acao_gpt`.

**Próximo passo:** Corrigir return type em except block (LOTE 4E proposto) para retornar dict instead de bool.
