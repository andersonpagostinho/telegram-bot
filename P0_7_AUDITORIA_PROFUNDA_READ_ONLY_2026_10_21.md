# 📋 P0.7 — AUDITORIA READ-ONLY PROFUNDA (Sem Editar, Sem Commit)

## 🎯 PONTO CRÍTICO IDENTIFICADO

**Arquivo:** `utils/gpt_utils.py` linha 121-126
```python
def estimar_duracao(servico):
    mapa = {"corte": 30, "escova": 40, "coloração": 90}
    try:
        return mapa.get(servico.lower(), 60)  # ← RETORNA 60 SE servico=None!
    except Exception:
        return 60
```

**Problema:** Quando `servico=None` (consulta sem serviço), função retorna **60 minutos como duração padrão**.

---

## 🔍 FLUXO COMPLETO RASTREADO

### ETAPA 1: Classificação GPT (P0.6.2 Fallback)
**Arquivo:** `router/principal_router.py` linhas 5414-5415

```
Entrada: "Tem horário para hoje às 15 com a Bruna?"

[P0.6.2_FALLBACK] Chama: interpretar_linguagem_operacional_gpt()
    ↓
[P0.6.2_FALLBACK_RESULTADO]
{
    'intencao': 'consulta',                 ← TIPO CORRETO
    'entidades': {
        'data': 'hoje',
        'horario': '15:00',
        'profissional': 'Bruna',
        'servico': []                       ← VAZIO (esperado!)
    },
    'confianca': 85                         ← CONFIANÇA ALTA
}
```

**Status:** ✅ GPT classifica CORRETAMENTE como consulta

---

### ETAPA 2: Validação de Catálogo (P0.6.2)
**Arquivo:** `router/principal_router.py` linhas 5427-5433

```python
servicos_gpt = []  # ← VAZIO
servicos_validos = []

for srv in servicos_gpt:  # Loop NÃO executa
    ...

# servicos_validos = []  (vazio)
[P0.6.2_VALIDACAO_CATALOGO] serviços GPT=[] | válidos=[]
```

**Lógica atual (PROBLEMA):**
```python
if len(servicos_validos) > 1:
    # múltiplos candidatos
    ...
elif len(servicos_validos) == 1 and confianca >= 75:
    # aceita este serviço
    ...
else:
    # ← REJEITA AQUI (intencao='consulta' chegando aqui também!)
    [P0.6.2_FALLBACK_REJEITO]
    return "Desculpe, qual serviço você gostaria de agendar?"
```

**Causa raiz:** Não diferencia `intencao="consulta"` (permitido sem serviço) de `intencao="agendamento_direto"` (precisa serviço).

**Status:** ❌ Consulta é REJEITADA indevidamente aqui

---

### ETAPA 3: Onde Deveria ir (Mas não Chega)
**Arquivo:** `router/principal_router.py` linhas 5769-5777

```python
elif interpretacao_gpt.get("intencao") == "consulta":
    ctx["objetivo_conversacional"] = "consultar_disponibilidade_por_servico"
    ctx["intencao_conversacional"] = "consulta_disponibilidade_servico"
```

**Status:** ❌ NUNCA chega aqui (rejeitado antes)

---

## 🔴 FLUXO SE CONSULTA CHEGASSE AO HANDLER

Se a consulta NÃO fosse rejeitada, o que aconteceria:

### Passo A: Chamada ao Handler de Buscar Horário
**Arquivo:** `router/principal_router.py` linhas 3645-3718

```python
async def buscar_horario_ajuste_no_dia(
    user_id, data, hora_referencia, 
    duracao_min,        # ← CRÍTICO!
    profissional, servico, ...
):
    # Obter janela funcionamento
    # Verificar cada candidato de hora
    
    conflito = await verificar_conflito_e_sugestoes_profissional(
        ...
        duracao_min=duracao_min,  # ← PASSA DURAÇÃO
        ...
    )
    
    if not conflito.get("conflito"):
        return {"hora": hora}
    return None
```

