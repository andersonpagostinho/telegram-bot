# INVENTÁRIO COMPLETO — MÓDULO DE CANCELAMENTO EXISTENTE

**Data:** 2026-06-19  
**Status:** AUDITORIA PURA (sem correções)  
**Objetivo:** Mapear tudo que existe antes de criar `resolver_fluxo_cancelamento()`

---

## 1️⃣ ARQUIVOS ENCONTRADOS

### Arquivos Principais (Implementação Ativa)

| Arquivo | Responsabilidade | Linhas-Chave |
|---------|-----------------|--------------|
| `handlers/bot.py` | Confirmação final de cancelamento | 217-300 (seção "P0.1A: CONFIRMAÇÃO DE CANCELAMENTO") |
| `services/event_service_async.py` | Funções core: cancelar, buscar, validar | 257-377 |
| `services/gpt_executor.py` | Processamento de ação GPT "cancelar_evento" | 627-640 |
| `router/principal_router.py` | Roteamento, estado fluxo, intenção | 3362, 3800-3815, 3935-3936 |
| `utils/contexto_temporario.py` | Persistência de cancelamento_pendente | 145, 183, 211 |

### Arquivos de Backup/Referência (Implementação Anterior)

| Arquivo | Tipo | Conteúdo |
|---------|------|----------|
| `backup/INTEGRACAO_MT07.../auditorias/AUDITORIA_P0_CANCELAMENTO_ATUAL.md` | Documentação | Análise completa do módulo existente |
| `backup/INTEGRACAO_MT07.../event_service_async.py` | Código anterior | Implementação com cancelado_por |
| `backup/P0_1A_2026-06-15.../test_p0_1a_cancelamento.py` | Testes | Casos de teste incluindo regressão |

---

## 2️⃣ FUNÇÕES EXISTENTES RELACIONADAS A CANCELAMENTO

### Core Functions

**`cancelar_evento(user_id, event_id, cancelado_por_tipo="cliente", motivo=None)`**
- **Localização:** `services/event_service_async.py:257-338`
- **Responsabilidade:** Marca evento como cancelado (soft delete) com auditoria
- **Validação:** ✅ Ownership (cliente só cancela seu, dono cancela qualquer)
- **Saída:** ✅ Campos de auditoria: `status="cancelado"`, `cancelado_em`, `cancelado_por`, `cancelado_por_tipo`, `cancelamento_confirmado_em`
- **Retorno:** Bool
- **Status:** REAPROVEITAR — já implementada, apenas usar

**`cancelar_evento_por_texto(user_id, termo: str)`**
- **Localização:** `services/event_service_async.py:341-376`
- **Responsabilidade:** Busca eventos por termo e retorna candidatos para confirmação
- **Output:** `(False, msg, candidatos)` com tuplas `(evento_id, evento_dict)`
- **Comportamento:** Sempre pede confirmação, nunca cancela direto
- **Status:** REAPROVEITAR — uso direto

**`evento_deve_entrar_na_agenda(evento_id, evento)`**
- **Localização:** `services/event_service_async.py:27-57`
- **Responsabilidade:** Filtro para eventos válidos em agenda
- **Importante:** ✅ Já ignora status `"cancelado"`, `"cancelada"`, `"removido"`, `"removida"`, `"excluido"`, `"excluído"`
- **Status:** REAPROVEITAR — filtro já correto

**`evento_deve_ser_ignorado(evento, event_id)`**
- **Localização:** `services/event_service_async.py` (linha ~230 em uso)
- **Verificar:** Função aparenta estar em uso mas não está definida na versão atual
- **Status:** NÃO USAR / VERIFICAR (pode ser função legada)

---

### Busca e Filtro

**`buscar_eventos_por_intervalo(user_id, dias=0, semana=False, dia_especifico=None)`**
- **Localização:** `services/event_service_async.py:189-254`
- **Responsabilidade:** Busca eventos em período, filtra cancelados automaticamente
- **Status:** REAPROVEITAR — já suporta filtro

