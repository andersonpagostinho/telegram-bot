# 🚨 BLOQUEADOR CRÍTICO — TENANT_ID MISMATCH

**Data:** 2026-10-03  
**Severidade:** 🔴 CRÍTICA  
**Status:** CONFIRMADO (requer verificação final de chamada)

---

## PROBLEMA EXATO

**Linha 747 vs Linha 771 em `services/gpt_executor.py`:**

### Bloco SEM CONFLITO:

```python
# Linha 747: CARREGA com id_dono
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}

# [... modifica contexto_tmp ...]

# Linha 769: Adiciona ultima_acao
contexto_tmp["ultima_acao"] = "criar_evento"

# Linha 771: SALVA com tenant_id (PARÂMETRO DA FUNÇÃO)
await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=tenant_id)
```

### Contraste — Bloco COM CONFLITO:

```python
# Linha 673: CARREGA com dono_id  
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}

# [... modifica contexto_tmp ...]

# Linha 701: SALVA com tenant_id (PARÂMETRO DA FUNÇÃO)
await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=tenant_id)
```

---

## O DEFEITO

**Linha 747 carrega com `id_dono`**  
**Linha 771 salva com `tenant_id`**

Se `tenant_id` ≠ `id_dono`:

```
Salva com:
  _tenant_id_guard = "VALOR_DO_PARAMETRO_tenant_id"
  Clientes/{user_id}/MemoriaTemporaria/contexto

Próximo webhook tenta carregar com:
  principal_router.py:3511
  ctx = await carregar_contexto_temporario_v2(dono_id, cliente_id)
  
  ↓ Internamente ↓
  
  path_legado = f"Clientes/{actor_id}/MemoriaTemporaria/contexto"
  data_legado.get("_tenant_id_guard") = "VALOR_DO_PARAMETRO_tenant_id"
  
  Valida: "VALOR_DO_PARAMETRO_tenant_id" == dono_id ?
  
  ❌ SE DIFERENTE: retorna {} (REJEITA CONTEXTO)
  
  ↓
  
  ultima_acao = None
  eh_aceite_de_acao_pendente() retorna False
  Evento NUNCA é criado
```

---

## PONTO DE DIVERGÊNCIA

**Pergunta crítica:** Qual é o `tenant_id` parâmetro em `executar_acao_gpt()`?

**Verificação necessária:**

1. **ANTES DA MUDANÇA:** Procurar como `executar_acao_gpt()` é chamado
   - Qual é o `tenant_id` passado?
   - É o mesmo que `dono_id` ou diferente?

2. **SE FOREM IGUAIS:** Minha mudança funciona ✅
   ```
   _tenant_id_guard = tenant_id = dono_id = OK
   ```

3. **SE FOREM DIFERENTES:** Bloqueador permanece ❌
   ```
   _tenant_id_guard = tenant_id ≠ dono_id
   Contexto é recusado na leitura
   ```

---

## LINHA 747 SUSPEITA

A linha 747 usa `id_dono`:
```python
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}
```

MAS a linha 771 usa `tenant_id`:
```python
await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=tenant_id)
```

**Onde `tenant_id` vem?**

**Possibilidades:**
1. É parâmetro da função `executar_acao_gpt()` - precisa verificar assinatura
2. É definido localmente - precisa procurar atribuição
3. É importado globalmente - improvável
4. É `None` por padrão - causaria erro

---

## SOLUÇÃO CORRETA

Há duas opções:

### OPÇÃO 1: Usar `id_dono` em ambas

```python
# Linha 747: ✅ CERTO
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}

# Linha 771: MUDAR PARA
await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=id_dono)
```

### OPÇÃO 2: Usar `tenant_id` em ambas

```python
# Linha 747: MUDAR PARA
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=tenant_id) or {}

# Linha 771: ✅ CERTO (já usa tenant_id)
await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=tenant_id)
```

**Qual é correto?** Depende de qual é o valor esperado no próximo webhook (principal_router linha 3511 passa `dono_id`).

Se principal_router passa `dono_id`, então **OPÇÃO 1 é correta**.

---

## EVIDÊNCIA NO CÓDIGO

**Linha 673 usa `dono_id` no bloco CONFLITO:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}
```

**Isso sugere que `dono_id` é o padrão correto** para isolar contexto por tenant.

---

## STATUS

🔴 **BLOQUEADOR NÃO RESOLVIDO AINDA**

A mudança que fiz (adicionar `ultima_acao` na linha 769) vai ser **INÚTIL** se houver mismatch de tenant_id na linha 771.

**Próximo passo:** Verificar se `tenant_id` na linha 771 é igual a `id_dono` ou diferente.

---

## RECOMENDAÇÃO

**Sem fazer alterações:**

1. Procurar como `executar_acao_gpt()` é chamado de `principal_router.py`
2. Verificar qual valor é passado como `tenant_id`
3. Comparar com `dono_id` usado em linha 747
4. Confirmar se são iguais ou diferentes

Se diferentes: **A correção real é trocar `tenant_id=tenant_id` para `tenant_id=id_dono` na linha 771**

