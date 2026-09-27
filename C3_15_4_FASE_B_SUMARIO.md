# C3.15.4 — FASE B: SUMÁRIO EXECUTIVO

**Data:** 2026-09-26  
**Status:** DESENHO CONCLUÍDO (Sem Implementação)  
**Próximo:** Fase C (aguarda aprovação)  

---

## DECISÕES PRINCIPAIS

### 1. Consolidação por Transaction Atômica
- ✅ Usar Firestore Transaction para atomicidade
- ✅ Um único vencedor define `dono_principal_actor_id`
- ✅ Segundo+ atores preservam o valor

### 2. Imutabilidade de `dono_principal_actor_id`
- ✅ Uma vez definido, NUNCA é sobrescrito
- ✅ Semanticamente: "primeiro ator a completar o onboarding"
- ✅ Determinístico, não baseado em timestamp

### 3. Idempotência Determinística
- ✅ Usar chave SHA256 armazenada no documento
- ✅ Webhook duplicado é seguro
- ✅ Retry de transaction é seguro
- ✅ Reutiliza mecanismo C3.15.3

### 4. Validação: Actor State vs Business Config
- ✅ **Novo:** `validar_actor_onboarding_completo()` — estado do ator
- ✅ **Novo:** `validar_negocio_configuracao_minima()` — estado do negócio
- ✅ Separação clara de responsabilidades

### 5. Consolidação não Destrutiva
- ✅ Legacy preservado (não deletado)
- ✅ Campos compartilhados mergeados, não sobrescritos
- ✅ Campos isolados permanecem no novo path

### 6. Fallback Seguro
- ✅ `validar_onboarding_minimo()` lê novo path → fallback legacy
- ✅ Ownership validation em ambos os casos
- ✅ Sem contaminação cross-actor

---

## INVARIANTES CRÍTICAS

```
1. dono_principal_actor_id é IMUTÁVEL
2. Ownership sempre validado
3. Tenant sempre validado
4. Legacy nunca é destruído
5. Isolamento mantido (sem contaminação)
6. Transaction garante atomicidade
7. Idempotência via chave determinística
```

---

## MUDANÇAS PREVISTAS (Fase C)

### Arquivos Alterados

| Arquivo | Mudanças | Linhas | Risco |
|---------|----------|--------|-------|
| services/onboarding_dono_service.py | marcar() → consolidar + ADD param | +50/- | MÉDIO |
| services/onboarding_service.py | validação → ADD actor_id | +10 | BAIXO |
| tests/test_c315_4_consolidacao.py | 16+ testes novos | +500 | N/A |

### Arquivos Não Alterados

```
✓ router/integracao_identidade_onboarding.py
✓ services/onboarding_isolado_schema.py
✓ services/firebase_service_async.py
```

---

## TESTES PREVISTOS (Fase C)

### Consolidação (Novos)
- C1-C6: Primeiro/segundo/concorrente/retry/webhook/transaction
- C7-C14: Validação/ownership/tenant/documento/mutabilidade
- C15: Legacy preservado

### Validação (Novos)
- V1-V4: Novo path/legacy/negócio/sem actor

### Regressão (Verificar)
- R1: C3.15.1 (10/10)
- R2: C3.15.2 (13/13)
- R3: C3.15.3 (16/16)

**Total Testes:** 20+

---

## RISCOS REMANESCENTES

| Risco | Mitigation |
|-------|-----------|
| Firestore transaction abort | Retry automático + idempotência |
| Timeout pós-commit | Idempotência detecta já consolidado |
| Webhook duplicado | Chave SHA256 detecta reprocessamento |
| Legacy corrompido | Preservar, nunca sobrescrever |

---

## ESCALA

- ✅ **O(1)** por operação (acesso direto por IDs)
- ✅ **Nenhuma query global** (sem varredura)
- ✅ **Transaction size:** 2 operações Firestore
- ✅ **Custo por consolidação:** 1 read + 1 write

---

## CONTRATO DE CONSOLIDAÇÃO

```python
async def consolidar_onboarding_completo(
    tenant_id: str,
    actor_id: str
) -> dict:
    """
    Consolida onboarding completo em Configuracao/negocio.
    
    Transaction garantida:
    - Primeiro a chegar define dono_principal_actor_id
    - Segundo preserva o valor existente
    - Idempotência via SHA256 key
    
    Returns:
    {
        "sucesso": bool,
        "consolidado": bool (True=primeiro, False=preservou),
        "dono_principal_actor_id": str,
        "timestamp_consolidacao": str
    }
    """
```

---

## MATRIZ LEGACY

```
Legacy do Mesmo Actor   → Fallback se novo não existe
Legacy de Outro Actor   → BLOQUEAR
Legacy sem Ownership    → Não assumir, usar novo
Novo Path Existe        → Novo tem prioridade
Ambos Existem           → Novo prevalece
Legacy Completo         → Preservar, não alterar
```

---

## SEPARAÇÃO SEMÂNTICA

```
ACTOR STATE                  BUSINESS CONFIGURATION
(Donos/{actor_id}/...)      (Configuracao/negocio)

onboarding_status           [consolidado_em]
onboarding_etapa_atual      [consolidado_por_actor_id]
onboarding_indice           [dono_principal_actor_id] ← IMUTÁVEL
_ultimo_campo_idempotencia  [campos de negócio...]

Isolado por ator            Compartilhado pelo tenant
```

---

## CHECKLIST DE APROVAÇÃO (FASE B)

- [x] Contrato de validar_onboarding_minimo() definido
- [x] Contrato de consolidar_onboarding_completo() definido
- [x] Dono principal formalizado (imutável)
- [x] Transaction boundary explícito
- [x] Idempotência determinística
- [x] Matriz legacy completa
- [x] Estratégia de migração documentada
- [x] Actor State ≠ Business Config
- [x] Callsites auditados
- [x] Testes planejados (20+)
- [x] Invariantes documentadas
- [x] Escala validada (O(1))
- [x] Riscos identificados
- [x] Nenhuma implementação
- [x] Nenhuma alteração Firestore
- [x] Nenhum commit/push

---

## STATUS ATUAL

```
CÓDIGO ALTERADO:        NÃO ✅
FIRESTORE ALTERADO:     NÃO ✅
DADOS MIGRADOS:         NÃO ✅
COMMIT FEITO:           NÃO ✅
PUSH FEITO:             NÃO ✅

FASE A (Auditoria):     CONCLUÍDA ✅
FASE B (Desenho):       CONCLUÍDA ✅
FASE C (Implementação): PRONTA PARA INICIAR (aguarda aprovação)
```

---

## PRÓXIMO PASSO

**ESPERAR APROVAÇÃO EXPLÍCITA antes de iniciar Fase C.**

Documentos entregues:
1. `C3_15_4_FASE_A_AUDITORIA.md` — Auditoria completa
2. `C3_15_4_FASE_B_DESENHO.md` — Desenho detalhado
3. `C3_15_4_FASE_B_SUMARIO.md` — Este documento

---

**Concluído:** 2026-09-26  
**Autorizado para:** Fase C (Implementação)  
**Status:** Aguardando aprovação explícita  

