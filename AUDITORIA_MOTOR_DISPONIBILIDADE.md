# 🎯 AUDITORIA: Motor de Disponibilidade — Análise de Reutilização

**Data:** 2026-06-02  
**Objetivo:** Verificar se a resposta determinística de disponibilidade já existe e pode ser reutilizada

---

## 📊 MAPEAMENTO DE FUNÇÕES

### 1️⃣ FUNÇÃO PRINCIPAL: `responder_consulta_informativa()`

**Arquivo:** `services/informacao_service.py`  
**Linhas:** 71-290  
**Tipo:** `async def`

**Propósito:** Responder perguntas informativas SEM chamar GPT

**Fluxo Interno:**

```
responder_consulta_informativa(mensagem, user_id)
├─ Linha 72-73: Normaliza mensagem
├─ Linha 76-78: Resolve dono_id
│
├─ Linha 81-90: [SERVIÇOS] Se "quais serviços oferece?"
│  └─ Retorna lista de serviços (nunca GPT)
│
├─ Linha 93-111: [PROFISSIONAIS] Se "quem faz X?"
│  └─ Retorna lista de profissionais por serviço (nunca GPT)
│
├─ Linha 121-166: [PREÇOS] Se "quanto custa?"
│  └─ Retorna tabela de preços (nunca GPT)
│
├─ Linha 176-288: [DISPONIBILIDADE] ⭐ AQUI ESTÁ
│  │
│  ├─ Linha 176: Detecta "quem tem disponível" via palavras-chave
│  │
│  ├─ Linha 178: Extrai serviço com encontrar_servico_mais_proximo()
│  ├─ Linha 183: Extrai data com interpretar_data_e_hora()
│  ├─ Linha 188-200: Extrai período (manhã, tarde, noite)
│  │
│  ├─ Linha 203: Busca profissionais_por_servico()
│  ├─ Linha 208-235: Determina duração do serviço
│  │
│  ├─ Linha 241-263: MOTOR DETERMINÍSTICO
│  │  │
│  │  ├─ Itera cada horário da janela (30 min step)
│  │  ├─ Linha 249-254: Chama buscar_profissionais_disponiveis_no_horario()
│  │  │            ↑
│  │  │            └─ Motor real que verifica conflitos de agenda
│  │  │
│  │  └─ Filtra profissionais que fazem o serviço (linha 257-260)
│  │
│  ├─ Linha 266-280: Formata com formatar_resposta_disponibilidade()
│  │
│  ├─ Linha 282-288: Se nenhum disponível, retorna sem profissionais
│  │
│  └─ Linha 273-280: USA formatador padrão
│
└─ Linha 290: Se não for nenhuma intenção, retorna None
```

**Retorno:** `str | None`
- Se encontrou pergunta informativa: retorna `str` com resposta completa
- Se não é pergunta informativa: retorna `None`

---

### 2️⃣ FUNÇÃO DE FORMATO: `formatar_resposta_disponibilidade()`

**Arquivo:** `services/informacao_service.py`  
**Linhas:** 27-69  
**Tipo:** `def` (síncrona)

**Assinatura:**
```python
def formatar_resposta_disponibilidade(
    servico: str,                           # ex: "corte"
    data_str: str,                          # ex: "03/06"
    periodo_str: str,                       # ex: "de manhã"
    profissionais_disponiveis: list[str],   # ex: ["Bruna", "Gloria"]
    com_horario: bool = False,              # True se horário específico
    horario: str = None                     # ex: "08:00"
) -> str:
```

**Lógica:**
```
✅ Garante profissionais_disponiveis tem max 3 nomes
✅ Usa formatar_nomes_humanos() para humanizar lista
✅ Se 1 prof: pergunta se "deixa com ela?"
✅ Se 2+ profs: pergunta se "prefere alguma delas?"
✅ NÃO assume horário se apenas período foi informado
```

**Onde é chamada:**
1. Linha 273-280 em `responder_consulta_informativa()` — DISPONIBILIDADE
2. Linha 283-288 em `responder_consulta_informativa()` — NENHUM DISPONÍVEL

**Nunca é chamada em:** GPT, roteador, ou qualquer outro lugar

---

### 3️⃣ FUNÇÃO HELPER: `formatar_nomes_humanos()`

**Arquivo:** `services/informacao_service.py`  
**Linhas:** 13-25  
**Tipo:** `def` (síncrona)

**Lógica:**
```
["Bruna"] → "Bruna"
["Bruna", "Gloria"] → "Bruna ou Gloria"
["Bruna", "Gloria", "Joana"] → "Bruna, Gloria ou Joana"
```

---

## 🔍 ANÁLISE: DETECÇÃO vs CÁLCULO

### Problema: DUAS formas de detectar consulta de disponibilidade

