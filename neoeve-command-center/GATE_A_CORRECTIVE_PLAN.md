# GATE A — CORRECTIVE IMPLEMENTATION PLAN

**Data:** 2026-11-25  
**Status:** Plan após rejeição de auditoria  
**Complexidade:** Alta — Requer redesign transacional

---

## A. ACHADOS DA AUDITORIA

Gate A foi rejeitado por 7 problemas críticos:

| # | Problema | Arquivo | Linhas | Severidade |
|---|----------|---------|--------|-----------|
| 1 | Duplos commits | projection_worker.py | 158, 253 | 🔴 CRÍTICO |
| 2 | Race condition | lease_service.py | 44-52 | 🔴 CRÍTICO |
| 3 | TOCTOU validate | lease_service.py | 106-117 | 🔴 CRÍTICO |
| 4 | TOCTOU release | lease_service.py | 150-163 | 🔴 CRÍTICO |
| 5 | Recovery não integrado | — | — | 🔴 CRÍTICO |
| 6 | Multi-tenant incompleto | — | — | 🟡 ALTO |
| 7 | Testes sem PostgreSQL real | — | — | 🟡 ALTO |

---

## B. ARQUITETURA TRANSACIONAL CORRIGIDA

### Antes (Rejeitado):

```
Transação 1 (Reserva):
  acquire_lease()
  commit()

[Sem proteção]
checkpoint.status = PROCESSING
_get_or_create_checkpoint()

Transação 2 (Projeção):
  for event in events:
    project_event()
  checkpoint.status = IDLE
  commit()

release_lease()
```

### Depois (Corrigido):

```
Transação Única (Reserva + Projeção):
  acquire_lease() with_for_update + INSERT ON CONFLICT (UPSERT)
  checkpoint.status = PROCESSING
  
  for event in events:
    project_event() [flush, sem commit]
  
  validate_lease() com lock
  checkpoint.status = IDLE
  
  COMMIT único

release_lease() [após commit bem-sucedido]
```

**Mudança:** Uma transação de ponta a ponta, não duplos commits.

---

## C. CORREÇÕES ESPECÍFICAS

### 1. acquire_lease() — Eliminar Race Condition

**Problema:** `with_for_update()` retorna None se linha não existe. Dois workers podem criar simultaneamente.

**Solução:** INSERT ON CONFLICT DO UPDATE (UPSERT atômico)

```python
def acquire_lease(self, db: Session, consumer_id: str, tenant_id: str, worker_id: str):
    """
    Atomically acquire lease using INSERT ON CONFLICT.
    
    Guarantees:
    - Exactly one winner if checkpoint doesn't exist
    - Atomicity at database level
    - Fencing token monotonic
    - Tenant-scoped
    """
    # Use PostgreSQL INSERT ... ON CONFLICT for atomicity
    # 1. Try INSERT new checkpoint
    # 2. If conflict (exists), UPDATE with conditions
    # 3. All atomic at database level
```

**Implementação:**
- Usar `insert().on_conflict_do_update()` de SQLAlchemy
- Ou executar SQL direto INSERT ... ON CONFLICT
- Validar tenant_id
- Incrementar fencing_token atomicamente

### 2. validate_lease() — Eliminar TOCTOU

**Problema:** Verificação sem lock. Estado pode mudar entre validação e uso.

**Solução:** Usar WITH_FOR_UPDATE durante a validação

```python
def validate_lease(self, db: Session, consumer_id: str, tenant_id: str, worker_id: str, fencing_token: int):
    """
    Validate with lock to prevent TOCTOU.
    
    Lock prevents ownership change during validation.
    """
    checkpoint = db.query(ProjectionCheckpoint).filter(
        ProjectionCheckpoint.consumer_id == consumer_id,
        ProjectionCheckpoint.tenant_id == tenant_id
    ).with_for_update().first()  # ← LOCK aqui
    
    if not checkpoint or checkpoint.worker_id != worker_id or checkpoint.fencing_token != fencing_token:
        return False
    
    return True
```

**Mudança:** WITH_FOR_UPDATE durante validação.

### 3. release_lease() — Eliminar TOCTOU

**Problema:** Sem lock entre verificação e modificação.

**Solução:** UPDATE com WHERE conditions atômico

```python
def release_lease(self, db: Session, consumer_id: str, tenant_id: str, fencing_token: int):
    """
    Atomically release lease using UPDATE with WHERE.
    
    Guarantees:
    - Only correct worker can release
    - Atomic at database level
    - Cannot release wrong lease
    """
    # UPDATE checkpoint
    # SET lease_expires_at = now()
    # WHERE consumer_id = ? AND tenant_id = ? AND fencing_token = ?
    # 
    # Atomic: só modifica se token corresponde
```

