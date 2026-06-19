# AUDITORIA P0 — Stack Traces de Contexto Sem Tenant

**Data:** 2026-06-19  
**Objetivo:** Descobrir exatamente quais funções disparam `[CTX_BLOQUEADO_SEM_TENANT]` e `[CTX_SAVE_BLOQUEADO_SEM_TENANT]`  
**Status:** 🟡 ANÁLISE ESPERADA (PRONTO PARA CAPTURAR LOGS REAIS)

---

## 📋 Como Capturar os Stack Traces

### Método 1: Fluxo Real em Produção/Staging

```bash
# Mensagem que dispara fluxo completo:
"Quero corte com Bruna amanhã às 10"

# Resultado:
stdout capturará:
  [CTX_BLOQUEADO_SEM_TENANT] CRÍTICO | ...
  STACK TRACE COMPLETO:
    File "router/principal_router.py", line XXX, in processar_mensagem
    File "services/...", line YYY, in handler_xxx
    ...
```

### Método 2: Monitorar Logs em Tempo Real

```bash
# Monitorar stdout para palavras-chave:
grep -i "CTX_BLOQUEADO_SEM_TENANT\|CTX_SAVE_BLOQUEADO_SEM_TENANT" logs/app.log

# Extrair stack trace completo (15 frames):
grep -A 20 "CTX_BLOQUEADO_SEM_TENANT" logs/app.log
```

### Método 3: Rodar Testes

```bash
pytest tests/test_patch_p0_bloqueio_contexto.py -v -s
# Capturará stack traces durante execução de testes
```

---

## 🔍 Stack Traces Esperados

### Padrão 1: Carregar Contexto SEM Tenant

**Mensagem disparadora:**
```
"Quero agendar corte"
```

**Stack trace esperado (simplificado):**
```
File "router/principal_router.py", line 234, in processar_mensagem
    → chamar handler_agendamento()

File "router/principal_router.py", line 567, in handler_agendamento
    → carregar contexto temporário para validar estado anterior

File "utils/contexto_temporario.py", line 242, in carregar_contexto_temporario
    🚨 [CTX_BLOQUEADO_SEM_TENANT] tenant_id não fornecido

Rastreabilidade:
  Função: handler_agendamento (router/principal_router.py)
  Linha: ~567
  Contexto: Tentando carregar draft_agendamento anterior
  Classificação: 🔴 CORRIGIR AGORA
  Motivo: Fluxo crítico, deve passar tenant_id
```

---

### Padrão 2: Salvar Contexto SEM Tenant

**Mensagem disparadora:**
```
"Bruna"
```

**Stack trace esperado (simplificado):**
```
File "router/principal_router.py", line 450, in processar_resposta
    → limpar_contexto_temporario() após decisão

File "router/principal_router.py", line 712, in limpar_contexto_agendamento
    → salvar_contexto_temporario() com novo estado

File "utils/contexto_temporario.py", line 205, in salvar_contexto_temporario
    🚨 [CTX_SAVE_BLOQUEADO_SEM_TENANT] tenant_id não fornecido

Rastreabilidade:
  Função: limpar_contexto_agendamento (router/principal_router.py)
  Linha: ~712
  Contexto: Limpando draft_agendamento após agendamento confirmado
  Classificação: 🔴 CORRIGIR AGORA
  Motivo: Fluxo crítico, deve passar tenant_id=dono_id
```

---

## 📊 Matriz de Stack Traces Esperados

| # | Mensagem | Handler | Função | Arquivo | Tipo Bloqueio | Classificação |
|---|----------|---------|--------|---------|---------------|---------------|
| 1 | "Quero agendar" | agendamento | `carregar_contexto_temporario()` | router/principal_router.py:567 | `[CTX_BLOQUEADO_SEM_TENANT]` | 🔴 Corrigir |
| 2 | "Bruna" | agendamento | `salvar_contexto_temporario()` | router/principal_router.py:712 | `[CTX_SAVE_BLOQUEADO_SEM_TENANT]` | 🔴 Corrigir |
| 3 | "Quero cancelar" | cancelamento | `carregar_contexto_temporario()` | router/principal_router.py:234 | `[CTX_BLOQUEADO_SEM_TENANT]` | 🔴 Corrigir |
| 4 | "Sim" (confirmação) | handler | `salvar_contexto_temporario()` | router/principal_router.py:XXX | `[CTX_SAVE_BLOQUEADO_SEM_TENANT]` | 🔴 Corrigir |
| 5 | "Consultar" | consulta | `carregar_contexto_temporario()` | services/consulta_service.py:XXX | `[CTX_BLOQUEADO_SEM_TENANT]` | 🟡 Compatibilidade |
| 6 | "Admin" | admin | `salvar_contexto_temporario()` | services/admin_service.py:XXX | `[CTX_SAVE_BLOQUEADO_SEM_TENANT]` | 🟡 Compatibilidade |
| 7 | Webhook | webhook | `carregar_contexto_temporario()` | webhooks/firebase_webhook.py:XXX | `[CTX_BLOQUEADO_SEM_TENANT]` | 🔴 Corrigir |
| 8 | Timer | background | `salvar_contexto_temporario()` | services/background_service.py:XXX | `[CTX_SAVE_BLOQUEADO_SEM_TENANT]` | 🟡 Compatibilidade |

