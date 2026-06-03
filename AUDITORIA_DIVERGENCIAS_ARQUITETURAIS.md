# 🔍 AUDITORIA: Divergências Arquiteturais — Cliente vs Dono vs Sistema

**Data:** 2026-06-02  
**Escopo:** Análise completa de fluxos diferentes entre tipos de usuários

---

## 📊 TABELA CONSOLIDADA: Divergências por Arquivo/Linha

| Arquivo | Linha | Fluxo Cliente | Fluxo Dono | Diferença | Risco | Prioridade |
|---------|-------|---------------|-----------|-----------|-------|-----------|
| **handlers/gpt_text_handler.py** | 387 | `responder_consulta_informativa(texto, user_id)` | N/A | Cliente tenta determinístico ANTES de GPT | 🟢 BAIXO | P2 |
| **handlers/gpt_text_handler.py** | 395 | `processar_com_gpt_com_acao(user_id, texto, contexto, INSTRUCAO)` | N/A | Cliente chama GPT DIRETO | 🔴 CRÍTICO | P0 |
| **handlers/gpt_text_handler.py** | 64-381 | Monta contexto: tarefas, eventos, e-mails, profissionais | N/A | Cliente INJETA dados reais no contexto | ⚠️ MÉDIO | P1 |
| **handlers/bot.py** | 180 | N/A | `carregar_contexto_temporario(user_id)` | Dono carrega contexto de memória | 🟢 BAIXO | P2 |
| **handlers/bot.py** | 316 | N/A | `roteador_principal(user_id, mensagem, update, context)` | Dono passa por roteador com fluxo completo | 🟢 BAIXO | P2 |
| **handlers/voice_command_handler.py** | 50 | `processar_com_gpt_com_acao(texto, contexto, INSTRUCAO, user_id)` | N/A | Áudio chama GPT DIRETO (sem roteador) | 🔴 CRÍTICO | P0 |
| **handlers/voice_command_handler.py** | 35-47 | Contexto: FORÇA planosAtivos = ["secretaria"] | N/A | Áudio força plano ativo para não bloquear | ⚠️ MÉDIO | P1 |
| **handlers/acao_handler.py** | 134 | N/A | `responder_consulta_informativa(mensagem, user_id)` | Dono também tenta determinístico ANTES | 🟢 BAIXO | P2 |
| **handlers/acao_handler.py** | 147 | N/A | `buscar_subcolecao(f"Clientes/{user_id}/Profissionais")` | ⚠️ PROBLEMA: Dono usa user_id, não dono_id | 🔴 CRÍTICO | P0 |
| **gpt_text_handler.py** | 77, 305 | `Clientes/{user_id}/MemoriaTemporaria/contexto` | N/A | Cliente salva memória com user_id | 🟢 BAIXO | P2 |
| **bot.py** | 153 | N/A | `buscar_subcolecao(f"Clientes/{user_id}/Profissionais")` | Dono também usa user_id AQUI | 🔴 CRÍTICO | P0 |
| **event_handler.py** | 183, 235 | N/A | `buscar_subcolecao(f"Clientes/{dono_id}/Eventos")` | Event handler usa dono_id corretamente | ✅ CERTO | - |
| **gpt_text_handler.py** | 183 | `buscar_subcolecao(f"Clientes/{id_negocio}/Profissionais")` | N/A | Cliente usa `id_negocio = obter_id_dono(user_id)` ✅ | 🟢 BAIXO | P2 |
| **router/principal_router.py** | 9229-9235 | N/A | `if eh_consulta_pura: bloqueia_gpt()` | Dono bloqueia GPT se consulta pura | ✅ CERTO | - |
| **router/principal_router.py** | 3205 | N/A | `if estado_fluxo=="idle": responder_consulta_informativa()` | Dono tenta determinístico apenas se idle | ⚠️ MÉDIO | P1 |
| **gpt_text_handler.py** | 82-108 | Responde direto: eventos de hoje, amanhã, semana | N/A | Cliente HAS atalho para buscar eventos | ⚠️ MÉDIO | P1 |
| **gpt_text_handler.py** | 235-252 | Exporta agenda em Excel se detecta | N/A | Cliente TEM atalho para exportação | 🟡 BAIXO | P2 |
| **gpt_text_handler.py** | 346-359 | Filtra e-mails por remetente, responde | N/A | Cliente TEM atalho para filtrar e-mails | ⚠️ MÉDIO | P1 |

