"""add_payment_and_expense_share_payment_tables

Revision ID: 75042fb02c73
Revises: 4eb4e454b292
Create Date: 2025-06-01 12:41:22.491320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '75042fb02c73'
down_revision: Union[str, None] = '4eb4e454b292'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('household_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('payment_type', sa.Enum('REIMBURSEMENT', 'EXPENSE_PAYMENT', 'ADJUSTMENT', name='paymenttype'), nullable=False),
        sa.Column('payment_method', sa.Enum('CASH', 'BANK_TRANSFER', 'CREDIT_CARD', 'DIGITAL_WALLET', 'CHECK', 'OTHER', name='paymentmethod'), nullable=True),
        sa.Column('payment_date', sa.DateTime(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for payments table
    op.create_index(op.f('ix_payments_amount'), 'payments', ['amount'], unique=False)
    op.create_index(op.f('ix_payments_currency'), 'payments', ['currency'], unique=False)
    op.create_index(op.f('ix_payments_household_id'), 'payments', ['household_id'], unique=False)
    op.create_index(op.f('ix_payments_payee_id'), 'payments', ['payee_id'], unique=False)
    op.create_index(op.f('ix_payments_payer_id'), 'payments', ['payer_id'], unique=False)
    op.create_index(op.f('ix_payments_payment_date'), 'payments', ['payment_date'], unique=False)
    op.create_index(op.f('ix_payments_payment_method'), 'payments', ['payment_method'], unique=False)
    op.create_index(op.f('ix_payments_payment_type'), 'payments', ['payment_type'], unique=False)
    
    # Create expense_share_payments table
    op.create_table(
        'expense_share_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expense_share_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('allocated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['expense_share_id'], ['expense_shares.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for expense_share_payments table
    op.create_index(op.f('ix_expense_share_payments_allocated_at'), 'expense_share_payments', ['allocated_at'], unique=False)
    op.create_index(op.f('ix_expense_share_payments_amount'), 'expense_share_payments', ['amount'], unique=False)
    op.create_index(op.f('ix_expense_share_payments_expense_share_id'), 'expense_share_payments', ['expense_share_id'], unique=False)
    op.create_index(op.f('ix_expense_share_payments_payment_id'), 'expense_share_payments', ['payment_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index(op.f('ix_expense_share_payments_payment_id'), table_name='expense_share_payments')
    op.drop_index(op.f('ix_expense_share_payments_expense_share_id'), table_name='expense_share_payments')
    op.drop_index(op.f('ix_expense_share_payments_amount'), table_name='expense_share_payments')
    op.drop_index(op.f('ix_expense_share_payments_allocated_at'), table_name='expense_share_payments')
    
    op.drop_index(op.f('ix_payments_payment_type'), table_name='payments')
    op.drop_index(op.f('ix_payments_payment_method'), table_name='payments')
    op.drop_index(op.f('ix_payments_payment_date'), table_name='payments')
    op.drop_index(op.f('ix_payments_payer_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_payee_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_household_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_currency'), table_name='payments')
    op.drop_index(op.f('ix_payments_amount'), table_name='payments')
    
    # Drop tables
    op.drop_table('expense_share_payments')
    op.drop_table('payments')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS paymentmethod')
    op.execute('DROP TYPE IF EXISTS paymenttype')
