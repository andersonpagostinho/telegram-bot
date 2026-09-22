# ANÁLISE ARQUITETURAL — Correção para Consulta de Agendamentos do Usuário

**Data:** 2026-09-14  
**Status:** Análise apenas (NENHUMA ALTERAÇÃO IMPLEMENTADA)

---

## 📋 ARQUITETURA ATUAL

### 1. Intenções Conversacionais Existentes

**Arquivo:** `services/classificador_conversa.py:282-375`

| Intenção | Linha | Confiança | Features Ativas | Descrição |
|----------|-------|-----------|-----------------|-----------|
| `confirmacao_agendamento` | P0 (LOTE_3B) | 95 | (from context) | Confirmação de agendamento existente |
| `negacao_confirmacao_agendamento` | 306 | 90 | aguardando_confirmacao=True | Rejeição de agendamento |
| `duvida_confianca_profissional` | 318 | 92 | tem_duvida_confianca | Dúvida sobre profissional |
| `cancelamento` | 325 | 90 | tem_cancelamento | Cancelar agendamento |
| `ajuste_incremental` | 332 | 90 | (tem_ajuste OR tem_ref_profissional) + (tem_fluxo_ativo OR tem_draft) | Alterar detalhes |
| **`consulta_disponibilidade_aberta`** | **339** | **88** | **tem_pergunta + tem_tempo + tem_indefinido** | **⚠️ PROBLEMA: confunde 2 casos** |
| `consulta_disponibilidade_servico` | 356 | 85 | tem_pergunta + tem_contexto_servico | Quem tem disponível? |
| `agendamento_direto` | 359 | 85 | tem_pedido + tem_contexto_servico + tem_tempo | Agendar direto |
| `pedido_aberto_temporal` | 362 | 75 | tem_pedido + tem_tempo | Pedido com tempo (indefinido) |
| `consulta_servico` | 373 | 70 | tem_contexto_servico | Perguntar sobre serviço |
| `indefinida` | 375 | 40 | (fallback) | Sem intenção clara |

---

### 2. Features do Classificador (extrair_features_conversa)

**Arquivo:** `services/classificador_conversa.py:15-133`

```python
tem_fluxo_ativo       # bool(estado_fluxo e estado_fluxo != "idle")
tem_draft             # bool(ctx.get("draft_agendamento"))
tem_confirmacao_pendente  # bool(ctx.get("aguardando_confirmacao_agendamento"))
tem_pergunta          # "?" ou palavras interrogativas
tem_tempo             # "hoje", "amanhã", horários, datas
tem_pedido            # "quero", "preciso", "gostaria", "consegue"
tem_indefinido        # "algo", "alguma", "qualquer", "coisa", "encaixe"
tem_contexto_servico  # "cabelo", "corte", "escova", "manicure", etc.
tem_ajuste            # "mais cedo", "trocar", "mudar", "pensei melhor"
tem_cancelamento      # "cancelar", "desmarcar", "nao vou"
tem_social            # "kkkk", "churrasco", "almoçar", "saudade"
tem_ref_profissional  # "com [nome]", "trocar profissional"
tem_duvida_confianca_profissional  # confirmar + pergunta + referencia profissional + sinais
```

---

### 3. Objetivos Conversacionais Existentes

**Arquivo:** `router/principal_router.py:4124-4163`

| Objetivo | Intenção de Origem | Linha | Função | Significado |
|----------|-------------------|-------|--------|------------|
| `descobrir_servico_para_consulta` | `consulta_disponibilidade_aberta` | 4135 | B-INICIO agendamento | Agendar (descobrir serviço) |
| `consultar_disponibilidade_por_servico` | `consulta_disponibilidade_servico` | 4138 | Consultar avail | Quem faz X? |
| `preparar_prechecagem_agendamento` | `agendamento_direto` | 4141 | Agendamento | Agendamento direto |
| `ajustar_draft_existente` | `ajuste_incremental` | 4144 | Alteração | Remarcar/alterar |
| `avaliar_cancelamento` | `cancelamento` | 4147 | Cancelamento | Avaliar cancelamento |
| `encerrar_fluxo_agendamento` | `negacao_confirmacao_agendamento` | 4150 | Rejeição | Encerrar fluxo |

**Objetivo NÃO implementado:**
- ❌ `consultar_agendamentos_usuario` — não existe

