# SEG-04 — PRD DE IMPLEMENTAÇÃO SPRINT 1
## MEC-03 Override Manual + MEC-04 Modo Dono

**Status:** Product Requirements Document  
**Data:** 2026-06-23  
**Sprint:** 1 de 4  
**Baseline:** 216/216 PASS (P1 42/42 + P0 174/174)  
**Baseado em:** SEG-01, SEG-02, SEG-03, SEG-03A  

---

## 1. PROBLEMA

### Situação Atual

- Usuários não podem pausar respostas automáticas
- Donos não podem escolher modo de interação
- Não há log de decisões administrativas
- Sem mecanismo de governança sobre automação

### Impacto

- Usuários recebem respostas automáticas mesmo querendo silêncio
- Donos não controlam automação no seu negócio
- Falta rastreabilidade de mudanças de política

---

## 2. OBJETIVO

Implementar dois mecanismos de governança conversacional para:
- Permitir que contatos pausem respostas automáticas (MEC-03)
- Permitir que donos escolham modo de interação (MEC-04)
- Criar auditoria de todas as decisões de governança

**Resultado esperado:** Usuários e donos têm controle sobre automação, com auditoria completa.

---

## 3. ESCOPO SPRINT 1

### Incluso

✅ **MEC-03: Override Manual por Contato**
- Coleção Governanca/{actor_id}
- Campo responder_automaticamente (bool)
- Bloqueia IA quando false
- Bloqueia agenda quando false

✅ **MEC-04: Modo do Dono**
- Campo modo_dono em Governanca/{actor_id}
- 3 modos: normal, admin, silencioso
- Cada modo com regras distintas

✅ **AuditoriaGovernanca**
- Coleção AuditoriaGovernanca/{evento_id}
- Registra toda alteração de policy

✅ **Bloco de Decisão**
- Inserção em router/principal_router.py:3360
- Antes de identidade/onboarding

✅ **Comandos Administrativos**
- /pausar (client)
- /retomar (client)
- /status (client)
- /silencioso (dono)
- /admin (dono)
- /normal (dono)

---

## 4. FORA DE ESCOPO SPRINT 1

❌ MEC-05 (Profissional como ator interno) — Sprint 2  
❌ MEC-02 (Contato desconhecido) — Sprint 3  
❌ Interface de comando Web/Dashboard — Sprint 4  
❌ Notificações para humano — Sprint 4+  
❌ TTL de bloqueio automático — Sprint 4+  

---

## 5. MODELO DE DADOS

### 5.1 Clientes/{tenant_id}/Governanca/{actor_id}

**Novo documento persistido em Firestore**

```json
{
  "actor_id": "whatsapp:5511999005",
  "responder_automaticamente": true,
  "bloqueado_ate": null,
  "modo_dono": "normal",
  "atualizado_em": "2026-06-23T12:00:00Z",
  "atualizado_por": "dono",
  "motivo": "usuario pausou via /pausar",
  "_tenant_id_guard": "audit_cenario_05_gpt",
  "_schema_version": 1
}
```

**Campos Obrigatórios:**
- `actor_id`: string (telefone/ID do ator)
- `responder_automaticamente`: boolean (default: true)
- `modo_dono`: "normal" | "admin" | "silencioso" (default: "normal")
- `atualizado_em`: ISO8601 timestamp
- `_tenant_id_guard`: tenant_id (validação multi-tenant)
- `_schema_version`: 1

**Campos Opcionais:**
- `bloqueado_ate`: ISO8601 (para pausas temporárias)
- `atualizado_por`: "dono" | "sistema" | "admin"
- `motivo`: string (razão da alteração)

---

### 5.2 Clientes/{tenant_id}/AuditoriaGovernanca/{evento_id}

**Novo documento append-only (imutável)**

```json
{
  "evento_id": "audit_gov_20260623_120000_abc123",
  "timestamp": "2026-06-23T12:00:00.123Z",
  "actor_id_afetado": "whatsapp:5511999005",
  "actor_id_executor": "whatsapp:5511999005",
  "comando": "/pausar",
  "campo_alterado": "responder_automaticamente",
  "valor_anterior": true,
  "valor_novo": false,
  "bloqueado_ate": "2026-06-24T12:00:00Z",
  "motivo": "usuario solicitou pausa",
  "_tenant_id_guard": "audit_cenario_05_gpt",
  "_schema_version": 1
}
```

