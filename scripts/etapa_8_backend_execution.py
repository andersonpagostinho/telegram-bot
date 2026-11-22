#!/usr/bin/env python3
"""
MISSÃO 006-R1 — ETAPA 8: Backend Agent Real Execution Orchestrator

Fluxo completo:
Architect → Event Bus → Dispatcher → Governance → Bridge → Runtime → Backend Agent
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

# Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from event_bus.event import Event, EventType, EventStatus
from event_bus.event_bus import EventBus
from event_bus.dispatcher import EventDispatcher, AgentRole
from event_bus.governance import GovernanceEngine
from event_bus.agent_invocation_bridge import AgentInvocationBridge
from event_bus.claude_code_runtime import ClaudeCodeRuntime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ETAPA8_BACKEND_EXECUTION")


class Etapa8Orchestrator:
    """Orchestrates ETAPA 8 Backend Agent real execution"""

    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "test_etapa8.db")
        self.results = {
            "execution_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "PENDING",
            "events": [],
            "governance_decision": None,
            "backend_response": None,
            "validation": {},
            "errors": []
        }

    async def execute(self):
        """Execute full Backend Agent workflow"""
        try:
            logger.info("=" * 80)
            logger.info("MISSÃO 006-R1 — ETAPA 8: BACKEND AGENT REAL EXECUTION")
            logger.info("=" * 80)

            # Step 1: Initialize components
            logger.info("\n[1/8] Initializing Event Bus, Dispatcher, Governance...")
            bus = EventBus(self.db_path, use_wal=False)
            dispatcher = EventDispatcher(bus)
            governance = GovernanceEngine(bus)

            # Step 2: Initialize Runtime (this validates authentication)
            logger.info("[2/8] Initializing Claude Code Runtime (SUBSCRIPTION_ONLY)...")
            try:
                runtime = ClaudeCodeRuntime()
                self.results["runtime"] = "ClaudeCodeRuntime (Claude Code CLI)"
                logger.info("✅ Runtime initialized successfully")
            except RuntimeError as e:
                self.results["status"] = "FAILED"
                self.results["errors"].append(f"Runtime initialization failed: {str(e)}")
                logger.error(f"❌ Runtime init failed: {e}")
                return False

            # Step 3: Initialize Bridge
            logger.info("[3/8] Initializing Agent Invocation Bridge...")
            bridge = AgentInvocationBridge(bus, dispatcher, governance, runtime)
            logger.info("✅ Bridge initialized")

            # Step 4: Create task event from Architect
            logger.info("[4/8] Creating task event (Architect → Backend)...")
            task_event = Event(
                event_type=EventType.TASK_ASSIGNED,
                mission_id="etapa8-backend-execution",
                task_id="backend-read-test-file",
                agent_id="architect",
                agent_role="architect",
                correlation_id=self.results["execution_id"],
                payload={
                    "target_agent": "backend",
                    "task_type": "read_only_analysis",
                    "file_to_analyze": "tests/test_runtime_integration.py",
                    "analysis_type": "test_structure_analysis"
                }
            )

            task_event_id = bus.publish(task_event)
            self.results["events"].append({
                "event_id": task_event_id,
                "type": "TASK_ASSIGNED",
                "from": "architect",
                "to": "backend"
            })
            logger.info(f"✅ Task event created: {task_event_id}")

            # Step 5: Governance evaluates
            logger.info("[5/8] Governance evaluates Backend execution...")
            governance_decision = governance.evaluate(task_event, "backend", "execute_task")
            self.results["governance_decision"] = {
                "allowed": governance_decision.allowed,
                "reason": governance_decision.reason
            }

            if not governance_decision.allowed:
                self.results["status"] = "BLOCKED_BY_GOVERNANCE"
                self.results["errors"].append(f"Governance blocked: {governance_decision.reason}")
                logger.error(f"❌ Governance blocked execution: {governance_decision.reason}")
                return False

            logger.info(f"✅ Governance approved: {governance_decision.reason}")

            # Step 6: Bridge invokes Backend via Runtime
            logger.info("[6/8] Bridge invoking Backend Agent via Claude Code Runtime...")
            context = {
                "execution_id": self.results["execution_id"],
                "task_id": "backend-read-test-file",
                "mission_id": "etapa8-backend-execution",
                "file_path": "tests/test_runtime_integration.py"
            }

            task_description = """Analyze the following test file and provide a structured report:

FILE: tests/test_runtime_integration.py

Provide a JSON response with:
{
  "file_path": "tests/test_runtime_integration.py",
  "purpose": "...",
  "components_tested": [...],
  "test_classes": [...],
  "test_methods_count": N,
  "key_validations": [...],
  "technical_observations": "...",
  "conclusion": "..."
}"""

            backend_result = await bridge.invoke_agent(
                task_event,
                AgentRole.BACKEND,
                task_description
            )

            if not backend_result:
                self.results["status"] = "EXECUTION_FAILED"
                self.results["errors"].append("Backend Agent returned no result")
                logger.error("❌ Backend Agent returned no result")
                return False

            self.results["backend_response"] = backend_result
            logger.info(f"✅ Backend Agent executed successfully")
            logger.info(f"Response status: {backend_result.get('status', 'unknown')}")

            # Step 7: Publish result event to Event Bus
            logger.info("[7/8] Publishing result event to Event Bus...")
            result_event = Event(
                event_type=EventType.TASK_COMPLETED,
                mission_id="etapa8-backend-execution",
                task_id="backend-read-test-file",
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
                "causation_id": task_event_id,
                "correlation_id": self.results["execution_id"]
            })
            logger.info(f"✅ Result event published: {result_event_id}")

            # Step 8: Validate persistence and correlations
            logger.info("[8/8] Validating Event Bus persistence and correlations...")

            # Retrieve events from bus
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
                "multi_tenant_isolated": (
                    retrieved_task and
                    retrieved_task.mission_id == "etapa8-backend-execution"
                )
            }

            self.results["validation"] = validation
            logger.info(f"✅ Validation complete:")
            for check, result in validation.items():
                status = "✅" if result else "❌"
                logger.info(f"   {status} {check}: {result}")

            # Final status
            if all(validation.values()):
                self.results["status"] = "SUCCESS"
                logger.info("\n✅ ETAPA 8 EXECUTION SUCCESSFUL")
                return True
            else:
                self.results["status"] = "PARTIAL_SUCCESS"
                logger.warning("\n⚠️ ETAPA 8 EXECUTION PARTIAL (some validations failed)")
                return False

        except Exception as e:
            self.results["status"] = "ERROR"
            self.results["errors"].append(f"Unexpected error: {str(e)}")
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return False

    def save_results(self):
        """Save execution results to file"""
        output_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "docs/agent-team/MISSION_006_R1_ETAPA_8_EXECUTION_RESULTS.json"
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\n📄 Results saved to: {output_path}")
        return output_path


async def main():
    """Main entry point"""
    orchestrator = Etapa8Orchestrator()

    try:
        success = await orchestrator.execute()
        orchestrator.save_results()

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("🎉 ETAPA 8 COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            return 0
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ ETAPA 8 FAILED")
            logger.error("=" * 80)
            return 1

    except KeyboardInterrupt:
        logger.info("\n⚠️ Execution interrupted by user")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
