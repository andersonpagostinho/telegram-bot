# SEG-03 — ESPECIFICAÇÃO DE GOVERNANÇA CONVERSACIONAL

**Status:** Especificação Executável (Sem Implementação)  
**Data:** 2026-06-23  
**Baseline:** 216/216 PASS (P1 42/42 + P0 174/174)  
**Versão:** 1.0  
**Autoria:** Claude Code (Auditoria + Modelagem + Especificação)

---

## 1. OBJETIVO

Definir e formalizar o comportamento de governança conversacional do NeoEve para:
- Proteger usuários de respostas automáticas inadequadas
- Permitir controle administrativo por contato
- Diferenciar atores internos (profissionais) de clientes
- Gerenciar contatos desconhecidos com segurança
- Manter baseline P1/P0 verde (216/216 PASS)

---

## 2. ESCOPO

### Incluso

✅ MEC-03: Override manual por contato (`responder_automaticamente`)  
✅ MEC-04: Modo do dono alternável (`modo_dono`)  
✅ MEC-05: Profissional como ator interno (default silencioso)  
✅ MEC-02: Contato desconhecido híbrido (D4)  
✅ Ponto de decisão (linha 3360 router/principal_router.py)  
✅ Persistência em Firestore  
✅ Auditoria de decisões  

### Fora de Escopo

❌ Alteração de prompts do GPT  
❌ Alteração de fluxo de agenda  
❌ Alteração de classificador conversacional  
❌ Implementação de notificações para humano  
❌ Interface de comando `/pausar` (apenas especificação)  
❌ Integração com sistemas externos  

---

## 3. MODELO DE DADOS

### 3.1 Estrutura de Persistência

**Coleção:** `Clientes/{tenant_id}/Sessoes/{actor_id}`

```json
{
  "actor_id": "whatsapp:5511999005",
  "tipo_usuario": "cliente|profissional|dono",
  
  // MEC-03: Override manual
  "responder_automaticamente": true|false,
  "bloqueado_ate": "2026-06-24T15:30:00Z" | null,
  "razao_bloqueio": "pausado_pelo_dono|bloqueio_admin|outro",
  
  // MEC-04: Modo do dono
  "modo_dono": "normal|admin|silencioso",
  
  // MEC-02: Contato desconhecido
  "identificado": true|false,
  "primeira_mensagem": "2026-06-23T12:00:00Z",
  
  // Metadados de governança
  "_tenant_id_guard": "{tenant_id}",
  "_ultima_decisao_governanca": "2026-06-23T12:00:00Z",
  "_decisoes_log": [
    {
      "timestamp": "2026-06-23T12:00:00Z",
      "decisao": "bypass_override",
      "motivo": "responder_automaticamente=false"
    }
  ],
  "_schema_version": 2
}
```

### 3.2 Campos Críticos por Mecanismo

| Campo | Mecanismo | Tipo | Default | Usado Em |
|-------|-----------|------|---------|----------|
| `responder_automaticamente` | MEC-03 | bool | true | [GOVERNANCA-CHECK] |
| `bloqueado_ate` | MEC-03 | ISO8601\|null | null | [GOVERNANCA-CHECK] |
| `modo_dono` | MEC-04 | string | "normal" | [GOVERNANCA-CHECK] |
| `tipo_usuario` | MEC-05 | string | "cliente" | [GOVERNANCA-CHECK] |
| `identificado` | MEC-02 | bool | false | [GOVERNANCA-CHECK] |

---

## 4. ORDEM DE DECISÃO

### Ponto de Inserção Exato

**Arquivo:** `router/principal_router.py`

```python
# Linha 3360: ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id)

# ┌─────────────────────────────────────────────────────────────┐
# │ [NOVO] BLOCO DE GOVERNANÇA ← INSERIR AQUI                   │
# │                                                              │
# │ Governança(user_id, dono_id, ctx) retorna:                 │
# │   {                                                          │
# │     "bloqueado": true|false,                                │
# │     "motivo": "string",                                      │
# │     "resposta_bloqueio": "string (se bloqueado)"            │
# │   }                                                          │
# └─────────────────────────────────────────────────────────────┘

# Linha 3366: await processar_fluxo_identidade_onboarding(...)
```

### Pseudocódigo da Ordem de Decisão

