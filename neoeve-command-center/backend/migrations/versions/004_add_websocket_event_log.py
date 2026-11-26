"""Add WebSocketEventLog table for event recovery mechanism.

Revision ID: 004
Revises: 003
Create Date: 2026-11-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create websocket_event_log table for reconnection recovery."""

    op.create_table(
        'websocket_event_log',
        sa.Column('sequence', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('event_id', sa.String(64), nullable=False, unique=True),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('project_id', sa.String(64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('ttl_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('sequence'),
    )

    # Create indexes
    op.create_index('idx_websocket_event_tenant', 'websocket_event_log', ['tenant_id'])
    op.create_index('idx_websocket_event_created', 'websocket_event_log', ['created_at'])
    op.create_index('idx_websocket_event_ttl', 'websocket_event_log', ['ttl_expires_at'])
    op.create_unique_constraint('uq_websocket_event_id', 'websocket_event_log', ['event_id'])


def downgrade():
    """Drop websocket_event_log table."""

    op.drop_constraint('uq_websocket_event_id', 'websocket_event_log', type_='unique')
    op.drop_index('idx_websocket_event_ttl')
    op.drop_index('idx_websocket_event_created')
    op.drop_index('idx_websocket_event_tenant')
    op.drop_table('websocket_event_log')