**`buscar_eventos_por_termo_avancado(user_id, termo)`**
- **Localização:** Importado mas não visto em event_service_async.py (verificar services/)
- **Responsabilidade:** Busca eventos por termo (palavra-chave)
- **Status:** CONFIRMAR LOCALIZAÇÃO

**`verificar_conflito(user_id, data, hora_inicio, duracao_min, profissional, cliente_id, event_id=None)`**
- **Localização:** `services/event_service_async.py:379-400+`
- **Responsabilidade:** Verifica conflito de horário
- **Importante:** ✅ Ignora cancelados (linha 42: check status)
- **Status:** REAPROVEITAR — filtro correto

---

## 3️⃣ HANDLERS EXISTENTES

### Handler Principal de Confirmação

**`tratar_mensagens_gerais()` — Seção "P0.1A: CONFIRMAÇÃO DE CANCELAMENTO"**
- **Localização:** `handlers/bot.py:217-300`
- **Fluxo:**
  1. Detecta `estado_fluxo == "aguardando_confirmacao_cancelamento"` (linha 221)
  2. Processa número (escolha entre múltiplos) (linha 224-259)
  3. Processa confirmação (sim/não) (linha 262-300)
  4. Chama `cancelar_evento()` se sim (linha 270)
  5. Limpa contexto em ambos os lugares (linha 289-295)
- **Campos usados:**
  - `ctx["cancelamento_pendente"]` — dict com evento_id, cliente_id, resumo_eventos
  - `ctx["estado_fluxo"]`
  - `context.user_data["cancelamento_pendente"]` — duplicação (deprecated?)
- **Status:** REAPROVEITAR — fluxo correto, mas ver duplicação

### Event Handler (Legacy)

**`cancelar_evento_cmd(update, context)`**
- **Localização:** `handlers/event_handler.py:419+` (mencionado em imports)
- **Responsabilidade:** Comando `/cancelar`
- **Problema:** Não testa ownership (ver AUDITORIA P0 em backup)
- **Status:** CORRIGIR — validação incompleta

---

## 4️⃣ ESTADOS DE FLUXO EXISTENTES

| Estado | Definição | Transição | Onde definido |
|--------|-----------|-----------|---------------|
| `"aguardando_confirmacao_cancelamento"` | Esperando confirmação do usuário | idle → aguardando → idle | `router/principal_router.py:3807` |
| `"idle"` | Sem ação em progresso | — | Base (todo contexto inicia aqui) |
| `"agendando"` | Agendamento em progresso | — | Não afeta cancelamento |

**FLAGS relacionadas:**
- `ctx["cancelamento_pendente"]` — dict, precedência alta
- Existe também `context.user_data["cancelamento_pendente"]` (duplicação)

---

## 5️⃣ CAMPOS DE CONTEXTO USADOS

### Em `context.user_data["cancelamento_pendente"]`

```python
{
    "cliente_id": str,              # ✅ user_id que solicitou cancelamento
    "evento_id": str | None,        # Caso único: evento_id selecionado
    "resumo_evento": {
        "evento_id": str,
        "descricao": str,
        "data": str,
        "hora_inicio": str,
        "profissional": str,
    },
    # OU múltiplos:
    "resumo_eventos": [             # Caso múltiplo: lista de eventos
        {
            "evento_id": str,
            "descricao": str,
            "data": str,
            "hora_inicio": str,
            "profissional": str,
        }
    ]
}
```

### Em `MemoriaTemporaria/contexto`

```python
ctx["cancelamento_pendente"]        # Mesmo que acima (sincronizado)
ctx["estado_fluxo"]                 # Deve ser "aguardando_confirmacao_cancelamento"
```

**Problema detectado:** Duplicação entre `context.user_data` e `MemoriaTemporaria`

---

## 6️⃣ CAMPOS DE EVENTO USADOS