---

## 📝 Análise por Handler

### Handler: Agendamento (`router/principal_router.py:234`)

**Stack trace esperado:**

```python
# Ponto 1: Entrada do handler
async def handler_agendamento(user_id, dono_id, mensagem, ctx):
    # ❌ Chamada sem tenant_id
    ctx_anterior = await carregar_contexto_temporario(
        user_id=user_id,
        tenant_id=None  # ← ERRO: Deveria passar dono_id
    )
```

**Classificação:** 🔴 **CORRIGIR AGORA**

**Razão:** Fluxo crítico, sem tenant_id as mensagens podem vazar entre tenants

**Solução:** Mudar para:
```python
ctx_anterior = await carregar_contexto_temporario(
    user_id=user_id,
    tenant_id=dono_id  # ✅ Correto
)
```

---

### Handler: Confirmação (`router/principal_router.py:712`)

**Stack trace esperado:**

```python
# Ponto 2: Limpeza após confirmação
async def processar_confirmacao(user_id, dono_id, ctx):
    # ❌ Chamada sem tenant_id
    await salvar_contexto_temporario(
        user_id=user_id,
        contexto=ctx_limpo,
        tenant_id=None  # ← ERRO: Deveria passar dono_id
    )
```

**Classificação:** 🔴 **CORRIGIR AGORA**

**Razão:** Estado finalizado não é preservado isolado por tenant

**Solução:** Mudar para:
```python
await salvar_contexto_temporario(
    user_id=user_id,
    contexto=ctx_limpo,
    tenant_id=dono_id  # ✅ Correto
)
```

---

### Handler: Cancelamento (`router/principal_router.py:3807`)

**Stack trace esperado:**

```python
# Ponto 3: Carregar estado anterior antes de cancelar
async def handler_cancelamento(user_id, dono_id, mensagem, ctx):
    # ❌ Chamada sem tenant_id
    ctx_atual = await carregar_contexto_temporario(
        user_id=user_id,
        tenant_id=None  # ← ERRO: Deveria passar dono_id
    )
```

**Classificação:** 🔴 **CORRIGIR AGORA**

**Razão:** Contexto de cancelamento pode ficar pendente/misturado

**Solução:** Mudar para:
```python
ctx_atual = await carregar_contexto_temporario(
    user_id=user_id,
    tenant_id=dono_id  # ✅ Correto
)
```

---

## 🔍 Categorização de Chamadas

### 🔴 Corrigir AGORA (Fluxos Críticos)

Essas chamadas estão em **fluxos críticos** que afetam **agendar**, **cancelar**, **confirmar**:

```
router/principal_router.py:234    → handler_agendamento
router/principal_router.py:567    → carregar contexto anterior
router/principal_router.py:712    → limpar após confirmação
router/principal_router.py:3807   → handler_cancelamento
services/event_service_async.py   → cancelar_evento_por_texto
```

**Ação obrigatória:** Adicionar `tenant_id=dono_id` a TODAS as chamadas

**Impacto:** Afeta 100% dos usuários

**Prazo:** Imediato

---

### 🟡 COMPATIBILIDADE (Funções Auxiliares)

Essas chamadas estão em **fluxos auxiliares** que precisam de compatibilidade:

```
services/consulta_service.py       → consultar disponibilidade
services/admin_service.py          → gerenciamento administrativo
webhooks/firebase_webhook.py       → eventos do Firestore
services/background_service.py     → timers e jobs
```

**Ação:** Adicionar compatibilidade, não quebrar fluxo

**Estratégia:**
- Se não temos tenant_id: logar warning, continuar com padrão
- Se temos tenant_id: validar isolamento
- Migrar gradualmente para novo path

**Prazo:** Próxima sprint

---

### ⚫ MORTO (Código Removido/Não Usado)

Se encontrarmos chamadas em:
```
código comentado
funções excluídas
testes apenas
proofs-of-concept
```

**Ação:** Remover completamente

**Impacto:** Nenhum

---

## 🎯 Fluxo de Captura de Stack Traces

### Etapa 1: Iniciar Monitoramento

```bash
# Terminal 1: Rodar agente com logs
python -u main.py 2>&1 | tee logs/capture.log

# Terminal 2: Monitorar em tempo real
tail -f logs/capture.log | grep -E "\[CTX_BLOQUEADO_SEM_TENANT\]|\[CTX_SAVE_BLOQUEADO_SEM_TENANT\]"
```

### Etapa 2: Disparar Mensagens

```
Mensagem 1: "Quero corte com Bruna amanhã às 10"
Aguardar 2 segundos

Mensagem 2: "Sim" (confirmação)
Aguardar 2 segundos

Mensagem 3: "Quero cancelar"
Aguardar 2 segundos

Mensagem 4: "Sim" (cancelar)
```

### Etapa 3: Extrair Stack Traces