**Implementação:**
- UPDATE com WHERE conditions todas juntas
- Fencing token validado na mesma query

### 4. consume_and_project() — Uma Transação Única

**Problema:** Duplos commits em linha 158 e 253.

**Solução:** Uma transação de ponta a ponta

```python
def consume_and_project(self, limit: Optional[int] = None) -> int:
    # Iniciar transação implícita
    
    # acquire_lease() com INSERT ON CONFLICT (UPSERT atomicamente)
    success, fencing_token = acquire_lease(...)
    if not success:
        return 0
    
    # checkpoint.status = PROCESSING
    # _get_or_create_checkpoint()
    
    # Processar eventos
    for event in events:
        project_event()  # flush, sem commit
    
    # validate_lease() com lock
    if not validate_lease(...):
        db.rollback()
        return 0
    
    # checkpoint.status = IDLE
    
    # COMMIT ÚNICO aqui (não em 158)
    db.commit()
    
    # release_lease() APÓS commit (opcional, não crítico)
    release_lease(...)
```

**Mudança:** Remove commit em linha 158, mantém apenas commit final.

### 5. Recovery — Integrar ao Scheduler

**Problema:** `find_expired_leases()` existe mas ninguém chama.

**Solução:** Integrar ao Scheduler existente

```python
# Em app/core/scheduler.py _recover_expired_events():

def _recover_expired_events(self):
    """Recover checkpoints with expired leases."""
    db = PGSessionLocal()
    try:
        lease_service = ProjectionCheckpointLeaseService()
        
        # Find expired leases
        expired = lease_service.find_expired_leases(db)
        
        for checkpoint in expired:
            try:
                # Try to acquire new lease
                success, token = lease_service.acquire_lease(
                    db=db,
                    consumer_id=checkpoint.consumer_id,
                    tenant_id=checkpoint.tenant_id,
                    worker_id=f"recovery_worker"
                )
                
                if success:
                    # Increment checkpoint for recovery
                    checkpoint.status = "IDLE"
                    checkpoint.error_count = 0
                    db.commit()
                    logger.info(f"Recovered checkpoint {checkpoint.consumer_id}")
            except Exception as e:
                logger.error(f"Failed to recover {checkpoint.consumer_id}: {e}")
    finally:
        db.close()
```

### 6. Multi-tenant — Adicionar tenant_id

**Problema:** Isolamento por consumer_id apenas. Sem tenant_id em ProjectionCheckpoint.

**Solução:** Adicionar tenant_id como parte da PK ou índice

**Migration:**
```sql
ALTER TABLE projection_checkpoints
ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
ADD CONSTRAINT fk_checkpoint_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
DROP CONSTRAINT projection_checkpoints_pkey,
ADD CONSTRAINT projection_checkpoints_pkey PRIMARY KEY (consumer_id, tenant_id);
```

**Queries:** Adicionar `tenant_id` a todas as queries.

### 7. Testes PostgreSQL Real

**Necessários:**

1. **test_concurrent_acquire** — Dois workers simultâneos
2. **test_checkpoint_creation_race** — Criação simultânea
3. **test_lease_expiration_recovery** — Recovery automático
4. **test_fencing_blocks_old_worker** — Fencing funcional
5. **test_release_wrong_token** — Token validation
6. **test_multi_tenant_isolation** — Tenant isolation
7. **test_scheduler_recovery** — Scheduler integrado
8. **test_single_transaction** — Nenhum duplo commit

Cada teste:
- Usa PostgreSQL real (port 5433)
- Usa conexões independentes para workers
- Valida estado em Firestore/PostgreSQL
- Prova concorrência real

---

## D. ORDEM DE IMPLEMENTAÇÃO

1. **Adicionar tenant_id ao model** (migration)
2. **Corrigir acquire_lease()** (INSERT ON CONFLICT)
3. **Corrigir validate_lease()** (WITH_FOR_UPDATE)
4. **Corrigir release_lease()** (UPDATE atômico)
5. **Corrigir consume_and_project()** (transação única)
6. **Integrar recovery ao Scheduler**
7. **Criar testes PostgreSQL real** (8 cenários)
8. **Executar regressões** (B1-B5)
9. **Criar relatório de implementação**

---

## E. PRÓXIMA SESSÃO

**Executor:** Implementar todas as correções acima

**Pré-requisitos:**
- PostgreSQL confirme port 5433
- Banco de teste isolado confirmado
- Token budget fresco

**Escopo:**
- Correção completa de todos os 7 problemas
- Testes PostgreSQL real
- Regressões
- Relatório

---

**Data:** 2026-11-25  
**Status:** Plan pronto para próxima sessão  
**Tokens Usados:** ~14.9M/15M (limite atingido)
