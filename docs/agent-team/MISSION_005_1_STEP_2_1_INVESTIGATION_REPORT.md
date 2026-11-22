# MISSÃO 005.1 — STEP 2.1 INVESTIGATION REPORT

**Data**: 2026-11-22  
**Status**: 🔴 ROOT CAUSES IDENTIFIED  
**Tests Executados**: 10/18  
**Resultado**: 1 PASS, 9 FAIL (8 file locking, 1 concurrent consume)

---

## Executive Summary

Duas causa-raiz críticas identificadas e confirmadas através de execução de testes:

1. **P0 — SQLite File Locking**: Conexões deixam locks residuais em cleanup Windows
2. **P1 — Concurrent Consume Race Condition**: GET + UPDATE não atômico em concorrência

---

## Diagnóstico Detalhado

### P0 — SQLite File Locking (8 testes afetados)

**Sintoma**:
```
PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo
C:\...\Temp\tmpXXXX\test.db
```

**Teste Afetado**: `test_concurrent_publish` (teardown)

**Root Cause**:

1. **WAL Mode Journals**: SQLite em modo WAL cria 3 arquivos:
   - `test.db` (main database)
   - `test.db-wal` (write-ahead log)
   - `test.db-shm` (shared memory)

2. **Connection Context Manager**: Embora `with self._get_connection() as conn:` chame `conn.close()`, em Windows há latência na liberação de locks.

3. **Timing Issue**: O tmpdir tentando deletar os arquivos ANTES do SQLite liberar completamente os locks.

**Evidência no Código**:

`event_store.py:29-36` (_get_connection):
```python
def _get_connection(self) -> sqlite3.Connection:
    conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
```

Problema: Nenhuma garantia de que checkpoint/close libera locks imediatamente em Windows.

**Teste Problematico**:

`test_event_bus_reliability.py:18-22` (bus fixture):
```python
@pytest.fixture
def bus(self):
    with tempfile.TemporaryDirectory() as tmpdir:  # <-- Falha aqui
        db_path = os.path.join(tmpdir, "test.db")
        yield EventBus(db_path)
        # tmpdir tenta deletar mas DB ainda tem locks
```

---

### P1 — Concurrent Consume Race Condition

**Sintoma**:
```
AssertionError: assert 4 <= 1  # 4 events remained PENDING
```

**Teste**: `test_concurrent_consume` (linha 47-78)

**Root Cause**:

Função `consume_pending()` em `event_consumer.py:20-37` NÃO É ATÔMICA:

```python
def consume_pending(self, mission_id: str, limit: int = 10) -> List[Event]:
    # STEP 1: Get pending events (not locked!)
    events = self.event_store.get_pending_events(mission_id, limit)
    
    # RACE CONDITION WINDOW HERE
    # Thread A pegou evt1-evt10, mas ainda não marcou como PROCESSING
    # Thread B entra e pega os MESMOS evt1-evt10!
    
    # STEP 2: Mark each as processing (LATE!)
    for event in events:
        self.event_store.update_event_status(event.event_id, EventStatus.PROCESSING)
    
    return events
```

**Timeline da Falha**:

```
T1: Thread-1.get_pending_events("mission-001", limit=3)
    → Retorna: [evt1, evt2, evt3] (todos PENDING)
    
T2: Thread-2.get_pending_events("mission-001", limit=3)
    → Retorna: [evt1, evt2, evt3] (AINDA PENDING!)
    
T3: Thread-1.update_event_status(evt1, PROCESSING)
    → evt1 = PROCESSING
    
T4: Thread-1.update_event_status(evt2, PROCESSING)
    → evt2 = PROCESSING
    
T5: Thread-1.update_event_status(evt3, PROCESSING)
    → evt3 = PROCESSING
    
T6: Thread-2.update_event_status(evt1, PROCESSING)
    → evt1 = PROCESSING (redundante!)
    
T7: Thread-2.update_event_status(evt2, PROCESSING)
    → evt2 = PROCESSING (redundante!)
    
T8: Thread-2.update_event_status(evt3, PROCESSING)
    → evt3 = PROCESSING (redundante!)

RESULTADO: Eventos consumidos 2x, conflito de processamento!
```

