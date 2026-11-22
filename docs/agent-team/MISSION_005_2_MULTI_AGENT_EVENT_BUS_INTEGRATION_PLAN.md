# MISSÃO 005.2 — MULTI-AGENT EVENT BUS INTEGRATION PLAN

**Status**: 📋 Architecture Ready  
**Foundation**: MISSION 005.1 STEP 2 (Core Event Bus APPROVED)  
**Timeline**: Ready for STEP 3 implementation

---

## Participants

1. **Architect/Tech Lead** — Coordena
2. **Backend Developer** — Implementa agents
3. **Debugger** — Investiga issues
4. **QA Engineer** — Testa integração
5. **Security Auditor** — Valida permissões
6. **Release Manager** — Governa publicação
7. **OpenAI Validator** (externo) — Aprova decisões

---

## Event Architecture

### Event Structure

```
Event {
  event_id: "evt-timestamp-uuid"
  event_type: EventType (TASK_CREATED, TASK_COMPLETED, etc)
  
  mission_id: "mission-001"           # Which mission
  task_id: "task-id"                  # Which task (if applicable)
  execution_id: "execution-id"        # Which execution attempt
  
  agent_id: "agent-role"              # Who published (architect, backend, qa, etc)
  agent_role: "role"                  # Role identifier
  
  correlation_id: "trace-id"          # Request trace
  causation_id: "parent-event-id"     # What triggered this
  
  payload: {...}                      # Domain data
  status: EventStatus (PENDING, PROCESSING, COMPLETED, FAILED)
  
  timestamp: ISO8601
  created_at: ISO8601
}
```

### Event Flow

```
1. Agent publishes event → EventBus.publish(event)
2. EventBus:
   - Validates event contract
   - Stores to SQLite (atomic write)
   - Logs to JSONL audit trail
   - Returns event_id
3. Consumers:
   - Query pending events
   - Atomically reserve (reserve_event_atomic)
   - Process in background
   - Mark COMPLETED or FAILED
```

---

## Per-Agent Integration

### 1. Architect/Tech Lead

**Publishes**:
- PHASE_PLAN (architecture decisions)
- DESIGN_REVIEW (review results)
- APPROVAL (component approval)

**Consumes**:
- TASK_CREATED (from Release Manager)
- BLOCKER_FOUND (from Debugger)
- VALIDATION_RESULT (from QA, Security)

**Idempotency Key**: `architect-{mission}-{phase}`

---

### 2. Backend Developer

**Publishes**:
- IMPLEMENTATION_STARTED
- CODE_COMMITTED
- BUILD_PASSED/FAILED

**Consumes**:
- REVIEW_REQUESTED (from Architect)
- TEST_FAILED (from QA)
- SECURITY_ISSUE (from Security Auditor)

**Idempotency Key**: `backend-{task}-{attempt}`

---

### 3. Debugger

**Publishes**:
- INVESTIGATION_STARTED
- ROOT_CAUSE_FOUND
- RECOMMENDATION (fix, clarify, or accept)

**Consumes**:
- TEST_FAILED (from QA)
- ISSUE_REPORTED (from Release Manager)

**Idempotency Key**: `debugger-{issue}-{attempt}`

---

### 4. QA Engineer

**Publishes**:
- TEST_STARTED
- TEST_PASSED
- TEST_FAILED

**Consumes**:
- CODE_COMMITTED (from Backend)
- REGRESSSION_CHECK (from Architect)

**Idempotency Key**: `qa-{test}-{run}`

---

### 5. Security Auditor

**Publishes**:
- AUDIT_STARTED
- VULNERABILITY_FOUND
- AUDIT_PASSED

**Consumes**:
- CODE_REVIEW_REQUESTED (from Architect)
- NEW_FEATURE_TO_AUDIT (from Backend)

**Idempotency Key**: `security-{component}-{version}`

---

### 6. Release Manager

**Publishes**:
- DEPLOYMENT_PLAN
- RELEASE_APPROVED
- RELEASE_BLOCKED

**Consumes**:
- ALL_APPROVALS_COLLECTED
- VALIDATION_RESULTS

**Idempotency Key**: `release-{version}-{attempt}`

---

### 7. OpenAI Validator (External)

**Publishes**:
- VALIDATION_PASSED
- VALIDATION_FAILED
- VALIDATION_COMMENT

**Consumes**:
- VALIDATION_REQUESTED (from Release Manager)

**Idempotency Key**: `validator-{request}-{attempt}`

**Special Handling**:
- API calls tracked (cost limits)
- Retry logic (up to 3 attempts)
- Timeout: 5 minutes per request
- Dead-letter if unavailable

---

## Contracts

### Must Be Preserved

1. **SQLite = Source of Truth**: JSONL complementar
2. **Event Bus = No Business Logic**: Only coordination
3. **Atomic Reserve**: No duplicates
4. **Idempotency**: Repeated publication safe
5. **Multi-tenant Isolation**: mission_id segregates data
6. **No Auto-Approval**: Each role validates independently
7. **Failure Handling**: Events can be retried or dead-lettered

### Mandatory Per Agent

- **Unique agent_id**: "architect", "backend", "qa", "security", "release", "debugger", "validator"
- **Proper correlation_id**: Trace calls
- **Causation_id when applicable**: Link dependencies
- **Idempotency key**: Allow safe replay

---

## Failure Handling

### Retry Strategy

```
Attempt 1: Immediate
Attempt 2: +5 seconds
Attempt 3: +30 seconds
After 3: Move to DEAD_LETTER, alert human
```

### Dead-Letter

- Events that fail processing 3× go to DEAD_LETTER
- Manual review required
- Cannot auto-recover

### Stuck Event Recovery

- Events in PROCESSING > 30min → Recovered to PENDING
- Automatic retry up to 3×
- Alert if still stuck

---

## Isolation & Multi-Tenant

### Data Segregation

```
Every event must have mission_id.
Queries always filter by mission_id.
No cross-mission data visible.
```

### Consumer Isolation

```
Each agent owns its own EventConsumer.
No shared state between agents.
Locks are per-event, not per-agent.
```

---

## Monitoring & Auditability

### Metrics to Track

- Events published per agent
- Event processing latency (p50, p99)
- Retry rate per event type
- Dead-letter queue size
- Consumer lag

### Audit Trail

- All events logged to JSONL
- Correlation_id traces request flow
- causation_id shows dependencies
- processing_log tracks state changes

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| TOCTOU | Race condition detected | Retry |
| TIMEOUT | Consumer took >30m | Recover to PENDING |
| DEADLETTER | Failed 3× | Manual review |
| BUSY | SQLite locked | Retry (up to 5s) |

---

## Configuration for Production

```ini
[Event Bus]
db_path = /var/lib/neoeve/event_bus.db
use_wal = True
journal_mode = WAL
synchronous = NORMAL
busy_timeout = 5000
max_retries = 3
stuck_timeout_minutes = 30
```

---

## Approval Gate for STEP 3

Before starting STEP 3 integration:

1. ✅ STEP 2.4 audit complete
2. ✅ This plan reviewed
3. ✅ Agents briefed
4. ✅ Deployment environment ready
5. ✅ Monitoring configured

**Status**: Ready for STEP 3 implementation authorization

---

**Integration Plan Ready**: 📋  
**Next**: STEP 3 Implementation
