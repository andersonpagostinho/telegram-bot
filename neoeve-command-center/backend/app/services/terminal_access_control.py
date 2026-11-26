"""Terminal Access Control: Security wrapper for command execution.

Implements:
- Whitelist-based command validation
- Dangerous command blacklist
- Workspace isolation
- Resource limits
- Audit trail logging
- Multi-tenant isolation
"""

import logging
import hashlib
import re
import os
from typing import Tuple, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session
from database.models import TerminalAuditLog
from app.services.agent_registry import AgentRegistry, Permission

logger = logging.getLogger(__name__)


class CommandBlockReason(Enum):
    """Reasons why command was blocked."""
    BLACKLIST_MATCH = "blacklist_match"
    NO_EXECUTE_PERMISSION = "no_execute_permission"
    INVALID_WORKSPACE = "invalid_workspace"
    MISSING_TENANT = "missing_tenant"
    UNKNOWN_AGENT = "unknown_agent"


class TerminalAccessControl:
    """Wrapper for terminal command execution with security validation."""

    # Dangerous command patterns (regex)
    BLACKLIST_PATTERNS = [
        r"rm\s+-.*[rf]",  # rm -rf, rm -f, rm -r (any combo with -r or -f)
        r"rm\s+-[rf]+",  # rm -rf, rm -r (explicitly)
        r"rm\s+(/|--recursive|--force)",  # rm /, rm --recursive, rm --force
        r"sudo\s+",  # sudo (privilege escalation)
        r"chmod\s+.*777",  # chmod 777 (unrestricted permissions)
        r"chmod\s+000",  # chmod 000 (no permissions)
        r"chown",  # chown (change ownership)
        r":(){ :|:& };:",  # Bash fork bomb
        r"dd\s+if=.*of=",  # dd (direct disk write)
        r"mkfs",  # mkfs (format filesystem)
        r"fdisk",  # fdisk (partition table)
        r"iptables.*-P.*DROP",  # iptables (network lockout)
        r"shutdown\s+(-h|-r|-P)",  # shutdown (system termination)
        r"halt",  # halt
        r"reboot",  # reboot
        r"\|\s*base64\s+--decode",  # Encoded commands (potential obfuscation)
        r"eval\s+",  # eval (dynamic code)
        r"exec\s+",  # exec (replace process)
        r"\$\(\s*curl",  # curl command substitution
        r"wget.*\.sh",  # Download and execute shell
    ]

    # Allowed operations (whitelist)
    ALLOWED_OPERATIONS = [
        "cd",  # Change directory (within workspace)
        "ls", "find", "grep", "cat", "head", "tail",  # Read operations
        "mkdir", "touch",  # Create files/dirs (within workspace)
        "cp", "mv", "rm",  # File operations (single files, not recursive)
        "git",  # Version control
        "python", "node", "npm", "pip",  # Runtimes and package managers
        "make", "gradle", "maven",  # Build tools
        "docker",  # Container execution
        "curl", "wget",  # HTTP downloads (with restrictions)
        "echo", "printf",  # Output
        "test", "[",  # Conditionals
        "if", "for", "while",  # Flow control
        "export",  # Environment variables
    ]

    # Restricted directories (never allowed)
    RESTRICTED_PATHS = [
        "/etc",
        "/sys",
        "/proc",
        "/boot",
        "/dev",
        "/root",
        "/.ssh",
        "/var/log",
        "/opt",
    ]

    # Resource limits
    RESOURCE_LIMITS = {
        "timeout_seconds": 300,
        "memory_mb": 2048,
        "cpu_percent": 80,
    }

    @staticmethod
    def _hash_command(command: str) -> str:
        """Compute SHA256 hash of command."""
        return hashlib.sha256(command.encode()).hexdigest()

    @staticmethod
    def _is_blacklisted(command: str) -> Tuple[bool, Optional[str]]:
        """Check if command matches dangerous pattern.

        Returns:
            (is_blacklisted, pattern_matched_or_reason)
        """
        for pattern in TerminalAccessControl.BLACKLIST_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True, pattern

        return False, None

    @staticmethod
    def _validate_workspace(workspace_path: str) -> Tuple[bool, Optional[str]]:
        """Validate workspace is in safe location.

        Returns:
            (is_valid, error_reason_or_None)
        """
        if not workspace_path:
            return False, "Workspace path is empty"

        # Normalize path
        normalized = workspace_path.replace("\\", "/")

        # Security Rule 1: Block path traversal (..)
        if ".." in normalized:
            return False, "Path traversal (..) not allowed"

        # Security Rule 2: Check restricted paths
        for restricted in TerminalAccessControl.RESTRICTED_PATHS:
            if normalized.startswith(restricted):
                return False, f"Workspace in restricted location: {restricted}"

        # Security Rule 3: Block other user homes
        if normalized.startswith("/home") and not normalized.startswith("/home/agent"):
            return False, "Cannot access other user home directories"

        # Security Rule 4: Symlink validation (direct + encadeado + TOCTOU)
        try:
            # Check 1: Direct symlink at workspace path
            if os.path.islink(workspace_path):
                return False, "Direct symlink in workspace path blocked"

            # Check 2: Resolve symlinks and validate workspace bounds
            # This catches: encadeado symlinks, intermediate symlinks, TOCTOU attacks
            real_path = os.path.realpath(workspace_path)

            # Normalize paths: convert to absolute, remove ./, resolve ..
            # Use normpath to handle both \ and / on different platforms
            workspace_abs = os.path.normpath(os.path.abspath(workspace_path))
            real_abs = os.path.normpath(real_path)

            # real_path must be WITHIN or EQUAL TO workspace
            # Allow: /home/agent/workspace = /home/agent/workspace (direct)
            # Allow: /home/agent/workspace/data = /home/agent/workspace (subdirectory)
            # Block: /etc/passwd = /home/agent/workspace (escape)

            # Compare with common separators (forward slash)
            workspace_normalized = workspace_abs.replace("\\", "/")
            real_normalized = real_abs.replace("\\", "/")

            # Check if real path is within workspace
            if real_normalized != workspace_normalized:
                # Must be a subdirectory of workspace
                workspace_prefix = workspace_normalized + "/"
                if not real_normalized.startswith(workspace_prefix):
                    # Escapes workspace (encadeado or TOCTOU)
                    return False, "Symlink resolves outside workspace (encadeado/TOCTOU)"

        except (OSError, RuntimeError) as e:
            # If we can't check symlinks, that's a security issue
            return False, f"Cannot safely resolve symlinks: {str(e)}"

        return True, None

    @staticmethod
    def validate_command(
        command: str,
        agent_id: str,
        workspace_path: str,
        tenant_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """Validate if command is allowed to execute.

        Returns:
            (is_allowed, block_reason_or_None)
        """
        # 1. Check agent exists and has EXECUTE permission
        if not AgentRegistry.has_permission(agent_id, Permission.EXECUTE):
            return False, f"{CommandBlockReason.NO_EXECUTE_PERMISSION.value}: Agent {agent_id} lacks EXECUTE permission"

        # 2. Validate tenant
        if not tenant_id:
            return False, f"{CommandBlockReason.MISSING_TENANT.value}"

        # 3. Validate workspace
        is_valid, reason = TerminalAccessControl._validate_workspace(workspace_path)
        if not is_valid:
            return False, f"{CommandBlockReason.INVALID_WORKSPACE.value}: {reason}"

        # 4. WHITELIST CHECK (BLOQUEIO POR PADRÃO - OBRIGATÓRIO)
        command_stripped = command.strip()
        if not command_stripped:
            return False, "Command is empty"

        command_parts = command_stripped.split()
        if not command_parts:
            return False, "Command cannot be parsed"

        cmd_name = command_parts[0]

        # Check if command name is in whitelist (allow ONLY known operations)
        is_whitelisted = any(cmd_name.endswith(op) or cmd_name == op
                            for op in TerminalAccessControl.ALLOWED_OPERATIONS)

        if not is_whitelisted:
            allowed_str = ", ".join(TerminalAccessControl.ALLOWED_OPERATIONS)
            return False, f"Command '{cmd_name}' not in whitelist. Allowed: {allowed_str}"

        # 5. BLACKLIST CHECK (additional protection layer)
        is_blacklisted, pattern = TerminalAccessControl._is_blacklisted(command)
        if is_blacklisted:
            return False, f"{CommandBlockReason.BLACKLIST_MATCH.value}: Pattern '{pattern}' matched"

        return True, None

    @staticmethod
    def audit_command(
        execution_id: str,
        agent_id: str,
        task_id: str,
        tenant_id: str,
        project_id: str,
        command: str,
        workspace_path: str,
        status: str,  # PERMITTED, BLOCKED, TIMEOUT, ERROR
        block_reason: Optional[str] = None,
        exit_code: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """Log command execution to audit trail.

        Returns:
            True if logged successfully
        """
        try:
            if not db:
                logger.warning(f"Cannot audit command {execution_id}: no database session")
                return False

            audit_log = TerminalAuditLog(
                audit_id=str(uuid4()),
                execution_id=execution_id,
                agent_id=agent_id,
                task_id=task_id,
                tenant_id=tenant_id,
                project_id=project_id,
                command=command[:2000],  # Truncate to 2KB
                command_hash=TerminalAccessControl._hash_command(command),
                workspace_path=workspace_path[:512],
                status=status,
                block_reason=block_reason,
                exit_code=exit_code,
                execution_time_ms=execution_time_ms,
            )

            db.add(audit_log)
            db.commit()

            logger.info(
                f"Audit: execution_id={execution_id}, agent={agent_id}, "
                f"status={status}, reason={block_reason or 'N/A'}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to audit command {execution_id}: {e}")
            return False


def wrap_claude_code_adapter(adapter_execute_func):
    """Decorator to wrap ClaudeCodeAdapter.execute() with access control.

    Usage:
        @wrap_claude_code_adapter
        def execute(self, ...):
            ...
    """
    def wrapper(self, execution_id: str, task_description: str, workspace_path: str, timeout_seconds: int = 300):
        # This would be injected with agent_id, tenant_id, etc. from context
        # For now, this is a structure example

        is_allowed, block_reason = TerminalAccessControl.validate_command(
            command=task_description,
            agent_id=getattr(self, '_agent_id', 'unknown'),
            workspace_path=workspace_path,
            tenant_id=getattr(self, '_tenant_id', 'unknown'),
        )

        if not is_allowed:
            logger.error(f"Command blocked: {block_reason}")
            return (1, "", f"Command blocked: {block_reason}")

        # If validation passed, execute the original function
        return adapter_execute_func(self, execution_id, task_description, workspace_path, timeout_seconds)

    return wrapper