---

### 4. Classificação da Mensagem "Tenho alguma coisa agendada para hoje?"

```
Texto normalizado: "tenho alguma coisa agendada para hoje"

Features detectadas:
✅ tem_pergunta = True         (tem "?")
✅ tem_tempo = True            (tem "hoje")
✅ tem_indefinido = True       (tem "alguma coisa")
❌ tem_fluxo_ativo = False     (estado_fluxo = "idle")
❌ tem_draft = False           (sem draft_agendamento)
❌ tem_contexto_servico = False (não menciona "corte", "escova", etc.)
❌ tem_ajuste = False          (não tem "trocar", "mudar")

Condição da linha 338 (classificador_conversa.py):
if f["tem_pergunta"] and f["tem_tempo"] and f["tem_indefinido"]:
    return {"intencao_conversacional": "consulta_disponibilidade_aberta", ...}

RESULTADO: intencao = "consulta_disponibilidade_aberta" (88% confiança)
```

**Problema aqui:** Essa intenção é usada para 2 casos completamente diferentes:
1. Consultar **meus** agendamentos ("Tenho alguma coisa agendada hoje?")
2. Consultar disponibilidade para **agendar** ("Tem horário disponível hoje?")

---

### 5. Fluxo de Processamento Atual

```
"Tenho alguma coisa agendada para hoje?"
    ↓
[A] CLASSIFICADOR CONTEXTO (classificador_conversa.py)
    └─ modo_conversa = "operacional" (55% confiança)
    ↓
[B] CLASSIFICADOR INTENÇÃO (classificador_conversa.py:338-339)
    └─ intencao = "consulta_disponibilidade_aberta" (88% confiança)
    ↓
[C] OBJETIVO CONVERSACIONAL (principal_router.py:4134-4135)
    └─ objetivo = "descobrir_servico_para_consulta"
    ↓
[D] PARSER DATA/HORA (utils/interpretador_datas.py)
    └─ dt = "2026-09-10T09:56:28" (hora do parse, não hora do usuário)
    ↓
[E] MESCLAR (principal_router.py:1600-1651)
    └─ data_hora = "2026-09-10T00:00:00" (sem hora anterior)
    └─ data_sem_hora = True
    ↓
[F] BLOQUEIO HORÁRIO PASSADO (principal_router.py:7555-7558)
    └─ 00:00 <= agora()? SIM
    └─ Chama _perguntar_amanha_mesmo_horario_e_bloquear()
    ↓
[G] RESPOSTA (principal_router.py:4465-4473)
    └─ "Esse horário (10/09/2026 às 00:00) já passou..."
```

---

## 🔴 PROBLEMA CENTRAL

**Não existe intenção/objetivo específico para "CONSULTAR AGENDAMENTOS DO USUÁRIO"**

A mensagem é interpretada como "quero agendar" em vez de "quero ver meus compromissos".

---

## 🟡 OPÇÃO A vs OPÇÃO B

### OPÇÃO A: Nova Intenção Separada

```
Nova intenção: "consultar_agendamentos_usuario"
├─ Detectar por: contexto + features
├─ Diferenciar de "consulta_disponibilidade_aberta"
├─ Criar objetivo correspondente: "consultar_agendamentos_usuario"
├─ Fluxo determinístico:
│  1. Buscar eventos do usuário para data/período
│  2. Formatar resposta
│  3. Enviar para usuário
└─ Risco: Modificações em classificador_conversa.py
```

**Dependências afetadas:**
- `classificador_conversa.py` — adicionar nova intenção
- `principal_router.py` — adicionar novo objetivo + roteamento
- `informacao_service.py` ou novo arquivo — adicionar função de busca

**Risco de regressão:** BAIXO (nova intenção não afeta existentes)

---

### OPÇÃO B: Novo Objetivo Derivado de Intenção Existente

```
Manter intenção: "consulta_disponibilidade_aberta"
├─ Adicionar análise contextual para 2 caminhos:
│  ├─ Path 1: tem_fluxo_ativo = False + outras features
│  │           → objetivo = "consultar_agendamentos_usuario"
│  └─ Path 2: tem_fluxo_ativo = True ou contexto agendamento
│           → objetivo = "descobrir_servico_para_consulta"
├─ Fluxo determinístico (mesmo que OPÇÃO A)
└─ Risco: Modificações apenas em principal_router.py (4134-4150)
```

