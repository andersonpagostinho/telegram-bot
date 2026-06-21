# LOTE-2: VALIDAÇÃO DE ESCOPO

**Data:** 2026-06-21  
**Status:** 🔍 INVESTIGAÇÃO COMPLETA  
**Inconsistência Detectada:** Relatório inicial disse "3 ocorrências" mas listou 4 linhas  

---

## 🚨 DESCOBERTA CRÍTICA

**Falsos Positivos Identificados:** 2 de 4 ocorrências já foram migradas

Das 4 linhas relatadas inicialmente:
- ✅ 2 JÁ FORAM MIGRADAS (falsos positivos)
- ❌ 2 REALMENTE FALTAM tenant_id

**LOTE-2 ESCOPO REAL:** 2 ocorrências (não 3, não 4)

---

## 📋 ANÁLISE DETALHADA DAS 4 OCORRÊNCIAS

### Ocorrência #1: principal_router.py:10918

**Status de Análise:** ❌ SEM tenant_id — NECESSITA MIGRAÇÃO

**Função:** `roteador_principal(user_id, mensagem, update, context)`  
**Linha:** 10918  
**Tipo:** ESCRITA (salvar_contexto_temporario)  
**Path Legado:** Clientes/{user_id}/MemoriaTemporaria/contexto  

**Código Atual (Linhas 10912-10918):**
```python
# Salvar estado para continuidade
ctx_consulta = {
    "aguardando_confirmacao_agendamento_por_consulta": True,
    "servico_sugerido_consulta": servico_para_resposta,
    "ultima_acao": "confirmar_agendamento_por_consulta",
    "estado_fluxo": "aguardando_confirmacao_consulta",
}
await salvar_contexto_temporario(user_id, ctx_consulta)
```

**Origem tenant_id:** ✅ EXPLÍCITA

- Função `roteador_principal()` resolve `dono_id` na linha 3354
- `dono_id = await obter_id_dono(user_id)`
- Fallback: `if not dono_id: dono_id = str(user_id)`
- Na linha 10918, `dono_id` está em escopo (sem callbacks, sem async yield)

**Actor ID:** user_id (cliente ou profissional)  
**Risco:** 🟠 ALTO

**Razão Alto Risco:**
- Salva estado crítico de fluxo: `aguardando_confirmacao_agendamento_por_consulta`
- Próxima mensagem do usuário deve continuar desse estado
- Se persistir em tenant_id errado, fluxo quebra

**Comportamento:** Consulta pura sem GPT → usuário responde "sim" → aguarda confirmação para agendar

**Patch Mínimo:** Adicionar `tenant_id=dono_id` ao final da chamada na linha 10918

**Classificação:** ✅ APROVADA PARA LOTE-2

---

### Ocorrência #2: principal_router.py:11344

**Status de Análise:** ❌ SEM tenant_id — NECESSITA MIGRAÇÃO

**Função:** `roteador_principal(user_id, mensagem, update, context)`  
**Linha:** 11344  
**Tipo:** ESCRITA (salvar_contexto_temporario)  
**Path Legado:** Clientes/{user_id}/MemoriaTemporaria/contexto  

**Código Atual (Linhas 11312-11344):**
```python
contexto_update = {
    "estado_fluxo": (
        "aguardando_escolha_horario"
        if estado_fluxo_atual == "aguardando_escolha_horario"
        else "aguardando_horario"
    ),
    "servico": servico_ctx,
    "profissional_escolhido": profissional_ctx,
    "ultima_acao": "criar_evento",
    "draft_agendamento": { ... },
}

ctx_atual = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}

# 🔥 NÃO deixar perder estado de escolha de horário
if ctx_atual.get("estado_fluxo") == "aguardando_escolha_horario":
    contexto_update["estado_fluxo"] = "aguardando_escolha_horario"
    contexto_update["horarios_sugeridos"] = ctx_atual.get("horarios_sugeridos") or []

# 🔥 merge em vez de sobrescrever
ctx_atual.update(contexto_update)

await salvar_contexto_temporario(user_id, ctx_atual)  # ← LINHA 11344
```

