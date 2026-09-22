# CONTRATO DE PLANOS — PHASE 1 (VERSÃO CORRIGIDA)

**Data:** 2026-07-29  
**Versão:** 2.0 (Corrigida)  
**Validade:** Obrigatória para PHASE 1  
**Status:** ✅ APROVADO PARA IMPLEMENTAÇÃO

---

## 🎯 DECISÃO CRÍTICA

**Número dedicado por plano foi removido do contrato.**

Todos os planos possuem **EXCLUSIVE_EVE_LINK** como infraestrutura, não como diferencial comercial ou limite quantitativo.

---

## 📋 CINCO PLANOS CANÔNICOS

### SOLO

**Limites (2):**
```
PROFESSIONALS: 1
CALENDARS: 1
```

**Features (8):**
1. AUTOMATIC_BOOKING
2. AUTOMATIC_CONFIRMATION
3. MORNING_REMINDER
4. REMINDER_30_MINUTES
5. AUTOMATIC_WAITLIST
6. REALTIME_AGENDA
7. EXCLUSIVE_EVE_LINK
8. WHATSAPP_SUPPORT

**Não possui:**
- CLIENT_REACTIVATION
- PREFERRED_TIME_SUGGESTIONS
- OCCUPANCY_REPORTS
- ASSISTED_ONBOARDING
- PRIORITY_SUPPORT
- DEDICATED_PRIORITY_SUPPORT

---

### SOLO_PRO

**Limites (2):**
```
PROFESSIONALS: 1
CALENDARS: 1
```

**Features (11):**
1. AUTOMATIC_BOOKING
2. AUTOMATIC_CONFIRMATION
3. MORNING_REMINDER
4. REMINDER_30_MINUTES
5. AUTOMATIC_WAITLIST
6. REALTIME_AGENDA
7. EXCLUSIVE_EVE_LINK
8. WHATSAPP_SUPPORT
9. CLIENT_REACTIVATION
10. PREFERRED_TIME_SUGGESTIONS
11. PRIORITY_SUPPORT

**Não possui:**
- OCCUPANCY_REPORTS
- ASSISTED_ONBOARDING
- DEDICATED_PRIORITY_SUPPORT

---

### STUDIO

**Limites (2):**
```
PROFESSIONALS: 3
CALENDARS: 3
```

**Features (12):**
1. AUTOMATIC_BOOKING
2. AUTOMATIC_CONFIRMATION
3. MORNING_REMINDER
4. REMINDER_30_MINUTES
5. AUTOMATIC_WAITLIST
6. REALTIME_AGENDA
7. EXCLUSIVE_EVE_LINK
8. WHATSAPP_SUPPORT
9. CLIENT_REACTIVATION
10. PREFERRED_TIME_SUGGESTIONS
11. PRIORITY_SUPPORT
12. ASSISTED_ONBOARDING

**Não possui:**
- OCCUPANCY_REPORTS
- DEDICATED_PRIORITY_SUPPORT

---

### SALAO

**Limites (2):**
```
PROFESSIONALS: 6
CALENDARS: 6
```

**Features (13):**
1. AUTOMATIC_BOOKING
2. AUTOMATIC_CONFIRMATION
3. MORNING_REMINDER
4. REMINDER_30_MINUTES
5. AUTOMATIC_WAITLIST
6. REALTIME_AGENDA
7. EXCLUSIVE_EVE_LINK
8. WHATSAPP_SUPPORT
9. CLIENT_REACTIVATION
10. PREFERRED_TIME_SUGGESTIONS
11. PRIORITY_SUPPORT
12. ASSISTED_ONBOARDING
13. OCCUPANCY_REPORTS

**Não possui:**
- DEDICATED_PRIORITY_SUPPORT

---

### PRO

**Limites (2):**
```
PROFESSIONALS: 10
CALENDARS: 10
```

**Features (14):**
1. AUTOMATIC_BOOKING
2. AUTOMATIC_CONFIRMATION
3. MORNING_REMINDER
4. REMINDER_30_MINUTES
5. AUTOMATIC_WAITLIST
6. REALTIME_AGENDA
7. EXCLUSIVE_EVE_LINK
8. WHATSAPP_SUPPORT
9. CLIENT_REACTIVATION
10. PREFERRED_TIME_SUGGESTIONS
11. PRIORITY_SUPPORT
12. ASSISTED_ONBOARDING
13. OCCUPANCY_REPORTS
14. DEDICATED_PRIORITY_SUPPORT

---

## 🔒 LIMITES ÚNICOS (2 Total)

```python
class PlanLimit(str, Enum):
    PROFESSIONALS = "PROFESSIONALS"
    CALENDARS = "CALENDARS"
```

Este catálogo contém exatamente estes dois limites. Nenhum outro.

---

## ⭐ FEATURES CANÔNICAS (14)

