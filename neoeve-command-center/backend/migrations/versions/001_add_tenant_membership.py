"""Add Tenant and Membership tables for multi-tenant authentication.

Revision ID: 001
Revises:
Create Date: 2026-11-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '001'
down_revision = '000'
branch_labels = None
depends_on = None


def upgrade():
    """Create Tenant and Membership tables."""

    # Create Tenant table
    op.create_table(
        'tenants',
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('tenant_id'),
    )

    # Create indexes on Tenant
    op.create_index('idx_tenant_is_active', 'tenants', ['is_active'])
    op.create_index('idx_tenant_created_at', 'tenants', ['created_at'])

    # Create Membership table
    op.create_table(
        'memberships',
        sa.Column('membership_id', sa.String(64), nullable=False),
        sa.Column('user_id', sa.String(64), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('role', sa.String(32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('membership_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='fk_membership_user_id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], name='fk_membership_tenant_id'),
    )

    # Create indexes on Membership
    op.create_index('idx_membership_user', 'memberships', ['user_id'])
    op.create_index('idx_membership_tenant', 'memberships', ['tenant_id'])
    op.create_index('idx_membership_user_tenant', 'memberships', ['user_id', 'tenant_id'])

    # Create unique index (user_id + tenant_id must be unique when deleted_at is NULL)
    op.create_index(
        'uq_membership_user_tenant_active',
        'memberships',
        ['user_id', 'tenant_id'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade():
    """Drop Tenant and Membership tables."""

    # Drop Membership first (FK constraint)
    op.drop_index('uq_membership_user_tenant_active')
    op.drop_index('idx_membership_user_tenant')
    op.drop_index('idx_membership_tenant')
    op.drop_index('idx_membership_user')
    op.drop_constraint('fk_membership_tenant_id', 'memberships', type_='foreignkey')
    op.drop_constraint('fk_membership_user_id', 'memberships', type_='foreignkey')
    op.drop_table('memberships')

    # Drop Tenant
    op.drop_index('idx_tenant_created_at')
    op.drop_index('idx_tenant_is_active')
    op.drop_table('tenants')
