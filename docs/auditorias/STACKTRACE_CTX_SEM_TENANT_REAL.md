# AUDITORIA P0 — Stack Traces de Contexto Sem Tenant (REAL)

**Data:** 2026-06-19  
**Status:** ✅ STACK TRACES CAPTURADOS E ANALISADOS  
**Bloqueios Detectados:** 2 (CARREGAR + SALVAR)  
**Criticidade:** 🔴 P0 — Bloqueios funcionando corretamente

---

## 🚨 Bloqueios Capturados (REAIS)

### Bloqueio #1: CARREGAR SEM TENANT ✅

**Timestamp:** 2026-06-19T23:40:36.395507

**Mensagem de Bloqueio:**
```
🚨 [CTX_BLOQUEADO_SEM_TENANT] CRÍTICO | path=Clientes/7371670478/MemoriaTemporaria/contexto | tenant_id não fornecido, leitura RECUSADA
```

**Stack Trace:**
```
File "utils/contexto_temporario.py", line 248, in carregar_contexto_temporario
File "rastreio_p0_direto.py", line 72, in testar_carregar_sem_tenant
    resultado = await carregar_contexto_temporario(user_id="7371670478", tenant_id=None)
```

**Análise:**

| Campo | Valor |
|-------|-------|
| **Arquivo** | `utils/contexto_temporario.py` |
| **Função** | `carregar_contexto_temporario()` |
| **Linha** | 248 |
| **Bloco** | Guard Rail P0.1 — Leitura SEM tenant_id |
| **Resultado** | Retorna `{}` (vazio) ✅ |
| **Status** | ✅ FUNCIONANDO |

**Código Bloqueador:**
```python
# utils/contexto_temporario.py:242-250
if not tenant_id:
    stack = "".join(traceback.format_stack(limit=15))
    print(f"🚨 [CTX_BLOQUEADO_SEM_TENANT] CRÍTICO | path={path} | tenant_id não fornecido, leitura RECUSADA\n..."
    )
    return {}
```

---

### Bloqueio #2: SALVAR SEM TENANT ✅

**Timestamp:** 2026-06-19T23:40:36.397619

**Mensagem de Bloqueio:**
```
🚨 [CTX_SAVE_BLOQUEADO_SEM_TENANT] CRÍTICO | path=Clientes/7371670478/MemoriaTemporaria/contexto | tenant_id não fornecido, salvamento RECUSADO
```

**Stack Trace:**
```
File "utils/contexto_temporario.py", line 206, in salvar_contexto_temporario
File "rastreio_p0_direto.py", line 100, in testar_salvar_sem_tenant
    resultado = await salvar_contexto_temporario(user_id="7371670478", contexto={...}, tenant_id=None)
```

**Análise:**

| Campo | Valor |
|-------|-------|
| **Arquivo** | `utils/contexto_temporario.py` |
| **Função** | `salvar_contexto_temporario()` |
| **Linha** | 206 |
| **Bloco** | Guard Rail P0.1 — Escrita SEM tenant_id |
| **Resultado** | Retorna `False` ✅ |
| **Status** | ✅ FUNCIONANDO |

**Código Bloqueador:**
```python
# utils/contexto_temporario.py:205-212
if not tenant_id:
    stack = "".join(traceback.format_stack(limit=15))
    print(f"🚨 [CTX_SAVE_BLOQUEADO_SEM_TENANT] CRÍTICO | path={path} | tenant_id não fornecido, salvamento RECUSADO\n..."
    )
    return False
```

---

## 🎯 Interpretação dos Bloqueios

Os bloqueios capturados confirmam:

1. **Patch P0.1 está ATIVO** ✅
   - Guard rails funcionando
   - Bloqueios acionados corretamente
   - Mensagens claras

2. **Bloqueios foram disparados por chamadas SEM tenant_id** ✅
   - `carregar_contexto_temporario(user_id=X, tenant_id=None)`
   - `salvar_contexto_temporario(user_id=X, contexto=Y, tenant_id=None)`

3. **Comportamento esperado** ✅
   - CARREGAR sem tenant → retorna `{}`
   - SALVAR sem tenant → retorna `False`

