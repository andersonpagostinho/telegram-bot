# ETAPA 6 — REAL AGENT INTEGRATION PLAN
## Claude Code Agents + OpenAI Validator

**Data**: 2026-11-22  
**Checkpoint**: 7dc9e98 (ETAPA 5.1 Complete)  
**Status**: Planning phase  
**Scope**: Design real invocation mechanisms for ETAPA 6 implementation

---

## EXECUTIVE SUMMARY

ETAPA 6 upgrades the event-driven pipeline from local Python handlers to real external agent invocations:

- **Architect**: Claude Code Agent (via Agent.invoke() with structured task)
- **Backend**: Claude Code Agent (via Agent.invoke() with implementation request)
- **Debugger**: Claude Code Agent (via Agent.invoke() with debugging request)
- **QA**: Claude Code Agent (via Agent.invoke() with test request)
- **Security**: Claude Code Agent (via Agent.invoke() with security audit request)
- **Release**: Python handler (local decision engine, no external invoke)
- **OpenAI Validator**: Real OpenAI API call (not Claude)

---

## PARTICIPANT INVOCATION MATRIX

### 1. ARCHITECT AGENT

**Type**: Claude Code Agent (Real)

**Current Implementation**: Local Python handler  
**Handler File**: `event_bus/agent_handlers.py:14-74`

**What to Change**:
```python
# FROM: Local simulation
result_data = event.payload.get("result", {})
logger.info(f"[ARCHITECT] Evaluating result for task {task_id}")

# TO: Real Claude Code Agent
from event_bus.agent_sdk import invoke_claude_code_agent

agent_result = invoke_claude_code_agent(
    agent_name="architect",
    task="Evaluate task completion and decide approval/rejection",
    input_data={
        "task_id": task_id,
        "mission_id": mission_id,
        "result": event.payload.get("result", {}),
        "requirements": event.payload.get("requirements", ""),
    },
    timeout_seconds=60
)
```

**Input Contract**:
- task_id: str
- mission_id: str  
- result: dict (task execution result)
- requirements: str (original requirements)

**Output Contract**:
- evaluation: str ("APPROVED", "REJECTED", "NEEDS_REVIEW")
- notes: str (reasoning)
- requires_security_review: bool
- requires_qa_validation: bool

**Success Criteria**:
- Agent invoked within timeout
- Returns valid evaluation
- Notes explain reasoning

**Error Handling**:
- Timeout → event marked FAILED, retry flag set
- Invalid response → event marked FAILED
- No auto-fallback to local handler

---

### 2. BACKEND DEVELOPER AGENT

**Type**: Claude Code Agent (Real)

**Current Implementation**: Local Python handler  
**Handler File**: `event_bus/agent_handlers.py:77-150`

**What to Change**:
```python
# FROM: Simulated execution
execution_result = self._execute_task(task_desc)

# TO: Real Claude Code Agent
from event_bus.agent_sdk import invoke_claude_code_agent

agent_result = invoke_claude_code_agent(
    agent_name="backend",
    task="Implement feature and commit code",
    input_data={
        "task_id": task_id,
        "mission_id": mission_id,
        "description": task_desc,
        "requirements": event.payload.get("requirements", ""),
        "acceptance_criteria": event.payload.get("acceptance_criteria", ""),
    },
    timeout_seconds=180,  # Longer timeout for code work
    allow_git=True,  # Allow git commits
    allow_test_execution=True,  # Allow running tests
)
```

**Input Contract**:
- task_id: str
- mission_id: str
- description: str (what to build)
- requirements: str (technical requirements)
- acceptance_criteria: str (what success looks like)

**Output Contract**:
- status: str ("COMPLETED", "FAILED", "PARTIAL")
- result: dict
  - files_modified: int
  - tests_added: int
  - tests_passed: int
  - tests_failed: int
  - commits: list[str] (commit hashes)
  - error: str (if FAILED)

**Success Criteria**:
- Agent invoked correctly
- Commits are made to repo
- Tests run and report results
- No destructive changes to main code

**Error Handling**:
- Timeout → partial work saved, event marked FAILED
- Failing tests → event marked FAILED with test results
- Git errors → event marked FAILED with error message

---

### 3. DEBUGGER AGENT

**Type**: Claude Code Agent (Real)

**Current Implementation**: Local Python handler  
**Handler File**: `event_bus/agent_handlers.py:267-292`

**What to Change**:
```python
from event_bus.agent_sdk import invoke_claude_code_agent

agent_result = invoke_claude_code_agent(
    agent_name="debugger",
    task="Investigate issue and identify root cause",
    input_data={
        "issue_description": event.payload.get("issue", ""),
        "error_logs": event.payload.get("error_logs", ""),
        "context": event.payload.get("context", ""),
        "files_to_check": event.payload.get("files", []),
    },
    timeout_seconds=120,
)
```

