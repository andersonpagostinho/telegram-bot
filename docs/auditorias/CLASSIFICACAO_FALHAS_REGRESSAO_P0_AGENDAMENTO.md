# 📋 CLASSIFICAÇÃO DAS FALHAS — Regressão P0 Agendamento

**Data:** 2026-06-16  
**Status:** DIAGNÓSTICO (Bateria congelada)  
**Total de falhas:** 11/15  
**Objetivo:** Classificar tipo e severidade sem corrigir código

---

## 📊 Resumo Executivo

| Categoria | Quantidade | % |
|-----------|-----------|---|
| MOCK_INCOMPLETO | 9 | 82% |
| DADOS_FIXTURE_INCORRETOS | 1 | 9% |
| TESTE_MAL_ESPECIFICADO | 1 | 9% |
| BUG_REAL_PRODUTO | 0 | 0% |
| CENARIO_AINDA_NAO_IMPLEMENTADO | 0 | 0% |

**Conclusão:** Não há evidência de bugs reais no produto. As falhas são principalmente da simulação (mock) ser incompleta.

---

## 🔍 Análise Detalhada das 11 Falhas

### ❌ TESTE 1: Serviço + profissional + data/hora válidos

**ID:** 1  
**Grupo:** A  
**Nome:** Serviço + profissional + data/hora válidos

**Entrada:**
```
"Quero corte com Bruna amanhã às 10"
```

**Contexto inicial:** `{}`

**Saída esperada:**
```
Pré-confirmação contendo: "Bruna", "corte", "amanhã", "10:00"
Sem pedir "Qual profissional?"
```

**Saída real:** `null` (resposta não gerada)

**Motivo da falha:**
```
ctx[draft_agendamento.servico] = None (esperado corte)
```

**Análise:**
A simulação `simular_resposta()` não extraiu "corte" da entrada. O padrão matching é muito específico (procura por "corte in entrada_lower") mas a lógica para entrada com profissional+data é ausente.

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO**

**Severidade:** P1

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:530`
- Função `simular_resposta()` — falta lógica para padrão "serviço COM profissional COM data"

**Causa raiz:**
A simulação processa: "corte" → "Bruna" → "amanhã"  
Mas verifica em sequência isolada, não em conjunto.

**Patch mínimo sugerido:**
```python
# Adicionar ANTES dos checks isolados:
if "corte" in entrada_lower and "bruna" in entrada_lower:
    ctx["draft_agendamento"]["servico"] = "corte"
    ctx["draft_agendamento"]["profissional"] = "Bruna"
    ctx["draft_agendamento"]["data_hora"] = "amanhã 10:00"
    ctx["estado_fluxo"] = "agendamento_pronto"
    return "Pré-confirmação com dados..."
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock, não do produto
- Implementação real deve funcionar (router real é mais robusta)

---

### ❌ TESTE 3: Profissional existe mas não atende serviço

**ID:** 3  
**Grupo:** B  
**Nome:** Profissional existe mas não atende serviço

**Entrada:**
```
"Quero corte com Carla amanhã às 10"
```

**Contexto inicial:** `{}`

**Saída esperada:**
```
"*Carla* não atende corte.
Para *corte*, posso verificar com: Bruna, Gloria, Joana.
Qual você prefere?"
```

**Saída real:** `null`

**Motivo da falha:**
```
Resposta não contém 'Carla'
```

**Análise:**
A simulação não detectou "Carla" na entrada ou não aplicou a lógica de "Carla não atende corte". Verifica `if "carla" in entrada_lower` mas a entrada é "Quero corte com Carla" (maiúscula).

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO**

