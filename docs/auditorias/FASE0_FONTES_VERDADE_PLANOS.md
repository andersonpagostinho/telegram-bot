# FASE 0 — VALIDAÇÃO DE FONTES DE VERDADE ATUAIS

**Data:** 2026-07-29  
**Status:** ✅ MAPEAMENTO COMPLETO

---

## 🎯 RESUMO EXECUTIVO

Existem **TRÊS fontes de verdade simultâneas e potencialmente divergentes**:

1. **plan_id** (Eventos Comerciais) — Histórico, imutável
2. **planosAtivos** (Firebase/Clientes) — Estado atual, mutável
3. **pagamentoAtivo** (Firebase/Clientes) — Flag booleano, mutável

**Problema:** Nenhuma é a fonte canônica. Não há sincronização garantida.

---

## 📍 FONTE 1: PLAN_ID (Eventos Comerciais)

### Localização
```
domain/commercial_events.py:147-149
TrialActivated.plan_id
SubscriptionActivated.plan_id
SubscriptionPaid.plan_id
```

### Características
- ✅ Imutável (evento é freezado)
- ✅ Histórico completo
- ✅ Auditável
- ❌ Somente leitura após escrita
- ❌ Não pode ser usado para decisão atual (histórico)

### Quem escreve
```
services/billing_application_service.py:52
    webhook → agregado → evento
```

### Quem lê
```
services/billing_domain_service.py:156
    (apenas mapeamento, não decisão)
```

### Prioridade Atual
🟡 MÉDIA — Usado apenas para histórico

### Conflita Com
```
planosAtivos (pode estar desatualizado)
pagamentoAtivo (pode estar inconsistente)
```

### Destino (Phase 2+)
```
Será fonte canônica via novo modelo de assinatura
Tenants/{tenant_id}/Assinatura/Atual
```

---

## 📍 FONTE 2: PLANOS_ATIVOS (Firebase Clientes)

### Localização
```
Firestore Collection: Clientes
Document: {user_id}
Field: planosAtivos (array de strings)
```

### Estrutura Atual
```json
{
  "planosAtivos": ["secretaria"],  // ← SEMPRE inicializado assim
  "dataAssinatura": "...",
  "proximoPagamento": "..."
}
```

### Características
- ⚠️ Mutável (pode ser alterado)
- ✅ Fácil de ler
- ❌ Sem versionamento
- ❌ Sem histórico
- ❌ Sem validação de plano canônico

### Quem escreve
```
services/firebase_service.py:57-61
    → salvar_cliente() com default ["secretaria"]

handlers/bot.py:237
    → Possível atualização manual (não mapeada totalmente)
```

### Quem lê
```
handlers/bot.py:156, 178
handlers/gpt_text_handler.py:89, 112
handlers/perfil_handler.py:45, 67, 123
handlers/voice_command_handler.py:102, 234
scheduler/email_to_event_loop.py:45
utils/plan_utils.py:36, 52
utils/gpt_utils.py:67, 134
services/gpt_service.py:125, 140, 156
services/gpt_service(1).py:89
+ 7 outros pontos
```

### Prioridade Atual
🔴 CRÍTICA — Usado para decisão em production

### Conflita Com
```
pagamentoAtivo (um pode ser true, outro false)
plan_id histórico (pode estar desatualizado)
```

### Problemas Conhecidos
1. **Default Hardcoded**
   - Todo novo cliente recebe `["secretaria"]`
   - Sem validação contra plano pago
   
2. **Sem Sincronização com Pagamento**
   - Cliente pode ter `planosAtivos=["secretaria"]` mas `pagamentoAtivo=false`
   - Ou vice-versa

3. **Sem Histórico**
   - Mudança de plano não registrada
   - Impossível auditar quando/por quem

4. **Sem Validação de Normalização**
   - Poderia conter `"Solo"`, `"solo"`, `"SOLO"`, `"solo-pro"`
   - Sem função de normalização em escrita

---

## 📍 FONTE 3: PAGAMENTO_ATIVO (Firebase Clientes)

### Localização
```
Firestore Collection: Clientes
Document: {user_id}
Field: pagamentoAtivo (boolean)
```

### Estrutura Atual
```json
{
  "pagamentoAtivo": true,  // ← SEMPRE true no salvar_cliente
  "dataAssinatura": "...",
  "proximoPagamento": "..."
}
```

### Características
- ⚠️ Mutável (pode ser alterado)
- ✅ Simples (booleano)
- ❌ Sem granularidade (não diferencia plano)
- ❌ Sem histórico
- ❌ Sem informação de motivo (why false?)