**Input Contract**:
- issue_description: str
- error_logs: str
- context: str (what was happening)
- files_to_check: list[str] (file paths)

**Output Contract**:
- root_cause: str (explanation)
- affected_files: list[str]
- suggested_fix: str
- confidence: str ("HIGH", "MEDIUM", "LOW")

---

### 4. QA ENGINEER AGENT

**Type**: Claude Code Agent (Real)

**Current Implementation**: Local Python handler  
**Handler File**: `event_bus/agent_handlers.py:295-320`

**What to Change**:
```python
agent_result = invoke_claude_code_agent(
    agent_name="qa",
    task="Test implementation against requirements",
    input_data={
        "code_location": event.payload.get("commits", []),
        "requirements": event.payload.get("requirements", ""),
        "acceptance_criteria": event.payload.get("acceptance_criteria", ""),
        "test_plan": event.payload.get("test_plan", ""),
    },
    timeout_seconds=180,
    allow_test_execution=True,
)
```

**Input Contract**:
- code_location: list[str] (commit hashes or branches)
- requirements: str
- acceptance_criteria: str
- test_plan: str (optional)

**Output Contract**:
- qa_decision: str ("APPROVED", "REJECTED")
- tests_total: int
- tests_passed: int
- tests_failed: int
- failures: list[dict] (if any)
  - test_name: str
  - error: str
  - expected: str
  - actual: str

---

### 5. SECURITY AUDITOR AGENT

**Type**: Claude Code Agent (Real)

**Current Implementation**: Local Python handler with severity logic  
**Handler File**: `event_bus/agent_handlers.py:323-378`

**What to Change**:
```python
agent_result = invoke_claude_code_agent(
    agent_name="security",
    task="Conduct security audit",
    input_data={
        "code_location": event.payload.get("commits", []),
        "code_summary": event.payload.get("code_summary", ""),
        "dependencies": event.payload.get("dependencies", []),
        "sensitive_data_handling": event.payload.get("sensitive_data", False),
    },
    timeout_seconds=120,
    allow_code_scan=True,
)
```

**Input Contract**:
- code_location: list[str]
- code_summary: str
- dependencies: list[dict]
- sensitive_data_handling: bool

**Output Contract**:
- security_decision: str ("APPROVED", "REJECTED")
- severity: str ("CRITICAL", "HIGH", "MEDIUM", "LOW")
- findings: list[dict]
  - issue: str
  - severity: str
  - affected_code: str
  - remediation: str

---

### 6. RELEASE MANAGER

**Type**: Local Python Handler (No External Invoke)

**Why**: Release Manager is orchestrator/decision engine, not executor.

**Current Implementation**: OK as-is  
**Handler File**: `event_bus/agent_handlers.py:351-376`

**Decision Logic**:
- Check QA_APPROVED from upstream
- Check SECURITY_APPROVED from upstream  
- Check VALIDATOR_APPROVED from upstream
- If all true: publish RELEASE_PROPOSED with status=READY_FOR_DEPLOYMENT
- Note: READY does not authorize actual deployment

**No Changes Needed** ✅

---

### 7. OPENAI VALIDATOR

**Type**: External API (Real OpenAI)

**Current Implementation**: Local Python handler  
**Handler File**: `event_bus/agent_handlers.py:379-405`

**What to Change**:
```python
from openai import OpenAI  # Official OpenAI SDK

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In handle_event():
response = openai_client.chat.completions.create(
    model="gpt-4o",  # Latest model for best analysis
    messages=[
        {
            "role": "system",
            "content": "You are an expert architecture reviewer. Analyze the provided architecture and validate it against best practices."
        },
        {
            "role": "user", 
            "content": f"""
Review the following architecture:

Code Summary: {event.payload.get('code_summary', '')}
Design: {event.payload.get('architecture_to_validate', '')}
Constraints: {event.payload.get('constraints', '')}

Provide:
1. Is this architecture sound? (yes/no)
2. Major concerns (if any)
3. Recommended improvements
4. Risk level: HIGH/MEDIUM/LOW
            """
        }
    ],
    temperature=0.7,
    max_tokens=1000,
    timeout=30  # Timeout protection
)

validation_text = response.choices[0].message.content
# Parse response into structured format
```

**Input Contract**:
- code_summary: str
- architecture_to_validate: dict
- constraints: str (operational constraints)

**Output Contract**:
- validation: str ("PASSED", "FAILED", "NEEDS_REVIEW")
- architecture_valid: bool
- concerns: list[str]
- risk_level: str ("HIGH", "MEDIUM", "LOW")
- reasoning: str