```python
async def governanca_conversacional(user_id, dono_id, ctx):
    """Bloco de governança — ordem crítica de decisões"""
    
    # 1. OVERRIDE MANUAL (MEC-03)
    if ctx.get("responder_automaticamente") == False:
        if not _eh_bloqueio_expirado(ctx.get("bloqueado_ate")):
            return {
                "bloqueado": True,
                "motivo": "MEC-03-OVERRIDE",
                "resposta_bloqueio": "Estou pausado no momento."
            }
    
    # 2. MODO DONO (MEC-04)
    if user_id == dono_id:
        modo = ctx.get("modo_dono", "normal")
        
        if modo == "silencioso":
            return {
                "bloqueado": True,
                "motivo": "MEC-04-DONO-SILENCIOSO",
                "resposta_bloqueio": "Modo silencioso ativado."
            }
        
        elif modo == "admin":
            # Continua, mas será filtrado depois
            # (apenas comandos /pausar, /retomar, etc)
            pass
    
    # 3. PROFISSIONAL COMO ATOR INTERNO (MEC-05)
    if ctx.get("tipo_usuario") == "profissional":
        modo_prof = ctx.get("modo_profissional", "silencioso")
        
        if modo_prof == "silencioso":
            return {
                "bloqueado": True,
                "motivo": "MEC-05-PROFISSIONAL",
                "resposta_bloqueio": "Profissional — encaminhando para equipe."
            }
    
    # 4. CONTATO DESCONHECIDO HÍBRIDO (MEC-02)
    if ctx.get("identificado") == False:
        # Verificar mensagem — será feito após classificação
        # Por enquanto, permitir passar (será decidido em MEC-02-CLASSIF)
        return {
            "bloqueado": False,
            "motivo": "MEC-02-PASSOU-ADIANTE",
            "nota": "Contato novo — será validado após classificação"
        }
    
    # NENHUM BLOQUEIO
    return {
        "bloqueado": False,
        "motivo": "NENHUM",
        "fluxo": "NORMAL"
    }
```

---

## 5. FLUXO POR TIPO DE ATOR

### 5.1 Ator: DONO (user_id == dono_id)

```
Mensagem de dono
    ↓
[GOVERNANCA-CHECK]
    ├─ modo_dono = "silencioso"?
    │  └─ BLOQUEADO → "Modo silencioso ativado"
    │
    ├─ modo_dono = "admin"?
    │  └─ CONTINUA (filtro admin depois)
    │
    └─ modo_dono = "normal"?
       └─ CONTINUA (fluxo cliente)
    ↓
Fluxo normal (classificação, GPT, agenda, etc.)
```

**Estados Possíveis:**
- `modo_dono = "normal"` → Fluxo cliente completo
- `modo_dono = "admin"` → Apenas comandos (/pausar, /retomar, /status)
- `modo_dono = "silencioso"` → Sem resposta automática

---

### 5.2 Ator: PROFISSIONAL (tipo_usuario == "profissional")

```
Mensagem de profissional
    ↓
[GOVERNANCA-CHECK]
    ├─ tipo_usuario = "profissional"?
    └─ modo_profissional != "silencioso"?
       └─ BLOQUEADO → "Profissional — encaminhando para equipe"
    ↓
NÃO ENTRA FLUXO DE CLIENTE
NÃO CHAMA GPT
NÃO AGENDA
REGISTRA AUDITORIA
```

**Estados Possíveis:**
- `modo_profissional = "silencioso"` (default) → Bloqueado
- `modo_profissional = "operacional"` (override) → Fluxo cliente

---

### 5.3 Ator: CLIENTE (tipo_usuario == "cliente" + identificado)

```
Mensagem de cliente identificado
    ↓
[GOVERNANCA-CHECK]
    ├─ responder_automaticamente = false?
    │  └─ BLOQUEADO → "Estou pausado"
    │
    └─ responder_automaticamente = true?
       └─ CONTINUA
    ↓
Fluxo normal (classificação, GPT, agenda, etc.)
```

**Estados Possíveis:**
- `responder_automaticamente = true` → Fluxo normal
- `responder_automaticamente = false` → Bloqueado

---

### 5.4 Ator: CONTATO DESCONHECIDO (identificado == false)

