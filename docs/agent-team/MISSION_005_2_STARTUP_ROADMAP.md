# MISSÃO 005.2 — MULTI-AGENT NEOEVE INTEGRATION
## Startup Roadmap & Implementation Strategy

**Status**: 📋 Fase 1 — Auditoria do Event Bus  
**Checkpoint**: aafbb95 (MISSION 005.1 STEP 2 APPROVED)  
**Escopo**: 8 Fases, 7 Agentes, Event-Driven Coordination

---

## Visão Geral

**Objetivo**: Eliminar intermediação manual do usuário pela integração de 7 participantes via Event Bus.

**Current State**:
- ✅ Core Event Bus: Production-ready (MISSION 005.1)
- ✅ Atomic operations: Guaranteed
- ✅ Multi-agent architecture: Planned
- ⏳ Agent integration: Not yet implemented

**Expected Result**:
```
User → Architect (publishes MISSION)
   ↓
Architect distributes TASK via Event Bus
   ↓
Backend/Debugger/QA consume task, work, publish result
   ↓
Results routed back to Architect
   ↓
Architect requests validation (Security, QA, OpenAI)
   ↓
Consolidated decision returned to User
```

---

## Os 7 Participantes

| Agent | Role | Publishes | Consumes | Approval Power |
|-------|------|-----------|----------|-----------------|
| **Architect** | Coordinator | MISSION, TASK, DECISION | All results | YES (decisions) |
| **Backend** | Implementer | FIX_IMPLEMENTED, CODE_DIFF | TASK, REVIEW_REQUESTED | NO |
| **Debugger** | Investigator | ROOT_CAUSE_IDENTIFIED, FIX_PROPOSED | BUG_DETECTED, TASK | NO |
| **QA** | Validator | TEST_COMPLETED, QA_APPROVED/REJECTED | CODE_DIFF, TASK | YES (tests) |
| **Security** | Auditor | SECURITY_APPROVED/REJECTED, AUDIT_REPORT | FIX_IMPLEMENTED, TASK | YES (security) |
| **Release Manager** | Publisher | RELEASE_PROPOSED, DEPLOYMENT_REQUESTED | All validations | YES (gates) |
| **OpenAI Validator** | Advisor | VALIDATION_COMPLETED, ANALYSIS_REPORT | VALIDATION_REQUESTED | YES (advisory) |

---

## 8 Fases de Implementação

### FASE 1: Auditoria Event Bus
**Objetivo**: Confirmar que o Core Event Bus atende aos requisitos multiagente.

**Checklist**:
- [ ] Event contracts exist and are extensible
- [ ] reserve_event_atomic() works for concurrent agents
- [ ] Consumer registration per agent working
- [ ] Loop implementation handles multiple consumers
- [ ] Recovery mechanisms preserve events
- [ ] SQLite schema supports agent_id, source_agent, target_agent
- [ ] Idempotency keys work for repeated agent invocations
- [ ] Multi-tenant isolation verified (mission_id)

**Deliverable**: MISSION_005_2_EVENT_BUS_AUDIT.md

**Estimated Effort**: 2-3 hours

---

### FASE 2: Event Envelope Padronizado
**Objetivo**: Define the standard event structure for all 7 agents.

**Requires**:
```json
{
  "event_id": "evt-timestamp-uuid",
  "event_type": "MISSION_CREATED|TASK_ASSIGNED|...",
  "schema_version": "1.0",
  
  "mission_id": "mission-001",
  "task_id": "task-001",
  "execution_id": "exec-id",
  
  "correlation_id": "trace-id",
  "causation_id": "parent-event-id",
  
  "project_id": "project-neoeve",
  "tenant_id": "tenant-001",
  
  "source_agent": "architect|backend|debugger|qa|security|release|validator",
  "target_agent": "architect|backend|...",
  
  "actor_id": "user-id",
  "actor_role": "admin|user",
  
  "payload": { /* domain-specific */ },
  "metadata": { /* tags, priority, etc */ },
  
  "created_at": "ISO8601",
  "idempotency_key": "unique-per-operation"
}
```

**Validation Rules**:
- No cross-tenant data mixing
- No secrets in payload
- Schema version must be explicit
- Correlation_id traces request flow

**Deliverable**: MISSION_005_2_EVENT_ENVELOPE.md + schema.json

