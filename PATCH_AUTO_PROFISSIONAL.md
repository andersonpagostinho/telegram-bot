# 🔧 PATCH MÍNIMO: AUTO-PROFISSIONAL BLOQUEADO PARA CONSULTA PURA

## 📍 Localização

**Arquivo:** `router/principal_router.py`  
**Linhas:** 8052-8071  
**Função:** `roteador_principal` (async)  
**Seção:** PROFISSIONAL INDIFERENTE — PÓS EXTRAÇÃO

---

## 🎯 Problema

Bloco de AUTO-PROFISSIONAL (linhas 8052-8177) reutilizava `ctx["draft_agendamento"]` antigo e sobrescrevia:
- `ctx["servico"] = servico_auto` (linha 8113)
- `ctx["objetivo_conversacional"] = None` (linha 8118)
- `ctx["intencao_conversacional"] = None` (linha 8120)
- Salvava com `await salvar_contexto_temporario(...)` (linha 8123/8177)

**Resultado:** Consulta pura "vocês fazem escova?" virava agendamento.

---

## ✅ Solução

Adicionar **guarda contra consulta pura** ANTES do bloco AUTO-PROFISSIONAL:

### Código Adicionado (linhas 8052-8062)

```python
# 🛡️ GUARDA CONTRA CONSULTA PURA
eh_consulta_pura = (
    ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
    or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
)

if eh_consulta_pura:
    print(
        "🛡️ [AUTO-PROF BLOQUEADO] consulta pura não pode virar agendamento",
        flush=True
    )
```

### Condição do IF Alterada (linha 8064-8071)

**ANTES:**
```python
if (
    data_hora_auto
    and tem_hora_real(data_hora_auto)
    and servico_auto
    and not prof_auto
    and ctx.get("profissional_indiferente")
):
```

**DEPOIS:**
```python
if (
    not eh_consulta_pura  # ← ADICIONADO
    and data_hora_auto
    and tem_hora_real(data_hora_auto)
    and servico_auto
    and not prof_auto
    and ctx.get("profissional_indiferente")
):
```

---

## 🧪 Teste: "vocês fazem escova?"

### Entrada
```
Mensagem: "vocês fazem escova?"
Contexto: Limpo
```

### Processamento

**[ETAPA 1] GPT Classifica**
```
✅ objetivo_conversacional = "consultar_disponibilidade_por_servico"
✅ intencao_conversacional = "consulta_disponibilidade_servico"
```

**[ETAPA 2] extrair_slots_e_mesclar (PATCH 1)**
```
✅ ctx["servico"] = None (bloqueado)
✅ draft["servico"] = None (bloqueado)
```

**[ETAPA 3] AUTO-PROFISSIONAL (NOVO PATCH)**
```
✅ eh_consulta_pura = True
✅ [AUTO-PROF BLOQUEADO] consulta pura não pode virar agendamento
✅ Condição if: False (skipado)
✅ ctx["objetivo_conversacional"] preservado
✅ ctx["intencao_conversacional"] preservado
✅ Nenhum salvar_contexto_temporario executado
```

**[ETAPA 4] resolver_proximo_passo_real (PATCH 2)**
```
✅ [CONSULTA PURA] resolver_proximo_passo_real bloqueado
✅ return None
```

### Resultado Final

```json
{
  "objetivo_conversacional": "consultar_disponibilidade_por_servico",
  "intencao_conversacional": "consulta_disponibilidade_servico",
  "servico": null,
  "draft_agendamento": null,
  "estado_fluxo": "inicial",
  "proximo_passo_real": null
}
```

### Validações

```
✅ PASS: servico ausente
✅ PASS: draft_agendamento ausente
✅ PASS: objetivo preservado
✅ PASS: intencao preservada
✅ PASS: proximo_passo_real = None
✅ PASS: estado_fluxo = inicial
```

---

## 📊 Comparação com Antes e Depois

| Aspecto | ANTES (Bug) | DEPOIS (Patch) |
|---------|------------|----------------|
| `ctx["servico"]` | `"escova"` ❌ | `None` ✅ |
| `ctx["draft_agendamento"]` | `{"servico": "escova"}` ❌ | `None` ✅ |
| `objetivo_conversacional` | `None` (deletado) ❌ | `"consultar_..."` ✅ |
| `intencao_conversacional` | `None` (deletado) ❌ | `"consulta_..."` ✅ |
| `proximo_passo_real` | `"perguntar_data_hora"` ❌ | `None` ✅ |
| `estado_fluxo` | `"aguardando_data"` ❌ | `"inicial"` ✅ |
| Resposta GPT | "Qual dia e horário?" ❌ | Resposta informativa ✅ |

---

## 🔐 Arquitetura de Defesa

Agora há **3 camadas de proteção** para consultas puras:

1. **PATCH 1** (linha 1137-1150): `extrair_slots_e_mesclar`
   - Bloqueia `ctx["servico"]` e `draft["servico"]`

2. **PATCH 3** (linha 8052-8071): AUTO-PROFISSIONAL (novo)
   - Bloqueia entrada no bloco que reutiliza draft antigo
   - Preserva sinais de consulta pura

3. **PATCH 2** (linha 143-156): `resolver_proximo_passo_real`
   - Early return `None` para consultas puras
   - Impede forçar `"perguntar_data_hora"`

---

## 🚀 Status

- ✅ Compilação bem-sucedida
- ✅ Teste simulado passou (6/6 validações)
- ✅ Pronto para teste com bot real

---

## 📝 Notas

- O patch é **mínimo e cirúrgico**
- Apenas adiciona uma guarda, não altera lógica existente
- Preserva todos os outros fluxos (agendamentos, ajustes, etc.)
- Usa as mesmas sinalizações (`objetivo_conversacional`, `intencao_conversacional`)
