#!/usr/bin/env python3
"""
MISSÃO 007 FASE 2: Architect Agent Activation

Primeira ativação real do agente Architect coordenador.
Tarefa: Análise arquitetural read-only de um componente.
Objetivo: Validar que o Architect pode ser invocado, receber tarefa,
executar análise e retornar resultado estruturado.
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
logger = logging.getLogger("FASE2_ARCHITECT_ACTIVATION")


class ArchitectActivation:
    """Activate and test Architect agent"""

    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "fase2_architect.db")
        self.results = {
            "execution_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "architect",
            "status": "PENDING",
            "events": [],
            "governance_decision": None,
            "architect_response": None,
            "validation": {},
            "errors": []
        }

    async def execute(self):
        """Execute Architect activation workflow"""
        try:
            logger.info("=" * 80)
            logger.info("MISSÃO 007 FASE 2: ARCHITECT AGENT ACTIVATION")
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

            # Create architecture review task
            logger.info("[4/8] Creating architecture review task...")
            task_event = Event(
                event_type=EventType.TASK_ASSIGNED,
                mission_id="fase2-architect-activation",
                task_id="architect-review-event-bus",
                agent_id="architect",
                agent_role="architect",
                correlation_id=self.results["execution_id"],
                payload={
                    "target_agent": "architect",
                    "task_type": "architecture_review",
                    "component_to_review": "event_bus",
                    "review_type": "read_only_analysis"
                }
            )

            task_event_id = bus.publish(task_event)
            self.results["events"].append({
                "event_id": task_event_id,
                "type": "TASK_ASSIGNED",
                "from": "system",
                "to": "architect"
            })
            logger.info(f"✅ Task created: {task_event_id}")

            # Governance evaluation
            logger.info("[5/8] Governance evaluation...")
            governance_decision = governance.evaluate(task_event, "architect", "publish_task")
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

            # Invoke Architect via Bridge
            logger.info("[6/8] Bridge invoking Architect agent...")
            context = {
                "execution_id": self.results["execution_id"],
                "task_id": "architect-review-event-bus",
                "mission_id": "fase2-architect-activation",
                "component": "event_bus"
            }

            task_description = """Review the Event Bus architecture and provide structured assessment:

COMPONENT: event_bus

Provide analysis as JSON:
{
  "component": "event_bus",
  "review_status": "APPROVED" | "NEEDS_IMPROVEMENT" | "BLOCKED",
  "strengths": [...],
  "weaknesses": [...],
  "risks": [...],
  "recommendations": [...],
  "readiness": "PRODUCTION_READY" | "STAGING" | "DEVELOPMENT",
  "confidence": N,
  "technical_notes": "..."
}"""

            architect_result = await bridge.invoke_agent(
                task_event,
                AgentRole.ARCHITECT,
                task_description
            )

            if not architect_result:
                self.results["status"] = "EXECUTION_FAILED"
                self.results["errors"].append("Architect agent returned no result")
                logger.error("❌ Architect returned no result")
                return False

            self.results["architect_response"] = architect_result
            logger.info("✅ Architect executed successfully")
            logger.info(f"Response status: {architect_result.get('review_status', 'unknown')}")

            # Publish result
            logger.info("[7/8] Publishing result event...")
            result_event = Event(
                event_type=EventType.TASK_COMPLETED,
                mission_id="fase2-architect-activation",
                task_id="architect-review-event-bus",
                agent_id="architect",
                agent_role="architect",
                correlation_id=self.results["execution_id"],
                causation_id=task_event_id,
                payload=architect_result
            )

            result_event_id = bus.publish(result_event)
            self.results["events"].append({
                "event_id": result_event_id,
                "type": "TASK_COMPLETED",
                "from": "architect",
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
            }

            self.results["validation"] = validation
            logger.info("✅ Validation complete:")
            for check, result in validation.items():
                status = "✅" if result else "❌"
                logger.info(f"   {status} {check}: {result}")

            # Final status
            if all(validation.values()):
                self.results["status"] = "SUCCESS"
                logger.info("\n✅ ARCHITECT ACTIVATION SUCCESSFUL")
                return True
            else:
                self.results["status"] = "PARTIAL_SUCCESS"
                logger.warning("\n⚠️ ARCHITECT ACTIVATION PARTIAL")
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
            "docs/agent-team/MISSION_007_ARCHITECT_ACTIVATION_RESULTS.json"
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\n📄 Results saved: {output_path}")
        return output_path


async def main():
    """Main entry point"""
    activation = ArchitectActivation()

    try:
        success = await activation.execute()
        activation.save_results()

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("🎉 ARCHITECT ACTIVATION COMPLETE")
            logger.info("=" * 80)
            return 0
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ ARCHITECT ACTIVATION FAILED")
            logger.error("=" * 80)
            return 1

    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
