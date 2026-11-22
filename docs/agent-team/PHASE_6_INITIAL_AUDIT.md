# ETAPA 6 — INITIAL AUDIT
## Real Agent Invocation Mechanisms

**Data**: 2026-11-22  
**Checkpoint**: 0e82313  
**Status**: Pre-implementation audit  
**Objective**: Identify real agent invocation mechanisms available

---

## ✅ State Verification

### Git Status
```
Branch: main
HEAD: 0e82313
Commits ahead: +43
Working tree: Clean
```

### Architecture Review

#### Current Handler Implementation

**File**: `event_bus/agent_handlers.py`

**Handlers Present** (7 total):
1. ArchitectHandler (lines 14-74)
2. BackendDeveloperHandler (lines 77-150)  
3. DebuggerHandler (lines 267-292)
4. QAEngineerHandler (lines 295-320)
5. SecurityAuditorHandler (lines 323-378)
6. ReleaseManagerHandler (lines 351-376)
7. OpenAIValidatorHandler (lines 379-405)

**Current Implementation Type**: Local Python handlers

**Handler Pattern**:
```python
def handle_event(self, event: Event) -> bool:
    logger.info(f"[{NAME}] Processing: {event.event_id}")
    try:
        # Simulated or local execution
        result_event = Event(...)
        self.event_bus.publish(result_event)
        self.event_bus.mark_completed(event.event_id, self.name)
        return True
    except Exception as e:
        logger.error(...)
        return False
```

**Current Limitation**: Each handler is a local Python function simulating agent behavior. Not real agent invocation.

---

## 🔍 REAL AGENT INVOCATION MECHANISMS

### A. Claude Code Agent Invocation

**Available Via**: Claude Code CLI tool (this environment)

**Mechanism**: 
- This IS Claude Code running
- Can spawn subagents with Agent tool (documented in system prompt)
- Agent types available:
  - `fork` — Forks self (inherits context)
  - `general-purpose` — General purpose agent
  - `code-review` — Code review specialist
  - `systematic-debugging` — Debugging agent
  - Other specialized agents listed in system prompt

**How to Invoke**:
```python
# Within event handler:
from agent_sdk import Agent  # Or equivalent import

agent = Agent(
    agent_type="general-purpose",  # or specific type
    prompt="Task description and requirements",
    input_data={...},
    timeout=120
)

result = agent.execute()  # Returns agent result
```

**Limitation**: 
- Agent tool is available to me (Claude), not easily callable from arbitrary Python
- Would need wrapper in event bus to bridge to Claude Code infrastructure

### B. OpenAI API Integration

**Currently Implemented**: Yes, in OpenAIValidatorHandler

**File**: `event_bus/agent_handlers.py:379-405`

**Mechanism**:
```python
# OpenAI client usage pattern
from openai import OpenAI
client = OpenAI(api_key=...)
response = client.chat.completions.create(...)
```

**Status**: Structure exists, needs real API credentials and calls

---

## 📊 PARTICIPANT INVOCATION MATRIX

| Participant | Handler | Invocation Type | Real? | Evidence |
|-------------|---------|-----------------|-------|----------|
| Architect | Yes (line 14) | Local Python | No | Simulates evaluation |
| Backend | Yes (line 77) | Local Python | No | Simulates execution |
| Debugger | Yes (line 267) | Local Python | No | Simulates analysis |
| QA | Yes (line 295) | Local Python | No | Simulates testing |
| Security | Yes (line 323) | Local Python + Severity logic | Partial | Has real severity classification |
| Release Manager | Yes (line 351) | Local Python | No | Decision engine only |
| OpenAI Validator | Yes (line 379) | API ready | Partial | Structure exists, needs credentials |

---

## 🛠️ IMPLEMENTATION STRATEGY FOR ETAPA 6

### Option A: Wrapper Layer (Recommended)