**Problema:** `duracao_min` é passado para `verificar_conflito_e_sugestoes_profissional`

### Passo B: Verificação de Conflito com Duração PADRÃO
**Arquivo:** `services/event_service_async.py` linhas 1232-1268

```python
async def verificar_conflito_e_sugestoes_profissional(
    user_id, data, hora_inicio, 
    duracao_min,  # ← RECEBE 60 min (padrão de estimar_duracao(None))
    profissional, servico, ...
):
    # Normaliza hora
    # Converte para datetime
    
    inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
    fim_novo = inicio_novo + timedelta(minutes=duracao_min)  # ← SOMA 60 MIN!
```

**Problema:** Se a consulta for "hoje às 15 sem serviço":
- `duracao_min = 60` (padrão porque servico=None)
- Verifica intervalo: 15:00 → 16:00 (60 minutos)
- Se 15:30-16:00 está ocupado, REJEITA disponibilidade de 15:00

### Passo C: Filtragem de Eventos
**Arquivo:** `services/event_service_async.py` linhas 1404-1498

```python
for eid, ev in eventos.items():
    # Verifica se evento "entra na agenda"
    entra_agenda = evento_deve_entrar_na_agenda(
        evento_id=eid,
        evento=ev,
        data_consulta=data
    )
```

Função: `evento_deve_entrar_na_agenda()` (linhas 30-60)
```python
def evento_deve_entrar_na_agenda(evento_id, evento, data_consulta=None) -> bool:
    # Sem profissional → FALSE
    # Status cancelado/removido → FALSE  ✅ (OK)
    # Sem estrutura (data/hora_inicio/hora_fim) → FALSE
    # Data diferente → FALSE
    
    return True  # ← SÓ eventos confirmados "entram"
```

**Status:** ✅ FUNCIONA CORRETAMENTE — descarta cancelados, filtra data

---

## 💀 O PROBLEMA COMPLETO

### Cenário: "Tem horário para hoje às 15 com a Bruna?"

```
1. GPT retorna: intencao='consulta', servico=None, confianca=85
2. Sistema rejeita ANTES de chegar em P0.6.2
3. SE não rejeitasse, chamaria: estimar_duracao(None) → 60 min
4. Verificaria intervalo: 15:00 - 16:00
5. Se 15:30-16:00 ocupado → disponibilidade FALSA (mas deveria perguntar serviço!)
6. Nunca pergunta: "qual serviço?"
```

---

## 📝 CONTRATO PROPOSTO (2 ETAPAS)

### ETAPA A: Consulta Sem Serviço (Apenas Disponibilidade)
**Chamador:** Cliente diz "Tem horário para hoje às 15 com a Bruna?"

**Entrada:**
- `intencao = "consulta"`
- `profissional = "Bruna"`
- `data = "2026-12-19"`
- `horario = "15:00"`
- `servico = None`  ← SEM SERVIÇO

**Lógica:**
1. Não chamar `estimar_duracao(None)`
2. Buscar APENAS se horário exato 15:00 está ocupado
3. Não somar duração (não sabemos duração sem serviço)
4. Responder: "Sim, 15:00 com a Bruna está disponível" ou "Não, 15:00 está ocupado"
5. Perguntar: "Qual serviço você gostaria consultar?"

**Saída:**
- Preservar contexto: `profissional="Bruna"`, `data="2026-12-19"`, `horario="15:00"`
- **Não criar evento**
- Continuar para ETAPA B

**Função a criar/modificar:**
- `consultar_disponibilidade_horario_puro(profissional, data, horario)` 
  - Sem `servico`
  - Sem `duracao_min`
  - Apenas verifica: algum evento ocupa exatamente esse horário?

### ETAPA B: Validar Serviço e Consultar Duração
**Chamador:** Cliente responde "Coloração"

**Entrada:**
- Contexto preservado: `profissional="Bruna"`, `data="2026-12-19"`, `horario="15:00"`
- Novo: `servico="coloracao"`

