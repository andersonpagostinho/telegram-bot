# ANÁLISE — REGRA DE EQUIVALÊNCIA DO DRAFT

**Data:** 2026-10-01  
**Status:** INVESTIGAÇÃO SEM ALTERAÇÕES DE CÓDIGO  
**Objetivo:** Definir regra determinística para decidir: preservar vs substituir draft

---

## A) CAMPOS DETERMINÍSTICOS PARA "MESMO PEDIDO"

### Resposta Direta

Três campos determinam a equivalência de um agendamento:

| Campo | Obrigatório | Tipo | Representação no Draft |
|-------|------------|------|------------------------|
| **servico** | ✅ Sim | string | `draft["servico"]` |
| **data_hora** | ✅ Sim | ISO 8601 | `draft["data_hora"]` = "2026-10-02T09:00:00" |
| **profissional** | ❌ Não | string \| None | `draft["profissional"]` |

### Definição

**Mesmo Pedido:** Todos os 3 campos idênticos entre draft atual e nova mensagem

**Novo Pedido:** Qualquer um desses 3 campos diverge

**Casos Especiais:**
- Profissional = None em ambos os lados = mesma situação (nenhum prof definido)
- Profissional = None em draft, mas menciona profissional em mensagem = NOVO
- Profissional = "Carla" em draft, mensagem não menciona prof = MESMA situação

---

## B) COMO O SISTEMA REPRESENTA CADA COMPONENTE

### 1. Draft Atual

**Localização:** `ctx["draft_agendamento"]`

**Estrutura:**
```python
{
    "servico": "corte",           # string ou None
    "data_hora": "2026-10-02T09:00:00",  # ISO 8601 ou None
    "profissional": None          # string (nome) ou None
}
```

**Código que acessa (linha 2148):**
```python
draft = (ctx or {}).get("draft_agendamento") or {}
```

### 2. Classificação/Tipo de Ajuste

**Localização:** `ctx["tipo_ajuste_incremental"]`

**Valores possíveis:**
- `"data"` — ajuste apenas de data (ex: "outro dia")
- `"horario"` — ajuste apenas de horário (ex: "mais cedo")
- `"profissional"` — mudança de profissional
- `"servico"` — mudança de serviço
- `None` — sem ajuste incremental ou agendamento completo novo

**Código que seta (linha 3656):**
```python
ctx["tipo_ajuste_incremental"] = class_intencao.get("tipo_ajuste_incremental")
```

### 3. Dados Extraídos da Mensagem Atual

**Função existente:** `detectar_alteracao_draft_agendamento()` (linha 2139)

**O que ela extrai:**
```python
servico_atual = draft.get("servico") or ctx.get("servico")
profissional_atual = draft.get("profissional") or ctx.get("profissional_escolhido")

# Novos dados da mensagem:
dt_novo = interpretar_data_e_hora(texto_usuario)  # linha 2224
servico_detectado = await encontrar_servico_mais_proximo(texto_usuario, dono_id)  # linha 2245

# Detecta profissional (implícito na função):
for _, p in profissionais.items():
    nome_norm = normalizar(nome)
    if nome_norm in texto_normalizado:
        # Encontrou novo profissional
```

**Como representa:**
- Data/hora: `datetime` object → convertido para ISO `"2026-10-02T09:00:00"`
- Serviço: string (ex: "corte")
- Profissional: string (ex: "Bruna") ou nada (None)

---

## C) FUNCÕES EXISTENTES QUE JÁ COMPARAM/MESCLAM

### ✅ FUNÇÃO IDEAL ENCONTRADA

**Nome:** `detectar_alteracao_draft_agendamento()`  
**Localização:** router/principal_router.py:2139-2290  
**Status:** ✅ REUTILIZÁVEL PARA ESTE PROPÓSITO

### O Que Ela Faz

Compara draft com novos dados extraídos da mensagem:

```python
async def detectar_alteracao_draft_agendamento(
    texto_usuario: str,
    ctx: dict,
    dono_id: str,
    cliente_id: str = None
) -> dict | None:
```

**Retorna:**

| Caso | Retorno |
|------|---------|
| Profissional diferente | `{"tipo": "profissional", "valor": "Bruna"}` |
| Data/hora diferente | `{"tipo": "data_hora", "valor": "2026-10-02T10:00:00"}` |
| Serviço diferente | `{"tipo": "servico", "valor": "escova"}` |
| **Nenhuma alteração** | **`None`** ← Esta é a chave! |