### Evento Dict (Firestore)

```json
{
  "status": "cancelado",                                    // ✅ Marcado por cancelar_evento()
  "cancelado_em": "2026-06-15T14:30:00-03:00",             // ✅ Timestamp ISO
  "cancelado_por": "user_123",                             // ✅ user_id que cancelou
  "cancelado_por_tipo": "cliente|dono|profissional",      // ✅ Tipo do cancelador
  "cancelamento_confirmado_em": "2026-06-15T14:30:05-03:00", // ✅ Timestamp confirmação
  "motivo_cancelamento": "outro compromisso"               // ⚠️ Opcional
}
```

**Campos já suportados:** ✅ Sim, todos implementados em `services/event_service_async.py:315-324`

---

## 7️⃣ BUSCA DE EVENTO CANDIDATO

**Status:** ✅ JÁ IMPLEMENTADO

### Fluxo

1. **Busca por texto:** `cancelar_evento_por_texto(user_id, termo)`
   - Retorna lista de candidatos: `[(evento_id, evento_dict), ...]`
   - Converte para resumo serializável: `sanitizar_cancelamento_pendente()`

2. **Seleção múltipla:**
   - Se 1 evento: mostra pergunta "Tem certeza?" (linha 367)
   - Se múltiplos: mostra lista numerada, usuário escolhe número

3. **Confirmação final:** Aguarda sim/não

**Localização:** 
- Busca: `services/event_service_async.py:341-376`
- Seleção: `handlers/bot.py:224-259`
- Confirmação: `handlers/bot.py:262-300`

---

## 8️⃣ CONFIRMAÇÃO FINAL

**Status:** ✅ JÁ IMPLEMENTADO

### Fluxo

```
Usuário escreve: "Tem certeza de cancelar X em Y às Z? (sim/não)"
    ↓
Bot aguarda resposta em estado "aguardando_confirmacao_cancelamento"
    ↓
Usuário responde: "sim" ou "não"
    ↓
Se "sim": executa cancelar_evento()
Se "não": aborta, limpa contexto, volta idle
```

**Validação:** ✅ Sim, existem listas de confirmações:
- `confirmacoes_sim = ["sim", "s", "ok", "confirma", "confirmar", "pode", "pode ser", "sim!"]` (linha 262)
- `confirmacoes_nao = ["não", "nao", "não!", "nao!", "desistir", "manter", ...]` (linha 263)

**Possível melhoria:** Lista pode ser incompleta, mas funciona.

---

## 9️⃣ ALTERAÇÃO DE STATUS = "cancelado"

**Status:** ✅ IMPLEMENTADO

### Onde acontece

**Função:** `cancelar_evento()` em `services/event_service_async.py:315-324`

```python
payload = {
    "status": "cancelado",
    "cancelado_em": now_iso,
    "cancelado_por": user_id,
    "cancelado_por_tipo": cancelado_por_tipo,
    "cancelamento_confirmado_em": now_iso,
}

await atualizar_dado_em_path(path, payload)
```

**Via Firestore:** 🔒 Usa `atualizar_dado_em_path()` (transação atomicamente segura)

---

## 🔟 HISTÓRICO / AUDITORIA

**Status:** ✅ PARCIALMENTE IMPLEMENTADO

### Campos de Auditoria em Evento

```python
"cancelado_por": user_id,              # ✅ Quem cancelou
"cancelado_por_tipo": str,             # ✅ Tipo (cliente/dono/profissional)
"cancelado_em": timestamp,             # ✅ Quando
"cancelamento_confirmado_em": timestamp, # ✅ Confirmação
"motivo_cancelamento": str             # ⚠️ Opcional, não preenchido
```

### O que FALTA

- ❌ Log estruturado de cancelamento (apenas log.info em linha 329)
- ❌ Coleta de motivo do cancelamento (campo existe, não é preenchido)
- ❌ Histórico cronológico em coleção separada

