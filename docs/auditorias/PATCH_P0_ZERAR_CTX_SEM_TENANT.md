# PATCH P0 — Zerar Chamadas de Contexto Sem Tenant

**Data:** 2026-06-19  
**Status:** ✅ PATCHES APLICADOS  
**Objetivo:** Eliminar 100% das chamadas a contexto SEM tenant_id nos fluxos críticos

---

## 🎯 Patches Aplicados (REAIS)

### 1. handlers/bot.py:248

**Antes:**
```python
ctx = await carregar_contexto_temporario(user_id) or {}
```

**Depois:**
```python
ctx = await carregar_contexto_temporario(user_id, tenant_id=tenant_id) or {}
```

**Contexto:** Handler de cancelamento pendente — sincronizar em MemoriaTemporaria  
**tenant_id Disponível:** ✅ SIM (linha 129: `tenant_id = await obter_id_dono(user_id)`)  
**Fluxo Afetado:** Cancelamento  
**Criticidade:** 🔴 P0 — Fluxo crítico

---

### 2. handlers/bot.py:289

**Antes:**
```python
ctx = await carregar_contexto_temporario(user_id) or {}
ctx.pop("cancelamento_pendente", None)
```

**Depois:**
```python
ctx = await carregar_contexto_temporario(user_id, tenant_id=tenant_id) or {}
ctx.pop("cancelamento_pendente", None)
```

**Contexto:** Limpar contexto após cancelamento confirmado  
**tenant_id Disponível:** ✅ SIM  
**Fluxo Afetado:** Cancelamento confirmado  
**Criticidade:** 🔴 P0 — Limpeza de estado crítico

---

### 3. handlers/bot.py:306

**Antes:**
```python
ctx = await carregar_contexto_temporario(user_id) or {}
ctx.pop("cancelamento_pendente", None)
```

**Depois:**
```python
ctx = await carregar_contexto_temporario(user_id, tenant_id=tenant_id) or {}
ctx.pop("cancelamento_pendente", None)
```

**Contexto:** Limpar contexto ao abortar cancelamento  
**tenant_id Disponível:** ✅ SIM  
**Fluxo Afetado:** Cancelamento abortado  
**Criticidade:** 🔴 P0 — Limpeza de estado crítico

---

### 4. services/gpt_executor.py:264

**Antes:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id) or {}
```

**Depois:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}
```

**Contexto:** Salvar estado de escolha de alternativa de profissional  
**tenant_id Disponível:** ✅ SIM (linha 215: `id_dono = await obter_id_dono(user_id)`)  
**Fluxo Afetado:** Agendamento com sugestão alternativa  
**Criticidade:** 🔴 P0 — Fluxo de agendamento

---

### 5. services/gpt_executor.py:329

**Antes:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id) or {}
```

**Depois:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}
```

**Contexto:** Resolver fora do expediente — salvar horário sugerido  
**tenant_id Disponível:** ✅ SIM  
**Fluxo Afetado:** Agendamento fora do expediente  
**Criticidade:** 🔴 P0 — Fluxo de agendamento

---

### 6. services/gpt_executor.py:437

**Antes:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id) or {}
```

**Depois:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}
```

**Contexto:** Salvar estado de escolha de horário em caso de conflito  
**tenant_id Disponível:** ✅ SIM (linha 407: `dono_id = await obter_id_dono(user_id)`)  
**Fluxo Afetado:** Agendamento com conflito  
**Criticidade:** 🔴 P0 — Fluxo crítico de agendamento

---

### 7. services/gpt_executor.py:496

**Antes:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id) or {}
contexto_tmp["estado_fluxo"] = "agendando"
```

**Depois:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}
contexto_tmp["estado_fluxo"] = "agendando"
```

**Contexto:** Salvar contexto sem conflito - confirmação  
**tenant_id Disponível:** ✅ SIM  
**Fluxo Afetado:** Agendamento confirmado  
**Criticidade:** 🔴 P0 — Fluxo crítico de agendamento

---

### 8. services/gpt_executor.py:557

