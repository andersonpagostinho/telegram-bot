"""Fix email uniqueness to be case-insensitive using LOWER().

Revision ID: 003
Revises: 002
Create Date: 2026-11-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Replace email index with case-insensitive LOWER(email) index."""

    # Drop old case-sensitive unique index
    op.drop_index('uq_user_email_active')

    # Create new case-insensitive unique index using LOWER(email)
    # This ensures ABC@example.com and abc@example.com are treated as identical
    op.create_index(
        'uq_user_email_active',
        'users',
        [sa.text('LOWER(email)')],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade():
    """Revert to case-sensitive email index."""

    # Drop case-insensitive index
    op.drop_index('uq_user_email_active')

    # Recreate case-sensitive index
    op.create_index(
        'uq_user_email_active',
        'users',
        ['email'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