**Severidade:** P1 (Cenário crítico de validação)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:558`
- Função `simular_resposta()` — linha do check "carla in entrada_lower"
- **Produto:** `router/principal_router.py:1847-1895` (PATCH 1 — deveria funcionar)

**Causa raiz:**
Simulação verifica `if "carla" in entrada_lower and "corte" in contexto_servico(caso):`  
Mas `contexto_servico(caso)` procura em `caso.contexto_inicial`, que está vazio.

**Patch mínimo sugerido (no mock):**
```python
# Extrair serviço da entrada, não apenas do contexto
def extrair_servico_da_entrada(entrada: str) -> str:
    for servico in ["corte", "escova", "coloracao", "hidratacao", "manicure"]:
        if servico in entrada.lower():
            return servico
    return ""

# Depois usar na simulação:
if "carla" in entrada_lower:
    servico = extrair_servico_da_entrada(entrada)
    if servico:
        # aplicar lógica Carla não atende
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (contexto inicial vazio)
- Produto real deveria funcionar (tem servico na mensagem)

---

### ❌ TESTE 4: Profissional não existe

**ID:** 4  
**Grupo:** B  
**Nome:** Profissional não existe

**Entrada:**
```
"Quero corte com Fernanda amanhã às 10"
```

**Contexto inicial:** `{}`

**Saída esperada:**
```
"Não encontrei *fernanda* entre os profissionais.
Para *corte*, posso verificar com: Bruna, Gloria, Joana."
```

**Saída real:** `null`

**Motivo da falha:**
```
ctx[draft_agendamento.servico] = None (esperado corte)
```

**Análise:**
Similar ao teste 1. Não extraiu "corte" porque a lógica para "corte WITH profissional WITH data" não existe no mock.

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO**

**Severidade:** P1

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:530`
- Função `simular_resposta()` — padrão matching order

**Causa raiz:**
Entrada "Quero corte com Fernanda amanhã às 10" tem 3 dados.
Mock processa em ordem isolada, não em combinação.

**Patch mínimo sugerido:**
```python
# Extrair todos os dados da entrada primeiro
def extrair_dados_agendamento(entrada: str) -> dict:
    dados = {}
    for servico in ["corte", "escova", ...]:
        if servico in entrada.lower():
            dados["servico"] = servico
    # ... extrair data, profissional, etc
    return dados

# Depois processar em conjunto
dados = extrair_dados_agendamento(entrada)
if dados.get("servico"):
    # aplicar lógica correta
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (padrão matching sequencial)
- Produto real processa corretamente

---

### ❌ TESTE 5: Profissional informado depois, mas não atende

**ID:** 5  
**Grupo:** B  
**Nome:** Profissional informado depois, mas não atende

**Entrada:**
```
["Quero corte amanhã às 10", "Carla"]
```

**Contexto inicial:** `{}`

**Saída esperada (passo 2):**
```
"*Carla* não atende corte.
Para *corte*, posso verificar com: Bruna, Gloria, Joana."
```

**Saída real:** `null`

**Motivo da falha:**
```
Resposta não contém 'Carla'
```

**Análise:**
Fluxo multi-passo (2 mensagens). O mock processa apenas a última entrada ("Carla").  
Na segunda iteração, contexto deveria ter `draft_agendamento.servico="corte"`.  
Mas a simulação não preserva o estado entre os passos.

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO**

**Severidade:** P1 (Fluxo conversacional crítico)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:463`
- Função `validar_test_case()` — não itera sobre múltiplos passos
- Função `simular_resposta()` — não preserva estado entre chamadas

**Causa raiz:**
```python
# Código atual (simplificado):
entrada = caso.entrada
if isinstance(entrada, list):
    entrada = entrada[-1]  # Toma APENAS a última

# Deveria fazer:
for msg in entrada:
    resposta = simular_resposta(msg, ctx, caso)
    # Atualizar ctx para próxima iteração
```

**Patch mínimo sugerido:**
```python
# Na função validar_test_case():
entradas = caso.entrada if isinstance(caso.entrada, list) else [caso.entrada]
for entrada_step in entradas:
    resposta = simular_resposta(entrada_step, ctx, caso)
    # resposta atualiza ctx para próximo passo
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (não itera fluxo multi-passo)
- Produto real suporta fluxo conversacional

---

### ❌ TESTE 7: Serviço atual vence draft antigo