**Campos Obrigatórios:**
- `evento_id`: string (unique, formato timestamp + rand)
- `timestamp`: ISO8601 timestamp
- `actor_id_afetado`: string (quem foi afetado)
- `comando`: string (qual comando foi executado)
- `campo_alterado`: string (qual campo foi alterado)
- `valor_anterior`: any (valor antes)
- `valor_novo`: any (valor depois)
- `_tenant_id_guard`: tenant_id

**Índices Necessários:**
- `_tenant_id_guard` (partition)
- `timestamp` (ordenar por recente)
- `actor_id_afetado` (buscar histórico por ator)

---

## 6. FLUXO DE DECISÃO

### 6.1 Localização Exata no Código

**Arquivo:** `router/principal_router.py`

**Linha de Inserção:** 3360 (após carregar contexto)

```python
# Linha 3355-3360 existente
dono_id = await obter_id_dono(user_id)
ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}

# ┌─────────────────────────────────────────────────┐
# │ [NOVO] BLOCO DE GOVERNANÇA — INSERIR AQUI       │
# └─────────────────────────────────────────────────┘

# Linha 3366 existente
decisao_confirmacao = await resolver_confirmacao_pendente(...)
```

---

### 6.2 Pseudocódigo do Bloco

```python
async def verificar_governanca(user_id, dono_id, ctx):
    """
    Verifica se contato/dono tem override de governança.
    Retorna (bloqueado: bool, motivo: str, resposta: str | None)
    """
    
    # 1. Carregar Governanca
    governanca = await buscar_governanca(user_id, dono_id)
    if not governanca:
        governanca = {
            "responder_automaticamente": true,
            "modo_dono": "normal"
        }
    
    # 2. MEC-03: Override Manual
    if governanca["responder_automaticamente"] == false:
        return (
            bloqueado=true,
            motivo="MEC-03-OVERRIDE-MANUAL",
            resposta="Estou pausado no momento."
        )
    
    # 3. MEC-04: Modo Dono (se user_id == dono_id)
    if user_id == dono_id:
        modo = governanca.get("modo_dono", "normal")
        
        if modo == "silencioso":
            return (
                bloqueado=true,
                motivo="MEC-04-DONO-SILENCIOSO",
                resposta="Modo silencioso ativado."
            )
        elif modo == "admin":
            # Não bloqueia aqui, mas marcará contexto
            # para filtrar apenas comandos admin depois
            ctx["modo_admin_ativo"] = true
    
    # 4. Nenhum bloqueio
    return (
        bloqueado=false,
        motivo="NENHUM",
        resposta=None
    )

# No router, após bloco:
bloqueado, motivo, resposta = await verificar_governanca(user_id, dono_id, ctx)
if bloqueado:
    return await _send_and_stop(context, user_id, resposta)

# Continuar fluxo normal
await processar_fluxo_identidade_onboarding(...)
```

---

## 7. COMANDOS ADMINISTRATIVOS

### 7.1 Comando: /pausar

**Requisito:** Qualquer contato pode pausar a si mesmo

**Ação:**
```
1. Validar: é comando?
2. Executar: Governanca/{user_id}.responder_automaticamente = false
3. Registrar: AuditoriaGovernanca evento
4. Responder: "Pausado até {bloqueado_ate}"
```

**Mensagem de Retorno:**
```
"Entendi! Vou ficar em silêncio por enquanto. 
Use /retomar para voltar ao normal."
```

**Default Bloqueio:** 24 horas (configurável)

---

### 7.2 Comando: /retomar

**Requisito:** Qualquer contato pode retomar a si mesmo

**Ação:**
```
1. Validar: é comando?
2. Executar: Governanca/{user_id}.responder_automaticamente = true
3. Executar: Governanca/{user_id}.bloqueado_ate = null
4. Registrar: AuditoriaGovernanca evento
5. Responder: "Voltei ao normal!"
```