**Estimated Effort**: 1-2 hours

---

### FASE 3: Integração dos Agentes
**Objetivo**: Enable each agent to publish and consume events.

**Per-Agent Integration**:

**Architect**:
- Consumer: TASK_COMPLETED, QA_APPROVED, SECURITY_APPROVED, VALIDATION_COMPLETED
- Publisher: MISSION_CREATED, TASK_ASSIGNED, REVIEW_REQUESTED
- Role: Distribute work + consolidate results

**Backend**:
- Consumer: TASK_ASSIGNED (implementation tasks)
- Publisher: CODE_COMMITTED, FIX_IMPLEMENTED, CODE_DIFF_AVAILABLE
- Role: Implement fixes, respond to requests

**Debugger**:
- Consumer: BUG_DETECTED, TASK_ASSIGNED (investigation tasks)
- Publisher: INVESTIGATION_STARTED, ROOT_CAUSE_IDENTIFIED, FIX_PROPOSED
- Role: Investigate, diagnose, recommend

**QA**:
- Consumer: CODE_DIFF_AVAILABLE, TASK_ASSIGNED (testing tasks)
- Publisher: TEST_STARTED, TEST_COMPLETED, QA_APPROVED, QA_REJECTED
- Role: Test, validate, approve/reject

**Security**:
- Consumer: FIX_IMPLEMENTED, TASK_ASSIGNED (audit tasks)
- Publisher: AUDIT_STARTED, SECURITY_APPROVED, SECURITY_REJECTED
- Role: Audit, verify, block if needed

**Release Manager**:
- Consumer: QA_APPROVED, SECURITY_APPROVED, VALIDATION_COMPLETED
- Publisher: RELEASE_PROPOSED, DEPLOYMENT_REQUESTED, RELEASE_BLOCKED
- Role: Gate-keeper, control release decisions

**OpenAI Validator**:
- Consumer: VALIDATION_REQUESTED
- Publisher: VALIDATION_COMPLETED, ANALYSIS_REPORT
- Role: Independent advisory

**Integration Approach**:
1. Add event publishing hooks to each agent
2. Create event consumer task per agent
3. Wire task results back to Event Bus
4. Implement auto-retry for failed processing

**Deliverable**: Agent integration code + hooks

**Estimated Effort**: 6-8 hours

---

### FASE 4: Dispatcher & Orchestrator
**Objetivo**: Route events, distribute tasks, track execution.

**Responsibilities**:
- Route event to correct consumer
- Track task assignment
- Handle acknowledgments
- Implement timeout/retry
- Reatribute abandoned tasks
- Deduplication on retry

**Key Contracts**:
- TASK can't be executed by 2 agents simultaneously (without explicit permission)
- Timeout = 30 minutes → escalate to Architect
- Retry up to 3 times → dead-letter if still failing
- Idempotency_key prevents duplicate execution

**Deliverable**: Dispatcher implementation + tests

**Estimated Effort**: 3-4 hours

---

### FASE 5: OpenAI Validator Integration
**Objetivo**: Wire OpenAI Validator as event consumer.

**Flow**:
1. Architect publishes VALIDATION_REQUESTED
2. Event Bus routes to Validator handler
3. Validator collects evidence (diffs, test results, audit)
4. OpenAI API call with structured output
5. Result published as VALIDATION_COMPLETED
6. Event routed back to Architect

**Constraints**:
- Cost tracking
- Token limits per request
- API retry logic
- Structured outputs validation

**Deliverable**: Validator adapter code + tests

**Estimated Effort**: 2-3 hours

---

### FASE 6: Estados e Recuperação
**Objetivo**: Implement mission/task lifecycle with recovery.

**States**:
```
MISSION: CREATED → QUEUED → ASSIGNED → RUNNING → 
         WAITING_VALIDATION → COMPLETED/FAILED/BLOCKED

TASK: CREATED → ASSIGNED → ACCEPTED → RUNNING → 
      COMPLETED/FAILED/REASSIGNED
```

**Recovery**:
- Restart with pending events preserved
- Stuck tasks recovered
- Abandoned work reatributed
- No duplicate execution

**Deliverable**: State machine implementation + tests

**Estimated Effort**: 2-3 hours

---

### FASE 7: Autonomia Operacional
**Objetivo**: Enable agents to work independently within permissions.

