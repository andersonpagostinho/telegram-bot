# 🔍 AUDITORIA: Fluxo de Consulta de Disponibilidade — Cliente vs Dono

**Data:** 2026-06-02  
**Objetivo:** Entender por que dono passa pelo fluxo determinístico e cliente passa pelo GPT

---

## 📊 EVIDÊNCIAS POR ARQUIVO E LINHA

### 1. **ENTRADA CLIENTE (Telegram Text)**

**Arquivo:** `handlers/gpt_text_handler.py`

| Linha | Código | Função |
|-------|--------|--------|
| 387-392 | `resposta_info = await responder_consulta_informativa(texto, user_id)` | Tenta responder com determinístico |
| 388-389 | `if resposta_info: await update.message.reply_text(resposta_info); resposta_ja_enviada = True; return` | Se responde, SAI (não vai para GPT) |
| 395-401 | `resultado_raw = await processar_com_gpt_com_acao(user_id=user_id, texto_usuario=texto, contexto=contexto, instrucao=INSTRUCAO_SECRETARIA)` | Se NÃO respondeu, chama **GPT DIRETO** |

**Problema:** Cliente chama GPT DIRETO, pulando `roteador_principal` que tem o fluxo com classificador determinístico.

---

### 2. **ENTRADA DONO (WhatsApp/Telegram Voice)**

**Arquivo:** `handlers/bot.py`

| Linha | Código | Função |
|-------|--------|--------|
| 242 | `resposta = await roteador_principal(user_id, mensagem, update, context)` | Chama roteador com fluxo determinístico |
| 316 | `resposta = await roteador_principal(user_id, mensagem, update, context)` | Chama roteador com fluxo determinístico |

**Vantagem:** Dono passa por `roteador_principal` que tem toda lógica de classificação.

---

### 3. **FLUXO DETERMINÍSTICO (principal_router.py)**

**Arquivo:** `router/principal_router.py`

#### Camada 1: Classificação da Intenção
| Linha | Código | Função |
|-------|--------|--------|
| 2968 | `class_intencao = classificar_intencao_conversacional(texto_usuario, ctx)` | Extrai intenção com classificador |
| 2994-2997 | `ctx["intencao_conversacional"] = class_intencao.get("intencao_conversacional")` | Salva intenção no contexto |

#### Camada 2: Mapeamento Intenção → Objetivo
| Linha | Código | Função |
|-------|--------|--------|
| 3013-3014 | `elif intencao_conv == "consulta_disponibilidade_servico": objetivo_conversacional = "consultar_disponibilidade_por_servico"` | **CHAVE:** Se intenção for consulta de serviço, objetivo fica determinístico |

#### Camada 3: Bloqueio do GPT
| Linha | Código | Função |
|-------|--------|--------|
| 3087-3096 | `if ( (not intencao_atual or intencao_atual == "indefinida") and interpretacao_conv.get("intencao") == "indefinida" ... )` | **BLOQUEIO:** Se já tem intenção, GPT NÃO é chamado |
| 3168-3171 | `else: print(f"🔒 [GPT BLOQUEADO]")` | Imprime quando GPT é bloqueado |

#### Camada 4: Resposta Determinística
| Linha | Código | Função |
|-------|--------|--------|
| 9229-9235 | `eh_consulta_pura = (ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico" or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico")` | Detecta consulta pura |
| 9235 | `if eh_consulta_pura: print("🛡️ [CONSULTA PURA RESPONDIDA SEM GPT]")` | **BLOQUEIO:** Se é consulta pura, retorna ANTES de chamar GPT |
| 9286 | `return await _send_and_stop(context, user_id, resposta_texto)` | Retorna resposta determinística e SAI |
| 9288 | `resposta_gpt = await chamar_gpt_com_contexto(...)` | Só chega aqui se NÃO é consulta pura |

---

### 4. **CLASSIFICADOR (services/classificador_conversa.py)**

**Arquivo:** `services/classificador_conversa.py`

| Linha | Código | Função |
|-------|--------|--------|
| 329-330 | `if f["tem_pergunta"] and f["tem_contexto_servico"]: return {"intencao_conversacional": "consulta_disponibilidade_servico", "confianca": 85}` | **CHAVE:** Se tem pergunta + contexto de serviço, classifica como consulta |
| 25-31 | `tem_pergunta = ("?" in t) or _tem(r"^(tem|...)") or _tem(r"\b(quem|qual|...)") or _tem(r"\bquem\s+(voce|você)?\s*tem\b")` | Detecta pergunta (CORRETO após patch) |
| 55-60 | `tem_contexto_servico = _tem(r"\b(cabelo|corte|escova|...)\b")` | Detecta contexto de serviço |

---

### 5. **FUNÇÃO DETERMINÍSTICA (informacao_service.py)**

**Arquivo:** `services/informacao_service.py`

| Linha | Código | Função |
|-------|--------|--------|
| 71-70 | `async def responder_consulta_informativa(mensagem, user_id)` | Função que responde deterministicamente |
| 169-200 | Lógica para "quem tem disponível" | **PROBLEMA:** Esta função é chamada ANTES do roteador no cliente |
| 176 | `if any(p in mensagem_normalizada for p in palavras_chave_disponibilidade):` | Verifica palavras-chave específicas |

---

## 🎯 CAUSA RAIZ