```
Mensagem de contato novo
    ↓
[GOVERNANCA-CHECK]
    └─ identificado = false?
       └─ CONTINUA (decisão pós-classificação)
    ↓
[CLASSIFICAÇÃO]
    ├─ modo = "pessoal" (confiança < 45)?
    │  └─ BLOQUEADO → Silenciar
    │
    ├─ modo = "operacional" (confiança >= 70)?
    │  └─ CONTINUA → Permitir fluxo
    │
    └─ modo = "neutro" (45-70)?
       └─ BLOQUEADO → Encaminhar identificação
    ↓
Resposta ou bloqueio
```

**Estados Possíveis:**
- Saudação (`confianca=70%`) → Responda "Oi! Como posso ajudar?"
- Operacional alta (`confianca>=70%`) → Fluxo normal
- Pessoal puro (`confianca<45%`) → Silenciar
- Ambíguo (`45-70%`) → Pedir identificação

---

## 6. ESTADOS POSSÍVEIS DO SISTEMA

### Por Contato (ator_id)

| Estado | responder_aut | modo_dono | tipo_usuario | Resultado |
|--------|---------------|-----------|--------------|-----------|
| **S1** | true | normal | cliente | ✅ Fluxo normal |
| **S2** | false | — | cliente | ❌ Bloqueado (pausa) |
| **S3** | — | silencioso | — | ❌ Bloqueado (dono silencioso) |
| **S4** | — | admin | — | ✅ Apenas admin cmds |
| **S5** | — | — | profissional | ❌ Bloqueado (ator interno) |
| **S6** | true | normal | cliente | ✅ Fluxo normal (desconhecido → ident) |

---

## 7. COMANDOS ADMINISTRATIVOS PREVISTOS

### Comandos a Implementar (Futura Sprint)

| Comando | Requisito | Ação | Resultado |
|---------|-----------|------|-----------|
| `/pausar` | user_id == dono_id | `responder_automaticamente = false` | ✅ "Pausado até {data}" |
| `/retomar` | user_id == dono_id | `responder_automaticamente = true` | ✅ "Voltei ao normal" |
| `/status` | user_id == dono_id | Retorna estado governança | ✅ "Modo: {modo_dono}, Pausa: {sim/não}" |
| `/silencioso` | user_id == dono_id | `modo_dono = "silencioso"` | ✅ "Modo silencioso" |
| `/admin` | user_id == dono_id | `modo_dono = "admin"` | ✅ "Modo admin" |
| `/normal` | user_id == dono_id | `modo_dono = "normal"` | ✅ "Modo normal" |

### Auditoria de Comandos

Cada comando registra em `_decisoes_log`:
```json
{
  "timestamp": "2026-06-23T12:30:00Z",
  "comando": "/pausar",
  "por": "dono",
  "acao": "responder_automaticamente = false",
  "bloqueado_ate": "2026-06-24T12:30:00Z"
}
```

---

## 8. CRITÉRIOS DE ACEITE

### CA-1: Override Manual (MEC-03)

**Quando:** Contato com `responder_automaticamente=false`  
**Critério:** Não recebe resposta automática de nenhum tipo  
**Validação:**
```
Given: responder_automaticamente = false
When: Envia mensagem qualquer
Then: Recebe mensagem "Estou pausado" (ou silencia)
And: LOG registra decisão governança
And: GPT NÃO é chamado
And: Agenda NÃO é consultada
```

### CA-2: Dono Modo Silencioso (MEC-04)

**Quando:** Dono com `modo_dono=silencioso`  
**Critério:** Não recebe resposta automática  
**Validação:**
```
Given: user_id == dono_id AND modo_dono = "silencioso"
When: Dono envia mensagem qualquer
Then: Não recebe resposta automática
And: Pode receber comandos admin (/status)
And: LOG registra MOTIVO = "MEC-04-DONO-SILENCIOSO"
```

### CA-3: Dono Modo Admin (MEC-04)

**Quando:** Dono com `modo_dono=admin`  
**Critério:** Executa apenas comandos administrativos  
**Validação:**
```
Given: user_id == dono_id AND modo_dono = "admin"
When: Dono envia /pausar
Then: Executa comando

When: Dono envia "Oi, tudo bem?"
Then: NÃO responde (conteúdo pessoal recusado)
And: LOG registra MOTIVO = "MEC-04-ADMIN-ONLY"
```

