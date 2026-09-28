# C3.15.3-D-C-A — DIAGNÓSTICO: E2E FALHA — cliente_id Perdido

**Data:** 2026-09-27  
**Status:** 🔴 BLOQUEADO — Causa raiz identificada  
**Mensagem de Entrada:** "quero corte amanha"  

---

## 🔴 ERRO OBSERVADO

```
[ACTOR_CANONICO] actor_id=whatsapp:5511991382080 ✅
[LOAD SESSAO v2] path=Clientes/7394370553/Sessoes/whatsapp:5511991382080 ✅

[slots] Falha ao extrair/mesclar slots: tenant_id é obrigatório para salvar sessão 🔴

[WA] Erro no roteador: tenant_id é obrigatório para carregar sessão 🔴
```

---

## 🎯 CAUSA RAIZ IDENTIFICADA

### Problema Crítico

**`cliente_id` é definido APENAS em `roteador_principal()` linha 3417**

```python
# router/principal_router.py:3417 (ÚNICO local onde cliente_id é definido)
cliente_id = actor_id_whatsapp or user_id
```

**MAS é usado em 157 locais:**
```
157 ocorrências de: salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
```

### Contexto do Problema

| Tipo | Quantidade | Localização | Acesso a cliente_id |
|------|-----------|-------------|-------------------|
| **roteador_principal()** | ~50+ | principal_router.py:3373+ | ✅ SIM (definido na linha 3417) |
| **Funções secundárias** | ~100+ | precheck_e_confirmacao, resolver_alteracao, etc. | ❌ NÃO |
| **Handlers/Services** | ~7 | Fora de roteador_principal | ❌ NÃO |

---

## 📍 PRIMEIRO PONTO ONDE cliente_id É PERDIDO

### Localização: router/principal_router.py:1789

**Função:** `precheck_e_confirmacao_agendamento()`

```python
async def precheck_e_confirmacao_agendamento(
    context,
    user_id: str,
    ctx: dict,
    servico: str,
    prof: str,
    data_hora: datetime,
    dono_id: str,  # ← tem tenant_id
    # ❌ NÃO recebe cliente_id
):
```

**Problema:** Recebe `dono_id` mas NÃO recebe `cliente_id`

**Onde é chamada:**  
router/principal_router.py:3862-3870 (de dentro de `roteador_principal()`)

```python
return await precheck_e_confirmacao_agendamento(
    context=context,
    user_id=user_id,  # ← apenas user_id
    ctx=ctx,
    servico=servico_ctx,
    prof=profissional_detectado,
    data_hora=data_hora_ctx,
    dono_id=dono_id_slot,
    # ❌ cliente_id NÃO é passado aqui
)
```

**O que tenta fazer:**  
Na linha ~1828-2122 (dentro de precheck_e_confirmacao_agendamento):

```python
await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
                                            ↑
                            NameError: cliente_id não está definido
```

---

## 📍 SEGUNDO PONTO ONDE actor_id É TROCADO

### Localização: router/principal_router.py:1197

**Função:** `extrair_slots_e_mesclar()`

```python
async def extrair_slots_e_mesclar(ctx: dict, texto_usuario: str, dono_id: str) -> dict:
```

**Problema:**
- Recebe: `ctx`, `texto_usuario`, `dono_id`
- ❌ NÃO recebe `cliente_id` ou `actor_id`
- Retorna: modificado `ctx`
- Quando salvado depois, usa `user_id` em vez de `actor_id`

**Onde é chamada:**  
router/principal_router.py:7568, 9836 (de dentro de `roteador_principal()`)

```python
ctx = await extrair_slots_e_mesclar(ctx, texto_usuario, dono_id)
#    não passa cliente_id aqui
```

---

## 🔗 CADEIA DE CHAMADAS ATÉ O ERRO

```
roteador_principal(tenant_id=7394370553)
    ↓ (linha 3417)
    cliente_id = actor_id_whatsapp or user_id
                 "whatsapp:5511991382080"
    
    ↓ (linha 7568, intencao_conversacional=agendamento_direto)
    ctx = await extrair_slots_e_mesclar(ctx, texto_usuario, dono_id)
          ❌ cliente_id NÃO é passado
    
    ↓ (linha 7645, após extrair_slots_e_mesclar)
    await salvar_contexto_temporario_v2(dono_id, cliente_id, ctx)
                                                ↑
                            NameError: cliente_id is not defined
                                        (dentro do except que captura como "Falha ao extrair/mesclar")
    
    ↓ (erro catched)
    except Exception as e:
        print(" [slots] Falha ao extrair/mesclar slots:", e, flush=True)
```

---

## 📋 LISTA DE ARQUIVOS/LINHAS AFETADAS