| Método | Arquivo | Linha | Tipo | Precisão |
|--------|---------|-------|------|----------|
| **Palavras-chave** | informacao_service.py | 169-174 | String hardcoded | 🟡 Específica (6 variações) |
| **Classificador** | classificador_conversa.py | 329-330 | Regex inteligente | 🟢 Ampla (`tem_pergunta + tem_contexto_servico`) |

**Palavras-chave detectadas por `responder_consulta_informativa()`:**
```python
"quem tem disponivel", "quem tem disponível",
"quem voce tem disponivel", "quem você tem disponível",
"tem disponivel", "tem disponível",
"quem esta disponivel", "quem está disponível"
```

**Palavras-chave detectadas por classificador (MAIS AMPLAS):**
```
tem_pergunta = (
    "?" in texto
    or _tem(r"^(tem|da|dá|consegue|pode)...")
    or _tem(r"\b(quem|qual|quais|quando|onde|como)\b")
    or _tem(r"\bquem\s+(voce|você)?\s*tem\b")
)
AND
tem_contexto_servico = _tem(r"\b(cabelo|corte|escova|...)\b")
```

**Resultado:** Classificador detecta perguntas que `responder_consulta_informativa` NÃO detecta:
- "Qual profissional tem disponível amanhã?" ← classificador OK, responder_consulta NÃO
- "Quando vocês têm horário?" ← classificador OK, responder_consulta NÃO
- "Tem profissional livre para corte hoje?" ← classificador OK, responder_consulta NÃO

---

## ✅ FLUXO ATUAL: Onde `responder_consulta_informativa` é chamada

### 1. Cliente (gpt_text_handler.py:387)

```python
# Linha 387
resposta_info = await responder_consulta_informativa(texto, user_id)
if resposta_info:
    await update.message.reply_text(resposta_info)
    return  # ⛔ SAI SEM CHAMAR GPT
```

**Status:** ✅ Funciona para cliente quando detecta palavras-chave

**Problema:** Cliente que pergunta "qual profissional tem livre?" não é detectado

---

### 2. Dono (bot.py → principal_router.py:3205)

```python
# Linha 3205 (dentro de roteador_principal, se estado_fluxo == "idle")
resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
if resposta_informativa:
    return await _send_and_stop(context, user_id, resposta_informativa)
```

**Status:** ✅ Funciona para dono quando detecta palavras-chave

---

### 3. Fluxo secundário (principal_router.py:4888)

```python
# Linha 4888 (dentro de fluxo de agendamento, se eh_consulta)
if eh_consulta(texto_usuario):
    resposta_info = await responder_consulta_informativa(mensagem, user_id)
    if resposta_info:
        return await _send_and_stop(context, user_id, resposta_info)
```

**Status:** ✅ Double-check dentro de fluxo de agendamento

---

## 🎯 PROPOSTA: Adicionar em `gpt_service.py`

### Contexto: Onde adicionar

**Arquivo:** `services/gpt_service.py`  
**Função:** `processar_com_gpt_com_acao()` (linha 111+)

**Local de inserção sugerido:** Após carregar contexto (linha ~160), ANTES de chamar GPT

```python
async def processar_com_gpt_com_acao(
    texto_usuario: str,
    contexto: dict,
    instrucao: str,
    user_id: str | None = None,
):
    # ... linhas 117-160: Carregar user_id robusto e profissionais ...
    
    # 🆕 NOVO: Tentar responder com motor determinístico PRIMEIRO
    # Linha ~165
    from services.classificador_conversa import classificar_intencao_conversacional
    
    intencao = classificar_intencao_conversacional(texto_usuario, contexto)
    
    # Se classificou como consulta_disponibilidade_servico, usar motor determinístico
    if intencao.get("intencao_conversacional") == "consulta_disponibilidade_servico":
        # NÃO chamar GPT, usar responder_consulta_informativa
        from services.informacao_service import responder_consulta_informativa
        
        resposta_det = await responder_consulta_informativa(texto_usuario, user_id)
        
        if resposta_det:
            # Retornar no formato que gpt_service espera
            return {
                "resposta": resposta_det,
                "acao": None,
                "dados": {}
            }
    
    # Caso contrário, chamar GPT normalmente
    # ... resto do código ...
```

---

## 🔄 FLUXO UNIFICADO RESULTANTE

```
CLIENTE (gpt_text_handler.py:395)
  └─ processar_com_gpt_com_acao()
     ├─ Classifica intenção
     ├─ Se consulta_disponibilidade_servico:
     │  └─ responder_consulta_informativa()
     │     └─ retorna resposta determinística ✅
     └─ Caso contrário:
        └─ Chamar GPT normal ✅

DONO (bot.py:316 → principal_router.py)
  └─ roteador_principal()
     ├─ Classifica intenção (já faz isso)
     ├─ Se consulta_disponibilidade_servico:
     │  └─ Bloqueia GPT (linha 9229-9235)
     │  └─ Retorna resposta determinística ✅
     └─ Caso contrário:
        └─ Chamar GPT normal ✅
```

