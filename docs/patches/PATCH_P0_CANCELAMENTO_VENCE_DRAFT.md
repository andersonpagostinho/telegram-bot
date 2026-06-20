# PATCH P0 — Cancelamento Vence Qualquer Draft de Agendamento

**Data:** 2026-06-19  
**Status:** ✅ IMPLEMENTADO E VALIDADO  
**Critério:** Mensagem com cancelamento nunca gera confirmação de agendamento

---

## 🎯 Regra Crítica

**CANCELAMENTO > AGENDAMENTO**

Se usuário está em fluxo de agendamento (estado "agendando") e muda de ideia para cancelar:

### ❌ ANTES (Comportamento Errado)
```
Estado: agendando
Draft: corte com Bruna amanhã 10h
Mensagem: "Quero cancelar com a Bruna amanhã"

Resultado: "Confirmando: corte com Bruna às 10h. Certo?"
PROBLEMA: Ignora intenção de cancelamento, tenta confirmar agendamento
```

### ✅ DEPOIS (Comportamento Correto)
```
Estado: agendando
Draft: corte com Bruna amanhã 10h
Mensagem: "Quero cancelar com a Bruna amanhã"

Resultado: "Tem certeza de cancelar o corte?"
CORRETO: Detecta cancelamento, limpa draft, processa cancelamento
```

---

## 🔧 Implementação

### Arquivo: router/principal_router.py (Linhas ~3810-3825)

**Antes:**
```python
features = class_ctx.get("features", {})
tem_cancelamento = features.get("tem_cancelamento", False)

if tem_cancelamento and (not ctx.get("estado_fluxo") or ctx.get("estado_fluxo") == "idle"):
    # Processar cancelamento
```

**Depois:**
```python
features = class_ctx.get("features", {})
tem_cancelamento = features.get("tem_cancelamento", False)

# 🔥 PATCH P0: Cancelamento vence qualquer draft de agendamento
if tem_cancelamento:
    print(f"[P0-CANCELAMENTO_VENCE] Cancelamento detectado, limpando draft anterior", flush=True)
    ctx.pop("draft_agendamento", None)
    ctx.pop("aguardando_confirmacao_agendamento", None)
    ctx.pop("dados_confirmacao_agendamento", None)
    ctx.pop("intencao_conversacional", None)
    ctx["estado_fluxo"] = "idle"  # Resetar para permitir cancelamento

if tem_cancelamento and (not ctx.get("estado_fluxo") or ctx.get("estado_fluxo") == "idle"):
    # Processar cancelamento
```

---

## 📋 Dados Limpos

Quando cancelamento é detectado, o sistema **remove**:

| Campo | Razão |
|-------|-------|
| `draft_agendamento` | Não deve confirmar agendamento anterior |
| `aguardando_confirmacao_agendamento` | Flag de confirmação pendente |
| `dados_confirmacao_agendamento` | Dados da confirmação anterior |
| `intencao_conversacional` | Intenção antiga não é relevante |

E **reseta**:
| Campo | Valor | Razão |
|-------|-------|-------|
| `estado_fluxo` | `"idle"` | Permite que bloco de cancelamento execute |

---

## 🧪 Teste Obrigatório

### Cenário
```
Estado Inicial:
  estado_fluxo = "agendando"
  draft_agendamento = {profissional: "Bruna", servico: "Corte", data_hora: "...10h"}
  intencao_conversacional = "agendamento_direto"
  aguardando_confirmacao_agendamento = True

Entrada:
  "Quero cancelar com a Bruna amanhã"

Features Detectadas:
  tem_cancelamento = True
```

### Validações Esperadas
✅ `draft_agendamento` foi limpado  
✅ `aguardando_confirmacao_agendamento` foi limpado  
✅ `dados_confirmacao_agendamento` foi limpado  
✅ `intencao_conversacional` foi limpado  
✅ `estado_fluxo` resetado para "idle"

### Teste Executado
```
[PASS] teste_cancelamento_vence_draft.py

Resultado:
  [PASS]: draft_agendamento foi limpado
  [PASS]: aguardando_confirmacao_agendamento foi limpado
  [PASS]: dados_confirmacao_agendamento foi limpado
  [PASS]: intencao_conversacional foi limpado
  [PASS]: estado_fluxo resetado para idle
```

---

## 🔄 Fluxo Resultante

```
Usuário em estado "agendando" com draft
         ↓
Mensagem contém "cancelar"
         ↓
[PATCH P0 ATIVA]
  • Limpa draft_agendamento
  • Reseta estado para idle
         ↓
Bloco de cancelamento executa normalmente
         ↓
cancelar_evento_por_texto() é chamado
         ↓
Resultado: "Tem certeza de cancelar..." ou "Não encontrei..."
         ↓
Agendamento NÃO é confirmado
```

---

## 🚨 Casos de Uso

### Caso 1: Cancelamento com sucesso
```
Estado: agendando (draft criado)
Mensagem: "Cancelar corte de Bruna"

Sistema:
  1. Detecta "cancelar"
  2. Limpa draft
  3. Busca eventos com "corte" e "Bruna"
  4. Encontra 1 evento
  5. Pergunta confirmação
  
Resultado: "Tem certeza de cancelar o corte com Bruna?"
```

### Caso 2: Cancelamento sem eventos encontrados
```
Estado: agendando (draft criado)
Mensagem: "Cancelar consulta com João"

Sistema:
  1. Detecta "cancelar"
  2. Limpa draft
  3. Busca eventos com "consulta" e "João"
  4. Nenhum encontrado

Resultado: "Não encontrei nenhum evento para cancelar"
```

### Caso 3: Múltiplos eventos encontrados
```
Estado: agendando (draft criado)
Mensagem: "Cancelar com Bruna"

Sistema:
  1. Detecta "cancelar"
  2. Limpa draft
  3. Busca eventos com "Bruna"
  4. Encontra 3 eventos

Resultado: Lista de opções para selecionar qual cancelar
```

---

## ⚠️ Possíveis Problemas P0 Evitados

| Cenário | Sem Patch | Com Patch |
|---------|-----------|-----------|
| Cancelar durante agendamento | ❌ Confirma agendamento | ✅ Processa cancelamento |
| Mudança de ideia rápida | ❌ Agendamento criado | ✅ Cancelamento feito |
| Conflito de intenção | ❌ Comportamento errado | ✅ Cancelamento vence |

---

## 📊 Impacto P0

**Criticidade:** 🔴 CRÍTICO  
**Escopo:** Fluxo de agendamento em progresso  
**Risco:** Criar evento indesejado quando usuário quer cancelar  
**Mitigação:** Limpeza imediata de draft ao detectar cancelamento

---

## ✅ Checklist

- [x] Patch implementado
- [x] Teste escrito
- [x] Teste passou
- [x] Documentação criada
- [x] Casos de uso cobertos
- [x] Impacto P0 entendido

---

## 📚 Referência

- **Arquivo:** `router/principal_router.py`
- **Linhas:** ~3810-3825
- **Função:** `roteador_principal()`
- **Teste:** `teste_cancelamento_vence_draft.py`

---

**Conclusão:** Cancelamento agora SEMPRE vence draft de agendamento, independente do estado anterior. Usuário nunca terá seu agendamento confirmado quando queria cancelar.
