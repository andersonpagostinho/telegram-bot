# 🔍 AUDITORIA: Diferenças Funcionais gpt_text_handler vs bot.py

**Data:** 2026-06-02  
**Objetivo:** Mapear tudo que seria perdido/alterado se trocar cliente de `processar_com_gpt_com_acao` para `roteador_principal`

---

## 📊 COMPARAÇÃO ESTRUTURAL

```
┌─────────────────────────────────────────────────────────────┐
│ gpt_text_handler.py (CLIENTE — Telegram)                    │
├─────────────────────────────────────────────────────────────┤
│ processar_texto(update, context)                            │
│  ├─ ANTES_1: Validações básicas (linhas 46-124)            │
│  ├─ ANTES_2: Carregar memória (linha 64)                   │
│  ├─ ANTES_3: Buscar dados e montar contexto (linhas 125-400)
│  ├─ CALL: processar_com_gpt_com_acao(linha 395)            │
│  ├─ DEPOIS_1: Pós-processamento (linhas 404-520)           │
│  ├─ DEPOIS_2: Execução de ações (linhas 582-605)           │
│  ├─ DEPOIS_3: Resposta final (linhas 611-620)              │
│  └─ DEPOIS_4: Limpeza (linhas 626-636)                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ bot.py (DONO — WhatsApp/Telegram Voice)                     │
├─────────────────────────────────────────────────────────────┤
│ tratar_mensagens_gerais(update, context)                    │
│  ├─ ANTES_1: Atalhos de cancelamento (linhas 110-133)      │
│  ├─ ANTES_2: Carregar contexto (linha 180)                 │
│  ├─ ANTES_3: Validações de fluxo (linhas 196-228)          │
│  ├─ CALL: roteador_principal(linha 316)                    │
│  ├─ DEPOIS_1: Resposta enviada (linhas 319-332)            │
│  └─ DEPOIS_2: Erro/logging (linhas 334-350)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 ANÁLISE DETALHADA

### A) VALIDAÇÕES ANTES DA CHAMADA

#### gpt_text_handler.py (CLIENTE)

| Linha | Validação | Impacto |
|-------|-----------|--------|
| 47-56 | Importação de profissionais — responde se "importou?" | ❌ Dono não usa Telegram, só cliente |
| 59-61 | E-mail em espera — desvia para enviar_email_natural() | ❌ Fluxo específico do cliente |
| 68-77 | Limpeza seletiva: se "todos profissionais", limpa contexto | ⚠️ PERDERIA se trocar para roteador |
| 82-108 | Busca eventos diretos — responde antes de GPT | ⚠️ PERDERIA: roteador não faz isso |
| 125-127 | Valida se cliente cadastrado | ✅ roteador também valida |
| 141-149 | Busca tarefas/eventos reais | ✅ roteador também busca, mas diferente |
| 196-233 | Detecção inteligente de serviço mencionado (fuzzy match) | ⚠️ DIFERENTE: roteador usa normalização |
| 235-252 | Exportação de agenda em Excel | ❌ PERDERIA: roteador não faz |
| 279-315 | Salva memória inicial (serviço, data_hora) | ⚠️ DIFERENTE: roteador também salva, mas em outro lugar |

**Resumo:** `gpt_text_handler` tem MUITOS atalhos antes de chamar GPT:
- Eventos diretos (linha 82-108)
- E-mails filtrados (linha 346-359)
- Exportação de agenda (linha 251)
- Resposta informativa (linha 387-392)

Se trocar para `roteador_principal`, **TODAS essas respostas diretas desaparecem**.

#### bot.py (DONO)

| Linha | Validação | Impacto |
|-------|-----------|--------|
| 114-132 | Atalho de cancelamento por número | ❌ Específico de WhatsApp/Voice, cliente não usa |
| 180 | Carrega contexto temporário | ✅ Mesmo que cliente |
| 197-213 | Desistência de fluxo se "aguardando_escolha_horario" | ⚠️ Cliente também tem isso? Precisa verificar |
| 216-228 | Mensagens neutras (obrigado, valeu, etc) | ⚠️ Cliente RESPONDE DIRETO, dono nega |
| 230-267 | Confirmação pendente de agendamento | ⚠️ Cliente também tem isso mas em outro lugar |
| 271-306 | Fluxo de configuração inicial | ❌ Específico de dono |

**Resumo:** `bot.py` é MAIS ENXUTO:
- Não busca eventos, e-mails, ou tarefas antes
- Deixa tudo para `roteador_principal`
- Menos atalhos

---

### B) ANTES DA CHAMADA: CONTEXTO MONTADO

#### gpt_text_handler.py monta contexto INTEIRO (linha 362-381)

```python
contexto = {
    "usuario": usuario,                          # 👤 Dados do usuário
    "tarefas": tarefas,                         # 📋 Tarefas reais do Firebase
    "eventos": eventos,                         # 📆 Eventos reais do Firebase
    "emails": emails,                           # 📧 E-mails reais do Google
    "profissionais": profissionais_filtrados    # 👥 Profissionais filtrados
}

