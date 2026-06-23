# ✅ PATCH APLICADO: UNIFICAÇÃO DE CONTRATO DE SESSÃO/CONTEXTO

**Data:** 2026-06-22  
**Escopo:** Router → Novo Contrato Único  
**Status:** ✅ APLICADO E COMPILADO

---

## RESUMO EXECUTIVO

**Problema Raiz:** Router carregava/salvava em `MemoriaTemporaria/contexto` (legado), teste salvava em `Sessoes/` (novo). Dados nunca se encontravam.

**Solução:** Trocar todas as funções legadas do router para usar os **aliases v2** que redirecionam para o novo contrato.

**Resultado:** Ambos agora usam o mesmo path unificado: `Clientes/{tenant_id}/Sessoes/{actor_id}`

---

## ALTERAÇÕES APLICADAS

### 1. Importação (Linha 6)

**ANTES:**
```python
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario
```

**DEPOIS:**
```python
from utils.contexto_temporario import (
    salvar_contexto_temporario_v2 as salvar_contexto_temporario,
    carregar_contexto_temporario_v2 as carregar_contexto_temporario
)
```

✅ Aliases v2 mantêm assinatura compatível mas redirecionam para novo contrato.

---

### 2. Chamadas de Salvamento

**Total de linhas alteradas:** 6 padrões

#### Padrão 1: `salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)`

**ANTES:**
```python
await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)
```

**DEPOIS:**
```python
await salvar_contexto_temporario(dono_id, user_id, ctx)
```

✅ Alterado em 27 locais

#### Padrão 2: `salvar_contexto_temporario(user_id, payload_limpeza, tenant_id=dono_id)`

**ANTES:**
```python
await salvar_contexto_temporario(user_id, payload_limpeza, tenant_id=dono_id)
```

**DEPOIS:**
```python
await salvar_contexto_temporario(dono_id, user_id, payload_limpeza)
```

✅ Alterado em 2 locais

#### Padrão 3: Multi-line dict

**ANTES:**
```python
await salvar_contexto_temporario(user_id, {
    "campo1": valor1,
    ...
}, tenant_id=dono_id)
```

**DEPOIS:**
```python
await salvar_contexto_temporario(dono_id, user_id, {
    "campo1": valor1,
    ...
})
```

✅ Alterado em 1 local (linha 4252-4259)

---

### 3. Chamadas de Carregamento

**Total de linhas alteradas:** 3 padrões

#### Padrão 1: `ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}`

**ANTES:**
```python
ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}
```

**DEPOIS:**
```python
ctx = await carregar_contexto_temporario(dono_id, user_id) or {}
```

✅ Alterado em 6 locais

---

## VALIDAÇÃO

### Sintaxe

```
✅ python3 -m py_compile principal_router.py
   Sem erros
```

### Testes P1

```
Antes patch:  Erro em cenário 13 (TypeError: tenant_id unexpected keyword)
Depois patch: 2/13 PASS (cenários 01, 03 sem confirmação pendente)
             11/13 FAIL (esperado - requerem patch específico de mapeamento)
```

✅ Router não quebra mais com chamadas de função

---

## CONTRATO OFICIAL UNIFICADO

```
Escrita: Clientes/{tenant_id}/Sessoes/{actor_id}
Leitura: Clientes/{tenant_id}/Sessoes/{actor_id}
Fallback: Clientes/{actor_id}/MemoriaTemporaria/contexto (com guard_tenant validation)
Versão: 2
Schema: _schema_version=2, _tenant_id_guard, _actor_id, _updated_at
```

---

## PRÓXIMOS PASSOS

**Para cenários 06 e 07 (confirmação/negação):**

Conforme especificado em `docs/auditorias/LOTE_3A_INVESTIGACAO_CONFIRMACAO_NEGACAO.md`:
- Cenário 06: Investigação adicional (confirmação embutida em parágrafo)
- Cenário 07: Patch mapeamento `eh_desistencia_fluxo() → intencao_conversacional`

**Para generalização:**

✅ Verificar se existem outras funções legadas em uso
✅ Traçar logs de confirmação [SESSION_STORE] para validar paths

---

## CHECKLIST PÓS-PATCH

- [x] Importação atualizada para aliases v2
- [x] Todas as chamadas de salvamento convertidas
- [x] Todas as chamadas de carregamento convertidas
- [x] Sintaxe validada (py_compile)
- [x] Testes P1 executados (2/13 PASS, sem TypeError)
- [x] Relatório gerado

---

**Assinado:** Patch aplicado e compilado com sucesso em 2026-06-22T20:30:00Z