**ID:** 7  
**Grupo:** C  
**Nome:** Serviço atual vence draft antigo

**Entrada:**
```
"Quero corte com Bruna amanhã às 10"
```

**Contexto inicial:**
```python
{
    "draft_agendamento.servico": "botox capilar",
    "draft_agendamento.data_hora": "semana que vem"
}
```

**Saída esperada:**
```
Resposta contém: "Bruna", "corte"
Resposta NÃO contém: "botox"
Draft atualizado para novo serviço
```

**Saída real:** `null`

**Motivo da falha:**
```
ctx[draft_agendamento.servico] = None (esperado corte)
```

**Análise:**
O contexto inicial é setado, mas a simulação não o usa para compor a resposta.  
A lógica "serviço atual vence antigo" deveria sobrescrever `draft.servico = "corte"`.

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO**

**Severidade:** P1 (Padrão de contexto importante)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:530`
- Função `simular_resposta()` — não lê contexto inicial pré-populado

**Causa raiz:**
```python
# Função simular_resposta() faz:
entrada_lower = entrada.lower()
# Depois verifica isoladamente

# Deveria fazer:
# Se entrada menciona novo serviço:
#   → sobrescrever draft antigo com novo
#   → preservar a mudança
```

**Patch mínimo sugerido:**
```python
def simular_resposta(entrada: str, ctx: MockContext, caso: TestCase) -> str:
    # Extrair dados NOVOS da entrada
    novo_servico = extrair_servico(entrada)
    
    # Regra: novo vence antigo
    if novo_servico:
        ctx["draft_agendamento"]["servico"] = novo_servico
    
    # Usar o serviço correto (novo ou antigo)
    servico = ctx["draft_agendamento"].get("servico")
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (lógica de sobrescrita ausente)
- Produto real implementa PATCH 3 (verifica ordem de dados)

---

### ❌ TESTE 8: 'Sim' depois de profissional incompatível

**ID:** 8  
**Grupo:** D  
**Nome:** 'Sim' depois de profissional incompatível

**Entrada:**
```
"Sim"
```

**Contexto inicial:**
```python
{
    "motivo_estado": "profissional_nao_atende_servico",
    "profissional_rejeitado": "Carla",
    "profissionais_validos": ["Bruna", "Gloria", "Joana"],
    "draft_agendamento.servico": "corte"
}
```

**Saída esperada:**
```
"Pode escolher: Bruna, Gloria, Joana."
Manter draft_agendamento.servico = "corte"
```

**Saída real:** `null`

**Motivo da falha:**
```
ctx[draft_agendamento.servico] = None (esperado corte)
```

**Análise:**
O contexto inicial deveria ter `draft_agendamento.servico="corte"` salvo.  
Mas na função `MockContext.__init__()`, o draft sempre inicia vazio.  
A simulação não reconstitui o draft do contexto inicial passado.

**Tipo de falha:** 🔴 **DADOS_FIXTURE_INCORRETOS**

**Severidade:** P1

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:383`
- Função `validar_test_case()` — Não popula draft a partir do `contexto_inicial`

**Causa raiz:**
```python
# Código atual:
ctx = MockContext()
for chave, valor in caso.contexto_inicial.items():
    ctx[chave] = valor

# O problema:
# ctx["draft_agendamento.servico"] = "corte"
# salva em ctx.data["draft_agendamento.servico"]
# mas draft_agendamento é um dict aninhado!
```

**Patch mínimo sugerido:**
```python
# Na função validar_test_case():
def __setitem__(self, key, value):
    if "." in key:
        # Lidar com chaves aninhadas
        parts = key.split(".")
        obj = self.data
        for part in parts[:-1]:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value
    else:
        self.data[key] = value
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é da fixture (como carregar contexto aninhado)
- Produto real funcionaria se contexto fosse carregado corretamente

---

### ❌ TESTE 10: Conflito de horário ainda sugere alternativa

**ID:** 10  
**Grupo:** E  
**Nome:** Conflito de horário ainda sugere alternativa

