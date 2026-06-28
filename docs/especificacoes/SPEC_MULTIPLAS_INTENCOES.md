# ESPECIFICAÇÃO — MÚLTIPLAS INTENÇÕES NA MESMA MENSAGEM

**Data:** 2026-06-28  
**Status:** ✅ ESPECIFICAÇÃO OFICIAL  
**Versão:** 1.0 — Congelada  

---

## PRINCÍPIO CENTRAL

```
Uma mensagem pode preencher múltiplos slots simultaneamente.

"Quero corte com a Bruna amanhã às 16h"
    ↓
    servico=corte
    profissional=Bruna
    data=amanhã
    horario=16h
```

**Contrato:**
- GPT interpreta linguagem → retorna estrutura
- Motor determinístico valida → executa

---

## O QUE GPT FAZ

### ✅ Extração de Múltiplos Slots

```python
mensagem = "Quero corte com a Bruna amanhã às 16h"

gpt_retorna = {
    "intencao_principal": "agendar",
    "servicos": ["corte"],
    "profissional": "Bruna",
    "data": "2026-06-29",  # amanhã
    "horario": "16:00",
    "ambigua": False,
    "confianca": 0.95
}
```

### ✅ Detecção de Múltiplos Serviços

```python
mensagem = "Quero escova E hidratação"

gpt_retorna = {
    "intencao_principal": "agendar",
    "servicos": ["escova", "hidratacao"],
    "multiplos_servicos": True,
    "profissional": None,
    "ambigua": False,
    "confianca": 0.90
}
```

### ✅ Detecção de Ambiguidade

```python
mensagem = "Quero corte"  # que hora? qual dia? qual profissional?

gpt_retorna = {
    "intencao_principal": "agendar",
    "servicos": ["corte"],
    "profissional": None,
    "data": None,
    "horario": None,
    "ambigua": True,
    "confianca": 0.85,
    "faltam": ["data", "horario"]  # opcional: ajuda motor
}
```

### ✅ Extração com Preferência Vaga

```python
mensagem = "Quero corte à tarde, qualquer profissional"

gpt_retorna = {
    "intencao_principal": "agendar",
    "servicos": ["corte"],
    "intervalo_horario": "tarde",  # 12:00-18:00
    "profissional_indiferente": True,
    "ambigua": False,
    "confianca": 0.90
}
```

---

## O QUE GPT NÃO FAZ

### ❌ Escolher Profissional

```python
# PROIBIDO:
if mensagem contém multiplos_nomes:
    gpt_escolhe profissional mais comum

# CORRETO:
gpt_retorna {
    "multiplos_profissionais": ["Bruna", "Carla"],
    "ambigua": True  # motor pergunta
}
```

### ❌ Resolver Conflito

```python
# PROIBIDO:
if horario_conflita:
    gpt_sugerir horario proximo

# CORRETO:
gpt_retorna estrutura
motor_valida e sugere alternativas
```

### ❌ Executar Múltiplas Ações

```python
# PROIBIDO:
if "cancela segunda e marca sexta" in mensagem:
    cancelar_evento()
    criar_novo_evento()

# CORRETO:
gpt_retorna {
    "intencoes": ["cancelamento", "novo_agendamento"],
    "multiplas_intencoes": True
}
motor_pede confirmação do fluxo
```

### ❌ Inventar Dados

```python
# PROIBIDO:
if profissional not in mensagem:
    gpt_escolher profissional_padrao

# CORRETO:
gpt_retorna {
    "profissional": None,
    "ambigua": True
}
motor pergunta ou usa preferência histórica
```

---

## RESPONSABILIDADE DO MOTOR DETERMINÍSTICO

### 1️⃣ Validação

```python
# Se GPT retornou serviço:
if servico not in configuracao.servicos:
    responder("Desculpa, não temos esse serviço")
    return

# Se GPT retornou profissional:
if profissional not in configuracao.profissionais:
    responder("Desculpa, não temos essa profissional")
    return
```

### 2️⃣ Disponibilidade

```python
# Buscar slots compatíveis
if profissional_especifico:
    slots = buscar_slots(
        servico,
        data,
        horario,
        profissional
    )
else:
    slots = buscar_slots(
        servico,
        data,
        horario
    )

if not slots:
    responder("Desculpa, sem disponibilidade")
    sugerir_alternativas()
    return
```

### 3️⃣ Confirmação

```python
# Se múltiplos serviços:
if multiplos_servicos:
    responder("Você quer " + ", ".join(servicos) + "?")
    return

# Se múltiplas intenções:
if multiplas_intencoes:
    responder("Confirma: cancelar segunda e marcar sexta?")
    return
```

