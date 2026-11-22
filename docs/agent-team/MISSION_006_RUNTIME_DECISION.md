# MISSÃO 006 — RUNTIME DECISION
## Chosen: Anthropic SDK beta.agents

**Data**: 2026-11-22  
**Decision**: ANTHROPIC SDK BETA.AGENTS

---

## 🎯 RUNTIME CHOSEN

**Anthropic SDK 0.105.2 `beta.agents`**

### Rationale

| Criterion | Anthropic SDK | Claude CLI |
|-----------|---------------|-----------|
| Official Support | ✅ First-party | ⚠️ CLI-based |
| Integration | ✅ Direct Python | ⚠️ Subprocess |
| Performance | ✅ Native API | ⚠️ Process overhead |
| Security | ✅ SDK managed | ⚠️ Process isolation |
| Maintenance | ✅ Official updates | ⚠️ CLI version tracking |
| Cost Control | ✅ Token counting | ✅ Token counting |
| Complexity | ✅ Lower | ⚠️ Higher |

**Decision**: Anthropic SDK is official, performant, and maintains full integration with Event Bus.

---

## 🏗️ ARCHITECTURE

```
Event Bus (SQLite)
    ↓
Dispatcher (routing)
    ↓
Governance Engine (authorization)
    ↓
Agent Invocation Bridge (new)
    ↓
Anthropic SDK (client.beta.agents)
    ↓
Claude Agent Runtime
    ↓
Agent Execution
    ↓
Structured Result
    ↓
Event Bus (publication)
```

---

## 🛠️ IMPLEMENTATION PLAN

**File**: `event_bus/agent_invocation_bridge.py`

**Core Class**:
```python
class AgentInvocationBridge:
    def __init__(self, event_bus, dispatcher, governance):
        self.event_bus = event_bus
        self.dispatcher = dispatcher
        self.governance = governance
        self.anthropic_client = Anthropic()
        self.agent_configs = {}
    
    async def invoke_agent(self, event: Event, target_agent: AgentRole) -> dict:
        """Invoke agent via Anthropic SDK"""
        # Validate, authorize, execute
        pass
```

**Key Methods**:
- `invoke_agent()` — Main invocation
- `_validate_target()` — Verify agent exists
- `_check_governance()` — Consult Governance Engine
- `_prepare_context()` — Build task context
- `_execute_via_sdk()` — Call Anthropic API
- `_capture_result()` — Parse structured output
- `_publish_result()` — Post to Event Bus
- `_handle_failure()` — Error management

---

## ✅ ADVANTAGES

1. **Official Support** — Part of Anthropic's public SDK
2. **Native Integration** — No subprocess overhead
3. **Cost Tracking** — Token usage directly visible
4. **Security** — SDK handles authentication
5. **Performance** — Direct API calls
6. **Maintenance** — Follows SDK updates

---

## ⚠️ CONSTRAINTS

1. **Authentication Required** — Must have ANTHROPIC_API_KEY
2. **API Rate Limits** — Anthropic API quotas apply
3. **Cost** — API calls incur charges
4. **Beta Status** — API may evolve

---

## 📌 NEXT STEPS

1. ETAPA 3: Implement Agent Invocation Bridge
2. ETAPA 4: Invoke Backend agent (structural, no auth)
3. ETAPA 5: Enable auth and test real invocation
4. Continue: Remaining agents

---

**STATUS**: 🟢 **RUNTIME DECISION MADE**