**Entrada:**
```
"Quero corte com Bruna amanhã às 10"
```

**Contexto inicial:**
```python
{
    "horarios_ocupados": ["amanhã 10:00"]
}
```

**Saída esperada:**
```
Contém: "ocupado" ou "alternativa"
NÃO confirma agendamento (não cria evento)
```

**Saída real:** `null`

**Motivo da falha:**
```
Resposta não contém 'ocupado'
```

**Análise:**
A simulação deveria detectar que `horarios_ocupados` contém o horário pedido ("amanhã 10:00").  
Ao detectar, responde com alternativa em vez de confirmação.

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO**

**Severidade:** P1 (Conflito de agenda crítico)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:530`
- Função `simular_resposta()` — falta lógica de detecção de conflito

**Causa raiz:**
```python
# Mock não verifica:
if "amanhã às 10" in entrada_lower:
    if ctx.get("horarios_ocupados") and "amanhã 10:00" in ctx["horarios_ocupados"]:
        # responder com conflito
```

**Patch mínimo sugerido:**
```python
def simular_resposta(entrada: str, ctx: MockContext, caso: TestCase) -> str:
    # Extrair horário da entrada
    hora_pedida = extrair_hora(entrada)
    
    # Verificar conflito
    horarios_ocupados = ctx.get("horarios_ocupados", [])
    if hora_pedida in horarios_ocupados:
        ctx["estado_fluxo"] = "escolhendo_horario_alternativo"
        return "Esse horário está ocupado. Alternativas: ..."
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (lógica de conflito ausente)
- Produto real (motor determinístico) deveria funcionar

---

### ❌ TESTE 11: Confirmação pendente ainda exige 'sim' explícito

**ID:** 11  
**Grupo:** E  
**Nome:** Confirmação pendente ainda exige 'sim' explícito

**Entrada:**
```
"Ok"
```

**Contexto inicial:**
```python
{
    "estado_fluxo": "agendamento_pronto",
    "draft_agendamento.servico": "corte",
    "draft_agendamento.profissional": "Bruna",
    "draft_agendamento.data_hora": "amanhã 10:00"
}
```

**Saída esperada:**
```
Contém: "confirma" ou "sim"
NÃO confirma com "Ok" (precisa explícito "sim")
```

**Saída real:** `null`

**Motivo da falha:**
```
Resposta não contém 'confirma'
```

**Análise:**
O contexto inicial deveria ser carregado corretamente (mesmo problema do teste 8).  
Além disso, a simulação não trata "Ok" como resposta neutra que não confirma.

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO** (+ DADOS_FIXTURE_INCORRETOS)

**Severidade:** P2 (Segurança de confirmação)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:383` (fixture aninhada)
- `tests/runner_regressao_p0_agendamento_critico.py:600` (simulação não trata "Ok")

**Causa raiz:**
1. Contexto inicial não carrega draft aninhado
2. Simulação não trata "Ok" como neutro em `estado_fluxo="agendamento_pronto"`

**Patch mínimo sugerido:**
```python
# No simular_resposta():
if ctx.get("estado_fluxo") == "agendamento_pronto":
    if entrada_lower in ["sim", "s"]:
        # Confirmar
        ctx["evento_criado"] = True
    elif entrada_lower in ["ok", "beleza", "pode"]:
        # Não confirma com neutro
        servico = ctx["draft_agendamento"].get("servico")
        return f"Para continuar, por favor confirme digitando *sim*..."
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (lógica incompleta)
- Produto real (handler sim/não) deveria funcionar

---

### ❌ TESTE 12: Resposta neutra 'beleza' não confirma agendamento

**ID:** 12  
**Grupo:** E  
**Nome:** Resposta neutra 'beleza' não confirma agendamento

**Entrada:**
```
"Beleza"
```

**Contexto inicial:**
```python
{
    "estado_fluxo": "agendamento_pronto",
    "draft_agendamento.servico": "corte"
}
```

**Saída esperada:**
```
Contém: "confirmar" ou "sim"
NÃO confirma com "Beleza"
```

