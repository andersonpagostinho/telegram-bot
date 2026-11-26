"""Agent Registry: central registry of the seven participants."""

import logging
from enum import Enum
from typing import Optional, List, Dict, Set
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from database.models import Agent
# P0 FIX: Import states from independent module to avoid circular import
from app.services.agent_states import OperationalState, ConnectivityState
from app.services.tenant_agent_state_service import TenantAgentStateService

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles."""
    ARCHITECT = "architect"
    BACKEND_DEVELOPER = "backend_developer"
    DEBUGGER = "debugger"
    QA_ENGINEER = "qa_engineer"
    SECURITY_AUDITOR = "security_auditor"
    RELEASE_MANAGER = "release_manager"
    OPENAI_VALIDATOR = "openai_validator"


class Permission(Enum):
    """Agent permissions."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    APPROVE = "approve"
    VETO = "veto"
    PUBLISH = "publish"


# Permission matrix: agent_role → {permission}
PERMISSION_MATRIX = {
    AgentRole.ARCHITECT: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
    AgentRole.BACKEND_DEVELOPER: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
    AgentRole.DEBUGGER: {Permission.READ, Permission.EXECUTE},
    AgentRole.QA_ENGINEER: {Permission.READ, Permission.EXECUTE},
    AgentRole.SECURITY_AUDITOR: {Permission.READ, Permission.VETO},
    AgentRole.RELEASE_MANAGER: {Permission.READ, Permission.EXECUTE},
    AgentRole.OPENAI_VALIDATOR: {Permission.READ},
}

# Capability descriptions
CAPABILITIES = {
    AgentRole.ARCHITECT: ["plan", "decompose", "delegate", "monitor"],
    AgentRole.BACKEND_DEVELOPER: ["implement", "refactor", "test"],
    AgentRole.DEBUGGER: ["investigate", "diagnose", "propose_fixes"],
    AgentRole.QA_ENGINEER: ["test", "validate", "document_findings"],
    AgentRole.SECURITY_AUDITOR: ["audit", "identify_risks", "veto"],
    AgentRole.RELEASE_MANAGER: ["prepare_release", "verify_criteria", "coordinate"],
    AgentRole.OPENAI_VALIDATOR: ["validate", "review", "assess"],
}