### Por Que Reutilizar

```
✅ Já detecta todas as 3 dimensões (servico, data_hora, profissional)
✅ Já normaliza dados para comparação
✅ Já trata casos especiais (horário relativo, data aberta)
✅ Já retorna None quando não há alteração (P3 guard, linha 2234-2235)
✅ Pronto para usar em P0.5
```

### Como Usar em P0.5

Na linha 3668, ANTES de deletar, chamar:

```python
if (
    ctx.get("motivo_estado") == "profissional_nao_atende_servico"
    and ctx.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]
):
    # NOVO: Comparar com detectar_alteracao
    alteracao = await detectar_alteracao_draft_agendamento(
        texto_usuario,
        ctx,
        dono_id,
        cliente_id
    )
    
    if alteracao is None:
        # Reiteration: mesmo agendamento
        ctx.pop("motivo_estado", None)  # Apenas limpar o bloqueador
    else:
        # Novo agendamento: limpar tudo
        ctx.pop("motivo_estado", None)
        ctx.pop("estado_fluxo", None)
        ctx.pop("draft_agendamento", None)
        # ... resto do P0.5
```

---

## D) CLASSIFICAÇÃO DOS 6 CENÁRIOS

### Contexto Comum

```
draft_agendamento = {
    "servico": "corte",
    "data_hora": "2026-10-02T09:00:00",
    "profissional": None
}

motivo_estado = "profissional_nao_atende_servico"  (Carla foi rejeitada)
```

---

### CENÁRIO 1

**Mensagem:** "quero corte amanhã às 9"

| Campo | Draft | Mensagem | Equals? |
|-------|-------|----------|---------|
| servico | corte | corte | ✅ SIM |
| data_hora | 2026-10-02T09:00:00 | 2026-10-02T09:00:00 | ✅ SIM |
| profissional | None | (não mencionado) | ✅ SIM |

**Intenção Detectada:** `agendamento_direto` (parece novo porque texto não menciona profissional)

**Dados Extraídos:** servico="corte", data_hora="2026-10-02T09:00:00", prof=None

**Comparação:** Idêntico ao draft

**Ação P0.5:** 
- `detectar_alteracao_draft_agendamento()` retorna `None`
- ✅ **PRESERVAR** draft
- ✅ Limpar apenas `motivo_estado`
- Fluxo continua: "Qual profissional?"

---

### CENÁRIO 2

**Mensagem:** "quero corte amanhã às 9 com Bruna"

| Campo | Draft | Mensagem | Equals? |
|-------|-------|----------|---------|
| servico | corte | corte | ✅ SIM |
| data_hora | 2026-10-02T09:00:00 | 2026-10-02T09:00:00 | ✅ SIM |
| profissional | None | Bruna | ❌ NÃO |

**Intenção Detectada:** `agendamento_direto` (menciona profissional novo)

**Dados Extraídos:** servico="corte", data_hora="2026-10-02T09:00:00", prof="Bruna"

**Comparação:** Profissional diferente

**Ação P0.5:**
- `detectar_alteracao_draft_agendamento()` retorna `{"tipo": "profissional", "valor": "Bruna"}`
- ✅ **SUBSTITUIR** draft com novo profissional
- ✅ Limpar `estado_fluxo`, `motivo_estado`, etc.
- Fluxo continua: Validar Bruna / disponibilidade

**Motivo:** Usuário explicitamente escolheu profissional diferente. É agendamento novo.

---

### CENÁRIO 3

**Mensagem:** "quero escova"

| Campo | Draft | Mensagem | Equals? |
|-------|-------|----------|---------|
| servico | corte | escova | ❌ NÃO |
| data_hora | 2026-10-02T09:00:00 | (não mencionado) | ? |
| profissional | None | (não mencionado) | ✅ SIM |

**Intenção Detectada:** `agendamento_direto` (novo serviço)

**Dados Extraídos:** servico="escova", data_hora=None, prof=None

**Comparação:** Serviço diferente