# MAIS INJEÇÕES:
contexto["profissional_escolhido"] = ...       # 🧠 Memória de profissional
contexto["ultima_acao"] = ...                  # 📝 Última ação
contexto["ultima_intencao"] = ...              # 💭 Última intenção
contexto["dados_anteriores"] = ...             # 🔄 Dados anteriores
```

**Passado para:** `processar_com_gpt_com_acao(..., contexto=contexto, ...)`

#### roteador_principal (bot.py linha 316)

```python
resposta = await roteador_principal(user_id, mensagem, update, context)
```

**PASSO:** `user_id` (string), `mensagem` (string), `update` (Telegram), `context` (ContextTypes)

**Diferença crítica:**
- `gpt_text_handler`: Passa contexto MONTADO e ESTRUTURADO
- `bot.py`: Passa apenas `user_id` e `mensagem`, roteador RECONSTRÓI tudo dentro

Vamos ver o que roteador_principal faz internamente (linha 2706+):
```python
async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    # Linha ~2800+: carrega contexto INTEIRO do Firestore
    # Mas: SEM tarefas, eventos, e-mails pré-carregados!
```

---

### C) CONTEXTO_MEMORIA vs CONTEXTO_ROTEADOR

#### gpt_text_handler (linha 64, 372-381)

```python
contexto_memoria = await carregar_contexto_temporario(user_id)
# Contém: estado_fluxo, draft_agendamento, profissional_escolhido, ...

# Injeta dados de memória no contexto a ser passado:
if profissional_escolhido:
    contexto["profissional_escolhido"] = profissional_escolhido
if contexto_memoria.get("ultima_acao"):
    contexto["ultima_acao"] = contexto_memoria["ultima_acao"]