### 4️⃣ Criação

```python
# SOMENTE após confirmação
criar_evento(
    servicos=servicos,
    profissional=profissional,
    data=data,
    horario=horario
)
```

---

## CENÁRIOS

### Cenário 1: Completo (4 slots)

```
MSG: "Quero corte com a Bruna amanhã às 16h"

GPT retorna:
{
    "servicos": ["corte"],
    "profissional": "Bruna",
    "data": "2026-06-29",
    "horario": "16:00",
    "ambigua": false,
    "confianca": 0.95
}

Motor:
1. Valida: corte ∈ servicos ✓
2. Valida: Bruna ∈ profissionais ✓
3. Busca slots(corte, 2026-06-29, 16:00, Bruna) → [16:00] ✓
4. Pede confirmação (ou agenda direto)
```

---

### Cenário 2: Parcial (2 slots)

```
MSG: "Quero escova sexta"

GPT retorna:
{
    "servicos": ["escova"],
    "data": "2026-07-04",  # sexta que vem
    "profissional": null,
    "horario": null,
    "ambigua": true,
    "faltam": ["horario", "profissional"]
}

Motor:
1. Pergunta: "Qual horário?"
2. Aguarda resposta
3. Pergunta: "Qual profissional?" (ou indiferente)
```

---

### Cenário 3: Múltiplos Serviços

```
MSG: "Quero escova E hidratação amanhã"

GPT retorna:
{
    "intencao_principal": "agendar",
    "servicos": ["escova", "hidratacao"],
    "multiplos_servicos": true,
    "data": "2026-06-29",
    "horario": null,
    "profissional": null,
    "ambigua": true
}

Motor:
1. Confirma: "Escova + Hidratação?"
2. Pergunta: "Que horário?"
3. Pergunta: "Qual profissional?"
4. Cria evento com ambos serviços
```

---

### Cenário 4: Múltiplas Intenções (Cancelamento + Nova)

```
MSG: "Cancela segunda e marca sexta às 15h"

GPT retorna:
{
    "intencoes": ["cancelamento", "novo_agendamento"],
    "multiplas_intencoes": true,
    "cancelamento": {
        "data": "2026-07-01"  // segunda
    },
    "novo_agendamento": {
        "data": "2026-07-04",  // sexta
        "horario": "15:00"
    }
}

Motor:
1. NÃO executa automaticamente
2. Pede confirmação: "Cancela segunda E marca sexta às 15h?"
3. Aguarda confirmação explícita
4. Executa ambas operações
```

---

### Cenário 5: Preferência Vaga

```
MSG: "Quero corte amanhã à tarde, qualquer profissional"

GPT retorna:
{
    "servicos": ["corte"],
    "data": "2026-06-29",
    "intervalo_horario": "tarde",  // 12:00-18:00
    "profissional_indiferente": true,
    "ambigua": false,
    "confianca": 0.92
}

Motor:
1. Busca slots(corte, 2026-06-29, 12:00-18:00, any)
2. Oferece opções: "Temos 14:00 com Bruna ou 15:00 com Carla"
3. Aguarda escolha
```

---

### Cenário 6: Mensagem Longa e Natural

```
MSG: "Oi, tudo bem? Queria saber se consigo fazer corte e escova 
amanhã depois das 14h com a Bruna, se ela estiver disponível."

GPT retorna:
{
    "intencao_principal": "agendar",
    "servicos": ["corte", "escova"],
    "multiplos_servicos": true,
    "data": "2026-06-29",
    "intervalo_horario_minimo": "14:00",
    "profissional": "Bruna",
    "profissional_verificado": "tentativo",  // "se ela estiver"
    "ambigua": false,
    "confianca": 0.88
}

Motor:
1. Confirma: "Corte + Escova com Bruna amanhã depois das 14h?"
2. Valida: Bruna ∈ profissionais ✓
3. Busca slots: (corte+escova, 2026-06-29, ≥14:00, Bruna)
4. Se houver: oferece horário; se não: sugere alternativas
```

---

### Cenário 7: Multi-Tenant

```
Tenant A MSG: "Quero corte com Bruna"
Tenant B MSG: "Quero corte com Bruna"

GPT deve respeitar tenant:
- Tenant A Bruna ≠ Tenant B Bruna
- Slots de A não afetam B
- Isolamento total
```

---

## PRIORIDADES

### Intenção Principal

```
Se múltiplas intenções possíveis, ordenar por prioridade:

1. Agendar novo evento
2. Confirmar pendente
3. Cancelar evento
4. Mudar agendamento
5. Consultar disponibilidade
```

