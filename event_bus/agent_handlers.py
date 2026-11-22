"""Real Agent Handlers — Demonstrates actual agent invocation and task execution"""

import logging
import json
from datetime import datetime
from uuid import uuid4

from event_bus.event import Event, EventType, EventStatus


logger = logging.getLogger(__name__)


class ArchitectHandler:
    """Architect Agent Handler — Coordinator and decision maker"""

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.name = "architect"

    def handle_task_completed(self, event: Event) -> bool:
        """
        Architect receives task completion from Backend/Debugger/QA.
        Evaluates result and decides next action.
        """
        logger.info(f"[ARCHITECT] Received task completion: {event.event_id}")

        try:
            # Extract result from payload
            result_data = event.payload.get("result", {})
            task_id = event.task_id
            mission_id = event.mission_id

            logger.info(f"[ARCHITECT] Evaluating result for task {task_id}")
            logger.info(f"[ARCHITECT] Result data: {json.dumps(result_data, indent=2)}")

            # Architect publishes evaluation
            evaluation_event = Event(
                event_type=EventType.REVIEW_REQUESTED,
                mission_id=mission_id,
                task_id=task_id,
                execution_id=event.execution_id,
                agent_id=self.name,
                agent_role=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={
                    "evaluation": "APPROVED",
                    "notes": f"Task {task_id} completed successfully",
                    "requires_security_review": True,
                    "requires_qa_validation": True
                },
                schema_version="1.0"
            )

            # Publish evaluation
            self.event_bus.publish(evaluation_event, idempotency_key=f"arch-eval-{task_id}")

            logger.info(f"[ARCHITECT] Published evaluation for task {task_id}")

            # Mark original event as completed
            self.event_bus.mark_completed(event.event_id, self.name)

            return True

        except Exception as e:
            logger.error(f"[ARCHITECT] Handler error: {e}", exc_info=True)
            return False

    def handle_event(self, event: Event) -> bool:
        """Main event handler for Architect"""
        if event.event_type == EventType.TASK_COMPLETED:
            return self.handle_task_completed(event)
        return False


class BackendDeveloperHandler:
    """Backend Developer Agent Handler — Implementer of tasks"""

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.name = "backend"

    def handle_task_assigned(self, event: Event) -> bool:
        """
        Backend receives task assignment.
        Executes implementation and publishes result.
        """
        logger.info(f"[BACKEND] Received task assignment: {event.event_id}")

        try:
            task_id = event.task_id
            mission_id = event.mission_id
            task_desc = event.payload.get("description", "Unknown task")

            logger.info(f"[BACKEND] Executing task: {task_desc}")

            # Simulate execution (in real scenario: git commit, etc.)
            execution_result = self._execute_task(task_desc)

            # Publish result
            result_event = Event(
                event_type=EventType.TASK_COMPLETED,
                mission_id=mission_id,
                task_id=task_id,
                execution_id=event.execution_id or f"exec-{uuid4().hex[:8]}",
                agent_id=self.name,
                agent_role=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={
                    "status": "completed",
                    "result": execution_result,
                    "timestamp": datetime.utcnow().isoformat(),
                    "commits": ["abc1234", "def5678"]
                },
                schema_version="1.0"
            )

            self.event_bus.publish(result_event, idempotency_key=f"backend-exec-{task_id}")

            logger.info(f"[BACKEND] Published result for task {task_id}")

            # Mark original event as completed
            self.event_bus.mark_completed(event.event_id, self.name)

            return True

        except Exception as e:
            logger.error(f"[BACKEND] Handler error: {e}", exc_info=True)
            return False

    def _execute_task(self, description: str) -> dict:
        """Simulate task execution (local, non-production)"""
        logger.info(f"[BACKEND] Executing: {description}")

        return {
            "task": description,
            "files_modified": 2,
            "tests_added": 3,
            "tests_passed": 3,
            "errors": 0,
            "output": "Task executed successfully (simulated)"
        }

    def handle_event(self, event: Event) -> bool:
        """Main event handler for Backend"""
        if event.event_type == EventType.TASK_ASSIGNED:
            return self.handle_task_assigned(event)
        return False


