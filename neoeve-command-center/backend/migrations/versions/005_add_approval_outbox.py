"""Add ApprovalOutbox table for transactional event publication.

Revision ID: 005
Revises: 004
Create Date: 2026-11-23 10:00:00.000000

ETAPA 4: Transactional Outbox pattern for Approval events
- Guarantees atomicity between Validation creation and Event publication
- Supports retry with backoff and idempotency
- Tracks publication status for eventual consistency
"""
from alembic import op
import sqlalchemy as sa


revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Create approval_outbox table with retry and idempotency support."""

    op.create_table(
        'approval_outbox',
        sa.Column('event_id', sa.String(64), nullable=False, primary_key=True),
        sa.Column('approval_id', sa.String(64), nullable=False),
        sa.Column('validation_id', sa.String(64), nullable=False),
        sa.Column('event_type', sa.String(32), nullable=False),  # approval.requested, approval.approved, etc.

        # Multi-tenant isolation
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('project_id', sa.String(64), nullable=False),
        sa.Column('actor_id', sa.String(64), nullable=False),

        # Payload
        sa.Column('payload', sa.Text(), nullable=False),  # JSON

        # Publication status
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),  # PENDING, PUBLISHED, FAILED

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_attempted_at', sa.DateTime(timezone=True), nullable=True),

        # Retry mechanism
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Idempotency key for deduplication
        sa.Column('idempotency_key', sa.String(100), nullable=False),

        # Foreign key to validations table
        sa.ForeignKeyConstraint(['validation_id'], ['validations.validation_id'], name='fk_approval_outbox_validation'),
    )

    # Create indexes for efficient querying
    op.create_index('idx_approval_outbox_event_id', 'approval_outbox', ['event_id'])
    op.create_index('idx_approval_outbox_approval_id', 'approval_outbox', ['approval_id'])
    op.create_index('idx_approval_outbox_validation_id', 'approval_outbox', ['validation_id'])
    op.create_index('idx_approval_outbox_tenant_project', 'approval_outbox', ['tenant_id', 'project_id'])
    op.create_index('idx_approval_outbox_status', 'approval_outbox', ['status'])
    op.create_index('idx_approval_outbox_created', 'approval_outbox', ['created_at'])
    op.create_index('idx_approval_outbox_idempotency_key', 'approval_outbox', ['idempotency_key'])

    # Create unique constraints for data integrity
    op.create_unique_constraint('uq_approval_outbox_event_id', 'approval_outbox', ['event_id'])
    op.create_unique_constraint(
        'uq_approval_outbox_idempotency',
        'approval_outbox',
        ['idempotency_key', 'tenant_id', 'project_id']
    )


def downgrade():
    """Drop approval_outbox table."""

    op.drop_constraint('uq_approval_outbox_idempotency', 'approval_outbox', type_='unique')
    op.drop_constraint('uq_approval_outbox_event_id', 'approval_outbox', type_='unique')
    op.drop_constraint('fk_approval_outbox_validation', 'approval_outbox', type_='foreignkey')

    op.drop_index('idx_approval_outbox_idempotency_key')
    op.drop_index('idx_approval_outbox_created')
    op.drop_index('idx_approval_outbox_status')
    op.drop_index('idx_approval_outbox_tenant_project')
    op.drop_index('idx_approval_outbox_validation_id')
    op.drop_index('idx_approval_outbox_approval_id')
    op.drop_index('idx_approval_outbox_event_id')

    op.drop_table('approval_outbox')
