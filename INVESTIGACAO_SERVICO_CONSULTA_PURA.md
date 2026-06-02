# 🔍 INVESTIGAÇÃO - Onde ctx["servico"] é Preenchido em Consulta Pura

**Data:** 31 Maio 2026  
**Objetivo:** Rastrear fluxo de preenchimento de ctx["servico"] após consulta pura

---

## 📍 Localizações Encontradas

Foram encontradas **3 atribuições** principais a `ctx["servico"]` após `extrair_slots_e_mesclar()`:

| Linha | Local | Código |
|-------|-------|--------|
| **8126** | AUTO-PROFISSIONAL | `ctx["servico"] = servico_auto` |
| **8265** | AUTO-PROFISSIONAL (incremental) | `ctx["servico"] = draft_inc.get("servico")` |
| **8569** | Fora do expediente | `ctx["servico"] = servico_check` |

---

## 🎯 Causa Raiz Identificada

### Fluxo Problemático

**Etapa 1: extrair_slots_e_mesclar() (linhas 1058-1464)**

```python
# Linhas 1136-1150
if servico_detectado:
    eh_consulta_pura_servico = (
        ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
        or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
    )

    if eh_consulta_pura_servico:
        print("[CONSULTA PURA] serviço detectado, mas não entra em ctx['servico']")
        # ✅ NÃO PREENCHE ctx["servico"]
    else:
        ctx["servico"] = servico_detectado  # Linha 1149
        draft["servico"] = servico_detectado  # Linha 1150
```

**Status:** ✅ Proteção FUNCIONA - `ctx["servico"]` não é preenchido para consultas puras

---

**Etapa 2: Após extrair_slots_e_mesclar() (linha 8020)**

```python
# Linhas 8026-8036
draft_auto = ctx.get("draft_agendamento") or {}

data_hora_auto = (
    ctx.get("data_hora")
    or draft_auto.get("data_hora")
)

servico_auto = (
    ctx.get("servico")              # ← Será None (bloqueado pela proteção)
    or draft_auto.get("servico")    # ← MAS isto pode ter valor antigo!
)
```

**Problema:** Se `draft_agendamento` tem um `servico` de uma ação anterior:
- `ctx.get("servico")` = None (proteção em consulta pura)
- `draft_auto.get("servico")` = "Escova" (valor antigo do draft)
- Resultado: `servico_auto` = "Escova" ❌

---

**Etapa 3: Atribuição em AUTO-PROFISSIONAL (linha 8126)**

```python
if (
    not eh_consulta_pura           # ← Verifica NOVAMENTE aqui
    and data_hora_auto
    and tem_hora_real(data_hora_auto)
    and servico_auto               # ← Tem valor! (do draft antigo)
    and not prof_auto
    and ctx.get("profissional_indiferente")
):
    # ...
    ctx["servico"] = servico_auto  # Linha 8126 - AQUI PREENCHE
```

**Resultado:** `ctx["servico"]` é preenchido com o valor antigo do draft, convertendo consulta pura em agendamento ❌

---

## 🔄 Fluxo Completo - Caso "vocês fazem escova?"

```
[1] Usuário escreve: "vocês fazem escova?"
    ↓
[2] Motor detecta: "objetivo_conversacional" = "consultar_disponibilidade_por_servico"
    ↓
[3] extrair_slots_e_mesclar():
    - Detecta: servico_detectado = "Escova"
    - Verifica: eh_consulta_pura_servico = TRUE
    - Ação: NÃO PREENCHE ctx["servico"]
    ✅ ctx["servico"] = None (proteção ativa)
    ↓
[4] Após extrair_slots_e_mesclar():
    - servico_auto = ctx.get("servico") or draft_auto.get("servico")
    - ctx.get("servico") = None
    - draft_auto.get("servico") = "Escova" (valor antigo do draft)
    ❌ servico_auto = "Escova"
    ↓
[5] AUTO-PROFISSIONAL (linha 8064-8126):
    - Verifica: eh_consulta_pura (baseado em objetivo_conversacional)
    - MAS também verifica: if (not eh_consulta_pura and ... and servico_auto)
    - servico_auto tem valor → Condição passa!
    - Executa: ctx["servico"] = servico_auto = "Escova"
    ❌ AQUI ACONTECE A CONTAMINAÇÃO
    ↓
[6] Resultado:
    ✅ Objetivo ainda é "consultar_disponibilidade_por_servico"
    ✅ Intenção ainda é "consulta_disponibilidade_servico"
    ❌ MAS ctx["servico"] = "Escova" (CONTAMINADO)
    ↓
[7] Bot interpreta como:
    "O usuário quer agendar Escova com horário/profissional automático"
    Resposta: "Qual dia e horário?"
    ❌ INCORRETO - Deveria ser apenas consulta!
```