**API Integration Details**:
- Model: gpt-4o (latest)
- Temperature: 0.7 (balanced analysis)
- Timeout: 30 seconds
- Max tokens: 1000
- Retry policy: 2 retries on timeout
- Cost: ~$0.01 per call (estimate)

**Error Handling**:
- API error → event marked FAILED, no auto-fallback
- Timeout after retries → event marked FAILED
- Invalid response format → event marked FAILED
- Rate limit → exponential backoff, up to 3 retries

---

## INVOCATION EVIDENCE & VALIDATION

For each participant, document:

### A. Handler Python Execution

```
Validation: Check event_store for handler completion
Evidence: event.status = COMPLETED and event.processed_by = handler_name
Verification: Real Python handler was invoked and completed
```

### B. Claude Code Agent Invocation

```
Validation: Check event_bus for agent result event published
Evidence: 
  - event.agent_id = agent_name
  - event.payload contains agent_result fields
  - event.causation_id = original event.event_id
Verification: Real Claude agent was invoked and completed successfully
```

### C. OpenAI API Invocation

```
Validation: Check OpenAI usage logs (via API dashboard)
Evidence:
  - API call logged with model, tokens, timestamp
  - Response received with valid completion
  - Cost charged to account
Verification: Real OpenAI API was called successfully
```

---

## EXECUTION FLOW FOR ETAPA 6

```
Architect publishes TASK_ASSIGNED
  ↓
Backend receives TASK_ASSIGNED
  → Invokes Claude Code Agent (invoke_claude_code_agent)
  → Agent commits code, runs tests
  → Publishes TASK_COMPLETED with results
  ↓
QA receives TASK_COMPLETED
  → Invokes Claude Code Agent (invoke_claude_code_agent)
  → Agent runs acceptance tests
  → Publishes REVIEW_APPROVED or REVIEW_REJECTED
  ↓ (if approved)
Security receives REVIEW_APPROVED
  → Invokes Claude Code Agent (invoke_claude_code_agent)
  → Agent audits code for vulnerabilities
  → Publishes REVIEW_APPROVED/REJECTED with severity
  ↓ (if approved)
OpenAI Validator receives REVIEW_APPROVED
  → Calls OpenAI API (gpt-4o)
  → Receives architecture analysis
  → Publishes REVIEW_APPROVED/REJECTED
  ↓ (if all approved)
Release Manager receives all approvals
  → Publishes RELEASE_PROPOSED with status=READY_FOR_DEPLOYMENT
  → NO automatic deployment happens (requires explicit authorization)
```

---

## RESOURCE & COST ESTIMATES

| Participant | Type | Invocation Cost | Per-Call Estimate |
|-------------|------|-----------------|-------------------|
| Architect | Claude Agent | Included | Varies |
| Backend | Claude Agent | Included | Varies |
| Debugger | Claude Agent | Included | Varies |
| QA | Claude Code Agent | Included | Varies |
| Security | Claude Code Agent | Included | Varies |
| Release | Local Handler | None | $0 |
| Validator | OpenAI API | Direct | ~$0.01 |

---

## ETAPA 6 IMPLEMENTATION STEPS

### Phase 1: Agent SDK Integration (Day 1)
- [ ] Create `event_bus/agent_sdk.py` wrapper
- [ ] Implement `invoke_claude_code_agent()` function
- [ ] Handle timeouts, retries, error cases

### Phase 2: OpenAI Integration (Day 1)
- [ ] Add OpenAI SDK to requirements
- [ ] Configure API credentials
- [ ] Implement OpenAI validator wrapper

### Phase 3: Handler Updates (Day 2)
- [ ] Update Architect handler
- [ ] Update Backend handler
- [ ] Update QA handler
- [ ] Update Security handler
- [ ] Update Debugger handler
- [ ] Keep Release Manager as-is

### Phase 4: Integration Testing (Day 2)
- [ ] Test Architect → Backend flow
- [ ] Test full pipeline with approvals
- [ ] Test security rejection blocking
- [ ] Test OpenAI timeout handling
- [ ] Test agent error recovery

### Phase 5: Documentation (Day 3)
- [ ] Document agent invocation contracts
- [ ] Create troubleshooting guide
- [ ] Document cost/quota management

---

## SUCCESS CRITERIA FOR ETAPA 6

- ✅ Architect Agent invoked and returns evaluation
- ✅ Backend Agent invoked and commits code
- ✅ QA Agent invoked and reports test results
- ✅ Security Agent invoked and identifies findings
- ✅ Debugger Agent invoked for root cause analysis
- ✅ OpenAI Validator invoked and validates architecture
- ✅ Full pipeline executes with real agents
- ✅ All governance rules still enforced
- ✅ Audit trail complete with agent invocation evidence
- ✅ Cost tracking enabled for OpenAI calls

---

**STATUS**: 🟢 **PLAN READY FOR IMPLEMENTATION**

