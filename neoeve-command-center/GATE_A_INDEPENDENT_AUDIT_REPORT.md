# GATE A — INDEPENDENT AUDIT REPORT

**Data:** 2026-11-25  
**Auditor:** Independent Review (READ-ONLY)  
**Status:** ⛔ CRITICAL ISSUES FOUND  

---

## A. VEREDITO FINAL

**⛔ REJECTED** — Implementação contém violações críticas de atomicidade e race conditions

---

## B. RESUMO EXECUTIVO

Gate A foi implementado com múltiplas violações de atomicidade e concorrência que reproduzem exatamente os problemas encontrados em P0.1:

1. ❌ **Duplos commits separados**
2. ❌ **Race condition em acquire_lease() com checkpoint não-existente**
3. ❌ **TOCTOU em validate_lease() e release_lease()**
4. ❌ **Falta de transação única** para operações críticas

---

## C. ARQUIVOS AUDITADOS

| Arquivo | Status |
|---------|--------|
| `database/models.py` | ✅ Correto |
| `app/services/projection_checkpoint_lease_service.py` | ⛔ Problemas críticos |
| `workers/projection_worker.py` | ⛔ Duplos commits |
| `tests/test_gate_a_reservation_recovery.py` | ⚠️ Testes sem PostgreSQL real |

---

## D. ACHADOS CRÍTICOS

### 🔴 CRÍTICO #1: Duplos Commits (Mesmo Padrão P0.1)

**Arquivo:** `projection_worker.py`  
**Linhas:** 158 (COMMIT 1) + 253 (COMMIT 2)  
**Evidência:**

```python
# Linha 158
self.db_session.commit()  # Persist lease reservation atomically

# [Muitas operações entre 158-253]

# Linha 253
self.db_session.commit()  # Finalize checkpoint
```

**Fluxo:**

```
consume_and_project():
  acquire_lease()
  commit() ← COMMIT 1 (linha 158)
  
  [Sem proteção transacional]
  checkpoint.status = PROCESSING
  _get_or_create_checkpoint()
  
  for event in events:
    project_event()  ← Sem lock após commit 1
  
  checkpoint.status = IDLE
  commit() ← COMMIT 2 (linha 253)
  
  release_lease()
```

**Problema:** Se exceção ocorre entre 158 e 253:
- Lease já foi commitada
- Projeções NÃO foram commitadas
- Inconsistência silenciosa

**Comparação com P0.1 Rejeitado:**
- P0.1 tinha `db.commit()` em linha 142 + 219
- Gate A tem `db.commit()` em linha 158 + 253
- **Exatamente o mesmo padrão que foi rejeitado**

---

### 🔴 CRÍTICO #2: Race Condition em acquire_lease()

**Arquivo:** `projection_checkpoint_lease_service.py`  
**Linhas:** 44-52  
**Evidência:**

```python
checkpoint = db.query(ProjectionCheckpoint).filter(
    ProjectionCheckpoint.consumer_id == consumer_id
).with_for_update().first()  # ← Lock aqui

if not checkpoint:
    # Create if not exists
    checkpoint = ProjectionCheckpoint(consumer_id=consumer_id)
    db.add(checkpoint)
    db.flush()  # ← Fora do lock!
```

**Cenário de Race Condition:**

```
Tempo T1:
  Worker A: query with_for_update() → não existe, retorna None
  
Tempo T2:
  Worker B: query with_for_update() → não existe, retorna None

Tempo T3:
  Worker A: cria checkpoint, flush()
  
Tempo T4:
  Worker B: cria checkpoint, flush()
  
Resultado: 
  UNIQUE violation
  ou dois checkpoints criados
  ou estado inconsistente
```

**Por quê?** Lock WITH_FOR_UPDATE não bloqueia quando resultado é None. Então dois workers podem criar simultaneamente.

---

### 🔴 CRÍTICO #3: TOCTOU em validate_lease()

**Arquivo:** `projection_checkpoint_lease_service.py`  
**Linhas:** 106-117  
**Evidência:**

```python
checkpoint = db.query(ProjectionCheckpoint).filter(
    ProjectionCheckpoint.consumer_id == consumer_id
).first()  # ← Sem lock

if not checkpoint:
    return False

# Check all three: worker_id, fencing_token, and lease not expired
is_owned = checkpoint.worker_id == worker_id
is_token_valid = checkpoint.fencing_token == fencing_token  # ← Verificado aqui
is_lease_valid = (...)

if not (is_owned and is_token_valid and is_lease_valid):
    return False

return True  # ← Worker A: validação passou
```

**TOCTOU (Time-Of-Check To Time-Of-Use):**

```
Tempo T1:
  Worker A: SELECT checkpoint → worker_id=A, token=10, valid lease
  Worker A: Validação passa (linha 124)

Tempo T2:
  Worker B: Adquire lease → token incrementa para 11
  
Tempo T3:
  Worker A: Tenta fazer operação crítica com token=10
  Resultado: Token errado, mas não foi validado novamente
```

**Falta de lock:** Sem WITH_FOR_UPDATE, estado pode mudar entre verificação e uso.

---

### 🔴 CRÍTICO #4: TOCTOU em release_lease()

**Arquivo:** `projection_checkpoint_lease_service.py`  
**Linhas:** 150-163  
**Evidência:**

```python
checkpoint = db.query(ProjectionCheckpoint).filter(
    ProjectionCheckpoint.consumer_id == consumer_id
).first()  # ← Sem lock

if not checkpoint:
    return False

# Only release if token matches
if checkpoint.fencing_token != fencing_token:  # ← Verificado aqui
    return False

checkpoint.lease_expires_at = utc_now()  # ← Modificado aqui, sem lock
db.flush()
```