### Quem escreve
```
services/firebase_service.py:57
    → salvar_cliente() com default true

handlers/bot.py:237
    → Possível atualização manual (não documentada)
```

### Quem lê
```
handlers/bot.py:159, 180
handlers/gpt_text_handler.py:91, 114
handlers/perfil_handler.py:46, 68, 124
handlers/voice_command_handler.py:104
scheduler/daily_summary.py:80
scheduler/email_to_event_loop.py:46
utils/plan_utils.py:33, 54
utils/gpt_utils.py:70
services/gpt_service.py:128, 145, 159
services/gpt_service(1).py:92
+ 3 outros pontos
```

### Prioridade Atual
🔴 CRÍTICA — Usado como gate binário para todas as operações

### Conflita Com
```
planosAtivos (ambos podem estar desatualados)
Máquina de estado de assinatura (states não mapeados)
```

### Problemas Conhecidos
1. **Default Hardcoded**
   - Todo novo cliente recebe `true`
   - Sem validação contra webhook ou contrato

2. **Sem Semântica**
   - `false` pode significar:
     - Pagamento não feito?
     - Cancelamento agendado?
     - Suspensão?
     - Inadimplência?
   - Sistema não diferencia

3. **Sem Histórico**
   - Mudança de status não registrada
   - Impossível saber quando ficou false

4. **Sem Integração com Máquina de Estado**
   - Assinatura tem estados (TRIAL, ATIVA, INADIMPLENTE, CANCELADA, etc)
   - pagamentoAtivo não reflete esses estados

---

## 📊 MATRIZ DE CONVERGÊNCIA: QUAL FONTE PREVALECE?

| Cenário | planosAtivos | pagamentoAtivo | plan_id | Comportamento Real | Problema |
|---------|--------------|-----------------|---------|-------------------|----------|
| Novo cliente | `["secretaria"]` | `true` | Ausente | ✅ Pode usar tudo | Default demais |
| Downgrade em progresso | `["studio"]` | `true` | `STUDIO` | ⚠️ Usa recurso antigo | Sem sincronização |
| Trial expirado | `["studio"]` | `false` | `STUDIO` | ✅ Bloqueado | Mas por qual motivo? |
| Upgrade em progresso | `["solo"]` | `true` | `SOLO_PRO` | ❌ Usa recurso velho | Divergência |
| Cancelado imediato | `["studio"]` | `false` | `STUDIO` (histórico) | ✅ Bloqueado | Estado correto por acaso |
| Migração manual | `[qualquer]` | `true` | Pode estar vazio | ❌ Impredizível | Sem fonte de verdade |

---

## 🚨 RISCOS CRÍTICOS IDENTIFICADOS

### RISCO 1: Divergência plan_id vs planosAtivos
**Tipo:** EXISTENTE_AGORA  
**Cenário:**
```
planosAtivos = ["secretaria"]  (antigo)
plan_id = STUDIO              (novo webhook recebido)
pagamentoAtivo = true

Cliente tenta usar recurso Studio → bloqueado por planosAtivos antigo
```

**Mitigation:** Phase 2 — assinatura única como fonte

---

### RISCO 2: Default True permite acesso sem contrato
**Tipo:** EXISTENTE_AGORA  
**Cenário:**
```
novo cliente criado
salvar_cliente(user_id, {nome: "João"})
→ Firebase retorna pagamentoAtivo=true automaticamente
→ Cliente pode agendar mesmo sem pagamento verificado
```

**Mitigation:** Phase 2 — remover defaults, exigir assinatura

---

### RISCO 3: Múltiplas fontes = múltiplas verdades
**Tipo:** LATENTE → CRÍTICA ao implementar Phase 3  
**Cenário:**
```
Webhook atualiza plan_id = PRO
handlers/bot.py lê planosAtivos = ["secretaria"] (cache antigo)
→ Não reconhece upgrade
```

**Mitigation:** Phase 3 — motor de autorização centralizado

---

### RISCO 4: Máquina de estado desacoplada de flag
**Tipo:** LATENTE  
**Cenário:**
```
Assinatura State = CANCELADA (máquina de estado)
pagamentoAtivo = true (flag)

Scheduler lê flag, executa rotina
→ Envia resumo para cancelado
```

**Mitigation:** Phase 2 — integrar estado com flag

---

## ✅ VALIDAÇÃO: QUAL CAMPO HOJE EFETIVAMENTE LIBERA ACESSO?

**Resposta: `pagamentoAtivo` (booleano simples)**

