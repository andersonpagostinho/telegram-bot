# ETAPA 5.1 — REMEDIATION AUDIT
## Detailed Analysis of Three Issues

**Data**: 2026-11-22  
**Checkpoint**: d18c804  
**Status**: Pre-remediation audit  

---

## ✅ State Verification

### Git Status
```
Branch: main
HEAD: d18c804
Commits ahead: +39
Working tree: Clean (only .claude/worktrees/)
```

### Previous Commits Preserved (Last 5)
```
d18c804 — ETAPA 5: Comprehensive E2E Validation Report
320b54f — ETAPA 5: E2E Scenarios Test Suite and Initial Audit
1ea4126 — ETAPA 4: Cinco Handlers Implementados
67846d4 — ETAPA 3: Governança Implementada
deaf143 — Plano Execução ETAPAS 3-6
```

---

## 🔍 ISSUE P5.1 — RELEASE MANAGER ROUTING

### Location
`event_bus/dispatcher.py:56-61`

### Current Code
```python
self.routing_rules = {
    EventType.TASK_ASSIGNED: [AgentRole.BACKEND, AgentRole.DEBUGGER, AgentRole.QA],
    EventType.REVIEW_REQUESTED: [AgentRole.SECURITY, AgentRole.QA],
    EventType.VALIDATION_REQUESTED: [AgentRole.VALIDATOR],
    EventType.MISSION_CREATED: [AgentRole.ARCHITECT],
}
```

### Problem
Line 58: `REVIEW_REQUESTED` can be routed to `[SECURITY, QA]` only. Missing `RELEASE`.

Release Manager is registered (handlers.py:351) but cannot receive REVIEW_REQUESTED events.

### Impact
- Scenario 1 (Happy Path) fails at STEP 6
- Release Manager never gets invoked
- Pipeline cannot complete

### Root Cause
When Validator publishes REVIEW_APPROVED/REJECTED, it's a REVIEW_REQUESTED type event that should go to Release Manager, but dispatcher blocks it.

### Fix Required
Add `AgentRole.RELEASE` to REVIEW_REQUESTED authorized agents:

```python
EventType.REVIEW_REQUESTED: [AgentRole.SECURITY, AgentRole.QA, AgentRole.RELEASE],
```

### Validation Plan
1. Apply fix
2. Re-run Scenario 1
3. Verify Release Manager receives event
4. Verify READY status published

### Effort
1 line change, 0 logic changes

---

## 🔍 ISSUE P5.2 — EVENT CORRELATION RETRIEVAL

### Location
`event_bus/event_store.py` — missing method

### Current State
EventStore has three query methods:

1. **`get_event(event_id: str)`** (line 160)
   - Retrieves single event by ID
   - Used by: individual lookups only

2. **`get_pending_events(mission_id: str, limit: int)`** (line 184)
   - Retrieves PENDING status events for mission
   - Used by: event consumer polling
   - **Limitation**: No correlation_id filter

3. **`get_history(mission_id: str, limit: int)`** (line 253)
   - Retrieves all events for mission (all statuses)
   - Used by: audit and test verification
   - **Limitation**: No correlation_id or causation_id filter
   - **Limitation**: Scoped to single mission only

### Problem
Test scenarios need to retrieve **entire correlation chain** across events:

```
Architect publishes TASK_ASSIGNED (correlation_id: "abc123")
  ↓
Backend publishes TASK_COMPLETED (correlation_id: "abc123", causation_id: evt1)
  ↓
QA publishes REVIEW_REQUESTED (correlation_id: "abc123", causation_id: evt2)
  ↓
(etc.)
```

**Missing**: Query method that accepts `correlation_id` and returns all linked events in order

### Impact
- Scenario 6 (Duplicate Event) — Cannot verify chain
- Scenario 7 (Recovery) — Cannot verify correlation maintained
- Audit verification blocked

### Root Cause
Event query API was designed for mission-scoped operations, not correlation-based tracing.

### Fix Required