**Status:** REAPROVEITAR os campos, AUSENTE a estrutura de logging completa

---

## 1️⃣1️⃣ NOTIFICAÇÕES APÓS CANCELAMENTO

**Status:** ❌ NÃO IMPLEMENTADO

### O que Falta

- ❌ Notificação ao **dono** após cancelamento
  - Quando: imediatamente após marcar como cancelado
  - O quê: "Seu agendamento de [descricao] em [data] às [hora] foi cancelado por [cliente_nome]"

- ❌ Notificação ao **profissional** após cancelamento
  - Quando: imediatamente após marcar como cancelado
  - O quê: "O agendamento de [cliente_nome] para [descricao] em [data] às [hora] foi cancelado"

- ❌ Notificação para **reagendar** se cliente cancelou
  - Quando: 5-10 minutos após confirmação
  - O quê: "Tudo bem cancelar. Se precisar reagendar, é só me chamar."

### Funções Disponíveis

- `criar_notificacao_agendada()` já existe (usada em salvar_evento, linha 170)
- Pode ser reutilizada com adjusts

**Localização esperada:** `services/notificacao_service.py`

**Status:** AUSENTE — precisa implementação

---

## 1️⃣2️⃣ LIBERAÇÃO DE HORÁRIO POR STATUS

**Status:** ✅ PARCIALMENTE IMPLEMENTADO

### O que Existe

**Filtro em verificações de conflito:**
- `evento_deve_entrar_na_agenda()` (linha 42) — ignora cancelados
- `verificar_conflito()` — filtra status cancelado
- Filtro em `_carregar_ocupados()` — ignora cancelados

**Garantia:** ✅ Sim, horário é liberado **imediatamente** quando `status="cancelado"`

### O que FALTA

- ❌ **Motor de remanejamento ativo** após cancelamento
  - Quando: cancelamento = horário liberado
  - Ação esperada: remanejador procura por eventos em espera para encaixar
  - Implementação: chegar `processar_motor_encaixe()` ou similar após cancelar_evento()

**Status:** Bloqueio defensivo ✅ | Remanejamento ativo ❌

---

## 1️⃣3️⃣ PONTOS ONDE CANCELAMENTO CAI EM AJUSTE INCREMENTAL

**Status:** ⚠️ RISCO DETECTADO

### Problema

**Linha:** `router/principal_router.py:3362`

```python
if ctx.get("estado_fluxo") == "aguardando_confirmacao_cancelamento" and ctx.get("cancelamento_pendente"):
    # ... processa confirmação
```

Mas depois, em muitos outros pontos do router:

```python
# AJUSTE INCREMENTAL pode executar mesmo com cancelamento pendente!
await resolver_alteracao_draft_agendamento(...)
```

**Risco:** Se cancelamento pendente fica "esquecido" no contexto, um mensagem "sim" pode:
1. Confirmar cancelamento (correto)
2. OU confirmar ajuste de agendamento (errado)
3. OU fazer ambos (muito errado)

### Locais de Risco

**Grep Results:**
- `resolver_alteracao_draft_agendamento()` é chamada em ~40+ locais
- Cada um desses lugares pode executar enquanto cancelamento_pendente está ativo

**Exemplo:**
```python
# Usuário está em "aguardando_confirmacao_cancelamento"
User: "sim"

# Sem guarda, pode:
1. Confirmar cancelamento ✅
2. Confirmar ajuste (se draft existir) ⚠️
3. Ambos (se ambos contextos presentes) 🔥
```

---

## 1️⃣4️⃣ SALVAR CONTEXTO SEM TENANT_ID

**Status:** ⚠️ FALHA DEFENSIVA DETECTADA

### Locations

```
utils/contexto_temporario.py:145 — [CTX_LEGADO_SAVE_SEM_TENANT]
utils/contexto_temporario.py:183 — [CTX_LEGADO_SEM_TENANT_PARAM]
utils/contexto_temporario.py:211 — [CTX_LEGADO_CLEAR_SEM_TENANT]
```