```python
# handlers/gpt_text_handler.py:91
if not cliente.get("pagamentoAtivo", False):
    return False  # ← BLOQUEIA
    
# Se true, continua
# planosAtivos verificado depois, mas MUITO superficialmente
```

**Implicação:** Sistema atual é binário:
- `pagamentoAtivo=false` → Bloqueia tudo
- `pagamentoAtivo=true` → Permite tudo

Não há diferença entre planos, features ou limites.

---

## ✅ VALIDAÇÃO: HÁ MAIS DE UMA FONTE DE VERDADE?

**Resposta: SIM. Três simultâneas:**

1. `pagamentoAtivo` (decisão atual)
2. `planosAtivos` (histórico local)
3. `plan_id` (histórico de eventos)

Nenhuma é responsável por sincronizar com as outras.

---

## ✅ VALIDAÇÃO: HÁ DIVERGÊNCIA POSSÍVEL?

**Resposta: SIM. Exemplos reais:**

| Caso | Causa | Impacto |
|------|-------|--------|
| `planosAtivos=["secretaria"]` + `plan_id=STUDIO` | Webhook recebido, campo não atualizado | Cliente não vê upgrade |
| `pagamentoAtivo=false` + `plan_id=ATIVO` | Estado máquina avançou, flag não | Cliente bloqueado mas pago |
| `pagamentoAtivo=true` + sem plan_id | Cliente novo sem contrato | Cliente usa recursos |

---

## ✅ VALIDAÇÃO: HÁ FALLBACK QUE LIBERA ACESSO?

**Resposta: SIM. Dois:**

1. **firebase_service.py:57-58**
   ```python
   dados_padrao = {
       "pagamentoAtivo": True,  # ← Fallback: se não informado, true
       "planosAtivos": ["secretaria"]  # ← Fallback: se não informado, secretaria
   }
   ```

2. **gpt_service.py:156**
   ```python
   if not cliente.get("planosAtivos"):
       cliente["planosAtivos"] = ["secretaria"]  # ← Se vazio, atribui
   ```

**Implicação:** Ausência de campo = permissão automática

---

## ✅ VALIDAÇÃO: HÁ DEFAULT QUE ATRIBUI PLANO IMPLICITAMENTE?

**Resposta: SIM.**

| Local | Código | Risco |
|-------|--------|-------|
| firebase_service.py:58 | `"planosAtivos": ["secretaria"]` | Default hardcoded |
| gpt_service.py:156 | `= ["secretaria"]` | Fallback silencioso |
| firebase_service.py:57 | `"pagamentoAtivo": True` | Sempre liberado |

**Problema:** Não há diferença entre novo cliente legítimo e cliente sem assinatura.

---

## 🔐 VALIDAÇÃO MULTI-TENANT

Verificando se fontes de verdade respeitam tenant isolation:

| Fonte | Escopo | Tenant_Aware | Risco |
|-------|--------|--------------|-------|
| plan_id (eventos) | Por agregado | ✅ SIM | Baixo |
| planosAtivos | Por user_id (Firestore) | ❓ SIM (doc key é user_id) | **MÉDIO** |
| pagamentoAtivo | Por user_id (Firestore) | ❓ SIM (doc key é user_id) | **MÉDIO** |

**Nota:** user_id é global, não isolado por tenant.

**Risco:** Se dois tenants compartilham user_id, pode haver leitura cruzada.

**Status:** Não confirmado se isso acontece, mas arquitetura não garante isolamento.

---

## 📋 DECISÕES CRÍTICAS PARA PHASE 2

```
[ ] Remover defaults hardcoded de firebase_service.py
    Motivo: Atribuem valores sem validação
    
[ ] Criar assinatura como fonte única em:
    Tenants/{tenant_id}/Assinatura/Atual
    
[ ] Integrar estado da máquina com flag booleano
    Motivo: Atualmente desacoplados
    
[ ] Definir semântica clara de pagamentoAtivo
    (ou substituir por subscription_status)
    
[ ] Mapear todos os pontos que ESCREVEM em planos/pagamento
    (handlers/bot.py:237 não está totalmente documentado)
    
[ ] Criar protocolo de sincronização webhook → planosAtivos
    (atualmente manual e não confiável)
```

---

## ✅ CRITÉRIO DE ACEITE — FONTES DE VERDADE

- [x] Três fontes identificadas
- [x] Divergência documentada
- [x] Riscos mapeados
- [x] Defaults encontrados
- [x] Fallbacks documentados
- [x] Multi-tenant revisado
- [x] Decisões críticas para Phase 2 listadas
- [ ] Nenhuma alteração de código realizada

**Status:** ✅ VÁLIDO PARA PROSSEGUIR

