# LOCALIZAÇÃO — MENSAGEM DE CONFLITO CORRETA

**Data:** 2026-06-19  
**Status:** 🟢 ENCONTRADA — Mensagem correta está no código!  
**Local:** `router/principal_router.py:4920-4935`

---

## ✅ MENSAGEM CORRETA ENCONTRADA

**Arquivo:** `router/principal_router.py`  
**Linhas:** 4920-4935  
**Status:** FUNCIONA CORRETAMENTE

```python
msg = (
    f"⛔ A *{profissional_escolhido}* já tem atendimento às *{hora_ref}* nesse dia.\n\n"
)

if sugestoes:
    msg += f"✅ Estes horários estão livres com a *{profissional_escolhido}* no mesmo dia:\n"
    for s in sugestoes[:3]:
        msg += f"🔄 {s}\n"

if alternativas:
    msg += (
        f"\n💡 Se você quiser manter *{hora_ref}*, estas profissionais fazem "
        f"*{servico_slot}* e estão disponíveis: *{', '.join(alternativas)}*.\n"
    )

msg += "\nDeseja escolher outro horário com essa profissional ou prefere uma das alternativas?"
```

---

## 📊 RESULTADO AO USUÁRIO

```
⛔ A Joana já tem atendimento às 09:00 nesse dia.

✅ Estes horários estão livres com a Joana no mesmo dia:
🔄 09:20 - 09:50
🔄 08:30 - 09:00
🔄 09:50 - 10:20

💡 Se você quiser manter 09:00, estas profissionais fazem corte e estão disponíveis: Bruna, Gloria.

Deseja escolher outro horário com essa profissional ou prefere uma das alternativas?
```

---

## 📍 ONDE ESTÁ EM OUTROS LUGARES

A mesma mensagem (ou variações) também está em:

| Local | Arquivo | Linhas | Status |
|-------|---------|--------|--------|
| **router/principal_router.py** | router/principal_router.py | 4920-4935 | ✅ **CORRETO** |
| event_handler.py | handlers/event_handler.py | 361-366 | ✅ **Parcial** |
| router/principal_router.py | router/principal_router.py | 5108 | ✅ Variação |
| router/principal_router.py | router/principal_router.py | 5350 | ✅ Variação |
| router/principal_router.py | router/principal_router.py | 6111 | ✅ Variação |
| gpt_executor.py | services/gpt_executor.py | 490 | ✅ Variação |

---

## 🎯 ESTRUTURA EXATA DA MENSAGEM

### 1️⃣ Linha 1: Conflito específico com hora
```python
f"⛔ A *{profissional_escolhido}* já tem atendimento às *{hora_ref}* nesse dia.\n\n"
```

### 2️⃣ Linhas 2-4: Sugestões com duração
```python
if sugestoes:
    msg += f"✅ Estes horários estão livres com a *{profissional_escolhido}* no mesmo dia:\n"
    for s in sugestoes[:3]:
        msg += f"🔄 {s}\n"
```

**Nota:** A variável `sugestoes` já contém a duração formatada (ex: "09:20 - 09:50")

### 3️⃣ Linhas 5-6: Opção de manter hora original
```python
if alternativas:
    msg += (
        f"\n💡 Se você quiser manter *{hora_ref}*, estas profissionais fazem "
        f"*{servico_slot}* e estão disponíveis: *{', '.join(alternativas)}*.\n"
    )
```

### 4️⃣ Linha 7: Pergunta clara
```python
msg += "\nDeseja escolher outro horário com essa profissional ou prefere uma das alternativas?"
```

---

## ❌ ONDE ESTÁ ERRADO

**Arquivo:** `handlers/event_handler.py`  
**Linhas:** 1008-1023 (PATCH P0 novo)  
**Status:** ❌ GENÉRICO

```python
prof_display = profissional or "profissional"
resposta = f"❌ A *{prof_display}* não tem esse horário disponível.\n\n"
```

**Problema:** Usa mensagem genérica em vez de reutilizar formato correto

---

## ✅ SOLUÇÃO

O código **já tem a mensagem correta** em `router/principal_router.py:4920-4935`.

**O PATCH P0 deveria:**
1. ❌ NÃO usar mensagem genérica (linha 1008)
2. ✅ REUTILIZAR a estrutura correta de `router/principal_router.py:4920-4935`

---

## 🔍 VARIÁVEIS NECESSÁRIAS

Para implementar a mensagem correta, precisa de:

| Variável | Valor | Fonte |
|----------|-------|-------|
| `profissional_escolhido` | "Joana" | evento_data.get("profissional") |
| `hora_ref` | "09:00" | evento_data.get("hora_inicio") |
| `sugestoes` | ["09:20 - 09:50", "08:30 - 09:00", ...] | conflito_info.get("sugestoes") |
| `servico_slot` | "corte" | evento_data.get("servico") |
| `alternativas` | ["Bruna", "Gloria"] | conflito_info.get("profissional_alternativo") |

---

## 📋 CHECKLIST PARA CORRIGIR

- [ ] Mudar arquivo: `handlers/event_handler.py:1008-1023`
- [ ] Remover mensagem genérica (❌ A [...] não tem esse horário)
- [ ] Implementar estrutura de `router/principal_router.py:4920-4935`
- [ ] Testar com dados reais
- [ ] Validar que duração dos horários aparece

---

## 🎯 REFERÊNCIA RÁPIDA

**✅ Mensagem correta (funciona):**
- Arquivo: `router/principal_router.py:4920-4935`
- Estrutura: 4 partes (conflito + sugestões + alternativas + pergunta)
- Duração: incluída nos horários
- Ícones: ⛔ 💡 🔄 ✅

**❌ Mensagem errada (PATCH P0):**
- Arquivo: `handlers/event_handler.py:1008-1023`
- Estrutura: genérica
- Duração: ausente
- Ícones: ❌

---

**Recomendação:** Quando implementar o PATCH P0, copiar a estrutura de `router/principal_router.py:4920-4935` que já funciona corretamente.