### Problema

Ao salvar cancelamento_pendente, o chamador DEVE passar `tenant_id`:

```python
await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)
```

Mas se não passar, a função **avisa no log mas continua**:

```python
print(f"🚨 [CTX_LEGADO_SAVE_SEM_TENANT] ⚠️ RISCO | path={path} | tenant_id não fornecido")
```

### Ocorrências em Cancelamento

**handlers/bot.py:250** — ✅ CORRETO: `tenant_id=tenant_id`  
**handlers/bot.py:292** — ✅ CORRETO: `tenant_id=tenant_id`  
**router/principal_router.py:3812** — ✅ CORRETO: `tenant_id=dono_id`  

**Status:** BAIXO RISCO — pontos principais têm tenant_id

---

## 1️⃣5️⃣ PONTOS DUPLICADOS OU MORTOS

### Duplicação Detectada

1. **`context.user_data["cancelamento_pendente"]` vs `MemoriaTemporaria ctx["cancelamento_pendente"]`**
   - Localização: `handlers/bot.py:235`, `handlers/bot.py:250`
   - Problema: Manutenção em dois lugares
   - Solução: Usar apenas MemoriaTemporaria, remover user_data

2. **Persistência dupla:**
   - Linha 250: salva em MemoriaTemporaria
   - Linha 235: salva em context.user_data
   - Ambas carregadas (linha 248 vs 166)
   - Resultado: Sincronização manual necessária

### Código Morto Potencial

1. **`evento_deve_ser_ignorado()`** (mencionado linha 229 em buscar_eventos_por_intervalo)
   - Função não encontrada na versão atual
   - Possível dead code ou função renomeada
   - **Ação:** Confirmar se ainda usada

2. **`/cancelar` command** em event_handler.py
   - Não testado em ciclos recentes
   - Sem validação de ownership
   - **Ação:** Desabilitar ou corrigir

---

## 1️⃣6️⃣ RISCOS P0 IDENTIFICADOS

| Risco | Localização | Severidade | Descrição |
|-------|-------------|-----------|-----------|
| **Ajuste paralelo com cancelamento** | router/principal_router.py (multiplos) | 🔴 CRÍTICO | Resolver alteração pode executar mesmo com cancelamento_pendente ativo |
| **Sem guarda P0 anti-crash** | router/principal_router.py:3362-3400 | 🔴 CRÍTICO | Nenhum `if estado=="aguardando_confirmacao_cancelamento": bloqueio_ajuste` |
| **Remanejamento não existe** | services/event_service_async.py | 🟡 ALTO | Cancelamento libera horário mas não tenta remanejador |
| **Notificações ausentes** | services/ (inexistente) | 🟡 ALTO | Dono/Profissional não sabem que evento foi cancelado |
| **Motivo não coletado** | handlers/bot.py | 🟡 MÉDIO | Campo existe mas usuário não é perguntado |
| **Duplicação de contexto** | handlers/bot.py:235-250 | 🟢 BAIXO | Manutenção dupla, inconsistência possível |
| **Comando /cancelar quebrado** | handlers/event_handler.py | 🟢 BAIXO | Sem validação de ownership |

---

## 1️⃣7️⃣ O QUE REAPROVEITAR

### ✅ PRONTO PARA USAR (sem mudanças)

1. **`cancelar_evento(user_id, event_id, cancelado_por_tipo, motivo)`**
   - Implementação completa
   - Validação de ownership OK
   - Campos de auditoria completos
   - Transação Firestore segura
   - **Usar em:** `resolver_fluxo_cancelamento()`

2. **`cancelar_evento_por_texto(user_id, termo)`**
   - Busca com múltiplos candidatos
   - Retorna resumo serializável
   - Nunca cancela direto
   - **Usar em:** Busca inicial de candidato

