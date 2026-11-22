# Task and Event Contract Specification

**Version**: 1.0  
**Author**: ARCHITECT Agent  
**Date**: 2026-11-21  
**Purpose**: Standardized contract for task delegation and event production in multi-agent workflow

---

## 1. Task Contract

### 1.1 — Task Definition (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NeoEve Task",
  "type": "object",
  "required": [
    "task_id",
    "mission_id",
    "assigned_agent",
    "objective",
    "status",
    "created_at"
  ],
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^task-[0-9]{3}-[a-z]-[0-9]{3}$",
      "description": "Unique task identifier (task-MISSION-SEQUENCE-ITEM)"
    },
    "mission_id": {
      "type": "string",
      "pattern": "^mission-[0-9]{3}-[a-z]$",
      "description": "Parent mission identifier"
    },
    "assigned_agent": {
      "type": "string",
      "enum": [
        "architect",
        "backend-developer",
        "debugger",
        "qa-engineer",
        "security-auditor",
        "release-manager",
        "UNASSIGNED"
      ],
      "description": "Target agent for this task"
    },
    "objective": {
      "type": "string",
      "minLength": 10,
      "maxLength": 500,
      "description": "What needs to be done (clear, specific, measurable)"
    },
    "context": {
      "type": "object",
      "properties": {
        "files_in_scope": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Files this task can/should modify"
        },
        "architecture_contracts": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "MULTI_TENANT_ISOLATION",
              "NO_FUNCTIONAL_REMOVAL",
              "IDEMPOTENCY",
              "GPT_BOUNDARIES",
              "DETERMINISTIC_ENGINE"
            ]
          },
          "description": "Architectural constraints to respect"
        },
        "technical_details": {
          "type": "object",
          "description": "Additional context (root cause, approach, etc)"
        }
      }
    },
    "dependencies": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "task_id": { "type": "string" },
          "required_status": {
            "type": "string",
            "enum": ["COMPLETED", "APPROVED"]
          }
        }
      },
      "description": "Tasks that must complete before this starts"
    },
    "acceptance_criteria": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1,
      "description": "Objective, measurable conditions for task success"
    },
    "risk_level": {
      "type": "string",
      "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
      "description": "Risk assessment"
    },
    "evidence_required": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "git_diff",
          "git_commit",
          "pytest_output",
          "test_summary",
          "security_audit",
          "architecture_analysis",
          "code_review",
          "deployment_logs"
        ]
      },
      "description": "Evidence types that MUST be provided for completion"
    },
    "status": {
      "type": "string",
      "enum": [
        "PENDING",
        "ASSIGNED",
        "IN_PROGRESS",
        "BLOCKED",
        "REVIEW",
        "APPROVED",
        "REJECTED",
        "COMPLETED"
      ],
      "description": "Current state of task"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "When task was created"
    },
    "assigned_at": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "started_at": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "completed_at": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "rejected_reason": {
      "type": ["string", "null"],
      "description": "If REJECTED, why"
    },
    "blocked_by": {
      "type": ["string", "null"],
      "description": "If BLOCKED, what (or who) is blocking"
    }
  }
}
```

### 1.2 — Task Lifecycle

```
┌──────────┐
│ PENDING  │ ← Created by ARCHITECT, awaiting assignment
└────┬─────┘
     │
     ├─→ ASSIGNED (agent acknowledged)
     │
     ├─→ IN_PROGRESS (agent started work)
     │   ├─→ BLOCKED (waiting for blocker resolution)
     │   │   └─→ IN_PROGRESS (blocker resolved)
     │   │
     │   └─→ REVIEW (work complete, sending for validation)
     │       ├─→ APPROVED (validador confirmed)
     │       │   └─→ COMPLETED (integrated into system)
     │       │
     │       └─→ REJECTED (not approved, reason given)
     │           └─→ ASSIGNED (restarted with feedback)
     │
     └─→ REJECTED (from PENDING, e.g., violates contract)