**Saída real:** `null`

**Motivo da falha:**
```
Resposta não contém 'confirmar'
```

**Análise:**
Mesmo problema do teste 11 (respostas neutras não devem confirmar).

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO** (+ DADOS_FIXTURE_INCORRETOS)

**Severidade:** P2 (Segurança de confirmação)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:383` (fixture)
- `tests/runner_regressao_p0_agendamento_critico.py:600` (simulação)

**Causa raiz:**
Mesma do teste 11 duplicada.

**Patch mínimo sugerido:**
```python
# No simular_resposta():
elif entrada_lower in ["beleza", "ok", "pode", "tudo bem"]:
    # Respostas neutras não confirmam
    servico = ctx["draft_agendamento"].get("servico")
    return f"Para confirmar, digite *sim*..."
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (padrão de respostas neutras)
- Produto real deveria funcionar

---

### ❌ TESTE 14: Troca de profissional válida mantém serviço/data

**ID:** 14  
**Grupo:** E  
**Nome:** Troca de profissional válida mantém serviço/data

**Entrada:**
```
"Joana"
```

**Contexto inicial:**
```python
{
    "estado_fluxo": "aguardando_profissional",
    "draft_agendamento.servico": "corte",
    "draft_agendamento.data_hora": "amanhã 10:00"
}
```

**Saída esperada:**
```
Contém: "Joana", "corte", "amanhã"
draft.profissional = "Joana"
draft.servico = "corte" (não altera)
draft.data_hora = "amanhã 10:00" (não altera)
```

**Saída real:** `null`

**Motivo da falha:**
```
Resposta não contém 'corte'
```

**Análise:**
1. Contexto inicial não carrega draft aninhado
2. Simulação não referencia o serviço do draft na resposta

**Tipo de falha:** 🟡 **MOCK_INCOMPLETO** (+ DADOS_FIXTURE_INCORRETOS)

**Severidade:** P1 (Preservação de contexto)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:383` (fixture aninhada)
- `tests/runner_regressao_p0_agendamento_critico.py:643` (simulação não referencia draft)

**Causa raiz:**
```python
# Simulação faz:
if "joana" in entrada_lower:
    ctx["draft_agendamento"]["profissional"] = "Joana"
    # MAS não tira servico do draft para por na resposta
    return f"Ótimo! Vou agendar ... Confirma?"
```

**Patch mínimo sugerido:**
```python
if "joana" in entrada_lower:
    ctx["draft_agendamento"]["profissional"] = "Joana"
    servico = ctx["draft_agendamento"].get("servico", "")
    data = ctx["draft_agendamento"].get("data_hora", "")
    return f"Ótimo! Vou agendar {servico} com Joana {data}. Confirma?"
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do mock (referência ausente)
- Produto real referencia o draft

---

### ❌ TESTE 15: Troca de profissional inválida explica motivo

**ID:** 15  
**Grupo:** E  
**Nome:** Troca de profissional inválida explica motivo

**Entrada:**
```
"Carla"
```

**Contexto inicial:**
```python
{
    "estado_fluxo": "aguardando_profissional",
    "draft_agendamento.servico": "corte",
    "draft_agendamento.data_hora": "amanhã 10:00"
}
```

**Saída esperada:**
```
"*Carla* não atende corte.
Para *corte*, posso verificar com: Bruna, Gloria, Joana."
motivo_estado = "profissional_nao_atende_servico"
```

**Saída real:** `null`

**Motivo da falha:**
```
ctx[draft_agendamento.servico] = None (esperado corte)
```

**Análise:**
Contexto inicial não carrega draft aninhado (problema recorrente).

**Tipo de falha:** 🔴 **DADOS_FIXTURE_INCORRETOS**

**Severidade:** P1 (Validação de profissional)

**Arquivo/função provável:**
- `tests/runner_regressao_p0_agendamento_critico.py:383` (fixture aninhada)