**Mensagem de Retorno:**
```
"Pronto! Voltei ao normal. Como posso ajudar?"
```

---

### 7.3 Comando: /status

**Requisito:** Qualquer contato

**Ação:**
```
1. Validar: é comando?
2. Carregar: Governanca/{user_id}
3. Responder: estado atual
```

**Mensagem de Retorno:**
```
"Meu status:
- Respondendo: sim ✓
- Modo: normal
- Última alteração: 2026-06-23 12:00"
```

---

### 7.4 Comando: /silencioso

**Requisito:** user_id == dono_id

**Ação:**
```
1. Validar: é dono?
2. Executar: Governanca/{dono_id}.modo_dono = "silencioso"
3. Registrar: AuditoriaGovernanca evento
4. Responder: "Modo silencioso ativado"
```

**Mensagem de Retorno:**
```
"Modo silencioso ativado. 
Não vou responder automaticamente até você usar /normal."
```

---

### 7.5 Comando: /admin

**Requisito:** user_id == dono_id

**Ação:**
```
1. Validar: é dono?
2. Executar: Governanca/{dono_id}.modo_dono = "admin"
3. Registrar: AuditoriaGovernanca evento
4. Responder: "Modo admin ativado"
```

**Mensagem de Retorno:**
```
"Modo admin ativado. 
Vou responder apenas comandos administrativos."
```

---

### 7.6 Comando: /normal

**Requisito:** user_id == dono_id

**Ação:**
```
1. Validar: é dono?
2. Executar: Governanca/{dono_id}.modo_dono = "normal"
3. Registrar: AuditoriaGovernanca evento
4. Responder: "Modo normal ativado"
```

**Mensagem de Retorno:**
```
"Modo normal ativado. 
Voltei ao comportamento padrão."
```

---

## 8. CRITÉRIOS DE ACEITE

### CA-01: Contato Pausado Bloqueado

**When:** responder_automaticamente = false  
**Then:**
- ✅ Não entra fluxo de cliente
- ✅ Não chama GPT
- ✅ Não consulta agenda
- ✅ Retorna "Estou pausado no momento."

**Teste:**
```
Given: responder_automaticamente = false
When: Enviar "Agende corte"
Then: Retorna "Estou pausado"
And: AuditoriaGovernanca log NOT criado (bloqueio é automático)
```

---

### CA-02: Contato Retomado Normal

**When:** /retomar executado  
**Then:**
- ✅ responder_automaticamente = true
- ✅ bloqueado_ate = null
- ✅ Fluxo volta ao normal
- ✅ AuditoriaGovernanca registra evento

**Teste:**
```
Given: responder_automaticamente = false
When: Executar /retomar
Then: responder_automaticamente = true
And: Próxima mensagem entra fluxo normal
And: AuditoriaGovernanca evento criado
```

---

### CA-03: Dono Silencioso Bloqueado

**When:** modo_dono = "silencioso" AND user_id == dono_id  
**Then:**
- ✅ Não recebe resposta automática
- ✅ Retorna "Modo silencioso ativado."
- ✅ Pode executar /normal para voltar

**Teste:**
```
Given: modo_dono = "silencioso", user_id == dono_id
When: Dono envia "Oi"
Then: Retorna "Modo silencioso ativado"
And: Não entra fluxo
```

---

### CA-04: Dono Admin Filtrado

**When:** modo_dono = "admin" AND user_id == dono_id  
**Then:**
- ✅ Comandos /pausar, /retomar, /status, /silencioso, /admin, /normal são executados
- ✅ Conteúdo pessoal é bloqueado
- ✅ Conteúdo operacional que não é comando é bloqueado

**Teste:**
```
Given: modo_dono = "admin"
When: Dono envia "/pausar"
Then: Executado com sucesso

When: Dono envia "Como você está?"
Then: Bloqueado (não é comando admin)
```

---

### CA-05: Dono Normal Sem Mudança

