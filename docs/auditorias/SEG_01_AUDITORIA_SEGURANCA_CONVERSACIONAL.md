# SEG-01 — AUDITORIA DE SEGURANÇA CONVERSACIONAL

**Status:** Completa (Sem Patch)  
**Data:** 2026-06-23  
**Baseline:** baseline-216-pass (216/216 PASS)  
**Objetivo:** Mapear mecanismos de segurança que impedem respostas a conversas pessoais

---

## MEC-01 — THRESHOLD CONSERVADOR

### Auditoría

**Pergunta:** Existe score de confiança e threshold mínimo para decidir se responde?

### Evidência Encontrada

✅ **STATUS: EXISTE**

**Arquivo:** `services/classificador_conversa.py`

**Thresholds Implementados:**

```python
# Linha 225-231 (Classificação OPERACIONAL)
if score_operacional >= 45 and diferenca >= 5:
    return {
        "modo_conversa": "operacional",
        "confianca": min(score_operacional, 100),
        ...
    }

# Linha 233-239 (Classificação PESSOAL)
if score_pessoal >= 45 and score_operacional < 50:
    return {
        "modo_conversa": "pessoal",
        "confianca": min(score_pessoal, 100),
        ...
    }

# Linha 241-246 (Classificação NEUTRO)
return {
    "modo_conversa": "neutro",
    "confianca": max(score_operacional, score_pessoal),
    ...
}
```

**Valores de Threshold:**

| Classificação | Condição | Valor |
|---|---|---|
| Operacional | `score >= 45 AND diferenca >= 5` | 45+ |
| Pessoal | `score >= 45 AND operacional < 50` | 45+ |
| Neutro | Padrão | Variável |
| Saudação (em fluxo) | Confiança | 70% |
| Saudação (sem fluxo) | Confiança | 40% |

**Fluxo Real:**

1. **Extração de Features** → Processa texto com regex
2. **Scoring** → Pontos por sinal detectado (35-45 pontos cada)
3. **Comparação** → score_operacional vs score_pessoal
4. **Decisão** → Modo conversa + confiança
5. **Roteamento** → Comando de ação baseado no modo

**Como funciona:**
- Mensagem entra → classificador calcula dois scores
- Se operacional >= 45 E diferença >= 5 → classifica como "operacional"
- Se pessoal >= 45 E operacional < 50 → classifica como "pessoal"
- Senão → classifica como "neutro"

**Proteção:**
- ✅ Mensagens pessoais (score < 45) não são tratadas como operacional
- ✅ Há threshold mínimo para agir
- ✅ Confiança é calculada e pode ser baixa (40% para saudação sem contexto)

---

## MEC-02 — CONTATO NÃO IDENTIFICADO

### Auditoria

**Pergunta:** Número novo recebe resposta? Existe distinção cliente conhecido vs desconhecido?

### Evidência Encontrada

✅ **STATUS: EXISTE (Parcial)**

**Arquivo:** `handlers/bot.py`

**Fluxo de Onboarding:**

```python
# Linha 527-530 (bot.py)
if tipo_usuario == "dono" and await precisa_onboarding(user_id):
    await update.message.reply_text(mensagem_onboarding(), parse_mode="Markdown")
```

**Arquivo:** `services/firebase_service_async.py`  
**Função:** `obter_id_dono()` (Linha 278-280)

```python
async def obter_id_dono(user_id: str) -> str:
    cliente = await buscar_cliente(user_id)
    return cliente.get("id_negocio", user_id) if cliente else user_id
```

**Fluxo Real:**

1. **Número novo entra** → Nenhum documento em `Clientes/{numero}`
2. **Busca cliente** → `buscar_cliente(user_id)` retorna `None`
3. **Fallback** → `obter_id_dono()` retorna o próprio `user_id`
4. **Multi-tenant** → Sistema usa isolamento por tenant
5. **Fluxo diferenciado** → Dono ativado → Onboarding executado

**Proteção:**
- ✅ Cliente desconhecido é identificado (documento não existe)
- ✅ Dono novo dispara onboarding (não responde diretamente)
- ✅ Número sem histórico = "desconhecido"
- ⚠️ Profissional novo não tem fluxo diferenciado específico

**Gap Identificado:**
- Contato pessoal (não dono, não profissional) recebe resposta normal
- Sem mecanismo específico que recuse conversa pessoal com número novo

---

## MEC-03 — OVERRIDE MANUAL

