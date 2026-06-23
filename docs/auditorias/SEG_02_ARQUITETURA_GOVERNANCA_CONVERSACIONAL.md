# SEG-02 — ARQUITETURA DE GOVERNANÇA CONVERSACIONAL

**Status:** Modelagem (Sem Implementação)  
**Data:** 2026-06-23  
**Baseline:** baseline-216-pass (216/216 PASS)  
**Contexto:** SEG-01 concluído com 5 mecanismos mapeados

---

## FLUXO ATUAL

```
MENSAGEM ENTRA (Telegram)
        ↓
handlers/bot.py:430
        ↓
router/principal_router.py:3343
        ↓
[1] Resolve tenant (obter_id_dono) — Linha 3355
        ↓
[2] Carrega contexto — Linha 3360
        ↓
[3] Identidade/Onboarding — Linha 3395
        ↓
[4] Classifica conversação — Linha 3421
        ↓
[5] Roteia (GPT/Agenda/Etc)
        ↓
RESPOSTA ENVIADA
```

**Ponto de Decisão Ideal para Governança:** Entre [2] e [3]  
(Após carregar contexto, antes de identidade)

---

## BLOCO A — OVERRIDE MANUAL POR CONTATO

### Modelagem: Onde Persistir?

**Opção A1: Em Sessão (Recomendado)**

```
Caminho: Clientes/{tenant_id}/Sessoes/{actor_id}
Campo:   responder_automaticamente: bool (padrão=true)
Chave:   actor_id (telefone Telegram normalizado)
Guardado: tenant_id para isolamento multi-tenant
```

**Estrutura:**
```json
{
  "actor_id": "whatsapp:5511999005",
  "responder_automaticamente": false,
  "bloqueado_ate": "2026-06-24T15:30:00",
  "razao": "pausado_pelo_dono",
  "_tenant_id_guard": "audit_cenario_05_gpt",
  "_updated_at": "2026-06-23T12:00:00",
  "_schema_version": 2
}
```

**Opção A2: Tabela de Overrides (Alternativa)**

```
Caminho: Clientes/{tenant_id}/Governanca/Overrides/{actor_id}
Documento separado para auditoria
```

### Fluxo Completo (A1)

```
COMANDO RECEBIDO (/pausar)
    ↓
[Command Handler]
    ↓
Validar: É dono? É profissional autorizado?
    ↓
SIM → Atualizar Sessão
    └─ Clientes/{tenant_id}/Sessoes/{actor_id}
       { responder_automaticamente: false }
    └─ Registrar: razao, bloqueado_ate
    ↓
PRÓXIMA MENSAGEM ENTRA
    ↓
[GOVERNANÇA CHECK] ← NOVO PONTO
    ↓
Carregar Sessão
    └─ verifica: responder_automaticamente == false?
    ↓
SIM → BYPASS IA
    └─ return "Estou pausado"
    ↓
NÃO → Continua fluxo normal
```

### Consulta no Router

**Arquivo:** `router/principal_router.py` (após carregar contexto)

```python
# NOVO: Bloco de governança (após linha 3360)
ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id)

# NOVO: Verificar override
if ctx.get("responder_automaticamente") == False:
    print(f"[GOVERNANCA] Bypass IA — usuario pausado")
    return await _send_and_stop(context, user_id, "Estou pausado no momento.")
```

### Remoção de Override

```
COMANDO: /retomar
    ↓
Validar dono/autorizado
    ↓
Atualizar Sessão
    └─ responder_automaticamente: true
    └─ bloqueado_ate: null
    ↓
CONFIRMAÇÃO: "Voltei ao normal!"
```

### Auditoria de Histórico

**Arquivo:** `Clientes/{tenant_id}/Governanca/AuditoriaOverrides/{actor_id}/{timestamp}`

```json
{
  "acao": "pausar",
  "por": "dono",
  "razao": "conversas pessoais",
  "de": "2026-06-23T12:00:00",
  "ate": "2026-06-24T15:30:00",
  "timestamp": "2026-06-23T12:00:00Z"
}
```

