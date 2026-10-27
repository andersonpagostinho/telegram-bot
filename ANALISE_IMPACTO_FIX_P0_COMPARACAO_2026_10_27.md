# 📊 ANÁLISE DE IMPACTO — FIX P0.7.1

**Data:** 2026-10-27  
**Status:** READ-ONLY AUDITORIA  
**Escopo:** Verificação de impacto em outras funções após mudança em P0.7  

---

## MUDANÇA IMPLEMENTADA

**Arquivo:** `router/principal_router.py` (bloco P0.7, linhas 5553-5577)  
**Tipo de mudança:** Detecção condicional + reordenação lógica

```python
# ANTES: Todas as consultas reclassificadas para "consulta_disponibilidade_aberta"
if interpretacao_gpt.get("intencao") == "consulta":
    ctx["intencao_conversacional"] = "consulta_disponibilidade_aberta"  # SEMPRE
    ctx["profissional"] = entidades.get("profissional")  # SEMPRE extrai

# DEPOIS: Detecta comparação e mantém como genérica
if interpretacao_gpt.get("intencao") == "consulta":
    eh_comparacao = bool(entidades.get("profissional_1") or entidades.get("profissional_2"))
    
    if eh_comparacao:
        ctx["intencao_conversacional"] = "consulta"  # MANTÉM genérico
        # NÃO extrai profissional
    else:
        ctx["intencao_conversacional"] = "consulta_disponibilidade_aberta"  # COMO ANTES
        ctx["profissional"] = entidades.get("profissional")  # COMO ANTES
```

---

## IMPACTO EM OUTRAS FUNÇÕES

### Análise 1: Mapeamento de `objetivo_conversacional`

**Localização:** `principal_router.py:5798-5832`

**Código:**
```python
if intencao_conv == "consulta_disponibilidade_aberta":
    objetivo_conversacional = "descobrir_servico_para_consulta"

elif intencao_conv == "consulta_disponibilidade_servico":
    objetivo_conversacional = "consultar_disponibilidade_por_servico"

elif intencao_conv == "agendamento_direto":
    objetivo_conversacional = "preparar_prechecagem_agendamento"

# ... mais condições ...

# Nota: Não há case para intencao_conv == "consulta" (genérico)
```

**Impacto:**
- ✅ Quando `intencao_conversacional = "consulta"` (comparações), `objetivo_conversacional` fica **None**
- ✅ `objetivo_conversacional = None` é um estado **válido e esperado** (código não quebra)
- ✅ Com `objetivo_conversacional = None`, o fluxo continua e chama GPT normalmente

**Verificação:**
```
intencao_conversacional = "consulta"
objetivo_conversacional = None
↓
Fluxo continua → GPT é chamado → GPT responde comparação
```

**Risco:** ✅ **BAIXO** — `None` é estado esperado

---

### Análise 2: Guardrails de Preservação de Contexto

**Localização:** `principal_router.py:5252-5258`

**Código:**
```python
estado_consulta_pura = (
    ctx.get("estado_fluxo") == "aguardando_servico"
    and ctx.get("objetivo_conversacional") == "descobrir_servico_para_consulta"
)

if estado_consulta_pura:
    # Preserva objetivo de consulta pura
```

**Impacto:**
- ✅ Verifica especificamente `objetivo_conversacional == "descobrir_servico_para_consulta"`
- ✅ Comparações com `objetivo_conversacional = None` não acionam este guardrail
- ✅ **SEM RISCO** — guardrail não interfere

**Risco:** ✅ **ZERO** — condição não é acionada

---

### Análise 3: Detecção de Prox_Passo

**Localização:** `principal_router.py:321-325`

**Código:**
```python
objetivo = contexto.get("objetivo_conversacional")

if objetivo == "descobrir_servico_para_consulta":
    if not tem_servico:
        return "perguntar_servico"
```

**Impacto:**
- ✅ Verifica especificamente `objetivo == "descobrir_servico_para_consulta"`
- ✅ Com `objetivo = None`, esta condição é **False** (continua para próximas verificações)
- ✅ Fluxo continua normalmente

**Risco:** ✅ **ZERO** — comparações não caem nesta condição

---

### Análise 4: Interpretação de Resposta Informativa

**Localização:** `principal_router.py:267-270`

**Código:**
```python
if (
    (objetivo == "consultar_disponibilidade_por_servico"
    or intencao == "consulta_disponibilidade_servico")
    and not tem_resposta_informativa
):
```

**Impacto:**
- ✅ Verifica `intencao == "consulta_disponibilidade_servico"` (específico, não genérico)
- ✅ Comparações com `intencao = "consulta"` não acionam esta lógica
- ✅ **SEM RISCO**

**Risco:** ✅ **ZERO** — comparações não caem nesta condição

---

### Análise 5: Contexto Preservado (P0.7.4)

**Localização:** `principal_router.py:5791-5794`