---

## 📋 VERIFICAÇÃO: É 100% Reutilizável?

### ✅ SIM, COM CAVEATS

**O que `responder_consulta_informativa()` JÁ faz:**

| Tarefa | Implementado? | Pronto para reusar? |
|--------|---|---|
| Normaliza mensagem | ✅ Linha 72-73 | ✅ SIM |
| Resolve dono_id | ✅ Linha 76-78 | ✅ SIM |
| Extrai serviço | ✅ Linha 178 | ✅ SIM |
| Extrai data | ✅ Linha 183 | ✅ SIM |
| Extrai período | ✅ Linha 188-200 | ✅ SIM |
| Busca profissionais | ✅ Linha 203 | ✅ SIM |
| Determina duração | ✅ Linha 208-235 | ✅ SIM |
| Chama motor determinístico | ✅ Linha 249-254 | ✅ SIM (buscar_profissionais_disponiveis_no_horario) |
| Formata resposta | ✅ Linha 273-280 | ✅ SIM (formatar_resposta_disponibilidade) |

**⚠️ Caveat único:** Detecção por palavras-chave (linha 176) é NARROW

Solução: Classificador já detecta casos que responder_consulta_informativa não detecta. Quando classificador retorna "consulta_disponibilidade_servico", chamar responder_consulta_informativa — se ela retornar None (porque não bateu nas palavras-chave), já sabemos que o usuário PEDIU informação de disponibilidade via classificador.

---

## 🛡️ PATCH MÍNIMO PROPOSTO

### Opção A (RECOMENDADA): Bloquear GPT se classificador disser consulta_disponibilidade_servico

**Localização:** `services/gpt_service.py`  
**Linhas:** Inserir em ~165 (após carregar contexto, antes de GPT)

```python
# 🆕 Bloqueio determinístico de consulta de disponibilidade
if intencao.get("intencao_conversacional") == "consulta_disponibilidade_servico":
    resposta = await responder_consulta_informativa(texto_usuario, user_id)
    if resposta:
        return {"resposta": resposta, "acao": None, "dados": {}}
    # Se responder_consulta retorna None, deixar cair no GPT (edge case)
```

**Vantagem:**
- ✅ Reutiliza 100% da lógica existente
- ✅ Honra classificador (não duplica)
- ✅ Mínimas linhas (~4)
- ✅ Cliente mantém atalhos
- ✅ Dono continua igual

**Risco:**
- ⚠️ Se classificador disser "consulta_disponibilidade_servico" mas responder_consulta_informativa retorna None, cai no GPT (pode ser inesperado)

---

### Opção B: Refactorizar responder_consulta_informativa para aceitar parâmetros já extraídos

**Localização:** Refactorizar `responder_consulta_informativa()`

```python
async def responder_consulta_disponibilidade(
    servico: str,
    data: date,
    periodo_str: str,
    user_id: str
) -> str | None:
    # Versão simplificada que recebe parâmetros já extraídos
    # Executa apenas motor + formatador
```

**Vantagem:**
- ✅ Mais modular
- ✅ Reutilizável em múltiplos pontos

**Risco:**
- ⚠️ Duplicação de código (extração de parâmetros)
- ⚠️ Maior mudança

---

## 🎯 RESUMO FINAL

| Quesito | Resposta |
|---------|----------|
| Existe motor de disponibilidade pronto? | ✅ SIM — `responder_consulta_informativa()` |
| Usa formatador padrão? | ✅ SIM — `formatar_resposta_disponibilidade()` |
| É 100% reutilizável? | ✅ SIM (com caveat de detecção) |
| Recomendação? | **Opção A:** Bloquear GPT em `gpt_service.py` se classificador detectar |
| Linhas de código? | ~4 linhas novas |
| Risco? | 🟢 BAIXO (reutiliza código existente) |

---

## 📌 PRÓXIMO PASSO

**Se aprovar Opção A:**

1. Adicionar em `gpt_service.py` linha ~165:
   - Chamar classificador
   - Se "consulta_disponibilidade_servico", chamar responder_consulta_informativa
   - Se não retorna, deixar cair no GPT

2. Testes:
   - Cliente: "qual profissional tem livre amanhã?" (detecta classificador + responder_consulta)
   - Cliente: "tem profissional disponível?" (detecta classificador, responder_consulta retorna None, cai no GPT)
   - Dono: mesmo fluxo (já tem roteador com mesma lógica)