3. **`sanitizar_cancelamento_pendente(candidatos, cliente_id)`**
   - Converte tuplas em dict JSON-safe
   - Já implementada em gpt_executor.py
   - **Usar em:** Salvar contexto

4. **Filtros de cancelado em agenda**
   - `evento_deve_entrar_na_agenda()` ignora cancelados
   - `verificar_conflito()` ignora cancelados
   - **Usar em:** Consultas de disponibilidade

5. **Handler confirmação em bot.py**
   - Fluxo sim/não correto
   - Limpeza de contexto
   - **Usar em:** Após resolver_fluxo

### ⚠️ PRONTO COM AJUSTES (mínimas mudanças)

1. **`handler confirmação (bot.py:217-300)`**
   - Remover duplicação `context.user_data["cancelamento_pendente"]`
   - Usar apenas MemoriaTemporaria
   - Adicionar notificações antes de limpar

2. **Estado `"aguardando_confirmacao_cancelamento"`**
   - Já existe
   - Adicionar guarda em resolver_alteracao_draft_agendamento()

---

## 1️⃣8️⃣ O QUE REMOVER

### ❌ REMOVER

1. **`context.user_data["cancelamento_pendente"]`**
   - Duplicação com MemoriaTemporaria
   - Substituir por MemoriaTemporaria apenas
   - Linhas: `handlers/bot.py:235`, `handlers/bot.py:294`

2. **`/cancelar` command** (ou corrigir)
   - Sem validação de ownership
   - Sem teste
   - Opção A: Desabilitar (comentar CommandHandler)
   - Opção B: Corrigir com mesma validação de cancelar_evento()

3. **`evento_deve_ser_ignorado()`** (se morto)
   - Se função não existe, remover import
   - Se existe, localizar e validar

---

## 1️⃣9️⃣ O QUE FALTA PARA MOTOR DETERMINÍSTICO COMPLETO

### AUSENTE — Implementação Necessária

1. **`resolver_fluxo_cancelamento(user_id, tenant_id)`**
   - Função que não existe ainda
   - Responsabilidade: centralizar lógica de cancelamento
   - Deve englobar:
     - Buscar candidato (via cancelar_evento_por_texto)
     - Montar contexto pendente
     - Salvar estado
     - Retornar mensagem

2. **Notificação ao dono após cancelamento**
   - Quando: imediatamente após salvar status="cancelado"
   - O quê: Informar que evento foi cancelado
   - Onde: Adicionar em cancelar_evento() ANTES de retornar

3. **Notificação ao profissional após cancelamento**
   - Quando: imediatamente após salvar
   - O quê: Informar que evento foi cancelado
   - Onde: Adicionar em cancelar_evento() ANTES de retornar

4. **Coleta de motivo**
   - Quando: após confirmar cancelamento (sim/não)
   - O quê: Perguntar "Qual é o motivo?"
   - Onde: Novo estado "aguardando_motivo_cancelamento"
   - Opcional: Se não responder em 30s, usar default

5. **Motor de remanejamento ativo**
   - Quando: após marcar como cancelado
   - O quê: Tentar encaixar eventos em espera no horário liberado
   - Onde: Chamar após salvar cancelamento em Firestore
   - Status: PROTOTIPADO em outros contextos (agenda_lock_service.py tem logica)

6. **Guarda P0 anti-crash**
   - Quando: estado="aguardando_confirmacao_cancelamento"
   - O quê: Bloquear resolver_alteracao_draft_agendamento() e outros ajustes
   - Onde: `router/principal_router.py` (seção de ajustes incrementais)
   - Padrão: `if estado=="aguardando_confirmacao_cancelamento": return`

7. **Fluxo de dono cancelar evento**
   - Intenção: "cancelar agendamento de [cliente]"
   - Ação: Buscar agendamentos do cliente, pedir confirmação, cancelar
   - Diferença: dono vê agendamentos de OUTROS, cliente vê seus

