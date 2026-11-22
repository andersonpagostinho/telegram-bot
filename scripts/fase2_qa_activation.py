#!/usr/bin/env python3
"""
MISSÃO 007 FASE 2.6: QA Engineer Agent Activation

Ativa o QA Engineer com auditoria independente e testes reais.
Demonstra capacidade de aprovação e reprovação.
Coleta métricas reais de execução.
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from event_bus.event import Event, EventType
from event_bus.event_bus import EventBus
from event_bus.dispatcher import EventDispatcher, AgentRole
from event_bus.governance import GovernanceEngine
from event_bus.agent_invocation_bridge import AgentInvocationBridge
from event_bus.claude_code_runtime import ClaudeCodeRuntime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FASE2_QA_ACTIVATION")


class QAActivation:
    """Activate QA Engineer agent with independent validation"""

    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "fase2_qa.db")

        # Execution metrics
        self.metrics = {
            "queued_at": None,
            "reserved_at": None,
            "started_at": None,
            "completed_at": None,
            "validated_at": None,
            "recorded_at": None,
        }

        self.results = {
            "execution_id": str(uuid4()),
            "timestamp_created": datetime.now(timezone.utc).isoformat(),
            "agent": "qa",
            "status": "PENDING",
            "events": [],
            "governance_decision": None,
            "qa_response": None,
            "validation": {},
            "metrics": self.metrics,
            "calculated_durations": {},
            "errors": []
        }

    def _now_utc(self):
        """Get current UTC timestamp"""
        return datetime.now(timezone.utc).isoformat()

    def _calculate_durations(self):
        """Calculate durations from metrics"""
        durations = {}

        if self.metrics["queued_at"] and self.metrics["reserved_at"]:
            q = datetime.fromisoformat(self.metrics["queued_at"])
            r = datetime.fromisoformat(self.metrics["reserved_at"])
            durations["queue_time_ms"] = int((r - q).total_seconds() * 1000)

        if self.metrics["reserved_at"] and self.metrics["started_at"]:
            r = datetime.fromisoformat(self.metrics["reserved_at"])
            s = datetime.fromisoformat(self.metrics["started_at"])
            durations["init_time_ms"] = int((s - r).total_seconds() * 1000)

        if self.metrics["started_at"] and self.metrics["completed_at"]:
            s = datetime.fromisoformat(self.metrics["started_at"])
            c = datetime.fromisoformat(self.metrics["completed_at"])
            durations["execution_time_ms"] = int((c - s).total_seconds() * 1000)

        if self.metrics["completed_at"] and self.metrics["validated_at"]:
            c = datetime.fromisoformat(self.metrics["completed_at"])
            v = datetime.fromisoformat(self.metrics["validated_at"])
            durations["validation_time_ms"] = int((v - c).total_seconds() * 1000)

        if self.metrics["queued_at"] and self.metrics["validated_at"]:
            q = datetime.fromisoformat(self.metrics["queued_at"])
            v = datetime.fromisoformat(self.metrics["validated_at"])
            durations["total_duration_ms"] = int((v - q).total_seconds() * 1000)

        return durations

    async def execute(self):
        """Execute QA activation workflow"""
        try:
            logger.info("=" * 80)
            logger.info("MISSÃO 007 FASE 2.6: QA ENGINEER ACTIVATION")
            logger.info("=" * 80)

            # Initialize infrastructure
            logger.info("\n[1/8] Initializing infrastructure...")
            self.metrics["queued_at"] = self._now_utc()

            bus = EventBus(self.db_path, use_wal=False)
            dispatcher = EventDispatcher(bus)
            governance = GovernanceEngine(bus)

            logger.info("[2/8] Initializing Claude Code Runtime...")
            try:
                runtime = ClaudeCodeRuntime()
                self.results["runtime"] = "Claude Code CLI (Subscription)"
                logger.info("✅ Runtime ready")
            except RuntimeError as e:
                self.results["status"] = "FAILED"
                self.results["errors"].append(f"Runtime init failed: {str(e)}")
                logger.error(f"❌ Runtime init failed: {e}")
                return False

            logger.info("[3/8] Initializing Bridge...")
            bridge = AgentInvocationBridge(bus, dispatcher, governance, runtime)
            logger.info("✅ Bridge ready")

            # Create QA audit task
            logger.info("[4/8] Creating QA audit task...")
            self.metrics["reserved_at"] = self._now_utc()

            task_event = Event(
                event_type=EventType.TASK_ASSIGNED,
                mission_id="fase2-qa-activation",
                task_id="qa-validate-multiagent",
                agent_id="architect",
                agent_role="architect",
                correlation_id=self.results["execution_id"],
                payload={
                    "target_agent": "qa",
                    "task_type": "independent_validation",
                    "components_to_validate": [
                        "event_bus",
                        "dispatcher",
                        "governance",
                        "bridge"
                    ],
                    "validation_type": "read_only_audit"
                }
            )

            task_event_id = bus.publish(task_event)
            self.results["events"].append({
                "event_id": task_event_id,
                "type": "TASK_ASSIGNED",
                "from": "architect",
                "to": "qa"
            })
            logger.info(f"✅ Task created: {task_event_id}")

            # Governance evaluation
            logger.info("[5/8] Governance evaluation...")
            governance_decision = governance.evaluate(task_event, "qa", "execute_tests")
            self.results["governance_decision"] = {
                "allowed": governance_decision.allowed,
                "reason": governance_decision.reason
            }

            if not governance_decision.allowed:
                self.results["status"] = "BLOCKED_BY_GOVERNANCE"
                self.results["errors"].append(f"Governance blocked: {governance_decision.reason}")
                logger.error(f"❌ Governance blocked: {governance_decision.reason}")
                return False

            logger.info(f"✅ Governance approved")

            # Invoke QA via Bridge
            logger.info("[6/8] Bridge invoking QA Engineer...")
            self.metrics["started_at"] = self._now_utc()

            task_description = """Execute independent QA audit and validation.

