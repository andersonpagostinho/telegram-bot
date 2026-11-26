"""Add recovery service models for ETAPA 2.1.

Revision ID: 006_recovery_service
Revises: 005_add_approval_outbox
Create Date: 2026-11-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006_recovery_service'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Create ExecutionAttempt, EventIdempotencyKey tables and extend Execution model."""

    # Add columns to executions table for recovery
    op.add_column('executions', sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('executions', sa.Column('fencing_token', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('executions', sa.Column('worker_id', sa.String(64), nullable=True))
    op.add_column('executions', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('executions', sa.Column('failure_classification', sa.String(32), nullable=True))
    op.add_column('executions', sa.Column('last_failure_reason', sa.Text(), nullable=True))
    op.add_column('executions', sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('executions', sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('executions', sa.Column('tenant_id', sa.String(64), nullable=False, server_default='unknown'))
    op.add_column('executions', sa.Column('project_id', sa.String(64), nullable=False, server_default='unknown'))
    op.add_column('executions', sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=True))

    # Create indices for recovery operations
    op.create_index('idx_execution_tenant', 'executions', ['tenant_id'])
    op.create_index('idx_execution_project', 'executions', ['project_id'])
    op.create_index('idx_execution_status_tenant', 'executions', ['status', 'tenant_id'])
    op.create_index('idx_execution_lease_expired', 'executions', ['lease_expires_at'])
    op.create_index('idx_execution_next_retry', 'executions', ['next_retry_at'])

    # Create ExecutionAttempt table (audit trail)
    op.create_table(
        'execution_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('execution_id', sa.String(64), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('worker_id', sa.String(64), nullable=True),
        sa.Column('fencing_token', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('failure_classification', sa.String(32), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.execution_id'], ),
        sa.UniqueConstraint('execution_id', 'attempt_number', 'fencing_token', name='uq_execution_attempt_token')
    )

    # Create indices on ExecutionAttempt
    op.create_index('idx_execution_attempt_execution', 'execution_attempts', ['execution_id'])
    op.create_index('idx_execution_attempt_tenant', 'execution_attempts', ['tenant_id'])

    # Create EventIdempotencyKey table (deduplication)
    op.create_table(
        'event_idempotency_keys',
        sa.Column('idempotency_key', sa.String(256), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('execution_id', sa.String(64), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('idempotency_key')
    )

    # Create indices on EventIdempotencyKey
    op.create_index('idx_event_key_tenant', 'event_idempotency_keys', ['tenant_id'])
    op.create_index('idx_event_key_execution', 'event_idempotency_keys', ['execution_id'])


def downgrade():
    """Rollback: remove recovery service models and columns."""

    # Drop EventIdempotencyKey table
    op.drop_index('idx_event_key_execution', table_name='event_idempotency_keys')
    op.drop_index('idx_event_key_tenant', table_name='event_idempotency_keys')
    op.drop_table('event_idempotency_keys')

    # Drop ExecutionAttempt table
    op.drop_index('idx_execution_attempt_tenant', table_name='execution_attempts')
    op.drop_index('idx_execution_attempt_execution', table_name='execution_attempts')
    op.drop_table('execution_attempts')

    # Remove columns from executions table
    op.drop_index('idx_execution_next_retry', table_name='executions')
    op.drop_index('idx_execution_lease_expired', table_name='executions')
    op.drop_index('idx_execution_status_tenant', table_name='executions')
    op.drop_index('idx_execution_project', table_name='executions')
    op.drop_index('idx_execution_tenant', table_name='executions')

    op.drop_column('executions', 'last_updated_at')
    op.drop_column('executions', 'project_id')
    op.drop_column('executions', 'tenant_id')
    op.drop_column('executions', 'max_attempts')
    op.drop_column('executions', 'next_retry_at')
    op.drop_column('executions', 'last_failure_reason')
    op.drop_column('executions', 'failure_classification')
    op.drop_column('executions', 'lease_expires_at')
    op.drop_column('executions', 'worker_id')
    op.drop_column('executions', 'fencing_token')
    op.drop_column('executions', 'attempt_number')
