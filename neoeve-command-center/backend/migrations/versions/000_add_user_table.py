"""Add User table for authentication.

Revision ID: 000
Revises: d19e221b7b2a
Create Date: 2026-11-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '000'
down_revision = 'd19e221b7b2a'
branch_labels = None
depends_on = None


def upgrade():
    """Create User table."""

    # Create User table
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(64), nullable=False),
        sa.Column('email', sa.String(256), nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('user_id'),
    )

    # Create indexes on User
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_user_is_active', 'users', ['is_active'])
    op.create_index('idx_user_created_at', 'users', ['created_at'])

    # Create partial unique index for email (active users only)
    # Email must be unique among users with deleted_at IS NULL
    # This allows email reuse after soft-delete
    op.create_index(
        'uq_user_email_active',
        'users',
        ['email'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade():
    """Drop User table."""

    op.drop_index('uq_user_email_active')
    op.drop_index('idx_user_created_at')
    op.drop_index('idx_user_is_active')
    op.drop_index('idx_user_email')
    op.drop_table('users')