8. **Fluxo de profissional cancelar evento**
   - Intenção: "não posso fazer o [descricao] de [cliente]"
   - Ação: Marcar cancelado pelo profissional, notificar cliente
   - Diferença: Cancelado_por_tipo="profissional"

---

## 📋 CLASSIFICAÇÃO FINAL POR STATUS

### REAPROVEITAR ✅ (usar direto, sem mudanças)

- `cancelar_evento()` — completa, pronta
- `cancelar_evento_por_texto()` — pronta
- `sanitizar_cancelamento_pendente()` — pronta
- Estado `"aguardando_confirmacao_cancelamento"` — pronto
- Campos de auditoria em evento — prontos
- Filtros de cancelado em agenda — prontos

### CORRIGIR ⚠️ (usar com ajustes mínimos)

- Handler confirmação (remover duplicação de contexto)
- Estado fluxo (adicionar guarda em resolver_alteracao)
- Comando `/cancelar` (adicionar validação ou desabilitar)

### NÃO USAR ❌ (remover ou deixar de lado)

- `context.user_data["cancelamento_pendente"]` (duplicação)
- `evento_deve_ser_ignorado()` (possível dead code)

### AUSENTE ⚫ (implementar novo)

- `resolver_fluxo_cancelamento()` — orquestrador
- Notificação ao dono — nova funcionalidade
- Notificação ao profissional — nova funcionalidade
- Coleta de motivo — novo fluxo
- Remanejamento ativo — integração
- Guarda P0 anti-crash — proteção
- Fluxo de dono cancelar — novo caso
- Fluxo de profissional cancelar — novo caso

---

## 🎯 PRÓXIMOS PASSOS (SEM IMPLEMENTAÇÃO AINDA)

### Fase 1: Guarda P0 Obrigatória (IMEDIATA)

Apenas **uma mudança defensiva** antes de implementar resolver_fluxo:

```python
# Em router/principal_router.py, seção de resolver_alteracao_draft_agendamento
if ctx.get("estado_fluxo") == "aguardando_confirmacao_cancelamento":
    print("[GUARD_P0_CANCELAMENTO] Bloqueando ajuste incremental")
    return {}  # Não processar nenhum ajuste
```

**Benefício:** Evita crash se cancelamento_pendente fica "esquecido"

### Fase 2: Implementação de resolver_fluxo_cancelamento()

**Será feita APÓS essa auditoria aprovada.**

Esperado usar:
- `cancelar_evento()` ✅
- `cancelar_evento_por_texto()` ✅
- Estado e contexto existentes ✅
- Adicionar notificações ⚫
- Adicionar remanejamento ⚫

---

## 📊 RESUMO EXECUTIVO

| Aspecto | Status | Cobertura |
|---------|--------|-----------|
| **Busca de candidato** | ✅ | 100% — cancelar_evento_por_texto() |
| **Múltiplos eventos** | ✅ | 100% — seleção por número |
| **Confirmação final** | ✅ | 100% — sim/não, persistência |
| **Marcar cancelado** | ✅ | 100% — soft delete, auditoria completa |
| **Validação ownership** | ✅ | 100% — cliente/dono bloqueio |
| **Campos auditoria** | ✅ | 100% — quem, quando, tipo |
| **Liberação horário** | ✅ | 50% — filtro sim, remanejamento não |
| **Notificações** | ❌ | 0% — inexistente |
| **Coleta motivo** | ❌ | 0% — campo existe, não pergunta |
| **Fluxo dono** | ❌ | 0% — não implementado |
| **Fluxo profissional** | ❌ | 0% — não implementado |
| **Guarda P0** | ❌ | 0% — risco detectado |

**Conclusão:** Sistema **50% completo** de forma **determinística**. Faltam notificações, guarda P0, e fluxos alternativos (dono/profissional).

---

**Data de geração:** 2026-06-19  
**Responsável:** Auditoria sistemática de cancelamento  
**Aprovação:** Aguardando review