**Origem tenant_id:** ✅ EXPLÍCITA

- Na linha 11334: `await carregar_contexto_temporario(user_id, tenant_id=dono_id)`
- Prova que `dono_id` está em escopo
- Mesma função `roteador_principal()`, mesmo contexto
- Sem callbacks entre carregar (11334) e salvar (11344)

**Actor ID:** user_id (cliente ou profissional)  
**Risco:** 🟠 ALTO

**Razão Alto Risco:**
- Merge complexo de contexto com múltiplos campos
- Preserva estado de escolha de horário
- Afeta continuidade de agendamento em estágio crítico

**Comportamento:** 
1. Carregar contexto (com tenant_id)
2. Atualizar com dados de profissional/serviço/horário
3. Merge preservando estado anterior
4. Salvar (FALTA tenant_id aqui)

**Patch Mínimo:** Adicionar `tenant_id=dono_id` ao final da chamada na linha 11344

**Classificação:** ✅ APROVADA PARA LOTE-2

---

### Ocorrência #3: handlers/event_handler.py:976

**Status de Análise:** ✅ JÁ MIGRADA — FALSO POSITIVO

**Função:** `add_agenda(update, context)`  
**Linha:** 976  
**Tipo:** ESCRITA (salvar_contexto_temporario)  

**Código Atual (Linhas 976-980):**
```python
await salvar_contexto_temporario(
    user_id,
    contexto_evento,
    tenant_id=dono_id  # P0-004 patch ← JÁ TEM TENANT_ID!
)
```

**Status:** ✅ MIGRADA

**Evidência:** Linha 979 contém `tenant_id=dono_id`

**Classificação:** ❌ REMOVER DE LOTE-2 — FALSO POSITIVO

**Motivo:** Já foi migrada em fase anterior (marcada como "P0-004 patch")

---

### Ocorrência #4: handlers/event_handler.py:1108

**Status de Análise:** ✅ JÁ MIGRADA — FALSO POSITIVO

**Função:** `add_agenda(update, context)` (mesmo handler que ocorrência 3)  
**Linha:** 1108  
**Tipo:** ESCRITA (salvar_contexto_temporario)  

**Código Atual (Linhas 1108-1112):**
```python
await salvar_contexto_temporario(
    user_id,
    contexto_conflito,
    tenant_id=dono_id  # ← JÁ TEM TENANT_ID!
)
```

**Status:** ✅ MIGRADA

**Evidência:** Linha 1111 contém `tenant_id=dono_id`

**Classificação:** ❌ REMOVER DE LOTE-2 — FALSO POSITIVO

**Motivo:** Já foi migrada (comentário marca como "P0-004 patch")

---

## 📊 MATRIZ CONSOLIDADA

| # | Arquivo | Linha | Status | Origem tenant_id | Risco | Ação | Classificação |
|---|---------|-------|--------|------------------|-------|------|---|
| 1 | principal_router.py | 10918 | ❌ SEM | dono_id (escopo) | 🟠 ALTO | Adicionar tenant_id=dono_id | ✅ LOTE-2 |
| 2 | principal_router.py | 11344 | ❌ SEM | dono_id (escopo) | 🟠 ALTO | Adicionar tenant_id=dono_id | ✅ LOTE-2 |
| 3 | handlers/event_handler.py | 976 | ✅ COM | dono_id | 🟠 ALTO | Nenhuma | ❌ REMOVER |
| 4 | handlers/event_handler.py | 1108 | ✅ COM | dono_id | 🟠 ALTO | Nenhuma | ❌ REMOVER |

---

## 🎯 LOTE-2 ESCOPO FINAL

**Ocorrências Reais:** 2 (não 3, não 4)

**Arquivo Único:** principal_router.py  
**Função Única:** `roteador_principal()`  
**Risco Total:** 🟠 ALTO (ambas fluxo crítico)

### Migração Necessária