**Lógica:**
1. Validar `"coloracao"` no catálogo de Bruna
2. Buscar duração real: `estimar_duracao("coloracao")` → 120 min
3. Verificar intervalo: 15:00 - 17:00
4. Se 15:00-17:00 livre → "Disponível para coloração"
5. Se ocupado → "Indisponível, sugerir outros horários ou profissionais"

**Saída:**
- Responder com disponibilidade confirmada
- **Não criar evento** (é apenas consulta)

---

## 🧪 TESTES NECESSÁRIOS

| Teste | Entrada | Esperado | Arquivo |
|-------|---------|----------|---------|
| T1 | Consulta sem serviço, horário livre | "Disponível às 15" + pergunta serviço | `test_p07_t1_...` |
| T2 | Consulta sem serviço, horário ocupado | "Indisponível às 15" + sugestões | `test_p07_t2_...` |
| T3 | Consulta com serviço explícito | Valida duração real, verifica intervalo | `test_p07_t3_...` |
| T4 | Evento cancelado não bloqueia | Ignora eventos.status="cancelado" | `test_p07_t4_...` |
| T5 | Evento confirmado bloqueia | Verifica intervalo completo (duração) | `test_p07_t5_...` |
| T6 | Sugestões respeitam expediente | Não sugere fora de 09:00-18:00 | `test_p07_t6_...` |
| T7 | Nenhum evento criado em consulta | Contexto salvo, evento.confirmado=False | `test_p07_t7_...` |
| T8 | Multi-tenant isolado | Consulta tenant A não vê Eventos tenant B | `test_p07_t8_...` |

---

## 🔧 ARQUIVOS E FUNÇÕES MAPEADAS

| Arquivo | Função | Linhas | Papel |
|---------|--------|--------|-------|
| `utils/gpt_utils.py` | `estimar_duracao()` | 121-126 | **PROBLEMA**: retorna 60 se servico=None |
| `router/principal_router.py` | P0.6.2 fallback (bloco) | 5406-5506 | **REJEITA** consulta sem serviço |
| `router/principal_router.py` | (onde deveria ir) | 5769-5777 | **NUNCA ALCANÇA** — rejeitado antes |
| `router/principal_router.py` | `buscar_horario_ajuste_no_dia()` | 3645-3718 | Passa `duracao_min` para conflito |
| `services/event_service_async.py` | `verificar_conflito_e_sugestoes_profissional()` | 1232-1600+ | Verifica intervalo com duracao |
| `services/event_service_async.py` | `evento_deve_entrar_na_agenda()` | 30-60 | Filtra eventos — ✅ CORRETO |

---

## 🎯 CAUSA RAIZ CONSOLIDADA

**Nível 1 (Imediato):** P0.6.2 fallback não diferencia `intencao="consulta"` de `intencao="agendamento_direto"`

**Nível 2 (Raiz):** `estimar_duracao(None)` retorna 60 como padrão, permitindo verificação de intervalo sem serviço

**Nível 3 (Arquitetural):** Sistema assume que TODA consulta de disponibilidade precisa de duração conhecida (serviço). Mas consulta sem serviço deveria apenas verificar se horário exato está ocupado.

---

## ✅ CHECKLIST PRÉ-IMPLEMENTAÇÃO

- ☐ P0.6.2 bifurcação (if intencao=="consulta")
- ☐ Nova função: `consultar_disponibilidade_horario_puro()` — SEM serviço, SEM duracao
- ☐ Preservar contexto (profissional, data, horario) no estado `consulta_disponibilidade_aberta`
- ☐ T1-T8 testes especificados
- ☐ `evento_deve_entrar_na_agenda()` já filtra cancelados corretamente
- ☐ Isolamento multi-tenant verificado em `verificar_conflito_e_sugestoes_profissional()`

---

**Data:** 2026-10-21  
**Status:** ✅ AUDITORIA COMPLETA (READ-ONLY)  
**Próximo:** Implementar com bifurcação P0.6.2 + nova função consulta-sem-serviço

