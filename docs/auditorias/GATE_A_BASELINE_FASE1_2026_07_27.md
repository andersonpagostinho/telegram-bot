# GATE A — FASE 1 BASELINE

**Data:** 2026-07-27  
**Etapa:** Após correção de imports  
**Status:** Executável mas com 5 falhas de estrutura  

---

## ✅ CORREÇÕES REALIZADAS

### Importação de AggregateSnapshot

| Arquivo | Linha | Import Anterior | Import Corrigido |
|---------|-------|-----------------|-----------------|
| `repositories/commercial_aggregate_repository.py` | 6 | `from services.billing_state_machines` | `from services.billing_domain_service` |
| `repositories/in_memory/in_memory_repositories.py` | 19 | `from services.billing_state_machines` | `from services.billing_domain_service` |
| `services/billing_application_service.py` | 14 | `from services.billing_state_machines` | Consolidado em `from services.billing_domain_service` |
| `tests/comercial/test_gate_a_in_memory.py` | 21 | `from services.billing_state_machines` | Consolidado em `from services.billing_domain_service` |

### Import Adicional: Optional

| Arquivo | Problema | Solução |
|---------|----------|----------|
| `repositories/commercial_audit_repository.py` | Faltava `Optional` | Adicionado em `from typing` |

---

## 📊 RESULTADO DE TESTES — BASELINE

```
Platform: win32 – Python 3.12.9, pytest-9.1.1, pluggy-1.6.0
Coletados: 25 testes
Executados: 25
PASS: 20 ✅
FAIL: 5 ❌
ERROR: 0
SKIP: 0
XFAIL: 0
XPASS: 0
Warnings: 30 (datetime.utcnow deprecated)
Duração: 0.54s
```

---

## 🔴 FALHAS (5 Testes)

### FALHA 1-5: TypeError em AggregateSnapshot

**Testes Afetados:**
1. `TestAggregateRepository::test_save_e_load`
2. `TestAggregateRepository::test_save_version_conflict`
3. `TestAggregateRepository::test_cross_tenant_isolation`
4. `TestAggregateRepository::test_tenant_id_vazio`
5. `TestUnitOfWork::test_transacao_commit`

**Erro:**
```python
TypeError: AggregateSnapshot.__init__() got an unexpected keyword argument 'aggregate_id'
```

**Root Cause:**

A classe `AggregateSnapshot` em `services/billing_domain_service.py` contém APENAS:

```python
class AggregateSnapshot:
    trial: TrialSnapshot
    assinatura: AssinaturaSnapshot
    pagamento: PagamentoSnapshot
    acesso: AcessoSnapshot
    retencao: RetencaoSnapshot
    timestamp: datetime
```

Não contém:
- ❌ `aggregate_id`
- ❌ `tenant_id`
- ❌ `version`
- ❌ `created_at`
- ❌ `updated_at`
- ❌ `lead_id` (pré-tenant)
- ❌ `subscription_id`
- ❌ `plan_id`
- ❌ `period_start/end`

**Problema Estrutural:**

O código esperava uma classe `AggregateSnapshot` que agrega TODOS os dados de negócio (identidade + estado + metadados). A classe real em `billing_domain_service.py` contém APENAS o estado das máquinas.

**Impacto:**

- Repositórios não podem persistir identidade (aggregate_id, tenant_id)
- Versionamento não pode ser implementado
- Referências de subscription não podem ser armazenadas
- Qualquer teste que crie AggregateSnapshot falha

---

## ✅ TESTES PASSAR (20)

### Grupo: TestAggregateRepository (Parcial)

```
✅ test_load_inexistente
❌ test_save_e_load (TypeError)
❌ test_save_version_conflict (TypeError)
❌ test_cross_tenant_isolation (TypeError)
❌ test_tenant_id_vazio (TypeError)
```

**Taxa:** 1/5 (20%)

### Grupo: TestProcessedEventRepository

```
✅ test_check_and_load_novo
✅ test_mark_processing
✅ test_mark_processed
✅ test_replay_idempotente
✅ test_mark_failed_retryable
✅ test_cross_tenant_isolation
```

**Taxa:** 6/6 (100%)

### Grupo: TestAuditRepository

```
✅ test_record_auditoria
✅ test_auditoria_append_only
✅ test_get_by_tenant
```

**Taxa:** 3/3 (100%)

### Grupo: TestOutboxRepository

```
✅ test_save_outbox
✅ test_nao_duplica_items_replay
✅ test_save_batch
✅ test_get_pending
```

**Taxa:** 4/4 (100%)

### Grupo: TestUnitOfWork

```
❌ test_transacao_commit (TypeError)
✅ test_transacao_rollback
```

**Taxa:** 1/2 (50%)

### Grupo: TestBillingApplicationService

```
✅ test_validacao_envelope_falha_sem_correlation_id
✅ test_validacao_envelope_falha_sem_tenant_id
✅ test_evento_novo_sucesso
✅ test_replay_idempotente
✅ test_isolamento_multi_tenant
```

**Taxa:** 5/5 (100%)

---

## 🔧 AÇÃO NECESSÁRIA

**Decisão de Design:**

Criar classe `CommercialAggregateSnapshot` (ou nome equivalente) que:

1. Encapsula IDENTIDADE do agregado
   - aggregate_id (UUID)
   - tenant_id (obrigatório)
   - version (inteiro sequencial)
   - lead_id (opcional, pré-tenant)

2. Encapsula ESTADO das máquinas
   - Reutiliza `AggregateSnapshot` de `billing_domain_service`
   - Acessa campos: trial, assinatura, pagamento, acesso, retencao

3. Encapsula REFERÊNCIAS de negócio
   - subscription_id
   - plan_id

4. Encapsula PERÍODOS
   - period_start
   - period_end

5. Encapsula METADADOS
   - created_at
   - updated_at (ou deixar vazio em Fase 3)

**Opções:**

### Opção A: Wrapper em BillingDomainService (Preferida)

```python
@dataclass(frozen=True)
class CommercialAggregate:
    """Agregado completo com identidade + estado + metadados."""
    aggregate_id: str
    tenant_id: str
    version: int
    snapshot: AggregateSnapshot  # Estado das máquinas
    subscription_id: Optional[str] = None
    plan_id: Optional[str] = None
    lead_id: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    created_at: datetime = field(default_factory=...)
```

**Vantagem:** Reutiliza `AggregateSnapshot`, isolamento claro entre identidade e estado

### Opção B: Estender AggregateSnapshot

```python
@dataclass(frozen=True)
class AggregateSnapshot:
    # Identidade
    aggregate_id: str
    tenant_id: str
    version: int
    
    # Estado (snapshots das máquinas)
    trial: TrialSnapshot
    ...
    
    # Metadados
    created_at: datetime
```

**Vantagem:** Simples, menos classes

**Desvantagem:** Mistura responsabilidades

---

## 📋 PRÓXIMOS PASSOS

1. **Decidir:** Opção A (wrapper) ou Opção B (estender)
2. **Implementar:** Classe nova em `services/billing_domain_service.py` ou arquivo novo
3. **Atualizar:** Repositórios e testes para usar a nova classe
4. **Re-executar:** pytest para nova contagem

---

## 📊 RESUMO ANTES/DEPOIS

| Métrica | Baseline | Meta |
|---------|----------|------|
| Testes Coletados | 25 | 25+ |
| Testes PASS | 20 | 25+ |
| Testes FAIL | 5 | 0 |
| Taxa de Sucesso | 80% | 100% |

---

**GATE_A_BASELINE_FASE1_2026_07_27.md**