**Authorized**:
- Read code/logs
- Investigate errors
- Create/run tests
- Propose fixes
- Request validations

**Protected** (require explicit authorization):
- Deploy
- Push remote
- Production access
- Destructive changes

**Deliverable**: Permission matrix + enforcement code

**Estimated Effort**: 2-3 hours

---

### FASE 8: Testes E2E & Auditoria Final
**Objetivo**: Validate full integration and security.

**Test Scenarios** (20+):
- [ ] Simple task flow (all 7 agents)
- [ ] Blocking by Security
- [ ] Rejection by QA
- [ ] OpenAI Validator approval
- [ ] Timeout and retry
- [ ] Reatribution on failure
- [ ] Idempotency on duplicate
- [ ] Recovery after process crash
- [ ] Multi-tenant isolation
- [ ] Concurrency (multiple missions)
- [ ] Error scenarios (API fail, DB fail, timeout)

**Deliverable**: MISSION_005_2_TEST_REPORT.md + all tests PASS

**Estimated Effort**: 4-6 hours

---

## Total Effort Estimate

| Phase | Hours | Cumulative |
|-------|-------|-----------|
| 1. Audit Event Bus | 3 | 3 |
| 2. Event Envelope | 2 | 5 |
| 3. Agent Integration | 7 | 12 |
| 4. Dispatcher | 4 | 16 |
| 5. OpenAI Validator | 3 | 19 |
| 6. States & Recovery | 3 | 22 |
| 7. Autonomy | 3 | 25 |
| 8. E2E Tests & Audit | 5 | 30 |
| **TOTAL** | **~30 hours** | - |

---

## Sequential Dependencies

```
FASE 1 ← Prerequisite (audit existing Event Bus)
  ↓
FASE 2 ← Define event structure
  ↓
FASE 3 ← Integrate agents (requires envelope from 2)
  ↓
FASE 4 ← Dispatcher (requires agents from 3)
  ↓
FASE 5 ← OpenAI (can run parallel with 3-4)
  ↓
FASE 6 ← States (requires dispatcher from 4)
  ↓
FASE 7 ← Permissions (can run parallel with 6)
  ↓
FASE 8 ← Tests (final validation of all phases)
```

---

## Deliverables Summary

```
MISSION_005_2_EVENT_BUS_AUDIT.md
  ↓
MISSION_005_2_EVENT_ENVELOPE.md + schema.json
  ↓
Agent integration code (7 adapters)
  ↓
Dispatcher implementation
  ↓
OpenAI Validator adapter
  ↓
State machine + recovery
  ↓
Permission matrix
  ↓
MISSION_005_2_IMPLEMENTATION_REPORT.md
MISSION_005_2_TEST_REPORT.md
MISSION_005_2_SECURITY_REPORT.md
MISSION_005_2_FINAL_HANDOFF.md
```

---

## Critical Success Factors

1. **Event Bus Stability**: MISSION 005.1 STEP 2 must remain stable
2. **Agent Availability**: All 7 agents must be invocable from Event Bus
3. **Atomic Operations**: No duplicated execution under any condition
4. **Idempotency**: Repeated invocations produce same result
5. **Recovery**: Restart doesn't lose work
6. **Isolation**: Multi-tenant data never mixed
7. **Security**: Each agent can only access authorized events
8. **Auditability**: Complete trace of all operations

---

## Non-Negotiables

✅ No automatic deploy (requires explicit Release Manager authorization)  
✅ No bypass of security review (Security can always block)  
✅ No shared state (each agent independent)  
✅ No hardcoded credentials (env vars only)  
✅ No production writes from test code  
✅ No automatic schema migrations  
✅ No OpenAI costs without tracking  
✅ NeoEve operational data remains independent  

---

## Ready for FASE 1

All prerequisites met:
- ✅ MISSION 005.1 STEP 2 APPROVED FOR PRODUCTION
- ✅ Core Event Bus: Production-ready
- ✅ Atomic reserve proven
- ✅ Multi-tenant architecture defined
- ✅ MISSION 005.2 architecture planned

**Next Step**: Begin FASE 1 (Event Bus Audit)

**Timeline**: 30 hours estimated, executáble in parallel phases where noted

**Status**: Ready to proceed when authorized by user
