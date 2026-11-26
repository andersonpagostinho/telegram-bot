# GATE A — TECHNICAL PLAN

**Data:** 2026-11-25  
**Escopo:** Reserva Segura + Lease + Fencing + Recovery para ProjectionWorker  

---

## A. AUDITORIA FINDINGS

### Achados Positivos

1. **RecoveryService já existe** (`backend/app/services/recovery_service.py`)
   - Lease management implementado
   - Fencing tokens implementados
   - Worker ID suportado
   - Multi-tenant support
   - FOR UPDATE lock para atomicidade

2. **Execution model tem suporte a lease** (database/models.py)
   - lease_expires_at
   - worker_id
   - fencing_token

3. **Scheduler já existe** (`app/core/scheduler.py`)
   - Recovery chamado via `_recover_expired_events()`
   - Intervalo configurável (10s)

### Achados Negativos

1. **ProjectionCheckpoint não tem lease fields**
   - Sem worker_id
   - Sem lease_expires_at
   - Sem fencing_token

2. **ProjectionWorker não usa RecoveryService**
   - Implementa seu próprio `recover_stuck_events()` mas não é chamado

3. **Checkpoint.status não tem proteção de concorrência**
   - Sem row lock durante atualização
   - Sem validação de worker_id

---

## B. ESTRATÉGIA

**Reutilizar:** RecoveryService (já funciona para Execution)

**Adaptar para:** ProjectionCheckpoint (adicionar lease fields + usar RecoveryService)

**Não duplicar:** Recovery logic, scheduler, lease management

---

## C. ARQUIVOS A MODIFICAR

| Arquivo | Mudança | Tipo |
|---------|---------|------|
| `database/models.py` | Adicionar worker_id, lease_expires_at, fencing_token ao ProjectionCheckpoint | Migration |
| `backend/workers/projection_worker.py` | Use RecoveryService.acquire_lease() em consume_and_project() | Code |
| `backend/workers/projection_worker.py` | Validar fencing_token antes de atualizar checkpoint | Code |
| `app/core/scheduler.py` | Chamar RecoveryService para recover ProjectionCheckpoint | Code |
| `backend/tests/test_p0_1_gate_a_reservation.py` | Testes de concorrência | Tests |

---

## D. MIGRATION NECESSÁRIA

```sql
ALTER TABLE projection_checkpoints
ADD COLUMN worker_id VARCHAR(64);
ADD COLUMN lease_expires_at TIMESTAMP(6);
ADD COLUMN fencing_token BIGINT;
```

---

## E. MECANISMO DE RESERVA

**Lock:** FOR UPDATE + atomic update  
**Lease:** 300 segundos (configurável)  
**Token:** Auto-increment ou timestamp  
**Validation:** Fencing token antes de atualizar  

---

## F. TESTES PREVISTOS

1. ✅ Reserva simples
2. ✅ Concorrência (dois workers)
3. ✅ Lease expirada + recovery
4. ✅ Fencing token validation
5. ✅ Worker restart
6. ✅ Multi-tenant isolation
7. ✅ Scheduler recovery

---

## G. CRONOGRAMA

1. ⏳ Executar auditoria completa
2. ⏳ Criar migration
3. ⏳ Integrar RecoveryService em ProjectionWorker
4. ⏳ Implementar validação de fencing token
5. ⏳ Implementar recovery no Scheduler
6. ⏳ Escrever testes
7. ⏳ Executar testes
8. ⏳ Criar relatório

---

**Status:** Pronto para Implementação  
**Risco:** Baixo (reutilizar RecoveryService existente)  
**Complexidade:** Média (integração com código existente)