```python
class PlanFeature(str, Enum):
    # Base — todos os planos
    AUTOMATIC_BOOKING = "AUTOMATIC_BOOKING"
    AUTOMATIC_CONFIRMATION = "AUTOMATIC_CONFIRMATION"
    MORNING_REMINDER = "MORNING_REMINDER"
    REMINDER_30_MINUTES = "REMINDER_30_MINUTES"
    AUTOMATIC_WAITLIST = "AUTOMATIC_WAITLIST"
    REALTIME_AGENDA = "REALTIME_AGENDA"
    EXCLUSIVE_EVE_LINK = "EXCLUSIVE_EVE_LINK"
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

**NÃO conterá:**
- DEDICATED_NUMBER
- PREMIUM_LINK
- CUSTOM_LINK
- MULTIPLE_LINKS

---

## 🌍 EXCLUSIVE_EVE_LINK

### O Que É
Um identificador único e determinístico que resolve um tenant específico.

### Presente Em
- ✅ SOLO
- ✅ SOLO_PRO
- ✅ STUDIO
- ✅ SALAO
- ✅ PRO

### O Que NÃO É
- ❌ Número telefônico dedicado
- ❌ Nome do salão no canal
- ❌ Limite quantitativo por plano
- ❌ Diferencial de upgrade
- ❌ Propriedade comercial do plano

### Responsabilidade
O catálogo da Phase 1 declara apenas que a feature existe.

A implementação real (resolução determinística, validação, revogação) será arquitetura futura (Phase 3+), fora do escopo de controle comercial de plano.

---

## 📊 MATRIZ DE HERANÇA

```
SOLO
├─ AUTOMATIC_BOOKING
├─ AUTOMATIC_CONFIRMATION
├─ MORNING_REMINDER
├─ REMINDER_30_MINUTES
├─ AUTOMATIC_WAITLIST
├─ REALTIME_AGENDA
├─ EXCLUSIVE_EVE_LINK
└─ WHATSAPP_SUPPORT

SOLO_PRO (herda tudo de SOLO, +)
├─ CLIENT_REACTIVATION
├─ PREFERRED_TIME_SUGGESTIONS
└─ PRIORITY_SUPPORT

STUDIO (herda tudo de SOLO_PRO, +)
└─ ASSISTED_ONBOARDING

SALAO (herda tudo de STUDIO, +)
└─ OCCUPANCY_REPORTS

PRO (herda tudo de SALAO, +)
└─ DEDICATED_PRIORITY_SUPPORT
```

---

## ✅ VALIDAÇÃO

### Contagem Final
- Planos: **5** ✓
- Features: **14** ✓
- Limites: **2** ✓

### Confirmações
- [x] Número dedicado removido
- [x] Todos possuem EXCLUSIVE_EVE_LINK
- [x] Link não é limite quantitativo
- [x] Link não diferencia upgrade/downgrade
- [x] Herança de features confirmada
- [x] Monotonicidade validada (Pro ⊇ Salão ⊇ Studio ⊇ Solo Pro ⊇ Solo)

---

## 🔐 POLÍTICA DE PLANO DESCONHECIDO

**Quando um tenant tem plan_id desconhecido:**

```
Falha fechada: BLOQUEADO

Ações permitidas: NENHUMA (exceto leitura de histórico)
Razão: Impossível resolver features e limites

Tratamento:
1. Log crítico: UNKNOWN_PLAN
2. Tentativa de carregar contrato versão anterior
3. Se falhar: bloquear até resolução operacional
4. Não liberar PRO como fallback
5. Não desabilitar silenciosamente
```

---

## ✅ ESCOPO DESTA VERSÃO

Este catálogo define:
- Exatamente 5 planos
- Exatamente 14 features
- Exatamente 2 limites

Conceitos descartados de versões anteriores são documentados apenas na errata formal (FASE0_ERRATA_DECISAO_LINK_EXCLUSIVO.md), não no contrato ativo.

---

## 🏗️ LOCALIZAÇÃO NO CÓDIGO

**Arquivo onde será implementado:**

```
domain/plan_catalog.py
```

**Estrutura esperada:**

```python
class PlanCatalog:
    VERSION = 1  # Versionado
    
    PLANS = {
        "SOLO": {
            "limits": {...},
            "features": {...}
        },
        # ... etc
    }
    
    @staticmethod
    def get_plan(plan_id):
        # Retorna definição versionada
        pass
    
    @staticmethod
    def validate():
        # Valida catálogo no init
        pass
```

---

## 🔗 DEPENDÊNCIAS EXISTENTES

Reutilizar:

- ✓ `domain/commercial_events.py` (plan_id já definido)
- ✓ `services/billing_state_machines.py` (máquinas de estado)
- ✓ `services/billing_domain_service.py` (orquestração)
- ✓ `services/billing_application_service.py` (agregado)

NÃO duplicar:

- ✗ `utils/plan_utils.py` (vai mudar em Phase 3)
- ✗ `services/firebase_service.py` (vai mudar em Phase 2)
- ✗ `planosAtivos` (vai ser descontinuado em Phase 7)

---

## 🎯 GATE DE APROVAÇÃO PHASE 1

**Critérios de Aprovação — TODOS ATENDIDOS:**

✅ PASS — 5 planos definidos (SOLO, SOLO_PRO, STUDIO, SALAO, PRO)  
✅ PASS — 14 features definidas (lista completa abaixo verificada)  
✅ PASS — 2 limites definidos (PROFESSIONALS, CALENDARS)  
✅ PASS — EXCLUSIVE_EVE_LINK presente em todos os 5 planos  
✅ PASS — Solo possui EXCLUSIVE_EVE_LINK  
✅ PASS — Nenhum plano diferencia acesso por número  
✅ PASS — Upgrade não implica troca de canal/link  
✅ PASS — Catálogo contém exatamente 2 limites  
✅ PASS — Nenhuma referência ativa a conceitos descartados  
✅ PASS — Catálogo versionado (VERSION = 1)  
✅ PASS — Herança de features validada (monotonicidade confirmada)  
✅ PASS — Nenhum arquivo Python foi modificado

---

## ✅ PRONTO PARA PHASE 1

**Este contrato é a única fonte de verdade para Phase 1.**

A implementação deve usar exclusivamente este documento.

Conceitos descartados são documentados apenas em FASE0_ERRATA_DECISAO_LINK_EXCLUSIVO.md.

---

**Versão:** 2.0 (Corrigida)  
**Data:** 2026-07-29  
**Status:** ✅ APROVADO PARA IMPLEMENTAÇÃO