**TOCTOU:**

```
Tempo T1:
  Worker A: SELECT checkpoint → fencing_token=10
  Worker A: Verificação passa

Tempo T2:
  Worker B: Adquire lease → fencing_token incrementa para 11
  
Tempo T3:
  Worker A: Modifica checkpoint.lease_expires_at
  Resultado: Worker A alterando checkpoint com token antigo
```

---

### 🟡 ALTO #5: Sem Atomicidade Real entre Lease e Projeções

**Arquivo:** `projection_worker.py`  
**Linhas:** 148-262  
**Problema:** 

Lease é commitada em linha 158. Projeções são commitadas em linha 253. Essas NÃO são uma transação única.

```
Worker A: Acquire lease, commit (158)
  ↓ [Lock é liberado aqui]
Worker B: Pode entrar e tentar adquirir (mas seria rejeitado por lease ativo)
  ↓ [Mas worker A não está mais in-transaction]
Worker A: Continua projeções (sem proteção)
```

Sem transação protegida, há janela onde:
- Lease foi adquirida
- Mas nenhuma lock está ativo
- E outras operações sobre checkpoint podem acontecer

---

## E. FENCING NÃO VALIDA TOCTOU

**Achado:** Mesmo com fencing token, há TOCTOU:

```
Worker A: Válida que tem token=10 ← Verificação
  [Sem lock]
Worker B: Incrementa token para 11 ← Outro worker muda estado
Worker A: Tenta usar token=10 ← TOCTOU: estado mudou desde verificação
```

Fencing token protege contra **reutilização de token**, mas não contra **TOCTOU em checkpoint modificado por outro worker durante o processamento**.

---

## F. RECOVERY INCOMPLETO

**Achado:** `find_expired_leases()` existe mas **NÃO é chamado por ninguém**

**Arquivo:** `projection_checkpoint_lease_service.py`  
**Linhas:** 182-204

```python
def find_expired_leases(self, ...):
    # Implementado
    pass
```

**Verificação:** Grep para ver quem chama

**Resultado:** Ninguém chama. Recovery é uma função isolada, não integrada ao Scheduler.

**Consequência:** Se worker cair:
1. Lease fica em "PROCESSING"
2. Scheduler NÃO recupera automaticamente
3. Checkpoint fica preso até timeout

---

## G. MULTI-TENANT NÃO VALIDADO

**Achado:** Isolamento por `consumer_id` apenas

```python
checkpoint = db.query(ProjectionCheckpoint).filter(
    ProjectionCheckpoint.consumer_id == consumer_id
).first()
```

**Falta:** Não há `tenant_id` em ProjectionCheckpoint

**Risco:** Se dois tenants usam mesmo `consumer_id`, há cruzamento potencial

---

## H. TESTES

### Status dos Testes:

| Teste | Tipo | Validação |
|-------|------|-----------|
| `test_lease_acquisition_simple` | Unitário | ⚠️ Sem mock |
| `test_lease_acquisition_concurrent_rejection` | Unitário | ⚠️ Simulado, não concorrente real |
| `test_lease_expiration_and_takeover` | Unitário | ⚠️ Fake timestamp |
| `test_lease_validation` | Unitário | ⚠️ Sem concorrência |
| `test_fencing_token_prevents_old_worker` | Unitário | ⚠️ Sem TOCTOU |
| `test_lease_release` | Unitário | ⚠️ Sem concorrência |
| `test_lease_release_wrong_token` | Unitário | ⚠️ Simulado |
| `test_lease_multi_tenant_isolation` | Unitário | ⚠️ Sem tenant_id real |

**Problema:** Nenhum teste com:
- ✅ PostgreSQL real
- ✅ Concorrência real (2 threads/workers)
- ✅ Integração real com ProjectionWorker
- ✅ TOCTOU verificação
- ✅ Falha durante commit

---

## I. LACUNAS

1. ❌ Sem transação única de ponta a ponta
2. ❌ Duplos commits (mesmo padrão P0.1 rejeitado)
3. ❌ Sem lock em validate_lease()
4. ❌ Sem lock em release_lease()
5. ❌ Race condition em acquire_lease() se checkpoint não existe
6. ❌ TOCTOU entre verificação e uso
7. ❌ Recovery não integrado ao Scheduler
8. ❌ Multi-tenant não implementado (só consumer_id)
9. ❌ Testes sem concorrência real
10. ❌ Nenhum teste PostgreSQL real

---

## J. VEREDITO

### ⛔ REJECTED

**Motivos:**

1. **Duplos commits** — Mesmo padrão de P0.1 que foi rejeitado
2. **Race conditions** — acquire_lease(), validate_lease(), release_lease()
3. **TOCTOU** — Sem locks apropriados
4. **Sem atomicidade real** — Lease e projeções em transações separadas
5. **Recovery incompleto** — Função existe mas não integrada
6. **Testes inadequados** — Nenhum com concorrência real

---

## K. CONCLUSÃO

Gate A foi implementado com a mesma arquitetura com falha que foi identificada e rejeitada em P0.1:

```
❌ Padrão Quebrado (Gate A):
  commit() lease
  [operações]
  commit() projections
  
❌ Padrão Quebrado (P0.1 Rejeitado):
  commit() checkpoint.status=PROCESSING
  [operações]
  commit() projections
```

**A diferença é só o que está sendo separado, não a natureza do problema.**

---

**Data:** 2026-11-25  
**Classificação:** REJECTED  
**Motivo Principal:** Duplos commits + Race conditions + TOCTOU  
**Recomendação:** Reimplementar com transação única de ponta a ponta, usando locks apropriados