**Ação P0.5:**
- `detectar_alteracao_draft_agendamento()` retorna `{"tipo": "servico", "valor": "escova"}`
- ✅ **SUBSTITUIR** draft com novo serviço
- ✅ Limpar `estado_fluxo`, `motivo_estado`, `draft_agendamento`
- Fluxo continua: "Qual data/hora para escova?"

**Motivo:** Novo serviço = novo agendamento

---

### CENÁRIO 4

**Mensagem:** "com outra pessoa?"

| Campo | Draft | Mensagem | Equals? |
|-------|-------|----------|---------|
| servico | corte | (não mencionado) | ✅ SIM |
| data_hora | 2026-10-02T09:00:00 | (não mencionado) | ✅ SIM |
| profissional | None | (não mencionado, apenas "outra") | ✅ SIM |

**Intenção Detectada:** `ajuste_incremental` (tipo: profissional ou indefinida)

**Dados Extraídos:** servico=corte (do draft), data_hora (do draft), prof=None (nenhum mencio nado especificamente)

**Comparação:** Idêntico ao draft

**Ação P0.5:**
- `detectar_alteracao_draft_agendamento()` retorna `None`
- ✅ **PRESERVAR** draft
- ✅ Limpar apenas `motivo_estado`
- Fluxo continua: Apresentar profissionais válidos

**Motivo:** Usuário quer mesmo agendamento, apenas trocar profissional. Reiteration com ajuste.

---

### CENÁRIO 5

**Mensagem:** "amanhã às 14h"

| Campo | Draft | Mensagem | Equals? |
|-------|-------|----------|---------|
| servico | corte | (não mencionado) | ✅ SIM |
| data_hora | 2026-10-02T09:00:00 | 2026-10-02T14:00:00 | ❌ NÃO |
| profissional | None | (não mencionado) | ✅ SIM |

**Intenção Detectada:** `ajuste_incremental` (tipo: horario)

**Dados Extraídos:** servico=corte (do draft), data_hora="2026-10-02T14:00:00" (nova), prof=None

**Comparação:** Horário diferente

**Ação P0.5:**
- `detectar_alteracao_draft_agendamento()` retorna `{"tipo": "data_hora", "valor": "2026-10-02T14:00:00"}`
- ✅ **PRESERVAR** draft (não é agendamento_direto, é ajuste)
- ✅ Aplicar apenas ajuste de horário
- Fluxo continua: Mesclar novo horário com draft existente

**Motivo:** Classificação é `ajuste_incremental`, não `agendamento_direto`. P0.5 não deveria interceptar.

**Nota:** P0.5 só atua se `intencao_conversacional in ["agendamento_direto", "pedido_aberto_temporal"]`

---

### CENÁRIO 6

**Mensagem:** "quero corte sexta às 15"

| Campo | Draft | Mensagem | Equals? |
|-------|-------|----------|---------|
| servico | corte | corte | ✅ SIM |
| data_hora | 2026-10-02T09:00:00 | 2026-10-05T15:00:00 | ❌ NÃO (sexta é 05-10) |
| profissional | None | (não mencionado) | ✅ SIM |

**Intenção Detectada:** `agendamento_direto` (novo dia/hora mencionado explicitamente)

**Dados Extraídos:** servico="corte", data_hora="2026-10-05T15:00:00", prof=None

**Comparação:** Data/hora diferente

**Ação P0.5:**
- `detectar_alteracao_draft_agendamento()` retorna `{"tipo": "data_hora", "valor": "2026-10-05T15:00:00"}`
- ✅ **SUBSTITUIR** draft com nova data/hora
- ✅ Limpar `estado_fluxo`, `motivo_estado`, `draft_agendamento`
- Fluxo continua: "Qual profissional para corte na sexta às 15h?"

**Motivo:** Mesmo serviço, mas data/hora completamente diferentes. É novo agendamento (mesmo que serviço igual).

---

## RESUMO DOS 6 CENÁRIOS