---

## 🗺️ MAPA DE FLUXOS ATUAL

### **CLIENTE — Telegram Texto (gpt_text_handler.py)**

```
Entrada: processar_texto(update, context)
   ↓
1. Validações básicas (importação, e-mail pendente)
   ↓
2. Carregar contexto_memoria (linha 64)
   ↓
3. ATALHOS (linhas 68-252):
   ├─ Listar profissionais? → responde direto
   ├─ Exportar agenda? → send_arquivo
   ├─ Filtrar e-mails? → formata + responde
   ├─ Eventos de hoje? → responde direto
   ├─ Eventos semana? → responde direto
   └─ Continue se nenhum atalho
   ↓
4. Buscar dados reais (tarefas, eventos, e-mails, profissionais)
   ↓
5. Montar contexto INTEIRO (tarefas, eventos, e-mails, profs) — linha 362-381
   ↓
6. Injetar memória (profissional_escolhido, ultima_acao, etc) — linha 372-381
   ↓
7. Tentar responder_consulta_informativa() — linha 387
   ├─ Se retorna: responde + atualiza contexto + volta
   └─ Se None: continua
   ↓
8. ✅ CHAMAR processar_com_gpt_com_acao() DIRETO — linha 395
   ↓
9. Pós-processamento (7 fallbacks, correções automáticas) — linhas 405-563
   ↓
10. Responder + Limpar contexto — linhas 611-622
```

**Problemas:**
- ❌ Pula roteador inteiramente
- ❌ Chama GPT direto sem classificador
- ❌ Tem atalhos que dono não tem
- ❌ Injeta contexto diferente do dono

---

### **DONO — WhatsApp/Telegram Voice (bot.py → principal_router.py)**

```
Entrada: tratar_mensagens_gerais(update, context)
   ↓
1. Atalhos de cancelamento (número) — linha 114-132
   ↓
2. Carregar contexto temporário — linha 180
   ↓
3. Verificações de fluxo (confirmação, desistência) — linhas 196-267
   ↓
4. Detectar config inicial — linhas 271-306
   ↓
5. ✅ CHAMAR roteador_principal() — linha 316
   │
   └─ Dentro roteador_principal (linha 2706+):
      ├─ Classificar intenção (linha 2968)
      │  └─ Se consulta_disponibilidade_servico:
      │     └─ Bloqueia GPT (linha 9229-9235)
      │     └─ Retorna determinístico
      │
      ├─ Se não é consulta pura:
      │  └─ Chamar GPT
      │
      └─ Retornar resposta

6. Enviar resposta — linhas 319-332
```

**Vantagens:**
- ✅ Passa por classificador obrigatoriamente
- ✅ Bloqueia GPT para consultas de disponibilidade
- ✅ Motor determinístico aplicado
- ✅ Sem atalhos que quebram fluxo

---

### **ÁUDIO — Telegram Voice (voice_command_handler.py)**

```
Entrada: processar_comando_voz(update, context, texto_transcrito)
   ↓
1. Buscar dados do usuário
   ↓
2. Montar contexto (força planosAtivos = ["secretaria"])
   ↓
3. ❌ CHAMAR processar_com_gpt_com_acao() DIRETO — linha 50
   │  (SEM roteador, SEM classificador, SEM atalhos)
   ↓
4. Executar ação do GPT
   ↓
5. Responder
```

**Problemas:**
- ❌ Pula roteador inteiramente
- ❌ Chama GPT direto
- ❌ FORÇA plano ativo (pode desbloquear features não pagas)
- ❌ Sem motor determinístico

---

## 🔴 DIVERGÊNCIAS CRÍTICAS (P0)

### 1. **Cliente/Áudio pulam roteador**

**Problema:** Cliente (gpt_text_handler) e Áudio (voice_command_handler) chamam `processar_com_gpt_com_acao()` DIRETO

**Impacto:**
- ❌ Não passa por classificador determinístico
- ❌ Não bloqueia GPT para consultas de disponibilidade
- ❌ Não usa motor de conflitos
- ❌ Responde com "[Conteúdo recebido da IA]" em vez de resposta formatada

