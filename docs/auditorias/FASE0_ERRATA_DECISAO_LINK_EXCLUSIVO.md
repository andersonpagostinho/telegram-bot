# FASE 0 — ERRATA: DECISÃO DE PRODUTO PÓS-AUDITORIA

**Data:** 2026-07-29  
**Tipo:** CORREÇÃO OBRIGATÓRIA  
**Impacto:** Altera contrato de entrada da FASE 1  
**Status:** ✅ ERRATA FORMAL REGISTRADA

---

## 🎯 DECISÃO DE PRODUTO

Após conclusão da FASE 0, foi tomada decisão que altera o contrato comercial:

### ❌ REMOVIDO

**Número Dedicado por Plano não existirá.**

```
ANTES (contrato anterior):
Solo: 0 números
Solo Pro: 1 número dedicado
Studio: 1 número dedicado
Salão: 1 número dedicado
Pro: 1 número dedicado

DEPOIS (contrato corrigido):
Solo: —
Solo Pro: —
Studio: —
Salão: —
Pro: —

(Nenhum plano controla canal de entrada)
```

### ✅ MANTIDO E GENERALIZADO

**Link Exclusivo em Todos os Planos**

```
Todos os tenants (independente de plano) possuem:
EXCLUSIVE_EVE_LINK

O link não é limite comercial.
O link não diferencia upgrade/downgrade.
O link é infraestrutura base.
```

---

## 🏗️ MODELO ARQUITETURAL

### Canal de Entrada
```
usuário acessa link exclusivo da Eve
    ↓
token/slug do link é validado deterministicamente
    ↓
tenant_id é resolvido
    ↓
actor_id é identificado pelo canal
    ↓
papel do ator (dono/profissional/cliente) é consultado
    ↓
roteador decide domínio
```

### O Que NÃO Pertence a Plano
```
✗ Número telefônico dedicado
✗ Nome do salão no canal
✗ Múltiplos links por plano
✗ Provisioning de número
✗ Limite de canais por plano
```

### O Que PERTENCE ao Catálogo de Plano
```
✓ EXCLUSIVE_EVE_LINK (em todos)
✓ Identificação determinística de tenant
✓ Isolamento multi-tenant
```

---

## 📋 MATRIZ OFICIAL CORRIGIDA

### SOLO
**Limites (2):**
- PROFESSIONALS: 1
- CALENDARS: 1

**Features (8):**
- AUTOMATIC_BOOKING
- AUTOMATIC_CONFIRMATION
- MORNING_REMINDER
- REMINDER_30_MINUTES
- AUTOMATIC_WAITLIST
- REALTIME_AGENDA
- **EXCLUSIVE_EVE_LINK** ← TODO PLANO TEM
- WHATSAPP_SUPPORT

---

### SOLO_PRO
**Limites (2):**
- PROFESSIONALS: 1
- CALENDARS: 1

**Features (11):**
- (todos do Solo)
- CLIENT_REACTIVATION
- PREFERRED_TIME_SUGGESTIONS
- PRIORITY_SUPPORT

---

### STUDIO
**Limites (2):**
- PROFESSIONALS: 3
- CALENDARS: 3

**Features (12):**
- (todos do Solo Pro)
- ASSISTED_ONBOARDING

---

### SALAO
**Limites (2):**
- PROFESSIONALS: 6
- CALENDARS: 6

**Features (13):**
- (todos do Studio)
- OCCUPANCY_REPORTS

---

### PRO
**Limites (2):**
- PROFESSIONALS: 10
- CALENDARS: 10

**Features (14):**
- (todos do Salão)
- DEDICATED_PRIORITY_SUPPORT

---

## 📊 CONTAGEM FINAL CORRIGIDA

```
Planos: 5
Features: 14 (não 15)
Limites: 2 (não 3)

Removido:
✗ DEDICATED_NUMBER (não é feature de plano)
✗ DEDICATED_NUMBERS (não é limite de plano)
✗ DEDICATED_LINKS (não existe)
✗ PREMIUM_LINKS (não existe)
✗ MAX_DEDICATED_NUMBERS (não é limite)

Mantido:
✓ EXCLUSIVE_EVE_LINK (em todos os planos)
✓ PROFESSIONALS (limite em todos)
✓ CALENDARS (limite em todos)
```

