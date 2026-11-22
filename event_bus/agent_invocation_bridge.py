"""Agent Invocation Bridge — Connects Event Bus to Agent Runtime"""

import logging
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from event_bus.event import Event, EventType, EventStatus
from event_bus.dispatcher import AgentRole
from event_bus.runtime import AgentRuntime


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    agent_id: str
    agent_role: AgentRole
    system_prompt: str
    authorized_tools: list
    max_tokens: int = 1000
    timeout_seconds: int = 60
    max_retries: int = 2


class AgentInvocationBridge:
    """
    Bridges Event Bus to Anthropic Agent Runtime.

    Responsibilities:
    - Receive authorized tasks from Dispatcher
    - Consult Governance Engine
    - Invoke agents via Anthropic SDK
    - Capture structured results
    - Publish results to Event Bus
    - Handle failures gracefully
    """

    def __init__(self, event_bus, dispatcher, governance, runtime: AgentRuntime):
        self.event_bus = event_bus
        self.dispatcher = dispatcher
        self.governance = governance
        self.runtime = runtime
        self.agent_configs: Dict[str, AgentConfig] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        """Register default agent configurations"""

        # Backend Developer
        self.agent_configs["backend"] = AgentConfig(
            agent_id="backend",
            agent_role=AgentRole.BACKEND,
            system_prompt="""You are a Backend Developer agent.
Your responsibilities:
- Implement features based on requirements
- Commit code with meaningful messages
- Run tests and report results
- Return structured JSON with execution details

Format your response as JSON:
{
  "status": "COMPLETED" | "FAILED" | "PARTIAL",
  "result": {...},
  "files_modified": N,
  "tests_passed": N,
  "tests_failed": N,
  "commits": [...]
}""",
            authorized_tools=["read_file", "write_file", "run_tests", "git_commit"],
            max_tokens=2000,
            timeout_seconds=300
        )

        # QA Engineer
        self.agent_configs["qa"] = AgentConfig(
            agent_id="qa",
            agent_role=AgentRole.QA,
            system_prompt="""You are a QA Engineer agent.
Your responsibilities:
- Test implementations against requirements
- Report test results
- Identify issues and regressions
- Return structured JSON with evaluation

Format your response as JSON:
{
  "qa_decision": "APPROVED" | "REJECTED",
  "tests_total": N,
  "tests_passed": N,
  "tests_failed": N,
  "failures": [...]
}""",
            authorized_tools=["read_file", "run_tests"],
            max_tokens=1500,
            timeout_seconds=180
        )

        # Security Auditor
        self.agent_configs["security"] = AgentConfig(
            agent_id="security",
            agent_role=AgentRole.SECURITY,
            system_prompt="""You are a Security Auditor agent.
Your responsibilities:
- Audit code for security vulnerabilities
- Classify findings by severity
- Recommend fixes
- Return structured JSON with evaluation

Format your response as JSON:
{
  "security_decision": "APPROVED" | "REJECTED",
  "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "findings": [...]
}""",
            authorized_tools=["read_file"],
            max_tokens=1500,
            timeout_seconds=180
        )

    def register_agent(self, config: AgentConfig):
        """Register a custom agent configuration"""
        self.agent_configs[config.agent_id] = config
        logger.info(f"Agent registered: {config.agent_id}")

    async def invoke_agent(
        self,
        event: Event,
        target_agent: AgentRole,
        task_description: str
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke agent via Anthropic SDK.

        Args:
            event: Task event
            target_agent: Target agent role
            task_description: Task instructions

        Returns:
            Structured result dict or None if failed
        """

        # Validate target
        if not self._validate_target(target_agent):
            logger.error(f"Invalid target agent: {target_agent.value}")
            return None

        # Check governance
        decision = self.governance.evaluate(event, target_agent.value, "execute")
        if not decision.allowed:
            logger.warning(f"Governance blocked execution: {decision.reason}")
            self.event_bus.mark_failed(
                event.event_id,
                f"Governance blocked: {decision.reason}",
                target_agent.value
            )
            return None

        # Get agent config
        config = self.agent_configs.get(target_agent.value)
        if not config:
            logger.error(f"No config for agent: {target_agent.value}")
            return None

        # Prepare context
        context = self._prepare_context(event, config)

        # Invoke via configured runtime
        try:
            result = await self._execute_via_runtime(config, context, task_description)

            if result:
                # Publish result to Event Bus
                result_event = Event(
                    event_type=EventType.TASK_COMPLETED,
                    mission_id=event.mission_id,
                    task_id=event.task_id,
                    agent_id=target_agent.value,
                    agent_role=target_agent.value,
                    correlation_id=event.correlation_id,
                    causation_id=event.event_id,
                    payload=result,
                    schema_version="1.0"
                )

                self.event_bus.publish(result_event)
                self.event_bus.mark_completed(event.event_id, target_agent.value)

                logger.info(f"Agent {target_agent.value} completed: {event.event_id}")
                return result
            else:
                self.event_bus.mark_failed(
                    event.event_id,
                    "Agent execution returned no result",
                    target_agent.value
                )
                return None

        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            self.event_bus.mark_failed(
                event.event_id,
                f"Execution error: {str(e)}",
                target_agent.value
            )
            return None

    def _validate_target(self, target_agent: AgentRole) -> bool:
        """Validate that target agent is known"""
        return target_agent.value in self.agent_configs

    def _prepare_context(self, event: Event, config: AgentConfig) -> Dict[str, Any]:
        """Prepare task context for agent"""
        return {
            "task_id": event.task_id,
            "mission_id": event.mission_id,
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "agent_id": config.agent_id,
            "task_payload": event.payload,
            "timestamp": datetime.utcnow().isoformat(),
            "execution_id": f"exec-{uuid4().hex[:8]}"
        }

    async def _execute_via_runtime(
        self,
        config: AgentConfig,
        context: Dict[str, Any],
        task_description: str
    ) -> Optional[Dict[str, Any]]:
        """
        Execute task via configured runtime (subscription or API-based).

        Delegates to runtime abstraction which handles:
        - Claude Code CLI (subscription-based)
        - Anthropic SDK (API-based)
        - Future runtimes
        """

        try:
            # Invoke runtime
            result = await self.runtime.invoke(
                agent_id=config.agent_id,
                agent_role=config.agent_role.value,
                system_prompt=config.system_prompt,
                task_description=task_description,
                context=context,
                authorized_tools=config.authorized_tools,
                max_tokens=config.max_tokens,
                timeout_seconds=config.timeout_seconds
            )

            # Check result status
            if result.status != "COMPLETED":
                logger.error(f"Runtime execution failed: {result.error}")
                return None

            if not result.result:
                logger.error("Runtime returned no result")
                return None

            # Ensure execution_id is preserved
            if isinstance(result.result, dict):
                result.result["execution_id"] = context["execution_id"]

            return result.result

        except Exception as e:
            logger.error(f"Runtime execution error: {e}", exc_info=True)
            return None

    def _handle_failure(self, event_id: str, reason: str, agent_id: str):
        """Handle agent execution failure"""
        self.event_bus.mark_failed(event_id, reason, agent_id)
        logger.error(f"Agent {agent_id} failed: {reason}")


# Synchronous wrapper for compatibility with existing handlers
class AgentInvocationBridgeSync(AgentInvocationBridge):
    """Synchronous version for compatibility"""

    def invoke_agent_sync(
        self,
        event: Event,
        target_agent: AgentRole,
        task_description: str
    ) -> Optional[Dict[str, Any]]:
        """Synchronous agent invocation (blocking)"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.invoke_agent(event, target_agent, task_description)
        )
