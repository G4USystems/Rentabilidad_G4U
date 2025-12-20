"""Add review_status to transactions

Revision ID: 003
Revises: 002
Create Date: 2024-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type
    op.execute("CREATE TYPE reviewstatus AS ENUM ('pending', 'confirmed')")

    # Add review_status column with default 'pending'
    op.add_column(
        'transactions',
        sa.Column(
            'review_status',
            sa.Enum('pending', 'confirmed', name='reviewstatus'),
            nullable=False,
            server_default='pending'
        )
    )

    # Create index for faster filtering
    op.create_index('ix_transactions_review_status', 'transactions', ['review_status'])


def downgrade() -> None:
    op.drop_index('ix_transactions_review_status', 'transactions')
    op.drop_column('transactions', 'review_status')
    op.execute("DROP TYPE reviewstatus")
