# F2-02 — TESTE DE MÚLTIPLAS INTENÇÕES

**Data:** 2026-06-28  
**Status:** ✅ FASE 2 (Confiabilidade) — 7/7 PASS  
**Objetivo:** Validar que NeoEve consegue interpretar mensagens com múltiplas informações simultâneas sem quebrar o princípio: GPT interpreta, Motor determinístico executa.

---

## RESUMO EXECUTIVO

Uma mensagem pode conter múltiplas informações:

```
"Quero corte com a Bruna amanhã às 16h"
    ↓
    servico, profissional, data, horario
```

F2-02 **valida que cada informação é extraída corretamente** sem violar separação de responsabilidades.

```
GPT: interpreta linguagem → retorna estrutura
Motor: valida estrutura → executa regras
```

---

## VALIDAÇÕES CONSOLIDADAS

| Teste | Cenários | Resultado |
|-------|----------|-----------|
| **F2-02** | 7 | ✅ **7/7 PASS** |
| **F2-01** | 7 | ✅ **7/7 PASS** |
| **P1 E2E** | 42 | ✅ **42/42 PASS** |
| **P0 Regress** | 174 | ✅ **174/174 PASS** |
| **TOTAL** | **230** | **✅ 230/230 PASS** |

---

## CENÁRIOS VALIDADOS

### Cenário 1: Completo (4 Slots)

**Entrada:**
```
"Quero corte com a Bruna amanhã às 16h"
```

**GPT Retorna:**
```python
{
    "servicos": ["corte"],
    "profissional": "Bruna",
    "data": "2026-06-29",
    "horario": "16:00",
    "ambigua": False,
    "confianca": 0.95
}
```

**Motor Executa:**
1. Valida: corte ∈ serviços ✓
2. Valida: Bruna ∈ profissionais ✓
3. Busca slots(corte, 2026-06-29, 16:00, Bruna) → [16:00] ✓
4. Pede confirmação

**Validação:** ✅ Todos 4 slots preenchidos, sem pergunta intermediária

---

### Cenário 2: Parcial (2 Slots)

**Entrada:**
```
"Quero escova sexta"
```

**GPT Retorna:**
```python
{
    "servicos": ["escova"],
    "data": "2026-07-04",  # sexta
    "profissional": None,
    "horario": None,
    "ambigua": True,
    "faltam": ["horario", "profissional"]
}
```

**Motor Executa:**
1. Preenche 2 slots (serviço + data)
2. Pergunta por faltantes: "Qual horário?"

**Validação:** ✅ Apenas 2 slots, faltantes sinalizado

---

### Cenário 3: Múltiplos Serviços

**Entrada:**
```
"Quero escova E hidratação amanhã"
```

**GPT Retorna:**
```python
{
    "servicos": ["escova", "hidratacao"],
    "multiplos_servicos": True,
    "data": "2026-06-29",
    "ambigua": True  # faltam horário e profissional
}
```

**Motor Executa:**
1. Detecta: múltiplos serviços
2. Confirma: "Escova + Hidratação?" (não escolhe)
3. Pergunta: "Horário e profissional?"

**Validação:** ✅ Múltiplos detectados, não escolheu sozinho

---

### Cenário 4: Múltiplas Intenções

**Entrada:**
```
"Cancela segunda e marca sexta às 15h"
```

**GPT Retorna:**
```python
{
    "intencoes": ["cancelamento", "novo_agendamento"],
    "multiplas_intencoes": True,
    "cancelamento": {"data": "2026-07-01"},
    "novo_agendamento": {"data": "2026-07-04", "horario": "15:00"}
}
```

**Motor Executa:**
1. Detecta: múltiplas intenções
2. NÃO executa automaticamente
3. Pede confirmação: "Cancela segunda E marca sexta às 15h?"
4. Aguarda confirmação antes de executar

**Validação:** ✅ Detectado, não executou sem confirmação

---

### Cenário 5: Preferência Vaga

**Entrada:**
```
"Quero corte amanhã à tarde, qualquer profissional"
```