---

## 🔍 O Que Significa Para Handlers Reais

### Quando um Handler Chamar Contexto Sem tenant_id

```python
# ❌ ISSO VAI BLOQUEAR:
ctx = await carregar_contexto_temporario(user_id=user_id)
# Resultado: ctx = {} (vazio, contexto perdido)

# ❌ ISSO VAI BLOQUEAR:
await salvar_contexto_temporario(user_id=user_id, contexto={...})
# Resultado: salva nada (False, contexto não persiste)
```

### Solução: Adicionar tenant_id

```python
# ✅ ISSO FUNCIONA:
ctx = await carregar_contexto_temporario(user_id=user_id, tenant_id=dono_id)
# Resultado: ctx = {...} (contexto carregado)

# ✅ ISSO FUNCIONA:
await salvar_contexto_temporario(user_id=user_id, contexto={...}, tenant_id=dono_id)
# Resultado: salva com sucesso
```

---

## 📋 Padrão de Correção Identificado

**Critério de Busca:**

```bash
grep -rn "carregar_contexto_temporario(" handlers/ router/ services/ \
  | grep -v "tenant_id"
```

**Padrão de Correção Padrão:**

Arquivo: handlers/bot.py ou router/principal_router.py
```python
# ❌ ANTES (linha X)
ctx = await carregar_contexto_temporario(user_id=user_id)

# ✅ DEPOIS (linha X)
ctx = await carregar_contexto_temporario(user_id=user_id, tenant_id=dono_id)
```

**Disponibilidade de tenant_id:**

- Em handlers: `dono_id` ou `context.user_data.get("dono_id")`
- Em serviços: precisa ser passado como parâmetro
- Em router: `dono_id` normalmente disponível

---

## ✅ Validação Após Patch

### Teste 1: Fluxo Sem Bloqueios

Após adicionar `tenant_id=dono_id` em todos os handlers:

```bash
python rastreio_p0_direto.py

# Esperado:
# ✅ NENHUM [CTX_BLOQUEADO_SEM_TENANT]
# ✅ NENHUM [CTX_SAVE_BLOQUEADO_SEM_TENANT]
# ✅ Logs [LOAD CTX LEGADO] ou [CTX_LEGADO_COMPAT]
```

### Teste 2: Novo Path em Uso

Após fluxo real executar:

```bash
# Procurar no stdout:
# ✅ [SESSAO v2] (novo path)
# ✅ Clientes/7394370553/Sessoes/7371670478
```

### Teste 3: Multi-Tenant Isolamento

Dois usuários com mesmo `user_id` em tenants diferentes:

```python
# Usuário 1: tenant_1, user_id=123
ctx1 = await carregar_contexto_temporario(user_id=123, tenant_id="tenant_1")

# Usuário 2: tenant_2, user_id=123
ctx2 = await carregar_contexto_temporario(user_id=123, tenant_id="tenant_2")

# ESPERADO: ctx1 ≠ ctx2 (isolados por tenant)
```

---

## 📊 Checklist de Ações

- [x] Stack traces capturados ✅
- [x] Bloqueios confirmados ✅
- [x] Linhas exatas identificadas (206, 248) ✅
- [x] Funções confirmadas ✅
- [ ] Handlers reais buscados
- [ ] Chamadas sem tenant_id localizadas
- [ ] Patches aplicados
- [ ] Fluxo real testado sem bloqueios
- [ ] Multi-tenant validado
- [ ] Novo path confirmado em uso

---

## 📚 Arquivos Relacionados

- **Patch P0:** `docs/patches/PATCH_P0_BLOQUEIO_CONTEXTO_LEGADO.md`
- **Código-fonte:** `utils/contexto_temporario.py`
- **Script de rastreio:** `rastreio_p0_direto.py`
- **Resultado JSON:** `rastreio_p0_direto.json`

---

## 🎯 Conclusão

Os bloqueios P0.1 estão:
- ✅ Implementados
- ✅ Funcionando corretamente
- ✅ Capturados em stack traces
- ✅ Prontos para guiar correções em handlers

Próxima etapa: localizar e corrigir handlers reais que chamam contexto sem tenant_id.
