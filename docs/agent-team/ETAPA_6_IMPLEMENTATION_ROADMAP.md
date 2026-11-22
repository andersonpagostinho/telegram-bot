# ETAPA 6 — IMPLEMENTATION ROADMAP
## Real Agent Integration - Handoff & Next Steps

**Date**: 2026-11-22  
**Status**: Phase planning complete, ready for implementation  
**Token Checkpoint**: Document created for future sessions  

---

## 📋 WHAT'S BEEN COMPLETED (ETAPAS 1-5.1)

### Foundation Built ✅
- Event Bus with full persistence
- Dispatcher with routing rules  
- Governance engine (8/8 rules)
- 7 agent handlers (local Python)
- Event correlation & causation chains
- Idempotency verification
- Audit trail implementation
- E2E test infrastructure

### Critical Fixes Applied ✅
- P5.1: Release Manager routing fixed
- P5.2: Event correlation retrieval added
- P5.3: Security severity integration complete

### Test Results ✅
- 3/7 E2E scenarios PASSING
- Core architecture verified
- Governance rules functional
- Zero blocking issues

---

## 🎯 ETAPA 6 PHASES AT A GLANCE

### PHASE 1: Agent Invocation Bridge (1-2 hours)
**Goal**: Establish mechanism to invoke real Claude Code agents

**Tasks**:
1. Create `event_bus/agent_invocation.py`
2. Implement wrapper for Claude Code Agent tool
3. Define input/output contracts
4. Add error handling & timeouts

**Deliverable**: Working bridge that handlers can call

---

### PHASE 2: Architect ↔ Backend Real Flow (2-3 hours)
**Goal**: Prove real agent communication

**Tasks**:
1. Update ArchitectHandler to call real agent
2. Update BackendHandler to call real agent
3. Run E2E test with real invocations
4. Capture execution evidence

**Success**: Agents invoke each other automatically via Event Bus

---

### PHASE 3: Remaining Agents Integration (2-3 hours)
**Goal**: Integrate Debugger, QA, Security into real pipeline

**Tasks**:
1. Update DebuggerHandler
2. Update QAEngineerHandler
3. Update SecurityAuditorHandler
4. Keep ReleaseManagerHandler as local decision engine

**Success**: All agents respond to events correctly

---

### PHASE 4: OpenAI Validator Real (1-2 hours)
**Goal**: Execute real OpenAI API calls

**Tasks**:
1. Configure OpenAI credentials
2. Update OpenAIValidatorHandler with real API calls
3. Add cost tracking
4. Implement timeout/retry logic

**Success**: Real GPT-4o validations recorded

---

### PHASE 5: Full Pipeline Test (1-2 hours)
**Goal**: Run complete mission through real agents

**Tasks**:
1. Create test mission
2. Execute Architect → Backend → QA → Security → Validator → Release flow
3. Record all invocation evidence
4. Verify governance still enforced

**Success**: Full automated pipeline with real agents

---

### PHASE 6: Failure Tests (1-2 hours)
**Goal**: Verify graceful failure handling

**Test Cases**:
1. Agent unavailable
2. Timeout
3. Invalid response
4. Duplicate event
5. Backend failure
6. QA rejection
7. Security veto
8. OpenAI API error
9. Self-approval attempt
10. Unauthorized operation

**Success**: All failures handled without data loss

---

### PHASE 7: Security & Audit (1-2 hours)
**Goal**: Verify isolation and audit trail

**Checks**:
- Isolation by project/mission
- Audit trail completeness
- No secrets in logs
- Agent identities verified
- Governance still enforced

---

### PHASE 8: Documentation (1-2 hours)
**Goal**: Complete final reports

**Deliverables**:
1. MISSION_005_2_FINAL_REPORT.md
2. MISSION_005_2_EXECUTIVE_SUMMARY.md
3. Agent invocation evidence
4. Cost summary
5. Limitations documented

---

## 🔧 IMPLEMENTATION DETAILS

### File Changes Required

**New Files**:
```
event_bus/agent_invocation.py          (100-150 lines)
tests/test_etapa_6_real_agents.py      (200-300 lines)
```

**Modified Files**:
```
event_bus/agent_handlers.py            (+80-100 lines per handler update)
docs/agent-team/PHASE_6_*.md           (documentation)
```

### Handler Update Pattern

**Current Pattern** (Local Simulation):
```python
def handle_event(self, event: Event) -> bool:
    logger.info(f"[{NAME}] Simulating...")
    # Local logic
    result_event = Event(...)
    self.event_bus.publish(result_event)
```