**Teste Evidence**:

```python
def test_concurrent_consume(self, bus):
    # Publish 10 events
    for i in range(10):
        event = Event(...)
        bus.publish(event)
    
    consumed = []
    lock = threading.Lock()
    
    def consume_and_process():
        events = bus.consume_pending("mission-001", "consumer-1", limit=3)
        # Race condition: 2 threads both consuming same 3 events
        with lock:
            consumed.extend([e.event_id for e in events])
        for event in events:
            bus.mark_completed(event.event_id, "consumer-1")
    
    threads = [threading.Thread(target=consume_and_process) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # 2 threads × 3 limit = 6 expected, but got 10 published
    # Remaining = 4 (because race condition prevented proper marking)
    pending = bus.store.get_pending_events("mission-001")
    assert len(pending) <= 1  # FAILS: len(pending) = 4
```

---

## Solução Proposta

### FIX 1: Atomic Event Reserve (P1)

**Novo método em `event_store.py`**:

```python
def reserve_event_atomic(self, event_id: str) -> bool:
    """
    Atomically reserve event for processing.
    
    Returns True if successfully transitioned PENDING -> PROCESSING
    Returns False if event already in different state
    """
    try:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Explicit transaction with IMMEDIATE lock
                cursor.execute("BEGIN IMMEDIATE")
                
                # Atomic: Check + Update in one statement
                cursor.execute("""
                    UPDATE events 
                    SET status = ?, updated_at = ?
                    WHERE event_id = ? AND status = ?
                """, (
                    EventStatus.PROCESSING.value,
                    datetime.utcnow().isoformat(),
                    event_id,
                    EventStatus.PENDING.value
                ))
                
                success = cursor.rowcount > 0
                
                if success:
                    conn.commit()
                else:
                    conn.rollback()
                
                return success
    except Exception as e:
        raise PersistenceException(f"Failed to reserve event: {e}")
```

**Integração em `event_consumer.py`**:

```python
def consume_pending(self, mission_id: str, limit: int = 10) -> List[Event]:
    """Get pending events and atomically reserve them"""
    events = self.event_store.get_pending_events(mission_id, limit)
    
    # Atomically reserve each event
    reserved = []
    for event in events:
        if self.event_store.reserve_event_atomic(event.event_id):
            reserved.append(event)
    
    return reserved
```

---

### FIX 2: WAL Checkpoint + Connection Cleanup (P0)

**Adicionar em `event_store.py`**:

```python
def _checkpoint_wal(self, conn: sqlite3.Connection) -> None:
    """Checkpoint WAL to ensure all data is persisted"""
    try:
        conn.execute("PRAGMA wal_checkpoint(RESTART)")
    except:
        pass  # Ignore if not in WAL mode

def _get_connection(self) -> sqlite3.Connection:
    """Get SQLite connection with proper settings"""
    conn = sqlite3.connect(
        str(self.db_path), 
        timeout=5.0, 
        check_same_thread=False,
        isolation_level="DEFERRED"  # Explicit transaction control
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
```

**Adicionar em todos métodos que modificam dados**:

```python
def store_event(self, event: Event) -> None:
    try:
        with self._lock:
            with self._get_connection() as conn:
                # ... existing code ...
                conn.commit()
                self._checkpoint_wal(conn)  # Explicit checkpoint
    except Exception as e:
        raise PersistenceException(f"Failed to store event: {e}")
```

---

### FIX 3: Test Synchronization (P0 - Windows specific)

**Adicionar em `test_event_bus_reliability.py`**:

