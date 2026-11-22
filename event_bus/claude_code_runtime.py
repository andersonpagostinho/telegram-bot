"""Claude Code Subscription Runtime

Executes agents using Claude Code CLI authenticated by subscription.
Implements SUBSCRIPTION_ONLY policy - no Anthropic API Key fallback.
"""

import subprocess
import json
import logging
import os
import shutil
import re
from typing import Optional, Dict, Any
from datetime import datetime

from event_bus.runtime import AgentRuntime, RuntimeResult


logger = logging.getLogger(__name__)


class SubscriptionOnlyPolicy:
    """Enforce SUBSCRIPTION_ONLY policy"""

    @staticmethod
    def validate_environment() -> None:
        """
        Validate that environment is safe for subscription-only execution.

        Raises:
            RuntimeError: If API Key detected or auth missing
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY detected in environment. "
                "NeoEve agents must use Claude subscription only. "
                "Remove ANTHROPIC_API_KEY and authenticate via: claude login"
            )

        # Verify claude CLI is available
        cli_path = shutil.which("claude")
        if not cli_path:
            raise RuntimeError(
                "Claude Code CLI not found. Install via: brew install anthropic-ai/cli/claude"
            )

        logger.info("✅ SUBSCRIPTION_ONLY policy validated")

    @staticmethod
    def clean_environment() -> Dict[str, str]:
        """
        Create clean environment for subprocess.

        Returns subprocess.Popen env dict without ANTHROPIC_API_KEY
        """
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        return env


class ClaudeCodeRuntime(AgentRuntime):
    """Execute agents via Claude Code CLI (subscription)"""

    def __init__(self):
        """Initialize and validate subscription runtime"""
        try:
            SubscriptionOnlyPolicy.validate_environment()
            self.policy = SubscriptionOnlyPolicy()
            logger.info("Claude Code Subscription Runtime initialized")
        except RuntimeError as e:
            logger.error(f"Runtime initialization failed: {e}")
            raise

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
        Execute agent via Claude Code CLI.

        Uses subprocess to run: claude -p "task" --allowed-tools "..."
        """
        start_time = datetime.utcnow()

        try:
            # Build task prompt with context
            task_prompt = self._build_task_prompt(
                system_prompt, task_description, context
            )

            # Build CLI command
            command = self._build_cli_command(
                task_prompt, authorized_tools, max_tokens
            )

            logger.debug(f"Executing {agent_id} via Claude Code CLI")

            # Run subprocess with timeout
            result = await self._run_subprocess(
                command, timeout_seconds, self.policy.clean_environment()
            )

            if result.status == "FAILED":
                return result

            # Parse response as JSON
            parsed_result = self._parse_response(result.result, context)

            duration = (datetime.utcnow() - start_time).total_seconds()

            return RuntimeResult(
                status="COMPLETED",
                result=parsed_result,
                duration_seconds=duration,
                execution_id=context.get("execution_id")
            )

        except subprocess.TimeoutExpired:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Agent {agent_id} timeout after {timeout_seconds}s")
            return RuntimeResult(
                status="TIMEOUT",
                result=None,
                error=f"Execution timeout after {timeout_seconds}s",
                duration_seconds=duration,
                execution_id=context.get("execution_id")
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Agent {agent_id} execution failed: {e}", exc_info=True)
            return RuntimeResult(
                status="FAILED",
                result=None,
                error=str(e),
                duration_seconds=duration,
                execution_id=context.get("execution_id")
            )

    async def _run_subprocess(
        self, command: list, timeout: int, env: Dict[str, str]
    ) -> RuntimeResult:
        """
        Run Claude Code CLI subprocess.

        Args:
            command: Command list for subprocess
            timeout: Timeout in seconds
            env: Environment dict (without API Key)

        Returns:
            RuntimeResult with process output
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=timeout,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace bad characters instead of crashing
                env=env
            )

            stdout = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""

            if result.returncode != 0:
                error_msg = stderr or stdout or "Process exited with error"
                logger.error(f"Process error: {error_msg}")
                return RuntimeResult(
                    status="FAILED",
                    result=None,
                    error=error_msg
                )

            if not stdout:
                return RuntimeResult(
                    status="FAILED",
                    result=None,
                    error="No output from Claude Code"
                )

            return RuntimeResult(
                status="COMPLETED",
                result=stdout
            )

        except subprocess.TimeoutExpired:
            raise
        except Exception as e:
            logger.error(f"Subprocess error: {e}")
            raise

    def _build_task_prompt(
        self,
        system_prompt: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Build complete task prompt for Claude Code CLI.

        Includes system prompt, task, and structured context.
        """
        context_json = json.dumps(context, indent=2)

        return f"""{system_prompt}

Task:
{task_description}

Context:
{context_json}

IMPORTANT: Respond ONLY with valid JSON. No additional text. Format:
{{"status": "COMPLETED", "result": {{...}}, "files_modified": N, "tests_passed": N}}"""

    def _build_cli_command(
        self,
        task_prompt: str,
        authorized_tools: list,
        max_tokens: int
    ) -> list:
        """
        Build Claude Code CLI command.

        Uses: claude -p "prompt" --allowed-tools "tool1,tool2"
        """
        # Format tools for CLI
        tools_arg = ",".join(authorized_tools) if authorized_tools else ""

        import platform
        cli_cmd = "claude.cmd" if platform.system() == "Windows" else "claude"
        command = [cli_cmd, "-p", task_prompt]

        if tools_arg:
            command.extend(["--allowed-tools", tools_arg])

        # Note: max_tokens is applied by agent config in system prompt
        # Claude Code CLI may not expose direct token limit

        return command

    def _parse_response(
        self,
        response_text: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse and validate JSON response from Claude Code.

        Attempts multiple parsing strategies:
        1. Direct JSON.loads()
        2. Extract JSON from text with regex
        3. Return raw response if valid structure
        """
        if not response_text:
            return None

        # Strategy 1: Direct JSON
        try:
            result = json.loads(response_text)
            if isinstance(result, dict):
                result["execution_id"] = context.get("execution_id")
                return result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON from text
        try:
            # Find first { ... } pattern
            match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if match:
                json_text = match.group(0)
                result = json.loads(json_text)
                if isinstance(result, dict):
                    result["execution_id"] = context.get("execution_id")
                    return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 3: Treat entire response as result
        logger.warning("Could not parse JSON, returning raw response")
        return {
            "status": "PARTIAL",
            "result": response_text,
            "execution_id": context.get("execution_id"),
            "parsing_note": "Raw response - JSON parsing failed"
        }

    def validate_authentication(self) -> bool:
        """
        Validate that Claude Code is authenticated.

        Checks for OAuth tokens in Claude config.
        """
        try:
            # Try running a simple command to validate auth
            result = subprocess.run(
                ["claude", "-p", "echo ok"],
                capture_output=True,
                timeout=5,
                text=True,
                env=self.policy.clean_environment()
            )

            is_valid = result.returncode == 0
            if is_valid:
                logger.info("✅ Claude Code authentication validated")
            else:
                logger.error("❌ Claude Code authentication failed")

            return is_valid

        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False

    def health_check(self) -> bool:
        """
        Check if runtime is operational.
        """
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                timeout=5,
                text=True
            )

            is_healthy = result.returncode == 0
            if is_healthy:
                logger.debug(f"✅ Runtime healthy: {result.stdout.strip()}")

            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