---

## BLOCO B — POLÍTICA DO DONO

### Opção B1: Dono Nunca Recebe Resposta Automática

**Fluxo:**
```
Mensagem de dono_id == user_id?
    ↓
SIM → Encaminhar para humano / Silenciar
    ├─ return "encaminhando para equipe..."
    └─ registrar: mensagem recebida de dono
    ↓
NÃO → Fluxo normal (cliente/prof)
```

**Impacto Operacional:**
- ✅ Dono sempre fala com humano (máxima confiança)
- ❌ Dono não pode usar self-service (suporta agenda próprio)
- ❌ Alto atrito (dono esperando humano)
- ❌ Alto custo (humano sempre acionado)

**Risco:** Nenhum, é bloqueio completo

**Aderência ao Modelo NeoEve:** ❌ Baixa (NeoEve é self-service)

---

### Opção B2: Dono Recebe Apenas Comandos Administrativos

**Fluxo:**
```
Mensagem de dono_id == user_id?
    ↓
SIM → Classificar como admin?
    ├─ Contém: "/", "pausar", "desativar", etc.
    │  └─ Responder como comando
    └─ Contém: conversa pessoal?
       └─ Silenciar / Encaminhar
    ↓
NÃO → Fluxo normal
```

**Impacto Operacional:**
- ✅ Dono pode administrar (pausar bot, etc)
- ✅ Dono não recebe conversa automática
- ⚠️ Médio atrito (dono aprende comandos)
- ⚠️ Médio custo (só humano se conversa pessoal)

**Risco:** Dono testa limites conversacionais (acha que é conversa normal)

**Aderência ao Modelo NeoEve:** ⚠️ Média (adiciona modo admin)

---

### Opção B3: Dono Pode Alternar Modos

**Fluxo:**
```
Mensagem de dono_id == user_id?
    ↓
SIM → Verificar: modo_dono?
    ├─ modo_dono == "silencio"
    │  └─ Silenciar
    ├─ modo_dono == "admin_only"
    │  └─ Apenas comandos
    ├─ modo_dono == "normal"
    │  └─ Fluxo cliente
    ↓
NÃO → Fluxo normal
```

**Impacto Operacional:**
- ✅ Flexibilidade máxima
- ✅ Dono escolhe proteção
- ✅ Baixo atrito
- ⚠️ Complexidade (3 modos)

**Risco:** Dono ativa "normal" sem querer proteção

**Aderência ao Modelo NeoEve:** ✅ Alta (alinha com self-service)

---

## BLOCO C — POLÍTICA DE PROFISSIONAIS

### Análise Estrutural

**Pergunta 1: Profissional é cliente?**

Resposta (Atual): SIM (em contexto operacional)
```
Path: Clientes/{tenant_id}/Atores/{actor_id}
tipo_usuario: "profissional"

Mas recebe resposta automática como cliente.
```

**Pergunta 2: Profissional é ator interno?**

Resposta (Atual): SIM (cadastrado em Profissionais)
```
Path: Clientes/{tenant_id}/Profissionais/{prof_id}
Mas não diferenciado em fluxo de resposta.
```

**Pergunta 3: Profissional deve passar pelo GPT?**

Cenário A (Atual): SIM
```
Profissional conversa
  ↓
Classificador → operacional/pessoal
  ↓
GPT processa
  ↓
Responde
```

Cenário B (Alternativa): NÃO
```
Profissional conversa
  ↓
[GOVERNANÇA CHECK]
  ↓
Profissional? SIM → Encaminhar humano
```

**Pergunta 4: Como diferenciar profissional de cliente?**

**Opção C1: Por tipo_usuario**
```python
tipo_usuario = await buscar_tipo_usuario(actor_id, tenant_id)
if tipo_usuario == "profissional":
    return await encaminhar_humano()
```

**Opção C2: Por presença em Profissionais**
```python
eh_profissional = actor_id in await buscar_profissionais(tenant_id)
if eh_profissional:
    return await encaminhar_humano()
```

