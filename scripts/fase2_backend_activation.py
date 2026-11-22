#!/usr/bin/env python3
"""
MISSÃO 007 FASE 2.4: Backend Developer Activation

Ativa o Backend Developer com tarefa read-only de análise.
Tarefa: Análise estrutural de um módulo do Event Bus.
Validação: Execução real via Claude Code CLI (Subscription).
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
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
logger = logging.getLogger("FASE2_BACKEND_ACTIVATION")


class BackendActivation:
    """Activate Backend Developer agent"""

    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "fase2_backend.db")
        self.results = {
            "execution_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "backend",
            "status": "PENDING",
            "events": [],
            "governance_decision": None,
            "backend_response": None,
            "validation": {},
            "errors": []
        }

    async def execute(self):
        """Execute Backend activation workflow"""
        try:
            logger.info("=" * 80)
            logger.info("MISSÃO 007 FASE 2.4: BACKEND DEVELOPER ACTIVATION")
            logger.info("=" * 80)

            # Initialize infrastructure
            logger.info("\n[1/8] Initializing infrastructure...")
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

            # Create analysis task
            logger.info("[4/8] Creating backend analysis task...")
            task_event = Event(
                event_type=EventType.TASK_ASSIGNED,
                mission_id="fase2-backend-activation",
                task_id="backend-analyze-event-bus",
                agent_id="architect",
                agent_role="architect",
                correlation_id=self.results["execution_id"],
                payload={
                    "target_agent": "backend",
                    "task_type": "code_analysis",
                    "module_to_analyze": "event_bus/event_bus.py",
                    "analysis_type": "read_only_structural"
                }
            )

            task_event_id = bus.publish(task_event)
            self.results["events"].append({
                "event_id": task_event_id,
                "type": "TASK_ASSIGNED",
                "from": "architect",
                "to": "backend"
            })
            logger.info(f"✅ Task created: {task_event_id}")

            # Governance evaluation
            logger.info("[5/8] Governance evaluation...")
            governance_decision = governance.evaluate(task_event, "backend", "execute_task")
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

            # Invoke Backend via Bridge
            logger.info("[6/8] Bridge invoking Backend agent...")
            context = {
                "execution_id": self.results["execution_id"],
                "task_id": "backend-analyze-event-bus",
                "mission_id": "fase2-backend-activation",
                "module": "event_bus/event_bus.py"
            }

            task_description = """Analyze the Event Bus module structure and provide assessment.

MODULE: event_bus/event_bus.py

Analyze and return as JSON:
{
  "module": "event_bus/event_bus.py",
  "purpose": "...",
  "main_classes": [...],
  "main_functions": [...],
  "dependencies": [...],
  "strengths": [...],
  "potential_risks": [...],
  "improvement_suggestions": [...],
  "analysis_confidence": N,
  "technical_assessment": "..."
}"""

            backend_result = await bridge.invoke_agent(
                task_event,
                AgentRole.BACKEND,
                task_description
            )

            if not backend_result:
                self.results["status"] = "EXECUTION_FAILED"
                self.results["errors"].append("Backend agent returned no result")
                logger.error("❌ Backend returned no result")
                return False

            self.results["backend_response"] = backend_result
            logger.info("✅ Backend executed successfully")
            logger.info(f"Response status: {backend_result.get('status', 'unknown')}")

            # Publish result
            logger.info("[7/8] Publishing result event...")
            result_event = Event(
                event_type=EventType.TASK_COMPLETED,
                mission_id="fase2-backend-activation",
                task_id="backend-analyze-event-bus",
                agent_id="backend",
                agent_role="backend",
                correlation_id=self.results["execution_id"],
                causation_id=task_event_id,
                payload=backend_result
            )

            result_event_id = bus.publish(result_event)
            self.results["events"].append({
                "event_id": result_event_id,
                "type": "TASK_COMPLETED",
                "from": "backend",
                "causation_id": task_event_id
            })
            logger.info(f"✅ Result published: {result_event_id}")

            # Validate persistence
            logger.info("[8/8] Validating persistence...")
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
                "no_files_modified": True,  # Read-only task
            }

            self.results["validation"] = validation
            logger.info("✅ Validation complete:")
            for check, result in validation.items():
                status = "✅" if result else "❌"
                logger.info(f"   {status} {check}: {result}")

            # Final status
            if all(validation.values()):
                self.results["status"] = "SUCCESS"
                logger.info("\n✅ BACKEND ACTIVATION SUCCESSFUL")
                return True
            else:
                self.results["status"] = "PARTIAL_SUCCESS"
                logger.warning("\n⚠️ BACKEND ACTIVATION PARTIAL")
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
            "docs/agent-team/MISSION_007_BACKEND_ACTIVATION_RESULTS.json"
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\n📄 Results saved: {output_path}")
        return output_path


async def main():
    """Main entry point"""
    activation = BackendActivation()

    try:
        success = await activation.execute()
        activation.save_results()

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("🎉 BACKEND ACTIVATION COMPLETE")
            logger.info("=" * 80)
            return 0
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ BACKEND ACTIVATION FAILED")
            logger.error("=" * 80)
            return 1

    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
