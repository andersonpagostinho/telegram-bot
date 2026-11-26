# Approval Engine C.2.2.2 — WebSocket + Concurrency Validation

**Date**: 2026-11-23  
**Status**: ✅ FOUNDATION READY FOR PHASE 2  
**Previous Completion**: C.2.2.1 (12/12 tests, idempotency fixed)

---

## CURRENT STATE

✅ **Approval Engine Core** (`app/services/approval_engine.py`):
- 7 methods: request_approval, submit_validation, approve, reject, veto, get_approval_status, get_approval_history
- Idempotency checks added in approve/reject/veto
- Multi-tenant isolation validated
- Event Bus integration (5 event types)
- In-memory storage (ready for database migration)

✅ **12 Tests** (`tests/test_approval_engine.py`):
- All passing in consolidated execution
- Coverage: request, approve, reject, veto, self-approval block, no-evidence block, duplicate detection, tenant isolation, history, placeholders for integration tests

---

## REQUIRED FOR C.2.2.2

### 1. PostgreSQL Persistence

**Current**: In-memory `_approvals` dict  
**Required**: Persist to `Validation` table (database/models.py:289-312)

**Migration**:
```python
# Current in-memory
self._approvals[approval_id] = record

# Required PostgreSQL
validation = Validation(
    validation_id=approval_id,
    mission_id=mission_id,
    validator="qa_engineer|security_auditor|...",
    verdict="APPROVED|REJECTED|BLOCKED|PENDING",
    findings_summary={...},
    created_at=utc_now()
)
db.add(validation)
db.commit()  # Must complete BEFORE event publishing
```

### 2. Event Bus Real Flow

**Current**: Mock events published  
**Required**: Real PostgreSQL commit → Event Bus → WebSocket

**Flow**:
```
1. Approval Engine commits to Validation table
2. Event Bus publishes to processed_events table
3. Projection Worker reads processed_events
4. WebSocket Manager notifies authorized clients
5. Client receives real-time update
```

**Changes Needed**:
- `app/services/approval_engine.py`: Inject database session, use Validation model instead of in-memory dict
- Event publishing: Ensure idempotency_key prevents duplicate events
- Projection Worker: Listen for approval.* events and route to WebSocket

### 3. Concurrency Safety

**Current Issue**: Two concurrent `approve()` calls on same `approval_id` could succeed

**Risk Scenario**:
```python
# Thread 1
if record.status not in DECIDED_STATES:  # Check passes
    # Thread 2 also passes check here
    record.status = APPROVED  # Both write

# Thread 2
if record.status not in DECIDED_STATES:  # Still PENDING
    record.status = APPROVED
```

**Solution Required**:
- PostgreSQL: Use `SELECT ... FOR UPDATE` (row-level lock)
- Or: Atomic `UPDATE Validation SET verdict=X WHERE validation_id=Y AND verdict IS NULL`
- Ensures only one thread succeeds

**Validation Query**:
```sql
UPDATE validation 
SET verdict = 'APPROVED'
WHERE validation_id = ? 
  AND verdict IS NULL
  AND updated_at = (SELECT updated_at FROM validation WHERE validation_id = ?)
RETURNING rows_affected;
```

### 4. WebSocket Integration Tests

**Tests to Add** (8 scenarios):

1. **test_websocket_approval_notifies_authorized_client**
   - Approve mission → WebSocket message sent to authorized tenant/project
   
2. **test_websocket_isolation_blocks_unauthorized**
   - Approve mission in tenant-A → tenant-B client receives nothing
   
3. **test_concurrent_approvals_one_wins**
   - Two threads call approve() simultaneously → only one succeeds
   
4. **test_concurrent_approve_reject_deterministic**
   - approve() and reject() race → deterministic winner (e.g., approve wins if first commit)
   
5. **test_veto_blocks_subsequent_approve**
   - Veto issued → subsequent approve() fails
   
6. **test_persistence_before_notification**
   - Approval persisted to PostgreSQL → then WebSocket notified (never before)
   
7. **test_rest_recovery_after_disconnect**
   - Client disconnected → reconnects → REST API returns pending approvals
   
8. **test_multiple_clients_same_mission**
   - Two clients subscribe to mission → both receive notifications (tenant-scoped)

---

## IMPLEMENTATION CHECKLIST FOR NEXT SESSION

### Phase 1: Database Integration
- [ ] Migrate `_approvals` dict to `Validation` table
- [ ] Update `request_approval()` to create Validation record
- [ ] Update `approve/reject/veto()` to use `SELECT ... FOR UPDATE`
- [ ] Ensure transaction completes before event publishing

### Phase 2: Concurrency Validation
- [ ] Add PostgreSQL-backed concurrency tests (3 scenarios)
- [ ] Verify row-level locks prevent duplicate decisions
- [ ] Test veto precedence logic

### Phase 3: WebSocket Integration
- [ ] Extend Projection Worker to listen for `approval.*` events
- [ ] WebSocket Manager routes events to authorized clients
- [ ] Add `WebSocketEventLog` persistence for recovery
- [ ] Implement REST recovery endpoint

### Phase 4: Real Integration Tests
- [ ] 8 test scenarios above
- [ ] Run with PostgreSQL (not SQLite)
- [ ] Verify end-to-end flow: approval → persistence → event → websocket

---

## FILES REQUIRING CHANGES

| File | Change | Complexity |
|------|--------|-----------|
| `app/services/approval_engine.py` | Inject DB session, use Validation model, add row locks | Medium |
| `tests/test_approval_engine.py` | Add 8 integration tests with real PostgreSQL | High |
| `app/services/event_bus.py` | Ensure event idempotency for approval.* events | Low |
| `app/services/projection_worker.py` | Add listener for approval.* event type | Medium |
| `app/services/websocket_manager.py` | Route approval events to authorized clients | Medium |

---

## KNOWN BLOCKERS

1. **In-Memory Storage**: Current implementation doesn't persist to database
   - **Impact**: No recovery after process restart
   - **Resolution**: Migrate to Validation table (Phase 1)

2. **No Row-Level Locks**: Concurrency tests will fail
   - **Impact**: Race conditions possible in production
   - **Resolution**: Use `SELECT ... FOR UPDATE` (Phase 2)

3. **WebSocket Not Wired**: Events published but not sent to clients
   - **Impact**: Real-time notifications not working
   - **Resolution**: Extend Projection Worker (Phase 3)

4. **SQLite in Tests**: Cannot test with real PostgreSQL isolation
   - **Impact**: Concurrency tests unreliable
   - **Resolution**: Use PostgreSQL test container (Phase 4)

---

## TOKENS ESTIMATE

- Phase 1 (Database): ~1.5M tokens
- Phase 2 (Concurrency): ~1M tokens
- Phase 3 (WebSocket): ~1.5M tokens
- Phase 4 (Integration): ~2M tokens
- **Total**: ~6M tokens

Recommend next session with fresh token budget.

---

## SIGN-OFF

**Current Status**: ✅ Ready for C.2.2.2 Phase 1  
**12 Tests**: ✅ All passing (in-memory)  
**Idempotency**: ✅ Fixed  
**Real Persistence**: ⏳ Required  
**Concurrency Safety**: ⏳ Required  
**WebSocket Integration**: ⏳ Required  

**Next Step**: Create new session, implement database layer + concurrency tests.