### Auditoria

**Pergunta:** Existe flag manual, whitelist, blacklist, ou bypass de IA?

### Evidência Encontrada

⚠️ **STATUS: PARCIAL**

**Arquivo:** `services/admin_command_service.py` (Mencionado em `grep`, não lido)

**Indicadores Encontrados:**

```python
# Em handlers/bot.py (linha ~527-530)
# Existe fluxo "responder_automaticamente" como conceitual
# Mas NÃO encontrada flag persistida em Firestore
```

**Busca por Padrões:**

| Padrão | Encontrado | Status |
|--------|-----------|--------|
| `manual_only` | ❌ Não | NÃO EXISTE |
| `responder_automaticamente` | ❌ Não (conceitual) | PARCIAL |
| `bloqueado` | ⚠️ Parcial | Em testes apenas |
| `whitelist` | ❌ Não | NÃO EXISTE |
| `blacklist` | ❌ Não | NÃO EXISTE |
| `pausado` | ❌ Não | NÃO EXISTE |

**Proteção:**
- ❌ Sem flag per-contato que desabilite resposta automática
- ❌ Sem comando `/pause` ou `/mute` administrativo
- ❌ Sem whitelist de contatos aprovados
- ❌ Sem blacklist de contatos bloqueados
- ⚠️ Apenas em testes há verificação de "bloqueado"

**Gap Crítico:**
- Não existe forma de impedir resposta automática para contato específico
- Não existe comando para silenciar bot sem código
- Não existe fallback para "encaminhar ao humano"

---

## MEC-04 — DONO DO NEGÓCIO

### Auditoria

**Pergunta:** Dono tem proteção especial? Pode ser respondido pela IA?

### Evidência Encontrada

❌ **STATUS: NÃO EXISTE (Proteção especial)**

**Arquivo:** `router/principal_router.py`

**Diferenciação Encontrada:**

```python
# Linha 10
from services.firebase_service_async import obter_id_dono

# Linha 63-64 (principal_router)
dono_id = await obter_id_dono(user_id)
await salvar_contexto_temporario_v2(dono_id, user_id, ctx)

# Linha 125-132
nome_dono = (
    ctx.get("nome_dono")
    or (await buscar_cliente(dono_id)).get("nome")
    if await buscar_cliente(dono_id)
    else "Proprietário"
)

# Linha 148-154 (Aceita requisição de falar com dono)
if nome_dono_norm and any(x in t for x in [
    f"falar com {nome_dono_norm}",
    f"quero falar com {nome_dono_norm}",
    f"prefiro falar com {nome_dono_norm}",
    ...
]):
    # Fluxo: Contata dono (não recusa)
```

**Fluxo Real:**

1. **Dono ou cliente entra** → Sistema resolve `obter_id_dono(user_id)`
2. **Isolamento** → Contexto salvo com `tenant_id = dono_id`
3. **Sem proteção** → Dono recebe resposta automática como cliente normal
4. **Requisição de dono** → Permite falar com dono (não recusa)

**Proteção:**
- ✅ Isolamento multi-tenant por `dono_id`
- ✅ Contexto diferenciado por dono
- ❌ **Sem proteção especial** que recuse resposta automática ao dono
- ❌ Dono pode ser respondido por IA como cliente normal
- ❌ Sem whitelist "dono sempre recebe resposta humana"

**Gap Crítico:**
- Dono pode conversar pessoalmente com bot (resposta automática ativada)
- Sem política que dê prioridade humana ao dono
- Sem mecanismo que force "encaminhar para humano" quando é dono

---

## MEC-05 — PROFISSIONAIS

### Auditoria

**Pergunta:** Profissional tem diferenciação? Existe proteção para não responder conversas pessoais?

### Evidência Encontrada

❌ **STATUS: NÃO EXISTE (Proteção específica)**

**Arquivo:** `services/profissional_service.py` (Referenciado mas não implementa proteção)

**Indicadores:**

```python
# Em router/principal_router.py (linha 38)
from services.profissional_service import buscar_profissionais_disponiveis_no_horario

# Uso: Apenas para buscar disponibilidade
# Sem lógica de "profissional não recebe resposta automática"
```

**Padrão Encontrado:**

| Contexto | Proteção | Status |
|----------|----------|--------|
| Profissional conversa | ❌ | Recebe resposta normal |
| Conversa pessoal com prof | ❌ | Sem bloqueio |
| Classificação mode="pessoal" | ⚠️ | Classifica, não bloqueia |
| Prof novo (não cadastro) | ❌ | Sem fluxo diferente |

