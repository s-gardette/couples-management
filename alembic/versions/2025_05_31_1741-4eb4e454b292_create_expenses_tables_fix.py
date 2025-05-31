"""create_expenses_tables_fix

Revision ID: 4eb4e454b292
Revises: 2025_05_28_1130
Create Date: 2025-05-31 17:41:47.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4eb4e454b292'
down_revision: Union[str, None] = '2025_05_28_1130'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for user household roles
    op.execute("CREATE TYPE userhouseholdrole AS ENUM ('admin', 'member')")
    
    # Create households table
    op.create_table('households',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('invite_code', sa.String(length=20), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_households_created_at'), 'households', ['created_at'], unique=False)
    op.create_index(op.f('ix_households_created_by'), 'households', ['created_by'], unique=False)
    op.create_index(op.f('ix_households_id'), 'households', ['id'], unique=False)
    op.create_index(op.f('ix_households_invite_code'), 'households', ['invite_code'], unique=True)
    op.create_index(op.f('ix_households_is_active'), 'households', ['is_active'], unique=False)
    op.create_index(op.f('ix_households_name'), 'households', ['name'], unique=False)

    # Create user_households table (using existing enum type)
    op.create_table('user_households',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('household_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'member', name='userhouseholdrole', create_type=False), nullable=False),
        sa.Column('nickname', sa.String(length=100), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_households_created_at'), 'user_households', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_households_household_id'), 'user_households', ['household_id'], unique=False)
    op.create_index(op.f('ix_user_households_id'), 'user_households', ['id'], unique=False)
    op.create_index(op.f('ix_user_households_is_active'), 'user_households', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_households_joined_at'), 'user_households', ['joined_at'], unique=False)
    op.create_index(op.f('ix_user_households_role'), 'user_households', ['role'], unique=False)
    op.create_index(op.f('ix_user_households_user_id'), 'user_households', ['user_id'], unique=False)

    # Create categories table
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('household_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_created_at'), 'categories', ['created_at'], unique=False)
    op.create_index(op.f('ix_categories_household_id'), 'categories', ['household_id'], unique=False)
    op.create_index(op.f('ix_categories_id'), 'categories', ['id'], unique=False)
    op.create_index(op.f('ix_categories_is_active'), 'categories', ['is_active'], unique=False)
    op.create_index(op.f('ix_categories_is_default'), 'categories', ['is_default'], unique=False)
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=False)

    # Create expenses table
    op.create_table('expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('household_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('receipt_url', sa.String(length=500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(length=50)), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expenses_amount'), 'expenses', ['amount'], unique=False)
    op.create_index(op.f('ix_expenses_category_id'), 'expenses', ['category_id'], unique=False)
    op.create_index(op.f('ix_expenses_created_at'), 'expenses', ['created_at'], unique=False)
    op.create_index(op.f('ix_expenses_created_by'), 'expenses', ['created_by'], unique=False)
    op.create_index(op.f('ix_expenses_currency'), 'expenses', ['currency'], unique=False)
    op.create_index(op.f('ix_expenses_expense_date'), 'expenses', ['expense_date'], unique=False)
    op.create_index(op.f('ix_expenses_household_id'), 'expenses', ['household_id'], unique=False)
    op.create_index(op.f('ix_expenses_id'), 'expenses', ['id'], unique=False)
    op.create_index(op.f('ix_expenses_is_active'), 'expenses', ['is_active'], unique=False)
    op.create_index(op.f('ix_expenses_title'), 'expenses', ['title'], unique=False)

    # Create expense_shares table
    op.create_table('expense_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('expense_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_household_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('share_amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('share_percentage', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('is_paid', sa.Boolean(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('payment_notes', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_household_id'], ['user_households.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expense_shares_created_at'), 'expense_shares', ['created_at'], unique=False)
    op.create_index(op.f('ix_expense_shares_expense_id'), 'expense_shares', ['expense_id'], unique=False)
    op.create_index(op.f('ix_expense_shares_id'), 'expense_shares', ['id'], unique=False)
    op.create_index(op.f('ix_expense_shares_is_active'), 'expense_shares', ['is_active'], unique=False)
    op.create_index(op.f('ix_expense_shares_is_paid'), 'expense_shares', ['is_paid'], unique=False)
    op.create_index(op.f('ix_expense_shares_paid_at'), 'expense_shares', ['paid_at'], unique=False)
    op.create_index(op.f('ix_expense_shares_share_amount'), 'expense_shares', ['share_amount'], unique=False)
    op.create_index(op.f('ix_expense_shares_user_household_id'), 'expense_shares', ['user_household_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('expense_shares')
    op.drop_table('expenses')
    op.drop_table('categories')
    op.drop_table('user_households')
    op.drop_table('households')
    
    # Drop enum type
    op.execute("DROP TYPE userhouseholdrole")