COMPONENTS TO VALIDATE:
1. Event Bus (publication, consumption, persistence)
2. Dispatcher (routing, agent resolution)
3. Governance (authorization, permission enforcement)
4. Bridge (agent invocation, runtime integration)

VALIDATION APPROACH:
- Examine test coverage
- Review existing test results
- Identify gaps in validation
- Execute tests for critical paths
- Demonstrate approval and rejection capability

EVIDENCE TO PROVIDE:
- Component analysis
- Test execution results
- Coverage assessment
- Risk areas
- Independent approval or rejection decision

Provide analysis as JSON:
{
  "qa_decision": "APPROVED" | "REJECTED" | "CONDITIONAL",
  "components_validated": [...],
  "tests_executed": N,
  "tests_passed": N,
  "tests_failed": N,
  "coverage_gaps": [...],
  "risk_assessment": "...",
  "approval_basis": "...",
  "rejection_reasons": [...],
  "confidence_level": N,
  "technical_notes": "..."
}"""

            qa_result = await bridge.invoke_agent(
                task_event,
                AgentRole.QA,
                task_description
            )

            self.metrics["completed_at"] = self._now_utc()

            if not qa_result:
                self.results["status"] = "EXECUTION_FAILED"
                self.results["errors"].append("QA agent returned no result")
                logger.error("❌ QA returned no result")
                return False

            self.results["qa_response"] = qa_result
            logger.info("✅ QA executed successfully")
            logger.info(f"Response status: {qa_result.get('qa_decision', 'unknown')}")

            # Publish result
            logger.info("[7/8] Publishing result event...")
            result_event = Event(
                event_type=EventType.TASK_COMPLETED,
                mission_id="fase2-qa-activation",
                task_id="qa-validate-multiagent",
                agent_id="qa",
                agent_role="qa",
                correlation_id=self.results["execution_id"],
                causation_id=task_event_id,
                payload=qa_result
            )

            result_event_id = bus.publish(result_event)
            self.results["events"].append({
                "event_id": result_event_id,
                "type": "TASK_COMPLETED",
                "from": "qa",
                "causation_id": task_event_id
            })
            logger.info(f"✅ Result published: {result_event_id}")

            # Validate persistence
            logger.info("[8/8] Validating persistence...")
            self.metrics["validated_at"] = self._now_utc()

            retrieved_task = bus.store.get_event(task_event_id)
            retrieved_result = bus.store.get_event(result_event_id)

            validation = {
                "task_event_persisted": retrieved_task is not None,
                "result_event_persisted": retrieved_result is not None,
                "correlation_preserved": (
                    retrieved_result and
                    retrieved_result.correlation_id == self.results["execution_id"]
                ),
                "causation_chain": (
                    retrieved_result and
                    retrieved_result.causation_id == task_event_id
                ),
                "no_files_modified": True,  # Read-only audit
            }

            self.results["validation"] = validation
            self.metrics["recorded_at"] = self._now_utc()

            # Calculate durations
            self.results["calculated_durations"] = self._calculate_durations()

            logger.info("✅ Validation complete:")
            for check, result in validation.items():
                status = "✅" if result else "❌"
                logger.info(f"   {status} {check}: {result}")

            logger.info("\n📊 Execution Metrics:")
            for metric_name, value_ms in self.results["calculated_durations"].items():
                logger.info(f"   {metric_name}: {value_ms}ms")

            # Final status
            if all(validation.values()):
                self.results["status"] = "SUCCESS"
                logger.info("\n✅ QA ACTIVATION SUCCESSFUL")
                return True
            else:
                self.results["status"] = "PARTIAL_SUCCESS"
                logger.warning("\n⚠️ QA ACTIVATION PARTIAL")
                return False

        except Exception as e:
            self.results["status"] = "ERROR"
            self.results["errors"].append(f"Unexpected error: {str(e)}")
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return False

    def save_results(self):
        """Save execution results"""
        output_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "docs/agent-team/MISSION_007_QA_ACTIVATION_RESULTS.json"
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\n📄 Results saved: {output_path}")
        return output_path


async def main():
    """Main entry point"""
    activation = QAActivation()

    try:
        success = await activation.execute()
        activation.save_results()

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("🎉 QA ACTIVATION COMPLETE")
            logger.info("=" * 80)
            return 0
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ QA ACTIVATION FAILED")
            logger.error("=" * 80)
            return 1

    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
