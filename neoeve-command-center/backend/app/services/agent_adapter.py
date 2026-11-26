"""Agent Adapter: interface for executors."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from enum import Enum


class ExecutionStatus(Enum):
    """Execution status."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentAdapter(ABC):
    """Abstract adapter for agent executors."""

    @abstractmethod
    def execute(
        self,
        execution_id: str,
        task_description: str,
        workspace_path: str,
        timeout_seconds: int = 300,
    ) -> Tuple[int, str, str]:
        """
        Execute a task.

        Returns:
            (exit_code, stdout, stderr)
        """
        pass

    @abstractmethod
    def cancel(self, execution_id: str) -> bool:
        """Cancel an execution."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if executor is available."""
        pass

    @abstractmethod
    def get_status(self, execution_id: str) -> ExecutionStatus:
        """Get current execution status."""
        pass