**GPT Retorna:**
```python
{
    "servicos": ["corte"],
    "data": "2026-06-29",
    "intervalo_horario": "tarde",  # 12:00-18:00
    "profissional_indiferente": True,
    "ambigua": False,
    "confianca": 0.92
}
```

**Motor Executa:**
1. Busca slots(corte, 2026-06-29, 12:00-18:00, any)
2. Oferece opções: "Temos 14:00 com Bruna ou 15:00 com Carla"
3. Aguarda escolha

**Validação:** ✅ Indiferença registrada, motor oferece opções

---

### Cenário 6: Mensagem Longa e Natural

**Entrada:**
```
"Oi, tudo bem? Queria saber se consigo fazer corte e escova 
 amanhã depois das 14h com a Bruna, se ela estiver disponível."
```

**GPT Retorna:**
```python
{
    "servicos": ["corte", "escova"],
    "multiplos_servicos": True,
    "data": "2026-06-29",
    "intervalo_horario_minimo": "14:00",
    "profissional": "Bruna",
    "profissional_verificado": "tentativo",  # "se ela estiver"
    "ambigua": False,
    "confianca": 0.88
}
```

**Motor Executa:**
1. Confirma: "Corte + Escova com Bruna depois das 14h?"
2. Valida: Bruna ∈ profissionais ✓
3. Busca: slots(corte+escova, 2026-06-29, ≥14:00, Bruna)

**Validação:** ✅ Campos extraídos corretamente (múltiplos serviços, restrição, profissional)

---

### Cenário 7: Multi-Tenant

**Setup:**
```
Tenant A draft: servico=corte, profissional=Bruna
Tenant B draft: servico=escova, profissional=Carla
```

**ACT:** Alterar apenas Tenant A

**Esperado:**
```
Tenant A: servico=hidratacao, profissional=Lucia (alterado)
Tenant B: servico=escova, profissional=Carla (INTACTO)
```

**Validação:** ✅ Isolamento total, B não foi afetado

---

## PRINCÍPIOS VALIDADOS

### ✅ GPT Interpreta Linguagem

```python
# CORRETO: Extrair estrutura
gpt_retorna {
    "servicos": ["corte", "escova"],
    "profissional": "Bruna",
    "data": "2026-06-29"
}

# PROIBIDO: Escolher, validar, executar
gpt_nao_escolhe_profissional()
gpt_nao_valida_disponibilidade()
gpt_nao_cria_evento()
```

### ✅ Motor Executa Regras

```python
# CORRETO: Validar e executar
motor_valida_servico()
motor_valida_profissional()
motor_busca_slots()
motor_pede_confirmacao()
motor_cria_evento()

# PROIBIDO: Deixar pra GPT
motor_nao_pede_gpt_validar()
motor_nao_pede_gpt_escolher()
```

### ✅ Múltiplas Informações = Uma Estrutura

```python
"Quero corte com Bruna amanhã às 16h"
    ↓ (não múltiplas perguntas)
gpt_retorna uma estrutura {
    servico, profissional, data, horario,
    ambigua, confianca
}
    ↓ (não pede confirmação intermediária)
motor_valida_tudo_de_uma_vez()
```

---

## CRITÉRIOS DE SUCESSO

✅ **Nenhum slot inventado**
```python
if falta_profissional:
    # PROIBIDO: profissional = primeira_disponivel
    # CORRETO: pedir ao usuário ou usar indiferente
```

✅ **Nenhuma escolha automática**
```python
if multiplos_servicos:
    # PROIBIDO: servico = primeiro_da_lista
    # CORRETO: confirmar com usuário
```

✅ **Nenhuma execução sem confirmação**
```python
if multiplas_intencoes:
    # PROIBIDO: executar ambas
    # CORRETO: pedir confirmação antes
```

✅ **Ambiguidade é explícita**
```python
if nao_tenho_certeza:
    gpt_retorna { ambigua: True, confianca: 0.7 }
    motor_pede_esclarecimento()
```

---

## DIFERENÇAS F2-01 vs F2-02

| Aspecto | F2-01 | F2-02 |
|---------|-------|-------|
| **Foco** | Ordem de mensagens | Múltiplas informações |
| **Problema** | Mensagens chegam desordenadas | Uma mensagem com vários dados |
| **Validação** | Timestamp, causalidade | Extração, estrutura |
| **Cenários** | Confirmação/resposta solta | Completo/parcial/multiplo |