---

## ⚠️ O Verdadeiro Problema

### Não é simplesmente "ctx["servico"] está sendo preenchido"

É que **`draft_agendamento` contém um `servico` antigo** que:

1. ✅ Não entra em `ctx["servico"]` inicialmente (proteção em 1149)
2. ❌ MAS entra em `servico_auto` via fallback (linha 8035)
3. ❌ E depois retorna para `ctx["servico"]` (linha 8126)

### Fluxo de Contaminação

```
draft_agendamento["servico"] = "Escova"  [valor antigo]
         ↓
    servico_auto = ... or draft_auto.get("servico")
         ↓
    servico_auto = "Escova"  [restaurado do draft]
         ↓
    ctx["servico"] = servico_auto
         ↓
    ctx["servico"] = "Escova"  [RECONTAMINADO]
```

---

## 🔧 Soluções Possíveis

### Solução 1: Bloquear em AUTO-PROFISSIONAL (Recomendado)

**Localização:** Linha 8064-8071

**Mudança:**
```python
# ANTES:
if (
    not eh_consulta_pura
    and data_hora_auto
    and tem_hora_real(data_hora_auto)
    and servico_auto  # ← Problema: pode vir do draft antigo
    and not prof_auto
    and ctx.get("profissional_indiferente")
):

# DEPOIS - REMOVER servico_auto SE for consulta pura:
if (
    not eh_consulta_pura
    and data_hora_auto
    and tem_hora_real(data_hora_auto)
    and servico_auto
    and not prof_auto
    and ctx.get("profissional_indiferente")
):
    # Bloquear entrada de servico se é consulta pura
    if eh_consulta_pura:
        print("[BLOQUEADO] Consulta pura não pode usar servico_auto do draft")
        servico_auto = None  # ← Anular o valor contaminado
```

---

### Solução 2: Limpar draft após Consulta Pura (Preventivo)

**Localização:** Após proteção em `extrair_slots_e_mesclar()` (linha 1150)

**Mudança:**
```python
if eh_consulta_pura_servico:
    print("[CONSULTA PURA] serviço detectado, mas não entra...")
    # Limpar draft para evitar reutilização
    if draft.get("servico") == servico_detectado:
        draft.pop("servico", None)  # ← Remove para não contaminar depois
```

---

### Solução 3: Verificar Objetivo em servico_auto (Completa)

**Localização:** Linha 8033-8036

**Mudança:**
```python
eh_consulta_pura = (
    ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
    or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
)

servico_auto = None  # ← Inicializar como None
if not eh_consulta_pura:
    servico_auto = (
        ctx.get("servico")
        or draft_auto.get("servico")
    )
```

---

## 📊 Tabela de Decisão

| Cenário | eh_consulta_pura | servico_auto | Ação |
|---------|-----------------|-------------|------|
| Consulta: "escova?" | TRUE | "Escova" | ❌ Deve ser None |
| Agendamento: "dia?" | FALSE | "Escova" | ✅ Mantém |
| Sem draft prévio | FALSE | None | ✅ Perguntar serviço |
| Draft + Consulta | TRUE | "Escova" | ❌ Deve ser None |

---

## ✅ Recomendação

**Implementar Solução 1:**
- Mais localizável
- Menos efeitos colaterais
- Mais fácil de debugar

**Código:**
```python
# Linha ~8068 - DENTRO do bloco if
if not eh_consulta_pura:
    # Seguro: servico_auto é usado
    ...
else:
    # Consulta pura: anular servico_auto
    servico_auto = None
```

---

## 🔍 Evidência do Bug

**Caso reportado:**
- Entrada: "vocês fazem escova?"
- Draft anterior: {"servico": "Escova"}
- `objetivo_conversacional`: "consultar_disponibilidade_por_servico"
- **Resultado esperado:** Apenas listar horários disponíveis
- **Resultado real:** "Qual dia e horário?" (agendamento)

**Motivo:**
1. ✅ Objetivo é detectado corretamente (consulta)
2. ✅ ctx["servico"] é bloqueado corretamente (None)
3. ❌ MAS draft_auto["servico"] contamina servico_auto
4. ❌ E linha 8126 restaura ctx["servico"] = "Escova"
5. ❌ Bot interpreta como agendamento (tem serviço + sem profissional)

---

**Conclusão:** O problema é a **reutilização de draft antigo após consulta pura ser detectada**.

O `draft_agendamento` deveria ser IGNORADO (ou LIMPO) quando é consulta pura.