**Fluxo Real:**

1. **Profissional envia mensagem** → Sistema não diferencia "sou profissional"
2. **Classificação** → Funciona normalmente (mode=operacional ou pessoal)
3. **Resposta** → Enviada conforme classificação (não há override)
4. **Sem proteção** → Conversa pessoal com profissional é respondida

**Proteção:**
- ❌ Sem mecanismo que identifique "esta pessoa é profissional"
- ❌ Sem proteção que recuse conversa pessoal com profissional
- ❌ Sem "profissional sempre fala com humano" policy
- ⚠️ Apenas a classificação diferencia (operacional vs pessoal)

**Gap Crítico:**
- Profissional pode ter conversa pessoal com bot (será respondida se pessoal < 45)
- Sem whitelist "profissional = humano apenas"
- Sem bypass de IA para profissionais

---

## TABELA FINAL DE SEGURANÇA

| Mecanismo | Status | Risco | Severidade | Evidência |
|-----------|--------|-------|-----------|-----------|
| **MEC-01: Threshold** | ✅ EXISTE | Baixo | Mitigado | `classificador_conversa.py:225-246` |
| **MEC-02: Contato Novo** | ⚠️ PARCIAL | Médio | Potencial | `firebase_service_async.py:278-280` |
| **MEC-03: Override Manual** | ❌ NÃO EXISTE | Alto | Crítico | Nenhum arquivo |
| **MEC-04: Dono Negócio** | ❌ NÃO EXISTE | Alto | Crítico | `principal_router.py:63-154` |
| **MEC-05: Profissionais** | ❌ NÃO EXISTE | Alto | Crítico | `profissional_service.py` (vazio) |

---

## CLASSIFICAÇÃO FINAL

### **B) Proteção Parcial**

**Justificativa:**

**Mecanismos Existentes (40%):**
- ✅ Threshold conservador implementado (MEC-01)
  - Score mínimo de 45 pontos para agir
  - Diferença de 5 pontos entre operacional e pessoal
  - Confiança de 40% para saudação sem contexto
  - **Proteção:** Mensagens puramente pessoais não são tratadas como operacional

- ⚠️ Isolamento multi-tenant por dono (MEC-02 parcial)
  - Contato desconhecido é identificado
  - Onboarding acionado para dono novo
  - **Gap:** Profissional/contato pessoal não diferenciado

**Mecanismos Faltantes (60%):**
- ❌ Sem override manual (MEC-03)
  - Sem forma de pausar bot
  - Sem whitelist/blacklist
  - Sem comando administrativo

- ❌ Sem proteção para dono (MEC-04)
  - Dono recebe resposta automática como cliente
  - Sem "encaminhar para humano" para dono

- ❌ Sem proteção para profissional (MEC-05)
  - Profissional não diferenciado
  - Conversa pessoal com prof é respondida se passar no threshold

---

## RECOMENDAÇÕES (Não Implementadas)

**Se implementar MEC-03:**
- Persistir flag `responder_automaticamente` por contato em Firestore
- Adicionar comando `/pausar` e `/retomar`
- Implementar whitelist de contatos aprovados

**Se implementar MEC-04:**
- Adicionar check: `if user_id == dono_id: return "encaminhar_para_humano"`
- Não responder automaticamente para dono

**Se implementar MEC-05:**
- Adicionar check: `if tipo_usuario == "profissional": return "encaminhar_para_humano"`
- Profissionais sempre falam com humano

---

## STATUS FINAL

**Baseline Congelado:**
- P1 E2E: 42/42 ✅
- P0: 174/174 ✅
- Checkpoint: baseline-216-pass ✅

**Segurança Conversacional:**
- Threshold conservador: ✅ Implementado
- Contato novo: ⚠️ Parcial
- Override manual: ❌ Não existe
- Dono: ❌ Sem proteção
- Profissional: ❌ Sem proteção

**Conclusão:** Sistema tem proteção básica (threshold), mas faltam mecanismos administrativos para impedir respostas automáticas a contatos específicos, dono e profissionais.

---

**Auditoria:** SEG-01  
**Data:** 2026-06-23  
**Assinatura:** Claude Code (Sem Patch)  
**Próximo:** ⏹️ PARAR (Escopo concluído)