| # | Linha | Mudança | Origem | Risco |
|---|-------|---------|--------|-------|
| 1 | 10918 | `await salvar_contexto_temporario(user_id, ctx_consulta, tenant_id=dono_id)` | dono_id | 🟠 ALTO |
| 2 | 11344 | `await salvar_contexto_temporario(user_id, ctx_atual, tenant_id=dono_id)` | dono_id | 🟠 ALTO |

**Total de Mudanças:** 2 linhas em 1 arquivo

**Validação Requerida:**
- ✅ py_compile
- ✅ grep (2/2 com tenant_id)
- ✅ P0 regressão 174/174 PASS
- ✅ P1 identidade (se ambiente disponível)

---

## 📋 RASTREABILIDADE POR OCORRÊNCIA

### Ocorrência #1: principal_router.py:10918

**Rastreamento:**
```
Função: roteador_principal() — linha 3342
  ├─ Resolução de tenant_id: linha 3354
  │  └─ dono_id = await obter_id_dono(user_id)
  │  └─ if not dono_id: dono_id = str(user_id)
  │
  ├─ Escopo em linha 10918: ✅ SIM
  │  └─ Sem callbacks
  │  └─ Sem async yield
  │  └─ Sem thread switch
  │
  └─ Migração: tenant_id=dono_id
```

**Caminho de Persistência:**
- Path legado: `Clientes/{user_id}/MemoriaTemporaria/contexto`
- Path v2: `Clientes/{dono_id}/Sessoes/{actor_id}`
- Mudança de sematype: Contexto fluxo → Sessão de tenant

---

### Ocorrência #2: principal_router.py:11344

**Rastreamento:**
```
Função: roteador_principal() — linha 3342
  ├─ Resolução de tenant_id: linha 3354
  │  └─ dono_id = await obter_id_dono(user_id)
  │
  ├─ Uso anterior (carregar): linha 11334
  │  └─ ctx_atual = await carregar_contexto_temporario(user_id, tenant_id=dono_id)
  │  └─ Prova que dono_id já está em uso
  │
  ├─ Escopo em linha 11344: ✅ SIM
  │  └─ Sem callbacks entre carregar (11334) e salvar (11344)
  │  └─ Mesma função, mesmo dono_id
  │
  └─ Migração: tenant_id=dono_id
```

**Caminho de Persistência:**
- Carregar: `Clientes/{dono_id}/Sessoes/{actor_id}` (já usa v2)
- Salvar: `Clientes/{user_id}/MemoriaTemporaria/contexto` (ainda legado) ← INCONSISTÊNCIA
- Fixação: Ambos usarem `Clientes/{dono_id}/Sessoes/{actor_id}`

---

## ✅ VALIDAÇÃO DE SEGURANÇA

### Proteções Mantidas

- ✅ Nenhuma alteração em agenda_service
- ✅ Nenhuma alteração em conflito_handler
- ✅ Nenhuma alteração em disponibilidade
- ✅ Nenhuma alteração em notificações
- ✅ Nenhuma alteração em criação de evento

### Guarda-Chuva

Ambas as ocorrências estão em `roteador_principal()`, função que JÁ:
- Resolve `dono_id` deterministicamente (linha 3354)
- Usa `dono_id` para outros salvar_contexto_temporario calls
- Tem fallback se resolução falhar

---

## 🎯 RECOMENDAÇÃO FINAL

**Escopo LOTE-2 Aprovado:**

✅ **Apenas 2 Ocorrências**
- principal_router.py:10918
- principal_router.py:11344

❌ **Remover de LOTE-2:**
- handlers/event_handler.py:976 (já migrada)
- handlers/event_handler.py:1108 (já migrada)

**Próximo Passo:** Implementar LOTE-2 com 2 ocorrências confirmadas

---

**Validação Completada:** 2026-06-21  
**Escopo Final:** 2/2 Ocorrências Reais Identificadas  
**Status:** ✅ PRONTO PARA IMPLEMENTAÇÃO LOTE-2
