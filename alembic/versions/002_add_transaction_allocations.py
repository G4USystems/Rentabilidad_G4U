"""Add transaction_allocations table for partial assignments

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create transaction_allocations table
    op.create_table(
        'transaction_allocations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('client_name', sa.String(length=200), nullable=True),
        sa.Column('percentage', sa.Numeric(precision=7, scale=4), nullable=False, default=100),
        sa.Column('amount_allocated', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['transaction_id'],
            ['transactions.id'],
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['project_id'],
            ['projects.id'],
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries
    op.create_index('ix_allocations_transaction', 'transaction_allocations', ['transaction_id'])
    op.create_index('ix_allocations_project', 'transaction_allocations', ['project_id'])
    op.create_index('ix_allocations_client', 'transaction_allocations', ['client_name'])


def downgrade() -> None:
    op.drop_index('ix_allocations_client', 'transaction_allocations')
    op.drop_index('ix_allocations_project', 'transaction_allocations')
    op.drop_index('ix_allocations_transaction', 'transaction_allocations')
    op.drop_table('transaction_allocations')