| # | Mensagem | Draft Match? | Intenção | Ação | Motivo |
|---|----------|-------------|----------|------|--------|
| 1 | "corte amanhã às 9" | ✅ 100% | agendamento_direto | **PRESERVAR** | Reiteration exata |
| 2 | "corte às 9 com Bruna" | ❌ Prof | agendamento_direto | **SUBSTITUIR** | Prof diferente |
| 3 | "quero escova" | ❌ Serviço | agendamento_direto | **SUBSTITUIR** | Serviço diferente |
| 4 | "com outra pessoa?" | ✅ 100% | ajuste_incremental | **PRESERVAR** | Reiteration + ajuste |
| 5 | "amanhã às 14h" | ❌ Hora | ajuste_incremental | **PRESERVAR** (ajuste) | P0.5 não atua |
| 6 | "corte sexta às 15" | ❌ Data_hora | agendamento_direto | **SUBSTITUIR** | Data nova |

---

## E) LOCALIZAÇÃO EXATA E DADOS DISPONÍVEIS

### Onde P0.5 Toma Decisão

**Arquivo:** router/principal_router.py  
**Linha:** 3668-3680  
**Função:** roteador_principal()

### Parâmetros Disponíveis Nesse Ponto

```python
async def roteador_principal(
    user_id: str,
    contexto: dict,
    texto_usuario: str,  ← Mensagem original
    dono_id: str,
    cliente_id: str,
    context: Any
):
    # ... linhas 1-3665 ...
    
    # PONTO DE DECISÃO (linha 3668):
    if (
        ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and ctx.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]
    ):
        # Dados disponíveis AQUI:
        # ✅ texto_usuario — mensagem original
        # ✅ ctx — contexto completo com draft_agendamento
        # ✅ dono_id — para buscar profissionais
        # ✅ cliente_id — para consultas
        # ✅ ctx["intencao_conversacional"] — já classificado
        # ✅ ctx["tipo_ajuste_incremental"] — já extraído
        # ✅ ctx["draft_agendamento"] — draft atual
```

### Dados Necessários para Decisão

| Dado | Fonte | Status |
|------|-------|--------|
| Draft atual | `ctx["draft_agendamento"]` | ✅ Disponível |
| Mensagem texto | `texto_usuario` | ✅ Disponível |
| Classificação | `ctx["intencao_conversacional"]` | ✅ Disponível |
| Tipo ajuste | `ctx["tipo_ajuste_incremental"]` | ✅ Disponível |
| Profissionais | `await buscar_subcolecao()` | ✅ Disponível |
| Extrair dados novos | `detectar_alteracao_draft_agendamento()` | ✅ **REUTILIZAR** |

---

## RECOMENDAÇÃO FINAL

### Regra Determinística Proposta

```
IF (
    motivo_estado == "profissional_nao_atende_servico"
    AND intencao_conversacional IN ["agendamento_direto", "pedido_aberto_temporal"]
):
    # NOVO: Chamar função que já existe
    alteracao = AWAIT detectar_alteracao_draft_agendamento(
        texto_usuario,
        ctx,
        dono_id,
        cliente_id
    )
    
    IF alteracao IS NULL:
        # Reiteration: mesmo agendamento
        PRESERVAR draft_agendamento
        LIMPAR ONLY motivo_estado
    ELSE:
        # Novo agendamento: todos os campos divergem
        SUBSTITUIR draft_agendamento
        LIMPAR estado_fluxo, motivo_estado, profissional_rejeitado, etc.
        (resto do P0.5 atual)
```

### Função Existente a Reutilizar

**`detectar_alteracao_draft_agendamento()`** (linha 2139)

- ✅ Já existe
- ✅ Já trata todas as dimensões (servico, data_hora, profissional)
- ✅ Já retorna None para "nenhuma alteração"
- ✅ Pronto para usar em P0.5

### Por Que Funciona

1. **Cenário 1 (Reiteration):** detecta nenhuma alteração → retorna None → PRESERVAR ✓
2. **Cenário 2 (Prof diferente):** detecta alteração profissional → SUBSTITUIR ✓
3. **Cenário 3 (Serviço novo):** detecta alteração serviço → SUBSTITUIR ✓
4. **Cenário 4 (Ajuste):** detecta nenhuma alteração → PRESERVAR ✓
5. **Cenário 5 (Ajuste hora):** tipo_ajuste_incremental=horario, P0.5 não atua (correto) ✓
6. **Cenário 6 (Data nova):** detecta alteração data_hora → SUBSTITUIR ✓

---

**Status:** ✅ ANÁLISE COMPLETA — SEM ALTERAÇÕES DE CÓDIGO

**Próximo Passo:** Aguardando autorização para implementar a solução proposta.
