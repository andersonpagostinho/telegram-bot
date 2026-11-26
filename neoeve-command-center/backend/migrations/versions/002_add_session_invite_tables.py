"""Add RefreshSession, RefreshToken, and InviteToken tables.

Revision ID: 002
Revises: 001
Create Date: 2026-11-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Create RefreshSession, RefreshToken, and InviteToken tables."""

    # Create RefreshSession table
    op.create_table(
        'refresh_sessions',
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('user_id', sa.String(64), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('family_id', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoke_reason', sa.String(256), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint('session_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='fk_refresh_session_user_id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], name='fk_refresh_session_tenant_id'),
    )

    # Create indexes on RefreshSession
    op.create_index('idx_refresh_session_user', 'refresh_sessions', ['user_id'])
    op.create_index('idx_refresh_session_tenant', 'refresh_sessions', ['tenant_id'])
    op.create_index('idx_refresh_session_expires_at', 'refresh_sessions', ['expires_at'])
    op.create_index('idx_refresh_session_family', 'refresh_sessions', ['family_id'])

    # Create RefreshToken table
    op.create_table(
        'refresh_tokens',
        sa.Column('refresh_token_id', sa.String(64), nullable=False),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('token_hash', sa.String(256), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replaced_by_token_id', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('refresh_token_id'),
        sa.ForeignKeyConstraint(['session_id'], ['refresh_sessions.session_id'], name='fk_refresh_token_session_id'),
        sa.ForeignKeyConstraint(['replaced_by_token_id'], ['refresh_tokens.refresh_token_id'], name='fk_refresh_token_replaced_by'),
    )

    # Create indexes on RefreshToken
    op.create_index('idx_refresh_token_session', 'refresh_tokens', ['session_id'])
    op.create_index('idx_refresh_token_expires_at', 'refresh_tokens', ['expires_at'])
    op.create_unique_constraint('uq_refresh_token_hash', 'refresh_tokens', ['token_hash'])

    # Create InviteToken table
    op.create_table(
        'invite_tokens',
        sa.Column('invite_id', sa.String(64), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('email', sa.String(256), nullable=False),
        sa.Column('role', sa.String(32), nullable=False),
        sa.Column('token_hash', sa.String(256), nullable=False, unique=True),
        sa.Column('created_by_user_id', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('invite_id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], name='fk_invite_token_tenant_id'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], name='fk_invite_token_creator_id'),
    )

    # Create indexes on InviteToken
    op.create_index('idx_invite_token_tenant', 'invite_tokens', ['tenant_id'])
    op.create_index('idx_invite_token_email', 'invite_tokens', ['email'])
    op.create_index('idx_invite_token_expires_at', 'invite_tokens', ['expires_at'])
    op.create_unique_constraint('uq_invite_token_hash', 'invite_tokens', ['token_hash'])


def downgrade():
    """Drop RefreshSession, RefreshToken, and InviteToken tables."""

    # Drop InviteToken first
    op.drop_constraint('uq_invite_token_hash', 'invite_tokens', type_='unique')
    op.drop_index('idx_invite_token_expires_at')
    op.drop_index('idx_invite_token_email')
    op.drop_index('idx_invite_token_tenant')
    op.drop_constraint('fk_invite_token_creator_id', 'invite_tokens', type_='foreignkey')
    op.drop_constraint('fk_invite_token_tenant_id', 'invite_tokens', type_='foreignkey')
    op.drop_table('invite_tokens')

    # Drop RefreshToken
    op.drop_constraint('uq_refresh_token_hash', 'refresh_tokens', type_='unique')
    op.drop_index('idx_refresh_token_expires_at')
    op.drop_index('idx_refresh_token_session')
    op.drop_constraint('fk_refresh_token_replaced_by', 'refresh_tokens', type_='foreignkey')
    op.drop_constraint('fk_refresh_token_session_id', 'refresh_tokens', type_='foreignkey')
    op.drop_table('refresh_tokens')

    # Drop RefreshSession
    op.drop_index('idx_refresh_session_family')
    op.drop_index('idx_refresh_session_expires_at')
    op.drop_index('idx_refresh_session_tenant')
    op.drop_index('idx_refresh_session_user')
    op.drop_constraint('fk_refresh_session_tenant_id', 'refresh_sessions', type_='foreignkey')
    op.drop_constraint('fk_refresh_session_user_id', 'refresh_sessions', type_='foreignkey')
    op.drop_table('refresh_sessions')