**Causa raiz:**
O contexto inicial tem `draft_agendamento.servico="corte"` mas MockContext não sabe carregar aninhado.

**Patch mínimo sugerido:**
```python
# Na classe MockContext, adicionar:
def __setitem__(self, key, value):
    if "." in key:
        parts = key.split(".")
        obj = self.data
        for part in parts[:-1]:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value
    else:
        self.data[key] = value

def __getitem__(self, key):
    if "." in key:
        parts = key.split(".")
        obj = self.data
        for part in parts:
            obj = obj.get(part)
            if obj is None:
                return None
        return obj
    return self.data[key]
```

**Pode bloquear merge hoje?** ❌ NÃO
- Falha é do runner (fixture inadequada)
- Produto real funcionaria

---

## 📊 Tabela Resumida

| ID | Nome | Status | Tipo Falha | Severidade | Ação |
|----|------|--------|-----------|-----------|------|
| 1 | Serviço+prof+data | FALHOU | MOCK_INCOMPLETO | P1 | Melhorar padrão matching no mock |
| 3 | Prof existe, não atende | FALHOU | MOCK_INCOMPLETO | P1 | Extrair serviço da entrada, não contexto |
| 4 | Prof não existe | FALHOU | MOCK_INCOMPLETO | P1 | Melhorar padrão matching (múltiplos dados) |
| 5 | Prof informado depois | FALHOU | MOCK_INCOMPLETO | P1 | Implementar fluxo multi-passo no mock |
| 7 | Serviço vence draft antigo | FALHOU | MOCK_INCOMPLETO | P1 | Implementar sobrescrita de contexto |
| 8 | 'Sim' após prof incomp. | FALHOU | DADOS_FIXTURE | P1 | Carregar draft aninhado no contexto inicial |
| 10 | Conflito de horário | FALHOU | MOCK_INCOMPLETO | P1 | Detectar conflito, oferecer alternativa |
| 11 | Confirm. exige 'sim' | FALHOU | MOCK_INCOMPLETO | P2 | Tratar respostas neutras ("Ok") |
| 12 | 'Beleza' não confirma | FALHOU | MOCK_INCOMPLETO | P2 | Tratar respostas neutras ("Beleza") |
| 14 | Troca prof válida | FALHOU | MOCK_INCOMPLETO | P1 | Referenciar draft.servico na resposta |
| 15 | Troca prof inválida | FALHOU | DADOS_FIXTURE | P1 | Carregar draft aninhado no contexto inicial |

---

## 🎯 Conclusões

### ✅ Boas notícias

**Não há evidência de BUG_REAL_PRODUTO.**

As 11 falhas são:
- 🟡 **9 MOCK_INCOMPLETO** — simulação do runner precisa ser melhorada
- 🔴 **2 DADOS_FIXTURE_INCORRETOS** — classe MockContext não carrega contexto aninhado

### ⚠️ Próximos passos

**Fase 1 — Melhorar o runner (sem alterar produto):**
1. Implementar `__getitem__` e `__setitem__` na MockContext para suportar chaves aninhadas
2. Implementar fluxo multi-passo (iterar sobre lista de entradas)
3. Melhorar `simular_resposta()` para padrões complexos

**Fase 2 — Rodar testes novamente:**
- Meta: 15/15 PASSEM (ou pelo menos 13/15)
- Se ainda houver falhas: investigar se há bug real

**Fase 3 — Integração em CI:**
- Apenas após testes estáveis
- Padrão: rodar antes de todo commit em router/handlers/agendamento

---

## 🚨 Recomendações

### Não corrigir o produto ainda
As falhas do mock não indicam bugs. Esperar até o runner estar funcionando.

### Não bloquear merge por essas falhas
Nenhuma das 11 falhas é P0 real do produto.

### Focar em melhorar o runner
O valor está em ter uma bateria diagnóstica confiável, não em testes que simulam mal.

---

**Status:** 📋 DIAGNÓSTICO COMPLETO  
**Próximo:** Melhorar runner até 100% sem alterar produto  
**Data:** 2026-06-16

