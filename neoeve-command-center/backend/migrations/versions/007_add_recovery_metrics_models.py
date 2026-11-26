"""Add RecoveryMetrics and RecoveryHistory models for dashboard.

Revision ID: 007
Revises: 006
Create Date: 2026-11-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006_recovery_service'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create recovery_metrics table
    # NOTE: index=True creates individual column indices in PostgreSQL
    # We only use composite indices via op.create_index() below
    op.create_table(
        'recovery_metrics',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('metric_type', sa.String(64), nullable=False),
        sa.Column('metric_value', sa.Integer(), nullable=False, default=0),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('failure_classification', sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indices for recovery_metrics (avoid duplicates with composite indices)
    op.create_index(
        'idx_recovery_metrics_tenant_type',
        'recovery_metrics',
        ['tenant_id', 'metric_type']
    )
    op.create_index(
        'idx_recovery_metrics_recorded_at',
        'recovery_metrics',
        ['recorded_at']
    )

    # Create recovery_history table (audit trail)
    # NOTE: Removed inline index=True to avoid duplicate indices
    op.create_table(
        'recovery_history',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('execution_id', sa.String(64), nullable=False),
        sa.Column('mission_id', sa.String(64), nullable=False),
        sa.Column('task_id', sa.String(64), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('worker_id', sa.String(64), nullable=True),
        sa.Column('fencing_token', sa.Integer(), nullable=False),
        sa.Column('failure_classification', sa.String(32), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indices for recovery_history
    op.create_index(
        'idx_recovery_history_tenant',
        'recovery_history',
        ['tenant_id']
    )
    op.create_index(
        'idx_recovery_history_execution',
        'recovery_history',
        ['execution_id']
    )
    op.create_index(
        'idx_recovery_history_attempted_at',
        'recovery_history',
        ['attempted_at']
    )
    op.create_index(
        'idx_recovery_history_next_retry',
        'recovery_history',
        ['next_retry_at']
    )


def downgrade() -> None:
    # Drop recovery_history table and indices
    op.drop_index('idx_recovery_history_next_retry', table_name='recovery_history')
    op.drop_index('idx_recovery_history_attempted_at', table_name='recovery_history')
    op.drop_index('idx_recovery_history_execution', table_name='recovery_history')
    op.drop_index('idx_recovery_history_tenant', table_name='recovery_history')
    op.drop_table('recovery_history')

    # Drop recovery_metrics table and indices
    op.drop_index('idx_recovery_metrics_recorded_at', table_name='recovery_metrics')
    op.drop_index('idx_recovery_metrics_tenant_type', table_name='recovery_metrics')
    op.drop_table('recovery_metrics')