```

#### roteador_principal (carrega dinamicamente)

```python
# Dentro de roteador_principal, carrega memória:
ctx = await carregar_contexto_temporario(user_id)
# Usa essa memória para classificação e fluxo
```

**Diferença:** `gpt_text_handler` INJETA memória no contexto de GPT. `roteador_principal` usa memória para DECISÕES de classificação, não necessariamente injeta em GPT.

---

### D) BUSCA DE DADOS REAIS

#### gpt_text_handler busca TUDO (linhas 149-340)

```python
tarefas = await obter_tarefas_lista(user_id)              # 📋 Tarefas
eventos_dict = await buscar_subcolecao(...)              # 📆 Eventos
eventos = [e["descricao"] ...]                           # Formata eventos
emails_raw = await ler_emails_google(user_id, num=15)    # 📧 E-mails
profissionais_dict = await buscar_subcolecao(...)        # 👥 Profissionais
```

**Resultado:** Contexto tem dados REAIS para GPT processar.

#### roteador_principal — NÃO busca tarefas/eventos/e-mails

```python
# Dentro roteador_principal():
# - Busca profissionais ✅ (linha ~8700)
# - Carrega contexto temporário ✅
# - MAS NÃO busca tarefas, eventos, e-mails ❌
```

**Implicação:** Se cliente trocar para roteador, **tarefas e e-mails não serão contextualizadas ao GPT**.

---

### E) PÓS-PROCESSAMENTO (O QUE ACONTECE APÓS PROCESSAR_COM_GPT_COM_ACAO)

#### gpt_text_handler (MUITO PÓS-PROCESSAMENTO)

| Linha | Processamento | Descrição |
|-------|---------------|-----------|
| 405-409 | Executa ação diretamente | Se resultado tem "acao", executa_acao_gpt |
| 415-418 | Guard-rail tarefas | Se usuário pediu tarefas, force busca |
| 421-426 | Resposta simples | Se só tem resposta, envia e sai |
| 449-520 | Fallbacks massivos | Corrige resposta se GPT errou (7 fallbacks!) |
| 529-563 | Validação de eventos/profissionais | Verifica se resposta bate com dados reais |
| 571-595 | Execução de ações específicas | Arquivo, email, followup, etc |
| 596-608 | Notificação agendada | Se criar_tarefa, agenda notificação |
| 611-622 | Resposta final + limpeza | Envia resposta e limpa contexto |

**Total: 10+ fallbacks e correções!**

#### roteador_principal (PÓS-PROCESSAMENTO)

| Linha | Processamento | Descrição |
|-------|---------------|-----------|
| 319-332 | Envia resposta ou ação | Simples: resposta ou acao |

**Total: 1 resposta, nada mais!**

---

### F) TRATAMENTO DE CANAIS (Telegram vs WhatsApp)

#### gpt_text_handler — ASSUMIDO TELEGRAM

```python
# Linha 40: async def processar_texto(update: Update, ...)
# update.message.text         # Telegram specific
# update.message.from_user    # Telegram specific
# update.message.reply_text() # Telegram specific
```

**PROBLEMA:** Se trocar para roteador, perderá:
- `update.message.reply_text()` é Telegram
- Se roteador tentar chamar, pode quebrar em WhatsApp

#### bot.py — AGNÓSTICO (Mas com suporte a WhatsApp)

```python
# Linha 83: async def tratar_mensagens_gerais(update: Update, ...)
# Também usa update.message.text (genérico)
# Mas roteador_principal suporta ambos os canais internamente
```

---

### G) LIMPEZA E FINALIZAÇÃO

#### gpt_text_handler (Linha 626-636)

```python
async def verificar_fim_fluxo_e_limpar(user_id, resultado):
    acao = resultado.get("acao")
    
    # Limpa contexto SE ação for: criar_evento, criar_tarefa, enviar_email, criar_followup
    if acao in ["criar_evento", "criar_tarefa", "enviar_email_natural", "criar_followup"]:
        await limpar_contexto(user_id)
    
    # Limpa também se frases de encerramento
    if any(p in resposta for p in ["obrigado", "obrigada", "valeu"]):
        await limpar_contexto(user_id)
```

#### roteador_principal — Limpeza interna

```python
# roteador_principal tem sua própria lógica de limpeza
# NÃO há garantia que faça igual a gpt_text_handler
```

---

## ⚠️ O QUE SERIA PERDIDO SE TROCAR DIRETO

### PERDERIA COMPLETAMENTE ❌

| Funcionalidade | Linha (gpt_text_handler) | Crítico? |
|---|---|---|
| Resposta direta para "eventos de hoje" | 82-108 | 🔴 ALTO |
| Resposta direta para "eventos amanhã" | 82-108 | 🔴 ALTO |
| Exportação de agenda em Excel | 235-252 | 🟡 MÉDIO |
| Resposta direta para e-mails filtrados | 346-359 | 🔴 ALTO |
| Busca de tarefas no contexto de GPT | 149, 364 | 🔴 ALTO |
| Busca de eventos no contexto de GPT | 151, 365 | 🔴 ALTO |
| Busca de e-mails no contexto de GPT | 332, 366 | 🔴 ALTO |
| 7 Fallbacks de correção de resposta | 449-563 | 🟡 MÉDIO |
| Notificação agendada para tarefas | 601-608 | 🟡 MÉDIO |

### COMPORTAMENTO DIFERENTE ⚠️

| Aspecto | gpt_text_handler | roteador_principal |
|---|---|---|
| Detecção de serviço | Fuzzy match (difflib) | Normalização exata |
| Classificação de intenção | Em `responder_consulta_informativa` | Em `classificador_conversa` + `roteador` |
| Tratamento de confirmação | Na memória injetada | Na memória carregada internamente |
| Resposta "Conteúdo recebido da IA" | Nunca (sempre responde) | Pode acontecer |

---

## 🛡️ WRAPPER SEGURO?

### Opção 1: Wrapper que chamaria roteador mas preserva atalhos

```python
async def processar_texto_unificado(update, context):
    user_id = str(update.message.from_user.id)
    texto = update.message.text
    
    # 1️⃣ ATALHOS GPTA_text_handler (preservar)
    # Linha 82-108: Eventos diretos
    # Linha 346-359: E-mails diretos
    # Linha 235-252: Exportação
    # Linha 387-392: Resposta informativa
    
    if evento_direto:
        await responder_evento_direto(...)
        return
    
    # 2️⃣ Chamar roteador (para dono + cliente)
    resposta = await roteador_principal(user_id, texto, update, context)
    
    # 3️⃣ PÓS-PROCESSAMENTO gpt_text_handler (preservar)
    # Linhas 449-563: Fallbacks
    # Linhas 596-622: Notificação + resposta
    
    if resposta_precisa_fallback:
        resposta = aplicar_fallback(resposta, contexto)
    
    await enviar_resposta(update, resposta)
    await verificar_fim_fluxo_e_limpar(user_id, resposta)