**Dependências afetadas:**
- `principal_router.py` — adicionar novo objetivo + lógica de diferenciação
- `informacao_service.py` ou novo arquivo — adicionar função de busca

**Risco de regressão:** MUITO BAIXO (mesma intenção, novo objetivo)

---

## ✅ RECOMENDAÇÃO

**OPÇÃO B — Novo Objetivo derivado de Intenção Existente**

### Justificativa:

1. **Menor Impacto Arquitetural**
   - A intenção `consulta_disponibilidade_aberta` YÁ captura o padrão corretamente
   - Diferenciação pode ser feita em nível de **objetivo** (mais fino que intenção)
   - Modifica apenas 1 arquivo (principal_router.py:4134-4150)

2. **Menor Risco de Regressão**
   - Não altera nenhuma regra de detecção de intenção
   - Não afeta testes de classificação existentes
   - Apenas NOVO objetivo — não muda existentes

3. **Reutilização de Features**
   - Usa mesmas features detectadas (tem_pergunta, tem_tempo, tem_indefinido)
   - Não adiciona complexidade ao classificador

4. **Menor Debt Técnico**
   - 1 objetivo para 1 objetivo em vez de 1 intenção em 2 caminhos
   - Mantém separação clara: intenção = "o que?" / objetivo = "como responder?"

---

## 📊 FLUXO PROPOSTO (OPÇÃO B)

```
"Tenho alguma coisa agendada para hoje?"
    ↓
[CLASSIFICADOR INTENÇÃO] → "consulta_disponibilidade_aberta" ✅ (sem mudança)
    ↓
[OBJETIVO CONVERSACIONAL] ← AQUI DIFERENCIA
    ├─ Se contexto.tem_fluxo_ativo = False
    │  AND não é referência a agendamento existente
    │  → objetivo = "consultar_agendamentos_usuario" (NOVO)
    │
    └─ Senão
       → objetivo = "descobrir_servico_para_consulta" (existente)
    ↓
[ROTEAMENTO POR OBJETIVO]
├─ "consultar_agendamentos_usuario"
│  └─ Buscar eventos do período
│     └─ Responder com lista ou "nenhum"
│
└─ "descobrir_servico_para_consulta"
   └─ Fluxo de agendamento (B-INICIO)
```

---

## 🔧 ARQUIVOS/FUNÇÕES A ALTERAR

### 1. **principal_router.py** (linhas 4134-4163)

**Função:** `processar_mensagem_operacional()`  
**Seção:** CAMADA 1.1 — OBJETIVO CONVERSACIONAL

```python
# ANTES (linhas 4134-4150):
if intencao_conv == "consulta_disponibilidade_aberta":
    objetivo_conversacional = "descobrir_servico_para_consulta"

# DEPOIS:
if intencao_conv == "consulta_disponibilidade_aberta":
    # Diferenciar entre:
    # 1. Consultar Meus agendamentos (novo objetivo)
    # 2. Agendar novo (objetivo existente)
    
    # Heurística: se não há contexto ativo + message pattern
    # → usuário quer ver seus compromissos
    
    if not (ctx.get("estado_fluxo") in [...fluxos de agendamento...]):
        objetivo_conversacional = "consultar_agendamentos_usuario"  # NOVO
    else:
        objetivo_conversacional = "descobrir_servico_para_consulta"
```

**Mudança:** +20 linhas aproximadamente (lógica de diferenciação)

---

### 2. **principal_router.py** (novo bloco após B-INICIO ou paralelamente)

**Função:** `processar_mensagem_operacional()`  
**Nova Seção:** Roteamento para objetivo "consultar_agendamentos_usuario"

```python
# Novo bloco (antes de B-INICIO, ~linha 5000-6000):
if ctx.get("objetivo_conversacional") == "consultar_agendamentos_usuario":
    # Chamar função de consulta de eventos
    # Formatar resposta
    # Enviar ao usuário
    # Return (não continua em B-INICIO)
```

**Mudança:** +80-120 linhas (novo fluxo determinístico)

---

### 3. **services/informacao_service.py** (novo adicional ou existente)

**Opção 3A:** Adicionar função em `informacao_service.py`