Add method to EventStore:

```python
def get_events_by_correlation(self, correlation_id: str) -> List[Event]:
    """
    Retrieve all events with given correlation_id across all missions.
    
    Returns events in chronological order (by created_at).
    
    Args:
        correlation_id: Correlation ID to match
        
    Returns:
        List of events, ordered by created_at ASC
    """
    with self._lock:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM events
                    WHERE correlation_id = ?
                    ORDER BY created_at ASC
                """, (correlation_id,))
                
                return [self._row_to_event(row) for row in cursor.fetchall()]
        except Exception as e:
            raise PersistenceException(f"Failed to get events by correlation: {e}")
```

### Additional Method (Optional but Recommended)

Also add method for causation-based queries:

```python
def get_causation_chain(self, root_event_id: str) -> List[Event]:
    """
    Retrieve causal chain starting from root_event_id.
    
    Follows causation_id links to build full dependency chain.
    
    Args:
        root_event_id: Starting event ID
        
    Returns:
        List of events in dependency order
    """
    chain = []
    with self._lock:
        current_id = root_event_id
        seen = set()
        
        while current_id and current_id not in seen:
            seen.add(current_id)
            event = self.get_event(current_id)
            if not event:
                break
            chain.append(event)
            current_id = event.causation_id
            
    return chain
```

### Test Updates

Update test helpers:
```python
def _get_events_by_correlation(self, store, correlation_id: str) -> List[Event]:
    """Helper to get all events in correlation chain"""
    return store.get_events_by_correlation(correlation_id)  # Direct call, no filtering
```

Remove mission_id parameter from calls.

### Validation Plan
1. Add method to EventStore
2. Update test helpers
3. Re-run Scenario 6
4. Re-run Scenario 7
5. Verify full chains retrieved

### Effort
15-20 lines for correlation method + 15 lines for causation method (optional)

---

## 🔍 ISSUE P5.3 — SECURITY SEVERITY INTEGRATION

### Location
Multiple files:
- `event_bus/governance.py:_rule_security_veto()` (line ~95)
- `event_bus/dispatcher.py:dispatch()` (line ~69)
- `event_bus/agent_handlers.py:SecurityAuditorHandler` (line ~323)

### Current State

**SecurityAuditorHandler** (line 329):
```python
def handle_event(self, event: Event) -> bool:
    logger.info(f"[SECURITY] Auditing: {event.event_id}")
    try:
        result_event = Event(
            event_type=EventType.REVIEW_APPROVED,
            payload={"evidence": {"vulnerabilities": 0}, "security_decision": "APPROVED"},
            ...
        )
        self.event_bus.publish(result_event)
        return True
```

**Problem 1**: Security handler ALWAYS publishes REVIEW_APPROVED, never checks severity.

**GovernanceEngine** (line ~95):
```python
def _rule_security_veto(self, event: Event, target_agent: str) -> GovernanceDecision:
    """Rule 3: Security veto power"""
    # Checks if Security rejected
    # Does NOT check severity level
```

**Problem 2**: Governance evaluates rejection but doesn't use severity classification.

**Dispatcher** (line ~69):
```python
def dispatch(self, event: Event, target_agent: AgentRole) -> bool:
    # Validate authorization
    if not self._is_authorized(event.event_type, target_agent):
        logger.warning(...)
        return False
    
    # NO GOVERNANCE CHECK before dispatch
    # NO SEVERITY CHECK
```

**Problem 3**: Dispatcher doesn't consult governance on severity before routing to downstream.

### Business Rule
```
CRITICAL severity → Block immediately (veto)
HIGH severity → Block until human authorization
MEDIUM severity → Log but allow (manager decides)
LOW severity → Log only
UNKNOWN/MISSING → Do not auto-approve
```

### Fix Required

**Step 1**: Update SecurityAuditorHandler to include severity

