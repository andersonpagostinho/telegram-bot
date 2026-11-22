# MISSÃO 005.1 — STEP 2.1 Plano de Continuação

**Status**: 🟡 AUTORIZADO — PRONTO PARA INVESTIGAÇÃO  
**Data Autorização**: 2026-11-22  
**Escopo**: Investigação + Correção SQLite + Concorrência  
**Estimativa**: 6 horas

---

## Estado Anterior (STEP 2)

**Commits**: 08f38dc  
**Resultado**: 1 PASS / 11 FAIL  
**Bloqueadores**:
- SQLite file locking (Windows)
- Concurrent consume race condition
- Thread synchronization issues

**Causa-Raiz**: Conexões SQLite não fechando → arquivo DB bloqueado → tempdir cleanup falha

---

## STEP 2.1 — Próximas Ações (Prioridade)

### FASE 1: Debugger Investigation (2h)

**P0 — SQLite File Locking**:
```
[ ] Reproduzir erro: python -m pytest tests/test_event_bus_reliability.py -v
[ ] Verificar: event_store.py _get_connection() context manager
[ ] Verificar: Conexões não fechadas em exceções
[ ] Verificar: Multiple threads accessing mesmo db_path
[ ] Testar: check_same_thread=False funciona
[ ] Verificar: WAL mode + Windows behavior
[ ] Raiz: db.close() not called in exception path
```

**P1 — Concurrent Consume**:
```
[ ] Reproduzir: test_concurrent_consume in isolation
[ ] Debug: Dois consumidores pegando mesmo evento
[ ] Verificar: UPDATE event SET status='PROCESSING' é atômico
[ ] Verificar: SQLite locks suficiente para serializar
[ ] Raiz: Falta BEGIN IMMEDIATE + atomic reserve
```

**P1 — Thread Sync**:
```
[ ] Verificar: Threads aguardam antes cleanup
[ ] Verificar: Arquivos temporários permanecem abertos
[ ] Verificar: Conexões não encerram
[ ] Raiz: sqlite3 connection pooling necessário
```

### FASE 2: Backend Dev Fixes (2h)

**Fix 1 — Garantir Fechamento Conexões**:
```python
# event_store.py — cada método:
try:
    conn = self._get_connection()
    # operação
    conn.commit()
finally:
    conn.close()  # OBRIGATÓRIO
```

**Fix 2 — Atomic Event Reserve**:
```python
# event_store.py — novo método:
def reserve_event_atomic(self, event_id: str) -> bool:
    """Atomically reserve event for processing"""
    with self._lock:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")  # Exclusive lock
            cursor.execute(
                "UPDATE events SET status=? WHERE event_id=? AND status=?",
                (EventStatus.PROCESSING.value, event_id, EventStatus.PENDING.value)
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return False
            conn.commit()
            return True
```

**Fix 3 — Test Synchronization**:
```python
# test_event_bus_reliability.py:
# Adicionar após threads.join():
time.sleep(1.0)  # Aguardar SQLite liberar locks
# ou usar Barrier() para sincronização determinística
```

### FASE 3: QA + Security Validation (2h)

**QA**:
```
[ ] Executar todos 12 testes
[ ] Registrar PASS/FAIL individual
[ ] Testar recovery path
[ ] Testar idempotência real
[ ] Testar persistence
[ ] Separar mock vs real SQLite
```

**Security**:
```
[ ] Verificar atomicidade reserva
[ ] Verificar ausência duplicação
[ ] Verificar integridade transições
[ ] Verificar isolamento dados
[ ] Verificar sem race conditions
```

---

## Checklist Implementação

### Backend Dev Checklist:
- [ ] Adicionar connection closing em finally blocks
- [ ] Implementar reserve_event_atomic()
- [ ] Adicionar BEGIN IMMEDIATE onde necessário
- [ ] Adicionar proper synchronization em testes
- [ ] Testar cada fix isoladamente

### QA Checklist:
- [ ] Re-executar test_concurrent_publish (must PASS)
- [ ] Re-executar test_concurrent_consume (fix concorrência)
- [ ] Re-executar test_restart_with_pending (fix file locking)
- [ ] Re-executar test_recover_stuck_events
- [ ] Re-executar test_concurrent_duplicate_key
- [ ] Re-executar todos 12 testes
- [ ] Verificar zero regressão STEP 1

### Security Auditor Checklist:
- [ ] Atomicidade de operações
- [ ] Ausência de TOCTOU bugs
- [ ] Integridade sob concorrência
- [ ] Isolamento entre missões

---

## Commits Esperados

1. `event_store.py` — Connection fixes + atomic reserve
2. `test_event_bus_reliability.py` — Synchronization fixes
3. `MISSION_005_1_STEP_2_1_INVESTIGATION_REPORT.md` — Final report

---

## Critérios Aprovação STEP 2.1

```
✅ Causa-raiz SQLite identificada e resolvida
✅ Concurrent consume funcionando corretamente
✅ File locking eliminado
✅ 11/12 testes PASS (ou >90%)
✅ Zero regressão STEP 1
✅ QA aprovado
✅ Security aprovado
✅ Relatório consolidado
```

---

## Timeline Sugerida

**Próxima Sessão**:
- 15 min: Debugger início investigação
- 45 min: Debugger continue investigação + relatório
- 1h 30 min: Backend Dev implement fixes
- 1h: QA execute testes + valida
- 30 min: Security audit + consolidação
- 15 min: Relatório final

---

**Pronto para**: Próxima sessão STEP 2.1  
**Arquivos críticos**: event_store.py, test_event_bus_reliability.py  
**Commits anteriores**: 08f38dc (testes base)

