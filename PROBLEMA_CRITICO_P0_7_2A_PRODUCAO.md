# 🚨 PROBLEMA CRÍTICO — P0.7.2A Não Responde em Produção

**Data:** 2026-10-27 20:35  
**Severidade:** CRÍTICO  
**Status:** BLOQUEADOR DE PRODUÇÃO  

---

## Evidência em Produção

**Conversação Real:**
```
Usuário: "a carla faz as mesmas coisa que a bruna?"

Sistema (ESPERADO): "Vamos ver: Carla: corte feminino, coloracao, hidratacao
                                   Bruna: corte feminino, escova, coloracao, hidratacao, manicure, pedicure"

Sistema (REAL):     "Atualmente, não tenho informações sobre os serviços que a Carla oferece. 
                    Apenas a Bruna está cadastrada como profissional..." [RESPOSTA GPT GENÉRICA]
```

**Logs Mostram:**
```
[P0.7_COMPARACAO_PROFISSIONAIS] Detectada comparação: Carla vs Bruna ✅ Detectado
[ANTES_CONSULTA_INFORMATIVA_IDLE] Resposta recebida: False | tipo=<class 'NoneType'> ❌ Retorna None
→ Sistema cai para GPT como fallback
```

---

## Análise do Fluxo

### ✅ Funcionamento Correto:
1. **Router (P0.7)** detecta comparação → linha 5567 `principal_router.py`
2. Seta `intencao_conversacional = "consulta"` → linha 5568
3. Passa para bloco consulta informativa → linha 5286

### ❌ Falha em Produção:
4. Handler é chamado → linha 5303:
   ```python
   resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
   ```
5. Handler retorna **None** ← **BUG**
6. Sistema cai para GPT como fallback

---

## Causa Raiz Identificada

**Arquivo:** `router/principal_router.py` linha 5303

```python
resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
```

**Problema:** O handler é chamado com `user_id`, mas **depende de `obter_id_dono(user_id)`** para converter user_id → tenant_id.

**Handler (informacao_service.py, linha ~314):**
```python
async def responder_consulta_informativa(mensagem: str, user_id: str) -> str | None:
    # ...
    dono_id = await obter_id_dono(user_id)  # ← DEPENDE DISTO
    
    profissionais_db = (await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais"))
```

### Possível Causa:
- Se `obter_id_dono(user_id)` retornar **None** → `dono_id = None`
- Se `dono_id = None` → `buscar_subcolecao(f"Clientes/None/Profissionais")` falha
- Handler retorna `None` (linha 399)
- **Sistema cai para GPT**

---

## Por Que Testes Passam

Os testes P0.7.2A usam **AsyncMock**, que nunca falham:

```python
# Em tests/test_p0_7_2a_comparacao_informativa.py:

with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
     patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

    mock_dono.return_value = "tenant_test"  # ← Mock funciona SEMPRE
    mock_buscar.side_effect = ...           # ← Retorna dados SEMPRE
```

Em produção:
- `obter_id_dono(user_id)` pode retornar **None**
- `buscar_subcolecao()` pode falhar/retornar vazio
- Handler retorna None

---

## Investigação Necessária

### Passo 1: Verificar o `user_id` passado
- Qual `user_id` está sendo usado na chamada linha 5303?
- É um `wa_id` ou um `actor_id`?
- É válido para `obter_id_dono()`?

### Passo 2: Verificar `obter_id_dono()`
- Pode retornar None para inputs válidos?
- Qual é a lógica de resolução tenant_id → user_id?

### Passo 3: Verificar `buscar_subcolecao()`
- Pode falhar silenciosamente?
- Qual é o retorno quando path não existe ou está vazio?

---

## Fix Recomendado (Preliminar)

**Opção A - Passar `dono_id` em vez de `user_id`:**

```python
# Linha 5303 em router/principal_router.py
resposta_informativa = await responder_consulta_informativa(mensagem, dono_id)  # ← MUDAR
```

Mas isto requer verificar se `dono_id` está disponível naquele escopo.

**Opção B - Adicionar fallback no handler:**

```python
# Em informacao_service.py
async def responder_consulta_informativa(mensagem: str, user_id: str) -> str | None:
    dono_id = await obter_id_dono(user_id)
    
    if not dono_id:
        print(f"⚠️ [AVISO] obter_id_dono retornou None para user_id={user_id}")
        return None  # Deixar GPT responder
    
    profissionais_db = (await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais")) or {}
    
    if not profissionais_db:
        print(f"⚠️ [AVISO] Nenhum profissional encontrado para dono_id={dono_id}")
        return None  # Deixar GPT responder
    
    # ... resto do handler
```

---

## Status

🔴 **BLOQUEADOR CRÍTICO**

- P0.7.2A implementado ✅
- Testes passam em isolamento ✅
- **Falha em produção com Firestore real** ❌

Próximo passo: Auditoria READ-ONLY para descobrir por que `obter_id_dono()` falha em produção.
