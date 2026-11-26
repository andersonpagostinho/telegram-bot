"""Add heartbeat tracking to TenantAgentState (B3 ETAPA 3)."""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = '0003_heartbeat'
down_revision = '0002_tenant_agent_state'  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    """Add last_heartbeat_at column to track agent heartbeat.

    SEMANTIC FIX: nullable=True (no artificial timestamps)
    - Registros sem heartbeat real começam com NULL
    - detect_connectivity_status(NULL) retorna UNKNOWN
    - Apenas record_heartbeat() atualiza com timestamp real
    """

    # Add new column WITHOUT default value (avoid artificial heartbeat)
    op.add_column(
        'tenant_agent_states',
        sa.Column(
            'last_heartbeat_at',
            sa.DateTime(timezone=True),
            nullable=True,  # SEMANTIC FIX: Allow NULL until real heartbeat
            server_default=None,  # SEMANTIC FIX: No artificial timestamp
            comment='Timestamp of last heartbeat from agent (UTC, NULL until first real heartbeat)'
        )
    )

    # Create index for efficient STALE/OFFLINE detection
    op.create_index(
        'idx_tenant_agent_state_heartbeat',
        'tenant_agent_states',
        ['tenant_id', 'last_heartbeat_at'],
        postgresql_where=sa.text("connectivity_status != 'ONLINE'")
    )

    print("✅ Migration: Added last_heartbeat_at to tenant_agent_states")


def downgrade():
    """Remove heartbeat tracking."""

    # Drop index
    op.drop_index(
        'idx_tenant_agent_state_heartbeat',
        table_name='tenant_agent_states'
    )

    # Remove column
    op.drop_column(
        'tenant_agent_states',
        'last_heartbeat_at'
    )

    print("✅ Migration downgraded: Removed last_heartbeat_at")