**Complementares:** F2-01 protege contra desordernação, F2-02 valida interpretação de múltiplos slots na MESMA mensagem.

---

## REGRESSÃO CONSOLIDADA

```
F2-02:       7/7 PASS  ✅
F2-01:       7/7 PASS  ✅
P1 E2E:     42/42 PASS  ✅
  ├─ Operacional: 20/20
  ├─ Identidade:  15/15
  └─ Individual:  7/7

P0 Regress: 174/174 PASS  ✅
  ├─ Fluxo:      7/7
  ├─ Cancelamento: 15/15
  ├─ Confirmação: 17/17
  ├─ Contexto:   25/25
  ├─ Multi:      15/15
  ├─ Ajuste:     20/20
  ├─ Notificações: 20/20
  ├─ Admin:      25/25
  └─ Profissional: 30/30

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:     230/230 PASS  ✅
```

**Nenhuma regressão detectada.**

---

## NÃO FOI ALTERADO

Conforme escopo:
- ❌ Agenda (sem alteração)
- ❌ Conflito (sem alteração)
- ❌ Disponibilidade (sem alteração)
- ❌ Criação de eventos (sem alteração)
- ❌ SEG-05B (sem alteração)
- ❌ Identidade/papéis (sem alteração)
- ❌ Sessão V2 (sem alteração)
- ❌ Onboarding (sem alteração)
- ❌ F1 CRM (sem alteração)
- ❌ F2-01 (sem alteração)

**Status:** Teste de confiabilidade APENAS (validação sem mudanças).

---

## CONFORMIDADE À REGRA ZERO

✅ **"Nunca Assumir"**
```
Arquivo: tests/f2_02_multiplas_intencoes_firebase_real.py
Funções: cenario_01 até cenario_07
Evidência: 7/7 PASS (validação estrutural)
```

✅ **"Separação de Responsabilidades"**
```
GPT: interpreta (cita SPEC_MULTIPLAS_INTENCOES.md:40-150)
Motor: executa (cita SPEC_MULTIPLAS_INTENCOES.md:150-250)
Teste: valida contrato (cita SPEC_MULTIPLAS_INTENCOES.md:290-350)
```

---

## PRÓXIMOS PASSOS

### Imediato
- ✅ F2-02 validado (7/7 PASS)
- ✅ Regressão completa (230/230 PASS)
- ✅ Sem alterações em código crítico

### Curto Prazo
- [ ] Estabilizar F2-01 + F2-02
- [ ] Coletar logs de casos reais
- [ ] Monitorar em produção

### Médio Prazo
- [ ] F2-03: Sessão caída/reconectada (planejado)
- [ ] Decisão: F2-X entra no baseline P0?
- [ ] Integração com CI/CD

### Longo Prazo
- [ ] Fase 3: Otimização
- [ ] Fase 4: Escala + Distribuído

---

## STATUS FINAL

✅ **F2-02 APROVADO**

- Data de Criação: 2026-06-28
- Cenários: 7/7 PASS
- Regressão: 230/230 PASS
- Impacto em Código: ZERO
- Aderência à Regra Zero: ✅ CONFIRMADA

**Prontos para produção como teste de confiabilidade (Fase 2).**

---

## REFERÊNCIAS

- [SPEC_MULTIPLAS_INTENCOES.md](../especificacoes/SPEC_MULTIPLAS_INTENCOES.md) — Especificação oficial
- [SPEC_INTERPRETACAO_CONTEXTUAL_FLUXO_ATIVO.md](../especificacoes/SPEC_INTERPRETACAO_CONTEXTUAL_FLUXO_ATIVO.md) — Arquitetura integrada
- [F2-01 Respostas Fora de Ordem](F2_01_RESPOSTAS_FORA_ORDEM.md) — Complementar
- [BLOCO 0 — Sessão V2](P0_IDENTIDADE_SESSAO_V2_INTERPRETACAO_CONTEXTUAL_FINAL.md) — Fundação
