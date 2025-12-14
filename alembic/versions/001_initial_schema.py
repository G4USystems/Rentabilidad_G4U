"""Initial schema with all models

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.Enum('revenue', 'other_income', 'cogs', 'operating_expense',
                                   'payroll', 'marketing', 'admin', 'rent', 'professional_services',
                                   'software', 'travel', 'taxes', 'interest', 'depreciation',
                                   'other_expense', 'transfer', 'investment', 'loan', 'equity',
                                   'uncategorized', name='categorytype'), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_system', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('client_name', sa.String(length=200), nullable=True),
        sa.Column('status', sa.Enum('active', 'completed', 'on_hold', 'cancelled',
                                     name='projectstatus'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('budget_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('budget_currency', sa.String(length=3), nullable=True, default='EUR'),
        sa.Column('contract_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_billable', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Create qonto_accounts table
    op.create_table(
        'qonto_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('qonto_id', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('iban', sa.String(length=50), nullable=False),
        sa.Column('bic', sa.String(length=20), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True, default='EUR'),
        sa.Column('balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('authorized_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_main', sa.Boolean(), nullable=True, default=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iban'),
        sa.UniqueConstraint('qonto_id')
    )

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('qonto_id', sa.String(length=100), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True, default='EUR'),
        sa.Column('local_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('local_currency', sa.String(length=3), nullable=True),
        sa.Column('side', sa.Enum('credit', 'debit', name='transactionside'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'completed', 'declined', 'reversed',
                                     name='transactionstatus'), nullable=True),
        sa.Column('operation_type', sa.Enum('transfer', 'card', 'direct_debit', 'income',
                                            'qonto_fee', 'check', 'swift', 'other',
                                            name='transactiontype'), nullable=True),
        sa.Column('emitted_at', sa.DateTime(), nullable=False),
        sa.Column('settled_at', sa.DateTime(), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('label', sa.String(length=500), nullable=False),
        sa.Column('reference', sa.String(length=200), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('counterparty_name', sa.String(length=200), nullable=True),
        sa.Column('counterparty_iban', sa.String(length=50), nullable=True),
        sa.Column('card_last_digits', sa.String(length=4), nullable=True),
        sa.Column('vat_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('vat_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('has_attachments', sa.Boolean(), nullable=True, default=False),
        sa.Column('attachment_count', sa.Integer(), nullable=True, default=0),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('is_reconciled', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_excluded_from_reports', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['qonto_accounts.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('qonto_id')
    )

    # Create indexes
    op.create_index('ix_transactions_date', 'transactions', ['transaction_date'])
    op.create_index('ix_transactions_category', 'transactions', ['category_id'])
    op.create_index('ix_transactions_project', 'transactions', ['project_id'])
    op.create_index('ix_transactions_side', 'transactions', ['side'])


def downgrade() -> None:
    op.drop_index('ix_transactions_side', 'transactions')
    op.drop_index('ix_transactions_project', 'transactions')
    op.drop_index('ix_transactions_category', 'transactions')
    op.drop_index('ix_transactions_date', 'transactions')
    op.drop_table('transactions')
    op.drop_table('qonto_accounts')
    op.drop_table('projects')
    op.drop_table('categories')