**Evidência:**
- `gpt_text_handler.py:395` → `processar_com_gpt_com_acao()`
- `voice_command_handler.py:50` → `processar_com_gpt_com_acao()`
- `principal_router.py:316` → `roteador_principal()` ✅ (dono)

**Patch Mínimo:** 
- ✅ JÁ IMPLEMENTADO: Bloqueio em `gpt_service.py:167` (classificador + responder_consulta_informativa)

---

### 2. **Profissionais buscados com user_id em vez de dono_id**

**Problema:** `acao_handler.py:147` e `bot.py:153` buscam profissionais com user_id

**Impacto:**
- ❌ Se user_id = cliente, busca profissionais do CLIENTE (erro)
- ❌ Se user_id = dono, por coincidência funciona
- ❌ **QUEBRA se cliente tenta agendar**

**Evidência:**
```python
# ❌ ERRADO (acao_handler.py:147)
profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}

# ✅ CERTO (event_handler.py:183)
dono_id = await obter_id_dono(user_id)
eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos")
```

**Patch Mínimo:**
```python
# acao_handler.py:147
dono_id = await obter_id_dono(user_id)
profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
```

---

## ⚠️ DIVERGÊNCIAS MÉDIAS (P1)

### 1. **Cliente tem atalhos que dono não tem**

**Problema:** Cliente (gpt_text_handler) responde direto para:
- "Eventos de hoje?" (linha 82-108)
- "Exportar agenda?" (linha 235-252)
- "E-mails do Itaú?" (linha 346-359)

**Impacto:**
- ⚠️ Comportamento inconsistente
- ⚠️ Dono não recebe mesma facilidade
- ⚠️ Cliente pode desincronizar de memória

**Patch Mínimo:** Mover atalhos para roteador ou remover

---

### 2. **Dono só tenta determinístico se `estado_fluxo == "idle"`**

**Problema:** `principal_router.py:3205` chama `responder_consulta_informativa()` APENAS se idle

**Impacto:**
- ⚠️ Durante fluxo de agendamento, dono pode ficar preso no GPT
- ⚠️ Consulta de disponibilidade não é bloqueada em fluxo ativo

**Evidência:**
```python
# principal_router.py:3203-3208
if estado_fluxo == "idle":
    resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
```

**Patch Mínimo:** Remover condição `estado_fluxo == "idle"`

---

### 3. **Áudio força `planosAtivos = ["secretaria"]`**

**Problema:** `voice_command_handler.py:39-40` força plano ativo

**Impacto:**
- ⚠️ Pode desbloquear features não pagas
- ⚠️ Usuário sem plano ativo consegue agendar por voz

**Evidência:**
```python
# voice_command_handler.py:39-40
"planosAtivos": list(set((dados_usuario.get("planosAtivos") or []) + ["secretaria"])),
```

**Patch Mínimo:** Validar plano antes de forçar

---

## 🟢 O QUE JÁ ESTÁ CERTO

| Fluxo | Arquivo | Linha | Status |
|-------|---------|-------|--------|
| Cliente usa `obter_id_dono()` para profissionais | gpt_text_handler.py | 182 | ✅ CERTO |
| Evento handler usa dono_id | event_handler.py | 183, 235 | ✅ CERTO |
| Dono bloqueia GPT se consulta pura | principal_router.py | 9229-9235 | ✅ CERTO |
| Cliente tenta determinístico antes | gpt_text_handler.py | 387 | ✅ CERTO |
| Bloqueio de disponibilidade implementado | gpt_service.py | 167 | ✅ IMPLEMENTADO |

---

## 📋 PONTOS QUE DEVEM CONTINUAR DIFERENTES

| Ponto | Motivo | Risco se unificar |
|-------|--------|-------------------|
| Cliente tem atalhos para eventos | Facilidade de uso específica de Telegram | 🟡 MÉDIO (mas pode remover) |
| Áudio tem contexto simplificado | Transcrição pode ser incompleta | 🟡 MÉDIO (mas deve validar plano) |
| Dono tem fluxo de confirmar pedido de cancelamento | Proteção contra cancelamentos acidentais | 🟢 BAIXO (diferença intencional) |