```python
async def consultar_agendamentos_usuario(
    user_id: str,
    data: date | None = None
) -> str | None:
    """
    Consultar agendamentos do usuário para data/período específico.
    
    Reutiliza: buscar_eventos_por_intervalo() de event_service_async.py
    Retorna: mensagem formatada ou None
    """
    # 1. Obter tenant_id efetivo
    # 2. Chamar buscar_eventos_por_intervalo(user_id, dia_especifico=data)
    # 3. Formatar resposta
    # 4. Retornar string
```

**Mudança:** +80-100 linhas (nova função)

**OU Opção 3B:** Reutilizar `responder_consulta_informativa()` com novo gatilho

```python
# Em informacao_service.py, adicionar bloco para detectar:
# "tenho agendado", "meus agendamentos", "o que tenho", etc.
# Se detectado: chamar buscar_eventos_por_intervalo() e responder
```

**Mudança:** +50-70 linhas (novo padrão em função existente)

---

### 4. **utils/interpretador_datas.py** (FIX para bug secundário)

**Função:** `interpretar_data_e_hora()`  
**Problema:** Retorna hora do parse em vez de None para data pura

```python
# ANTES (linhas ~239-252):
if ("hoje" in texto_norm or "amanh" in texto_norm) and \
   re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
    # ... monta com hora explícita

# DEPOIS: adicionar check
if ("hoje" in texto_norm or "amanh" in texto_norm):
    if re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
        # ... monta com hora explícita
    else:
        # Sem hora explícita → retornar None (apenas data)
        return None
```

**Mudança:** +5 linhas (proteção)

---

### 5. **principal_router.py** (FIX para bug secundário — horário passado)

**Função:** `processar_mensagem_operacional()`  
**Linhas:** 7555-7558

```python
# ANTES:
if ctx.get("data_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])

# DEPOIS: adicionar guard
if ctx.get("data_hora") and not ctx.get("data_sem_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
```

**Mudança:** +1 linha (guard)

---

## 🔄 FUNÇÕES EXISTENTES REUTILIZÁVEIS

### 1. `buscar_eventos_por_intervalo()` ← **USE ESTA**

**Arquivo:** `services/event_service_async.py:192-256`  
**Assinatura:**
```python
async def buscar_eventos_por_intervalo(
    user_id: str,
    dias: int = 0,
    semana: bool = False,
    dia_especifico: date | None = None
) -> list[dict]
```

**Características:**
- ✅ Já resolve tenant_id efetivamente (cliente → dono)
- ✅ Filtra eventos ignorados automaticamente
- ✅ Retorna list de eventos com event_id preservado
- ✅ Suporta busca por dia específico
- ✅ Tratamento de exceção incluído

**Como usar:**
```python
eventos = await buscar_eventos_por_intervalo(
    user_id=user_id,
    dia_especifico=datetime.strptime("2026-09-10", "%Y-%m-%d").date()
)

for evento in eventos:
    print(f"{evento.get('servico')} com {evento.get('profissional')} às {evento.get('hora_inicio')}")
```

### 2. `formatar_evento()` ← **USE ESTA TAMBÉM**

**Arquivo:** `services/event_service_async.py:895-901`  
**Função:**
```python
def formatar_evento(evento: dict) -> str:
    # Retorna string formatada do evento
```

**Características:**
- ✅ Formata evento para string legível
- ✅ Simples, sem lógica complexa

### 3. `obter_id_dono()` ← **USE PARA TENANT**

**Arquivo:** `services/firebase_service_async.py`  
**Função:**
```python
async def obter_id_dono(user_id: str) -> str:
    # Retorna tenant_id a partir de user_id
```

### 4. `montar_frase_data_legivel()` ← **USE PARA FORMATAÇÃO**

**Arquivo:** `router/principal_router.py:86-102`  
**Função:**
```python
def montar_frase_data_legivel(data_hora_iso: str | None) -> str:
    # "2026-09-10" → "10 de setembro"
    # "2026-09-10T09:00:00" → "hoje às 9h"
```

---

## 🐛 TRATAMENTO DATA SEM HORA

### Problema:
```
Entrada: "hoje"
Parser: interpreta_data_e_hora("hoje") 
Saída: datetime(2026-09-10, 9, 56, 28) ← HORA DO PARSE
Mesclar: transforma em 2026-09-10T00:00:00
Bloqueio: 00:00 <= agora()? SIM → bloqueia como passado
```

