"""TenantAgentState service for multi-tenant agent state management (PHASE 1.1)."""

import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from database.models import TenantAgentState, Agent
from app.services.base import BaseService
# P0 FIX: Import states from independent module to avoid circular import
from app.services.agent_states import OperationalState, ConnectivityState

logger = logging.getLogger(__name__)


def utc_now():
    return datetime.now(timezone.utc)


class TenantAgentStateService(BaseService[TenantAgentState]):
    """Service for tenant-scoped agent state queries with isolation."""

    def __init__(self, db: Session):
        """Initialize with TenantAgentState model."""
        super().__init__(TenantAgentState, db)

    def get_or_create(
        self,
        tenant_id: str,
        agent_id: str
    ) -> TenantAgentState:
        """Get or create tenant-scoped agent state."""
        try:
            # Try to get existing
            state = self.db.query(TenantAgentState).filter(
                TenantAgentState.tenant_id == tenant_id,
                TenantAgentState.agent_id == agent_id
            ).first()

            # Create if not found
            if not state:
                state = TenantAgentState(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    status="IDLE",
                    connectivity_status="UNKNOWN"
                )
                self.db.add(state)
                self.db.commit()
                logger.info(f"Created TenantAgentState: tenant={tenant_id}, agent={agent_id}")

            return state
        except Exception as e:
            self.logger.error(f"Error getting/creating state for {tenant_id}/{agent_id}: {e}")
            self.db.rollback()
            raise

    def update_status(
        self,
        tenant_id: str,
        agent_id: str,
        status: str
    ) -> bool:
        """Update operational status (IDLE, WORKING, ERROR)."""
        try:
            state = self.get_or_create(tenant_id, agent_id)
            state.status = status
            state.last_event_at = utc_now()
            self.db.commit()
            logger.info(f"Updated status: {tenant_id}/{agent_id} → {status}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
            return False

    def update_connectivity_status(
        self,
        tenant_id: str,
        agent_id: str,
        connectivity_status: str
    ) -> bool:
        """Update connectivity status (ONLINE, OFFLINE, STALE, UNKNOWN)."""
        try:
            state = self.get_or_create(tenant_id, agent_id)
            state.connectivity_status = connectivity_status
            state.last_event_at = utc_now()

            # If transitioning to ONLINE, record the health check time
            if connectivity_status == "ONLINE":
                state.last_health_check = utc_now()

            self.db.commit()
            logger.info(f"Updated connectivity: {tenant_id}/{agent_id} → {connectivity_status}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating connectivity: {e}")
            return False

    def update_with_transaction_lock(
        self,
        tenant_id: str,
        agent_id: str,
        new_status: str,
        connectivity_status: Optional[str] = None
    ) -> bool:
        """Update state with transaction lock (SELECT FOR UPDATE).

        ETAPA 2: INSERT ON CONFLICT for concurrent creation.
        Order: INSERT ON CONFLICT → SELECT FOR UPDATE → UPDATE → COMMIT
        """
        try:
            # 1. Ensure row exists (atomic INSERT ... ON CONFLICT)
            from sqlalchemy import text
            self.db.execute(text("""
                INSERT INTO tenant_agent_states
                (tenant_id, agent_id, status, connectivity_status, subscription_status, executor_status, created_at, updated_at)
                VALUES (:tenant_id, :agent_id, 'IDLE', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', NOW(), NOW())
                ON CONFLICT (tenant_id, agent_id) DO NOTHING
            """), {"tenant_id": tenant_id, "agent_id": agent_id})

            # 2. Now lock the row (guaranteed to exist)
            state = self.db.query(TenantAgentState).filter(
                TenantAgentState.tenant_id == tenant_id,
                TenantAgentState.agent_id == agent_id
            ).with_for_update().first()

            if state:
                # 3. Update locked row
                state.status = new_status
                if connectivity_status:
                    state.connectivity_status = connectivity_status
                state.last_event_at = utc_now()

            self.db.commit()
            logger.info(f"Transaction locked update (ETAPA 2): {tenant_id}/{agent_id} → {new_status}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Transaction lock update failed (ETAPA 2): {e}")
            return False

    def get_by_tenant_and_agent(
        self,
        tenant_id: str,
        agent_id: str
    ) -> Optional[TenantAgentState]:
        """Get agent state for a specific tenant."""
        try:
            return self.db.query(TenantAgentState).filter(
                TenantAgentState.tenant_id == tenant_id,
                TenantAgentState.agent_id == agent_id
            ).first()
        except Exception as e:
            self.logger.error(f"Error fetching state: {e}")
            return None

    def list_by_tenant(
        self,
        tenant_id: str,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[TenantAgentState], int]:
        """List all agent states for a tenant."""
        try:
            query = self.db.query(TenantAgentState).filter(
                TenantAgentState.tenant_id == tenant_id
            )
            total = query.count()

            states = (
                query.order_by(TenantAgentState.updated_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return states, total
        except Exception as e:
            self.logger.error(f"Error listing states: {e}")
            return [], 0

    def list_by_agent(
        self,
        agent_id: str,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[TenantAgentState], int]:
        """List agent states across all tenants (admin only)."""
        try:
            query = self.db.query(TenantAgentState).filter(
                TenantAgentState.agent_id == agent_id
            )
            total = query.count()

            states = (
                query.order_by(TenantAgentState.updated_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return states, total
        except Exception as e:
            self.logger.error(f"Error listing states by agent: {e}")
            return [], 0

    def validate_tenant_isolation(
        self,
        tenant_id_a: str,
        tenant_id_b: str,
        agent_id: str
    ) -> bool:
        """Validate that two tenants have isolated states for the same agent."""
        try:
            state_a = self.get_by_tenant_and_agent(tenant_id_a, agent_id)
            state_b = self.get_by_tenant_and_agent(tenant_id_b, agent_id)

            # Both should exist
            if not state_a or not state_b:
                logger.error(f"States not found: A={state_a is not None}, B={state_b is not None}")
                return False

            # PKs must be different (tenant_id part differs)
            if state_a.tenant_id == state_b.tenant_id:
                logger.error("Tenant IDs are the same - isolation failed")
                return False

            # Agent IDs must be same
            if state_a.agent_id != state_b.agent_id:
                logger.error("Agent IDs don't match - isolation check invalid")
                return False

            logger.info(f"Isolation validated: {tenant_id_a} and {tenant_id_b} have separate states for {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error validating isolation: {e}")
            return False

    def record_heartbeat(
        self,
        tenant_id: str,
        agent_id: str
    ) -> bool:
        """B3 ETAPA 3: Record heartbeat for agent (transactional).

        Updates last_heartbeat_at atomically, preserving operational_state.
        Ensures heartbeat from newer timestamp is not overwritten.
        """
        try:
            # 1. Lock row (SELECT FOR UPDATE)
            state = self.db.query(TenantAgentState).filter(
                TenantAgentState.tenant_id == tenant_id,
                TenantAgentState.agent_id == agent_id
            ).with_for_update().first()

            if not state:
                logger.warning(f"Agent state not found: {tenant_id}/{agent_id}")
                return False

            now = utc_now()

            # 2. Only update if new heartbeat is more recent
            if state.last_heartbeat_at is None or now > state.last_heartbeat_at:
                state.last_heartbeat_at = now
                # operational_state preserved (not changed)
                self.db.commit()
                logger.info(f"Heartbeat recorded: {tenant_id}/{agent_id} at {now}")
                return True
            else:
                # Heartbeat is older, don't overwrite
                self.db.rollback()
                logger.debug(f"Heartbeat older than current, skipped: {tenant_id}/{agent_id}")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording heartbeat: {e}")
            return False

    def detect_connectivity_status(
        self,
        tenant_id: str,
        agent_id: str
    ) -> str:
        """B3 ETAPA 3: Detect connectivity status based on heartbeat.

        Returns: ONLINE, STALE, OFFLINE, or UNKNOWN
        Policy:
        - <= 60s: ONLINE
        - 60-300s: STALE
        - > 300s: OFFLINE
        - No heartbeat: UNKNOWN
        """
        try:
            state = self.db.query(TenantAgentState).filter(
                TenantAgentState.tenant_id == tenant_id,
                TenantAgentState.agent_id == agent_id
            ).first()

            if not state or state.last_heartbeat_at is None:
                return ConnectivityState.UNKNOWN.value

            elapsed = (utc_now() - state.last_heartbeat_at).total_seconds()

            if elapsed <= 60:
                return ConnectivityState.ONLINE.value
            elif elapsed <= 300:
                return ConnectivityState.STALE.value
            else:
                return ConnectivityState.OFFLINE.value

        except Exception as e:
            logger.error(f"Error detecting connectivity: {e}")
            return ConnectivityState.UNKNOWN.value