**Antes:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id) or {}
servico_ctx = _extrair_servico_do_contexto(contexto_tmp)
```

**Depois:**
```python
contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}
servico_ctx = _extrair_servico_do_contexto(contexto_tmp)
```

**Contexto:** Criar evento - preferir contexto, se não existir, inferir do texto  
**tenant_id Disponível:** ✅ SIM (linha 554: `dono_id = await obter_id_dono(user_id)`)  
**Fluxo Afetado:** Criação de evento (confirmação final)  
**Criticidade:** 🔴 P0 — Fluxo crítico de agendamento

---

## 📊 Sumário de Patches

| # | Arquivo | Linha | Tipo | Função | Fluxo | Status |
|---|---------|-------|------|--------|-------|--------|
| 1 | handlers/bot.py | 248 | CARREGAR | Cancelamento pendente | Cancelamento | ✅ |
| 2 | handlers/bot.py | 289 | CARREGAR | Limpeza pós-cancelamento | Cancelamento | ✅ |
| 3 | handlers/bot.py | 306 | CARREGAR | Limpeza aborto | Cancelamento | ✅ |
| 4 | services/gpt_executor.py | 264 | CARREGAR | Alternativa profissional | Agendamento | ✅ |
| 5 | services/gpt_executor.py | 329 | CARREGAR | Fora do expediente | Agendamento | ✅ |
| 6 | services/gpt_executor.py | 437 | CARREGAR | Conflito/escolha | Agendamento | ✅ |
| 7 | services/gpt_executor.py | 496 | CARREGAR | Confirmação | Agendamento | ✅ |
| 8 | services/gpt_executor.py | 557 | CARREGAR | Criar evento | Agendamento | ✅ |

**Total de patches:** 8  
**Todos com tenant_id disponível:** ✅ SIM  
**Fluxos críticos cobertos:** ✅ SIM (Agendamento + Cancelamento)

---

## 🧪 Validação

### Antes do Patch
```
❌ [CTX_BLOQUEADO_SEM_TENANT] (linhas 248, 289, 306, ...)
❌ [CTX_SAVE_BLOQUEADO_SEM_TENANT] (se salvar sem tenant)
❌ Contexto retorna {} ou False (bloqueado)
```

### Depois do Patch
```
✅ Nenhum [CTX_BLOQUEADO_SEM_TENANT] esperado
✅ Nenhum [CTX_SAVE_BLOQUEADO_SEM_TENANT] esperado
✅ Contexto carregado normalmente
✅ Log contém: [LOAD CTX LEGADO] ou [CTX_LEGADO_COMPAT]
✅ Novo path em uso: Clientes/{tenant_id}/Sessoes/{actor_id}
```

---

## 🎯 Críterio de Aceite

Após executar fluxo real com mensagem:
```
"Quero corte com Bruna amanhã às 10"
```

**O log DEVE conter:**
- ✅ Nenhum `[CTX_BLOQUEADO_SEM_TENANT]`
- ✅ Nenhum `[CTX_SAVE_BLOQUEADO_SEM_TENANT]`
- ✅ Novo path: `Clientes/7394370553/Sessoes/7371670478`

**E PODE conter:**
- ✅ `[LOAD CTX LEGADO]` (compatibilidade em ação)
- ✅ `[CTX_LEGADO_COMPAT]` (guard validado)
- ✅ Sucesso na criação de evento

---

## 📝 Padrão de Correção Aplicado

Todas as 8 correções seguem o mesmo padrão:

```python
# ❌ ANTES
ctx = await carregar_contexto_temporario(user_id) or {}

# ✅ DEPOIS
ctx = await carregar_contexto_temporario(user_id, tenant_id=<tenant_id_var>) or {}
```

Onde `<tenant_id_var>` é uma das:
- `tenant_id` (de `await obter_id_dono(user_id)`)
- `id_dono` (de `await obter_id_dono(user_id)`)
- `dono_id` (de `await obter_id_dono(user_id)`)

Todos resolvidos com: `<var> = await obter_id_dono(user_id)`

---

## 🔍 Próximas Ocorrências (Não Críticas)

Ainda existem chamadas SEM tenant_id em:
- services/gpt_executor.py:630
- services/gpt_service.py (9 ocorrências)
- services/gpt_service(1).py (3 ocorrências)
- router/principal_router.py (3 ocorrências)
- router/principal_router_precheck_func.py (3 ocorrências)
- services/admin_command_service.py (3 ocorrências)

**Status:** Podem ser corrigidas em próxima sprint (não afetam fluxo de agendamento direto)

---

## ✅ Status Final

**Implementação:** ✅ COMPLETA (8 patches críticos)  
**Fluxos Críticos:** ✅ COBERTOS (Agendamento + Cancelamento)  
**Bloqueios Esperados:** ✅ ELIMINADOS (em fluxos críticos)  
**Validação Pendente:** ⏳ Teste real com "Quero corte com Bruna amanhã às 10"

---

## 📚 Referência

- **Patch P0 Original:** `docs/patches/PATCH_P0_BLOQUEIO_CONTEXTO_LEGADO.md`
- **Stack Traces Reais:** `docs/auditorias/STACKTRACE_CTX_SEM_TENANT_REAL.md`
- **Código-fonte:** 
  - `handlers/bot.py` (linhas 248, 289, 306)
  - `services/gpt_executor.py` (linhas 264, 329, 437, 496, 557)

---

**Conclusão:** Todos os fluxos críticos (agendamento, cancelamento) agora passam `tenant_id` ao chamar contexto. Nenhum bloqueio P0 é esperado em operação normal.