**Código:**
```python
if preservar_continuidade_data:
    intencao_conv = ctx.get("intencao_conversacional")
else:
    intencao_conv = class_intencao.get("intencao_conversacional")
```

**Impacto:**
- ✅ Lógica preserva `intencao_conversacional` do contexto quando `preservar_continuidade_data = True`
- ✅ Comparações podem ter `intencao_conversacional = "consulta"` de turnos anteriores
- ✅ Isso é **esperado e correto** — comparações continuam sendo tratadas como genéricas

**Risco:** ✅ **ZERO** — comportamento esperado

---

## CASOS ADJACENTES

### Case 1: Ajuste Incremental vs Comparação

**Cenário:**
```
Mensagem anterior: "Qual a disponibilidade?"
  → intencao_conversacional = "consulta_disponibilidade_aberta"
  → estado_fluxo = "aguardando_servico"

Mensagem nova: "A Carla faz as mesmas coisas que a Bruna?"
  → GPT retorna: intencao="consulta", profissional_1="Carla", profissional_2="Bruna"
  → Fix detecta comparação
  → intencao_conversacional = "consulta" (genérico, não reclassifica)
```

**Impacto:**
- ✅ Não entra em "ajuste_incremental" (intencao != ajuste_incremental)
- ✅ GPT é chamado para responder comparação
- ✅ Estado anterior `estado_fluxo = "aguardando_servico"` pode permanecer (mas não interfere com comparação)

**Risco:** ✅ **BAIXO** — estado anterior não interfere

---

### Case 2: Confirmação Pendente + Comparação

**Cenário:**
```
Estado anterior: aguardando_confirmacao_agendamento = True

Mensagem nova: "A Carla faz as mesmas coisas que a Bruna?"
  → Comparação detectada
  → intencao_conversacional = "consulta"
```

**Verificação:**
```python
# Na linha 5997:
if ctx.get("intencao_conversacional") != "negacao_confirmacao_agendamento":
    ctx["intencao_conversacional"] = interpretacao_gpt.get("intencao")  # "consulta"
```

**Impacto:**
- ✅ Comparação sobrescreve `intencao_conversacional` anterior
- ✅ `aguardando_confirmacao_agendamento` fica True (mas não é verificado para comparações)
- ✅ GPT responde a comparação normalmente

**Risco:** ⚠️ **MÉDIO-BAIXO** — `aguardando_confirmacao_agendamento` fica True mesmo após comparação  
**Recomendação:** Considerar limpar `aguardando_confirmacao_agendamento` quando comparação é detectada

---

## RESUMO DE RISCOS

| Função/Ponto | Verificação | Impacto | Risco |
|--------------|-------------|--------|-------|
| objetivo_conversacional = None | Mapeamento (L5798-5832) | Estado esperado | ✅ ZERO |
| Estado consulta pura | Guardrail P0.7.4 (L5252) | Não acionado | ✅ ZERO |
| Próx_passo detection | Objetivo check (L321-325) | Não acionado | ✅ ZERO |
| Resposta informativa | Intencao check (L267-270) | Não acionado | ✅ ZERO |
| Preservação contexto | P0.7.4 (L5791-5794) | Comportamento correto | ✅ ZERO |
| Confirmação pendente | Flag check (L5997) | Flag permanece True | ⚠️ MÉDIO-BAIXO |

---

## RECOMENDAÇÕES

### 🟢 SEM AÇÃO NECESSÁRIA (SAFE TO COMMIT)

- Comparações não quebram nenhuma lógica existente
- `objetivo_conversacional = None` é estado válido e esperado
- Nenhum guardrail é acionado

### 🟡 MELHORIA FUTURA (NÃO BLOQUEIA COMMIT)

**Limpar `aguardando_confirmacao_agendamento` quando comparação é detectada:**

```python
# No bloco P0.7.1, quando detecta comparação:
if eh_comparacao:
    ctx["intencao_conversacional"] = "consulta"
    ctx["aguardando_confirmacao_agendamento"] = False  # ADICIONAR ISTO
    # NÃO extrai profissional
```

**Justificativa:** Evitar confusão de estado quando usuário sai de confirmação para fazer pergunta lateral

**Impacto:** Mínimo (preventivo, não corrige bug)  
**Prioridade:** BAIXA (melhoria, não defeito)

---

## CONCLUSÃO

✅ **O fix é SEGURO para commit**

- Nenhuma função existente é quebrada
- Comportamento anterior é preservado para consultas reais
- Comparações funcionam corretamente com `objetivo_conversacional = None`
- Nenhum guardrail é acionado indevidamente

**Recomendação:** Commit agora, considerar melhoria de `aguardando_confirmacao_agendamento` em PR futuro

---

**Auditoria realizada em:** 2026-10-27 17:50:00 UTC  
**Tipo de auditoria:** Análise de impacto em função de outras partes do código  
**Métodos:** Grep + análise estática de fluxo de controle  
**Conclusão:** ✅ SEGURO PARA COMMIT
