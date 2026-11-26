"""Claude Code Adapter: executor using Claude Code CLI with subscription verification."""

import logging
import subprocess
import os
import signal
import psutil
import json
import shutil
import threading
import time
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from app.services.agent_adapter import AgentAdapter, ExecutionStatus
from app.services.terminal_access_control import TerminalAccessControl

logger = logging.getLogger(__name__)


class ClaudeCodeAdapter(AgentAdapter):
    """Execute tasks via Claude Code CLI with real subprocess management."""

    def __init__(self, subscription_only: bool = True):
        self.subscription_only = subscription_only
        self._processes = {}  # Maps execution_id → (process, start_time)
        self._subscription_verified = False
        self._subscription_status = None

        # Resource limits from TerminalAccessControl
        limits = TerminalAccessControl.RESOURCE_LIMITS
        self.timeout_seconds = limits.get("timeout_seconds", 300)
        self.memory_mb = limits.get("memory_mb", 2048)
        self.cpu_percent = limits.get("cpu_percent", 80)

        self._resource_monitor_threads = {}  # Maps execution_id → thread

    def _monitor_resources(self, execution_id: str, process: subprocess.Popen, timeout_seconds: int) -> None:
        """Monitor process resources in background thread.

        Kills process if:
        - Memory exceeds limit (memory_mb)
        - CPU exceeds limit (cpu_percent) for extended period
        - Timeout exceeded
        """
        start_time = time.time()
        cpu_violation_count = 0

        try:
            parent = psutil.Process(process.pid)

            while process.poll() is None:  # While process is running
                try:
                    # Check memory
                    mem_info = parent.memory_info()
                    mem_mb = mem_info.rss / (1024 * 1024)

                    if mem_mb > self.memory_mb:
                        logger.warning(f"Execution {execution_id}: Memory limit exceeded ({mem_mb:.1f}MB > {self.memory_mb}MB), killing process")
                        parent.terminate()
                        time.sleep(1)
                        if process.poll() is None:
                            parent.kill()
                        return

                    # Check CPU (avoid first second)
                    elapsed = time.time() - start_time
                    if elapsed > 1:
                        try:
                            cpu_percent = parent.cpu_percent(interval=0.5)

                            if cpu_percent > self.cpu_percent:
                                cpu_violation_count += 1
                                if cpu_violation_count > 3:  # 3 violations = kill
                                    logger.warning(f"Execution {execution_id}: CPU limit exceeded ({cpu_percent}% > {self.cpu_percent}%), killing process")
                                    parent.terminate()
                                    time.sleep(1)
                                    if process.poll() is None:
                                        parent.kill()
                                    return
                            else:
                                cpu_violation_count = max(0, cpu_violation_count - 1)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    # Check timeout
                    if time.time() - start_time > timeout_seconds:
                        logger.warning(f"Execution {execution_id}: Timeout ({timeout_seconds}s) exceeded, killing process")
                        parent.terminate()
                        time.sleep(1)
                        if process.poll() is None:
                            parent.kill()
                        return

                    time.sleep(0.5)  # Check every 500ms

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process already terminated or no access
                    return

        except Exception as e:
            logger.error(f"Execution {execution_id}: Resource monitor error: {e}")

    def _get_claude_executable(self) -> Optional[str]:
        """Find claude executable path."""
        return shutil.which("claude")

    def verify_subscription(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify Claude Code subscription status via native CLI.

        Returns:
            (is_valid, status_dict)
            is_valid: True if Claude Pro subscription is active
            status_dict: Full auth status or error details
        """
        try:
            claude_exe = self._get_claude_executable()
            if not claude_exe:
                return False, {"error": "Claude CLI not found in PATH"}

            result = subprocess.run(
                [claude_exe, "auth", "status"],
                capture_output=True,
                timeout=5,
                text=True,
            )

            if result.returncode != 0:
                return False, {"error": "Auth status check failed", "stderr": result.stderr}

            status = json.loads(result.stdout)

            is_logged_in = status.get("loggedIn", False)
            is_pro = status.get("subscriptionType") == "pro"

            if not is_logged_in:
                return False, {
                    "error": "Claude CLI not authenticated",
                    "loggedIn": False,
                }

            if not is_pro:
                return False, {
                    "error": "Claude subscription is not Pro tier",
                    "subscriptionType": status.get("subscriptionType"),
                }

            logger.info(
                f"Claude subscription verified: "
                f"user={status.get('email')}, "
                f"plan={status.get('planTier')}, "
                f"expires={status.get('loginExpiresAt')}"
            )

            self._subscription_verified = True
            self._subscription_status = status
            return True, status

        except json.JSONDecodeError as e:
            return False, {"error": f"Invalid JSON response: {e}"}
        except subprocess.TimeoutExpired:
            return False, {"error": "Auth status check timed out"}
        except Exception as e:
            return False, {"error": f"Verification failed: {e}"}

    def health_check(self) -> Dict[str, Any]:
        """
        Extended health check: CLI availability + subscription status.

        Returns:
            {
                "cli_available": bool,
                "subscription_valid": bool,
                "subscription_status": dict or None,
                "errors": list
            }
        """
        result = {
            "cli_available": False,
            "subscription_valid": False,
            "subscription_status": None,
            "errors": []
        }

        try:
            claude_exe = self._get_claude_executable()
            if not claude_exe:
                result["errors"].append("Claude CLI not found in PATH")
                return result

            # Check CLI version
            version_result = subprocess.run(
                [claude_exe, "--version"],
                capture_output=True,
                timeout=5,
            )

            if version_result.returncode != 0:
                result["errors"].append("Claude CLI version check failed")
                return result

            result["cli_available"] = True

            # Check subscription
            if self.subscription_only:
                is_valid, status = self.verify_subscription()
                result["subscription_valid"] = is_valid
                result["subscription_status"] = status

                if not is_valid:
                    result["errors"].append(status.get("error", "Unknown subscription error"))

            return result

        except Exception as e:
            result["errors"].append(f"Health check failed: {e}")
            return result

    def execute(
        self,
        execution_id: str,
        task_description: str,
        workspace_path: str,
        timeout_seconds: int = 300,
    ) -> Tuple[int, str, str]:
        """Execute task via Claude Code CLI - REAL execution."""

        # 1. VERIFY SUBSCRIPTION (via native CLI)
        if self.subscription_only:
            if not self._subscription_verified:
                is_valid, status = self.verify_subscription()
                if not is_valid:
                    error_msg = f"Claude subscription verification failed: {status.get('error', 'Unknown error')}"
                    logger.error(f"Execution {execution_id}: {error_msg}")
                    self._processes[execution_id] = ExecutionStatus.FAILED
                    return (1, "", error_msg)
            logger.info(f"Execution {execution_id}: Subscription auth verified via native CLI")

        try:
            # 2. VALIDATE WORKSPACE
            if not os.path.isdir(workspace_path):
                error_msg = f"Workspace not found: {workspace_path}"
                logger.error(f"Execution {execution_id}: {error_msg}")
                self._processes[execution_id] = ExecutionStatus.FAILED
                return (1, "", error_msg)

            # 3. BUILD REAL CLAUDE CODE COMMAND
            # Using: claude code --workspace <path> <command>
            cmd = [
                "claude",
                "code",
                "--workspace", workspace_path,
                "--",  # End of options
                task_description,
            ]

            logger.info(f"Execution {execution_id}: Starting process with command: {' '.join(cmd[:4])}...")

            # 4. EXECUTE WITH RESOURCE MONITORING
            process = subprocess.Popen(
                cmd,
                cwd=workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Store process reference for cancellation
            self._processes[execution_id] = (process, datetime.now(timezone.utc))

            # SECURITY: Start resource monitor thread (memory, CPU, timeout)
            monitor_thread = threading.Thread(
                target=self._monitor_resources,
                args=(execution_id, process, timeout_seconds),
                daemon=True,
            )
            monitor_thread.start()
            self._resource_monitor_threads[execution_id] = monitor_thread

            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
                exit_code = process.returncode

                logger.info(f"Execution {execution_id}: Process completed with exit code {exit_code}")
                self._processes[execution_id] = ExecutionStatus.COMPLETED
                self._resource_monitor_threads.pop(execution_id, None)
                return (exit_code, stdout[:5000], stderr[:5000])  # Truncate to 5KB

            except subprocess.TimeoutExpired:
                # Kill process and subprocesses
                logger.warning(f"Execution {execution_id}: Timeout after {timeout_seconds}s, killing process")
                try:
                    parent = psutil.Process(process.pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
                except Exception as e:
                    logger.error(f"Execution {execution_id}: Error killing process: {e}")
                    process.kill()

                self._processes[execution_id] = ExecutionStatus.FAILED
                self._resource_monitor_threads.pop(execution_id, None)
                return (124, "", f"Timeout exceeded ({timeout_seconds}s)")

        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}", exc_info=True)
            self._processes[execution_id] = ExecutionStatus.FAILED
            return (1, "", str(e))

    def cancel(self, execution_id: str) -> bool:
        """Cancel execution - REAL process termination."""
        logger.info(f"Cancellation requested for {execution_id}")

        process_info = self._processes.get(execution_id)
        if not process_info or isinstance(process_info, ExecutionStatus):
            logger.warning(f"Execution {execution_id}: Not found or already terminal")
            return False

        process, start_time = process_info

        try:
            # Kill process and all subprocesses
            if process.poll() is None:  # Process still running
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                logger.info(f"Execution {execution_id}: Process terminated successfully")

            self._processes[execution_id] = ExecutionStatus.CANCELLED
            return True
        except Exception as e:
            logger.error(f"Execution {execution_id}: Error cancelling: {e}")
            return False

    def get_status(self, execution_id: str) -> ExecutionStatus:
        """Get execution status."""
        process_info = self._processes.get(execution_id, ExecutionStatus.QUEUED)
        if isinstance(process_info, ExecutionStatus):
            return process_info

        process, start_time = process_info
        if process.poll() is None:
            return ExecutionStatus.RUNNING
        return ExecutionStatus.COMPLETED