**When:** modo_dono = "normal" AND user_id == dono_id  
**Then:**
- ✅ Comportamento idêntico a atual (sem governança)
- ✅ Fluxo cliente completo funciona
- ✅ GPT é chamado
- ✅ Agenda pode ser consultada

**Teste:**
```
Given: modo_dono = "normal" (default), user_id == dono_id
When: Dono envia "Agende corte"
Then: Fluxo cliente normal (baseline)
```

---

### CA-06: Auditoria Registra Tudo

**When:** Qualquer comando administrativo executado  
**Then:**
- ✅ AuditoriaGovernanca/{evento_id} criado
- ✅ Contém: comando, campo_alterado, valor_anterior, valor_novo, timestamp
- ✅ _tenant_id_guard preenchido

**Teste:**
```
Given: Nenhuma auditoria anterior
When: Executar /pausar
Then: AuditoriaGovernanca documento criado
And: Contém: ["comando", "campo_alterado", "valor_anterior", "valor_novo"]
```

---

### CA-07: Default Não Muda Comportamento

**When:** Governanca/{actor_id} não existe  
**Then:**
- ✅ Comportamento continua idêntico (fluxo normal)
- ✅ responder_automaticamente = true (implícito)
- ✅ modo_dono = "normal" (implícito)
- ✅ Nenhum bloqueio

**Teste:**
```
Given: Governanca/{actor_id} não existe
When: Enviar qualquer mensagem
Then: Fluxo normal (sem Governanca)
And: Não cria documento até primeiro comando
```

---

### CA-08: Baseline Verde

**When:** Implementação concluída  
**Then:**
- ✅ P1 E2E: 42/42 PASS
- ✅ P0 Regressão: 174/174 PASS
- ✅ Nenhuma mudança de comportamento em fluxos existentes

**Teste:**
```
python -m pytest tests/p1_e2e_*.py -v
→ 42/42 PASS

python -m pytest tests/p0_*.py -v
→ 174/174 PASS
```

---

## 9. TESTES PLANEJADOS

### T1: MEC-03 Override Manual (5 testes)

```
T1.1: Contato pausado envia "Olá"
      → Bloqueado, retorna "Estou pausado"

T1.2: Contato pausado envia "Agende corte"
      → Bloqueado, GPT não chamado

T1.3: Contato pausado executa /retomar
      → Executado, volta ao normal

T1.4: Contato retomado envia mensagem
      → Fluxo normal

T1.5: Auditoria registra /pausar e /retomar
      → 2 eventos em AuditoriaGovernanca
```

### T2: MEC-04 Modo Dono (6 testes)

```
T2.1: Dono modo normal (default)
      → Fluxo cliente completo

T2.2: Dono modo silencioso
      → Bloqueado, "Modo silencioso ativado"

T2.3: Dono modo silencioso executa /normal
      → Volta ao normal

T2.4: Dono modo admin
      → Comandos executados

T2.5: Dono modo admin envia conversa pessoal
      → Bloqueado

T2.6: Auditoria registra /silencioso, /admin, /normal
      → 3 eventos em AuditoriaGovernanca
```

### T3: Regressão (2 testes)

```
T3.1: P1 E2E 42/42 PASS
      → Nenhuma regressão

T3.2: P0 Regressão 174/174 PASS
      → Nenhuma regressão
```

---

## 10. PLANO DE IMPLEMENTAÇÃO POR LOTES

### LOTE A: Estrutura de Dados (1-2 dias)

**Tarefas:**
1. Criar serviço `services/governanca_service.py`
   - `async def carregar_governanca(actor_id, tenant_id)`
   - `async def atualizar_governanca(actor_id, tenant_id, updates, executor_id, motivo)`
   - `async def registrar_auditoria(actor_id_afetado, comando, campo, anterior, novo, tenant_id)`

2. Criar testes unitários em `tests/unit_governanca_service.py`
   - Mocking Firestore
   - Testes de carregar/atualizar
   - Testes de auditoria

**Critério de Conclusão:** Tests 100% green, serviço pronto para uso

---

### LOTE B: Bloco de Decisão no Router (2-3 dias)