### Solução (OPÇÃO B):

**1. Em `utils/interpretador_datas.py`:**

Adicionar proteção para "data pura" (sem hora explícita):

```python
# Linha ~239-252 (bloco "hoje" ou "amanhã" com hora):
if ("hoje" in texto_norm or "amanh" in texto_norm):
    if re.search(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\b", texto_norm):
        # SIM: tem hora explícita → processar normal
        # ...código existente...
    else:
        # NÃO: apenas data, sem hora → retornar None
        return None  # ← NOVO
```

**2. Em `router/principal_router.py`:**

Adicionar guard antes de bloquear horário passado (linha 7555-7558):

```python
# Proteção: não bloquear se é apenas data (sem hora real)
if ctx.get("data_hora") and not ctx.get("data_sem_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
```

**3. Em `router/principal_router.py` (bloco MESCLAR, linhas 1600-1651):**

Preservar flag `data_sem_hora = True` (já está feito, só precisa ser respeitado em outros pontos):

```python
# Já existe (linha 1646):
ctx["data_sem_hora"] = True

# Apenas garantir que downstream respeita essa flag
```

### Resultado:
```
"hoje" sem hora
├─ Parser: retorna None (ou deixa apenas a data)
├─ Mesclar: não transforma em T00:00:00
├─ Bloqueio: não executa (ou verifica data_sem_hora=True)
└─ Resposta: "Você tem corte com Amanda às 10h"
```

---

## 🛡️ GUARD DE HORÁRIO PASSADO

### Atual (linhas 7555-7558):
```python
if ctx.get("data_hora"):
    dt_naive = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive and dt_naive <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
```

### Casos que Deve Tratar:

| Entrada | Deve Bloquear? | Razão | Solução |
|---------|----------------|-------|---------|
| `2026-09-10T15:30` (hora + futura) | NÃO | Horário futuro válido | ✅ Atual funciona |
| `2026-09-10T09:00` (hora + passado) | SIM | Horário passou | ✅ Atual funciona |
| `2026-09-10T00:00` (data_sem_hora=True) | NÃO | Apenas data, sem hora | ⚠️ Guard necessário |
| `2026-09-10` (sem T + sem hora) | NÃO | Apenas data | ✅ Parser não retorna |
| Nenhuma (None) | NÃO | Nada para bloquear | ✅ Atual verifica None |

### Solução Proposta:

```python
# Linhas 7555-7558 (ANTES):
if ctx.get("data_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])

# (DEPOIS):
# ✅ Adicionar guard: se é apenas DATA (sem hora real), não bloquear
if ctx.get("data_hora") and not ctx.get("data_sem_hora"):
    dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
    if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
        return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])
```

**Impacto:** +1 condicional (muito seguro)

---

## 📋 MATRIZ DE CASOS

### Todos os Casos Relevantes

| # | Mensagem | Intenção Esperada | Objetivo Esperado | Ação | Resposta Esperada |
|---|----------|-------------------|-------------------|------|-------------------|
| **1** | "Tenho alguma coisa agendada para hoje?" | consulta_disponibilidade_aberta | `consultar_agendamentos_usuario` (NOVO) | Buscar eventos do usuário hoje | "Você tem: corte com Amanda às 10h, manicure com Larissa às 14h" |
| **2** | "O que tenho agendado hoje?" | consulta_disponibilidade_aberta | `consultar_agendamentos_usuario` (NOVO) | Buscar eventos | "Tenho corte com Amanda às 10h" |
| **3** | "Tenho horário marcado amanhã?" | consulta_disponibilidade_aberta | `consultar_agendamentos_usuario` (NOVO) | Buscar eventos amanhã | "Não, você não tem agendamentos para amanhã" |
| **4** | "Qual é meu próximo horário?" | consulta_disponibilidade_aberta | `consultar_agendamentos_usuario` (NOVO) | Buscar próximo evento | "Seu próximo agendamento é corte com Amanda amanhã às 10h" |
| **5** | "Tenho corte hoje?" | consulta_disponibilidade_aberta | `consultar_agendamentos_usuario` (NOVO) | Buscar eventos de corte | "Sim, você tem corte com Amanda às 10h" |
| **6** | "Tem horário disponível hoje?" | consulta_disponibilidade_aberta | `descobrir_servico_para_consulta` (existente) | Agendar novo | "Qual serviço você quer?" |
| **7** | "Tem vaga amanhã?" | consulta_disponibilidade_aberta | `descobrir_servico_para_consulta` (existente) | Agendar novo | "Qual serviço você quer?" |
| **8** | "Quero marcar um corte hoje" | agendamento_direto | preparar_prechecagem_agendamento (existente) | Agendar direto | "Perfeito! Qual profissional você prefere?" |
| **9** | "Quem tem disponível para corte hoje?" | consulta_disponibilidade_servico | consultar_disponibilidade_por_servico (existente) | Consultar disponibilidade | "Bruna, Joana e Gloria têm disponível" |
| **10** | "Cancelar meu corte de amanhã" | cancelamento | avaliar_cancelamento (existente) | Avaliar cancelamento | "Qual agendamento você quer cancelar?" |