class AgentRegistry:
    """Central registry of agents."""

    # Seven registered agents
    AGENTS = {
        "architect": {
            "agent_id": "agent-architect",
            "role": AgentRole.ARCHITECT,
            "name": "Architect / Tech Lead",
            "description": "Plans and decomposes missions into tasks",
        },
        "backend_developer": {
            "agent_id": "agent-backend",
            "role": AgentRole.BACKEND_DEVELOPER,
            "name": "Backend Developer",
            "description": "Implements authorized tasks",
        },
        "debugger": {
            "agent_id": "agent-debugger",
            "role": AgentRole.DEBUGGER,
            "name": "Debugger",
            "description": "Investigates errors and proposes fixes",
        },
        "qa_engineer": {
            "agent_id": "agent-qa",
            "role": AgentRole.QA_ENGINEER,
            "name": "QA Engineer",
            "description": "Executes tests and validates deliverables",
        },
        "security_auditor": {
            "agent_id": "agent-security",
            "role": AgentRole.SECURITY_AUDITOR,
            "name": "Security Auditor",
            "description": "Audits security and can veto releases",
        },
        "release_manager": {
            "agent_id": "agent-release",
            "role": AgentRole.RELEASE_MANAGER,
            "name": "Release Manager",
            "description": "Prepares and coordinates releases",
        },
        "openai_validator": {
            "agent_id": "agent-validator",
            "role": AgentRole.OPENAI_VALIDATOR,
            "name": "OpenAI Validator",
            "description": "Independent external validator (read-only)",
        },
    }

    @classmethod
    def register_all_agents(cls, db: Session) -> None:
        """Register all seven agents in the database."""
        for key, agent_config in cls.AGENTS.items():
            agent = Agent(
                agent_id=agent_config["agent_id"],
                agent_role=agent_config["role"].value,
                runtime="claude-code-cli",
                status=OperationalState.IDLE.value,
                connectivity_status=ConnectivityState.NOT_CONFIGURED.value,
            )
            db.add(agent)
        db.commit()
        logger.info("All seven agents registered")

    @classmethod
    def get_agent(cls, agent_id: str, db: Session) -> Optional[Agent]:
        """Retrieve agent by ID."""
        return db.query(Agent).filter(Agent.agent_id == agent_id).first()

    @classmethod
    def get_agent_by_role(cls, role: AgentRole, db: Session) -> Optional[Agent]:
        """Retrieve agent by role."""
        return db.query(Agent).filter(Agent.agent_role == role.value).first()

    @classmethod
    def list_agents(cls, db: Session) -> List[Agent]:
        """List all agents."""
        return db.query(Agent).all()

    @classmethod
    def has_permission(cls, agent_id: str, permission: Permission) -> bool:
        """Check if agent has permission."""
        agent_config = None
        for key, config in cls.AGENTS.items():
            if config["agent_id"] == agent_id:
                agent_config = config
                break

        if not agent_config:
            return False

        role = agent_config["role"]
        return permission in PERMISSION_MATRIX.get(role, set())

    @classmethod
    def can_approve(cls, agent_id: str) -> bool:
        """Check if agent can approve."""
        return cls.has_permission(agent_id, Permission.APPROVE)

    @classmethod
    def can_veto(cls, agent_id: str) -> bool:
        """Check if agent can veto."""
        return cls.has_permission(agent_id, Permission.VETO)

    @classmethod
    def is_read_only(cls, agent_id: str) -> bool:
        """Check if agent is read-only (like OpenAI Validator)."""
        agent_config = None
        for key, config in cls.AGENTS.items():
            if config["agent_id"] == agent_id:
                agent_config = config
                break

        if not agent_config:
            return False

        permissions = PERMISSION_MATRIX.get(agent_config["role"], set())
        return permissions == {Permission.READ}

    @classmethod
    def get_capabilities(cls, agent_id: str) -> List[str]:
        """Get agent capabilities."""
        agent_config = None
        for key, config in cls.AGENTS.items():
            if config["agent_id"] == agent_id:
                agent_config = config
                break

        if not agent_config:
            return []

        role = agent_config["role"]
        return CAPABILITIES.get(role, [])

    @classmethod
    def update_operational_state(
        cls,
        db: Session,
        tenant_id: str,
        agent_id: str,
        state: OperationalState,
    ) -> bool:
        """Update agent operational state for a specific tenant."""
        if not tenant_id or not agent_id:
            logger.error(f"update_operational_state: Missing tenant_id or agent_id")
            return False

        try:
            service = TenantAgentStateService(db)
            success = service.update_status(tenant_id, agent_id, state.value)
            if success:
                logger.info(f"Agent {agent_id} in tenant {tenant_id} state updated to {state.value}")
            return success
        except Exception as e:
            logger.error(f"Error updating operational state: {e}")
            return False

    @classmethod
    def update_connectivity_state(
        cls,
        db: Session,
        tenant_id: str,
        agent_id: str,
        state: ConnectivityState,
    ) -> bool:
        """Update agent connectivity state for a specific tenant."""
        if not tenant_id or not agent_id:
            logger.error(f"update_connectivity_state: Missing tenant_id or agent_id")
            return False

        try:
            service = TenantAgentStateService(db)
            success = service.update_connectivity_status(tenant_id, agent_id, state.value)
            if success:
                logger.info(f"Agent {agent_id} in tenant {tenant_id} connectivity updated to {state.value}")
            return success
        except Exception as e:
            logger.error(f"Error updating connectivity state: {e}")
            return False