**Tarefas:**
1. Implementar função `verificar_governanca()` em router/principal_router.py:3360
   - Carregar Governanca
   - Verificar MEC-03 (responder_automaticamente)
   - Verificar MEC-04 (modo_dono)
   - Retornar decisão

2. Criar testes em `tests/test_governanca_router.py`
   - Teste bloquei MEC-03
   - Teste bloqueio MEC-04 (silencioso)
   - Teste modo admin
   - Teste default

**Critério de Conclusão:** Tests passam, bloco integrado, P1/P0 ainda green

---

### LOTE C: Comandos Administrativos (2-3 dias)

**Tarefas:**
1. Criar handler de comandos em `handlers/commands_handler.py`
   - Detectar /pausar, /retomar, /status, /silencioso, /admin, /normal
   - Validar permissões (dono vs contato)
   - Chamar governanca_service.atualizar_governanca()
   - Registrar auditoria

2. Criar testes em `tests/test_commands_handler.py`
   - /pausar — cliente (sucesso)
   - /retomar — cliente (sucesso)
   - /status — cliente (retorna status)
   - /silencioso — dono (sucesso)
   - /admin — dono (sucesso)
   - /normal — dono (sucesso)
   - /silencioso — cliente (erro: apenas dono)

**Critério de Conclusão:** Todos os comandos funcionam, P1/P0 still green

---

### LOTE D: Integração e Regressão (1-2 dias)

**Tarefas:**
1. Integração full-stack com audit_cenario_05_gpt_real.py
   - Criar cenários de teste
   - Validar bloqueios funcionam em fluxo real

2. Executar P1 E2E + P0 Regressão
   - 42/42 PASS
   - 174/174 PASS

3. Testes manuais
   - Pausa/retoma funcionam
   - Modo dono funciona
   - Auditoria registra tudo

**Critério de Conclusão:** CA-01 a CA-08 PASS

---

## 11. PLANO DE ROLLBACK

**Se falha encontrada antes de merge:**
```bash
git reset --hard origin/main
```

**Se falha encontrada após merge:**
1. Criar revert commit
2. Merge revert ao main
3. Análise pós-mortem

**Failsafe:** Bloqueio é conservador (default = sem bloqueio), então falha em governança não causa bloqueio indevido.

---

## 12. RISCOS E MITIGAÇÕES

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Bloqueio permanente | CRÍTICA | Default = sem bloqueio; usuário pode /retomar |
| Duplicate evento auditoria | MÉDIA | Índice único em event_id (timestamp+rand) |
| Performance (+2 Firestore reads) | BAIXA | Índices em _tenant_id_guard, actor_id |
| Contato não consegue desbloqueador | CRÍTICA | /retomar sempre funciona |
| Dono em modo admin bloqueia tudo | MÉDIA | Testes em LOTE C validam filtro |
| Regressão P1/P0 | CRÍTICA | Regressão em LOTE D |

---

## CHECKLIST DE IMPLEMENTAÇÃO

- [ ] **LOTE A:** Serviço governanca_service.py
- [ ] **LOTE A:** Testes unitários
- [ ] **LOTE B:** Bloco verificar_governanca em router
- [ ] **LOTE B:** Testes router
- [ ] **LOTE C:** Handlers de comandos
- [ ] **LOTE C:** Testes de comandos
- [ ] **LOTE D:** Testes de integração
- [ ] **LOTE D:** P1 E2E 42/42 PASS
- [ ] **LOTE D:** P0 Regressão 174/174 PASS
- [ ] **LOTE D:** Testes manuais
- [ ] **LOTE D:** Merge ao main

---

## CONCLUSÃO

Sprint 1 implementa governança básica com **zero risco de regressão** porque:
1. Defaults preservam comportamento atual
2. Bloqueios são conservadores
3. Regressão é testada ao final
4. Rollback é simples (revert commit)

**Estimativa:** 4-6 dias, 4 lotes, 21 testes

---

**PRD:** SEG-04  
**Status:** ✅ Pronto para implementação  
**Próximo:** Sprint 2 (MEC-05)

**Parar aqui — Sem código, sem patch, sem teste.**