### CA-4: Profissional Bloqueado (MEC-05)

**Quando:** Ator com `tipo_usuario=profissional`  
**Critério:** Não entra fluxo de cliente  
**Validação:**
```
Given: tipo_usuario = "profissional" AND modo_profissional = "silencioso"
When: Profissional envia mensagem qualquer
Then: Não recebe resposta de cliente
And: LOG registra MOTIVO = "MEC-05-PROFISSIONAL"
And: GPT NÃO é chamado
And: Agenda NÃO é consultada
```

### CA-5: Contato Desconhecido Pessoal (MEC-02)

**Quando:** Contato novo com `identificado=false` + mensagem pessoal  
**Critério:** Não recebe resposta automática para conteúdo pessoal  
**Validação:**
```
Given: identificado = false AND classificacao.modo = "pessoal"
When: Novo contato envia "Oi! Tudo bem? Como você está?"
Then: Silencia OU encaminha para identificação
And: LOG registra MOTIVO = "MEC-02-PESSOAL-NOVO"
And: GPT NÃO responde conteúdo pessoal
```

### CA-6: Contato Desconhecido Operacional (MEC-02)

**Quando:** Contato novo com `identificado=false` + mensagem operacional alta confiança  
**Critério:** Permite fluxo se confiança >= 70%  
**Validação:**
```
Given: identificado = false AND classificacao.confianca >= 70 AND modo = "operacional"
When: Novo contato envia "Quanto custa corte? Tem vaga amanhã?"
Then: Pode iniciar fluxo normal (agenda, consulta, etc.)
And: LOG registra MOTIVO = "MEC-02-OPERACIONAL-PERMITIDO"
```

### CA-7: Baseline Verde (P1/P0)

**Quando:** Após implementação  
**Critério:** P1 42/42 + P0 174/174 permanecem PASS  
**Validação:**
```
Given: Código modificado com governança
When: Executar P1 E2E + P0 Regressão
Then: P1 = 42/42 PASS
And:  P0 = 174/174 PASS
And:  Nenhuma regressão em fluxos existentes
```

---

## 9. CASOS DE TESTE PLANEJADOS

### Teste 1: Override Manual — Contato Pausado

```
Setup:
  - Criar contato: whatsapp:5511999999
  - Definir: responder_automaticamente = false
  - Definir: bloqueado_ate = 2030-01-01

Caso 1a: Envia mensagem pessoal
  Input: "Oi! Tudo bem? Como você está?"
  Expected: Resposta "Estou pausado"
  Assert: GPT não chamado
  Assert: LOG governanca.motivo = "MEC-03-OVERRIDE"

Caso 1b: Envia comando /retomar
  Input: "/retomar"
  Expected: Erro (contato não é dono)
  Assert: Comando recusado
```

### Teste 2: Dono Modo Silencioso

```
Setup:
  - Criar dono: user_id = tenant_id
  - Definir: modo_dono = "silencioso"

Caso 2a: Dono envia "Oi"
  Input: "Oi"
  Expected: Bloqueado
  Assert: LOG.motivo = "MEC-04-DONO-SILENCIOSO"

Caso 2b: Dono envia /status
  Input: "/status"
  Expected: Retorna status (é comando admin)
  Assert: Executado mesmo em modo silencioso
```

### Teste 3: Dono Modo Admin

```
Setup:
  - Criar dono: user_id = tenant_id
  - Definir: modo_dono = "admin"

Caso 3a: Envia "Quero agendar corte"
  Input: "Quero agendar corte"
  Expected: Bloqueado
  Assert: Não entra fluxo agendamento
  Assert: LOG.motivo contém "ADMIN-ONLY"

Caso 3b: Envia /pausar
  Input: "/pausar"
  Expected: Executado
  Assert: responder_automaticamente = false
```

### Teste 4: Profissional Silencioso

```
Setup:
  - Criar profissional: tipo_usuario = "profissional"
  - Definir: modo_profissional = "silencioso"

Caso 4a: Profissional envia qualquer mensagem
  Input: "Oi", "Como vai?", "Qual agenda?"
  Expected: Bloqueado
  Assert: LOG.motivo = "MEC-05-PROFISSIONAL"
  Assert: Não chama GPT
  Assert: Não consulta agenda
```