```

### 1.3 — Valid Transitions

```
PENDING      → ASSIGNED | REJECTED
ASSIGNED     → IN_PROGRESS | BLOCKED
IN_PROGRESS  → BLOCKED | REVIEW
BLOCKED      → IN_PROGRESS
REVIEW       → APPROVED | REJECTED
APPROVED     → COMPLETED
REJECTED     → ASSIGNED
COMPLETED    ✓ Terminal state
```

### 1.4 — Example Task

```json
{
  "task_id": "task-002-a-001",
  "mission_id": "mission-002-a",
  "assigned_agent": "backend-developer",
  "objective": "Fix UnboundLocalError in informacao_service.py:524 by moving local import to top-level scope",
  "context": {
    "files_in_scope": [
      "services/informacao_service.py",
      "tests/test_p03_*.py"
    ],
    "architecture_contracts": [
      "NO_FUNCTIONAL_REMOVAL",
      "MULTI_TENANT_ISOLATION"
    ],
    "technical_details": {
      "root_cause": "Local import at line 335 shadows top-level import, causing UnboundLocalError at line 524",
      "fix_approach": "Move import to top-level (already exists at line 4, remove duplication)",
      "affected_function": "responder_consulta_informativa()"
    }
  },
  "dependencies": [],
  "acceptance_criteria": [
    "✓ UnboundLocalError removed (no exception at line 524)",
    "✓ All 118 P0.3 tests PASS",
    "✓ No regression in baseline tests",
    "✓ No other modules modified",
    "✓ Commit message is clear and references mission"
  ],
  "risk_level": "CRITICAL",
  "evidence_required": [
    "git_diff",
    "git_commit",
    "pytest_output",
    "test_summary"
  ],
  "status": "PENDING",
  "created_at": "2026-11-21T18:00:00Z",
  "assigned_at": null,
  "started_at": null,
  "completed_at": null,
  "rejected_reason": null,
  "blocked_by": null
}
```

---

## 2. Event Contract

### 2.1 — Event Definition (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NeoEve Agent Event",
  "type": "object",
  "required": [
    "event_id",
    "event_type",
    "timestamp",
    "correlation_id"
  ],
  "properties": {
    "event_id": {
      "type": "string",
      "pattern": "^evt-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z-]+$",
      "description": "Unique event identifier (evt-YYYY-MM-DD-TYPE-SEQUENCE)"
    },
    "event_type": {
      "type": "string",
      "enum": [
        "MISSION_CREATED",
        "MISSION_PLANNED",
        "TASK_CREATED",
        "TASK_ASSIGNED",
        "TASK_STARTED",
        "TASK_BLOCKED",
        "TASK_UNBLOCKED",
        "TASK_COMPLETED",
        "REVIEW_REQUESTED",
        "REVIEW_APPROVED",
        "REVIEW_REJECTED",
        "MISSION_COMPLETED",
        "ARCHITECT_WARNING"
      ],
      "description": "Type of event"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "When event occurred"
    },
    "correlation_id": {
      "type": "string",
      "description": "Unique identifier for event chain (all events in a mission share same correlation_id)"
    },
    "mission_id": {
      "type": ["string", "null"],
      "pattern": "^mission-[0-9]{3}-[a-z]$"
    },
    "task_id": {
      "type": ["string", "null"],
      "pattern": "^task-[0-9]{3}-[a-z]-[0-9]{3}$"
    },
    "agent": {
      "type": ["string", "null"],
      "enum": [
        "architect",
        "backend-developer",
        "debugger",
        "qa-engineer",
        "security-auditor",
        "release-manager"
      ]
    },
    "data": {
      "type": "object",
      "description": "Event-specific data"
    },
    "severity": {
      "type": "string",
      "enum": ["INFO", "WARNING", "ERROR"],
      "default": "INFO"
    }
  }
}
```

### 2.2 — Event Types and Payloads

#### MISSION_CREATED

