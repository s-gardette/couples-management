"""add_user_role_and_admin_fields

Revision ID: add_user_role_and_admin_fields
Revises: 2a3eed298b83
Create Date: 2025-05-28 14:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_user_role_and_admin_fields'
down_revision: Union[str, None] = '2a3eed298b83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum type for user roles
    user_role_enum = sa.Enum('admin', 'user', name='userrole')
    user_role_enum.create(op.get_bind())
    
    # Add new columns to users table
    op.add_column('users', sa.Column('role', user_role_enum, nullable=False, server_default='user'))
    op.add_column('users', sa.Column('created_by_admin_id', sa.String(36), nullable=True))
    op.add_column('users', sa.Column('requires_password_change', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create indexes
    op.create_index('ix_users_role', 'users', ['role'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_users_role', 'users')
    
    # Drop columns
    op.drop_column('users', 'requires_password_change')
    op.drop_column('users', 'created_by_admin_id')
    op.drop_column('users', 'role')
    
    # Drop enum type
    user_role_enum = sa.Enum('admin', 'user', name='userrole')
    user_role_enum.drop(op.get_bind()) 