**New Pattern** (Real Agent):
```python
def handle_event(self, event: Event) -> bool:
    logger.info(f"[{NAME}] Invoking real agent...")
    
    # Invoke real agent
    agent_result = self._invoke_real_agent(event)
    if not agent_result:
        self.event_bus.mark_failed(event.event_id, "Agent invocation failed", self.name)
        return False
    
    # Publish result
    result_event = Event(
        event_type=EventType.TASK_COMPLETED,
        payload=agent_result.to_dict(),
        ...
    )
    self.event_bus.publish(result_event)
    self.event_bus.mark_completed(event.event_id, self.name)
    return True

def _invoke_real_agent(self, event: Event):
    """Call real Claude Code agent"""
    invoker = AgentInvoker()
    return invoker.invoke_agent(
        agent_name=self.name,
        task=self._build_task_prompt(event),
        input_data=event.payload,
        timeout_seconds=120
    )
```

---

## 📊 EFFORT & TIMELINE

| Phase | Effort | Complexity | Duration |
|-------|--------|-----------|----------|
| Phase 1: Bridge | 2 hrs | MEDIUM | 1-2 hrs |
| Phase 2: Architect↔Backend | 2.5 hrs | HIGH | 2-3 hrs |
| Phase 3: Remaining Agents | 2.5 hrs | MEDIUM | 2-3 hrs |
| Phase 4: OpenAI | 1.5 hrs | MEDIUM | 1-2 hrs |
| Phase 5: Pipeline | 1.5 hrs | HIGH | 1-2 hrs |
| Phase 6: Failure Tests | 2 hrs | MEDIUM | 1-2 hrs |
| Phase 7: Security | 1.5 hrs | MEDIUM | 1-2 hrs |
| Phase 8: Documentation | 2 hrs | LOW | 1-2 hrs |
| **TOTAL** | **15.5 hrs** | **MEDIUM-HIGH** | **11-18 hrs** |

**Realistic Timeline**: 1-2 days (depending on agent SDK availability)

---

## ⚠️ CRITICAL UNKNOWNS

### Agent Invocation Mechanism

**Question**: How to invoke Claude Code agents from within Python handlers?

**Options**:
1. **Via Agent Tool** (Most Likely)
   - Use `Agent()` class available in Claude Code environment
   - Handlers run as subagents calling parent agents
   - Pros: Direct, clean
   - Cons: Circular dependency possible

2. **Via Subprocess/CLI**
   - Shell out to `claude` CLI
   - Capture JSON output
   - Pros: Clean separation
   - Cons: Overhead

3. **Via Remote API**
   - Call external endpoint
   - Pros: True microservices
   - Cons: Network dependency, latency

**Recommendation**: Investigate Option 1 first (Agent tool)

---

## 🚦 GO/NO-GO CRITERIA

### Ready to Proceed ✅
- Event Bus fully functional
- Governance complete
- Handlers structured
- Tests pass locally
- No blocking architecture issues

### Not Ready ❌
- Agent invocation mechanism undefined
- OpenAI API credentials missing
- Security review incomplete

**Current Status**: 🟢 **READY WITH CAVEATS**
- Ready to implement if Agent SDK available
- Ready to integrate OpenAI if credentials available

---

## 📝 HANDOFF CHECKLIST

For next implementer:

- [ ] Review PHASE_6_INITIAL_AUDIT.md
- [ ] Review PHASE_6_REAL_AGENT_INTEGRATION_PLAN.md  
- [ ] Confirm Agent invocation mechanism available
- [ ] Confirm OpenAI API credentials available
- [ ] Create event_bus/agent_invocation.py
- [ ] Update handlers incrementally (Phase 2-3)
- [ ] Run tests after each phase
- [ ] Document evidence continuously
- [ ] Create final reports

---

## 📚 KEY DOCUMENTS FOR REFERENCE

```
docs/agent-team/
├── PHASE_6_INITIAL_AUDIT.md              ← Current state
├── PHASE_6_REAL_AGENT_INTEGRATION_PLAN.md ← Detailed spec
├── MISSION_005_2_PHASE_5_1_REVALIDATION_REPORT.md ← What works
├── ETAPA_6_IMPLEMENTATION_ROADMAP.md     ← This document
└── [To be created during implementation]
    ├── PHASE_6_PHASE_1_BRIDGE.md
    ├── PHASE_6_PHASE_2_ARCHITECT_BACKEND.md
    └── ...
```

---

## ✅ READINESS SUMMARY

**ETAPA 6 is ready to begin with the following caveats:**

1. ✅ Architecture is sound
2. ✅ Governance rules are complete
3. ✅ Event Bus is fully functional
4. ⚠️ Agent invocation mechanism needs confirmation
5. ⚠️ OpenAI credentials need setup
6. ⚠️ Handler updates will be significant refactoring

**Recommended Next Session**:
1. Confirm agent invocation mechanism
2. Implement Phase 1 (bridge)
3. Implement Phase 2 (Architect↔Backend real flow)
4. Run first real agent invocation test

**Estimated Completion**: ETAPA 6 fully complete in 15-20 hours of focused work

---

**Last Updated**: 2026-11-22  
**Prepared By**: Claude Haiku 4.5  
**Status**: Ready for handoff to implementation phase