### PARTE A: Funções que recebem `dono_id` mas NÃO `cliente_id`

| Arquivo | Linha | Função | Recebe | Falta |
|---------|-------|--------|--------|-------|
| principal_router.py | 1789 | `precheck_e_confirmacao_agendamento()` | dono_id | ❌ cliente_id |
| principal_router.py | 1197 | `extrair_slots_e_mesclar()` | dono_id | ❌ cliente_id |
| principal_router.py | 2127 | `detectar_alteracao_draft_agendamento()` | dono_id | ❌ cliente_id |
| principal_router.py | 2282 | `resolver_alteracao_draft_agendamento()` | dono_id | ❌ cliente_id |
| principal_router.py | 3182 | `buscar_horario_ajuste_no_dia()` | dono_id | ❌ cliente_id |

### PARTE B: Chamadas dentro de `roteador_principal()` que NÃO passam `cliente_id`

| Linha | Função chamada | Passa cliente_id? |
|-------|----------------|-----------------|
| 3862 | precheck_e_confirmacao_agendamento() | ❌ NÃO |
| 7568 | extrair_slots_e_mesclar() | ❌ NÃO |
| 8805 | precheck_e_confirmacao_agendamento() | ❌ NÃO |
| 9836 | extrair_slots_e_mesclar() | ❌ NÃO |

### PARTE C: Locais onde `salvar_contexto_temporario_v2(dono_id, cliente_id, ...)` falha

**Todas as 157 ocorrências em funções que NÃO recebem `cliente_id`:**

- Em `precheck_e_confirmacao_agendamento()`: linhas 1828, 1869, 1933, 2031, 2122, 2330, 2361, 2383, 2404, 2469, etc.
- Em `detectar_alteracao_draft_agendamento()`: linhas ~2600+
- Em `resolver_alteracao_draft_agendamento()`: linhas ~2700+
- Em blocos try-except de `extrair_slots_e_mesclar()`: linhas ~7645

---

## 📍 MENOR PONTO ARQUITETURAL PARA CORREÇÃO

### Opção 1: Passar `cliente_id` como parâmetro

**Alterar ASSINATURA de cada função que usa `salvar_contexto_temporario_v2()`:**

```python
# ANTES
async def precheck_e_confirmacao_agendamento(
    context, user_id, ctx, servico, prof, data_hora, dono_id
):

# DEPOIS
async def precheck_e_confirmacao_agendamento(
    context, user_id, ctx, servico, prof, data_hora, dono_id, cliente_id
):
```

**Alterar TODAS as chamadas para passar `cliente_id`:**

```python
# ANTES (linha 3862)
return await precheck_e_confirmacao_agendamento(
    context=context,
    user_id=user_id,
    ...
    dono_id=dono_id_slot,
)

# DEPOIS
return await precheck_e_confirmacao_agendamento(
    context=context,
    user_id=user_id,
    ...
    dono_id=dono_id_slot,
    cliente_id=cliente_id,  # ← ADICIONADO
)
```

**Impacto:**
- ~5 funções a modificar (assinatura)
- ~4-10 chamadas a modificar (passar parâmetro)
- ~157 locais usarão `cliente_id` corretamente

### Opção 2: Derivar `cliente_id` localmente (NÃO RECOMENDADO)

Cada função recalcularía `cliente_id = actor_id_whatsapp or user_id`, mas `actor_id_whatsapp` não está disponível fora de `roteador_principal()`.

**❌ INVIÁVEL** — actor_id_whatsapp é local ao roteador

---

## 📊 RESUMO DO DIAGNÓSTICO

| Métrica | Valor |
|---------|-------|
| **Primeira perda de cliente_id** | Linha 1789: `precheck_e_confirmacao_agendamento()` não recebe parâmetro |
| **Primeira troca actor_id→user_id** | Linha 1197: `extrair_slots_e_mesclar()` não recebe cliente_id |
| **Locais que falham** | 157 chamadas a `salvar_contexto_temporario_v2()` |
| **Funções afetadas** | 5 principais + 100+ callsites dentro delas |
| **Arquivos afetados** | router/principal_router.py APENAS |
| **Tipo de problema** | Falta de propagação de parâmetro `cliente_id` |
| **Solução mínima** | Adicionar `cliente_id` a 5 assinaturas de função |

---

## 🛑 STATUS

**🔴 BLOQUEADO** — Implementação D-B foi incompleta

A substituição global de `user_id` por `cliente_id` nas chamadas de `salvar_contexto_temporario_v2()` foi feita, MAS `cliente_id` não foi propagado como parâmetro às funções que o usam.

Resultado: NameError em 157 locais quando essas funções tentam usar `cliente_id`.

---

**Próximo passo:** D-C-B — Implementar propagação de `cliente_id` como parâmetro