```
CLIENTE (gpt_text_handler):
  responder_consulta_informativa()  ← retorna string ou None
    ├─ Se retorna string → envia resposta e para
    └─ Se retorna None → chama processar_com_gpt_com_acao() DIRETO
       └─ GPT vê contexto com profissionais
       └─ GPT retorna resposta finalizada

DONO (bot.py → roteador_principal):
  roteador_principal()  ← fluxo completo com classificador
    ├─ classificar_intencao_conversacional()  ← detecta "consulta_disponibilidade_servico"
    ├─ objetivo = "consultar_disponibilidade_por_servico"
    ├─ eh_consulta_pura = True
    ├─ if eh_consulta_pura: retorna determinístico SEM chamar GPT
    └─ Se não for consulta pura, chama chamar_gpt_com_contexto()
```

---

## 🔴 PROBLEMA ESPECÍFICO

1. **Cliente chama `responder_consulta_informativa` que é TOO NARROW:**
   - Linha 176: só detecta palavras-chave específicas como "quem tem disponível"
   - Para pergunta genérica como "quem você tem?" ou "tem profissional?", pode não detectar
   - Se não detectar, retorna None → cai no GPT

2. **Cliente pula o `roteador_principal` inteiramente:**
   - Nunca passa por `classificar_intencao_conversacional` (linha 2968)
   - Nunca obtém objetivo_conversacional (linha 3014)
   - Nunca passa pela verificação "eh_consulta_pura" (linha 9229)
   - Vai direto para `processar_com_gpt_com_acao` (linha 395)

3. **Dono sempre passa por `roteador_principal`:**
   - Sempre classifica intenção
   - Se intenção = "consulta_disponibilidade_servico" → objetivo = "consultar_disponibilidade_por_servico"
   - Bloqueia GPT na linha 9229-9235
   - Retorna resposta determinística

---

## ⚠️ POR QUE CLIENTE VAI PARA GPT

**Cenário: Cliente pergunta "Quem você tem disponível amanhã de manhã para corte?"**

```
responder_consulta_informativa(mensagem):
  ├─ Checa: "servi" in msg AND ("oferec" OR "tem")? → NÃO (não é listagem de serviços)
  ├─ Checa: "quem faz" or "qual profissional"? → NÃO
  ├─ Checa: "quanto custa"? → NÃO
  ├─ Checa: "quem tem disponivel"? → TALVEZ... depende da normalização
  │  ├─ Se SIM → retorna disponibilidade determinística ✅
  │  └─ Se NÃO → retorna None ❌
  └─ Return None → cliente cai no GPT (linha 395)
```

**Problema:** A detecção em linha 176 é muito específica:
```python
palavras_chave_disponibilidade = [
    "quem tem disponivel", "quem tem disponível",
    "quem voce tem disponivel", "quem você tem disponível",
    "tem disponivel", "tem disponível",
    "quem esta disponivel", "quem está disponível"
]
```

Mas **perguntas variam:**
- "Quem você tem amanhã?" → NÃO em lista
- "Tem alguém disponível?" → NÃO em lista
- "Qual profissional tem disponível?" → NÃO em lista

---

## 📋 ARQUIVOS CRÍTICOS

| Arquivo | Responsabilidade | Status |
|---------|-----------------|--------|
| `handlers/gpt_text_handler.py` linha 395 | Cliente chama GPT direto | ❌ PROBLEMA |
| `handlers/bot.py` linha 316 | Dono chama roteador | ✅ CORRETO |
| `router/principal_router.py` linhas 9229-9286 | Bloqueia GPT se é consulta pura | ✅ CORRETO |
| `services/informacao_service.py` linha 176 | Palavras-chave muito específicas | ⚠️ NARROW |
| `services/classificador_conversa.py` linhas 329-330 | Detecta consulta_disponibilidade_servico | ✅ CORRETO |

---

## 💡 PATCH MÍNIMO PROPOSTO

**Opção A (RECOMENDADA):** Cliente usa roteador como dono

Mudar em `handlers/gpt_text_handler.py` linha 395:

```python
# ANTES (problema):
resultado_raw = await processar_com_gpt_com_acao(...)

# DEPOIS (solução):
resultado_raw = await roteador_principal(user_id, texto, update, context)
```

Isso faz cliente passar por toda a lógica de classificação (linhas 2968-9286) como dono.

**Risco:** Pode haver diferenças de contexto ou behavior entre gpt_text_handler e bot.py que precisam ser testadas.

---

**Opção B:** Expandir palavras-chave em responder_consulta_informativa

Mudar em `services/informacao_service.py` linha 169-174:

```python
# Adicionar mais variações
palavras_chave_disponibilidade = [
    "quem tem disponivel", "quem tem disponível",
    "quem voce tem", "quem você tem",  # ← NOVA
    "tem disponivel", "tem disponível",
    "qual profissional", "qual profissional tem",  # ← NOVA
    "tem alguem", "tem alguém",  # ← NOVA
    ...
]
```

**Risco:** Falsos positivos. "Qual profissional?" sem contexto de serviço pode não ser consulta de disponibilidade.

---

## 🚨 REGRESSÕES POTENCIAIS

Se implementar Opção A:
1. ❌ Cliente pode ter comportamento diferente do esperado (precisa testar textos, áudio, etc)
2. ❌ Pode quebrar fluxos específicos de Telegram que funcionam em gpt_text_handler
3. ⚠️ Precisa verificar se context manager (contexto_memoria) se comporta igual

---

## ✅ PRÓXIMO PASSO

**Não aplique patch sem aprovação.**

User deve decidir:
1. Usar Opção A (usar roteador para cliente também)?
2. Usar Opção B (expandir palavras-chave)?
3. Usar Opção C (algo diferente)?

Recomendo **Opção A** pois mantém cliente e dono no mesmo fluxo determinístico.