```json
{
  "event_type": "MISSION_CREATED",
  "event_id": "evt-2026-11-21-mission-created-001",
  "mission_id": "mission-002-a",
  "timestamp": "2026-11-21T18:00:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "objective": "Corrigir UnboundLocalError em informacao_service.py:524",
    "risk_level": "CRITICAL",
    "estimated_timeline_hours": 8,
    "depends_on_missions": []
  },
  "severity": "INFO"
}
```

#### MISSION_PLANNED

```json
{
  "event_type": "MISSION_PLANNED",
  "event_id": "evt-2026-11-21-mission-planned-001",
  "mission_id": "mission-002-a",
  "timestamp": "2026-11-21T18:05:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "tasks_created": 4,
    "tasks": [
      "task-002-a-001",
      "task-002-a-002",
      "task-002-a-003",
      "task-002-a-004"
    ],
    "parallel_opportunities": [
      ["task-002-a-002", "task-002-a-003"]
    ],
    "critical_path": ["task-002-a-001", "task-002-a-002", "task-002-a-003", "task-002-a-004"]
  },
  "severity": "INFO"
}
```

#### TASK_CREATED

```json
{
  "event_type": "TASK_CREATED",
  "event_id": "evt-2026-11-21-task-created-001",
  "mission_id": "mission-002-a",
  "task_id": "task-002-a-001",
  "timestamp": "2026-11-21T18:05:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "assigned_agent": "UNASSIGNED",
    "objective": "Fix UnboundLocalError in informacao_service.py:524",
    "risk_level": "CRITICAL",
    "blockers": []
  },
  "severity": "INFO"
}
```

#### TASK_ASSIGNED

```json
{
  "event_type": "TASK_ASSIGNED",
  "event_id": "evt-2026-11-21-task-assigned-001",
  "mission_id": "mission-002-a",
  "task_id": "task-002-a-001",
  "agent": "backend-developer",
  "timestamp": "2026-11-21T18:06:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "acknowledged": true,
    "estimated_start": "2026-11-21T18:30:00Z"
  },
  "severity": "INFO"
}
```

#### TASK_BLOCKED

```json
{
  "event_type": "TASK_BLOCKED",
  "event_id": "evt-2026-11-21-task-blocked-001",
  "mission_id": "mission-002-a",
  "task_id": "task-002-a-002",
  "agent": "qa-engineer",
  "timestamp": "2026-11-21T18:30:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "blocker": {
      "type": "DEPENDENCY_NOT_COMPLETED",
      "depends_on": "task-002-a-001",
      "dependency_status": "IN_PROGRESS",
      "dependency_progress": "50%"
    },
    "action": "Task moved to BLOCKED state, awaiting task-002-a-001 completion"
  },
  "severity": "INFO"
}
```

#### REVIEW_REQUESTED

```json
{
  "event_type": "REVIEW_REQUESTED",
  "event_id": "evt-2026-11-21-review-requested-001",
  "mission_id": "mission-002-a",
  "task_id": "task-002-a-001",
  "agent": "backend-developer",
  "timestamp": "2026-11-21T19:00:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "validator": "openai-validator",
    "decision_requested": "ARQUITECTURAL_SOUNDNESS",
    "evidence_provided": [
      "git_diff",
      "pytest_output",
      "test_summary"
    ],
    "submission_id": "val-2026-11-21-p03-fix-001"
  },
  "severity": "INFO"
}
```

#### REVIEW_APPROVED

```json
{
  "event_type": "REVIEW_APPROVED",
  "event_id": "evt-2026-11-21-review-approved-001",
  "mission_id": "mission-002-a",
  "task_id": "task-002-a-001",
  "timestamp": "2026-11-21T19:30:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "validator": "openai-validator",
    "decision": "APROVADO",
    "confidence": 0.98,
    "recommendations": "DEPLOY"
  },
  "severity": "INFO"
}
```

#### ARCHITECT_WARNING