```python
def handle_event(self, event: Event) -> bool:
    logger.info(f"[SECURITY] Auditing: {event.event_id}")
    try:
        # Determine severity based on findings
        severity = self._determine_severity(event.payload)
        
        # Always report findings, decision depends on severity
        result_event = Event(
            event_type=EventType.REVIEW_APPROVED if severity not in ["CRITICAL", "HIGH"] else EventType.REVIEW_REJECTED,
            payload={
                "evidence": {"vulnerabilities": 2, "severity": severity},
                "security_decision": "APPROVED" if severity not in ["CRITICAL", "HIGH"] else "REJECTED",
                "reason": f"Security finding: {severity}",
            },
            ...
        )
        self.event_bus.publish(result_event)
        return True
```

**Step 2**: Update GovernanceEngine to check severity

```python
def _rule_security_veto(self, event: Event, target_agent: str) -> GovernanceDecision:
    """Rule 3: Security veto power"""
    
    # Check if Security explicitly rejected
    if event.event_type == EventType.REVIEW_REJECTED and event.agent_id == "security":
        severity = event.payload.get("severity", "UNKNOWN")
        
        if severity == "CRITICAL":
            return GovernanceDecision(
                allowed=False,
                reason=f"Security veto: CRITICAL vulnerability found",
                rule_id=3
            )
        elif severity == "HIGH":
            return GovernanceDecision(
                allowed=False,
                reason=f"Security veto: HIGH severity issue requires authorization",
                rule_id=3
            )
    
    return GovernanceDecision(allowed=True, rule_id=3)
```

**Step 3**: Update Dispatcher to check governance

```python
def dispatch(self, event: Event, target_agent: AgentRole) -> bool:
    # Validate authorization
    if not self._is_authorized(event.event_type, target_agent):
        logger.warning(...)
        return False
    
    # NEW: Check governance rules
    if self.governance:
        decision = self.governance.evaluate(event, target_agent.value, "receive")
        if not decision.allowed:
            logger.warning(f"Governance blocked: {decision.reason}")
            return False
    
    # Rest of dispatch logic...
```

### Validation Plan
1. Update SecurityAuditorHandler with severity determination
2. Update GovernanceEngine._rule_security_veto()
3. Update Dispatcher.dispatch() to check governance
4. Create test for each severity level (CRITICAL, HIGH, MEDIUM, LOW)
5. Re-run Scenario 3 (Security Blocks)
6. Re-run governance tests (Rule 3: Security Veto)

### Effort
20-30 lines for severity determination + 15 lines governance update + 10 lines dispatcher integration

---

## 📋 FILES TO MODIFY

| File | Issue | Lines | Type |
|------|-------|-------|------|
| dispatcher.py | P5.1 | 1 | Add RELEASE to routing |
| event_store.py | P5.2 | 15 | Add correlation query |
| handlers.py | P5.3 | 20 | Add severity logic |
| governance.py | P5.3 | 15 | Add severity check |
| dispatcher.py | P5.3 | 10 | Add governance check |
| test_phase_5_e2e_scenarios.py | P5.2 | 5 | Update helpers |

**Total Estimated Lines**: 70-80 lines of new/changed code

---

## ✅ REMEDIATION ORDER

1. **P5.1 First** (easiest, unblocks Scenario 1)
   - 1 line change
   - Instant validation
   - No side effects

2. **P5.2 Second** (most essential, unblocks Scenario 6, 7)
   - Add event_store methods
   - Update test helpers
   - Required for correlation verification

3. **P5.3 Third** (most complex, completes governance)
   - Update handler logic
   - Update governance rules
   - Update dispatcher integration
   - Required for complete security veto

---

## 📊 SUCCESS CRITERIA

After remediation:
- ✅ All 7 scenarios PASS or document legitimate blockers
- ✅ No false PASS declarations
- ✅ Full correlation chains retrievable
- ✅ Security severity blocking working
- ✅ All 8 governance rules functional
- ✅ All 9 governance tests PASS
- ✅ Commits clear and scoped

---

**STATUS**: 🟢 **AUDIT COMPLETE — READY FOR REMEDIATION**