### Análise da Matriz:

**Linhas 1-5:** Novo objetivo `consultar_agendamentos_usuario`
- Padrão: "tenho", "o que tenho", "qual é", pergunta sobre compromissos pessoais
- Diferenciador: contexto.estado_fluxo = "idle" (não em agendamento)

**Linhas 6-7:** Objetivo existente `descobrir_servico_para_consulta`
- Padrão: "tem vaga?", "tem disponível?", perguntas sobre slots abertos
- Diferenciador: contexto.estado_fluxo ≠ "idle" OU intencionalidade de agendar

**Linhas 8-10:** Outros objetivos (não afetados por essa correção)

---

## 🧪 TESTES DE REGRESSÃO NECESSÁRIOS

### TESTES NOVOS (validar nova funcionalidade)

**Teste 1:** Consultar agendamentos do usuário (caso sucesso)
```python
async def test_consultar_agendamentos_usuario_sucesso():
    user_id = "..."
    # Preparar: 2 eventos para "hoje"
    # Entrada: "Tenho alguma coisa agendada para hoje?"
    # Esperado: Listar 2 eventos formatados
    # Assert: resposta contém "corte com Amanda" e "manicure com Larissa"
```

**Teste 2:** Sem agendamentos para o período
```python
async def test_consultar_agendamentos_vazio():
    user_id = "..."
    # Preparar: NENHUM evento para amanhã
    # Entrada: "Tenho algo agendado amanhã?"
    # Esperado: "Não, você não tem agendamentos para amanhã"
    # Assert: resposta contém "não"
```

**Teste 3:** Agendamentos de serviço específico
```python
async def test_consultar_agendamentos_por_servico():
    user_id = "..."
    # Preparar: 3 eventos (2 cortes, 1 manicure)
    # Entrada: "Tenho corte hoje?"
    # Esperado: Listar apenas cortes
    # Assert: resposta contém "corte" mas não "manicure"
```

**Teste 4:** Data/hora específica
```python
async def test_consultar_agendamentos_data_futura():
    user_id = "..."
    # Preparar: evento em 5 dias
    # Entrada: "Tenho agendamento em 5 dias?"
    # Esperado: Encontrar evento
    # Assert: data está correta
```

### TESTES DE REGRESSÃO (garantir que não quebrou)

**Teste R1:** Agendamento novo (objetivo existente)
```python
async def test_agendamento_novo_flow():
    # Entrada: "Quero agendar um corte hoje"
    # Esperado: Objetivo = "preparar_prechecagem_agendamento"
    # Assert: continua pedindo profissional/data/horário
```

**Teste R2:** Consulta de disponibilidade (objetivo existente)
```python
async def test_consulta_disponibilidade_servico():
    # Entrada: "Quem tem disponível para corte hoje?"
    # Esperado: Objetivo = "consultar_disponibilidade_por_servico"
    # Assert: responde com lista de profissionais
```

**Teste R3:** Cancelamento (objetivo existente)
```python
async def test_cancelamento_flow():
    # Entrada: "Cancelar meu corte de amanhã"
    # Esperado: Objetivo = "avaliar_cancelamento"
    # Assert: continua fluxo de cancelamento
```