### Ambiguidade

```
Se ambíguo:
1. NÃO inventar
2. NÃO escolher
3. NÃO executar
4. PERGUNTAR

Resposta segura:
"Desculpa, não entendi. Você quer...?"
```

---

## CONTRATO ENTRADA/SAÍDA

### Input para GPT

```python
{
    "estado_fluxo": str | None,
    "draft_agendamento": dict | None,
    "mensagem": str,
    "tenant_config": {
        "servicos": [str],
        "profissionais": [str],
        "expediente": dict
    },
    "historico": [dict]  # contexto de conversas anteriores
}
```

### Output de GPT

```python
{
    # Intenção
    "intencao_principal": str,  # agendar, cancelar, consultar, etc
    "intencoes": [str],  # se múltiplas
    "multiplas_intencoes": bool,

    # Agendamento
    "servicos": [str],
    "profissional": str | None,
    "data": str | None,  # YYYY-MM-DD
    "horario": str | None,  # HH:MM
    "intervalo_horario": str | None,  # "tarde", "manhã"
    "intervalo_horario_minimo": str | None,  # "≥14:00"
    "profissional_indiferente": bool,

    # Cancelamento
    "cancelamento": {
        "data": str,
        "horario": str | None
    } | None,

    # Qualidade
    "ambigua": bool,
    "confianca": float,  # 0.0-1.0
    "faltam": [str],  # campos que faltam
    "motivo_se_recusou": str | None
}
```

---

## PADRÃO PROIBIDO

### ❌ Listas Fixas

```python
# PROIBIDO:
if "corte" in mensagem.lower():
    servico = "corte"
elif "escova" in mensagem.lower():
    servico = "escova"
```

### ❌ Heurísticas Frágeis

```python
# PROIBIDO:
if mensagem.count(" ") > 10:
    multiplas_intencoes = True
```

### ❌ Fallbacks sem Contexto

```python
# PROIBIDO:
if profissional not in mensagem:
    profissional = "primeira profissional disponível"
```

---

## PADRÃO CORRETO

### ✅ Semântica + Estrutura

```python
# CORRETO:
gpt_interpreta semântica da mensagem
gpt_extrai campos em estrutura tipada
gpt_sinaliza ambiguidade explicitamente

motor_valida estrutura
motor_executa regras determinísticas
motor_pede confirmação se necessário
```

---

## INTEGRAÇÃO COM INTERPRETACAO_CONTEXTUAL_SERVICE

**Fluxo Típico:**

```
1. Usuário envia mensagem
2. Router identifica estado_fluxo
3. Chamar interpretar_com_fluxo_ativo()
4. GPT retorna estrutura (tipo_resposta + múltiplos campos)
5. Motor determinístico valida cada campo
6. Se falta campo: volta para pedir
7. Se múltiplas intenções: volta para confirmar
8. Se tudo ok: executa
```

---

## TESTES OBRIGATÓRIOS

- ✅ Cenário 1: Completo (4 slots)
- ✅ Cenário 2: Parcial (2 slots)
- ✅ Cenário 3: Múltiplos serviços
- ✅ Cenário 4: Múltiplas intenções
- ✅ Cenário 5: Preferência vaga
- ✅ Cenário 6: Mensagem longa e natural
- ✅ Cenário 7: Multi-tenant

---

## CHECKLIST FINAL

- ✅ GPT extrai múltiplos slots
- ✅ GPT não escolhe
- ✅ GPT não executa
- ✅ Ambiguidade é explícita
- ✅ Motor valida tudo
- ✅ Motor pede confirmação
- ✅ Motor executa após confirmação
- ✅ Estrutura sempre tipada
- ✅ Sem listas fixas
- ✅ Sem fallbacks sem contexto
- ✅ Multi-tenant isolado

---

## STATUS

✅ **ESPECIFICAÇÃO OFICIAL**

Data de implementação: 2026-06-28  
Data de validação: (a validar em F2-02 testes)  

**Próximas mudanças não são permitidas sem decisão explícita.**

---

## REFERÊNCIAS

- [SPEC_INTERPRETACAO_CONTEXTUAL_FLUXO_ATIVO.md](SPEC_INTERPRETACAO_CONTEXTUAL_FLUXO_ATIVO.md)
- [SPEC_FINAL_IDENTIDADE_PAPEIS_ATORES.md](SPEC_FINAL_IDENTIDADE_PAPEIS_ATORES.md)
- [F2-02 Teste](../../../tests/f2_02_multiplas_intencoes_firebase_real.py)
