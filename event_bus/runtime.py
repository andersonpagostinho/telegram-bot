"""Abstract Runtime Interface for Agent Execution

Defines contract for executing agents independently of implementation.
Allows swapping between Anthropic SDK, Claude Code CLI, or other runtimes.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


@dataclass
class RuntimeResult:
    """Result from agent execution"""
    status: str  # "COMPLETED", "FAILED", "TIMEOUT"
    result: Optional[Dict[str, Any]]
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    tokens_used: Optional[int] = None
    execution_id: Optional[str] = None


class AgentRuntime(ABC):
    """Abstract base class for agent execution runtimes"""

    @abstractmethod
    async def invoke(
        self,
        agent_id: str,
        agent_role: str,
        system_prompt: str,
        task_description: str,
        context: Dict[str, Any],
        authorized_tools: list,
        max_tokens: int,
        timeout_seconds: int,
    ) -> RuntimeResult:
        """
        Execute agent task via this runtime.

        Args:
            agent_id: Unique agent identifier
            agent_role: Agent role (backend, qa, security, etc)
            system_prompt: System prompt defining agent behavior
            task_description: User-facing task description
            context: Structured context (task_id, mission_id, etc)
            authorized_tools: List of allowed tools for this agent
            max_tokens: Maximum response tokens
            timeout_seconds: Execution timeout

        Returns:
            RuntimeResult with status, result, and metadata
        """
        pass

    @abstractmethod
    def validate_authentication(self) -> bool:
        """Validate that runtime can authenticate and execute"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if runtime is operational"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