---

## 🔄 FEATURES CANÔNICAS (14)

```python
class PlanFeature(str, Enum):
    # Base (todos os planos)
    AUTOMATIC_BOOKING = "AUTOMATIC_BOOKING"
    AUTOMATIC_CONFIRMATION = "AUTOMATIC_CONFIRMATION"
    MORNING_REMINDER = "MORNING_REMINDER"
    REMINDER_30_MINUTES = "REMINDER_30_MINUTES"
    AUTOMATIC_WAITLIST = "AUTOMATIC_WAITLIST"
    REALTIME_AGENDA = "REALTIME_AGENDA"
    EXCLUSIVE_EVE_LINK = "EXCLUSIVE_EVE_LINK"  # ← TODO PLANO
    WHATSAPP_SUPPORT = "WHATSAPP_SUPPORT"
    
    # Solo Pro+
    CLIENT_REACTIVATION = "CLIENT_REACTIVATION"
    PREFERRED_TIME_SUGGESTIONS = "PREFERRED_TIME_SUGGESTIONS"
    PRIORITY_SUPPORT = "PRIORITY_SUPPORT"
    
    # Studio+
    ASSISTED_ONBOARDING = "ASSISTED_ONBOARDING"
    
    # Salão+
    OCCUPANCY_REPORTS = "OCCUPANCY_REPORTS"
    
    # Pro
    DEDICATED_PRIORITY_SUPPORT = "DEDICATED_PRIORITY_SUPPORT"
```

---

## 🔒 LIMITES CANÔNICOS (2)

```python
class PlanLimit(str, Enum):
    PROFESSIONALS = "PROFESSIONALS"
    CALENDARS = "CALENDARS"
    
    # NÃO CONTERÁ:
    # DEDICATED_NUMBERS
    # MAX_DEDICATED_NUMBERS
    # PREMIUM_LINKS
    # MAX_LINKS_BY_PLAN
```

---

## 🗑️ O QUE SERÁ DESCARTADO

### Referências Legadas a NÃO Integrar ao Catálogo da Phase 1

Se encontrar no código legado:
- `dedicated_number`
- `dedicated_numbers`
- `premium_channel`
- `channel_by_plan`
- `provisioning_number`
- `custom_link_by_plan`

**Ação:** Apenas documentar como arquitetura descartada. NÃO integrar ao novo catálogo.

---

## 🚀 COMPONENTES ARQUITETURAIS FUTUROS (Fora do Controle de Plano)

Esses NÃO são features de plano, pois todos os planos possuem o link:

```
resolve_link_exclusivo()
    → token/slug → tenant_id

validar_link()
    → token ativo/revogado
    → tenant autorizado

revogar_link()
    → invalidar token
    → manter histórico

rotacionar_token()
    → segurança
    → sem interrupção

proteger_isolamento_multitenant()
    → actor de A não usa contexto de B
    → cache separado por tenant
    → logs registram tenant_id
```

**Responsabilidade:** Phase 3+ (motor de autorização), não Phase 1 (catálogo).

---

## 📝 IMPACTO NAS FASES POSTERIORES

### PHASE 3 — Motor de Autorização
```
Não terá:
✗ authorize_feature(..., "DEDICATED_NUMBER")

Terá:
✓ authorize_feature(..., "EXCLUSIVE_EVE_LINK") para todos
✓ Validação determinística de tenant_id via link
```

### PHASE 4 — Limites Transacionais
```
Controlará apenas:
✓ PROFESSIONALS (1/1/3/6/10)
✓ CALENDARS (1/1/3/6/10)

Não controlará:
✗ DEDICATED_NUMBERS
✗ MAX_LINKS
```

### PHASE 5 — Guards nos Recursos
```
Remover guards planejados:
✗ "Solicitar número dedicado"
✗ "Provisionar número dedicado"
✗ "Limite de números"

Guards canônicos:
✓ "Criar profissional" (respeita PROFESSIONALS)
✓ "Criar agenda" (respeita CALENDARS)
✓ "Acessar relatório" (respeita OCCUPANCY_REPORTS)
✓ "Usar retenção" (respeita CLIENT_REACTIVATION)
```