Create `event_bus/agent_invocation.py`:
```python
class AgentInvoker:
    """Bridges event handlers to real agent invocation"""
    
    async def invoke_architect(self, event: Event):
        """Invoke real Architect agent"""
        # Use Agent tool or CLI mechanism
        
    async def invoke_backend(self, event: Event):
        """Invoke real Backend agent"""
        
    # etc.
```

**Pros**: 
- Clean separation of concerns
- Can scale to multiple agent types
- Preserves existing handler structure

**Cons**:
- Requires async support
- Complexity increase

### Option B: Direct Handler Enhancement

Update handlers in-place with real invocation:
```python
class ArchitectHandler:
    def handle_event(self, event: Event) -> bool:
        # Instead of local simulation:
        # Call real Claude Code agent
        result = self._invoke_real_agent(event)
```

**Pros**:
- Minimal architecture changes
- Direct evidence in handlers

**Cons**:
- Handlers become more complex
- Harder to test

### Option C: Hybrid (Local Simulation + Real for Proof)

Keep local handlers for unit testing.
Add real invocation path for ETAPA 6 proof.

**Recommended for**: This phase (ETAPA 6)

---

## 🔐 SECURITY CONSIDERATIONS

### Agent Invocation Security

1. **Input Validation**
   - Only pass necessary data to agents
   - Scrub credentials/secrets
   - Validate event schema

2. **Output Validation**
   - Verify agent response schema
   - Catch malformed responses
   - Log all external API calls

3. **Isolation**
   - Each agent execution isolated
   - No shared state between agents
   - Clear role boundaries

4. **OpenAI API Security**
   - API key in environment variable only
   - Never log API keys
   - Use least-privilege API key
   - Monitor usage/costs

---

## 📋 DISCOVERY QUESTIONS FOR ETAPA 6

1. **Claude Code Agent Invocation**
   - Can Agent tool be called from within Python handlers?
   - What's the execution model (synchronous/async)?
   - How are results returned?
   - What timeout/retry mechanisms exist?

2. **OpenAI Validator**
   - Is API key available in environment?
   - Which model to use (gpt-4o, gpt-4-turbo)?
   - What's the cost/token budget?
   - Should responses be cached?

3. **Local vs. Remote Execution**
   - Should agents run locally (Python subprocess)?
   - Should agents run remotely (via API)?
   - How to track execution IDs?

4. **Synchronization**
   - Should handler await agent result?
   - Should agent result be published as event?
   - How to handle agent timeouts?

---

## ✅ READINESS ASSESSMENT

| Requirement | Status | Notes |
|-------------|--------|-------|
| Event Bus | ✅ Ready | Full implementation |
| Dispatcher | ✅ Ready | Routing complete |
| Governance | ✅ Ready | 8/8 rules functional |
| Handlers | ⚠️ Partial | Local implementation, need real agents |
| OpenAI Integration | ⚠️ Partial | Structure ready, need credentials/calls |
| Testing | ⚠️ Partial | Unit tests exist, need E2E with real agents |

---

## 🎯 NEXT STEPS FOR ETAPA 6.1

1. **Identify Agent Invocation Mechanism**
   - Determine if Agent tool can be called from Python
   - Or implement subprocess/CLI wrapper
   - Or use remote API endpoint

2. **Create Agent Invocation Bridge**
   - Implement wrapper in `event_bus/agent_invocation.py`
   - Define contracts for each agent
   - Add error handling

3. **Update Architect Handler**
   - Replace local simulation with real agent call
   - Verify agent invocation happens
   - Confirm result event published

4. **Document Evidence**
   - Log agent ID
   - Log execution ID
   - Log correlation chain
   - Capture timing/costs

---

**STATUS**: 🟡 **AUDIT COMPLETE — READY FOR IMPLEMENTATION**

**Blocking Issues**: None - can proceed with current information

**Unknowns**: Agent invocation mechanism (to be determined in Phase 1)