### Teste 5: Contato Novo — Pessoal

```
Setup:
  - Novo numero: identificado = false
  - Mensagem: 100% pessoal (confianca < 45)

Caso 5a: Pessoal puro
  Input: "Olá! Tudo bem? Como você está? Me conta sobre você"
  Expected: Silencia OU pede identificação
  Assert: LOG.motivo = "MEC-02-PESSOAL-NOVO"
  Assert: Não chama GPT
```

### Teste 6: Contato Novo — Operacional

```
Setup:
  - Novo numero: identificado = false
  - Mensagem: operacional alta confiança (>= 70)

Caso 6a: Operacional claro
  Input: "Qual é o valor do corte? Tem vaga amanhã às 15h?"
  Expected: Permite fluxo
  Assert: LOG.motivo = "MEC-02-OPERACIONAL-PERMITIDO"
  Assert: Chama GPT (fluxo normal)
```

### Teste 7: Regressão P1/P0

```
Setup:
  - Código com governança implementado

Caso 7a: P1 E2E (42 testes)
  Expected: 42/42 PASS
  Assert: Sem regressão

Caso 7b: P0 Regressão (174 testes)
  Expected: 174/174 PASS
  Assert: Sem regressão
```

---

## 10. ESPECIFICAÇÃO DE RESPOSTA À GOVERNANÇA

### Respostas Padrão

| Motivo | Resposta | Ator |
|--------|----------|------|
| MEC-03-OVERRIDE | "Estou pausado no momento." | Cliente |
| MEC-04-DONO-SILENCIOSO | "Modo silencioso ativado." | Dono |
| MEC-04-ADMIN-ONLY | "Modo admin — use /comandos" | Dono |
| MEC-05-PROFISSIONAL | "Profissional — encaminhando para equipe" | Prof |
| MEC-02-PESSOAL-NOVO | [Silencia] OR "Preciso saber seu nome primeiro" | Desconhecido |

### Auditoria Obrigatória

Cada bloqueio registra:
```json
{
  "timestamp": "ISO8601",
  "actor_id": "string",
  "tenant_id": "string",
  "decisao": "bloqueado|permitido",
  "motivo": "MEC-XX-RAZAO",
  "mensagem": "primeiros 100 chars",
  "campos_governanca": {
    "responder_automaticamente": boolean,
    "modo_dono": "string",
    "tipo_usuario": "string",
    "identificado": boolean
  }
}
```

---

## 11. SEQUÊNCIA DE IMPLEMENTAÇÃO RECOMENDADA

### Sprint 1 (MEC-03 + MEC-04)

1. Adicionar campos em Sessão (responder_aut, modo_dono)
2. Implementar bloco governança em principal_router.py:3360
3. Implementar CA-1, CA-2, CA-3, CA-7

### Sprint 2 (MEC-05)

1. Adicionar modo_profissional em Sessão
2. Verificação tipo_usuario == "profissional" em governança
3. Implementar CA-4

### Sprint 3 (MEC-02)

1. Integrar decisão de contato desconhecido
2. Validar confiança post-classificação
3. Implementar CA-5, CA-6

### Sprint 4 (Regressão + Comandos)

1. Implementar /pausar, /retomar, /status, /silencioso, /admin, /normal
2. Executar CA-7 completo
3. Validação de auditoria

---

## 12. RESUMO EXECUTIVO

| Item | Especificação |
|------|----------------|
| **Mecanismos** | 4 (MEC-03, 04, 05, 02) |
| **Campos Novos** | 5 em Sessão + 1 em Atores |
| **Pontos de Decisão** | 1 (linha 3360 router) |
| **Critérios de Aceite** | 7 (CA-1 até CA-7) |
| **Casos de Teste** | 13 subcasos em 7 testes |
| **Comandos Admin** | 6 previstos |
| **Risco de Regressão** | Baixo (isolado em governança) |
| **Compatibilidade Baseline** | 100% (P1/P0 verde) |

---

## CONCLUSÃO

Especificação completa, testável e pronta para implementação.

**Próximo passo:** Criar PRD de implementação com sprints detalhadas.

---

**Especificação:** SEG-03  
**Versão:** 1.0  
**Status:** ✅ Completa  
**Parar aqui — Sem código, sem testes, sem patches.**