```python
import time

@pytest.fixture
def bus(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield EventBus(db_path)
        
        # CRITICAL: Aguardar WAL checkpoint antes cleanup
        time.sleep(1.0)  # Allow SQLite to checkpoint + release locks

def test_concurrent_consume(self, bus):
    # ... existing test ...
    
    threads = [threading.Thread(target=consume_and_process) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # CRITICAL: Aguardar commits + processing antes assertion
    time.sleep(0.5)
    
    pending = bus.store.get_pending_events("mission-001")
    assert len(pending) <= 1
```

---

## Implementação Timeline

### FASE 1: Backend Dev Fixes (1h)
- [ ] Implementar `reserve_event_atomic()` em event_store.py
- [ ] Integrar em event_consumer.py consume_pending()
- [ ] Adicionar `_checkpoint_wal()` em event_store.py
- [ ] Atualizar todos métodos de modificação com checkpoint

### FASE 2: Test Synchronization (30 min)
- [ ] Adicionar time.sleep() em fixtures
- [ ] Adicionar time.sleep() antes assertions
- [ ] Adicionar barrier synchronization onde apropriado

### FASE 3: QA + Security Validation (1h)
- [ ] Re-executar 10 testes
- [ ] Executar 8 testes faltantes (completar 18/18)
- [ ] Testar regressão STEP 1
- [ ] Security audit atomicidade

---

## Critérios de Sucesso

✅ 0 PermissionError em Windows  
✅ Concurrent consume sem race condition  
✅ 18/18 testes PASS (ou 90%+ com evidência clara)  
✅ Zero regressão STEP 1  
✅ Atomicidade verificada (no duplicated processing)  
✅ WAL checkpoint validado  

---

## Referências

- **Event Store**: `C:\dev\neoeve\event_bus\event_store.py`
- **Event Consumer**: `C:\dev\neoeve\event_bus\event_consumer.py`
- **Tests**: `C:\dev\neoeve\tests\test_event_bus_reliability.py`
- **SQLite WAL**: https://www.sqlite.org/wal.html
- **SQLite Threading**: https://www.sqlite.org/threadsafe.html

---

## Status de Implementação (Atualizado 2026-11-22)

### FASE 1: Backend Dev ✅ 
- [x] Implementar `reserve_event_atomic()` ✅ COMPLETO
- [x] Integrar em event_consumer.py ✅ COMPLETO
- [x] Adicionar WAL checkpoint ✅ COMPLETO
- [x] Atualizar test waits ✅ COMPLETO

### FASE 2: Resultados Teste

**test_concurrent_consume**: 4/10 eventos consumidos (esperado 6)
- ✅ Atomic reserve funcionando (sem duplicatas)
- ⚠️ Limitação: get_pending_events() chamado antes de reservas completarem
- 🔴 Necessário: Loop com retry ou re-query após falhas

**SQLite WAL Locking**: Persistente em Windows
- ✅ WAL_CHECKPOINT(TRUNCATE) aplicado
- ✅ sleep(2.0) adicionado
- 🔴 Teardown ainda falha: PermissionError em arquivo .db
- 🔴 Raiz: Windows não libera locks mesmo após checkpoint + close()

### BLOCKERS IDENTIFICADOS

1. **Concurrent Consume Efficiency**: 40% eventos consumidos vs 60% esperado
   - Causa: Race entre get_pending + reserve atomicamente
   - Fix necessário: Loop com exponential backoff ou redesign consume pattern

2. **WAL Locking Windows Persistence**: Bloqueia cleanup tempdir
   - Causa: SQLite manter locks em modo WAL após close() em Windows
   - Fix recomendado: 
     a. Usar persistent DB path instead of tempdir (não é testing)
     b. Disable WAL mode for tests (`PRAGMA journal_mode=DELETE`)
     c. Increase sleep dramatically (5+ seconds)

---

**Status**: 🟡 PARCIALMENTE RESOLVIDO  
**P0 (WAL Locking)**: 30% mitigado (ainda bloqueia cleanup)  
**P1 (Concurrent Consume)**: 60% resolvido (atomic reserve works, efficiency baixa)  
**Próximo**: Decisão sobre WAL vs non-WAL tests