**Teste R4:** Ajuste de agendamento (objetivo existente)
```python
async def test_ajuste_agendamento():
    # Preparar: cliente em confirmação de agendamento
    # Entrada: "Na verdade, prefiro amanhã"
    # Esperado: Objetivo = "ajustar_draft_existente"
    # Assert: muda data corretamente
```

**Teste R5:** Data sem hora → não bloqueia
```python
async def test_data_sem_hora_nao_bloqueia():
    # Entrada: "Tenho alguma coisa agendada para hoje?"
    # Esperado: data_sem_hora = True
    # Assert: NÃO chama _perguntar_amanha_mesmo_horario_e_bloquear()
```

**Teste R6:** Horário com hora passada → bloqueia
```python
async def test_horario_passado_bloqueia():
    # Entrada: agendamento com data_hora = "2026-09-09T14:00:00" (ontem)
    # Esperado: Objetivo = "descobrir_servico_para_consulta"
    # Assert: Chama _perguntar_amanha_mesmo_horario_e_bloquear()
```

**Teste R7:** Classificação de intenção não muda
```python
def test_classificacao_intencao_estavel():
    # Entrada: "Tenho alguma coisa agendada para hoje?"
    # Esperado: intencao = "consulta_disponibilidade_aberta"
    # Assert: confiança permanece 88
```

**Teste R8:** Features não mudam
```python
def test_features_consulta_aberta():
    # Entrada: "Tenho alguma coisa agendada para hoje?"
    # Esperado: tem_pergunta=True, tem_tempo=True, tem_indefinido=True
    # Assert: exatamente essas features
```

### TESTES DE INTEGRAÇÃO (E2E)

**Teste E1:** Fluxo completo de consulta
```python
async def test_e2e_consultar_agendamentos():
    user_id = "..."
    # Setup: 2 eventos para hoje
    # Mensagem 1: "Tenho alguma coisa agendada para hoje?"
    # Assert: resposta lista os 2 eventos
    # Mensagem 2: (novo tópico)
    # Assert: contexto limpo (estado_fluxo = "idle")
```

**Teste E2:** Mix de operações
```python
async def test_e2e_mix_consulta_e_agendamento():
    user_id = "..."
    # Step 1: "Tenho agendado hoje?" → lista eventos
    # Step 2: "Quero agendar corte amanhã" → entra fluxo agendamento
    # Step 3: Confirmação → agenda novo
    # Assert: ambos os fluxos funcionam sequencialmente
```

### TESTES DE REGRESSÃO CRÍTICOS (P0)

| Teste | Cenário | Assert |
|-------|---------|--------|
| R-P0-01 | 174 P0 regressão suite | Todos passam |
| R-P0-02 | 42 P1 E2E regressão suite | Todos passam |
| R-P0-03 | Timeout gRPC não aumenta | Exit code = 0 |
| R-P0-04 | Classificação estável (1000 iterações) | Intenção não muda |
| R-P0-05 | Multi-tenant isolamento | user_id A não vê agendamentos de user_id B |

---

## 📝 SUMÁRIO EXECUTIVO

### O que mudar?

**Arquivo primário:**
- `router/principal_router.py` (linhas 4134-4150)
  - Adicionar lógica de diferenciação de objetivo
  - Adicionar novo bloco de roteamento (antes de B-INICIO)

**Arquivo secundário:**
- `utils/interpretador_datas.py` (linhas ~239-252)
  - Proteção para data pura (retornar None)
- `router/principal_router.py` (linhas 7555-7558)
  - Guard para data_sem_hora (1 linha)

**Arquivo de suporte:**
- `services/informacao_service.py` OU novo arquivo
  - Função wrapper para consultar agendamentos

### Não mudar:

- ❌ `services/classificador_conversa.py` (intenção YÁ funciona)
- ❌ `schema Firestore` (estrutura já existe)
- ❌ `GPT prompts` (lógica é determinística)
- ❌ `Outros objetivos` (não afetados)

### Risco:

- **Técnico:** MUITO BAIXO (novo objetivo, não altera existentes)
- **Regressão:** MUITO BAIXO (adiciona, não modifica)
- **Tenant/Multi-tenant:** ZERO (reutiliza funções existentes)

### Timeframe:

- **Implementação:** ~4-6 horas
- **Testes:** ~2-3 horas  
- **Validação regressão:** ~1 hora

---

**Próximo Passo:** Aguardando aprovação para implementação (OPÇÃO B recomendada)