```json
{
  "event_type": "ARCHITECT_WARNING",
  "event_id": "evt-2026-11-21-warning-001",
  "mission_id": "mission-002-a",
  "timestamp": "2026-11-21T18:03:00Z",
  "correlation_id": "mission-002-a-chain",
  "data": {
    "warning_type": "CANNOT_AUTO_APPROVE",
    "message": "ARCHITECT cannot auto-approve its own decisions. Sending to independent validator.",
    "recommendation": "Encaminhado para OpenAI Validator"
  },
  "severity": "WARNING"
}
```

### 2.3 — Event Stream Example

```
evt-2026-11-21-mission-created-001
  → MISSION_CREATED [mission-002-a]
  
evt-2026-11-21-mission-planned-001
  → MISSION_PLANNED [4 tasks]
  
evt-2026-11-21-task-created-001
  → TASK_CREATED [task-002-a-001]
evt-2026-11-21-task-created-002
  → TASK_CREATED [task-002-a-002]
evt-2026-11-21-task-created-003
  → TASK_CREATED [task-002-a-003]
evt-2026-11-21-task-created-004
  → TASK_CREATED [task-002-a-004]
  
evt-2026-11-21-task-assigned-001
  → TASK_ASSIGNED [task-002-a-001 → backend-developer]
evt-2026-11-21-task-assigned-002
  → TASK_ASSIGNED [task-002-a-002 → qa-engineer]
evt-2026-11-21-task-assigned-003
  → TASK_ASSIGNED [task-002-a-003 → security-auditor]
evt-2026-11-21-task-assigned-004
  → TASK_ASSIGNED [task-002-a-004 → release-manager]

evt-2026-11-21-task-started-001
  → TASK_STARTED [task-002-a-001]

evt-2026-11-21-task-blocked-001
  → TASK_BLOCKED [task-002-a-002] (depends on 001)

evt-2026-11-21-task-completed-001
  → TASK_COMPLETED [task-002-a-001]

evt-2026-11-21-task-unblocked-001
  → TASK_UNBLOCKED [task-002-a-002]

evt-2026-11-21-review-requested-001
  → REVIEW_REQUESTED [task-002-a-001]

evt-2026-11-21-warning-001
  → ARCHITECT_WARNING [Cannot auto-approve]

evt-2026-11-21-review-approved-001
  → REVIEW_APPROVED [task-002-a-001]

... (continue for other tasks)

evt-2026-11-21-mission-completed-001
  → MISSION_COMPLETED [mission-002-a]
```

---

## 3. OpenAI Validator Contract

### 3.1 — Submission Format

```json
{
  "submission": {
    "request_id": "val-2026-11-21-p03-fix-001",
    "mission_id": "mission-002-a",
    "decision_requested": "ARQUITECTURAL_SOUNDNESS|MULTI_TENANT_SAFETY|REGRESSSION_RISK",
    "package": {
      "objective": "...",
      "diagnosis": {
        "root_cause": "...",
        "impact": "...",
        "severity": "CRITICAL|HIGH|MEDIUM|LOW"
      },
      "proposed_plan": {...},
      "modules_involved": [...],
      "architecture_contracts_checked": {...},
      "risk_assessment": {...},
      "acceptance_criteria": [...],
      "evidence_available": [...]
    }
  }
}
```

### 3.2 — Validator Response

```json
{
  "response": {
    "request_id": "val-2026-11-21-p03-fix-001",
    "decision": "APROVADO|REPROVADO|INVESTIGAÇÃO_NECESSÁRIA|EVIDÊNCIA_INSUFICIENTE",
    "confidence": 0.95,
    "components_reviewed": [...],
    "findings": [...],
    "architecture_compliance": {...},
    "regression_risk": {...},
    "recommendation": "DEPLOY|REJECT|INVESTIGATE"
  }
}
```

---

## 4. Command Center Integration

Events produced by ARCHITECT and all agents will be persisted for Command Center dashboard:

```
docs/agent-team/events/
  └─ 2026-11-21/
     ├─ mission-002-a.events.jsonl
     └─ metrics.json
```

Each event is a valid JSON line, allowing streaming consumption.

---

**Contract Version**: 1.0  
**Status**: Ready for implementation  
**Next**: Command Center dashboard development