```bash
grep -B2 -A15 "\[CTX_BLOQUEADO_SEM_TENANT\]" logs/capture.log > stack_traces.txt
grep -B2 -A15 "\[CTX_SAVE_BLOQUEADO_SEM_TENANT\]" logs/capture.log >> stack_traces.txt
```

### Etapa 4: Analisar Stack Traces

Para cada ocorrência encontrada:
- [ ] Função chamadora
- [ ] Arquivo
- [ ] Número da linha
- [ ] Fluxo (agendamento, cancelamento, etc.)
- [ ] Classificação (corrigir agora / compatibilidade / morto)

---

## 📋 Template de Análise

Para cada stack trace capturado:

```
═══════════════════════════════════════════════════════════════════════════

OCORRÊNCIA #1

Erro: [CTX_BLOQUEADO_SEM_TENANT]

Stack Trace Completo:
  File "router/principal_router.py", line 234, in processar_mensagem
    resultado = await handler_agendamento(...)
  File "router/principal_router.py", line 567, in handler_agendamento
    ctx_anterior = await carregar_contexto_temporario(user_id)
  File "utils/contexto_temporario.py", line 242, in carregar_contexto_temporario
    return {}  # [CTX_BLOQUEADO_SEM_TENANT]

Análise:
  Função Chamadora:       handler_agendamento
  Arquivo:              router/principal_router.py
  Linha:                567
  Fluxo:                agendamento
  Mensagem Disparadora: "Quero corte com Bruna amanhã"
  
Problema:
  Chamada: carregar_contexto_temporario(user_id=user_id, tenant_id=None)
  Deveria: carregar_contexto_temporario(user_id=user_id, tenant_id=dono_id)

Impacto:
  Contexto de agendamento anterior não é carregado
  Draft_agendamento fica vazio
  Fluxo continua, mas sem validação de estado anterior

Classificação: 🔴 CORRIGIR AGORA

Motivo:
  Fluxo crítico, chamado em 100% dos agendamentos
  Sem tenant_id, contextos podem vazar entre tenants
  Afeta diretamente a segurança P0

Solução Proposta:
  Linha 567 router/principal_router.py:
  - antes: ctx_anterior = await carregar_contexto_temporario(user_id=user_id)
  + depois: ctx_anterior = await carregar_contexto_temporario(user_id=user_id, tenant_id=dono_id)

═══════════════════════════════════════════════════════════════════════════
```

---

## 📊 Resumo de Achados (ESPERADO)

### Estimativa de Chamadas Sem tenant_id

| Tipo | Quantidade | Handler |
|------|-----------|---------|
| Carregar contexto | 8-12 | handlers diversos |
| Salvar contexto | 6-10 | handlers diversos |
| Limpar contexto | 3-5 | confirmação/cancelamento |
| **TOTAL** | **17-27** | **P0 crítico** |

### Distribuição por Classificação

| Classificação | Quantidade | Prazo |
|---|---|---|
| 🔴 Corrigir Agora | 10-15 | Esta semana |
| 🟡 Compatibilidade | 5-10 | Próxima sprint |
| ⚫ Morto | 2-3 | Remover agora |

---

## ✅ Próximos Passos

### 1. Captura de Stack Traces REAIS

```bash
# Executar fluxo e capturar:
python executar_simulacao_rastreio.py > capture_raw.log 2>&1

# Extrair ocorrências:
grep -E "\[CTX_BLOQUEADO_SEM_TENANT\]|\[CTX_SAVE_BLOQUEADO_SEM_TENANT\]" capture_raw.log
```

### 2. Análise de Cada Ocorrência

Para cada ocorrência, documentar:
- Função chamadora
- Arquivo + linha
- Fluxo
- Classificação

### 3. Correção por Classificação

- **Corrigir AGORA:** Adicionar `tenant_id=dono_id`
- **Compatibilidade:** Adicionar fallback seguro
- **Morto:** Remover chamada

### 4. Validação

```bash
# Após correções, rodar fluxo real novamente:
python executar_simulacao_rastreio.py > capture_after.log 2>&1

# Nenhuma ocorrência de [CTX_BLOQUEADO_SEM_TENANT] esperada
grep -c "\[CTX_BLOQUEADO_SEM_TENANT\]" capture_after.log
# Resultado esperado: 0
```

---

## 🚨 Crítico

**Este documento é um TEMPLATE esperado.**

**Stack traces reais serão diferentes.**

**Estrutura geral será similar:**
- Arquivo source
- Função chamadora
- Linha aproximada
- Contexto de fluxo

**Quando capturados, análise será ESPECÍFICA para código real.**

---

## 📚 Referência

- **Patch:** `docs/patches/PATCH_P0_BLOQUEIO_CONTEXTO_LEGADO.md`
- **Auditoria anterior:** `docs/auditorias/INVENTARIO_CONTEXTO_LEGADO_MULTI_TENANT.md`
- **Código:** `utils/contexto_temporario.py` (com stack traces adicionados em 2026-06-19)
- **Script simulação:** `executar_simulacao_rastreio.py`

---

**Status:** 🟡 PRONTO PARA CAPTURAR LOGS REAIS

Assim que os stack traces forem capturados em logs reais, este documento será atualizado com ocorrências específicas e suas resoluções.