### PHASE 6 — Upgrade/Downgrade
```
Quando tenant faz upgrade/downgrade:
✓ Plano muda
✓ Features mudam
✓ Limites mudam
✗ Link NÃO muda (é infraestrutura)
✗ Canal NÃO muda (é infraestrutura)
✗ Número NÃO muda (não existe)

Regra crítica:
Link permanece estável durante transição de plano.
Revogação só por decisão operacional/segurança.
```

### PHASE 7 — Migração
```
Dados legados de "número dedicado":
✗ NÃO transformar em entitlement
✗ NÃO migrar para novo catálogo
✓ Documentar como técnico legado
✓ Preservar se existir na infraestrutura atual
✓ Mas não vincular ao plano novo
```

---

## 📋 DOCUMENTOS DA FASE 0 A ATUALIZAR

### 1. FASE0_FECHAMENTO_E_GATE.md
**Seção a Adicionar:**
```
ERRATA PÓS-AUDITORIA:

Número dedicado por plano removido do contrato.
Todos os planos possuem link exclusivo.
Referências anteriores a número dedicado são legado.
Não orientam implementação de Phase 1.
```

### 2. FASE0_MAPA_GUARDS_FUTUROS.md
**Operações a Marcar como DESCARTADAS:**
```
OP-12: Solicitar número dedicado → DESCARTADA
OP-13: Provisionar número dedicado → DESCARTADA
OP-XX: Limite de números → DESCARTADA

Substituídas por:
OP-NEW-1: Resolver link exclusivo (futuro, fora Phase 1)
OP-NEW-2: Validar tenant via link (futuro, fora Phase 1)
OP-NEW-3: Revogar link (futuro, fora Phase 1)
```

### 3. FASE0_FONTES_VERDADE_PLANOS.md
**Seção a Adicionar:**
```
DECISÃO PÓS-AUDITORIA:

Link exclusivo não é fonte de verdade para plan_id.
Link resolve tenant_id apenas.
Plan_id é obtido sempre de assinatura do tenant.
Isolamento multi-tenant não muda.
```

---

## ✅ VALIDAÇÃO: CONTRATO CORRIGIDO

### Contagem Final
```
Planos: 5 ✓
Features: 14 ✓
Limites: 2 ✓
```

### Checklist de Remoção
```
[x] DEDICATED_NUMBER removido
[x] DEDICATED_NUMBERS removido
[x] PREMIUM_LINKS removido
[x] MAX_DEDICATED_NUMBERS removido
[x] Nenhum plano diferencia por número
[x] Nenhum plano diferencia por link
```

### Checklist de Manutenção
```
[x] EXCLUSIVE_EVE_LINK em SOLO
[x] EXCLUSIVE_EVE_LINK em SOLO_PRO
[x] EXCLUSIVE_EVE_LINK em STUDIO
[x] EXCLUSIVE_EVE_LINK em SALAO
[x] EXCLUSIVE_EVE_LINK em PRO
```

### Checklist de Sequência
```
[x] Phase 1: Apenas catálogo (não implementa link)
[x] Phase 3: Autorização centralizada (pode usar link)
[x] Phase 5+: Guards não mencionam dedicado
[x] Phase 6+: Upgrade não troca link
```

---

## 🎯 GATE DE CORREÇÃO

```
╔════════════════════════════════════════════════════════╗
║                                                        ║
║     ✅ ERRATA APROVADA — CONTRATO CORRIGIDO           ║
║                                                        ║
║  Número dedicado: REMOVIDO                            ║
║  Link exclusivo: MANTIDO EM TODOS                     ║
║  Features finais: 14                                  ║
║  Limites finais: 2                                    ║
║                                                        ║
║  ➡️  PHASE 1 PODE INICIAR COM CONTRATO CORRIGIDO      ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

---

## 📌 PRÓXIMOS PASSOS

1. ✅ **Errata registrada** (este documento)
2. ✅ **Documentos Phase 0 atualizados** (ver próximos)
3. ⏳ **Phase 1 usando contrato corrigido** (quando aprovado)

**Contrato anterior descartado.** Phase 1 usará apenas a versão corrigida.

---

**Errata Formal:** 2026-07-29  
**Status:** ✅ APROVADO PARA PHASE 1