---

## 📋 PONTOS QUE DEVEM SER UNIFICADOS

| Ponto | Status | Ação |
|-------|--------|------|
| Cliente/Áudio devem usar classificador | ⚠️ PARCIAL | ✅ IMPLEMENTADO em gpt_service.py:167 |
| Profissionais devem usar dono_id | ❌ QUEBRADO em acao_handler | 🔧 PRECISA FIX |
| Dono deve tentar determinístico sempre | ⚠️ LIMITADO | 🔧 PRECISA REMOVER `if estado_fluxo == "idle"` |
| Áudio não deve forçar plano | ❌ SEGURANÇA | 🔧 PRECISA FIX |

---

## 🎯 PATCHES MÍNIMOS RECOMENDADOS

### **P0 — CRÍTICO (FAZER AGORA)**

#### 1. Corrigir `acao_handler.py:147` — Profissionais com dono_id

```python
# acao_handler.py:147
# ANTES:
profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}

# DEPOIS:
dono_id = await obter_id_dono(user_id)
profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
```

**Impacto:** Evita buscar profissionais do cliente em vez do dono

---

#### 2. Corrigir `bot.py:153` — Profissionais com dono_id (se usado)

```python
# bot.py:153
# Verificar se está correto ou se também precisa de obter_id_dono()
```

---

### **P1 — IMPORTANTE (FAZER PRÓXIMA SPRINT)**

#### 1. Remover `if estado_fluxo == "idle"` em `principal_router.py:3203`

```python
# principal_router.py:3203-3208
# ANTES:
if estado_fluxo == "idle":
    resposta_informativa = await responder_consulta_informativa(...)

# DEPOIS:
resposta_informativa = await responder_consulta_informativa(...)
```

**Impacto:** Dono pode consultar disponibilidade durante fluxo ativo

---

#### 2. Validar plano em `voice_command_handler.py:39-40`

```python
# voice_command_handler.py:39-40
# ANTES:
"planosAtivos": list(set((dados_usuario.get("planosAtivos") or []) + ["secretaria"])),

# DEPOIS:
"planosAtivos": dados_usuario.get("planosAtivos") or [],
# OU validar se "secretaria" já está incluído antes de forçar
```

**Impacto:** Não força plano não pago

---

#### 3. Mover ou remover atalhos de cliente

**Opção A:** Mover atalhos para roteador
**Opção B:** Remover atalhos (responder_consulta_informativa já cobre)

---

### **P2 — MELHORIAS (FAZER DEPOIS)**

1. Consolidar contexto montado (cliente vs dono)
2. Documentar por que áudio é diferente
3. Remover logs temporários `[TESTE_SURI]`

---

## 🔗 RELACIONADOS IMPLEMENTADOS

- ✅ **gpt_service.py:167** — Bloqueio de disponibilidade (JÁ FEITO)
- ✅ **informacao_service.py:27-69** — Formatador padrão (JÁ FEITO)
- ✅ **informacao_service.py:13-25** — Nomes humanizados (JÁ FEITO)
- ✅ **classificador_conversa.py:329-330** — Detecta consulta_disponibilidade_servico (JÁ FEITO)

---

## 📊 RESUMO EXECUTIVO

| Categoria | Status | Ação |
|-----------|--------|------|
| **Cliente pula roteador** | ⚠️ PARCIAL | ✅ MITIGADO (bloqueio em gpt_service) |
| **Profissionais com user_id** | ❌ QUEBRADO | 🔧 FIX CRÍTICO (P0) |
| **Áudio força plano** | ❌ SEGURANÇA | 🔧 FIX IMPORTANTE (P1) |
| **Dono limitado a idle** | ⚠️ LIMITAÇÃO | 🔧 MELHORIA (P1) |
| **Atalhos inconsistentes** | ⚠️ DIVERGÊNCIA | 🔧 DECIDIR (P2) |

---

## ✅ PRÓXIMOS PASSOS PROPOSTOS

1. **Hoje:** Corrigir P0 (acao_handler profissionais com dono_id)
2. **Esta semana:** Corrigir P1 (plano, idle, atalhos)
3. **Próxima sprint:** P2 (consolidações)