**Recomendado:** C1 (mais direto, já existe em contexto)

---

### Modelagem de Fluxo

```
Mensagem entra
    ↓
Carregar contexto
    ├─ tipo_usuario = "profissional"?
    ↓
SIM → BYPASS IA
    ├─ return "Encaminhando para equipe..."
    └─ Registrar: mensagem de profissional
    ↓
NÃO → Fluxo normal (cliente/dono)
```

**Impacto:**
- ✅ Profissional não recebe automação
- ✅ Profissional sempre fala com humano
- ❌ Alto custo (humano sempre)
- ❌ Profissional não usa self-service da agenda

---

## BLOCO D — CONTATOS DESCONHECIDOS

### Opção D1: Nunca Responder

```
Contato novo (sem documento Clientes/{user_id})?
    ↓
SIM → Silenciar
    └─ return "Desculpa, nao reconheci seu numero. 
                Contacte o salao direto."
    └─ Registrar: contato desconhecido ignorado
```

**Impacto:** ❌ Alto (perde clientes novos)

---

### Opção D2: Responder Apenas Saudação

```
Contato novo?
    ↓
SIM → 
    ├─ É saudação? ("Oi", "Olá", etc)
    │  └─ Responder: "Oi! Como posso ajudar?"
    └─ É pedido/conversa?
       └─ Silenciar: "Precisa se identificar primeiro"
    ↓
NÃO → Fluxo normal
```

**Impacto:** ⚠️ Médio (oferece onboarding, mas bloqueia pedidos)

---

### Opção D3: Responder Após Identificação

```
Contato novo?
    ↓
SIM → 
    ├─ Pedir identificação
    │  └─ "Qual é seu nome? Você é cliente ou profissional?"
    ├─ Aguardar resposta
    │  └─ Criar documento Clientes/{user_id}
    │  └─ Atualizar tipo_usuario
    ├─ Agora pode responder
    │  └─ Fluxo normal
```

**Impacto:** ✅ Baixo (onboarding natural, sem atrito)

---

### Opção D4: Modo Híbrido

```
Contato novo?
    ↓
SIM → 
    ├─ Responder apenas SAUDAÇÃO (D2)
    ├─ Responder apenas OPERACIONAL (se > 70 confiança)
    └─ Bloquear PESSOAL completamente
    ↓
NÃO → Fluxo normal
```

**Impacto:** ✅ Equilibrado (oferece mais, mantém proteção)

---

## BLOCO E — PONTO DE DECISÃO

### Localização Exata no Fluxo

```
FLUXO ATUAL:
handlers/bot.py:430
    ↓
router/principal_router.py:3343 (inicio)
    ↓
Linha 3355: dono_id = await obter_id_dono(user_id)
    ↓
Linha 3360: ctx = await carregar_contexto_temporario(user_id, tenant_id=dono_id)
    ↓
┌───────────────────────────────────────────┐
│ [NOVO] BLOCO DE GOVERNANÇA ← AQUI         │
│                                           │
│ 1. Verificar override (responder_aut)    │
│ 2. Verificar política dono               │
│ 3. Verificar política profissional       │
│ 4. Verificar contato desconhecido        │
│                                           │
│ if [governanca_bloqueia]:                │
│     return [resposta_bloqueada]          │
└───────────────────────────────────────────┘
    ↓
Linha 3366: processar_fluxo_identidade_onboarding()
    ↓
Linha 3421: normalizar_intencao_humana()
    ↓
Classificador
    ↓
GPT
    ↓
Retorna resposta
```

### Justificação

**Por que entre linha 3360 e 3366?**

✅ **Contexto já carregado** → Tem dados para decidir  
✅ **Tenant resolvido** → Sabe quem é o usuario  
✅ **Antes de identidade** → Pode bloquear antes de processamento  
✅ **Antes de classificador** → Evita custo GPT desnecessário  
❌ **Não bloqueia onboarding** → Contatos novos ainda são onboarded  

---

## TABELA FINAL DE ARQUITETURA