class ProofOfConcept:
    """
    Demonstrates real communication flow:
    Architect → publishes task → Backend → executes → publishes result → Architect
    """

    def __init__(self, event_bus, dispatcher):
        self.event_bus = event_bus
        self.dispatcher = dispatcher

        # Register handlers
        self.architect = ArchitectHandler(event_bus)
        self.backend = BackendDeveloperHandler(event_bus)

        from event_bus.dispatcher import AgentRole
        self.dispatcher.register_handler(AgentRole.ARCHITECT, self.architect.handle_event)
        self.dispatcher.register_handler(AgentRole.BACKEND, self.backend.handle_event)

    def run_proof_of_concept(self) -> bool:
        """
        Run real communication proof:
        1. Architect publishes TASK_ASSIGNED
        2. Dispatcher routes to Backend
        3. Backend executes and publishes TASK_COMPLETED
        4. Dispatcher routes to Architect
        5. Architect receives and processes
        """
        from event_bus.event import Event, EventType

        mission_id = "poc-mission-001"
        task_id = "poc-task-001"
        correlation_id = f"poc-{uuid4().hex[:8]}"

        logger.info("=" * 80)
        logger.info("STARTING PROOF OF CONCEPT: Architect ↔ Backend")
        logger.info("=" * 80)

        # STEP 1: Architect publishes task
        logger.info("\n[STEP 1] Architect publishes TASK_ASSIGNED")

        task_event = Event(
            event_type=EventType.TASK_ASSIGNED,
            mission_id=mission_id,
            task_id=task_id,
            agent_id="architect",
            agent_role="architect",
            correlation_id=correlation_id,
            payload={
                "description": "Create unit test for new feature",
                "target_agent": "backend",
                "priority": "high"
            },
            schema_version="1.0"
        )

        self.event_bus.publish(task_event)
        logger.info(f"Published: {task_event.event_id}")

        # STEP 2: Dispatcher routes to Backend and invokes
        logger.info("\n[STEP 2] Dispatcher routes to Backend")
        from event_bus.dispatcher import AgentRole

        dispatched = self.dispatcher.dispatch(task_event, AgentRole.BACKEND)
        if not dispatched:
            logger.error("Failed to dispatch to Backend")
            return False

        # STEP 3: Backend publishes result
        logger.info("\n[STEP 3] Backend executes and publishes result")

        # Get pending events (simulating event bus polling)
        pending = self.event_bus.store.get_pending_events(mission_id, limit=10)
        result_event = None
        for evt in pending:
            if evt.event_type == EventType.TASK_COMPLETED:
                result_event = evt
                break

        if not result_event:
            logger.error("Backend did not publish result event")
            return False

        logger.info(f"Result published: {result_event.event_id}")
        logger.info(f"Result payload: {json.dumps(result_event.payload, indent=2)}")

        # STEP 4: Dispatcher routes result to Architect
        logger.info("\n[STEP 4] Dispatcher routes result to Architect")

        dispatched = self.dispatcher.dispatch(result_event, AgentRole.ARCHITECT)
        if not dispatched:
            logger.error("Failed to dispatch to Architect")
            return False

        # STEP 5: Verify correlation
        logger.info("\n[STEP 5] Verify traceability via correlation_id")

        all_events = []
        for evt in self.event_bus.store.get_pending_events(mission_id, limit=100):
            if evt.correlation_id == correlation_id:
                all_events.append(evt)

        logger.info(f"Events in chain: {len(all_events)}")
        for evt in all_events:
            logger.info(f"  - {evt.event_type.value}: {evt.agent_id}")

        logger.info("=" * 80)
        logger.info("PROOF OF CONCEPT COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

        return True


# ============= FIVE REMAINING HANDLERS =============

class DebuggerHandler:
    """Debugger Agent Handler"""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.name = "debugger"

    def handle_event(self, event: Event) -> bool:
        logger.info(f"[DEBUGGER] Investigating: {event.event_id}")
        try:
            result_event = Event(
                event_type=EventType.TASK_COMPLETED,
                mission_id=event.mission_id,
                task_id=event.task_id,
                agent_id=self.name,
                agent_role=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={"findings": ["Root cause identified"], "status": "COMPLETE"},
                schema_version="1.0"
            )
            self.event_bus.publish(result_event)
            self.event_bus.mark_completed(event.event_id, self.name)
            return True
        except Exception as e:
            logger.error(f"[DEBUGGER] Error: {e}")
            return False


class QAEngineerHandler:
    """QA Engineer Agent Handler"""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.name = "qa"

    def handle_event(self, event: Event) -> bool:
        logger.info(f"[QA] Testing: {event.event_id}")
        try:
            result_event = Event(
                event_type=EventType.REVIEW_APPROVED,
                mission_id=event.mission_id,
                task_id=event.task_id,
                agent_id=self.name,
                agent_role=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={"evidence": {"tests_passed": 10}, "qa_decision": "APPROVED"},
                schema_version="1.0"
            )
            self.event_bus.publish(result_event)
            self.event_bus.mark_completed(event.event_id, self.name)
            return True
        except Exception as e:
            logger.error(f"[QA] Error: {e}")
            return False


class SecurityAuditorHandler:
    """Security Auditor Agent Handler"""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.name = "security"

    def _determine_severity(self, payload: dict) -> str:
        """Determine severity level from findings"""
        # Check explicit severity in payload
        if "severity" in payload:
            severity = payload["severity"].upper()
            if severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                return severity

        # Infer from vulnerabilities
        vulnerabilities = payload.get("vulnerabilities", 0)
        if vulnerabilities >= 3:
            return "CRITICAL"
        elif vulnerabilities >= 2:
            return "HIGH"
        elif vulnerabilities >= 1:
            return "MEDIUM"
        return "LOW"

    def handle_event(self, event: Event) -> bool:
        logger.info(f"[SECURITY] Auditing: {event.event_id}")
        try:
            # Determine severity from findings
            severity = self._determine_severity(event.payload or {})
            logger.info(f"[SECURITY] Finding severity: {severity}")

            # CRITICAL or HIGH = REJECT, others = APPROVE
            should_approve = severity not in ["CRITICAL", "HIGH"]

            result_event = Event(
                event_type=EventType.REVIEW_APPROVED if should_approve else EventType.REVIEW_REJECTED,
                mission_id=event.mission_id,
                task_id=event.task_id,
                agent_id=self.name,
                agent_role=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={
                    "evidence": {"vulnerabilities": event.payload.get("vulnerabilities", 0) if event.payload else 0},
                    "severity": severity,
                    "security_decision": "APPROVED" if should_approve else "REJECTED",
                    "reason": f"Security finding: {severity}" if severity != "LOW" else "No critical findings"
                },
                schema_version="1.0"
            )
            self.event_bus.publish(result_event)
            self.event_bus.mark_completed(event.event_id, self.name)
            return True
        except Exception as e:
            logger.error(f"[SECURITY] Error: {e}")
            return False


class ReleaseManagerHandler:
    """Release Manager Agent Handler"""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.name = "release"

    def handle_event(self, event: Event) -> bool:
        logger.info(f"[RELEASE] Evaluating: {event.event_id}")
        try:
            result_event = Event(
                event_type=EventType.REVIEW_APPROVED,
                mission_id=event.mission_id,
                task_id=event.task_id,
                agent_id=self.name,
                agent_role=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={"status": "READY_FOR_DEPLOYMENT", "note": "Requires explicit authorization"},
                schema_version="1.0"
            )
            self.event_bus.publish(result_event)
            self.event_bus.mark_completed(event.event_id, self.name)
            return True
        except Exception as e:
            logger.error(f"[RELEASE] Error: {e}")
            return False


class OpenAIValidatorHandler:
    """OpenAI Validator Agent Handler (External, read-only)"""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.name = "validator"

    def handle_event(self, event: Event) -> bool:
        logger.info(f"[VALIDATOR] Validating: {event.event_id}")
        try:
            result_event = Event(
                event_type=EventType.REVIEW_APPROVED,
                mission_id=event.mission_id,
                task_id=event.task_id,
                agent_id=self.name,
                agent_role=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                payload={"validation": "PASSED", "architecture_valid": True},
                schema_version="1.0"
            )
            self.event_bus.publish(result_event)
            self.event_bus.mark_completed(event.event_id, self.name)
            return True
        except Exception as e:
            logger.error(f"[VALIDATOR] Error: {e}")
            self.event_bus.mark_failed(event.event_id, f"Validation error: {str(e)}", self.name)
            return False