```

**Vantagem:** Preserva atalhos do cliente, unifica fluxo de classificação
**Risco:** Complexo, difícil de manter, pode ter conflitos

### Opção 2: NÃO trocar cliente para roteador, CORRIGIR roteador

```
Status quo: Cliente → processar_com_gpt_com_acao (direto)
Problema: Não passa por classificador

Solução: Fazer processar_com_gpt_com_acao chamar classificador INTERNAMENTE
         Isso evita trocar o handler do cliente
```

**Vantagem:** Mínimo de mudança, cliente continua funcionando igual
**Risco:** Pode haver divergência entre duas classificações

---

## 📋 PATCH MÍNIMO DE MENOR RISCO

### Recomendação: **NÃO TROCAR HANDLER**

Ao invés de trocar `gpt_text_handler` para usar `roteador_principal`, **fazer `processar_com_gpt_com_acao` chamar o classificador DETERMINÍSTICO antes de chamar GPT**.

#### Implementação sugerida (gpt_service.py):

```python
async def processar_com_gpt_com_acao(
    texto_usuario: str,
    contexto: dict,
    instrucao: str,
    user_id: str | None = None,
):
    # ... codigo atual ...
    
    # NOVA: Classificar como determinístico PRIMEIRO
    from services.classificador_conversa import classificar_intencao_conversacional
    
    intencao_class = classificar_intencao_conversacional(texto_usuario, contexto)
    
    # Se é consulta_disponibilidade_servico, usar determinístico (nunca chamar GPT)
    if intencao_class.get("intencao_conversacional") == "consulta_disponibilidade_servico":
        # Retornar resposta determinística, não chamar GPT
        return resposta_deterministica(...)
    
    # Caso contrário, chamar GPT normal
    return await chamar_gpt_normal(...)
```

**Vantagem:**
- ✅ Cliente mantém todos seus atalhos (eventos, e-mails, etc)
- ✅ Cliente passa por classificador determinístico
- ✅ Mínima mudança no código
- ✅ Menor risco de regressão

**Risco:**
- ⚠️ Duplica lógica de classificação (uma em cliente via gpt_text_handler, outra em gpt_service)
- ⚠️ Precisaria sincronizar as duas classificações

---

## 🎯 RESUMO FINAL

| Quesito | Valor |
|---------|-------|
| Pode trocar cliente direto para roteador? | ❌ NÃO (perderia 10+ funcionalidades) |
| Existe wrapper seguro? | ⚠️ COMPLEXO (teria que duplicar muita lógica) |
| Patch mínimo de menor risco? | ✅ SIM — Chamar classificador em gpt_service.py ANTES de GPT |

**Próximo passo:** Implementar classificador em `gpt_service.py` linha 170+ (após carregar contexto) para bloquear GPT se for consulta_disponibilidade_servico.