| Mecanismo | Persistência | Consulta | Impacto | Complexidade |
|-----------|--------------|----------|---------|--------------|
| **MEC-03: Override Manual** | `Clientes/{tenant}/Sessoes/{actor}` | `responder_automaticamente` | ⚠️ Médio (novo campo) | 🟢 Baixa (1 flag bool) |
| **MEC-04: Política Dono** | Tipo_usuario + ctx | `if user_id == dono_id` | ❌ Alto (perde função) | 🟢 Baixa (1 check) |
| **MEC-05: Política Prof** | tipo_usuario | `if tipo_usuario == prof` | ❌ Alto (prof sem IA) | 🟢 Baixa (1 check) |
| **MEC-02: Contato Novo** | Clientes/{user_id} | `if doc.exists` | ⚠️ Médio (onboarding) | 🟡 Média (lógica if/else) |

---

## RECOMENDAÇÃO ARQUITETURAL

### Menor Risco + Menor Atrito + Maior Aderência

**Combinação Recomendada:**

1. **MEC-03 (Override Manual):** ✅ IMPLEMENTAR
   - Path: `Clientes/{tenant}/Sessoes/{actor}`
   - Flag: `responder_automaticamente` (bool)
   - Comando: `/pausar`, `/retomar`
   - Impacto: Baixo, alinha com self-service
   - Risco: Nenhum (opt-in)

2. **MEC-04 (Dono):** OPÇÃO B3 (Alternar Modos)
   - Modo: silent / admin / normal
   - Padrão: "normal" (aderência)
   - Dono escolhe proteção
   - Impacto: Baixo atrito

3. **MEC-05 (Profissional):** ⚠️ REQUER DECISÃO
   - Profissional é cliente na agenda? SIM
   - Profissional recebe automação? ⚠️ A DECIDIR
   - Opção A: Sim (aderência máxima, risco conversacional)
   - Opção B: Não (máxima proteção, baixa funcionalidade)

4. **MEC-02 (Contato Novo):** OPÇÃO D4 (Híbrida)
   - Responder saudação? SIM
   - Responder operacional alto-confiança? SIM
   - Responder pessoal? NÃO
   - Encaminhar para identificação: SIM

### Ponto de Decisão

**Inserir BLOCO DE GOVERNANÇA após linha 3360:**
```
Após: ctx = await carregar_contexto_temporario()
Antes: await processar_fluxo_identidade_onboarding()
```

---

## MATRIZ DE COMPATIBILIDADE

| Aspecto | MEC-03 | MEC-04 B3 | MEC-05 A | MEC-02 D4 | Score |
|---------|--------|-----------|----------|-----------|-------|
| Multi-tenant | ✅ | ✅ | ✅ | ✅ | 100% |
| Persistência simples | ✅ | ✅ | ✅ | ⚠️ | 75% |
| Sem alteração fluxo principal | ✅ | ✅ | ✅ | ⚠️ | 75% |
| Self-service preservado | ✅ | ✅ | ⚠️ | ✅ | 75% |
| GPT-cost otimizado | ✅ | ✅ | ✅ | ✅ | 100% |
| **SCORE TOTAL** | | | | | **85%** |

---

## CONCLUSÃO

**Arquitetura Recomendada:** Combinação MEC-03 + MEC-04(B3) + MEC-05(?) + MEC-02(D4)

**Características:**
- ✅ Governança em ponto único (após carregar contexto)
- ✅ Sem refatoração grande do router
- ✅ Multi-tenant seguro (tenant_id guard)
- ✅ Compatível com baseline (216/216 PASS)
- ✅ Extensível (novos mecanismos depois)

**Próximo Passo:** Decisão sobre MEC-05 (profissional: proteção ou funcionalidade?)

---

**Modelagem:** SEG-02  
**Data:** 2026-06-23  
**Status:** Sem Implementação  
**Autoria:** Claude Code (Auditoria + Modelagem apenas)  
**Ponto de Decisão:** Linha 3360 de principal_router.py

**PARAR AQUI — Modelagem concluída, sem patches, sem testes, sem código alterado.**
